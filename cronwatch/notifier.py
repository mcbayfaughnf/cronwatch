"""Notifier module: rate-limits and deduplicates alerts before dispatching."""

import logging
import time
from typing import Dict, Tuple

from cronwatch.alerts import Alert, AlertType, send_alert

logger = logging.getLogger(__name__)

# Key: (job_name, alert_type), Value: timestamp of last notification
_last_notified: Dict[Tuple[str, AlertType], float] = {}


def _notification_key(alert: Alert) -> Tuple[str, AlertType]:
    return (alert.job_name, alert.alert_type)


def should_notify(alert: Alert, cooldown_seconds: int, now: float = None) -> bool:
    """Return True if enough time has passed since the last alert of this type."""
    if now is None:
        now = time.time()
    key = _notification_key(alert)
    last = _last_notified.get(key)
    if last is None:
        return True
    return (now - last) >= cooldown_seconds


def record_notified(alert: Alert, now: float = None) -> None:
    """Record that a notification was sent for this alert."""
    if now is None:
        now = time.time()
    _last_notified[_notification_key(alert)] = now


def reset() -> None:
    """Clear all notification history (useful for testing)."""
    _last_notified.clear()


def notify(alert: Alert, webhook_url: str, cooldown_seconds: int = 300) -> bool:
    """Send an alert if it is not within the cooldown window.

    Returns True if the alert was dispatched, False if suppressed.
    """
    now = time.time()
    if not should_notify(alert, cooldown_seconds, now=now):
        logger.debug(
            "Suppressing %s alert for '%s' (cooldown %ds)",
            alert.alert_type.value,
            alert.job_name,
            cooldown_seconds,
        )
        return False

    try:
        send_alert(alert, webhook_url)
        record_notified(alert, now=now)
        logger.info(
            "Dispatched %s alert for '%s'",
            alert.alert_type.value,
            alert.job_name,
        )
        return True
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "Failed to dispatch alert for '%s': %s",
            alert.job_name,
            exc,
        )
        return False
