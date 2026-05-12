# cronwatch

Lightweight daemon that monitors cron job execution times and alerts on missed or long-running jobs via webhook.

## Installation

```bash
pip install cronwatch
```

Or install from source:

```bash
git clone https://github.com/yourname/cronwatch && cd cronwatch && pip install .
```

## Usage

Define your monitored jobs in `cronwatch.yaml`:

```yaml
jobs:
  daily-backup:
    schedule: "0 2 * * *"
    timeout: 300          # alert if running longer than 5 minutes
    grace: 60             # allow 60s delay before marking as missed
    webhook: "https://hooks.slack.com/services/your/webhook/url"

  hourly-sync:
    schedule: "0 * * * *"
    timeout: 120
    webhook: "https://hooks.slack.com/services/your/webhook/url"
```

Start the daemon:

```bash
cronwatch start --config cronwatch.yaml
```

Notify cronwatch when a job begins and ends by wrapping your cron commands:

```bash
# In your crontab
0 2 * * * cronwatch ping daily-backup -- /usr/local/bin/backup.sh
```

Check daemon status:

```bash
cronwatch status
```

## How It Works

cronwatch tracks expected job start times based on their cron schedules. If a job does not check in within the grace period, or exceeds its timeout, cronwatch fires a POST request to the configured webhook with a JSON payload describing the alert.

## License

MIT