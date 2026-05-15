"""Integration tests: silence windows interact with checker-style alert suppression."""

import time
import pytest

from cronwatch import silence
from cronwatch.alerts import AlertType, Alert


@pytest.fixture(autouse=True)
def clear_state():
    silence.reset()
    yield
    silence.reset()


def _make_alert(job_name: str, kind: AlertType) -> Alert:
    return Alert(job_name=job_name, alert_type=kind, message=f"{kind.value} alert for {job_name}")


def _should_send(alert: Alert, now: float) -> bool:
    """Simulate the gate that checker would use before dispatching."""
    return not silence.is_silenced(alert.job_name, now=now)


# ---------------------------------------------------------------------------
# Scenario: missed-job alert suppressed during maintenance window
# ---------------------------------------------------------------------------

def test_missed_alert_suppressed_during_window():
    now = time.time()
    silence.add_window("nightly_backup", now - 300, now + 300)
    alert = _make_alert("nightly_backup", AlertType.MISSED)
    assert _should_send(alert, now=now) is False


def test_missed_alert_sent_outside_window():
    now = time.time()
    silence.add_window("nightly_backup", now + 1000, now + 2000)
    alert = _make_alert("nightly_backup", AlertType.MISSED)
    assert _should_send(alert, now=now) is True


# ---------------------------------------------------------------------------
# Scenario: window expires and alerts resume
# ---------------------------------------------------------------------------

def test_alert_resumes_after_window_expires():
    now = 2_000_000.0
    silence.add_window("report_job", now - 100, now - 1)  # already expired
    alert = _make_alert("report_job", AlertType.LONG_RUNNING)
    assert _should_send(alert, now=now) is True


# ---------------------------------------------------------------------------
# Scenario: multiple jobs, only one silenced
# ---------------------------------------------------------------------------

def test_only_silenced_job_is_suppressed():
    now = time.time()
    silence.add_window("maintenance_job", now - 60, now + 60)

    silenced_alert = _make_alert("maintenance_job", AlertType.MISSED)
    other_alert = _make_alert("critical_job", AlertType.MISSED)

    assert _should_send(silenced_alert, now=now) is False
    assert _should_send(other_alert, now=now) is True


# ---------------------------------------------------------------------------
# Scenario: overlapping windows still silence correctly
# ---------------------------------------------------------------------------

def test_overlapping_windows_keep_job_silenced():
    now = 3_000_000.0
    silence.add_window("deploy_job", now - 200, now + 100)
    silence.add_window("deploy_job", now - 50, now + 300)
    alert = _make_alert("deploy_job", AlertType.MISSED)
    assert _should_send(alert, now=now) is False


# ---------------------------------------------------------------------------
# Scenario: reset clears all windows
# ---------------------------------------------------------------------------

def test_reset_removes_all_windows():
    now = time.time()
    silence.add_window("job_a", now - 60, now + 60)
    silence.add_window("job_b", now - 60, now + 60)
    silence.reset()
    assert silence.is_silenced("job_a", now=now) is False
    assert silence.is_silenced("job_b", now=now) is False
