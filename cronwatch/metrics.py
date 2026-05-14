"""Lightweight in-memory metrics collection for cronwatch."""

import time
from collections import defaultdict
from typing import Dict, List, Optional

# Stores per-job runtime samples (seconds)
_runtime_samples: Dict[str, List[float]] = defaultdict(list)

# Stores per-job alert counts keyed by alert type name
_alert_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

# Timestamp of when metrics collection started
_start_time: float = time.time()


def record_runtime(job_name: str, seconds: float) -> None:
    """Record a completed job's runtime in seconds."""
    _runtime_samples[job_name].append(seconds)


def record_alert(job_name: str, alert_type: str) -> None:
    """Increment the alert counter for a given job and alert type."""
    _alert_counts[job_name][alert_type] += 1


def average_runtime(job_name: str) -> Optional[float]:
    """Return the average runtime for a job, or None if no samples."""
    samples = _runtime_samples.get(job_name)
    if not samples:
        return None
    return sum(samples) / len(samples)


def max_runtime(job_name: str) -> Optional[float]:
    """Return the maximum recorded runtime for a job, or None if no samples."""
    samples = _runtime_samples.get(job_name)
    if not samples:
        return None
    return max(samples)


def alert_count(job_name: str, alert_type: str) -> int:
    """Return the total number of alerts of a given type for a job."""
    return _alert_counts.get(job_name, {}).get(alert_type, 0)


def build_metrics_snapshot() -> dict:
    """Return a snapshot of all collected metrics."""
    jobs: Dict[str, dict] = {}
    all_job_names = set(_runtime_samples) | set(_alert_counts)
    for name in all_job_names:
        jobs[name] = {
            "average_runtime_seconds": average_runtime(name),
            "max_runtime_seconds": max_runtime(name),
            "sample_count": len(_runtime_samples.get(name, [])),
            "alerts": dict(_alert_counts.get(name, {})),
        }
    return {
        "uptime_seconds": time.time() - _start_time,
        "jobs": jobs,
    }


def reset() -> None:
    """Clear all collected metrics (primarily for testing)."""
    global _start_time
    _runtime_samples.clear()
    _alert_counts.clear()
    _start_time = time.time()
