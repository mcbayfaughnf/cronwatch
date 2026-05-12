"""Tests for the cronwatch daemon loop."""

import signal
from unittest.mock import MagicMock, call, patch

import pytest

from cronwatch.daemon import run, setup_logging


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.log_level = "INFO"
    config.poll_interval = 2
    config.jobs = []
    return config


def test_setup_logging_does_not_raise():
    """setup_logging should configure logging without raising."""
    setup_logging("DEBUG")
    setup_logging("WARNING")
    setup_logging("invalid_level")  # should fall back gracefully


def test_run_calls_check_jobs_and_exits(mock_config):
    """run() should call check_jobs each cycle and stop after signal."""
    alerts = []

    with patch("cronwatch.daemon.load_config", return_value=mock_config), \
         patch("cronwatch.daemon.Tracker") as MockTracker, \
         patch("cronwatch.daemon.check_jobs", return_value=alerts) as mock_check, \
         patch("cronwatch.daemon.dispatch_alerts") as mock_dispatch, \
         patch("cronwatch.daemon.time.sleep") as mock_sleep, \
         patch("cronwatch.daemon._running", True):

        call_count = 0

        def fake_sleep(_):
            nonlocal call_count
            call_count += 1
            if call_count >= mock_config.poll_interval:
                import cronwatch.daemon as d
                d._running = False

        mock_sleep.side_effect = fake_sleep

        run("config.yaml")

        assert mock_check.called
        assert mock_dispatch.called


def test_run_handles_check_exception_gracefully(mock_config):
    """run() should log and continue if check_jobs raises."""
    with patch("cronwatch.daemon.load_config", return_value=mock_config), \
         patch("cronwatch.daemon.Tracker"), \
         patch("cronwatch.daemon.check_jobs", side_effect=RuntimeError("boom")), \
         patch("cronwatch.daemon.dispatch_alerts"), \
         patch("cronwatch.daemon.time.sleep") as mock_sleep:

        call_count = 0

        def fake_sleep(_):
            nonlocal call_count
            call_count += 1
            if call_count >= mock_config.poll_interval:
                import cronwatch.daemon as d
                d._running = False

        mock_sleep.side_effect = fake_sleep

        # Should not raise even though check_jobs raises
        run("config.yaml")


def test_run_registers_signal_handlers(mock_config):
    """run() should register SIGTERM and SIGINT handlers."""
    with patch("cronwatch.daemon.load_config", return_value=mock_config), \
         patch("cronwatch.daemon.Tracker"), \
         patch("cronwatch.daemon.check_jobs", return_value=[]), \
         patch("cronwatch.daemon.dispatch_alerts"), \
         patch("cronwatch.daemon.time.sleep") as mock_sleep, \
         patch("cronwatch.daemon.signal.signal") as mock_signal:

        def fake_sleep(_):
            import cronwatch.daemon as d
            d._running = False

        mock_sleep.side_effect = fake_sleep

        run("config.yaml")

        registered_signals = [c[0][0] for c in mock_signal.call_args_list]
        assert signal.SIGTERM in registered_signals
        assert signal.SIGINT in registered_signals
