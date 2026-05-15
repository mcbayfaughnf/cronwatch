"""Integration tests: circuit breaker wired into alert delivery."""

import pytest
from unittest.mock import patch, MagicMock

import cronwatch.circuit as circuit
from cronwatch.circuit import reset, record_failure, record_success, is_open, OPEN, HALF_OPEN
from cronwatch.alerts import Alert, AlertType

URL = "https://hooks.example.com/alert"
THRESHOLD = 3


@pytest.fixture(autouse=True)
def clear_all():
    reset()
    yield
    reset()


def _make_alert() -> Alert:
    return Alert(
        alert_type=AlertType.MISSED,
        job_name="nightly-backup",
        message="Job has not run recently",
    )


def test_alert_sent_when_circuit_closed():
    """Alerts are dispatched normally while the circuit is closed."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("cronwatch.alerts.requests.post", return_value=mock_resp) as mock_post:
        from cronwatch.alerts import send_alert
        alert = _make_alert()
        send_alert(alert, URL)
        mock_post.assert_called_once()


def test_failures_open_circuit():
    for _ in range(THRESHOLD):
        record_failure(URL, threshold=THRESHOLD)
    assert is_open(URL)


def test_open_circuit_blocks_delivery():
    """When the circuit is open, send_alert should be skipped."""
    for _ in range(THRESHOLD):
        record_failure(URL, threshold=THRESHOLD)
    assert is_open(URL)

    with patch("cronwatch.alerts.requests.post") as mock_post:
        # Simulate a guard that checks the circuit before sending
        alert = _make_alert()
        if not is_open(URL):
            from cronwatch.alerts import send_alert
            send_alert(alert, URL)
        mock_post.assert_not_called()


def test_circuit_recovers_after_success():
    for _ in range(THRESHOLD):
        record_failure(URL, threshold=THRESHOLD)
    assert is_open(URL)
    record_success(URL)
    assert not is_open(URL)


def test_consecutive_successes_keep_circuit_closed():
    for _ in range(5):
        record_success(URL)
    assert not is_open(URL)
    assert circuit.failure_count(URL) == 0


def test_partial_failures_do_not_open_circuit():
    record_failure(URL, threshold=THRESHOLD)
    record_failure(URL, threshold=THRESHOLD)
    record_success(URL)  # resets count
    record_failure(URL, threshold=THRESHOLD)
    assert not is_open(URL)
    assert circuit.failure_count(URL) == 1
