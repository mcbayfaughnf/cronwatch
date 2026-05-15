"""Tests for cronwatch.circuit (circuit breaker)."""

import time
import pytest

import cronwatch.circuit as circuit
from cronwatch.circuit import (
    CLOSED, OPEN, HALF_OPEN,
    reset, get_state, is_open,
    record_success, record_failure,
    failure_count, circuit_summary,
)

URL = "https://hooks.example.com/alert"
THRESHOLD = 3


@pytest.fixture(autouse=True)
def clear_state():
    reset()
    yield
    reset()


def test_initial_state_is_closed():
    assert get_state(URL) == CLOSED


def test_is_open_false_initially():
    assert not is_open(URL)


def test_failure_count_zero_initially():
    assert failure_count(URL) == 0


def test_record_failure_increments_count():
    record_failure(URL, threshold=THRESHOLD)
    assert failure_count(URL) == 1


def test_circuit_opens_at_threshold():
    for _ in range(THRESHOLD):
        record_failure(URL, threshold=THRESHOLD)
    assert get_state(URL) == OPEN
    assert is_open(URL)


def test_circuit_does_not_open_below_threshold():
    for _ in range(THRESHOLD - 1):
        record_failure(URL, threshold=THRESHOLD)
    assert get_state(URL) == CLOSED
    assert not is_open(URL)


def test_record_success_closes_circuit():
    for _ in range(THRESHOLD):
        record_failure(URL, threshold=THRESHOLD)
    assert is_open(URL)
    record_success(URL)
    assert get_state(URL) == CLOSED
    assert failure_count(URL) == 0


def test_half_open_after_cooldown(monkeypatch):
    for _ in range(THRESHOLD):
        record_failure(URL, threshold=THRESHOLD)
    assert get_state(URL) == OPEN

    # Advance monotonic clock past the cooldown
    original = time.monotonic
    monkeypatch.setattr(
        circuit.time, "monotonic",
        lambda: original() + circuit._DEFAULT_COOLDOWN + 1,
    )
    assert get_state(URL) == HALF_OPEN
    assert not is_open(URL)


def test_success_after_half_open_closes_circuit(monkeypatch):
    for _ in range(THRESHOLD):
        record_failure(URL, threshold=THRESHOLD)
    original = time.monotonic
    monkeypatch.setattr(
        circuit.time, "monotonic",
        lambda: original() + circuit._DEFAULT_COOLDOWN + 1,
    )
    assert get_state(URL) == HALF_OPEN
    record_success(URL)
    assert get_state(URL) == CLOSED


def test_multiple_urls_are_independent():
    url2 = "https://other.example.com/hook"
    for _ in range(THRESHOLD):
        record_failure(URL, threshold=THRESHOLD)
    assert is_open(URL)
    assert not is_open(url2)


def test_reset_single_url():
    for _ in range(THRESHOLD):
        record_failure(URL, threshold=THRESHOLD)
    reset(URL)
    assert get_state(URL) == CLOSED
    assert failure_count(URL) == 0


def test_circuit_summary_keys():
    summary = circuit_summary(URL)
    assert "url" in summary
    assert "state" in summary
    assert "failures" in summary


def test_circuit_summary_reflects_state():
    record_failure(URL, threshold=THRESHOLD)
    summary = circuit_summary(URL)
    assert summary["state"] == CLOSED
    assert summary["failures"] == 1
