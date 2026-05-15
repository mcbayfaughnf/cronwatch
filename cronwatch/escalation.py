"""Alert escalation: track repeated alerts and escalate after a threshold."""

import time
from typing import Dict, Optional, Tuple

from cronwatch.alerts import Alert, AlertType

# { (job_name, alert_type) -> (count, first_seen_ts, last_notified_ts) }
_state: Dict[Tuple[str, str], Tuple[int, float, float]] = {}

DEFAULT_THRESHOLD = 3
DEFAULT_ESCALATION_COOLDOWN = 1800  # 30 minutes between escalation notices


def reset() -> None:
    """Clear all escalation state (useful in tests)."""
    _state.clear()


def _key(alert: Alert) -> Tuple[str, str]:
    return (alert.job_name, alert.alert_type.value)


def record_occurrence(alert: Alert) -> int:
    """Record an alert occurrence and return the current repeat count."""
    k = _key(alert)
    now = time.time()
    if k in _state:
        count, first_seen, last_notified = _state[k]
        _state[k] = (count + 1, first_seen, last_notified)
    else:
        _state[k] = (1, now, 0.0)
    return _state[k][0]


def should_escalate(
    alert: Alert,
    threshold: int = DEFAULT_THRESHOLD,
    cooldown: float = DEFAULT_ESCALATION_COOLDOWN,
) -> bool:
    """Return True if this alert has crossed the threshold and cooldown has elapsed."""
    k = _key(alert)
    if k not in _state:
        return False
    count, _first_seen, last_notified = _state[k]
    if count < threshold:
        return False
    return (time.time() - last_notified) >= cooldown


def record_escalated(alert: Alert) -> None:
    """Mark that an escalation notice was sent now."""
    k = _key(alert)
    if k in _state:
        count, first_seen, _ = _state[k]
        _state[k] = (count, first_seen, time.time())


def escalation_summary(alert: Alert) -> Optional[str]:
    """Return a human-readable escalation summary or None if no state exists."""
    k = _key(alert)
    if k not in _state:
        return None
    count, first_seen, last_notified = _state[k]
    age_minutes = (time.time() - first_seen) / 60
    last = f"{(time.time() - last_notified):.0f}s ago" if last_notified else "never"
    return (
        f"{alert.job_name} [{alert.alert_type.value}]: "
        f"repeated {count}x over {age_minutes:.1f}m, last escalated {last}"
    )
