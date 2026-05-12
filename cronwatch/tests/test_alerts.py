"""Tests for cronwatch.alerts module."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerts import Alert, AlertType, build_payload, send_alert


@pytest.fixture
def missed_alert():
    return Alert(
        job_name="backup",
        alert_type=AlertType.MISSED,
        message="Job 'backup' missed.",
        threshold_seconds=3600.0,
    )


@pytest.fixture
def long_running_alert():
    return Alert(
        job_name="report",
        alert_type=AlertType.LONG_RUNNING,
        message="Job 'report' is too slow.",
        runtime_seconds=120.5,
        threshold_seconds=60.0,
    )


def test_build_payload_missed(missed_alert):
    payload = build_payload(missed_alert)
    assert payload["job"] == "backup"
    assert payload["alert_type"] == "missed"
    assert payload["threshold_seconds"] == 3600.0
    assert "runtime_seconds" not in payload


def test_build_payload_long_running(long_running_alert):
    payload = build_payload(long_running_alert)
    assert payload["alert_type"] == "long_running"
    assert payload["runtime_seconds"] == 120.5
    assert payload["threshold_seconds"] == 60.0


def _make_mock_response(status=200):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_send_alert_success(missed_alert):
    mock_resp = _make_mock_response(200)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = send_alert("http://example.com/hook", missed_alert)
    assert result is True


def test_send_alert_non_2xx_returns_false(missed_alert):
    mock_resp = _make_mock_response(500)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = send_alert("http://example.com/hook", missed_alert)
    assert result is False


def test_send_alert_network_error_returns_false(missed_alert):
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        result = send_alert("http://example.com/hook", missed_alert)
    assert result is False
