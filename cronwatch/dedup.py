"""Alert deduplication: suppress identical alerts within a configurable window."""

import time
from typing import Optional
from cronwatch.alerts import Alert, AlertType

# {dedup_key: last_sent_timestamp}
_sent: dict[str, float] = {}

_DEFAULT_WINDOW_SECONDS = 300  # 5 minutes


def _key(alert: Alert) -> str:
    """Return a string key that uniquely identifies an alert by job and type."""
    return f"{alert.job_name}:{alert.alert_type.value}"


def is_duplicate(alert: Alert, window_seconds: float = _DEFAULT_WINDOW_SECONDS) -> bool:
    """Return True if an identical alert was already sent within *window_seconds*."""
    k = _key(alert)
    last = _sent.get(k)
    if last is None:
        return False
    return (time.time() - last) < window_seconds


def record_sent(alert: Alert) -> None:
    """Record that *alert* has just been sent."""
    _sent[_key(alert)] = time.time()


def time_since_last(alert: Alert) -> Optional[float]:
    """Return seconds since the same alert was last sent, or None if never sent."""
    last = _sent.get(_key(alert))
    if last is None:
        return None
    return time.time() - last


def reset() -> None:
    """Clear all deduplication state (useful for testing)."""
    _sent.clear()


def dedup_summary(alert: Alert, window_seconds: float = _DEFAULT_WINDOW_SECONDS) -> dict:
    """Return a human-readable summary dict for *alert*'s dedup state."""
    elapsed = time_since_last(alert)
    return {
        "job": alert.job_name,
        "alert_type": alert.alert_type.value,
        "is_duplicate": is_duplicate(alert, window_seconds),
        "seconds_since_last": round(elapsed, 2) if elapsed is not None else None,
        "window_seconds": window_seconds,
    }
