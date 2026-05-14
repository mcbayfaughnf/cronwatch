"""Tests for cronwatch.digest."""

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerts import Alert, AlertType
from cronwatch.digest import (
    add_alert,
    build_digest_payload,
    flush_digest,
    is_flush_due,
    reset,
)


@pytest.fixture(autouse=True)
def clear_state():
    reset()
    yield
    reset()


def _missed(name="job_a") -> Alert:
    return Alert(job_name=name, alert_type=AlertType.MISSED, message="missed")


def _long(name="job_b") -> Alert:
    return Alert(job_name=name, alert_type=AlertType.LONG_RUNNING, message="long")


def test_is_flush_due_first_time():
    assert is_flush_due(300) is True


def test_is_flush_due_after_flush_not_immediately():
    import cronwatch.digest as d
    d._last_flush_time = time.time()
    assert is_flush_due(300) is False


def test_is_flush_due_after_interval_elapsed():
    import cronwatch.digest as d
    d._last_flush_time = time.time() - 400
    assert is_flush_due(300) is True


def test_build_digest_payload_keys():
    add_alert(_missed())
    payload = build_digest_payload()
    assert "type" in payload
    assert "generated_at" in payload
    assert "total_alerts" in payload
    assert "missed_jobs" in payload
    assert "long_running_jobs" in payload
    assert "missed_count" in payload
    assert "long_running_count" in payload


def test_build_digest_payload_counts():
    add_alert(_missed("a"))
    add_alert(_missed("b"))
    add_alert(_long("c"))
    payload = build_digest_payload()
    assert payload["total_alerts"] == 3
    assert payload["missed_count"] == 2
    assert payload["long_running_count"] == 1
    assert set(payload["missed_jobs"]) == {"a", "b"}
    assert payload["long_running_jobs"] == ["c"]


def test_build_digest_payload_type():
    payload = build_digest_payload()
    assert payload["type"] == "digest"


def test_flush_digest_not_due_returns_false():
    import cronwatch.digest as d
    d._last_flush_time = time.time()
    add_alert(_missed())
    result = flush_digest("http://example.com/hook", 300)
    assert result is False


def test_flush_digest_no_pending_returns_false():
    result = flush_digest("http://example.com/hook", 300)
    assert result is False


def test_flush_digest_sends_and_clears():
    import cronwatch.digest as d
    add_alert(_missed())
    add_alert(_long())

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: mock_resp
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = flush_digest("http://example.com/hook", 300)

    assert result is True
    assert d._pending == []


def test_flush_digest_clears_pending_on_error():
    import cronwatch.digest as d
    add_alert(_missed())

    with patch("urllib.request.urlopen", side_effect=OSError("network error")):
        result = flush_digest("http://example.com/hook", 300)

    assert result is True  # attempted
    assert d._pending == []
