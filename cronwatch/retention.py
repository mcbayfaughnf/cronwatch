"""Retention policy: prune old run history and metrics beyond a configured age."""

import time
import logging
from typing import Optional

import cronwatch.history as history
import cronwatch.metrics as metrics

logger = logging.getLogger(__name__)

# Module-level last-prune timestamp
_last_prune_time: Optional[float] = None


def _reset_last_prune_time() -> None:
    """Reset the last-prune timestamp (used in tests)."""
    global _last_prune_time
    _last_prune_time = None


def is_prune_due(interval_seconds: int) -> bool:
    """Return True if enough time has elapsed since the last prune."""
    if _last_prune_time is None:
        return True
    return (time.time() - _last_prune_time) >= interval_seconds


def prune_history(job_name: str, max_age_seconds: float) -> int:
    """Remove run records for *job_name* older than *max_age_seconds*.

    Returns the number of records removed.
    """
    cutoff = time.time() - max_age_seconds
    runs = history.get_runs(job_name)
    kept = [r for r in runs if r["finished_at"] >= cutoff]
    removed = len(runs) - len(kept)
    if removed:
        history._ensure(job_name)
        history._runs[job_name] = kept
        logger.debug("Pruned %d old run(s) for job '%s'", removed, job_name)
    return removed


def prune_all(job_names: list, max_age_seconds: float) -> dict:
    """Prune history for all *job_names*. Returns mapping of job -> removed count."""
    global _last_prune_time
    results = {}
    for name in job_names:
        results[name] = prune_history(name, max_age_seconds)
    _last_prune_time = time.time()
    total = sum(results.values())
    if total:
        logger.info("Retention prune complete: removed %d run record(s) across %d job(s)",
                    total, len(job_names))
    return results


def maybe_prune(job_names: list, max_age_seconds: float, interval_seconds: int) -> None:
    """Prune old history if the prune interval has elapsed."""
    if is_prune_due(interval_seconds):
        prune_all(job_names, max_age_seconds)
