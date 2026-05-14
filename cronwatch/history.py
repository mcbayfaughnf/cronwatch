"""Per-job run history: record completed runs and query aggregate stats."""

import time
from typing import Optional

# Internal store: job_name -> list of {finished_at, duration}
_runs: dict = {}


def _ensure(job_name: str) -> None:
    """Initialise the store entry for *job_name* if absent."""
    if job_name not in _runs:
        _runs[job_name] = []


def reset() -> None:
    """Clear all recorded history (used in tests)."""
    _runs.clear()


def record_run(job_name: str, duration: float) -> None:
    """Append a completed run record for *job_name*."""
    _ensure(job_name)
    _runs[job_name].append({
        "finished_at": time.time(),
        "duration": duration,
    })


def get_runs(job_name: str) -> list:
    """Return all recorded runs for *job_name* (oldest first)."""
    return list(_runs.get(job_name, []))


def run_count(job_name: str) -> int:
    """Return the total number of recorded runs for *job_name*."""
    return len(_runs.get(job_name, []))


def average_runtime(job_name: str) -> Optional[float]:
    """Return the mean duration across all recorded runs, or None if no data."""
    runs = _runs.get(job_name, [])
    if not runs:
        return None
    return sum(r["duration"] for r in runs) / len(runs)


def last_runtime(job_name: str) -> Optional[float]:
    """Return the duration of the most recent run, or None if no data."""
    runs = _runs.get(job_name, [])
    if not runs:
        return None
    return runs[-1]["duration"]


def last_finished_at(job_name: str) -> Optional[float]:
    """Return the finish timestamp of the most recent run, or None."""
    runs = _runs.get(job_name, [])
    if not runs:
        return None
    return runs[-1]["finished_at"]


def max_runtime(job_name: str) -> Optional[float]:
    """Return the maximum recorded duration, or None if no data."""
    runs = _runs.get(job_name, [])
    if not runs:
        return None
    return max(r["duration"] for r in runs)
