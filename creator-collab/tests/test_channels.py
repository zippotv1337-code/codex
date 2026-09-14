from __future__ import annotations

import json
import base64
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from creator_ops.channel_ops import ChannelOpsService
from creator_ops.web import create_server


ROOT = Path(__file__).resolve().parents[1]


class ChannelOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "channels.json").write_text(
            (ROOT / "config" / "channels.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.service = ChannelOpsService(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_milo_has_instagram_tiktok_and_real_9_16_review_contract(self) -> None:
        snapshot = self.service.snapshot()
        self.assertEqual(snapshot["external_actions"], "NONE")
        brand = snapshot["brands"][0]
        self.assertEqual(brand["slug"], "milo-der-zug")
        self.assertIn("KI-generierte", brand["disclosure"])
        self.assertEqual({item["platform"] for item in brand["accounts"]}, {"instagram", "tiktok"})
        draft = brand["drafts"][0]
        self.assertEqual(draft["preview"]["aspect_ratio"], "9:16")
        self.assertFalse(draft["asset_ready"])
        self.assertIn("real_9_16_asset_missing", draft["direct_post_blockers"])

    def test_real_milo_asset_gets_safe_preview_url_and_mime_type(self) -> None:
        draft = self.service.snapshot()["brands"][0]["drafts"][0]
        target = self.root / draft["asset_path"]
        target.parent.mkdir(parents=True)
        target.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        ))
        refreshed = self.service.snapshot()["brands"][0]["drafts"][0]
        self.assertTrue(refreshed["asset_ready"])
        self.assertTrue(refreshed["preview"]["asset_url"].endswith("/asset"))
        preview = self.service.asset_preview("milo-der-zug", "milo-intro-001")
        self.assertIsNotNone(preview)
        self.assertEqual(preview[1], "image/png")

    def test_direct_post_is_separate_and_fails_closed_at_every_gate(self) -> None:
        with self.assertRaisesRegex(ValueError, "owner_approval_required"):
            self.service.set_upload_mode("milo-der-zug", "milo-intro-001", "DIRECT_POST")
        approved = self.service.decide("milo-der-zug", "milo-intro-001", "approve")
        self.assertEqual(approved["approval_status"], "OWNER_APPROVED")
        with self.assertRaisesRegex(ValueError, "real_9_16_asset_required"):
            self.service.set_upload_mode("milo-der-zug", "milo-intro-001", "DIRECT_POST")
        draft = self.service.set_upload_mode("milo-der-zug", "milo-intro-001", "DRAFT_UPLOAD")
        self.assertEqual(draft["upload_mode"], "DRAFT_UPLOAD")
        self.assertFalse(draft["account_connected"])

    def test_analytics_preserves_unknown_values_and_requires_real_signal(self) -> None:
        with self.assertRaisesRegex(ValueError, "at_least_one_real_metric"):
            self.service.append_analytics(
                "milo-der-zug",
                "milo-intro-001",
                {"views": None},
                source="MANUAL_OWNER",
            )
        event = self.service.append_analytics(
            "milo-der-zug",
            "milo-intro-001",
            {"views": 17, "likes": None},
            source="MANUAL_OWNER",
        )
        self.assertEqual(event["metrics"]["views"], 17)
        self.assertIsNone(event["metrics"]["likes"])
        stored = json.loads((self.root / "data" / "channel_ops.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["analytics"][0]["metrics"]["views"], 17)

    def test_error_log_sanitizes_code_and_never_executes_external_action(self) -> None:
        event = self.service.record_error(
            "milo-der-zug",
            "milo-intro-001",
            "account unavailable\nunsafe detail",
        )
        self.assertEqual(event["code"], "ACCOUNT_UNAVAILABLE_UNSAFE_DETAIL")
        self.assertEqual(self.service.snapshot()["external_actions"], "NONE")

    def test_http_dashboard_exposes_value_free_channel_and_security_status(self) -> None:
        configured = self.service.snapshot()["brands"][0]["drafts"][0]
        target = self.root / configured["asset_path"]
        target.parent.mkdir(parents=True)
        expected = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        target.write_bytes(expected)
        database = self.root / "review.db"
        server = create_server(database, port=0, asset_root=self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/channels", timeout=5) as response:
                html = response.read().decode("utf-8")
            self.assertIn("Milo der Zug", html)
            self.assertIn("Draft Upload", html)
            with urlopen(base + "/api/channels", timeout=5) as response:
                channels = json.load(response)
            self.assertEqual(channels["external_actions"], "NONE")
            asset_url = channels["brands"][0]["drafts"][0]["preview"]["asset_url"]
            with urlopen(base + asset_url, timeout=5) as response:
                self.assertEqual(response.headers.get_content_type(), "image/png")
                self.assertEqual(response.read(), expected)
            with urlopen(base + "/api/security", timeout=5) as response:
                security = json.load(response)
            self.assertFalse(security["secret_provider"]["values_exposed"])

            body = b"note=owner+approved"
            request = Request(
                base + "/api/channels/milo-der-zug/drafts/milo-intro-001/approve",
                data=body,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urlopen(request, timeout=5) as response:
                result = json.load(response)
            self.assertFalse(result["external_action"])
            self.assertEqual(result["result"]["approval_status"], "OWNER_APPROVED")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
