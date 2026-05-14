"""Integration tests: export data reflects recorded metrics + history."""

import json
import pytest

from cronwatch.config import JobConfig, CronwatchConfig
from cronwatch import export, metrics, history


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
        JobConfig(name="sync", schedule="*/5 * * * *", max_duration=120, missed_after=600),
        JobConfig(name="cleanup", schedule="0 0 * * *", max_duration=300, missed_after=900),
    ]
    return CronwatchConfig(jobs=jobs, webhook_url="http://hook.example/", check_interval=30)


def _simulate_runs(job_name: str, runtimes, alert_count: int = 0):
    t = 1_000_000.0
    for rt in runtimes:
        history.record_run(job_name, started_at=t, finished_at=t + rt, runtime=rt)
        metrics.record_runtime(job_name, rt)
        t += 3600.0
    for _ in range(alert_count):
        metrics.record_alert(job_name)


def test_json_export_reflects_recorded_data(config):
    _simulate_runs("sync", [30.0, 60.0, 90.0], alert_count=1)
    raw = export.export_json(config)
    data = json.loads(raw)
    sync = data["jobs"]["sync"]
    assert sync["average_runtime"] == 60.0
    assert sync["max_runtime"] == 90.0
    assert sync["alert_count"] == 1
    assert sync["run_count"] == 3
    assert abs(sync["failure_rate"] - 0.3333) < 0.001


def test_csv_export_reflects_multiple_jobs(config):
    import csv, io
    _simulate_runs("sync", [45.0])
    _simulate_runs("cleanup", [200.0, 250.0])
    raw = export.export_csv(config)
    reader = csv.DictReader(io.StringIO(raw))
    rows = {r["job"]: r for r in reader}
    assert rows["sync"]["run_count"] == "1"
    assert rows["cleanup"]["run_count"] == "2"
    assert float(rows["cleanup"]["max_runtime"]) == 250.0


def test_history_rows_match_recorded_runs(config):
    _simulate_runs("sync", [10.0, 20.0, 30.0])
    rows = export.get_history_rows("sync")
    assert len(rows) == 3
    runtimes = sorted(r["runtime"] for r in rows)
    assert runtimes == [10.0, 20.0, 30.0]


def test_empty_jobs_export_gracefully(config):
    raw = export.export_json(config)
    data = json.loads(raw)
    for job_name in ("sync", "cleanup"):
        assert data["jobs"][job_name]["run_count"] == 0
        assert data["jobs"][job_name]["failure_rate"] == 0.0
