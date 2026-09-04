from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from creator_ops.web import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    DashboardAuth,
    create_server,
)


PASSWORD = "correct horse battery staple"


class DashboardAuthUnitTests(unittest.TestCase):
    def test_auth_disabled_without_password(self) -> None:
        auth = DashboardAuth(None)
        self.assertFalse(auth.enabled)
        self.assertIsNotNone(auth.get(None))

    def test_short_password_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DashboardAuth("too-short")

    def test_password_session_and_logout(self) -> None:
        auth = DashboardAuth(PASSWORD)
        self.assertIsNone(auth.authenticate("wrong", "127.0.0.1"))
        session = auth.authenticate(PASSWORD, "127.0.0.1")
        self.assertIsNotNone(session)
        assert session is not None
        self.assertEqual(auth.get(session.token), session)
        auth.logout(session.token)
        self.assertIsNone(auth.get(session.token))

    def test_bad_logins_are_limited(self) -> None:
        auth = DashboardAuth(PASSWORD)
        for _ in range(6):
            self.assertIsNone(auth.authenticate("wrong", "example-client"))
        self.assertFalse(auth.login_allowed("example-client"))


class DashboardAuthHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tempdir.name) / "review.db"
        self.server = create_server(
            self.database_path,
            port=0,
            asset_root=Path(self.tempdir.name),
            auth_password=PASSWORD,
        )
        self.server.RequestHandlerClass.service.ensure_date(date(2026, 9, 5))
        self.content_id = self.server.RequestHandlerClass.service.cards(
            date(2026, 9, 5)
        )[0]["content_id"]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tempdir.cleanup()

    def _authenticated_opener(self) -> tuple[object, dict[str, str]]:
        jar = CookieJar()
        opener = build_opener(HTTPCookieProcessor(jar))
        request = Request(
            f"{self.base}/login",
            data=urlencode({"password": PASSWORD}).encode("ascii"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with opener.open(request, timeout=5) as response:
            self.assertEqual(response.status, 200)
        cookies = {cookie.name: cookie.value for cookie in jar}
        return opener, cookies

    def test_review_api_requires_login(self) -> None:
        with self.assertRaises(HTTPError) as raised:
            urlopen(f"{self.base}/api/reviews?date=2026-09-05", timeout=5)
        self.assertEqual(raised.exception.code, 401)
        self.assertEqual(
            json.load(raised.exception),
            {"error": "authentication_required"},
        )

    def test_wrong_password_returns_401(self) -> None:
        request = Request(
            f"{self.base}/login",
            data=urlencode({"password": "definitely-wrong"}).encode("ascii"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=5)
        self.assertEqual(raised.exception.code, 401)

    def test_correct_login_sets_session_and_csrf_cookies(self) -> None:
        opener, cookies = self._authenticated_opener()
        self.assertTrue(cookies[SESSION_COOKIE])
        self.assertTrue(cookies[CSRF_COOKIE])
        with opener.open(
            f"{self.base}/api/reviews?date=2026-09-05", timeout=5
        ) as response:
            payload = json.load(response)
        self.assertEqual(len(payload["cards"]), 2)

    def test_approval_requires_valid_csrf(self) -> None:
        opener, cookies = self._authenticated_opener()
        request = Request(
            f"{self.base}/api/reviews/{self.content_id}/approve",
            data=b"",
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            opener.open(request, timeout=5)
        self.assertEqual(raised.exception.code, 403)
        self.assertEqual(json.load(raised.exception), {"error": "csrf_failed"})

        authorized = Request(
            f"{self.base}/api/reviews/{self.content_id}/approve",
            data=b"",
            headers={"X-CSRF-Token": cookies[CSRF_COOKIE]},
            method="POST",
        )
        with opener.open(authorized, timeout=5) as response:
            payload = json.load(response)
        self.assertEqual(payload["status"], "SCHEDULED")
        publication = self.server.RequestHandlerClass.service.pipeline.db.one(
            "SELECT provider, external_id, external_url FROM publications WHERE content_id = ?",
            (self.content_id,),
        )
        self.assertEqual(publication["provider"], "mock-draft")
        self.assertIsNone(publication["external_id"])
        self.assertIsNone(publication["external_url"])

    def test_health_is_public_and_reports_auth_mode(self) -> None:
        with urlopen(f"{self.base}/api/health", timeout=5) as response:
            payload = json.load(response)
        self.assertEqual(payload, {"status": "ok", "mode": "local-mock", "auth": True})


if __name__ == "__main__":
    unittest.main()
