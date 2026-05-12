"""Alert sending via webhook for missed or long-running cron jobs."""

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    MISSED = "missed"
    LONG_RUNNING = "long_running"
    RECOVERED = "recovered"


@dataclass
class Alert:
    job_name: str
    alert_type: AlertType
    message: str
    runtime_seconds: Optional[float] = None
    threshold_seconds: Optional[float] = None


def build_payload(alert: Alert) -> dict:
    """Build the JSON payload for a webhook POST request."""
    payload = {
        "job": alert.job_name,
        "alert_type": alert.alert_type.value,
        "message": alert.message,
    }
    if alert.runtime_seconds is not None:
        payload["runtime_seconds"] = alert.runtime_seconds
    if alert.threshold_seconds is not None:
        payload["threshold_seconds"] = alert.threshold_seconds
    return payload


def send_alert(webhook_url: str, alert: Alert, timeout: int = 10) -> bool:
    """Send an alert to the configured webhook URL.

    Returns True if the alert was delivered successfully, False otherwise.
    """
    payload = build_payload(alert)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            if status < 300:
                logger.info("Alert sent for job '%s' (%s)", alert.job_name, alert.alert_type.value)
                return True
            logger.warning(
                "Webhook returned unexpected status %d for job '%s'", status, alert.job_name
            )
            return False
    except urllib.error.URLError as exc:
        logger.error("Failed to send alert for job '%s': %s", alert.job_name, exc)
        return False
