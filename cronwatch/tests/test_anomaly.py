"""Tests for cronwatch.anomaly."""

import pytest

import cronwatch.history as history
from cronwatch.anomaly import (
    DEFAULT_SIGMA_THRESHOLD,
    MIN_SAMPLES,
    _stddev,
    anomaly_summary,
    is_anomalous,
    runtime_stddev,
)


@pytest.fixture(autouse=True)
def clear_history():
    history.reset()
    yield
    history.reset()


def _add_runs(job_name: str, runtimes: list[float]):
    for rt in runtimes:
        history.record_run(job_name, runtime=rt, success=True)


# ---------------------------------------------------------------------------
# _stddev helper
# ---------------------------------------------------------------------------

def test_stddev_empty_returns_zero():
    assert _stddev([]) == 0.0


def test_stddev_uniform_returns_zero():
    assert _stddev([5.0, 5.0, 5.0]) == pytest.approx(0.0)


def test_stddev_known_values():
    # population stddev of [2, 4, 4, 4, 5, 5, 7, 9] == 2.0
    result = _stddev([2, 4, 4, 4, 5, 5, 7, 9])
    assert result == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# runtime_stddev
# ---------------------------------------------------------------------------

def test_runtime_stddev_none_when_no_runs():
    assert runtime_stddev("backup") is None


def test_runtime_stddev_none_with_single_run():
    _add_runs("backup", [10.0])
    assert runtime_stddev("backup") is None


def test_runtime_stddev_nonzero_with_multiple_runs():
    _add_runs("backup", [10.0, 20.0])
    result = runtime_stddev("backup")
    assert result is not None
    assert result > 0


# ---------------------------------------------------------------------------
# is_anomalous
# ---------------------------------------------------------------------------

def test_not_anomalous_below_min_samples():
    _add_runs("sync", [10.0, 11.0, 10.5])  # fewer than MIN_SAMPLES
    assert is_anomalous("sync", 999.0) is False


def test_not_anomalous_within_normal_range():
    _add_runs("sync", [10.0] * MIN_SAMPLES)
    assert is_anomalous("sync", 10.5) is False


def test_anomalous_when_runtime_far_above_mean():
    # mean=10, stddev≈0 → any large value should trigger
    _add_runs("sync", [10.0] * MIN_SAMPLES)
    assert is_anomalous("sync", 50.0) is True


def test_anomalous_respects_custom_sigma():
    # With a high sigma threshold the same value should not trigger
    _add_runs("sync", [10.0] * MIN_SAMPLES)
    assert is_anomalous("sync", 50.0, sigma_threshold=1000.0) is False


def test_anomalous_respects_custom_min_samples():
    _add_runs("sync", [10.0, 10.0])  # only 2 runs
    # With min_samples=2 it should now evaluate properly
    assert is_anomalous("sync", 10.1, min_samples=2) is False


# ---------------------------------------------------------------------------
# anomaly_summary
# ---------------------------------------------------------------------------

def test_anomaly_summary_keys():
    summary = anomaly_summary("report")
    assert set(summary.keys()) == {"job", "sample_count", "mean_runtime", "stddev_runtime", "ready"}


def test_anomaly_summary_not_ready_when_few_samples():
    _add_runs("report", [5.0, 6.0])
    summary = anomaly_summary("report")
    assert summary["ready"] is False
    assert summary["sample_count"] == 2


def test_anomaly_summary_ready_with_enough_samples():
    _add_runs("report", [5.0] * MIN_SAMPLES)
    summary = anomaly_summary("report")
    assert summary["ready"] is True
    assert summary["mean_runtime"] == pytest.approx(5.0)
