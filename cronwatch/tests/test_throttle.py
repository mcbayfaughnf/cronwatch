"""Tests for cronwatch.throttle."""

import pytest

from cronwatch.alerts import Alert, AlertType
from cronwatch.throttle import (
    DEFAULT_MIN_INTERVAL,
    is_throttled,
    record_sent,
    reset,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_state():
    """Ensure throttle state is clean before every test."""
    reset()
    yield
    reset()


@pytest.fixture
def missed_alert():
    return Alert(job_name="backup", alert_type=AlertType.MISSED, message="missed")


@pytest.fixture
def long_alert():
    return Alert(job_name="backup", alert_type=AlertType.LONG_RUNNING, message="slow")


# ---------------------------------------------------------------------------
# is_throttled
# ---------------------------------------------------------------------------

def test_not_throttled_on_first_call(missed_alert):
    assert is_throttled(missed_alert) is False


def test_throttled_immediately_after_record(missed_alert):
    now = 1_000_000.0
    record_sent(missed_alert, _now=now)
    assert is_throttled(missed_alert, _now=now + 1) is True


def test_not_throttled_after_interval_expires(missed_alert):
    now = 1_000_000.0
    record_sent(missed_alert, _now=now)
    future = now + DEFAULT_MIN_INTERVAL + 1
    assert is_throttled(missed_alert, _now=future) is False


def test_throttled_at_exact_interval_boundary(missed_alert):
    now = 1_000_000.0
    record_sent(missed_alert, _now=now)
    # strictly less-than, so exactly at boundary is still throttled
    assert is_throttled(missed_alert, _now=now + DEFAULT_MIN_INTERVAL) is True


def test_different_alert_types_tracked_independently(missed_alert, long_alert):
    now = 1_000_000.0
    record_sent(missed_alert, _now=now)
    # long_alert for same job should NOT be throttled
    assert is_throttled(long_alert, _now=now + 1) is False


def test_different_jobs_tracked_independently():
    a1 = Alert(job_name="jobA", alert_type=AlertType.MISSED, message="m")
    a2 = Alert(job_name="jobB", alert_type=AlertType.MISSED, message="m")
    now = 1_000_000.0
    record_sent(a1, _now=now)
    assert is_throttled(a2, _now=now + 1) is False


def test_custom_min_interval(missed_alert):
    now = 1_000_000.0
    record_sent(missed_alert, _now=now)
    # With a very short interval the alert should no longer be throttled
    assert is_throttled(missed_alert, min_interval=5, _now=now + 10) is False


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

def test_reset_clears_state(missed_alert):
    now = 1_000_000.0
    record_sent(missed_alert, _now=now)
    reset()
    assert is_throttled(missed_alert, _now=now + 1) is False
