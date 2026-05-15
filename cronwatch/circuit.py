"""Circuit breaker for webhook alert delivery.

Prevents repeated failed alert attempts from hammering an unavailable
webhook endpoint. After a configurable number of consecutive failures
the circuit opens and calls are blocked until a cooldown has elapsed.
"""

import time
from typing import Dict

# States
CLOSED = "closed"      # normal operation
OPEN = "open"          # failures exceeded threshold; calls blocked
HALF_OPEN = "half_open"  # cooldown elapsed; next call is a probe

_DEFAULT_THRESHOLD = 3       # consecutive failures before opening
_DEFAULT_COOLDOWN = 60.0     # seconds to wait before probing

# Per-webhook state
_state: Dict[str, str] = {}
_failures: Dict[str, int] = {}
_opened_at: Dict[str, float] = {}


def reset(webhook_url: str = "") -> None:
    """Reset circuit state.  Pass empty string to reset all."""
    if webhook_url:
        _state.pop(webhook_url, None)
        _failures.pop(webhook_url, None)
        _opened_at.pop(webhook_url, None)
    else:
        _state.clear()
        _failures.clear()
        _opened_at.clear()


def get_state(webhook_url: str) -> str:
    """Return the current circuit state for *webhook_url*."""
    state = _state.get(webhook_url, CLOSED)
    if state == OPEN:
        opened = _opened_at.get(webhook_url, 0.0)
        if time.monotonic() - opened >= _DEFAULT_COOLDOWN:
            _state[webhook_url] = HALF_OPEN
            return HALF_OPEN
    return state


def is_open(webhook_url: str) -> bool:
    """Return True when the circuit is OPEN (calls should be blocked)."""
    return get_state(webhook_url) == OPEN


def record_success(webhook_url: str) -> None:
    """Record a successful delivery; close the circuit."""
    _failures[webhook_url] = 0
    _state[webhook_url] = CLOSED
    _opened_at.pop(webhook_url, None)


def record_failure(
    webhook_url: str,
    threshold: int = _DEFAULT_THRESHOLD,
) -> None:
    """Record a failed delivery; open the circuit when threshold is reached."""
    count = _failures.get(webhook_url, 0) + 1
    _failures[webhook_url] = count
    if count >= threshold:
        _state[webhook_url] = OPEN
        _opened_at[webhook_url] = time.monotonic()


def failure_count(webhook_url: str) -> int:
    """Return the current consecutive failure count."""
    return _failures.get(webhook_url, 0)


def circuit_summary(webhook_url: str) -> Dict[str, object]:
    """Return a dict summarising the circuit state for *webhook_url*."""
    return {
        "url": webhook_url,
        "state": get_state(webhook_url),
        "failures": failure_count(webhook_url),
    }
