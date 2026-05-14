"""Integration tests: budget module working with live history records."""

import pytest

from cronwatch.history import reset, record_run
from cronwatch.budget import budget_utilisation, is_over_budget, budget_summary
from cronwatch.config import JobConfig


@pytest.fixture(autouse=True)
def clear_history():
    reset()
    yield
    reset()


def _simulate_runs(job_name: str, runtimes: list[float]) -> None:
    for rt in runtimes:
        record_run(job_name, runtime=rt)


def test_no_budget_signal_before_min_samples():
    """Budget analysis should stay silent until enough data has accumulated."""
    _simulate_runs("etl", [100.0, 100.0])  # only 2
    assert budget_utilisation("etl", max_seconds=60) is None
    assert is_over_budget("etl", max_seconds=60) is False


def test_budget_established_after_min_samples():
    _simulate_runs("etl", [30.0, 30.0, 30.0])
    util = budget_utilisation("etl", max_seconds=60)
    assert util is not None


def test_gradually_increasing_runtimes_trigger_budget_warning():
    """Simulate a job whose runtime creeps upward until it breaches 90 %."""
    runtimes = [50.0, 52.0, 54.0, 56.0, 54.0, 55.0, 56.0, 57.0, 58.0, 55.0]
    _simulate_runs("report", runtimes)
    # Average ≈ 54.7 / 60 ≈ 0.91 → should be over budget
    assert is_over_budget("report", max_seconds=60) is True


def test_healthy_job_stays_under_budget():
    _simulate_runs("ping", [5.0, 6.0, 5.5, 5.0, 6.0, 5.5, 5.0, 5.5, 6.0, 5.0])
    assert is_over_budget("ping", max_seconds=60) is False


def test_multiple_jobs_are_independent():
    _simulate_runs("heavy", [55.0, 56.0, 57.0])
    _simulate_runs("light", [5.0, 5.0, 5.0])
    assert is_over_budget("heavy", max_seconds=60) is True
    assert is_over_budget("light", max_seconds=60) is False


def test_summary_reflects_live_history():
    _simulate_runs("nightly", [45.0, 50.0, 55.0])
    summary = budget_summary("nightly", max_seconds=60)
    expected_avg = (45.0 + 50.0 + 55.0) / 3
    assert abs(summary["average_runtime"] - expected_avg) < 1e-9
    assert summary["sample_count"] == 3
