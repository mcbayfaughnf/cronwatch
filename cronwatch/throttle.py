"""
cronwatch.throttle
~~~~~~~~~~~~~~~~~~
Rate-limits outgoing webhook calls so a single misbehaving job cannot
flood the configured endpoint.

Each (job_name, alert_type) pair is tracked independently.  A call is
allowed through only when the elapsed time since the last successful
send exceeds *min_interval_seconds* (default: 300 s / 5 min).

The in-process state is intentionally kept as a plain dict so it is
easy to reset in tests without monkey-patching.
"""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

from cronwatch.alerts import Alert

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

# Maps (job_name, alert_type_value) -> epoch timestamp of last allowed send
_last_sent: Dict[Tuple[str, str], float] = {}

DEFAULT_MIN_INTERVAL: int = 300  # seconds


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _key(alert: Alert) -> Tuple[str, str]:
    """Return the throttle-map key for *alert*."""
    return (alert.job_name, alert.alert_type.value)


def is_throttled(
    alert: Alert,
    min_interval: int = DEFAULT_MIN_INTERVAL,
    *,
    _now: Optional[float] = None,
) -> bool:
    """Return *True* when *alert* should be suppressed due to rate-limiting."""
    now = _now if _now is not None else time.time()
    last = _last_sent.get(_key(alert))
    if last is None:
        return False
    return (now - last) < min_interval


def record_sent(
    alert: Alert,
    *,
    _now: Optional[float] = None,
) -> None:
    """Record that *alert* was successfully dispatched right now."""
    now = _now if _now is not None else time.time()
    _last_sent[_key(alert)] = now


def reset() -> None:
    """Clear all throttle state (useful in tests)."""
    _last_sent.clear()
