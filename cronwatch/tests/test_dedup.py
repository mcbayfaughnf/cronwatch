"""Tests for cronwatch.dedup."""

import time
import pytest
from unittest.mock import patch

from cronwatch.alerts import Alert, AlertType
import cronwatch.dedup as dedup


@pytest.fixture(autouse=True)
def clear_state():
    dedup.reset()
    yield
    dedup.reset()


@pytest.fixture
def missed():
    return Alert(job_name="backup", alert_type=AlertType.MISSED, message="missed")


@pytest.fixture
def long_running():
    return Alert(job_name="backup", alert_type=AlertType.LONG_RUNNING, message="slow")


def test_not_duplicate_on_first_call(missed):
    assert dedup.is_duplicate(missed) is False


def test_duplicate_immediately_after_record(missed):
    dedup.record_sent(missed)
    assert dedup.is_duplicate(missed) is True


def test_not_duplicate_after_window_expires(missed):
    dedup.record_sent(missed)
    with patch("cronwatch.dedup.time") as mock_time:
        mock_time.time.return_value = time.time() + 400
        assert dedup.is_duplicate(missed, window_seconds=300) is False


def test_still_duplicate_within_window(missed):
    dedup.record_sent(missed)
    with patch("cronwatch.dedup.time") as mock_time:
        mock_time.time.return_value = time.time() + 100
        assert dedup.is_duplicate(missed, window_seconds=300) is True


def test_different_alert_types_tracked_independently(missed, long_running):
    dedup.record_sent(missed)
    assert dedup.is_duplicate(missed) is True
    assert dedup.is_duplicate(long_running) is False


def test_different_jobs_tracked_independently():
    a1 = Alert(job_name="job_a", alert_type=AlertType.MISSED, message="m")
    a2 = Alert(job_name="job_b", alert_type=AlertType.MISSED, message="m")
    dedup.record_sent(a1)
    assert dedup.is_duplicate(a1) is True
    assert dedup.is_duplicate(a2) is False


def test_time_since_last_none_before_record(missed):
    assert dedup.time_since_last(missed) is None


def test_time_since_last_returns_elapsed(missed):
    dedup.record_sent(missed)
    elapsed = dedup.time_since_last(missed)
    assert elapsed is not None
    assert 0.0 <= elapsed < 2.0


def test_reset_clears_state(missed):
    dedup.record_sent(missed)
    dedup.reset()
    assert dedup.is_duplicate(missed) is False


def test_dedup_summary_keys(missed):
    summary = dedup.dedup_summary(missed)
    assert "job" in summary
    assert "alert_type" in summary
    assert "is_duplicate" in summary
    assert "seconds_since_last" in summary
    assert "window_seconds" in summary


def test_dedup_summary_not_duplicate_before_record(missed):
    summary = dedup.dedup_summary(missed)
    assert summary["is_duplicate"] is False
    assert summary["seconds_since_last"] is None


def test_dedup_summary_is_duplicate_after_record(missed):
    dedup.record_sent(missed)
    summary = dedup.dedup_summary(missed)
    assert summary["is_duplicate"] is True
    assert summary["seconds_since_last"] is not None
