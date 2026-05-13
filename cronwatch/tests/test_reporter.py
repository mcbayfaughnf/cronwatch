"""Tests for cronwatch.reporter."""

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerts import AlertType
from cronwatch.reporter import (
    _reset_last_report_time,
    build_report_payload,
    is_report_due,
    maybe_send_report,
    send_report,
)


@pytest.fixture(autouse=True)
def reset_state():
    _reset_last_report_time()
    yield
    _reset_last_report_time()


@pytest.fixture
def config():
    cfg = MagicMock()
    cfg.webhook_url = "https://hooks.example.com/test"
    cfg.report_interval = 3600
    cfg.jobs = {}
    return cfg


@pytest.fixture
def tracker():
    return MagicMock()


def test_is_report_due_first_time():
    assert is_report_due(3600) is True


def test_is_report_due_after_record(config, tracker):
    with patch("cronwatch.reporter.send_alert"):
        with patch("cronwatch.reporter.build_summary", return_value={"total_jobs": 0, "jobs": {}}):
            send_report(config, tracker)
    # Immediately after sending, should not be due again
    assert is_report_due(3600) is False


def test_is_report_due_after_interval_elapsed(monkeypatch):
    import cronwatch.reporter as rep
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    rep._last_report_time = past
    assert is_report_due(1) is True


def test_build_report_payload_keys(config, tracker):
    with patch("cronwatch.reporter.build_summary", return_value={"total_jobs": 2, "jobs": {}}):
        payload = build_report_payload(config, tracker)
    assert "type" in payload
    assert payload["type"] == "periodic_report"
    assert "generated_at" in payload
    assert "summary" in payload
    assert "report_interval_seconds" in payload
    assert payload["report_interval_seconds"] == 3600


def test_send_report_calls_send_alert(config, tracker):
    with patch("cronwatch.reporter.build_summary", return_value={"total_jobs": 1, "jobs": {}}):
        with patch("cronwatch.reporter.send_alert") as mock_send:
            send_report(config, tracker)
    assert mock_send.called
    alert_arg = mock_send.call_args[0][1]
    assert alert_arg.alert_type == AlertType.REPORT


def test_send_report_no_webhook_skips(config, tracker):
    config.webhook_url = None
    with patch("cronwatch.reporter.send_alert") as mock_send:
        send_report(config, tracker)
    mock_send.assert_not_called()


def test_maybe_send_report_no_interval_skips(config, tracker):
    config.report_interval = None
    with patch("cronwatch.reporter.send_report") as mock_report:
        maybe_send_report(config, tracker)
    mock_report.assert_not_called()


def test_maybe_send_report_calls_when_due(config, tracker):
    with patch("cronwatch.reporter.send_report") as mock_report:
        maybe_send_report(config, tracker)
    mock_report.assert_called_once_with(config, tracker)
