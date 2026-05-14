"""Tests for cronwatch.retention."""

import time
import pytest

import cronwatch.history as history
import cronwatch.retention as retention


@pytest.fixture(autouse=True)
def clear_state():
    """Reset history and retention state before each test."""
    history.reset()
    retention._reset_last_prune_time()
    yield
    history.reset()
    retention._reset_last_prune_time()


def _record(job: str, finished_at: float, duration: float = 1.0):
    history._ensure(job)
    history._runs[job].append({"finished_at": finished_at, "duration": duration})


# --- is_prune_due ---

def test_prune_due_first_time():
    assert retention.is_prune_due(3600) is True


def test_prune_not_due_immediately_after_record():
    retention._last_prune_time = time.time()
    assert retention.is_prune_due(3600) is False


def test_prune_due_after_interval(monkeypatch):
    retention._last_prune_time = time.time() - 3601
    assert retention.is_prune_due(3600) is True


# --- prune_history ---

def test_prune_history_removes_old_records():
    now = time.time()
    _record("backup", finished_at=now - 7200)  # old
    _record("backup", finished_at=now - 100)   # recent
    removed = retention.prune_history("backup", max_age_seconds=3600)
    assert removed == 1
    assert len(history.get_runs("backup")) == 1


def test_prune_history_keeps_recent_records():
    now = time.time()
    _record("sync", finished_at=now - 60)
    _record("sync", finished_at=now - 30)
    removed = retention.prune_history("sync", max_age_seconds=3600)
    assert removed == 0
    assert len(history.get_runs("sync")) == 2


def test_prune_history_empty_job():
    removed = retention.prune_history("nonexistent", max_age_seconds=3600)
    assert removed == 0


def test_prune_history_removes_all_when_all_old():
    now = time.time()
    _record("old_job", finished_at=now - 10000)
    _record("old_job", finished_at=now - 9000)
    removed = retention.prune_history("old_job", max_age_seconds=3600)
    assert removed == 2
    assert history.get_runs("old_job") == []


# --- prune_all ---

def test_prune_all_returns_per_job_counts():
    now = time.time()
    _record("job_a", finished_at=now - 7200)
    _record("job_a", finished_at=now - 10)
    _record("job_b", finished_at=now - 8000)
    results = retention.prune_all(["job_a", "job_b"], max_age_seconds=3600)
    assert results["job_a"] == 1
    assert results["job_b"] == 1


def test_prune_all_updates_last_prune_time():
    retention.prune_all(["job_x"], max_age_seconds=3600)
    assert retention._last_prune_time is not None


# --- maybe_prune ---

def test_maybe_prune_runs_when_due():
    now = time.time()
    _record("cron", finished_at=now - 9000)
    retention.maybe_prune(["cron"], max_age_seconds=3600, interval_seconds=0)
    assert len(history.get_runs("cron")) == 0


def test_maybe_prune_skips_when_not_due():
    now = time.time()
    _record("cron", finished_at=now - 9000)
    retention._last_prune_time = time.time()  # just pruned
    retention.maybe_prune(["cron"], max_age_seconds=3600, interval_seconds=3600)
    # record should still be there because prune was skipped
    assert len(history.get_runs("cron")) == 1
