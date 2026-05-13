"""Periodic report generation and delivery for cronwatch."""

import logging
from datetime import datetime, timezone
from typing import Optional

from cronwatch.config import CronwatchConfig
from cronwatch.summary import build_summary
from cronwatch.tracker import Tracker
from cronwatch.alerts import send_alert, Alert, AlertType

logger = logging.getLogger(__name__)

_last_report_time: Optional[datetime] = None


def _reset_last_report_time() -> None:
    """Reset the last report time (used in tests)."""
    global _last_report_time
    _last_report_time = None


def is_report_due(interval_seconds: int) -> bool:
    """Return True if enough time has passed since the last report."""
    global _last_report_time
    if _last_report_time is None:
        return True
    now = datetime.now(tz=timezone.utc)
    elapsed = (now - _last_report_time).total_seconds()
    return elapsed >= interval_seconds


def build_report_payload(config: CronwatchConfig, tracker: Tracker) -> dict:
    """Build a structured report payload from the current tracker state."""
    summary = build_summary(config, tracker)
    return {
        "type": "periodic_report",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "report_interval_seconds": config.report_interval,
        "summary": summary,
    }


def send_report(config: CronwatchConfig, tracker: Tracker) -> None:
    """Build and send a periodic report via the configured webhook."""
    global _last_report_time
    if not config.webhook_url:
        logger.debug("No webhook_url configured; skipping report.")
        return
    payload = build_report_payload(config, tracker)
    alert = Alert(
        alert_type=AlertType.REPORT,
        job_name="__report__",
        message=f"Periodic report: {payload['summary']['total_jobs']} jobs tracked.",
        payload=payload,
    )
    try:
        send_alert(config.webhook_url, alert)
        _last_report_time = datetime.now(tz=timezone.utc)
        logger.info("Periodic report sent.")
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to send periodic report: %s", exc)


def maybe_send_report(config: CronwatchConfig, tracker: Tracker) -> None:
    """Send a report only if the configured interval has elapsed."""
    if not getattr(config, "report_interval", None):
        return
    if is_report_due(config.report_interval):
        send_report(config, tracker)
