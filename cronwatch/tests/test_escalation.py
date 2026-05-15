"""Tests for cronwatch.escalation."""

import time
import pytest

from cronwatch.alerts import Alert, AlertType
from cronwatch import escalation


@pytest.fixture(autouse=True)
def clear_state():
    escalation.reset()
    yield
    escalation.reset()


@pytest.fixture
def missed():
    return Alert(job_name="backup", alert_type=AlertType.MISSED, message="missed")


@pytest.fixture
def long_running():
    return Alert(job_name="backup", alert_type=AlertType.LONG_RUNNING, message="slow")


def test_record_occurrence_starts_at_one(missed):
    count = escalation.record_occurrence(missed)
    assert count == 1


def test_record_occurrence_increments(missed):
    escalation.record_occurrence(missed)
    escalation.record_occurrence(missed)
    count = escalation.record_occurrence(missed)
    assert count == 3


def test_should_not_escalate_below_threshold(missed):
    escalation.record_occurrence(missed)
    escalation.record_occurrence(missed)
    assert not escalation.should_escalate(missed, threshold=3, cooldown=0)


def test_should_escalate_at_threshold_with_zero_cooldown(missed):
    for _ in range(3):
        escalation.record_occurrence(missed)
    assert escalation.should_escalate(missed, threshold=3, cooldown=0)


def test_should_not_escalate_within_cooldown(missed):
    for _ in range(3):
        escalation.record_occurrence(missed)
    escalation.record_escalated(missed)
    assert not escalation.should_escalate(missed, threshold=3, cooldown=3600)


def test_should_escalate_after_cooldown(missed, monkeypatch):
    for _ in range(3):
        escalation.record_occurrence(missed)
    escalation.record_escalated(missed)
    # Advance time beyond cooldown
    future = time.time() + 3601
    monkeypatch.setattr("cronwatch.escalation.time", type("T", (), {"time": staticmethod(lambda: future)})())
    assert escalation.should_escalate(missed, threshold=3, cooldown=3600)


def test_different_alert_types_are_independent(missed, long_running):
    for _ in range(3):
        escalation.record_occurrence(missed)
    assert escalation.should_escalate(missed, threshold=3, cooldown=0)
    assert not escalation.should_escalate(long_running, threshold=3, cooldown=0)


def test_escalation_summary_none_when_no_state(missed):
    assert escalation.escalation_summary(missed) is None


def test_escalation_summary_contains_job_name(missed):
    escalation.record_occurrence(missed)
    summary = escalation.escalation_summary(missed)
    assert summary is not None
    assert "backup" in summary


def test_escalation_summary_contains_count(missed):
    for _ in range(5):
        escalation.record_occurrence(missed)
    summary = escalation.escalation_summary(missed)
    assert "5x" in summary
