"""Alert construction and delivery for cronwatch."""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from urllib import request, error

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    MISSED = "missed"
    LONG_RUNNING = "long_running"
    REPORT = "report"


@dataclass
class Alert:
    alert_type: AlertType
    job_name: str
    message: str
    payload: Dict[str, Any] = field(default_factory=dict)


def build_payload(alert: Alert) -> Dict[str, Any]:
    """Construct the JSON payload for a webhook delivery."""
    base = {
        "alert_type": alert.alert_type.value,
        "job_name": alert.job_name,
        "message": alert.message,
    }
    base.update(alert.payload)
    return base


def send_alert(webhook_url: str, alert: Alert, timeout: int = 10) -> None:
    """Send an alert payload to the configured webhook URL."""
    payload = build_payload(alert)
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            logger.debug("Alert sent to %s — HTTP %s", webhook_url, status)
    except error.HTTPError as exc:
        logger.error("HTTP error sending alert: %s %s", exc.code, exc.reason)
        raise
    except error.URLError as exc:
        logger.error("URL error sending alert: %s", exc.reason)
        raise
