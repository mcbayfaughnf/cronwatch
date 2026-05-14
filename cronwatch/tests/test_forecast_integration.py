"""Integration tests: forecast interacts correctly with history module."""

import pytest
from cronwatch import history, forecast


@pytest.fixture(autouse=True)
def clear_history():
    history.reset()
    yield
    history.reset()


def _simulate_runs(job_name: str, runtimes: list):
    for rt in runtimes:
        history.record_run(job_name, rt)


def test_forecast_improves_as_more_data_arrives():
    """Forecast should become available once MIN_SAMPLES is reached."""
    job = "cleanup"
    history.record_run(job, 20.0)
    assert forecast.forecast_runtime(job) is None
    history.record_run(job, 22.0)
    assert forecast.forecast_runtime(job) is None
    history.record_run(job, 21.0)
    result = forecast.forecast_runtime(job)
    assert result is not None
    assert 20.0 <= result <= 22.0


def test_forecast_reflects_recent_trend():
    """Weighted average should reflect that recent values have more influence."""
    job = "indexer"
    # Early runs are slow, recent runs are fast
    _simulate_runs(job, [60.0, 60.0, 60.0, 10.0, 10.0, 10.0])
    result = forecast.forecast_runtime(job)
    # Should be closer to 10 than to 60
    assert result < 35.0


def test_deviation_zero_when_actual_matches_forecast():
    job = "report"
    _simulate_runs(job, [15.0, 15.0, 15.0])
    predicted = forecast.forecast_runtime(job)
    dev = forecast.forecast_deviation(job, predicted)
    assert dev == pytest.approx(0.0, abs=1e-6)


def test_forecast_uses_only_last_ten_runs():
    """Forecast should cap at 10 most recent runs."""
    job = "archiver"
    # 20 old slow runs then 10 fast runs
    _simulate_runs(job, [200.0] * 20)
    _simulate_runs(job, [10.0] * 10)
    result = forecast.forecast_runtime(job)
    # Only the 10 fast runs should matter
    assert result == pytest.approx(10.0)
