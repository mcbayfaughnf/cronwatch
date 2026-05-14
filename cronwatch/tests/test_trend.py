"""Tests for cronwatch.trend module."""

import pytest
from cronwatch.history import reset, record_run
from cronwatch import trend


JOB = "backup"


@pytest.fixture(autouse=True)
def clear_history():
    reset()
    yield
    reset()


def _add_runs(job: str, runtimes: list[float]):
    for rt in runtimes:
        record_run(job, runtime=rt, success=True)


def test_trend_slope_none_when_no_data():
    assert trend.trend_slope(JOB) is None


def test_trend_slope_none_with_single_run():
    _add_runs(JOB, [30.0])
    assert trend.trend_slope(JOB) is None


def test_trend_slope_flat_returns_zero():
    _add_runs(JOB, [10.0, 10.0, 10.0, 10.0])
    slope = trend.trend_slope(JOB)
    assert slope is not None
    assert abs(slope) < 1e-9


def test_trend_slope_increasing():
    # runtimes grow by 5 each run => slope ~5
    _add_runs(JOB, [10.0, 15.0, 20.0, 25.0, 30.0])
    slope = trend.trend_slope(JOB)
    assert slope is not None
    assert slope > 4.0


def test_trend_slope_decreasing():
    _add_runs(JOB, [30.0, 25.0, 20.0, 15.0, 10.0])
    slope = trend.trend_slope(JOB)
    assert slope is not None
    assert slope < -4.0


def test_is_trending_up_true():
    _add_runs(JOB, [10.0, 15.0, 20.0, 25.0, 30.0])
    assert trend.is_trending_up(JOB, threshold=1.0) is True


def test_is_trending_up_false_for_flat():
    _add_runs(JOB, [10.0, 10.0, 10.0, 10.0])
    assert trend.is_trending_up(JOB, threshold=1.0) is False


def test_is_trending_up_false_when_no_data():
    assert trend.is_trending_up(JOB) is False


def test_trend_summary_keys():
    _add_runs(JOB, [10.0, 12.0, 14.0])
    summary = trend.trend_summary(JOB)
    assert "job" in summary
    assert "samples" in summary
    assert "slope" in summary
    assert "trending_up" in summary
    assert "min_runtime" in summary
    assert "max_runtime" in summary


def test_trend_summary_values_when_empty():
    summary = trend.trend_summary(JOB)
    assert summary["samples"] == 0
    assert summary["slope"] is None
    assert summary["min_runtime"] is None
    assert summary["max_runtime"] is None


def test_trend_summary_respects_window():
    # Add 20 runs but only last 5 should count
    _add_runs(JOB, [100.0] * 15 + [10.0, 11.0, 12.0, 13.0, 14.0])
    summary = trend.trend_summary(JOB, window=5)
    assert summary["samples"] == 5
    assert summary["min_runtime"] == pytest.approx(10.0)
