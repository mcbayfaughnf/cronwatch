"""Edge case tests for cronwatch.baseline."""

import time
import pytest
from cronwatch import history
from cronwatch.baseline import (
    baseline_range,
    is_within_baseline,
    baseline_summary,
    MIN_SAMPLES,
)


@pytest.fixture(autouse=True)
def clear_history():
    history.reset()
    yield
    history.reset()


def _add(job, runtimes):
    ts = time.time()
    for i, rt in enumerate(runtimes):
        history.record_run(job, ts + i * 60, rt)


def test_baseline_range_excludes_none_runtimes():
    """Runs with None runtime should not contribute to baseline."""
    ts = time.time()
    for i in range(MIN_SAMPLES):
        history.record_run("job", ts + i * 60, None)
    # All runtimes are None, so no valid samples
    assert baseline_range("job") is None


def test_lower_bound_never_negative():
    """Lower bound should be clamped to 0 even for very small means."""
    _add("tiny", [0.1, 0.2, 0.15, 0.1, 0.2, 0.12, 0.18])
    lower, upper = baseline_range("tiny")
    assert lower >= 0.0


def test_exactly_at_lower_bound_is_within():
    _add("job", [20.0] * 10)
    lower, upper = baseline_range("job")
    assert is_within_baseline("job", lower) is True


def test_exactly_at_upper_bound_is_within():
    _add("job", [20.0] * 10)
    lower, upper = baseline_range("job")
    assert is_within_baseline("job", upper) is True


def test_just_above_upper_bound_is_outside():
    _add("job", [10.0, 12.0, 11.0, 10.5, 11.5, 10.8, 11.2])
    lower, upper = baseline_range("job")
    assert is_within_baseline("job", upper + 0.001) is False


def test_summary_rounds_to_three_decimals():
    _add("job", [10.123456, 10.234567, 10.0, 10.1, 10.2])
    summary = baseline_summary("job")
    if summary["has_baseline"]:
        # Values should be rounded to 3 decimal places
        for key in ("lower", "upper"):
            val = summary[key]
            assert val == round(val, 3)


def test_zero_runtime_handled_gracefully():
    _add("instant", [0.0] * MIN_SAMPLES)
    result = baseline_range("instant")
    assert result is not None
    lower, upper = result
    assert lower == 0.0
    assert upper == 0.0
