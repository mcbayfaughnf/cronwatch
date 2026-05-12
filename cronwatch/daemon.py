"""Main daemon loop for cronwatch."""

import logging
import signal
import time

from cronwatch.alerts import send_alert
from cronwatch.checker import check_jobs, dispatch_alerts
from cronwatch.config import CronwatchConfig, load_config
from cronwatch.tracker import Tracker

logger = logging.getLogger(__name__)

_running = True


def _handle_signal(signum, frame):
    global _running
    logger.info("Received signal %s, shutting down...", signum)
    _running = False


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=getattr(logging, level.upper(), logging.INFO),
    )


def run(config_path: str) -> None:
    """Load config and run the daemon loop until interrupted."""
    config: CronwatchConfig = load_config(config_path)
    setup_logging(config.log_level)

    logger.info("Starting cronwatch daemon (poll_interval=%ss)", config.poll_interval)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    tracker = Tracker(config.jobs)

    global _running
    _running = True

    while _running:
        try:
            alerts = check_jobs(config, tracker)
            dispatch_alerts(alerts, config, send_alert)
        except Exception:
            logger.exception("Unexpected error during check cycle")

        for _ in range(config.poll_interval):
            if not _running:
                break
            time.sleep(1)

    logger.info("cronwatch daemon stopped.")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="cronwatch daemon")
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
