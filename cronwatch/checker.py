"""Checks job states against configured thresholds and fires alerts."""

import logging
from typing import List

from cronwatch.alerts import Alert, AlertType, send_alert
from cronwatch.config import CronwatchConfig
from cronwatch.tracker import (
    JobTracker,
    is_running,
    runtime_seconds,
    seconds_since_last_seen,
)

logger = logging.getLogger(__name__)


def check_jobs(config: CronwatchConfig, tracker: JobTracker) -> List[Alert]:
    """Inspect all configured jobs and return a list of triggered alerts."""
    fired: List[Alert] = []

    for job in config.jobs:
        if is_running(tracker, job.name):
            rt = runtime_seconds(tracker, job.name)
            if job.max_runtime is not None and rt is not None and rt > job.max_runtime:
                alert = Alert(
                    job_name=job.name,
                    alert_type=AlertType.LONG_RUNNING,
                    message=(
                        f"Job '{job.name}' has been running for {rt:.1f}s, "
                        f"exceeding max_runtime of {job.max_runtime}s."
                    ),
                    runtime_seconds=rt,
                    threshold_seconds=float(job.max_runtime),
                )
                fired.append(alert)
                logger.warning(alert.message)
        else:
            last_seen = seconds_since_last_seen(tracker, job.name)
            if job.expected_interval is not None and last_seen is not None:
                if last_seen > job.expected_interval:
                    alert = Alert(
                        job_name=job.name,
                        alert_type=AlertType.MISSED,
                        message=(
                            f"Job '{job.name}' last seen {last_seen:.1f}s ago, "
                            f"expected every {job.expected_interval}s."
                        ),
                        runtime_seconds=None,
                        threshold_seconds=float(job.expected_interval),
                    )
                    fired.append(alert)
                    logger.warning(alert.message)

    return fired


def dispatch_alerts(config: CronwatchConfig, alerts: List[Alert]) -> None:
    """Send each alert to the configured webhook."""
    if not alerts or not config.webhook_url:
        return
    for alert in alerts:
        send_alert(config.webhook_url, alert)
