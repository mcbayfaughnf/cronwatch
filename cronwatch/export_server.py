"""Tiny HTTP endpoint that serves /export/json and /export/csv."""

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from cronwatch.config import CronwatchConfig
from cronwatch import export

logger = logging.getLogger(__name__)


def _make_handler(config: CronwatchConfig):
    """Return a handler class closed over *config*."""

    class ExportHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/export/json":
                body = export.export_json(config).encode()
                self._respond(200, "application/json", body)
            elif self.path == "/export/csv":
                body = export.export_csv(config).encode()
                self._respond(200, "text/csv", body)
            else:
                self._respond(404, "text/plain", b"Not Found")

        def _respond(self, status: int, content_type: str, body: bytes):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):  # silence default access log
            logger.debug("export_server: " + fmt, *args)

    return ExportHandler


class ExportServer:
    """Background HTTP server exposing metrics exports."""

    def __init__(self, config: CronwatchConfig, host: str = "127.0.0.1", port: int = 9091):
        self._config = config
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        handler = _make_handler(self._config)
        self._server = HTTPServer((self._host, self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Export server listening on %s:%d", self._host, self._port)

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server = None
        logger.info("Export server stopped")
