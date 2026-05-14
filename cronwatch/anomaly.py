"""Anomaly detection: flag jobs whose runtime deviates significantly from historical average."""

import logging
from typing import Optional

from cronwatch.history import average_runtime, get_runs

logger = logging.getLogger(__name__)

# Minimum number of historical runs required before anomaly detection kicks in.
MIN_SAMPLES = 5

# Number of standard deviations above the mean that triggers an anomaly.
DEFAULT_SIGMA_THRESHOLD = 2.0


def _stddev(values: list[float]) -> float:
    """Population standard deviation."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5


def runtime_stddev(job_name: str) -> Optional[float]:
    """Return the population standard deviation of recorded runtimes for *job_name*."""
    runs = get_runs(job_name)
    runtimes = [r["runtime"] for r in runs if r.get("runtime") is not None]
    if len(runtimes) < 2:
        return None
    return _stddev(runtimes)


def is_anomalous(
    job_name: str,
    current_runtime: float,
    sigma_threshold: float = DEFAULT_SIGMA_THRESHOLD,
    min_samples: int = MIN_SAMPLES,
) -> bool:
    """Return True if *current_runtime* is an anomaly relative to historical data.

    An anomaly is defined as a runtime that exceeds ``mean + sigma_threshold * stddev``.
    Returns False when there are fewer than *min_samples* historical runs.
    """
    runs = get_runs(job_name)
    runtimes = [r["runtime"] for r in runs if r.get("runtime") is not None]
    if len(runtimes) < min_samples:
        logger.debug(
            "anomaly check skipped for %s: only %d samples (need %d)",
            job_name,
            len(runtimes),
            min_samples,
        )
        return False

    mean = sum(runtimes) / len(runtimes)
    stddev = _stddev(runtimes)
    threshold = mean + sigma_threshold * stddev

    if current_runtime > threshold:
        logger.warning(
            "anomaly detected for %s: runtime %.1fs exceeds threshold %.1fs (mean=%.1f, sigma=%.1f)",
            job_name,
            current_runtime,
            threshold,
            mean,
            stddev,
        )
        return True
    return False


def anomaly_summary(job_name: str) -> dict:
    """Return a dict summarising anomaly-detection statistics for *job_name*."""
    avg = average_runtime(job_name)
    stddev = runtime_stddev(job_name)
    runs = get_runs(job_name)
    sample_count = sum(1 for r in runs if r.get("runtime") is not None)
    return {
        "job": job_name,
        "sample_count": sample_count,
        "mean_runtime": avg,
        "stddev_runtime": stddev,
        "ready": sample_count >= MIN_SAMPLES,
    }
