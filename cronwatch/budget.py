"""Runtime budget tracking: warns when a job consistently consumes more
than its configured max_seconds threshold."""

from __future__ import annotations

from typing import Optional

from cronwatch.history import get_runs

# Minimum number of recent runs required before budget analysis is meaningful.
_MIN_SAMPLES = 3

# How many of the most recent runs to consider.
_WINDOW = 10


def _recent_runtimes(job_name: str, window: int = _WINDOW) -> list[float]:
    """Return up to *window* most recent non-None runtimes for *job_name*."""
    runs = get_runs(job_name)
    runtimes = [r["runtime"] for r in runs if r.get("runtime") is not None]
    return runtimes[-window:]


def budget_utilisation(job_name: str, max_seconds: float) -> Optional[float]:
    """Return average runtime as a fraction of *max_seconds*, or None if
    insufficient data is available.

    A value of 1.0 means the job is using exactly its budget on average;
    values above 1.0 indicate consistent over-budget execution.
    """
    if max_seconds <= 0:
        return None
    runtimes = _recent_runtimes(job_name)
    if len(runtimes) < _MIN_SAMPLES:
        return None
    avg = sum(runtimes) / len(runtimes)
    return avg / max_seconds


def is_over_budget(job_name: str, max_seconds: float, threshold: float = 0.9) -> bool:
    """Return True when average utilisation exceeds *threshold*.

    The default threshold of 0.9 fires a warning when the job is consistently
    using 90 % or more of its allowed runtime, giving operators early notice
    before hard misses start occurring.
    """
    util = budget_utilisation(job_name, max_seconds)
    if util is None:
        return False
    return util >= threshold


def budget_summary(job_name: str, max_seconds: float) -> dict:
    """Return a dict describing the current budget status for *job_name*."""
    util = budget_utilisation(job_name, max_seconds)
    runtimes = _recent_runtimes(job_name)
    avg = sum(runtimes) / len(runtimes) if runtimes else None
    return {
        "job": job_name,
        "max_seconds": max_seconds,
        "average_runtime": avg,
        "utilisation": util,
        "over_budget": is_over_budget(job_name, max_seconds),
        "sample_count": len(runtimes),
    }
