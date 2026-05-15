"""Integration tests: ratelimit interacts with alerts and notifier."""

import time
import pytest
from cronwatch.alerts import Alert, AlertType
import cronwatch.ratelimit as rl
import cronwatch.notifier as notifier


@pytest.fixture(autouse=True)
def clear_all():
    rl.reset()
    notifier.reset()
    yield
    rl.reset()
    notifier.reset()


def _make_alert(kind: AlertType, job: str) -> Alert:
    return Alert(type=kind, job_name=job, message=f"{kind.value} {job}")


def test_first_alert_is_not_rate_limited():
    alert = _make_alert(AlertType.MISSED, "sync_job")
    assert not rl.is_rate_limited(alert.type.value, alert.job_name)


def test_second_alert_within_window_is_limited():
    alert = _make_alert(AlertType.MISSED, "sync_job")
    rl.record_sent(alert.type.value, alert.job_name)
    assert rl.is_rate_limited(alert.type.value, alert.job_name)


def test_long_running_and_missed_are_tracked_independently():
    job = "etl_job"
    rl.record_sent(AlertType.MISSED.value, job)
    assert not rl.is_rate_limited(AlertType.LONG_RUNNING.value, job)


def test_rate_limit_does_not_affect_different_jobs():
    rl.record_sent(AlertType.MISSED.value, "job_a")
    assert not rl.is_rate_limited(AlertType.MISSED.value, "job_b")


def test_reset_clears_all_entries():
    rl.record_sent(AlertType.MISSED.value, "job_a")
    rl.record_sent(AlertType.LONG_RUNNING.value, "job_b")
    rl.reset()
    assert not rl.is_rate_limited(AlertType.MISSED.value, "job_a")
    assert not rl.is_rate_limited(AlertType.LONG_RUNNING.value, "job_b")
