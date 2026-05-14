"""Persistent job run history: stores recent runtimes per job for trend analysis."""

import time
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

# (start_ts, end_ts, runtime_seconds)
RunRecord = Tuple[float, float, float]

_MAX_HISTORY = 50  # max records kept per job

_history: Dict[str, Deque[RunRecord]] = {}


def _ensure(job_name: str) -> Deque[RunRecord]:
    if job_name not in _history:
        _history[job_name] = deque(maxlen=_MAX_HISTORY)
    return _history[job_name]


def record_run(job_name: str, start_ts: float, end_ts: float) -> None:
    """Record a completed run for a job."""
    runtime = end_ts - start_ts
    _ensure(job_name).append((start_ts, end_ts, runtime))


def get_runs(job_name: str) -> List[RunRecord]:
    """Return all stored run records for a job (oldest first)."""
    return list(_ensure(job_name))


def average_runtime(job_name: str) -> Optional[float]:
    """Return average runtime in seconds, or None if no history."""
    runs = get_runs(job_name)
    if not runs:
        return None
    return sum(r[2] for r in runs) / len(runs)


def last_runtime(job_name: str) -> Optional[float]:
    """Return the most recent runtime in seconds, or None."""
    runs = get_runs(job_name)
    if not runs:
        return None
    return runs[-1][2]


def last_start(job_name: str) -> Optional[float]:
    """Return the most recent start timestamp, or None."""
    runs = get_runs(job_name)
    if not runs:
        return None
    return runs[-1][0]


def run_count(job_name: str) -> int:
    """Return the number of stored runs for a job."""
    return len(_ensure(job_name))


def reset(job_name: Optional[str] = None) -> None:
    """Clear history for a specific job or all jobs."""
    global _history
    if job_name is None:
        _history.clear()
    else:
        _history.pop(job_name, None)
