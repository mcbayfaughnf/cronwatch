"""Silence windows: suppress alerts for specific jobs during scheduled maintenance."""

import time
from typing import Dict, List, Optional, Tuple

# job_name -> list of (start_epoch, end_epoch) silence windows
_windows: Dict[str, List[Tuple[float, float]]] = {}


def reset() -> None:
    """Clear all silence windows (used in tests)."""
    _windows.clear()


def add_window(job_name: str, start: float, end: float) -> None:
    """Register a silence window for a job.

    Args:
        job_name: The name of the job to silence.
        start: Unix timestamp when the silence begins.
        end: Unix timestamp when the silence ends.
    """
    if end <= start:
        raise ValueError("Silence window end must be after start")
    _windows.setdefault(job_name, []).append((start, end))


def remove_expired(job_name: str, now: Optional[float] = None) -> None:
    """Drop any windows that have already ended."""
    now = now if now is not None else time.time()
    if job_name not in _windows:
        return
    _windows[job_name] = [(s, e) for s, e in _windows[job_name] if e > now]
    if not _windows[job_name]:
        del _windows[job_name]


def is_silenced(job_name: str, now: Optional[float] = None) -> bool:
    """Return True if *job_name* is currently inside a silence window.

    Args:
        job_name: The job to check.
        now: Override current time (useful in tests).

    Returns:
        True when the current moment falls within any registered window.
    """
    now = now if now is not None else time.time()
    for start, end in _windows.get(job_name, []):
        if start <= now < end:
            return True
    return False


def silence_summary(job_name: str, now: Optional[float] = None) -> Dict:
    """Return a summary dict describing the silence state for a job."""
    now = now if now is not None else time.time()
    active = is_silenced(job_name, now=now)
    windows = _windows.get(job_name, [])
    # Find the soonest upcoming window start (if not currently silenced)
    upcoming: Optional[float] = None
    if not active:
        future = [s for s, e in windows if s > now]
        upcoming = min(future) if future else None
    return {
        "job": job_name,
        "silenced": active,
        "window_count": len(windows),
        "next_window_start": upcoming,
    }
