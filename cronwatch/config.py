"""Configuration loading for cronwatch."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    schedule: str
    max_runtime: Optional[int] = None   # seconds
    missed_after: Optional[int] = None  # seconds
    enabled: bool = True


@dataclass
class CronwatchConfig:
    webhook_url: Optional[str]
    check_interval: int
    log_path: str
    report_interval: Optional[int]
    jobs: Dict[str, JobConfig] = field(default_factory=dict)


def _parse_job(name: str, raw: dict) -> JobConfig:
    return JobConfig(
        name=name,
        schedule=raw.get("schedule", ""),
        max_runtime=raw.get("max_runtime"),
        missed_after=raw.get("missed_after"),
        enabled=raw.get("enabled", True),
    )


def load_config(path: str) -> CronwatchConfig:
    """Load and parse a YAML configuration file."""
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh)

    jobs: Dict[str, JobConfig] = {}
    for name, job_raw in (raw.get("jobs") or {}).items():
        jobs[name] = _parse_job(name, job_raw or {})

    return CronwatchConfig(
        webhook_url=raw.get("webhook_url"),
        check_interval=int(raw.get("check_interval", 60)),
        log_path=raw.get("log_path", "/var/log/cron"),
        report_interval=raw.get("report_interval"),
        jobs=jobs,
    )
