from __future__ import annotations

import argparse
import hmac
import html
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from .asset_import import LocalAssetImportService
from .cli import ROOT, build_pipeline
from .review import ReviewDashboardService


STATIC_ROOT = ROOT / "dashboard"
SESSION_COOKIE = "creator_ops_session"
CSRF_COOKIE = "creator_ops_csrf"
SESSION_TTL_SECONDS = 12 * 60 * 60
MAX_LOGIN_FAILURES = 6
LOGIN_WINDOW_SECONDS = 5 * 60
MIN_PASSWORD_LENGTH = 12


@dataclass(frozen=True)
class Session:
    token: str
    csrf: str
    expires_at: float


class DashboardAuth:
    """Small in-memory owner login for the optional remote dashboard mode."""

    def __init__(self, password: str | None) -> None:
        normalized = password or None
        if normalized is not None and len(normalized) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"CREATOR_OPS_PASSWORD must contain at least {MIN_PASSWORD_LENGTH} characters")
        self._password = normalized
        self._sessions: dict[str, Session] = {}
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._password is not None

    def _prune(self, now: float) -> None:
        self._sessions = {
            token: session
            for token, session in self._sessions.items()
            if session.expires_at > now
        }
        for key, values in list(self._failures.items()):
            recent = [value for value in values if now - value < LOGIN_WINDOW_SECONDS]
            if recent:
                self._failures[key] = recent
            else:
                self._failures.pop(key, None)

    def login_allowed(self, client_key: str) -> bool:
        if not self.enabled:
            return True
        now = time.time()
        with self._lock:
            self._prune(now)
            return len(self._failures.get(client_key, [])) < MAX_LOGIN_FAILURES

    def authenticate(self, password: str, client_key: str) -> Session | None:
        if not self.enabled:
            return Session("", "", time.time() + SESSION_TTL_SECONDS)
        now = time.time()
        with self._lock:
            self._prune(now)
            failures = self._failures.get(client_key, [])
            if len(failures) >= MAX_LOGIN_FAILURES:
                return None
            if not hmac.compare_digest(password, self._password or ""):
                failures.append(now)
                self._failures[client_key] = failures
                return None
            self._failures.pop(client_key, None)
            session = Session(
                token=secrets.token_urlsafe(32),
                csrf=secrets.token_urlsafe(24),
                expires_at=now + SESSION_TTL_SECONDS,
            )
            self._sessions[session.token] = session
            return session

    def get(self, token: str | None) -> Session | None:
        if not self.enabled:
            return Session("", "", time.time() + SESSION_TTL_SECONDS)
        if not token:
            return None
        now = time.time()
        with self._lock:
            self._prune(now)
            return self._sessions.get(token)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)


class DashboardHandler(BaseHTTPRequestHandler):
    service: ReviewDashboardService
    asset_root: Path = ROOT
    auth: DashboardAuth = DashboardAuth(None)

    def _is_https(self) -> bool:
        return self.headers.get("X-Forwarded-Proto", "").lower() == "https"

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'self'",
        )
        if self._is_https():
            self.send_header("Strict-Transport-Security", "max-age=31536000")

    def _cookies(self) -> SimpleCookie:
        cookie = SimpleCookie()
        raw = self.headers.get("Cookie")
        if raw:
            try:
                cookie.load(raw)
            except Exception:
                pass
        return cookie

    def _session_token(self) -> str | None:
        item = self._cookies().get(SESSION_COOKIE)
        return item.value if item else None

    def _session(self) -> Session | None:
        return self.auth.get(self._session_token())

    def _client_key(self) -> str:
        return self.headers.get("CF-Connecting-IP") or self.client_address[0]

    def _send_cookie(
        self,
        name: str,
        value: str,
        *,
        http_only: bool,
        max_age: int = SESSION_TTL_SECONDS,
    ) -> None:
        parts = [f"{name}={value}", "Path=/", f"Max-Age={max_age}", "SameSite=Strict"]
        if http_only:
            parts.append("HttpOnly")
        if self._is_https():
            parts.append("Secure")
        self.send_header("Set-Cookie", "; ".join(parts))

    def _clear_auth_cookies(self) -> None:
        for name in (SESSION_COOKIE, CSRF_COOKIE):
            parts = [f"{name}=", "Path=/", "Max-Age=0", "SameSite=Strict"]
            if name == SESSION_COOKIE:
                parts.append("HttpOnly")
            if self._is_https():
                parts.append("Secure")
            self.send_header("Set-Cookie", "; ".join(parts))

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _html(self, text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, target: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", target)
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()

    def _file(self, name: str, content_type: str) -> None:
        body = (STATIC_ROOT / name).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _binary(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "private, max-age=300")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _tomorrow() -> str:
        return (datetime.now(ZoneInfo("Europe/Berlin")).date() + timedelta(days=1)).isoformat()

    def _login_page(self, error: str = "") -> str:
        message = (
            f'<p class="error">{html.escape(error)}</p>'
            if error
            else '<p class="hint">Privater Zugriff</p>'
        )
        return f"""<!doctype html><html lang="de"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Creator Ops Login</title><style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:linear-gradient(145deg,#f5ead7,#f7f3eb 45%,#e9efe9);color:#25231f}}
main{{width:min(92vw,430px);background:rgba(255,255,255,.92);padding:34px;border:1px solid rgba(90,70,45,.12);border-radius:24px;box-shadow:0 24px 70px rgba(80,60,30,.12)}}
.kicker{{margin:0 0 6px;color:#8b6b43;font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:.75rem}}h1{{margin:.15rem 0 .4rem;font-size:2rem}}
.hint{{color:#6e675d;margin:.2rem 0 1.5rem}}.error{{color:#9b2c2c;margin:.2rem 0 1.5rem;font-weight:650}}
label{{display:block;margin-bottom:8px;font-weight:700}}input{{width:100%;padding:14px 15px;border:1px solid #cfc5b6;border-radius:12px;font:inherit;background:#fff}}
button{{width:100%;margin-top:16px;padding:14px 16px;border:0;border-radius:12px;font:inherit;font-weight:800;cursor:pointer;background:#2e4035;color:#fff}}
small{{display:block;margin-top:18px;color:#81796e;line-height:1.45}}
</style></head><body><main><p class="kicker">Private Studio</p><h1>Creator Ops</h1>{message}
<form method="post" action="/login"><label for="password">Passwort</label>
<input id="password" name="password" type="password" autocomplete="current-password" required autofocus>
<button type="submit">Anmelden</button></form>
<small>Das Passwort wird nicht in GitHub oder SQLite gespeichert.</small></main></body></html>"""

    def _auth_gate(self, *, api: bool = False) -> Session | None:
        if not self.auth.enabled:
            return self._session()
        session = self._session()
        if session is not None:
            return session
        if api:
            self._json({"error": "authentication_required"}, HTTPStatus.UNAUTHORIZED)
        else:
            self._redirect("/login")
        return None

    def _csrf_valid(self, session: Session) -> bool:
        if not self.auth.enabled:
            return True
        supplied = self.headers.get("X-CSRF-Token", "")
        item = self._cookies().get(CSRF_COOKIE)
        cookie_value = item.value if item else ""
        return (
            bool(supplied)
            and hmac.compare_digest(supplied, session.csrf)
            and hmac.compare_digest(cookie_value, session.csrf)
        )

    def _read_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 16_384:
            raise ValueError("request_too_large")
        return parse_qs(self.rfile.read(length).decode("utf-8", "replace"))

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                self._json(
                    {"status": "ok", "mode": "local-mock", "auth": self.auth.enabled}
                )
                return
            if parsed.path == "/login":
                if not self.auth.enabled or self._session() is not None:
                    self._redirect("/")
                else:
                    self._html(self._login_page())
                return

            api = parsed.path.startswith("/api/")
            if self._auth_gate(api=api) is None and self.auth.enabled:
                return

            if parsed.path == "/":
                self._file("index.html", "text/html; charset=utf-8")
            elif parsed.path == "/app.css":
                self._file("app.css", "text/css; charset=utf-8")
            elif parsed.path == "/app.js":
                self._file("app.js", "text/javascript; charset=utf-8")
            elif parsed.path in {
                "/assets/leona-voss-avatar.png",
                "/assets/mara-field-avatar.png",
            }:
                self._file(parsed.path.lstrip("/"), "image/png")
            elif parsed.path.startswith("/api/assets/") and parsed.path.endswith("/preview"):
                asset_id = int(parsed.path.split("/")[3])
                preview = LocalAssetImportService(
                    self.service.pipeline, self.asset_root
                ).preview_path(asset_id)
                if preview is None:
                    self._json({"error": "preview_not_found"}, HTTPStatus.NOT_FOUND)
                else:
                    self._binary(*preview)
            elif parsed.path == "/api/reviews":
                target = parse_qs(parsed.query).get("date", [self._tomorrow()])[0]
                cards = self.service.ensure_date(datetime.fromisoformat(target).date())
                self._json({"date": target, "cards": cards})
            elif parsed.path == "/api/session":
                self._json(
                    {
                        "authenticated": self._session() is not None,
                        "auth_required": self.auth.enabled,
                    }
                )
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
            if parsed.path == "/login":
                if not self.auth.enabled:
                    self._redirect("/")
                    return
                client_key = self._client_key()
                if not self.auth.login_allowed(client_key):
                    self._html(
                        self._login_page(
                            "Zu viele Versuche. Bitte in einigen Minuten erneut versuchen."
                        ),
                        HTTPStatus.TOO_MANY_REQUESTS,
                    )
                    return
                password = self._read_form().get("password", [""])[0]
                session = self.auth.authenticate(password, client_key)
                if session is None:
                    self._html(
                        self._login_page("Passwort nicht korrekt."),
                        HTTPStatus.UNAUTHORIZED,
                    )
                    return
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", "/")
                self.send_header("Cache-Control", "no-store")
                self._send_cookie(SESSION_COOKIE, session.token, http_only=True)
                self._send_cookie(CSRF_COOKIE, session.csrf, http_only=False)
                self._security_headers()
                self.end_headers()
                return

            session = self._auth_gate(api=True)
            if session is None and self.auth.enabled:
                return

            if parsed.path == "/logout":
                if session is not None and not self._csrf_valid(session):
                    self._json({"error": "csrf_failed"}, HTTPStatus.FORBIDDEN)
                    return
                self.auth.logout(self._session_token())
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", "/login")
                self.send_header("Cache-Control", "no-store")
                self._clear_auth_cookies()
                self._security_headers()
                self.end_headers()
                return

            if session is not None and not self._csrf_valid(session):
                self._json({"error": "csrf_failed"}, HTTPStatus.FORBIDDEN)
                return

            if len(parts) == 4 and parts[:2] == ["api", "reviews"] and parts[3] == "approve":
                content_id = int(parts[2])
                self._json(self.service.approve(content_id))
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


def create_server(
    database_path: Path,
    host: str = "127.0.0.1",
    port: int = 4180,
    asset_root: Path = ROOT,
    auth_password: str | None = None,
) -> ThreadingHTTPServer:
    pipeline = build_pipeline(database_path)
    pipeline.initialize()
    service = ReviewDashboardService(pipeline)
    handler = type(
        "BoundDashboardHandler",
        (DashboardHandler,),
        {
            "service": service,
            "asset_root": asset_root,
            "auth": DashboardAuth(auth_password),
        },
    )
    return ThreadingHTTPServer((host, port), handler)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Creator Ops local approval dashboard")
    result.add_argument("--db", type=Path, default=ROOT / "data" / "review_dashboard.db")
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", type=int, default=4180)
    return result


def main() -> int:
    args = parser().parse_args()
    password = os.environ.get("CREATOR_OPS_PASSWORD")
    server = create_server(
        args.db,
        args.host,
        args.port,
        auth_password=password,
    )
    auth_mode = "password" if password else "local-open"
    print(
        f"Creator Ops Dashboard: http://{args.host}:{server.server_port} "
        f"(auth={auth_mode})",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
