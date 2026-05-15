"""
Per-job alert rate limiting with configurable windows.

Prevents alert storms by enforcing a minimum interval between
repeated alerts of the same type for the same job.
"""

import time
from typing import Dict, Optional, Tuple

# State: (alert_type, job_name) -> last_sent_timestamp
_sent_at: Dict[Tuple[str, str], float] = {}

# Default minimum seconds between repeated alerts of the same kind
DEFAULT_WINDOW_SECONDS = 300  # 5 minutes


def _key(alert_type: str, job_name: str) -> Tuple[str, str]:
    return (alert_type, job_name)


def is_rate_limited(
    alert_type: str,
    job_name: str,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> bool:
    """Return True if an alert of this type for this job was sent within the window."""
    k = _key(alert_type, job_name)
    last = _sent_at.get(k)
    if last is None:
        return False
    return (time.time() - last) < window_seconds


def record_sent(alert_type: str, job_name: str) -> None:
    """Record that an alert of this type for this job was sent right now."""
    _sent_at[_key(alert_type, job_name)] = time.time()


def time_until_allowed(
    alert_type: str,
    job_name: str,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> Optional[float]:
    """Return seconds remaining in the rate-limit window, or None if not limited."""
    k = _key(alert_type, job_name)
    last = _sent_at.get(k)
    if last is None:
        return None
    remaining = window_seconds - (time.time() - last)
    return remaining if remaining > 0 else None


def reset(alert_type: Optional[str] = None, job_name: Optional[str] = None) -> None:
    """Clear rate-limit state. Optionally filter by type and/or job name."""
    global _sent_at
    if alert_type is None and job_name is None:
        _sent_at.clear()
        return
    keys_to_remove = [
        k for k in _sent_at
        if (alert_type is None or k[0] == alert_type)
        and (job_name is None or k[1] == job_name)
    ]
    for k in keys_to_remove:
        del _sent_at[k]
