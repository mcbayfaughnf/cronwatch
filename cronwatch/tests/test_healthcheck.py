"""Tests for cronwatch.healthcheck."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.healthcheck import HealthcheckServer, _build_status
from cronwatch.tracker import JobState


@pytest.fixture()
def tracker():
    """A minimal mock tracker with two jobs."""
    t = MagicMock()
    t.job_configs = {"backup": MagicMock(), "sync": MagicMock()}
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    backup_state = JobState()
    backup_state.last_started = now
    backup_state.last_finished = now
    backup_state.running = False
    sync_state = JobState()
    sync_state.last_started = None
    sync_state.last_finished = None
    sync_state.running = True
    t.state = {"backup": backup_state, "sync": sync_state}
    t.is_running.side_effect = lambda name: t.state[name].running
    return t


def test_build_status_keys(tracker):
    status = _build_status(tracker)
    assert status["status"] == "ok"
    assert "backup" in status["jobs"]
    assert "sync" in status["jobs"]


def test_build_status_running_flag(tracker):
    status = _build_status(tracker)
    assert status["jobs"]["backup"]["running"] is False
    assert status["jobs"]["sync"]["running"] is True


def test_build_status_timestamps(tracker):
    status = _build_status(tracker)
    assert status["jobs"]["backup"]["last_finished"] == "2024-01-01T12:00:00+00:00"
    assert status["jobs"]["sync"]["last_finished"] is None


def test_healthcheck_server_start_stop(tracker):
    server = HealthcheckServer(tracker, host="127.0.0.1", port=19876)
    server.start()
    assert server._thread is not None
    assert server._thread.is_alive()
    server.stop()


def test_healthcheck_server_responds(tracker):
    import urllib.request

    server = HealthcheckServer(tracker, host="127.0.0.1", port=19877)
    server.start()
    try:
        with urllib.request.urlopen("http://127.0.0.1:19877/health") as resp:
            assert resp.status == 200
            body = json.loads(resp.read())
            assert body["status"] == "ok"
    finally:
        server.stop()


def test_healthcheck_404_for_unknown_path(tracker):
    import urllib.error
    import urllib.request

    server = HealthcheckServer(tracker, host="127.0.0.1", port=19878)
    server.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen("http://127.0.0.1:19878/unknown")
        assert exc_info.value.code == 404
    finally:
        server.stop()
