"""No-send regression coverage for the production DM lane."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
import json
import threading
from datetime import UTC, datetime, timedelta
from email.message import Message
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from creator_ops.cli import build_pipeline
from creator_ops.database import CreatorDatabase
from creator_ops.dm_health import bot_smoke_test
from creator_ops.instagram_dm import InboundValidationError, InstagramDMService
from creator_ops.instagram_dm_provider import InstagramDMProviderError, MetaInstagramDMProvider
from creator_ops.publishing import MetaGraphError, UrllibMetaGraphTransport


class ProbeProvider:
    auto_reply_enabled = True

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.failures: list[str] = []
        self.polled: dict[str, list[dict[str, object]]] = {
            "leona-voss": [], "mara-field": [],
        }
        self.poll_failure: str | None = None

    def account_id_for(self, persona: str) -> str | None:
        return {"leona-voss": "111", "mara-field": "222"}.get(persona)

    def readiness(self) -> dict[str, object]:
        return {
            "personas": {
                slug: {"configured": True, "read_ready": True, "write_ready": True}
                for slug in self.polled
            }
        }

    def poll(self, persona: str) -> list[dict[str, object]]:
        if persona == "leona-voss" and self.poll_failure:
            raise InstagramDMProviderError(self.poll_failure)
        return self.polled[persona]

    def send_message(self, persona: str, recipient_id: str, text: str) -> str:
        self.sent.append(persona)
        if self.failures:
            raise InstagramDMProviderError(self.failures.pop(0))
        return f"receipt-{len(self.sent)}"


class ScriptedGraphWriteTransport:
    def __init__(self, failures: list[MetaGraphError], *, receipt_id: str = "receipt") -> None:
        self.failures = list(failures)
        self.receipt_id = receipt_id
        self.post_calls: list[str] = []

    def get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        raise AssertionError("write_test_must_not_read_provider")

    def post(self, path: str, data: dict[str, str]) -> dict[str, object]:
        self.post_calls.append(path)
        if self.failures:
            raise self.failures.pop(0)
        return {"message_id": f"{self.receipt_id}-{len(self.post_calls)}"}


class InstagramDMHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pipeline = build_pipeline(self.root / "review.db")
        self.pipeline.initialize()
        self.provider = ProbeProvider()
        self.service = InstagramDMService(self.pipeline.db, provider=self.provider)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def payload(persona: str = "leona-voss", suffix: str = "one") -> dict[str, object]:
        return {
            "provider": "instagram-meta-test", "event_id": f"event-{suffix}",
            "message_id": f"message-{suffix}",
            "conversation_id": f"thread-{suffix}", "sender_id": "same-user",
            "target_persona": persona, "text": "Hallo, wie geht es dir?",
            "received_at": datetime.now(UTC).isoformat(),
        }

    def test_same_sender_on_both_accounts_never_inherits_other_persona(self) -> None:
        first = self.payload("leona-voss", "leona")
        second = self.payload("mara-field", "mara")
        first["conversation_id"] = "webhook-igsid:same-user"  # legacy collision
        second["conversation_id"] = "webhook-igsid:same-user"
        self.service.ingest(first, provider_verified=True)
        with self.assertRaisesRegex(InboundValidationError, "conversation_persona_mismatch"):
            self.service.ingest(second, provider_verified=True, auto_process=True)
        self.assertEqual(self.provider.sent, [])
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 1)

    def test_both_personas_send_only_from_their_own_account(self) -> None:
        for persona in ("leona-voss", "mara-field"):
            result = self.service.ingest(
                self.payload(persona, persona), provider_verified=True, auto_process=True
            )
            self.assertEqual(result["processing"]["status"], "SENT")
        self.assertEqual(self.provider.sent, ["leona-voss", "mara-field"])
        rows = self.pipeline.db.all(
            """SELECT cr.slug FROM instagram_dm_outbox o
               JOIN instagram_dm_conversations c ON c.id=o.conversation_id
               JOIN creators cr ON cr.id=c.creator_id ORDER BY o.id"""
        )
        self.assertEqual([row["slug"] for row in rows], self.provider.sent)

    def test_replayed_message_id_for_other_persona_fails_closed(self) -> None:
        self.service.ingest(self.payload("leona-voss", "shared"), provider_verified=True)
        second = self.payload("mara-field", "other")
        second["message_id"] = "message-shared"
        with self.assertRaisesRegex(InboundValidationError, "duplicate_event_persona_mismatch"):
            self.service.ingest(second, provider_verified=True, auto_process=True)
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 1)
        self.assertEqual(self.provider.sent, [])

    def test_definite_rate_limit_retries_bounded_and_records_events(self) -> None:
        self.provider.failures = ["meta_graph_http_429", "meta_graph_http_429"]
        result = self.service.ingest(
            self.payload(), provider_verified=True, auto_process=True
        )
        self.assertEqual(result["processing"]["status"], "SENT")
        self.assertEqual(len(self.provider.sent), 3)
        row = self.pipeline.db.one("SELECT status, attempt_count FROM instagram_dm_outbox")
        self.assertEqual((row["status"], row["attempt_count"]), ("SENT", 3))
        self.assertEqual(
            self.pipeline.db.scalar(
                "SELECT COUNT(*) FROM instagram_dm_operation_events WHERE result='RETRYING'"
            ), 2,
        )
        duplicate = self.service.dispatch_reply(int(result["processing"]["outbox_id"]))
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(len(self.provider.sent), 3)

    @staticmethod
    def graph_http_error(status: int, graph_code: int | None) -> MetaGraphError:
        detail: dict[str, object] = {"message": "private-token-diagnostic-marker"}
        if graph_code is not None:
            detail["code"] = graph_code
        headers = Message()
        headers["x-fb-request-id"] = "RequestId_123456"
        response = HTTPError(
            "https://graph.instagram.com", status, "private-token-diagnostic-marker",
            headers, BytesIO(json.dumps({"error": detail}).encode()),
        )
        return UrllibMetaGraphTransport._http_error(response)

    @staticmethod
    def graph_write_provider(transport: ScriptedGraphWriteTransport) -> MetaInstagramDMProvider:
        return MetaInstagramDMProvider(
            accounts={"leona-voss": ("111", "test-token")},
            graph_version="v24.0", graph_host="graph.instagram.com",
            auto_reply_enabled=True, transport_factory=lambda persona: transport,
        )

    def test_structured_graph_throttles_retry_one_post_per_attempt(self) -> None:
        for http_status in (400, 403):
            for graph_code in (4, 17, 32, 613):
                with self.subTest(http_status=http_status, graph_code=graph_code):
                    suffix = f"graph-{http_status}-{graph_code}"
                    transport = ScriptedGraphWriteTransport([
                        self.graph_http_error(http_status, graph_code) for _ in range(2)
                    ], receipt_id=suffix)
                    service = InstagramDMService(
                        self.pipeline.db, provider=self.graph_write_provider(transport)
                    )
                    with patch("creator_ops.instagram_dm.time.sleep") as sleeper:
                        result = service.ingest(
                            self.payload("leona-voss", suffix),
                            provider_verified=True, auto_process=True,
                        )
                    outbox_id = int(result["processing"]["outbox_id"])
                    row = self.pipeline.db.one(
                        "SELECT status, attempt_count, last_error FROM instagram_dm_outbox WHERE id=?",
                        (outbox_id,),
                    )
                    events = self.pipeline.db.all(
                        "SELECT * FROM instagram_dm_operation_events WHERE job_id=? ORDER BY id",
                        (str(outbox_id),),
                    )
                    self.assertEqual(result["processing"]["status"], "SENT")
                    self.assertEqual((row["status"], row["attempt_count"], row["last_error"]), ("SENT", 3, None))
                    self.assertEqual(transport.post_calls, ["111/messages"] * 3)
                    self.assertEqual([call.args[0] for call in sleeper.call_args_list], [0.25, 0.5])
                    self.assertEqual(
                        [event["error_code"] for event in events if event["result"] == "RETRYING"],
                        ["meta_graph_rate_limited"] * 2,
                    )
                    self.assertNotIn(
                        "private-token-diagnostic-marker",
                        json.dumps([result, dict(row), *map(dict, events)]),
                    )
                    duplicate = service.dispatch_reply(outbox_id)
                    self.assertTrue(duplicate["duplicate"])
                    self.assertEqual(len(transport.post_calls), 3)

    def test_structured_graph_throttle_stops_after_three_post_attempts(self) -> None:
        transport = ScriptedGraphWriteTransport([
            self.graph_http_error(403, 613) for _ in range(3)
        ])
        service = InstagramDMService(self.pipeline.db, provider=self.graph_write_provider(transport))
        with patch("creator_ops.instagram_dm.time.sleep") as sleeper:
            result = service.ingest(self.payload(), provider_verified=True, auto_process=True)
        outbox_id = int(result["processing"]["outbox_id"])
        row = self.pipeline.db.one(
            "SELECT status, attempt_count, last_error FROM instagram_dm_outbox WHERE id=?",
            (outbox_id,),
        )
        self.assertEqual((row["status"], row["attempt_count"], row["last_error"]),
                         ("FAILED", 3, "meta_graph_rate_limited_retry_exhausted"))
        self.assertEqual(transport.post_calls, ["111/messages"] * 3)
        self.assertEqual([call.args[0] for call in sleeper.call_args_list], [0.25, 0.5])
        self.assertTrue(service.dispatch_reply(outbox_id)["duplicate"])
        self.assertEqual(len(transport.post_calls), 3)

    def test_http_400_without_graph_throttle_code_is_permanent_and_secret_free(self) -> None:
        transport = ScriptedGraphWriteTransport([self.graph_http_error(400, None)])
        service = InstagramDMService(self.pipeline.db, provider=self.graph_write_provider(transport))
        with patch("creator_ops.instagram_dm.time.sleep") as sleeper:
            result = service.ingest(self.payload(), provider_verified=True, auto_process=True)
        outbox_id = int(result["processing"]["outbox_id"])
        row = self.pipeline.db.one(
            "SELECT status, attempt_count, last_error FROM instagram_dm_outbox WHERE id=?",
            (outbox_id,),
        )
        events = self.pipeline.db.all(
            "SELECT * FROM instagram_dm_operation_events WHERE job_id=? ORDER BY id",
            (str(outbox_id),),
        )
        self.assertEqual((row["status"], row["attempt_count"], row["last_error"]),
                         ("FAILED", 1, "meta_graph_http_400"))
        self.assertEqual(transport.post_calls, ["111/messages"])
        sleeper.assert_not_called()
        self.assertNotIn(
            "private-token-diagnostic-marker",
            json.dumps([result, dict(row), *map(dict, events)]),
        )

    def test_uncertain_server_error_reconciles_without_retry(self) -> None:
        self.provider.failures = ["meta_graph_http_503"]
        result = self.service.ingest(
            self.payload(), provider_verified=True, auto_process=True
        )
        self.assertEqual(result["processing"]["status"], "RECONCILE_REQUIRED")
        self.service.dispatch_reply(int(result["processing"]["outbox_id"]))
        self.assertEqual(self.provider.sent, ["leona-voss"])

    def test_permanent_provider_error_is_failed_without_retry(self) -> None:
        self.provider.failures = ["meta_graph_http_400"]
        result = self.service.ingest(
            self.payload(), provider_verified=True, auto_process=True
        )
        self.assertEqual(result["processing"]["status"], "FAILED")
        self.assertEqual(self.provider.sent, ["leona-voss"])

    def test_one_personas_provider_sync_failure_does_not_block_other(self) -> None:
        self.provider.poll_failure = "meta_graph_http_503"
        self.provider.polled["mara-field"] = [self.payload("mara-field", "mara")]
        result = self.service.sync_provider()
        self.assertEqual(result["personas"]["leona-voss"]["status"], "ERROR")
        self.assertEqual(result["personas"]["mara-field"]["status"], "SYNCED")
        self.assertEqual(self.provider.sent, ["mara-field"])

    def test_restart_resumes_only_known_429_rejection(self) -> None:
        inbound = self.service.ingest(self.payload(), provider_verified=True)
        drafted = self.service.queue_reply(int(inbound["event_id"]))
        self.service.approve_reply(int(drafted["outbox_id"]))
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """UPDATE instagram_dm_outbox SET status='RETRYING',
                   last_error='meta_graph_http_429', attempt_count=1 WHERE id=?""",
                (drafted["outbox_id"],),
            )
        restarted = InstagramDMService(self.pipeline.db, provider=self.provider)
        sent = restarted.dispatch_reply(int(drafted["outbox_id"]))
        self.assertEqual(sent["status"], "SENT")
        self.assertEqual(self.provider.sent, ["leona-voss"])

    def test_restart_never_resends_stale_in_flight_claim(self) -> None:
        inbound = self.service.ingest(self.payload(), provider_verified=True)
        drafted = self.service.queue_reply(int(inbound["event_id"]))
        self.service.approve_reply(int(drafted["outbox_id"]))
        stale = (datetime.now(UTC) - timedelta(minutes=3)).isoformat()
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE instagram_dm_outbox SET status='SEND_PENDING', updated_at=? WHERE id=?",
                (stale, drafted["outbox_id"]),
            )
        restarted = InstagramDMService(self.pipeline.db, provider=self.provider)
        result = restarted.dispatch_reply(int(drafted["outbox_id"]))
        self.assertEqual(result["status"], "RECONCILE_REQUIRED")
        self.assertEqual(self.provider.sent, [])

    def test_stale_claim_cannot_overwrite_concurrent_sent_receipt(self) -> None:
        inbound = self.service.ingest(self.payload(), provider_verified=True)
        drafted = self.service.queue_reply(int(inbound["event_id"]))
        self.service.approve_reply(int(drafted["outbox_id"]))
        outbox_id = int(drafted["outbox_id"])
        stale = (datetime.now(UTC) - timedelta(minutes=3)).isoformat()
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE instagram_dm_outbox SET status='SEND_PENDING', updated_at=? WHERE id=?",
                (stale, outbox_id),
            )

        original_one = self.pipeline.db.one
        injected = False

        def complete_after_stale_read(sql: str, parameters: tuple = ()):
            nonlocal injected
            row = original_one(sql, parameters)
            if not injected and "SELECT o.*, c.external_user_id" in sql:
                injected = True
                now = datetime.now(UTC).isoformat()
                with self.pipeline.db.transaction() as connection:
                    connection.execute(
                        """UPDATE instagram_dm_outbox
                           SET status='SENT', provider_message_id='concurrent-receipt',
                               sent_at=?, updated_at=? WHERE id=?""",
                        (now, now, outbox_id),
                    )
            return row

        with patch.object(self.pipeline.db, "one", side_effect=complete_after_stale_read):
            result = self.service.dispatch_reply(outbox_id)

        persisted = original_one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,))
        self.assertTrue(injected)
        self.assertEqual(result["status"], "SENT")
        self.assertEqual(result["reason"], "reply_dispatch_state_changed")
        self.assertEqual(persisted["status"], "SENT")
        self.assertEqual(persisted["provider_message_id"], "concurrent-receipt")
        self.assertEqual(self.provider.sent, [])

    def test_database_failure_occurs_before_any_send(self) -> None:
        unavailable = CreatorDatabase(self.root / "unavailable.db")
        unavailable.path.mkdir()  # SQLite cannot open a directory as a DB.
        service = InstagramDMService(unavailable, provider=self.provider)
        with self.assertRaises(sqlite3.Error):
            service.ingest(self.payload(), provider_verified=True, auto_process=True)
        self.assertEqual(self.provider.sent, [])

    def test_smoke_reads_both_accounts_and_db_without_ingest_or_send(self) -> None:
        self.provider.polled["leona-voss"] = [self.payload()]
        report = bot_smoke_test(self.service)
        self.assertEqual(report["database"], "OK")
        self.assertEqual(report["foreign_key_errors"], 0)
        self.assertEqual(report["personas"]["leona-voss"]["messages_visible"], 1)
        self.assertEqual(report["personas"]["mara-field"]["provider_probe"], "REACHABLE")
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 0)
        self.assertEqual(self.provider.sent, [])

    def test_graph_http_diagnostics_keep_only_safe_codes_and_request_id(self) -> None:
        headers = Message()
        headers["x-fb-request-id"] = "RequestId_123456"
        raw = json.dumps({"error": {
            "code": 4, "error_subcode": 2207001,
            "message": "private token sample-secret-should-not-survive",
        }}).encode()
        error = HTTPError("https://graph.instagram.com", 429, "limited", headers, BytesIO(raw))
        diagnostic = UrllibMetaGraphTransport._http_error(error)
        self.assertEqual(str(diagnostic), "meta_graph_http_429")
        self.assertEqual((diagnostic.http_status, diagnostic.graph_code, diagnostic.graph_subcode), (429, 4, 2207001))
        self.assertEqual(diagnostic.request_id, "RequestId_123456")
        self.assertNotIn("sample-secret", repr(diagnostic))

    def test_concurrent_duplicate_dispatch_does_not_send_twice(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        class BlockingProvider(ProbeProvider):
            def send_message(self, persona: str, recipient_id: str, text: str) -> str:
                self.sent.append(persona)
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("test_release_missing")
                return "receipt-once"

        provider = BlockingProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        inbound = service.ingest(self.payload(), provider_verified=True)
        queued = service.queue_reply(int(inbound["event_id"]))
        service.approve_reply(int(queued["outbox_id"]))
        outcomes: list[dict[str, object]] = []
        thread = threading.Thread(
            target=lambda: outcomes.append(service.dispatch_reply(int(queued["outbox_id"]))),
            daemon=True,
        )
        thread.start()
        self.assertTrue(entered.wait(5))
        duplicate = service.dispatch_reply(int(queued["outbox_id"]))
        self.assertEqual(duplicate["reason"], "reply_dispatch_in_flight")
        self.assertTrue(duplicate["duplicate"])
        release.set()
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(outcomes[0]["status"], "SENT")
        self.assertEqual(provider.sent, ["leona-voss"])

    def test_unexpected_provider_write_is_uncertain_not_retried(self) -> None:
        class CrashingProvider(ProbeProvider):
            def send_message(self, persona: str, recipient_id: str, text: str) -> str:
                self.sent.append(persona)
                raise RuntimeError("opaque provider failure")

        provider = CrashingProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        result = service.ingest(self.payload(), provider_verified=True, auto_process=True)
        self.assertEqual(result["processing"]["status"], "RECONCILE_REQUIRED")
        service.dispatch_reply(int(result["processing"]["outbox_id"]))
        self.assertEqual(provider.sent, ["leona-voss"])
        event = self.pipeline.db.one(
            "SELECT error_code, error_summary FROM instagram_dm_operation_events ORDER BY id DESC LIMIT 1"
        )
        self.assertEqual(event["error_code"], "provider_write_exception_uncertain")
        self.assertNotIn("opaque", str(dict(event)))


if __name__ == "__main__":
    unittest.main()
