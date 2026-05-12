"""Tests for cronwatch.notifier."""

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerts import Alert, AlertType
from cronwatch.notifier import notify, record_notified, reset, should_notify

WEBHOOK = "https://hooks.example.com/test"
COOLDOWN = 300


@pytest.fixture(autouse=True)
def clear_state():
    """Reset notifier state before every test."""
    reset()
    yield
    reset()


@pytest.fixture
def missed_alert():
    return Alert(job_name="backup", alert_type=AlertType.MISSED, detail="overdue by 10m")


@pytest.fixture
def long_alert():
    return Alert(job_name="backup", alert_type=AlertType.LONG_RUNNING, detail="running 20m")


# --- should_notify ---

def test_should_notify_first_time(missed_alert):
    assert should_notify(missed_alert, COOLDOWN) is True


def test_should_notify_within_cooldown(missed_alert):
    now = time.time()
    record_notified(missed_alert, now=now)
    assert should_notify(missed_alert, COOLDOWN, now=now + COOLDOWN - 1) is False


def test_should_notify_after_cooldown(missed_alert):
    now = time.time()
    record_notified(missed_alert, now=now)
    assert should_notify(missed_alert, COOLDOWN, now=now + COOLDOWN) is True


def test_different_alert_types_tracked_independently(missed_alert, long_alert):
    now = time.time()
    record_notified(missed_alert, now=now)
    # long_running for same job should still be allowed
    assert should_notify(long_alert, COOLDOWN, now=now + 1) is True


def test_different_jobs_tracked_independently():
    alert_a = Alert(job_name="job_a", alert_type=AlertType.MISSED, detail="")
    alert_b = Alert(job_name="job_b", alert_type=AlertType.MISSED, detail="")
    now = time.time()
    record_notified(alert_a, now=now)
    assert should_notify(alert_b, COOLDOWN, now=now + 1) is True


# --- notify ---

def test_notify_dispatches_on_first_call(missed_alert):
    with patch("cronwatch.notifier.send_alert") as mock_send:
        result = notify(missed_alert, WEBHOOK, cooldown_seconds=COOLDOWN)
    assert result is True
    mock_send.assert_called_once_with(missed_alert, WEBHOOK)


def test_notify_suppresses_within_cooldown(missed_alert):
    now = time.time()
    record_notified(missed_alert, now=now - 10)  # 10s ago
    with patch("cronwatch.notifier.send_alert") as mock_send:
        result = notify(missed_alert, WEBHOOK, cooldown_seconds=COOLDOWN)
    assert result is False
    mock_send.assert_not_called()


def test_notify_returns_false_on_send_exception(missed_alert):
    with patch("cronwatch.notifier.send_alert", side_effect=RuntimeError("network error")):
        result = notify(missed_alert, WEBHOOK, cooldown_seconds=COOLDOWN)
    assert result is False
    # Should not record a successful notification
    assert should_notify(missed_alert, COOLDOWN) is True


def test_notify_records_timestamp_after_success(missed_alert):
    with patch("cronwatch.notifier.send_alert"):
        notify(missed_alert, WEBHOOK, cooldown_seconds=COOLDOWN)
    # Immediately after, should be suppressed
    assert should_notify(missed_alert, COOLDOWN) is False
