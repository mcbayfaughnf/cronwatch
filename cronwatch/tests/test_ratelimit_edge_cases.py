"""Edge cases for the ratelimit module."""

import time
import pytest
import cronwatch.ratelimit as rl


@pytest.fixture(autouse=True)
def clear_state():
    rl.reset()
    yield
    rl.reset()


def test_zero_window_always_allows():
    rl.record_sent("missed", "job")
    # A zero-second window means any elapsed time >= 0 is outside the window
    assert not rl.is_rate_limited("missed", "job", window_seconds=0)


def test_very_large_window_stays_limited():
    rl.record_sent("missed", "job")
    assert rl.is_rate_limited("missed", "job", window_seconds=999_999)


def test_multiple_record_calls_refresh_window():
    rl.record_sent("missed", "job")
    first_ts = rl._sent_at[("missed", "job")]
    time.sleep(0.05)
    rl.record_sent("missed", "job")
    second_ts = rl._sent_at[("missed", "job")]
    assert second_ts > first_ts


def test_time_until_allowed_zero_after_window(monkeypatch):
    rl.record_sent("missed", "job")
    future = time.time() + rl.DEFAULT_WINDOW_SECONDS + 10
    monkeypatch.setattr(
        "cronwatch.ratelimit.time",
        type("T", (), {"time": staticmethod(lambda: future)})()
    )
    result = rl.time_until_allowed("missed", "job", window_seconds=rl.DEFAULT_WINDOW_SECONDS)
    assert result is None


def test_reset_with_no_args_clears_everything():
    rl.record_sent("missed", "a")
    rl.record_sent("long_running", "b")
    rl.reset()
    assert len(rl._sent_at) == 0


def test_reset_nonexistent_key_does_not_raise():
    # Should not raise even if nothing was recorded
    rl.reset(alert_type="missed", job_name="ghost_job")


def test_is_rate_limited_empty_strings():
    # Edge: empty strings are valid keys
    assert not rl.is_rate_limited("", "")
    rl.record_sent("", "")
    assert rl.is_rate_limited("", "")
