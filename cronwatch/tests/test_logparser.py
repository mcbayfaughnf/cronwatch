"""Tests for cronwatch.logparser."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from cronwatch.logparser import parse_line, process_line


DT = datetime(2024, 1, 15, 10, 30, 0)


class TestParseLine:
    def test_valid_start_line(self):
        line = "[CRONWATCH] START backup 2024-01-15T10:30:00"
        result = parse_line(line)
        assert result == ("START", "backup", DT)

    def test_valid_finish_line(self):
        line = "[CRONWATCH] FINISH backup 2024-01-15T10:30:00"
        result = parse_line(line)
        assert result == ("FINISH", "backup", DT)

    def test_line_with_surrounding_text(self):
        line = "2024-01-15 INFO [CRONWATCH] START nightly-report 2024-01-15T10:30:00 done"
        result = parse_line(line)
        assert result is not None
        assert result[0] == "START"
        assert result[1] == "nightly-report"

    def test_unrelated_line_returns_none(self):
        assert parse_line("nothing to see here") is None

    def test_empty_line_returns_none(self):
        assert parse_line("") is None

    def test_partial_match_returns_none(self):
        assert parse_line("[CRONWATCH] START") is None

    def test_strips_whitespace(self):
        line = "  [CRONWATCH] FINISH sync 2024-01-15T10:30:00  "
        result = parse_line(line)
        assert result is not None
        assert result[0] == "FINISH"


class TestProcessLine:
    def _make_tracker(self, known_jobs=None):
        tracker = MagicMock()
        tracker.job_configs = {j: object() for j in (known_jobs or ["backup"])}
        return tracker

    def test_returns_false_for_unrecognised_line(self):
        tracker = self._make_tracker()
        assert process_line("garbage", tracker) is False

    def test_returns_true_for_valid_start(self):
        tracker = self._make_tracker()
        result = process_line("[CRONWATCH] START backup 2024-01-15T10:30:00", tracker)
        assert result is True

    def test_calls_mark_started_for_known_job(self):
        tracker = self._make_tracker()
        process_line("[CRONWATCH] START backup 2024-01-15T10:30:00", tracker)
        tracker.mark_started.assert_called_once_with("backup", DT)

    def test_calls_mark_finished_for_known_job(self):
        tracker = self._make_tracker()
        process_line("[CRONWATCH] FINISH backup 2024-01-15T10:30:00", tracker)
        tracker.mark_finished.assert_called_once_with("backup", DT)

    def test_does_not_call_mark_started_for_unknown_job(self):
        tracker = self._make_tracker(known_jobs=[])
        process_line("[CRONWATCH] START unknown-job 2024-01-15T10:30:00", tracker)
        tracker.mark_started.assert_not_called()

    def test_does_not_call_mark_finished_for_unknown_job(self):
        tracker = self._make_tracker(known_jobs=[])
        process_line("[CRONWATCH] FINISH unknown-job 2024-01-15T10:30:00", tracker)
        tracker.mark_finished.assert_not_called()

    def test_returns_true_even_for_unknown_job(self):
        """Line matched the pattern, so we return True regardless of job lookup."""
        tracker = self._make_tracker(known_jobs=[])
        result = process_line("[CRONWATCH] START ghost 2024-01-15T10:30:00", tracker)
        assert result is True
