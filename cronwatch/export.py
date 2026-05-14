"""Export metrics and history to JSON or CSV for external consumption."""

import csv
import io
import json
import time
from typing import Dict, Any, List

from cronwatch import metrics, history
from cronwatch.config import CronwatchConfig


def build_metrics_export(config: CronwatchConfig) -> Dict[str, Any]:
    """Build a dict of per-job metrics suitable for JSON export."""
    result: Dict[str, Any] = {
        "generated_at": time.time(),
        "jobs": {},
    }
    for job in config.jobs:
        name = job.name
        result["jobs"][name] = {
            "average_runtime": metrics.average_runtime(name),
            "max_runtime": metrics.max_runtime(name),
            "alert_count": metrics.alert_count(name),
            "run_count": history.run_count(name),
            "failure_rate": _failure_rate(name),
        }
    return result


def _failure_rate(job_name: str) -> float:
    """Return fraction of runs that were alerts (0.0 – 1.0)."""
    runs = history.run_count(job_name)
    if runs == 0:
        return 0.0
    alerts = metrics.alert_count(job_name)
    return round(alerts / runs, 4)


def export_json(config: CronwatchConfig) -> str:
    """Return metrics export as a JSON string."""
    payload = build_metrics_export(config)
    return json.dumps(payload, indent=2)


def export_csv(config: CronwatchConfig) -> str:
    """Return metrics export as a CSV string."""
    payload = build_metrics_export(config)
    buf = io.StringIO()
    fieldnames = [
        "job",
        "average_runtime",
        "max_runtime",
        "alert_count",
        "run_count",
        "failure_rate",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for job_name, stats in payload["jobs"].items():
        writer.writerow({"job": job_name, **stats})
    return buf.getvalue()


def get_history_rows(job_name: str) -> List[Dict[str, Any]]:
    """Return raw history records for a job as a list of dicts."""
    return [
        {
            "job": job_name,
            "started_at": r.get("started_at"),
            "finished_at": r.get("finished_at"),
            "runtime": r.get("runtime"),
        }
        for r in history.get_runs(job_name)
    ]
