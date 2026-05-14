"""Runtime forecasting: predict next expected runtime based on history."""

from typing import Optional
from cronwatch.history import get_runs

_MIN_SAMPLES = 3


def _recent_runtimes(job_name: str, limit: int = 10) -> list:
    runs = get_runs(job_name)
    return [r["runtime"] for r in runs if r.get("runtime") is not None][-limit:]


def weighted_average(runtimes: list) -> Optional[float]:
    """Compute a linearly weighted average, giving more weight to recent values."""
    if not runtimes:
        return None
    n = len(runtimes)
    total_weight = sum(range(1, n + 1))
    weighted_sum = sum(w * v for w, v in zip(range(1, n + 1), runtimes))
    return weighted_sum / total_weight


def forecast_runtime(job_name: str) -> Optional[float]:
    """Return a forecasted runtime in seconds, or None if insufficient data."""
    runtimes = _recent_runtimes(job_name)
    if len(runtimes) < _MIN_SAMPLES:
        return None
    return weighted_average(runtimes)


def forecast_deviation(job_name: str, actual: float) -> Optional[float]:
    """Return how far actual deviates from forecast (positive = over forecast)."""
    predicted = forecast_runtime(job_name)
    if predicted is None:
        return None
    return actual - predicted


def forecast_summary(job_name: str) -> dict:
    """Return a summary dict with forecast info for a job."""
    runtimes = _recent_runtimes(job_name)
    predicted = forecast_runtime(job_name)
    return {
        "job": job_name,
        "samples": len(runtimes),
        "forecasted_runtime": round(predicted, 2) if predicted is not None else None,
        "has_forecast": predicted is not None,
    }
