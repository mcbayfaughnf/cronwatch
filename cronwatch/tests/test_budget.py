"""Tests for cronwatch.budget."""

import pytest

from cronwatch.history import reset, record_run
import cronwatch.budget as budget


@pytest.fixture(autouse=True)
def clear_history():
    reset()
    yield
    reset()


def _add_runs(job_name: str, runtimes: list[float]) -> None:
    for rt in runtimes:
        record_run(job_name, runtime=rt)


# ---------------------------------------------------------------------------
# budget_utilisation
# ---------------------------------------------------------------------------

def test_utilisation_none_when_no_data():
    assert budget.budget_utilisation("backup", max_seconds=60) is None


def test_utilisation_none_below_min_samples():
    _add_runs("backup", [30.0, 35.0])  # only 2 runs
    assert budget.budget_utilisation("backup", max_seconds=60) is None


def test_utilisation_returns_float_at_min_samples():
    _add_runs("backup", [30.0, 30.0, 30.0])
    util = budget.budget_utilisation("backup", max_seconds=60)
    assert util is not None
    assert abs(util - 0.5) < 1e-9


def test_utilisation_above_one_when_over_budget():
    _add_runs("backup", [70.0, 80.0, 90.0])
    util = budget.budget_utilisation("backup", max_seconds=60)
    assert util is not None
    assert util > 1.0


def test_utilisation_none_when_max_seconds_zero():
    _add_runs("backup", [10.0, 10.0, 10.0])
    assert budget.budget_utilisation("backup", max_seconds=0) is None


def test_utilisation_uses_only_recent_window():
    # 10 old cheap runs + 3 expensive recent runs; window=10 should include all
    _add_runs("j", [1.0] * 10 + [90.0, 90.0, 90.0])
    util = budget.budget_utilisation("j", max_seconds=100)
    assert util is not None
    # Average of last 10 values: 7*1 + 3*90 = 277 / 10 = 27.7 → util = 0.277
    assert abs(util - 0.277) < 0.01


# ---------------------------------------------------------------------------
# is_over_budget
# ---------------------------------------------------------------------------

def test_not_over_budget_when_no_data():
    assert budget.is_over_budget("backup", max_seconds=60) is False


def test_not_over_budget_when_well_under_threshold():
    _add_runs("backup", [10.0, 10.0, 10.0])
    assert budget.is_over_budget("backup", max_seconds=60) is False


def test_over_budget_at_default_threshold():
    # utilisation = 55/60 ≈ 0.917 > 0.9
    _add_runs("backup", [55.0, 55.0, 55.0])
    assert budget.is_over_budget("backup", max_seconds=60) is True


def test_over_budget_custom_threshold():
    _add_runs("backup", [40.0, 40.0, 40.0])  # util = 40/60 ≈ 0.667
    assert budget.is_over_budget("backup", max_seconds=60, threshold=0.5) is True
    assert budget.is_over_budget("backup", max_seconds=60, threshold=0.8) is False


# ---------------------------------------------------------------------------
# budget_summary
# ---------------------------------------------------------------------------

def test_budget_summary_keys():
    _add_runs("sync", [20.0, 25.0, 30.0])
    summary = budget.budget_summary("sync", max_seconds=60)
    for key in ("job", "max_seconds", "average_runtime", "utilisation",
                "over_budget", "sample_count"):
        assert key in summary


def test_budget_summary_values():
    _add_runs("sync", [30.0, 30.0, 30.0])
    summary = budget.budget_summary("sync", max_seconds=60)
    assert summary["job"] == "sync"
    assert summary["max_seconds"] == 60
    assert abs(summary["average_runtime"] - 30.0) < 1e-9
    assert abs(summary["utilisation"] - 0.5) < 1e-9
    assert summary["over_budget"] is False
    assert summary["sample_count"] == 3
