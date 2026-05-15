"""Integration tests: escalation interacting with alerts and notifier flow."""

import pytest

from cronwatch.alerts import Alert, AlertType
from cronwatch import escalation


@pytest.fixture(autouse=True)
def clear_all():
    escalation.reset()
    yield
    escalation.reset()


def _make_alert(job: str, kind: AlertType = AlertType.MISSED) -> Alert:
    return Alert(job_name=job, alert_type=kind, message=f"{kind.value} alert")


def test_no_escalation_before_threshold():
    alert = _make_alert("etl")
    for _ in range(2):
        escalation.record_occurrence(alert)
    assert not escalation.should_escalate(alert, threshold=3, cooldown=0)


def test_escalation_triggered_exactly_at_threshold():
    alert = _make_alert("etl")
    for _ in range(3):
        escalation.record_occurrence(alert)
    assert escalation.should_escalate(alert, threshold=3, cooldown=0)


def test_record_escalated_prevents_immediate_re_escalation():
    alert = _make_alert("etl")
    for _ in range(5):
        escalation.record_occurrence(alert)
    assert escalation.should_escalate(alert, threshold=3, cooldown=60)
    escalation.record_escalated(alert)
    assert not escalation.should_escalate(alert, threshold=3, cooldown=60)


def test_multiple_jobs_escalate_independently():
    etl = _make_alert("etl")
    backup = _make_alert("backup")

    for _ in range(3):
        escalation.record_occurrence(etl)
    escalation.record_occurrence(backup)

    assert escalation.should_escalate(etl, threshold=3, cooldown=0)
    assert not escalation.should_escalate(backup, threshold=3, cooldown=0)


def test_summary_after_escalation_cycle():
    alert = _make_alert("reports")
    for _ in range(4):
        escalation.record_occurrence(alert)
    escalation.record_escalated(alert)

    summary = escalation.escalation_summary(alert)
    assert summary is not None
    assert "reports" in summary
    assert "4x" in summary
    assert "missed" in summary
