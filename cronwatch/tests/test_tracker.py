"""Tests for cronwatch.tracker module."""

import time
from unittest.mock import patch

import pytest

from cronwatch.config import JobConfig
from cronwatch.tracker import JobState, JobTracker


@pytest.fixture
def job_configs():
    return {
        "backup": JobConfig(
            name="backup",
            max_runtime_seconds=60,
            expected_interval_seconds=3600,
        ),
        "cleanup": JobConfig(
            name="cleanup",
            max_runtime_seconds=None,
            expected_interval_seconds=None,
        ),
    }


@pytest.fixture
def tracker(job_configs):
    return JobTracker(jobs=job_configs)


def test_initial_state_is_not_running(tracker):
    state = tracker.get_state("backup")
    assert state is not None
    assert state.is_running is False
    assert state.started_at is None
    assert state.last_seen is None


def test_start_marks_job_running(tracker):
    tracker.start("backup")
    state = tracker.get_state("backup")
    assert state.is_running is True
    assert state.started_at is not None
    assert state.last_seen is not None


def test_finish_clears_running_state(tracker):
    tracker.start("backup")
    tracker.finish("backup")
    state = tracker.get_state("backup")
    assert state.is_running is False
    assert state.started_at is None


def test_runtime_seconds_returns_none_when_not_running(tracker):
    state = tracker.get_state("backup")
    assert state.runtime_seconds() is None


def test_check_long_running_true_when_exceeded(tracker):
    tracker.start("backup")
    state = tracker.get_state("backup")
    # Simulate the job having started 120 seconds ago
    state.started_at -= 120
    assert tracker.check_long_running("backup") is True


def test_check_long_running_false_within_limit(tracker):
    tracker.start("backup")
    assert tracker.check_long_running("backup") is False


def test_check_long_running_false_when_no_threshold(tracker):
    tracker.start("cleanup")
    state = tracker.get_state("cleanup")
    state.started_at -= 9999
    assert tracker.check_long_running("cleanup") is False


def test_check_missed_true_when_overdue(tracker):
    tracker.start("backup")
    tracker.finish("backup")
    state = tracker.get_state("backup")
    # Simulate last seen 2 hours ago
    state.last_seen -= 7200
    assert tracker.check_missed("backup") is True


def test_check_missed_false_when_recent(tracker):
    tracker.start("backup")
    tracker.finish("backup")
    assert tracker.check_missed("backup") is False


def test_check_missed_false_when_never_seen(tracker):
    # last_seen is None — no data yet, should not alert
    assert tracker.check_missed("backup") is False


def test_get_state_returns_none_for_unknown_job(tracker):
    assert tracker.get_state("nonexistent") is None
