from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from creator_ops.cli import build_pipeline
from creator_ops.dm_health import bot_health_snapshot
from creator_ops.instagram_dm import InstagramDMService
from creator_ops.instagram_dm_provider import InstagramDMProviderError
from creator_ops.web import create_server


class HealthProvider:
    auto_reply_enabled = True

    def __init__(self) -> None:
        self.fail_mara = False

    def readiness(self) -> dict[str, object]:
        return {
            "provider": "test-meta",
            "auto_reply_enabled": True,
            "webhook_ready": False,
            "personas": {
                slug: {"configured": True, "read_ready": True, "write_ready": True}
                for slug in ("leona-voss", "mara-field")
            },
        }

    def poll(self, persona: str) -> list[dict[str, object]]:
        if persona == "mara-field" and self.fail_mara:
            raise InstagramDMProviderError("meta_read_unavailable")
        return []

    def send_message(self, persona: str, recipient_id: str, text: str) -> str:
        return "test-provider-message-id"


class DMBotHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pipeline = build_pipeline(self.root / "review.db")
        self.pipeline.initialize()
        self.provider = HealthProvider()
        self.service = InstagramDMService(self.pipeline.db, provider=self.provider)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_health_keeps_personas_and_last_error_separate(self) -> None:
        self.provider.fail_mara = True
        self.service.sync_provider()
        snapshot = bot_health_snapshot(self.service)
        personas = {item["persona"]: item for item in snapshot["personas"]}

        self.assertEqual(snapshot["bot_online"], "WEB_RUNTIME_ONLINE")
        self.assertEqual(snapshot["provider"]["status"], "ERROR")
        self.assertEqual(personas["leona-voss"]["sync_status"], "SYNCED")
        self.assertEqual(personas["mara-field"]["sync_status"], "ERROR")
        self.assertEqual(snapshot["last_error"]["persona"], "mara-field")
        self.assertEqual(snapshot["last_error"]["code"], "meta_read_unavailable")
        self.assertEqual(snapshot["last_action"]["action"], "PROVIDER_SYNC")
        self.assertEqual(snapshot["worker"]["mode"], "INLINE_WEBHOOK_AND_ON_DEMAND")
        self.assertFalse(snapshot["worker"]["dedicated_worker"])
        self.assertNotIn("test-provider-message-id", json.dumps(snapshot))

    def test_health_reports_real_sent_message_and_outbox_counts(self) -> None:
        self.service.ingest(
            {
                "provider": "instagram-meta-graph",
                "event_id": "health-inbound-1",
                "message_id": "health-inbound-1",
                "conversation_id": "health-conversation-1",
                "sender_id": "health-test-sender",
                "target_persona": "leona-voss",
                "text": "Hallo Leona",
                "received_at": datetime.now(UTC).isoformat(),
            },
            provider_verified=True,
            auto_process=True,
        )
        snapshot = bot_health_snapshot(self.service)
        self.assertEqual(snapshot["jobs"]["active"], 0)
        self.assertEqual(snapshot["jobs"]["retry"], 0)
        self.assertEqual(snapshot["jobs"]["blocked"], 0)
        self.assertEqual(snapshot["last_successful_message"]["persona"], "leona-voss")
        self.assertEqual(snapshot["last_successful_message"]["status"], "SENT")
        self.assertEqual(snapshot["last_action"]["action"], "DISPATCH_REPLY")

    def test_legacy_free_text_error_is_not_exposed(self) -> None:
        self.provider.fail_mara = True
        self.service.sync_provider("mara-field")
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE instagram_dm_provider_sync SET last_error=? WHERE status='ERROR'",
                ("Bearer sample-only-value",),
            )
        snapshot = bot_health_snapshot(self.service)
        mara = next(item for item in snapshot["personas"] if item["persona"] == "mara-field")
        self.assertEqual(mara["last_sync_error"], "redacted_error")
        self.assertNotIn("sample-only-value", json.dumps(snapshot))

    def test_health_http_uses_bound_provider_without_external_request(self) -> None:
        server = create_server(
            self.root / "http.db", host="127.0.0.1", port=0, asset_root=self.root,
            instagram_dm_provider=self.provider,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/api/instagram-dm/health",
                timeout=5,
            ) as response:
                snapshot = json.load(response)
            self.assertEqual(snapshot["provider"]["name"], "test-meta")
            self.assertEqual(snapshot["database"], "ok")
            self.assertEqual(snapshot["queue"], "DB_OUTBOX_READABLE")
            self.assertEqual(snapshot["provider"]["status"], "UNKNOWN")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
