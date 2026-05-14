"""Periodic digest: aggregates recent alerts and sends a summary webhook."""

import json
import logging
import time
from typing import List, Optional

from cronwatch.alerts import Alert, AlertType

logger = logging.getLogger(__name__)

_pending: List[Alert] = []
_last_flush_time: Optional[float] = None


def _reset_last_flush_time() -> None:
    """Reset flush timestamp (used in tests)."""
    global _last_flush_time
    _last_flush_time = None


def reset() -> None:
    """Clear all pending alerts and reset flush time."""
    global _pending
    _pending = []
    _reset_last_flush_time()


def add_alert(alert: Alert) -> None:
    """Stage an alert to be included in the next digest."""
    _pending.append(alert)


def is_flush_due(interval_seconds: int) -> bool:
    """Return True if enough time has passed since the last digest flush."""
    global _last_flush_time
    if _last_flush_time is None:
        return True
    return (time.time() - _last_flush_time) >= interval_seconds


def build_digest_payload() -> dict:
    """Build a webhook payload summarising all pending alerts."""
    missed = [a for a in _pending if a.alert_type == AlertType.MISSED]
    long_running = [a for a in _pending if a.alert_type == AlertType.LONG_RUNNING]
    return {
        "type": "digest",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_alerts": len(_pending),
        "missed_jobs": [a.job_name for a in missed],
        "long_running_jobs": [a.job_name for a in long_running],
        "missed_count": len(missed),
        "long_running_count": len(long_running),
    }


def flush_digest(webhook_url: str, interval_seconds: int) -> bool:
    """Send digest if due and there are pending alerts. Returns True if sent."""
    global _last_flush_time

    if not is_flush_due(interval_seconds):
        return False

    _last_flush_time = time.time()

    if not _pending:
        logger.debug("Digest flush due but no pending alerts; skipping send.")
        return False

    payload = build_digest_payload()
    try:
        import urllib.request
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Digest sent: %d alerts, status %s", len(_pending), resp.status)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to send digest: %s", exc)
    finally:
        _pending.clear()

    return True
