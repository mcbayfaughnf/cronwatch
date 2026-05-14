"""Baseline runtime tracking: compute and store expected runtime ranges per job."""

from typing import Optional, Tuple
from cronwatch.history import get_runs, run_count

# Minimum number of runs required before a baseline is considered valid
MIN_SAMPLES = 5

# How many standard deviations above the mean to set the upper bound
STDDEV_MULTIPLIER = 2.0


def _mean(values: list) -> float:
    return sum(values) / len(values)


def _stddev(values: list) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return variance ** 0.5


def has_baseline(job_name: str) -> bool:
    """Return True if enough runs exist to compute a meaningful baseline."""
    return run_count(job_name) >= MIN_SAMPLES


def baseline_range(job_name: str) -> Optional[Tuple[float, float]]:
    """Return (lower, upper) expected runtime bounds for a job, or None."""
    if not has_baseline(job_name):
        return None
    runs = get_runs(job_name)
    runtimes = [r["runtime"] for r in runs if r.get("runtime") is not None]
    if len(runtimes) < MIN_SAMPLES:
        return None
    m = _mean(runtimes)
    sd = _stddev(runtimes)
    lower = max(0.0, m - STDDEV_MULTIPLIER * sd)
    upper = m + STDDEV_MULTIPLIER * sd
    return (lower, upper)


def is_within_baseline(job_name: str, runtime: float) -> Optional[bool]:
    """Return True/False if runtime is within baseline, or None if no baseline."""
    bounds = baseline_range(job_name)
    if bounds is None:
        return None
    lower, upper = bounds
    return lower <= runtime <= upper


def baseline_summary(job_name: str) -> dict:
    """Return a dict summarising the baseline for a job."""
    bounds = baseline_range(job_name)
    if bounds is None:
        return {"job": job_name, "has_baseline": False, "lower": None, "upper": None}
    return {
        "job": job_name,
        "has_baseline": True,
        "lower": round(bounds[0], 3),
        "upper": round(bounds[1], 3),
    }
