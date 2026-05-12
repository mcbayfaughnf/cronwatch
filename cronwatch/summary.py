"""Generates periodic summary reports of cron job health."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from cronwatch.tracker import Tracker
from cronwatch.config import CronwatchConfig

logger = logging.getLogger(__name__)


def _format_timestamp(ts: Optional[float]) -> Optional[str]:
    """Format a UNIX timestamp as an ISO 8601 string, or None."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def build_summary(config: CronwatchConfig, tracker: Tracker) -> Dict[str, Any]:
    """Build a summary dict describing the current state of all tracked jobs."""
    jobs = []
    now = datetime.now(tz=timezone.utc).timestamp()

    for job in config.jobs:
        name = job.name
        is_running = tracker.is_running(name)
        last_started = tracker.last_started(name)
        last_finished = tracker.last_finished(name)

        elapsed: Optional[float] = None
        if is_running and last_started is not None:
            elapsed = round(now - last_started, 1)

        overdue = False
        if not is_running and last_finished is not None:
            seconds_since = now - last_finished
            if seconds_since > job.interval_seconds * 1.5:
                overdue = True
        elif not is_running and last_finished is None:
            overdue = True

        jobs.append({
            "name": name,
            "running": is_running,
            "overdue": overdue,
            "last_started": _format_timestamp(last_started),
            "last_finished": _format_timestamp(last_finished),
            "elapsed_seconds": elapsed,
        })

    total = len(jobs)
    running_count = sum(1 for j in jobs if j["running"])
    overdue_count = sum(1 for j in jobs if j["overdue"])

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "total_jobs": total,
        "running": running_count,
        "overdue": overdue_count,
        "jobs": jobs,
    }


def log_summary(config: CronwatchConfig, tracker: Tracker) -> None:
    """Log a human-readable summary of all job states."""
    summary = build_summary(config, tracker)
    logger.info(
        "Summary: %d jobs | %d running | %d overdue",
        summary["total_jobs"],
        summary["running"],
        summary["overdue"],
    )
    for job in summary["jobs"]:
        status = "RUNNING" if job["running"] else ("OVERDUE" if job["overdue"] else "OK")
        logger.info(
            "  [%s] %s | last_finished=%s",
            status,
            job["name"],
            job["last_finished"] or "never",
        )
