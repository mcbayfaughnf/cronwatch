"""Tests for cronwatch.export_server."""

import json
import csv
import io
import time
import urllib.request
import pytest

from cronwatch.config import JobConfig, CronwatchConfig
from cronwatch.export_server import ExportServer
from cronwatch import metrics, history


@pytest.fixture(autouse=True)
def clear_state():
    metrics.reset()
    history.reset()
    yield
    metrics.reset()
    history.reset()


@pytest.fixture
def config():
    jobs = [
        JobConfig(name="nightly", schedule="0 3 * * *", max_duration=1800, missed_after=3600),
    ]
    return CronwatchConfig(jobs=jobs, webhook_url="http://example.com/hook", check_interval=60)


@pytest.fixture
def server(config):
    srv = ExportServer(config, host="127.0.0.1", port=19091)
    srv.start()
    time.sleep(0.05)  # allow thread to bind
    yield srv
    srv.stop()


def _get(path: str) -> tuple:
    url = f"http://127.0.0.1:19091{path}"
    with urllib.request.urlopen(url) as resp:
        return resp.status, resp.read().decode()


def test_export_json_endpoint(server):
    status, body = _get("/export/json")
    assert status == 200
    parsed = json.loads(body)
    assert "jobs" in parsed
    assert "nightly" in parsed["jobs"]


def test_export_csv_endpoint(server):
    status, body = _get("/export/csv")
    assert status == 200
    reader = csv.DictReader(io.StringIO(body))
    rows = list(reader)
    assert any(r["job"] == "nightly" for r in rows)


def test_unknown_path_returns_404(server):
    import urllib.error
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        _get("/unknown")
    assert exc_info.value.code == 404


def test_server_stop_is_idempotent(config):
    srv = ExportServer(config, host="127.0.0.1", port=19092)
    srv.start()
    time.sleep(0.05)
    srv.stop()
    srv.stop()  # should not raise
