"""Parse cron job execution signals from log lines or stdin input."""

import re
import logging
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Expected log line format:
# [CRONWATCH] START job_name 2024-01-15T10:30:00
# [CRONWATCH] FINISH job_name 2024-01-15T10:30:45
LOG_PATTERN = re.compile(
    r"\[CRONWATCH\]\s+(START|FINISH)\s+(\S+)\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
)

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


def parse_line(line: str) -> Optional[Tuple[str, str, datetime]]:
    """Parse a single log line.

    Returns a tuple of (action, job_name, timestamp) or None if the line
    does not match the expected format.

    Args:
        line: Raw log line string.

    Returns:
        Tuple of (action, job_name, timestamp) or None.
    """
    match = LOG_PATTERN.search(line.strip())
    if not match:
        return None

    action, job_name, ts_str = match.groups()
    try:
        timestamp = datetime.strptime(ts_str, DATETIME_FORMAT)
    except ValueError:
        logger.warning("Could not parse timestamp %r in line: %s", ts_str, line)
        return None

    return action, job_name, timestamp


def process_line(line: str, tracker) -> bool:
    """Parse a log line and update the tracker accordingly.

    Args:
        line: Raw log line string.
        tracker: A Tracker instance (from cronwatch.tracker).

    Returns:
        True if the line was recognised and processed, False otherwise.
    """
    result = parse_line(line)
    if result is None:
        return False

    action, job_name, timestamp = result

    if action == "START":
        if job_name in tracker.job_configs:
            tracker.mark_started(job_name, timestamp)
            logger.debug("Marked %s as started at %s", job_name, timestamp)
        else:
            logger.warning("Received START for unknown job %r", job_name)
    elif action == "FINISH":
        if job_name in tracker.job_configs:
            tracker.mark_finished(job_name, timestamp)
            logger.debug("Marked %s as finished at %s", job_name, timestamp)
        else:
            logger.warning("Received FINISH for unknown job %r", job_name)

    return True
