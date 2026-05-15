"""Parameterised window-boundary tests for ratelimit."""

import time
import pytest
import cronwatch.ratelimit as rl


@pytest.fixture(autouse=True)
def clear_state():
    rl.reset()
    yield
    rl.reset()


@pytest.mark.parametrize("window", [10, 60, 300, 3600])
def test_limited_within_various_windows(window):
    rl.record_sent("missed", "job")
    assert rl.is_rate_limited("missed", "job", window_seconds=window)


@pytest.mark.parametrize("window", [10, 60, 300])
def test_time_until_allowed_within_window(window):
    rl.record_sent("missed", "job")
    remaining = rl.time_until_allowed("missed", "job", window_seconds=window)
    assert remaining is not None
    assert 0 < remaining <= window


@pytest.mark.parametrize("n_jobs", [1, 5, 20])
def test_independent_jobs_do_not_interfere(n_jobs):
    job_names = [f"job_{i}" for i in range(n_jobs)]
    # Record only the first job
    rl.record_sent("missed", job_names[0])
    for name in job_names[1:]:
        assert not rl.is_rate_limited("missed", name)


@pytest.mark.parametrize("alert_type", ["missed", "long_running"])
def test_each_alert_type_tracked_separately(alert_type):
    other = "long_running" if alert_type == "missed" else "missed"
    rl.record_sent(alert_type, "job")
    assert not rl.is_rate_limited(other, "job")
    assert rl.is_rate_limited(alert_type, "job")
