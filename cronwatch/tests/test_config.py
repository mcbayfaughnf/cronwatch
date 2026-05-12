"""Tests for the configuration loader."""

import os
import pytest
import tempfile
import yaml

from cronwatch.config import load_config, CronwatchConfig, JobConfig


SAMPLE_CONFIG = {
    "webhook_url": "https://hooks.example.com/notify",
    "check_interval": 30,
    "log_level": "DEBUG",
    "jobs": [
        {
            "name": "daily-backup",
            "schedule": "0 2 * * *",
            "timeout": 7200,
            "grace_period": 120,
        },
        {
            "name": "hourly-sync",
            "schedule": "0 * * * *",
        },
    ],
}


@pytest.fixture
def config_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        path = f.name
    yield path
    os.unlink(path)


def test_load_config_returns_cronwatch_config(config_file):
    cfg = load_config(config_file)
    assert isinstance(cfg, CronwatchConfig)


def test_load_config_top_level_fields(config_file):
    cfg = load_config(config_file)
    assert cfg.webhook_url == "https://hooks.example.com/notify"
    assert cfg.check_interval == 30
    assert cfg.log_level == "DEBUG"


def test_load_config_jobs(config_file):
    cfg = load_config(config_file)
    assert len(cfg.jobs) == 2
    assert isinstance(cfg.jobs[0], JobConfig)
    assert cfg.jobs[0].name == "daily-backup"
    assert cfg.jobs[0].timeout == 7200
    assert cfg.jobs[0].grace_period == 120


def test_load_config_job_defaults(config_file):
    cfg = load_config(config_file)
    hourly = cfg.jobs[1]
    assert hourly.timeout == 3600
    assert hourly.grace_period == 60
    assert hourly.webhook_url is None


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.yaml")


def test_load_config_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        path = f.name
    try:
        with pytest.raises(ValueError, match="empty or invalid"):
            load_config(path)
    finally:
        os.unlink(path)
