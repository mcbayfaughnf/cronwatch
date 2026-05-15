"""Integration tests: dedup interacting with alert dispatch flow."""

import pytest
from unittest.mock import patch, MagicMock

from cronwatch.alerts import Alert, AlertType
import cronwatch.dedup as dedup


@pytest.fixture(autouse=True)
def clear_all():
    dedup.reset()
    yield
    dedup.reset()


def _make_alert(job: str, kind: AlertType) -> Alert:
    return Alert(job_name=job, alert_type=kind, message="test")


def _dispatch(alert: Alert, window: float = 300) -> bool:
    """Simulate a dispatch that honours dedup. Returns True if alert was sent."""
    if dedup.is_duplicate(alert, window_seconds=window):
        return False
    dedup.record_sent(alert)
    return True


def test_first_alert_is_sent():
    a = _make_alert("etl", AlertType.MISSED)
    assert _dispatch(a) is True


def test_second_alert_within_window_is_suppressed():
    a = _make_alert("etl", AlertType.MISSED)
    assert _dispatch(a) is True
    assert _dispatch(a) is False


def test_alert_sent_again_after_window(monkeypatch):
    import time as _time
    a = _make_alert("etl", AlertType.MISSED)
    _dispatch(a)

    future = _time.time() + 400
    with patch("cronwatch.dedup.time") as mock_time:
        mock_time.time.return_value = future
        assert _dispatch(a, window=300) is True


def test_missed_and_long_running_sent_independently():
    missed = _make_alert("etl", AlertType.MISSED)
    long = _make_alert("etl", AlertType.LONG_RUNNING)
    assert _dispatch(missed) is True
    assert _dispatch(long) is True
    # second round — both suppressed
    assert _dispatch(missed) is False
    assert _dispatch(long) is False


def test_multiple_jobs_do_not_interfere():
    a = _make_alert("job_a", AlertType.MISSED)
    b = _make_alert("job_b", AlertType.MISSED)
    assert _dispatch(a) is True
    assert _dispatch(b) is True
    assert _dispatch(a) is False
    assert _dispatch(b) is False
