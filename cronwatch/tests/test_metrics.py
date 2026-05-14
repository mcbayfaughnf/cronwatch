"""Tests for cronwatch.metrics."""

import pytest
import cronwatch.metrics as metrics


@pytest.fixture(autouse=True)
def clear_metrics():
    """Reset metrics state before each test."""
    metrics.reset()
    yield
    metrics.reset()


def test_average_runtime_none_when_no_samples():
    assert metrics.average_runtime("backup") is None


def test_max_runtime_none_when_no_samples():
    assert metrics.max_runtime("backup") is None


def test_record_and_average_runtime():
    metrics.record_runtime("backup", 10.0)
    metrics.record_runtime("backup", 20.0)
    assert metrics.average_runtime("backup") == 15.0


def test_record_and_max_runtime():
    metrics.record_runtime("backup", 10.0)
    metrics.record_runtime("backup", 35.0)
    metrics.record_runtime("backup", 5.0)
    assert metrics.max_runtime("backup") == 35.0


def test_alert_count_zero_when_none_recorded():
    assert metrics.alert_count("backup", "missed") == 0


def test_record_and_retrieve_alert_count():
    metrics.record_alert("backup", "missed")
    metrics.record_alert("backup", "missed")
    metrics.record_alert("backup", "long_running")
    assert metrics.alert_count("backup", "missed") == 2
    assert metrics.alert_count("backup", "long_running") == 1


def test_build_metrics_snapshot_keys():
    metrics.record_runtime("sync", 5.0)
    snapshot = metrics.build_metrics_snapshot()
    assert "uptime_seconds" in snapshot
    assert "jobs" in snapshot


def test_build_metrics_snapshot_job_fields():
    metrics.record_runtime("sync", 8.0)
    metrics.record_runtime("sync", 12.0)
    metrics.record_alert("sync", "missed")
    snapshot = metrics.build_metrics_snapshot()
    job = snapshot["jobs"]["sync"]
    assert job["average_runtime_seconds"] == 10.0
    assert job["max_runtime_seconds"] == 12.0
    assert job["sample_count"] == 2
    assert job["alerts"] == {"missed": 1}


def test_build_metrics_snapshot_includes_alert_only_jobs():
    metrics.record_alert("nightly", "missed")
    snapshot = metrics.build_metrics_snapshot()
    assert "nightly" in snapshot["jobs"]
    assert snapshot["jobs"]["nightly"]["sample_count"] == 0
    assert snapshot["jobs"]["nightly"]["average_runtime_seconds"] is None


def test_reset_clears_all_state():
    metrics.record_runtime("sync", 5.0)
    metrics.record_alert("sync", "missed")
    metrics.reset()
    assert metrics.average_runtime("sync") is None
    assert metrics.alert_count("sync", "missed") == 0
    snapshot = metrics.build_metrics_snapshot()
    assert snapshot["jobs"] == {}


def test_uptime_seconds_is_non_negative():
    snapshot = metrics.build_metrics_snapshot()
    assert snapshot["uptime_seconds"] >= 0.0


def test_multiple_jobs_tracked_independently():
    metrics.record_runtime("job_a", 3.0)
    metrics.record_runtime("job_b", 9.0)
    assert metrics.average_runtime("job_a") == 3.0
    assert metrics.average_runtime("job_b") == 9.0
