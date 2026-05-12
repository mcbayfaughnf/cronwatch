"""Tests for cronwatch.watcher.LogWatcher."""

import os
import time
import pytest

from cronwatch.tracker import Tracker
from cronwatch.config import JobConfig
from cronwatch.watcher import LogWatcher


JOB_NAME = "backup"


@pytest.fixture()
def job_configs():
    return {
        JOB_NAME: JobConfig(
            name=JOB_NAME,
            schedule="0 2 * * *",
            max_runtime=3600,
            alert_after=120,
        )
    }


@pytest.fixture()
def tracker(job_configs):
    return Tracker(job_configs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: str, content: str) -> None:
    with open(path, "a") as fh:
        fh.write(content)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_step_processes_start_line(tmp_path, tracker):
    log = tmp_path / "cron.log"
    log.write_text(f"CRONWATCH START job={JOB_NAME}\n")

    watcher = LogWatcher(str(log), tracker)
    watcher.step()

    assert tracker.is_running(JOB_NAME)


def test_step_processes_finish_line(tmp_path, tracker):
    log = tmp_path / "cron.log"
    log.write_text(
        f"CRONWATCH START job={JOB_NAME}\n"
        f"CRONWATCH FINISH job={JOB_NAME}\n"
    )

    watcher = LogWatcher(str(log), tracker)
    watcher.step()
    watcher.step()  # second step should be a no-op (no new lines)

    assert not tracker.is_running(JOB_NAME)


def test_step_handles_missing_file(tmp_path, tracker, caplog):
    watcher = LogWatcher(str(tmp_path / "missing.log"), tracker)
    # Should not raise
    watcher.step()
    assert "not found" in caplog.text


def test_rotation_detection(tmp_path, tracker):
    log = tmp_path / "cron.log"
    log.write_text(f"CRONWATCH START job={JOB_NAME}\n")

    watcher = LogWatcher(str(log), tracker)
    watcher.step()
    assert tracker.is_running(JOB_NAME)

    # Simulate rotation: replace file with a finish line
    log.unlink()
    log.write_text(f"CRONWATCH FINISH job={JOB_NAME}\n")

    watcher.step()
    assert not tracker.is_running(JOB_NAME)


def test_stop_closes_file(tmp_path, tracker):
    log = tmp_path / "cron.log"
    log.write_text("")

    watcher = LogWatcher(str(log), tracker)
    watcher.step()  # opens the file
    assert watcher._file is not None

    watcher.stop()
    assert watcher._file is None
