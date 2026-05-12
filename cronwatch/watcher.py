"""Tail and process a cron log file, updating tracker state in real time."""

import logging
import os
import time
from typing import Optional

from cronwatch.logparser import process_line
from cronwatch.tracker import Tracker

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 0.5  # seconds between read attempts


class LogWatcher:
    """Follow a log file and feed new lines into the tracker.

    Handles log rotation by detecting when the file inode changes or its
    size shrinks, then reopening from the beginning.
    """

    def __init__(self, path: str, tracker: Tracker, poll_interval: float = _POLL_INTERVAL) -> None:
        self.path = path
        self.tracker = tracker
        self.poll_interval = poll_interval
        self._file = None
        self._inode: Optional[int] = None
        self._running = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open(self) -> None:
        """Open (or reopen) the log file and record its inode."""
        if self._file:
            self._file.close()
        self._file = open(self.path, "r")  # noqa: WPS515
        stat = os.stat(self.path)
        self._inode = stat.st_ino
        logger.debug("Opened log file %s (inode %d)", self.path, self._inode)

    def _rotated(self) -> bool:
        """Return True if the file has been rotated since last open."""
        try:
            stat = os.stat(self.path)
        except FileNotFoundError:
            return True
        if stat.st_ino != self._inode:
            return True
        # Detect truncation
        if self._file and stat.st_size < self._file.tell():
            return True
        return False

    def _process_available_lines(self) -> None:
        """Read and process all lines currently available."""
        for raw_line in self._file:
            line = raw_line.rstrip("\n")
            if line:
                process_line(line, self.tracker)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Perform one poll cycle (open if needed, read lines, handle rotation)."""
        if self._file is None:
            try:
                self._open()
            except FileNotFoundError:
                logger.warning("Log file not found: %s", self.path)
                return

        if self._rotated():
            logger.info("Log rotation detected for %s, reopening", self.path)
            self._open()

        self._process_available_lines()

    def run(self) -> None:
        """Block and continuously tail the log file until stop() is called."""
        self._running = True
        logger.info("LogWatcher started on %s", self.path)
        while self._running:
            self.step()
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        """Signal the run loop to exit."""
        self._running = False
        if self._file:
            self._file.close()
            self._file = None
        logger.info("LogWatcher stopped")
