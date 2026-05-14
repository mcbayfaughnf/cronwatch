"""Tests for cronwatch.export."""

import json
import csv
import io
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
        JobConfig(name="backup", schedule="0 2 * * *", max_duration=3600, missed_after=7200),
        JobConfig(name="report", schedule="0 8 * * 1", max_duration=600, missed_after=1200),
    ]
    return CronwatchConfig(jobs=jobs, webhook_url="http://example.com/hook", check_interval=60)


def test_build_metrics_export_keys(config):
    result = export.build_metrics_export(config)
    assert "generated_at" in result
    assert "jobs" in result
    assert set(result["jobs"].keys()) == {"backup", "report"}


def test_build_metrics_export_job_fields(config):
    fields = export.build_metrics_export(config)["jobs"]["backup"]
    assert "average_runtime" in fields
    assert "max_runtime" in fields
    assert "alert_count" in fields
    assert "run_count" in fields
    assert "failure_rate" in fields


def test_build_metrics_export_with_data(config):
    metrics.record_runtime("backup", 120.0)
    metrics.record_runtime("backup", 180.0)
    metrics.record_alert("backup")
    history.record_run("backup", started_at=1000.0, finished_at=1120.0, runtime=120.0)
    history.record_run("backup", started_at=2000.0, finished_at=2180.0, runtime=180.0)

    result = export.build_metrics_export(config)["jobs"]["backup"]
    assert result["average_runtime"] == 150.0
    assert result["max_runtime"] == 180.0
    assert result["alert_count"] == 1
    assert result["run_count"] == 2
    assert result["failure_rate"] == 0.5


def test_export_json_is_valid_json(config):
    raw = export.export_json(config)
    parsed = json.loads(raw)
    assert "jobs" in parsed


def test_export_csv_has_header_and_rows(config):
    metrics.record_runtime("backup", 90.0)
    raw = export.export_csv(config)
    reader = csv.DictReader(io.StringIO(raw))
    rows = list(reader)
    assert len(rows) == 2
    job_names = {r["job"] for r in rows}
    assert job_names == {"backup", "report"}


def test_failure_rate_zero_when_no_runs(config):
    result = export.build_metrics_export(config)["jobs"]["backup"]
    assert result["failure_rate"] == 0.0


def test_get_history_rows(config):
    history.record_run("backup", started_at=500.0, finished_at=560.0, runtime=60.0)
    rows = export.get_history_rows("backup")
    assert len(rows) == 1
    assert rows[0]["job"] == "backup"
    assert rows[0]["runtime"] == 60.0
