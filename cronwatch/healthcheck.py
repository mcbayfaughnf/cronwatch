"""HTTP healthcheck endpoint for cronwatch daemon."""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from cronwatch.tracker import Tracker

logger = logging.getLogger(__name__)


def _build_status(tracker: Tracker) -> dict:
    """Build a status dict summarising all tracked jobs."""
    jobs = {}
    for name in tracker.job_configs:
        state = tracker.state.get(name)
        jobs[name] = {
            "running": tracker.is_running(name),
            "last_finished": state.last_finished.isoformat() if state and state.last_finished else None,
            "last_started": state.last_started.isoformat() if state and state.last_started else None,
        }
    return {"status": "ok", "jobs": jobs}


def _make_handler(tracker: Tracker):
    """Return a request handler class bound to *tracker*."""

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/health"):
                self.send_response(404)
                self.end_headers()
                return
            payload = json.dumps(_build_status(tracker), indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):  # silence default stderr logging
            logger.debug("healthcheck: " + fmt, *args)

    return HealthHandler


class HealthcheckServer:
    """Tiny HTTP server that exposes a /health endpoint in a background thread."""

    def __init__(self, tracker: Tracker, host: str = "127.0.0.1", port: int = 8080):
        self.tracker = tracker
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        handler = _make_handler(self.tracker)
        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Healthcheck server listening on %s:%s", self.host, self.port)

    def stop(self):
        if self._server:
            self._server.shutdown()
            logger.info("Healthcheck server stopped")
