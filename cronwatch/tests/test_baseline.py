"""Tests for cronwatch.baseline."""

import pytest
from cronwatch import history, baseline
from cronwatch.baseline import (
    has_baseline,
    baseline_range,
    is_within_baseline,
    baseline_summary,
    MIN_SAMPLES,
)


@pytest.fixture(autouse=True)
def clear_history():
    history.reset()
    yield
    history.reset()


def _add_runs(job_name: str, runtimes: list):
    import time
    ts = time.time()
    for i, rt in enumerate(runtimes):
        history.record_run(job_name, ts + i * 60, rt)


def test_has_baseline_false_when_empty():
    assert has_baseline("backup") is False


def test_has_baseline_false_below_min_samples():
    _add_runs("backup", [10.0] * (MIN_SAMPLES - 1))
    assert has_baseline("backup") is False


def test_has_baseline_true_at_min_samples():
    _add_runs("backup", [10.0] * MIN_SAMPLES)
    assert has_baseline("backup") is True


def test_baseline_range_none_when_no_data():
    assert baseline_range("backup") is None


def test_baseline_range_returns_tuple():
    _add_runs("backup", [10.0, 11.0, 10.5, 9.5, 10.2])
    result = baseline_range("backup")
    assert result is not None
    lower, upper = result
    assert lower < upper
    assert lower >= 0.0


def test_baseline_range_uniform_runtimes():
    _add_runs("backup", [10.0] * 10)
    lower, upper = baseline_range("backup")
    # stddev is 0, so lower == upper == mean
    assert abs(lower - 10.0) < 1e-9
    assert abs(upper - 10.0) < 1e-9


def test_is_within_baseline_none_when_no_baseline():
    assert is_within_baseline("backup", 10.0) is None


def test_is_within_baseline_true_for_normal_value():
    _add_runs("backup", [10.0, 11.0, 10.5, 9.5, 10.2])
    assert is_within_baseline("backup", 10.0) is True


def test_is_within_baseline_false_for_outlier():
    _add_runs("backup", [10.0, 11.0, 10.5, 9.5, 10.2])
    assert is_within_baseline("backup", 999.0) is False


def test_baseline_summary_no_baseline():
    result = baseline_summary("backup")
    assert result["has_baseline"] is False
    assert result["lower"] is None
    assert result["upper"] is None


def test_baseline_summary_with_baseline():
    _add_runs("backup", [10.0, 11.0, 10.5, 9.5, 10.2])
    result = baseline_summary("backup")
    assert result["has_baseline"] is True
    assert result["job"] == "backup"
    assert isinstance(result["lower"], float)
    assert isinstance(result["upper"], float)


def test_multiple_jobs_are_independent():
    _add_runs("jobA", [5.0] * MIN_SAMPLES)
    _add_runs("jobB", [100.0] * MIN_SAMPLES)
    rA = baseline_range("jobA")
    rB = baseline_range("jobB")
    assert rA is not None
    assert rB is not None
    assert rA[1] < rB[0]
