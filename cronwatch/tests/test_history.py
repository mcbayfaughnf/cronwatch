"""Tests for cronwatch.history module."""

import time
import pytest
import cronwatch.history as history


@pytest.fixture(autouse=True)
def clear_history():
    history.reset()
    yield
    history.reset()


def test_run_count_zero_initially():
    assert history.run_count("backup") == 0


def test_record_run_increments_count():
    history.record_run("backup", 1000.0, 1060.0)
    assert history.run_count("backup") == 1


def test_get_runs_returns_records():
    history.record_run("backup", 1000.0, 1060.0)
    runs = history.get_runs("backup")
    assert len(runs) == 1
    start, end, runtime = runs[0]
    assert start == 1000.0
    assert end == 1060.0
    assert runtime == pytest.approx(60.0)


def test_average_runtime_none_when_empty():
    assert history.average_runtime("nojob") is None


def test_average_runtime_single_run():
    history.record_run("deploy", 0.0, 90.0)
    assert history.average_runtime("deploy") == pytest.approx(90.0)


def test_average_runtime_multiple_runs():
    history.record_run("deploy", 0.0, 60.0)
    history.record_run("deploy", 200.0, 280.0)
    # runtimes: 60 and 80 -> avg 70
    assert history.average_runtime("deploy") == pytest.approx(70.0)


def test_last_runtime_none_when_empty():
    assert history.last_runtime("nojob") is None


def test_last_runtime_returns_most_recent():
    history.record_run("sync", 0.0, 30.0)
    history.record_run("sync", 100.0, 145.0)
    assert history.last_runtime("sync") == pytest.approx(45.0)


def test_last_start_returns_most_recent_start():
    history.record_run("sync", 500.0, 530.0)
    history.record_run("sync", 900.0, 940.0)
    assert history.last_start("sync") == pytest.approx(900.0)


def test_reset_specific_job():
    history.record_run("job_a", 0.0, 10.0)
    history.record_run("job_b", 0.0, 20.0)
    history.reset("job_a")
    assert history.run_count("job_a") == 0
    assert history.run_count("job_b") == 1


def test_reset_all_jobs():
    history.record_run("job_a", 0.0, 10.0)
    history.record_run("job_b", 0.0, 20.0)
    history.reset()
    assert history.run_count("job_a") == 0
    assert history.run_count("job_b") == 0


def test_max_history_cap():
    for i in range(60):
        history.record_run("heavy", float(i * 100), float(i * 100 + 10))
    assert history.run_count("heavy") == 50


def test_multiple_jobs_independent():
    history.record_run("alpha", 0.0, 5.0)
    history.record_run("beta", 0.0, 15.0)
    assert history.last_runtime("alpha") == pytest.approx(5.0)
    assert history.last_runtime("beta") == pytest.approx(15.0)
