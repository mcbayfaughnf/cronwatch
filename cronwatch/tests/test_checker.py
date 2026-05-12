"""Tests for cronwatch.checker module."""

import time
from unittest.mock import patch

import pytest

from cronwatch.alerts import AlertType
from cronwatch.checker import check_jobs, dispatch_alerts
from cronwatch.config import CronwatchConfig, JobConfig
from cronwatch.tracker import JobTracker, mark_finished, mark_started


@pytest.fixture
def config():
    return CronwatchConfig(
        webhook_url="http://hooks.example.com/notify",
        check_interval=60,
        jobs=[
            JobConfig(name="backup", expected_interval=3600, max_runtime=300),
            JobConfig(name="report", expected_interval=None, max_runtime=60),
        ],
    )


@pytest.fixture
def tracker(config):
    return JobTracker(job_names=[j.name for j in config.jobs])


def test_no_alerts_when_jobs_on_time(config, tracker):
    now = time.time()
    mark_started(tracker, "backup", at=now - 10)
    mark_finished(tracker, "backup", at=now - 5)
    alerts = check_jobs(config, tracker)
    assert all(a.job_name != "backup" for a in alerts)


def test_missed_job_triggers_alert(config, tracker):
    past = time.time() - 7200  # 2 hours ago
    mark_started(tracker, "backup", at=past)
    mark_finished(tracker, "backup", at=past + 10)
    alerts = check_jobs(config, tracker)
    missed = [a for a in alerts if a.job_name == "backup" and a.alert_type == AlertType.MISSED]
    assert len(missed) == 1
    assert missed[0].threshold_seconds == 3600.0


def test_long_running_job_triggers_alert(config, tracker):
    mark_started(tracker, "report", at=time.time() - 120)
    alerts = check_jobs(config, tracker)
    long = [a for a in alerts if a.job_name == "report" and a.alert_type == AlertType.LONG_RUNNING]
    assert len(long) == 1
    assert long[0].runtime_seconds > 60


def test_dispatch_alerts_calls_send_alert(config, tracker):
    from cronwatch.alerts import Alert
    alerts = [Alert(job_name="backup", alert_type=AlertType.MISSED, message="missed")]
    with patch("cronwatch.checker.send_alert", return_value=True) as mock_send:
        dispatch_alerts(config, alerts)
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert call_args[0][0] == config.webhook_url


def test_dispatch_alerts_skips_when_no_webhook(config, tracker):
    config.webhook_url = None
    from cronwatch.alerts import Alert
    alerts = [Alert(job_name="backup", alert_type=AlertType.MISSED, message="missed")]
    with patch("cronwatch.checker.send_alert") as mock_send:
        dispatch_alerts(config, alerts)
    mock_send.assert_not_called()
