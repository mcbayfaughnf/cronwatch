"""Integration tests: trend analysis against real history records."""

import pytest
from cronwatch.history import reset, record_run
from cronwatch import trend


@pytest.fixture(autouse=True)
def clear_history():
    reset()
    yield
    reset()


def test_slope_matches_manual_calculation():
    """Verify slope against a hand-calculated expected value."""
    # runtimes: 2, 4, 6 => indices 0,1,2; mean_x=1, mean_y=4
    # numerator = (0-1)(2-4)+(1-1)(4-4)+(2-1)(6-4) = 2+0+2 = 4
    # denominator = 1+0+1 = 2 => slope = 2.0
    record_run("job", runtime=2.0, success=True)
    record_run("job", runtime=4.0, success=True)
    record_run("job", runtime=6.0, success=True)
    assert trend.trend_slope("job") == pytest.approx(2.0)


def test_multiple_jobs_are_independent():
    record_run("job_a", runtime=5.0, success=True)
    record_run("job_a", runtime=10.0, success=True)
    record_run("job_b", runtime=50.0, success=True)
    record_run("job_b", runtime=50.0, success=True)

    slope_a = trend.trend_slope("job_a")
    slope_b = trend.trend_slope("job_b")

    assert slope_a is not None and slope_a > 0
    assert slope_b is not None and abs(slope_b) < 1e-9


def test_trend_up_alert_scenario():
    """Simulate a degrading job and confirm trending_up is detected."""
    runtimes = [20 + i * 3 for i in range(10)]  # 20,23,26,...,47
    for rt in runtimes:
        record_run("slow_job", runtime=float(rt), success=True)

    assert trend.is_trending_up("slow_job", window=10, threshold=2.0) is True
    summary = trend.trend_summary("slow_job", window=10)
    assert summary["trending_up"] is True
    assert summary["slope"] == pytest.approx(3.0)
