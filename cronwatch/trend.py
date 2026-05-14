"""Trend analysis for job runtimes over recent history."""

from typing import Optional
from cronwatch.history import get_runs


def _recent_runtimes(job_name: str, window: int) -> list[float]:
    """Return the last `window` runtimes for a job."""
    runs = get_runs(job_name)
    return [r["runtime"] for r in runs[-window:] if r.get("runtime") is not None]


def trend_slope(job_name: str, window: int = 10) -> Optional[float]:
    """Return the linear trend slope of runtimes over the last `window` runs.

    A positive slope means runtimes are increasing; negative means decreasing.
    Returns None if fewer than 2 data points are available.
    """
    runtimes = _recent_runtimes(job_name, window)
    n = len(runtimes)
    if n < 2:
        return None

    indices = list(range(n))
    mean_x = sum(indices) / n
    mean_y = sum(runtimes) / n

    numerator = sum((indices[i] - mean_x) * (runtimes[i] - mean_y) for i in range(n))
    denominator = sum((indices[i] - mean_x) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0

    return numerator / denominator


def is_trending_up(job_name: str, window: int = 10, threshold: float = 1.0) -> bool:
    """Return True if runtimes are increasing by more than `threshold` sec/run."""
    slope = trend_slope(job_name, window)
    return slope is not None and slope > threshold


def is_trending_down(job_name: str, window: int = 10, threshold: float = 1.0) -> bool:
    """Return True if runtimes are decreasing by more than `threshold` sec/run.

    A negative slope whose absolute value exceeds `threshold` indicates a
    consistent improvement in job performance over the sampled window.
    """
    slope = trend_slope(job_name, window)
    return slope is not None and slope < -threshold


def trend_summary(job_name: str, window: int = 10) -> dict:
    """Return a dict summarising the trend for a job."""
    runtimes = _recent_runtimes(job_name, window)
    slope = trend_slope(job_name, window)
    return {
        "job": job_name,
        "samples": len(runtimes),
        "slope": slope,
        "trending_up": is_trending_up(job_name, window),
        "trending_down": is_trending_down(job_name, window),
        "min_runtime": min(runtimes) if runtimes else None,
        "max_runtime": max(runtimes) if runtimes else None,
    }
