"""Tests for cronwatch.silence — silence window management."""

import time
import pytest

from cronwatch import silence


@pytest.fixture(autouse=True)
def clear_state():
    silence.reset()
    yield
    silence.reset()


# ---------------------------------------------------------------------------
# add_window / is_silenced basics
# ---------------------------------------------------------------------------

def test_not_silenced_when_no_windows():
    assert silence.is_silenced("backup") is False


def test_silenced_within_window():
    now = time.time()
    silence.add_window("backup", now - 60, now + 60)
    assert silence.is_silenced("backup", now=now) is True


def test_not_silenced_before_window_starts():
    now = time.time()
    silence.add_window("backup", now + 100, now + 200)
    assert silence.is_silenced("backup", now=now) is False


def test_not_silenced_after_window_ends():
    now = time.time()
    silence.add_window("backup", now - 200, now - 100)
    assert silence.is_silenced("backup", now=now) is False


def test_silenced_at_exact_start():
    now = 1_000_000.0
    silence.add_window("backup", now, now + 60)
    assert silence.is_silenced("backup", now=now) is True


def test_not_silenced_at_exact_end():
    now = 1_000_000.0
    silence.add_window("backup", now - 60, now)
    assert silence.is_silenced("backup", now=now) is False


def test_multiple_windows_one_active():
    now = time.time()
    silence.add_window("backup", now - 500, now - 400)  # expired
    silence.add_window("backup", now - 10, now + 10)   # active
    assert silence.is_silenced("backup", now=now) is True


def test_different_jobs_are_independent():
    now = time.time()
    silence.add_window("backup", now - 60, now + 60)
    assert silence.is_silenced("backup", now=now) is True
    assert silence.is_silenced("report", now=now) is False


def test_invalid_window_raises():
    now = time.time()
    with pytest.raises(ValueError):
        silence.add_window("backup", now + 100, now)  # end before start


# ---------------------------------------------------------------------------
# remove_expired
# ---------------------------------------------------------------------------

def test_remove_expired_cleans_old_windows():
    now = time.time()
    silence.add_window("backup", now - 200, now - 100)
    silence.remove_expired("backup", now=now)
    assert silence.is_silenced("backup", now=now) is False


def test_remove_expired_keeps_active_windows():
    now = time.time()
    silence.add_window("backup", now - 10, now + 60)
    silence.remove_expired("backup", now=now)
    assert silence.is_silenced("backup", now=now) is True


def test_remove_expired_on_unknown_job_is_safe():
    silence.remove_expired("nonexistent")  # should not raise


# ---------------------------------------------------------------------------
# silence_summary
# ---------------------------------------------------------------------------

def test_summary_silenced_flag_true():
    now = time.time()
    silence.add_window("backup", now - 10, now + 60)
    s = silence.silence_summary("backup", now=now)
    assert s["silenced"] is True


def test_summary_window_count():
    now = time.time()
    silence.add_window("backup", now - 10, now + 60)
    silence.add_window("backup", now + 100, now + 200)
    s = silence.silence_summary("backup", now=now)
    assert s["window_count"] == 2


def test_summary_next_window_start_when_not_silenced():
    now = 1_000_000.0
    silence.add_window("backup", now + 500, now + 600)
    s = silence.silence_summary("backup", now=now)
    assert s["next_window_start"] == pytest.approx(now + 500)


def test_summary_no_next_window_when_none_scheduled():
    now = time.time()
    s = silence.silence_summary("backup", now=now)
    assert s["next_window_start"] is None
