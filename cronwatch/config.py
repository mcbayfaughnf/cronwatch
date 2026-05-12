"""Configuration loader for cronwatch."""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    timeout: int = 3600  # seconds
    grace_period: int = 60  # seconds allowed past expected run time
    webhook_url: Optional[str] = None


@dataclass
class CronwatchConfig:
    webhook_url: Optional[str] = None
    check_interval: int = 60  # seconds between checks
    log_level: str = "INFO"
    jobs: List[JobConfig] = field(default_factory=list)


def load_config(path: str) -> CronwatchConfig:
    """Load and parse a YAML config file into a CronwatchConfig."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError("Config file is empty or invalid YAML.")

    jobs = [
        JobConfig(
            name=j["name"],
            schedule=j["schedule"],
            timeout=j.get("timeout", 3600),
            grace_period=j.get("grace_period", 60),
            webhook_url=j.get("webhook_url"),
        )
        for j in raw.get("jobs", [])
    ]

    return CronwatchConfig(
        webhook_url=raw.get("webhook_url"),
        check_interval=raw.get("check_interval", 60),
        log_level=raw.get("log_level", "INFO"),
        jobs=jobs,
    )
