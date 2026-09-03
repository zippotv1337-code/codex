from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from .cli import ROOT, build_pipeline
from .review import ReviewDashboardService


STATIC_ROOT = ROOT / "dashboard"


class DashboardHandler(BaseHTTPRequestHandler):
    service: ReviewDashboardService

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, name: str, content_type: str) -> None:
        body = (STATIC_ROOT / name).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _tomorrow() -> str:
        return (datetime.now(ZoneInfo("Europe/Berlin")).date() + timedelta(days=1)).isoformat()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self._file("index.html", "text/html; charset=utf-8")
            elif parsed.path == "/app.css":
                self._file("app.css", "text/css; charset=utf-8")
            elif parsed.path == "/app.js":
                self._file("app.js", "text/javascript; charset=utf-8")
            elif parsed.path == "/api/reviews":
                target = parse_qs(parsed.query).get("date", [self._tomorrow()])[0]
                cards = self.service.ensure_date(datetime.fromisoformat(target).date())
                self._json({"date": target, "cards": cards})
            elif parsed.path == "/api/health":
                self._json({"status": "ok", "mode": "local-mock"})
            else:
                self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        except (KeyError, ValueError) as error:
            self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self._json(
                {"error": "dashboard_error", "detail": f"{type(error).__name__}: {error}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        try:
            if len(parts) == 4 and parts[:2] == ["api", "reviews"] and parts[3] == "approve":
                content_id = int(parts[2])
                result = self.service.approve(content_id)
                self._json(result)
                return
            self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        except KeyError as error:
            self._json({"error": str(error)}, HTTPStatus.NOT_FOUND)
        except ValueError as error:
            self._json({"error": str(error)}, HTTPStatus.CONFLICT)
        except Exception as error:
            self._json(
                {"error": "dashboard_error", "detail": f"{type(error).__name__}: {error}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"dashboard: {format % args}")


def create_server(database_path: Path, host: str = "127.0.0.1", port: int = 4180) -> ThreadingHTTPServer:
    pipeline = build_pipeline(database_path)
    pipeline.initialize()
    service = ReviewDashboardService(pipeline)
    handler = type("BoundDashboardHandler", (DashboardHandler,), {"service": service})
    return ThreadingHTTPServer((host, port), handler)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Creator Ops local approval dashboard")
    result.add_argument("--db", type=Path, default=ROOT / "data" / "review_dashboard.db")
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", type=int, default=4180)
    return result


def main() -> int:
    args = parser().parse_args()
    server = create_server(args.db, args.host, args.port)
    print(f"Creator Ops Dashboard: http://{args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
