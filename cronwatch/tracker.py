"""Tracks cron job execution state and detects missed or long-running jobs."""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from cronwatch.config import JobConfig


@dataclass
class JobState:
    """Tracks runtime state for a single cron job."""
    name: str
    last_seen: Optional[float] = None
    started_at: Optional[float] = None
    is_running: bool = False

    def mark_started(self) -> None:
        self.started_at = time.monotonic()
        self.is_running = True
        self.last_seen = time.time()

    def mark_finished(self) -> None:
        self.is_running = False
        self.started_at = None

    def runtime_seconds(self) -> Optional[float]:
        if self.is_running and self.started_at is not None:
            return time.monotonic() - self.started_at
        return None

    def seconds_since_last_seen(self) -> Optional[float]:
        if self.last_seen is None:
            return None
        return time.time() - self.last_seen


class JobTracker:
    """Manages state for all configured jobs and evaluates alert conditions."""

    def __init__(self, jobs: Dict[str, JobConfig]) -> None:
        self._configs = jobs
        self._states: Dict[str, JobState] = {
            name: JobState(name=name) for name in jobs
        }

    def start(self, job_name: str) -> None:
        """Record that a job has started."""
        if job_name in self._states:
            self._states[job_name].mark_started()

    def finish(self, job_name: str) -> None:
        """Record that a job has finished."""
        if job_name in self._states:
            self._states[job_name].mark_finished()

    def check_long_running(self, job_name: str) -> bool:
        """Return True if the job has exceeded its max_runtime_seconds threshold."""
        state = self._states.get(job_name)
        config = self._configs.get(job_name)
        if state is None or config is None or config.max_runtime_seconds is None:
            return False
        runtime = state.runtime_seconds()
        return runtime is not None and runtime > config.max_runtime_seconds

    def check_missed(self, job_name: str) -> bool:
        """Return True if the job has not been seen within its expected interval."""
        state = self._states.get(job_name)
        config = self._configs.get(job_name)
        if state is None or config is None or config.expected_interval_seconds is None:
            return False
        elapsed = state.seconds_since_last_seen()
        return elapsed is not None and elapsed > config.expected_interval_seconds

    def get_state(self, job_name: str) -> Optional[JobState]:
        return self._states.get(job_name)
