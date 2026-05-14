"""Tests for cronwatch.forecast module."""

import pytest
from cronwatch import history, forecast


@pytest.fixture(autouse=True)
def clear_history():
    history.reset()
    yield
    history.reset()


def _add_runs(job_name: str, runtimes: list):
    for rt in runtimes:
        history.record_run(job_name, rt)


def test_forecast_none_when_no_data():
    result = forecast.forecast_runtime("backup")
    assert result is None


def test_forecast_none_below_min_samples():
    _add_runs("backup", [10.0, 12.0])
    result = forecast.forecast_runtime("backup")
    assert result is None


def test_forecast_returns_float_at_min_samples():
    _add_runs("backup", [10.0, 12.0, 11.0])
    result = forecast.forecast_runtime("backup")
    assert isinstance(result, float)


def test_weighted_average_uniform():
    result = forecast.weighted_average([10.0, 10.0, 10.0])
    assert result == pytest.approx(10.0)


def test_weighted_average_increasing_weights_recent():
    # weights: 1,2,3 for values 5,10,15 => (5+20+45)/6 = 11.67
    result = forecast.weighted_average([5.0, 10.0, 15.0])
    assert result == pytest.approx(11.6667, rel=1e-3)


def test_weighted_average_empty_returns_none():
    assert forecast.weighted_average([]) is None


def test_forecast_deviation_none_without_enough_data():
    _add_runs("sync", [10.0])
    result = forecast.forecast_deviation("sync", 15.0)
    assert result is None


def test_forecast_deviation_positive_when_over():
    _add_runs("sync", [10.0, 10.0, 10.0])
    dev = forecast.forecast_deviation("sync", 15.0)
    assert dev == pytest.approx(5.0)


def test_forecast_deviation_negative_when_under():
    _add_runs("sync", [20.0, 20.0, 20.0])
    dev = forecast.forecast_deviation("sync", 10.0)
    assert dev == pytest.approx(-10.0)


def test_forecast_summary_keys():
    summary = forecast.forecast_summary("backup")
    assert "job" in summary
    assert "samples" in summary
    assert "forecasted_runtime" in summary
    assert "has_forecast" in summary


def test_forecast_summary_no_data():
    summary = forecast.forecast_summary("backup")
    assert summary["has_forecast"] is False
    assert summary["forecasted_runtime"] is None
    assert summary["samples"] == 0


def test_forecast_summary_with_data():
    _add_runs("backup", [30.0, 32.0, 31.0])
    summary = forecast.forecast_summary("backup")
    assert summary["has_forecast"] is True
    assert summary["forecasted_runtime"] is not None
    assert summary["samples"] == 3


def test_multiple_jobs_are_independent():
    _add_runs("job_a", [5.0, 5.0, 5.0])
    _add_runs("job_b", [100.0, 100.0, 100.0])
    assert forecast.forecast_runtime("job_a") == pytest.approx(5.0)
    assert forecast.forecast_runtime("job_b") == pytest.approx(100.0)
