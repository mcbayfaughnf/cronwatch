"""Integration tests: baseline interacts with checker to suppress/raise alerts."""

import time
import pytest
from unittest.mock import patch, MagicMock
from cronwatch import history, baseline
from cronwatch.baseline import MIN_SAMPLES, is_within_baseline


@pytest.fixture(autouse=True)
def clear_history():
    history.reset()
    yield
    history.reset()


def _simulate_stable_job(job_name: str, runtime: float, count: int = MIN_SAMPLES):
    ts = time.time()
    for i in range(count):
        history.record_run(job_name, ts + i * 3600, runtime)


def test_no_baseline_before_min_samples():
    _simulate_stable_job("etl", 30.0, count=MIN_SAMPLES - 1)
    assert baseline.has_baseline("etl") is False
    assert is_within_baseline("etl", 30.0) is None


def test_baseline_established_after_min_samples():
    _simulate_stable_job("etl", 30.0, count=MIN_SAMPLES)
    assert baseline.has_baseline("etl") is True


def test_normal_runtime_within_baseline():
    _simulate_stable_job("etl", 30.0, count=10)
    assert is_within_baseline("etl", 31.0) is True


def test_spike_runtime_outside_baseline():
    _simulate_stable_job("etl", 30.0, count=10)
    # 300 seconds is far outside 2-stddev range of a uniform 30s job
    assert is_within_baseline("etl", 300.0) is False


def test_baseline_range_grows_with_variance():
    ts = time.time()
    # High-variance job
    runtimes = [10.0, 50.0, 10.0, 50.0, 30.0, 10.0, 50.0]
    for i, rt in enumerate(runtimes):
        history.record_run("variable", ts + i * 60, rt)

    bounds = baseline.baseline_range("variable")
    assert bounds is not None
    lower, upper = bounds
    # Range should be wide enough to accommodate spread
    assert upper - lower > 20.0


def test_summary_reflects_computed_range():
    _simulate_stable_job("report", 60.0, count=8)
    summary = baseline.baseline_summary("report")
    assert summary["has_baseline"] is True
    assert summary["lower"] <= 60.0 <= summary["upper"]
