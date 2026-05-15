import time
import pytest
import cronwatch.ratelimit as rl


@pytest.fixture(autouse=True)
def clear_state():
    rl.reset()
    yield
    rl.reset()


@pytest.fixture
def missed():
    return ("missed", "backup_job")


@pytest.fixture
def long_running():
    return ("long_running", "backup_job")


def test_not_limited_initially(missed):
    assert rl.is_rate_limited(*missed) is False


def test_limited_immediately_after_record(missed):
    rl.record_sent(*missed)
    assert rl.is_rate_limited(*missed) is True


def test_not_limited_after_window_expires(missed, monkeypatch):
    rl.record_sent(*missed)
    # Advance time beyond the window
    future = time.time() + rl.DEFAULT_WINDOW_SECONDS + 1
    monkeypatch.setattr("cronwatch.ratelimit.time", type("T", (), {"time": staticmethod(lambda: future)})()
    )
    assert rl.is_rate_limited(*missed, window_seconds=rl.DEFAULT_WINDOW_SECONDS) is False


def test_different_types_are_independent(missed, long_running):
    rl.record_sent(*missed)
    assert rl.is_rate_limited(*long_running) is False


def test_different_jobs_are_independent():
    rl.record_sent("missed", "job_a")
    assert rl.is_rate_limited("missed", "job_b") is False


def test_time_until_allowed_none_when_not_limited(missed):
    assert rl.time_until_allowed(*missed) is None


def test_time_until_allowed_positive_after_record(missed):
    rl.record_sent(*missed)
    remaining = rl.time_until_allowed(*missed)
    assert remaining is not None
    assert 0 < remaining <= rl.DEFAULT_WINDOW_SECONDS


def test_reset_specific_type_clears_only_that_type():
    rl.record_sent("missed", "job_a")
    rl.record_sent("long_running", "job_a")
    rl.reset(alert_type="missed")
    assert rl.is_rate_limited("missed", "job_a") is False
    assert rl.is_rate_limited("long_running", "job_a") is True


def test_reset_specific_job_clears_only_that_job():
    rl.record_sent("missed", "job_a")
    rl.record_sent("missed", "job_b")
    rl.reset(job_name="job_a")
    assert rl.is_rate_limited("missed", "job_a") is False
    assert rl.is_rate_limited("missed", "job_b") is True


def test_custom_window_respected():
    rl.record_sent("missed", "job_a")
    # With a 1-second window it should still be limited immediately
    assert rl.is_rate_limited("missed", "job_a", window_seconds=1) is True
