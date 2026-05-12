"""Tests for cronwatch.summary."""

import time
import pytest

from cronwatch.config import CronwatchConfig, JobConfig
from cronwatch.tracker import Tracker
from cronwatch.summary import build_summary, log_summary


@pytest.fixture
def job_configs():
    return [
        JobConfig(name="job_a", schedule="* * * * *", interval_seconds=60, max_runtime_seconds=30),
        JobConfig(name="job_b", schedule="*/5 * * * *", interval_seconds=300, max_runtime_seconds=120),
    ]


@pytest.fixture
def config(job_configs):
    return CronwatchConfig(
        webhook_url="http://example.com/hook",
        jobs=job_configs,
        check_interval_seconds=10,
    )


@pytest.fixture
def tracker(job_configs):
    return Tracker(job_configs)


def test_build_summary_keys(config, tracker):
    summary = build_summary(config, tracker)
    assert "generated_at" in summary
    assert "total_jobs" in summary
    assert "running" in summary
    assert "overdue" in summary
    assert "jobs" in summary


def test_build_summary_total_jobs(config, tracker):
    summary = build_summary(config, tracker)
    assert summary["total_jobs"] == 2


def test_build_summary_all_overdue_when_never_run(config, tracker):
    summary = build_summary(config, tracker)
    assert summary["overdue"] == 2
    for job in summary["jobs"]:
        assert job["overdue"] is True
        assert job["last_finished"] is None


def test_build_summary_running_job(config, tracker):
    tracker.mark_started("job_a")
    summary = build_summary(config, tracker)
    running_jobs = [j for j in summary["jobs"] if j["name"] == "job_a"]
    assert len(running_jobs) == 1
    assert running_jobs[0]["running"] is True
    assert running_jobs[0]["elapsed_seconds"] is not None
    assert running_jobs[0]["elapsed_seconds"] >= 0
    assert summary["running"] == 1


def test_build_summary_finished_job_not_overdue(config, tracker):
    tracker.mark_started("job_b")
    tracker.mark_finished("job_b")
    summary = build_summary(config, tracker)
    job_b = next(j for j in summary["jobs"] if j["name"] == "job_b")
    # Just finished, should not be overdue yet
    assert job_b["overdue"] is False
    assert job_b["last_finished"] is not None
    assert job_b["running"] is False
    assert job_b["elapsed_seconds"] is None


def test_build_summary_timestamps_are_iso_format(config, tracker):
    tracker.mark_started("job_a")
    tracker.mark_finished("job_a")
    summary = build_summary(config, tracker)
    job_a = next(j for j in summary["jobs"] if j["name"] == "job_a")
    # Should be parseable ISO strings
    from datetime import datetime
    datetime.fromisoformat(job_a["last_started"])
    datetime.fromisoformat(job_a["last_finished"])


def test_log_summary_does_not_raise(config, tracker, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="cronwatch.summary"):
        log_summary(config, tracker)
    assert "Summary" in caplog.text
