from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from datetime import UTC, datetime, timedelta
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from creator_ops.cli import build_pipeline
from creator_ops.instagram_dm import InstagramDMService
from creator_ops.instagram_dm_provider import (
    InstagramDMProviderConnectionError,
    InstagramDMProviderError,
    MetaInstagramDMProvider,
)
from creator_ops.web import CSRF_COOKIE, create_server


PASSWORD = "test-only-correct-horse-battery-staple"


class FakeProvider:
    def __init__(
        self, *, uncertain: bool = False, auto_reply_enabled: bool = True
    ) -> None:
        self.auto_reply_enabled = auto_reply_enabled
        self.uncertain = uncertain
        self.sent: list[tuple[str, str, str]] = []
        self.polled: dict[str, list[dict[str, object]]] = {
            "leona-voss": [],
            "mara-field": [],
        }

    def readiness(self) -> dict[str, object]:
        return {
            "provider": "fake-meta",
            "webhook_ready": True,
            "auto_reply_enabled": self.auto_reply_enabled,
            "personas": {
                "leona-voss": {"configured": True},
                "mara-field": {"configured": True},
            },
        }

    def verify_challenge(self, mode: str, token: str, challenge: str) -> str:
        return challenge

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        return signature == "valid"

    def parse_webhook(self, raw_body: bytes) -> list[dict[str, object]]:
        return json.loads(raw_body)

    def poll(self, persona: str) -> list[dict[str, object]]:
        return self.polled[persona]

    def send_message(self, persona: str, recipient_id: str, text: str) -> str:
        self.sent.append((persona, recipient_id, text))
        if self.uncertain:
            raise InstagramDMProviderConnectionError("meta_graph_write_uncertain")
        return f"provider-{len(self.sent)}"

    def reconcile_message(
        self, persona: str, conversation_id: str, provider_message_id: str
    ) -> bool | None:
        return provider_message_id.startswith("provider-")


class FakeTransport:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, str]]] = []
        self.gets: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        self.gets.append((path, params))
        if path.endswith("/conversations"):
            return {"data": [{"id": "thread-1"}]}
        if path == "thread-1" and "message,created_time" in params.get("fields", ""):
            return {
                "messages": {
                    "data": [
                        {
                            "id": "msg-in-1",
                            "from": {"id": "igsid-user"},
                            "message": "Hallo Leona",
                            "created_time": datetime.now(UTC).isoformat(),
                        },
                        {"id": "own-1", "from": {"id": "1784"}, "message": "Hi"},
                    ]
                }
            }
        return {"messages": {"data": [{"id": "provider-1"}]}}

    def post(self, path: str, data: dict[str, str]) -> dict[str, object]:
        self.posts.append((path, data))
        return {"message_id": "provider-1"}


class InstagramDMP1Tests(unittest.TestCase):
    def test_poll_error_is_recorded_per_persona_without_send_or_outbox(self) -> None:
        provider = FakeProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        error = "instagram_dm_response_data_invalid"
        with patch.object(provider, "poll", side_effect=[InstagramDMProviderError(error), []]) as poll:
            result = service.sync_provider()
        self.assertEqual([call.args[0] for call in poll.call_args_list], ["leona-voss", "mara-field"])
        self.assertEqual(result["personas"]["leona-voss"], {
            "status": "ERROR", "seen": 0, "ingested": 0,
            "rejected": 0, "replies_sent": 0, "error": error,
        })
        self.assertEqual(result["personas"]["mara-field"]["status"], "SYNCED")
        self.assertFalse(result["external_action"])
        self.assertEqual(provider.sent, [])
        for table in ("instagram_dm_outbox", "instagram_dm_events", "instagram_dm_conversations"):
            self.assertEqual(self.pipeline.db.scalar(f"SELECT COUNT(*) FROM {table}"), 0)
        rows = {row["slug"]: row for row in self.pipeline.db.all(
            "SELECT c.slug, s.* FROM instagram_dm_provider_sync s "
            "JOIN creators c ON c.id=s.creator_id"
        )}
        self.assertEqual(rows["leona-voss"]["status"], "ERROR")
        self.assertEqual(rows["leona-voss"]["last_error"], error)
        self.assertIsNone(rows["leona-voss"]["last_success_at"])
        self.assertEqual(rows["leona-voss"]["messages_seen"], 0)
        self.assertEqual(rows["leona-voss"]["messages_ingested"], 0)
        self.assertEqual(rows["mara-field"]["status"], "SYNCED")
        self.assertIsNone(rows["mara-field"]["last_error"])
        self.assertIsNotNone(rows["mara-field"]["last_success_at"])

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pipeline = build_pipeline(self.root / "review.db")
        self.pipeline.initialize()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def payload(
        *, event_id: str = "evt-1", text: str = "Hallo Leona"
    ) -> dict[str, object]:
        return {
            "provider": "instagram-meta-graph",
            "event_id": event_id,
            "message_id": event_id,
            "conversation_id": "thread-1",
            "sender_id": "igsid-user",
            "target_persona": "leona-voss",
            "text": text,
            "received_at": datetime.now(UTC).isoformat(),
        }

    def test_verified_inbound_is_replied_once_and_delivery_is_reconciled(self) -> None:
        provider = FakeProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        first = service.ingest(
            self.payload(), provider_verified=True, auto_process=True
        )
        self.assertEqual(first["processing"]["status"], "SENT")
        self.assertTrue(first["processing"]["external_action"])
        self.assertEqual(len(provider.sent), 1)

        duplicate = service.ingest(
            self.payload(text="different wrapper"),
            provider_verified=True,
            auto_process=True,
        )
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(len(provider.sent), 1)

        outbox_id = int(first["processing"]["outbox_id"])
        reconciled = service.reconcile_reply(outbox_id)
        self.assertTrue(reconciled["reconciled"])
        self.assertEqual(reconciled["status"], "DELIVERED")
        dashboard = service.dashboard()
        self.assertEqual(dashboard["counts"]["delivered"], 1)

    def test_uncertain_write_is_never_blindly_retried(self) -> None:
        provider = FakeProvider(uncertain=True)
        service = InstagramDMService(self.pipeline.db, provider=provider)
        result = service.ingest(
            self.payload(), provider_verified=True, auto_process=True
        )
        self.assertEqual(result["processing"]["status"], "RECONCILE_REQUIRED")
        outbox_id = int(result["processing"]["outbox_id"])
        second = service.dispatch_reply(outbox_id)
        self.assertEqual(second["reason"], "reconcile_required_before_retry")
        self.assertEqual(len(provider.sent), 1)
        with self.assertRaisesRegex(
            ValueError, "reply_cannot_be_cancelled_after_send_started"
        ):
            service.cancel_reply(outbox_id)

    def test_disabled_auto_reply_preserves_safe_draft(self) -> None:
        provider = FakeProvider(auto_reply_enabled=False)
        service = InstagramDMService(self.pipeline.db, provider=provider)
        result = service.ingest(
            self.payload(event_id="draft-disabled"),
            provider_verified=True,
            auto_process=True,
        )
        self.assertEqual(result["processing"]["status"], "DRAFTED")
        self.assertEqual(
            result["processing"]["reason"], "provider_or_auto_reply_not_ready"
        )
        self.assertEqual(provider.sent, [])
        stored = self.pipeline.db.one(
            "SELECT status, attempt_count, last_error FROM instagram_dm_outbox"
        )
        self.assertEqual(stored["status"], "DRAFTED")
        self.assertEqual(stored["attempt_count"], 0)
        self.assertIsNone(stored["last_error"])

    def test_unsafe_message_never_queues_or_sends(self) -> None:
        provider = FakeProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        result = service.ingest(
            self.payload(text="Schick mir deinen OTP Code"),
            provider_verified=True,
            auto_process=True,
        )
        self.assertEqual(result["status"], "NEEDS_HUMAN")
        self.assertNotIn("processing", result)
        self.assertEqual(provider.sent, [])
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_outbox"), 0
        )

    def test_unverified_local_import_can_queue_but_never_send(self) -> None:
        provider = FakeProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        ingested = service.ingest(self.payload())
        queued = service.queue_reply(int(ingested["event_id"]))
        service.approve_reply(int(queued["outbox_id"]))
        with self.assertRaisesRegex(ValueError, "provider_verified_inbound_required"):
            service.dispatch_reply(int(queued["outbox_id"]))
        self.assertEqual(provider.sent, [])

    def test_closed_24_hour_window_is_fail_closed(self) -> None:
        provider = FakeProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        payload = self.payload()
        payload["received_at"] = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        result = service.ingest(payload, provider_verified=True)
        queued = service.queue_reply(int(result["event_id"]))
        service.approve_reply(int(queued["outbox_id"]))
        with self.assertRaisesRegex(ValueError, "instagram_24h_reply_window_closed"):
            service.dispatch_reply(int(queued["outbox_id"]))
        self.assertEqual(provider.sent, [])

    def test_provider_webhook_signature_parse_poll_and_send(self) -> None:
        transport = FakeTransport()
        provider = MetaInstagramDMProvider(
            accounts={"leona-voss": ("1784", "not-returned")},
            graph_version="v24.0",
            graph_host="graph.instagram.com",
            app_secret="test-secret",
            verify_token="verify-token",
            auto_reply_enabled=True,
            transport_factory=lambda persona: transport,
        )
        raw = json.dumps(
            {
                "object": "instagram",
                "entry": [
                    {
                        "id": "1784",
                        "messaging": [
                            {
                                "sender": {"id": "igsid-user"},
                                "recipient": {"id": "1784"},
                                "timestamp": 1_800_000_000_000,
                                "message": {"mid": "mid-1", "text": "Hallo"},
                            }
                        ],
                    }
                ],
            }
        ).encode()
        signature = "sha256=" + hmac.new(
            b"test-secret", raw, hashlib.sha256
        ).hexdigest()
        self.assertTrue(provider.verify_signature(raw, signature))
        events = provider.parse_webhook(raw)
        self.assertEqual(events[0]["payload"]["target_persona"], "leona-voss")
        self.assertEqual(provider.verify_challenge("subscribe", "verify-token", "42"), "42")
        polled = provider.poll("leona-voss")
        self.assertEqual(len(polled), 1)
        self.assertEqual(polled[0]["message_id"], "msg-in-1")
        self.assertEqual(provider.send_message("leona-voss", "igsid-user", "Hi"), "provider-1")
        self.assertTrue(provider.reconcile_message("leona-voss", "thread-1", "provider-1"))

    def test_custom_request_and_sales_intent_are_visible_without_fake_revenue(self) -> None:
        service = InstagramDMService(self.pipeline.db, provider=FakeProvider())
        custom = service.ingest(
            self.payload(event_id="custom", text="Kannst du mir ein Custom Bild machen?"),
            provider_verified=True,
            auto_process=True,
        )
        support = service.ingest(
            {
                **self.payload(event_id="support", text="Wie kann ich dich unterstützen?"),
                "conversation_id": "thread-2",
                "sender_id": "igsid-user-2",
            },
            provider_verified=True,
            auto_process=True,
        )
        self.assertEqual(custom["processing"]["status"], "OWNER_REVIEW")
        self.assertEqual(support["processing"]["status"], "SENT")
        dashboard = service.dashboard()
        self.assertEqual(dashboard["counts"]["custom_requests"], 1)
        self.assertEqual(dashboard["counts"]["sales_signals"], 2)
        self.assertEqual(
            self.pipeline.db.scalar(
                "SELECT COUNT(*) FROM instagram_dm_sales_events WHERE amount IS NOT NULL"
            ),
            0,
        )

    def test_safe_draft_owner_review_approval_cancel_and_exactly_once(self) -> None:
        provider = FakeProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        safe = service.ingest(self.payload(), provider_verified=True)
        draft = service.queue_reply(int(safe["event_id"]))
        self.assertEqual(draft["status"], "DRAFTED")
        review = service.request_owner_review(int(draft["outbox_id"]), "tone_check")
        self.assertEqual(review["status"], "OWNER_REVIEW")
        approved = service.approve_reply(int(draft["outbox_id"]))
        self.assertEqual(approved["status"], "APPROVED")
        sent = service.dispatch_reply(int(draft["outbox_id"]))
        self.assertEqual(sent["status"], "SENT")
        duplicate = service.dispatch_reply(int(draft["outbox_id"]))
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(len(provider.sent), 1)

        second = service.ingest(
            {**self.payload(event_id="cancel-1"), "conversation_id": "thread-cancel"},
            provider_verified=True,
        )
        second_draft = service.queue_reply(int(second["event_id"]))
        cancelled = service.cancel_reply(int(second_draft["outbox_id"]))
        self.assertEqual(cancelled["status"], "CANCELLED")

    def test_payment_truth_requires_existing_revenue_and_prevents_double_count(self) -> None:
        service = InstagramDMService(self.pipeline.db, provider=FakeProvider())
        result = service.ingest(
            self.payload(event_id="sale-1", text="Wie kann ich dich unterstützen?"),
            provider_verified=True,
        )
        service.queue_reply(int(result["event_id"]))
        sale_id = int(self.pipeline.db.scalar("SELECT id FROM instagram_dm_sales_events"))
        open_state = service.set_payment_state(
            sale_id, "OPEN", expected_amount=49.0, expected_currency="EUR"
        )
        self.assertEqual(open_state["payment_status"], "OPEN")
        self.assertIsNone(open_state["confirmed_revenue"])
        open_dashboard = service.dashboard()
        self.assertEqual(open_dashboard["items"][0]["expected_open_amount"], 49.0)
        self.assertIsNone(open_dashboard["counts"]["confirmed_dm_revenue"])
        with self.assertRaisesRegex(ValueError, "confirmed_payment_requires_revenue_event"):
            service.set_payment_state(sale_id, "CONFIRMED")
        with self.assertRaisesRegex(ValueError, "verified_revenue_event_required"):
            service.confirm_payment_from_revenue(sale_id, 9999)

        creator_id = int(self.pipeline.db.scalar("SELECT id FROM creators WHERE slug='leona-voss'"))
        with self.pipeline.db.transaction() as connection:
            revenue_id = int(connection.execute(
                """INSERT INTO revenue_events
                   (creator_id, content_id, amount, currency, source, occurred_at)
                   VALUES (?, NULL, 49, 'EUR', 'verified-payment-provider', ?)""",
                (creator_id, datetime.now(UTC).isoformat()),
            ).lastrowid)
        confirmed = service.confirm_payment_from_revenue(sale_id, revenue_id)
        self.assertEqual(confirmed["payment_status"], "CONFIRMED")
        self.assertEqual(confirmed["confirmed_revenue"], 49.0)
        confirmed_dashboard = service.dashboard()
        self.assertEqual(confirmed_dashboard["counts"]["confirmed_dm_revenue"], 49.0)
        self.assertEqual(
            confirmed_dashboard["counts"]["confirmed_dm_revenue_by_currency"],
            {"EUR": 49.0},
        )
        self.assertTrue(
            service.confirm_payment_from_revenue(sale_id, revenue_id)["duplicate"]
        )
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM revenue_events"), 1
        )

        second = service.ingest(
            {
                **self.payload(event_id="sale-2", text="Wie kann ich dich unterstützen?"),
                "conversation_id": "thread-sale-2",
                "sender_id": "igsid-user-2",
            },
            provider_verified=True,
        )
        service.queue_reply(int(second["event_id"]))
        second_sale_id = int(self.pipeline.db.scalar(
            "SELECT MAX(id) FROM instagram_dm_sales_events"
        ))
        with self.assertRaisesRegex(ValueError, "revenue_event_already_attributed"):
            service.confirm_payment_from_revenue(second_sale_id, revenue_id)

    def test_payment_truth_survives_repeated_initialize(self) -> None:
        service = InstagramDMService(self.pipeline.db, provider=FakeProvider())

        def sale(event_id: str, conversation_id: str) -> int:
            inbound = service.ingest(
                {
                    **self.payload(
                        event_id=event_id,
                        text="Wie kann ich dich unterstützen?",
                    ),
                    "conversation_id": conversation_id,
                    "sender_id": f"user-{event_id}",
                },
                provider_verified=True,
            )
            service.queue_reply(int(inbound["event_id"]))
            return int(self.pipeline.db.scalar(
                "SELECT id FROM instagram_dm_sales_events WHERE trigger_event_id=?",
                (inbound["event_id"],),
            ))

        confirmed_id = sale("persist-confirmed", "thread-confirmed")
        unknown_id = sale("persist-unknown", "thread-unknown")
        failed_id = sale("persist-failed", "thread-failed")
        creator_id = int(self.pipeline.db.scalar(
            "SELECT id FROM creators WHERE slug='leona-voss'"
        ))
        with self.pipeline.db.transaction() as connection:
            revenue_id = int(connection.execute(
                """INSERT INTO revenue_events
                   (creator_id, content_id, amount, currency, source, occurred_at)
                   VALUES (?, NULL, 75, 'EUR', 'verified-payment-provider', ?)""",
                (creator_id, datetime.now(UTC).isoformat()),
            ).lastrowid)
        service.confirm_payment_from_revenue(confirmed_id, revenue_id)
        service.set_payment_state(unknown_id, "UNKNOWN")
        service.set_payment_state(failed_id, "FAILED_OR_NOT_RECEIVED")

        self.pipeline.initialize()
        self.pipeline.initialize()

        confirmed = service.payment_state(confirmed_id)
        self.assertEqual(confirmed["payment_status"], "CONFIRMED")
        self.assertEqual(confirmed["revenue_event_id"], revenue_id)
        self.assertEqual(confirmed["confirmed_revenue"], 75.0)
        self.assertEqual(service.payment_state(unknown_id)["payment_status"], "UNKNOWN")
        self.assertEqual(
            service.payment_state(failed_id)["payment_status"],
            "FAILED_OR_NOT_RECEIVED",
        )
        dashboard = service.dashboard()
        self.assertEqual(dashboard["counts"]["confirmed_dm_revenue"], 75.0)
        self.assertEqual(
            dashboard["counts"]["confirmed_dm_revenue_by_currency"],
            {"EUR": 75.0},
        )
        reply_view_columns = {
            row[1] for row in self.pipeline.db.all(
                "PRAGMA table_info(instagram_dm_reply_actions)"
            )
        }
        sales_view_columns = {
            row[1] for row in self.pipeline.db.all(
                "PRAGMA table_info(instagram_dm_sales)"
            )
        }
        self.assertTrue(
            {"owner_review_reason", "approved_at", "cancelled_at"}
            <= reply_view_columns
        )
        self.assertTrue(
            {"payment_status", "expected_amount", "expected_currency", "revenue_event_id"}
            <= sales_view_columns
        )

    def polled(
        self, event_id: str, *, hours_ago: float, conversation_id: str = "thread-1",
        persona: str = "leona-voss", **extra: object,
    ) -> dict[str, object]:
        return {
            **self.payload(event_id=event_id),
            "conversation_id": conversation_id,
            "target_persona": persona,
            "received_at": (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat(),
            **extra,
        }

    def test_sync_survives_stale_and_malformed_messages(self) -> None:
        provider = FakeProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        provider.polled["leona-voss"] = [
            self.polled("stale", hours_ago=30),
            {**self.polled("broken", hours_ago=1, conversation_id="t-x"), "text": 7},
        ]
        provider.polled["mara-field"] = [
            self.polled("mara-1", hours_ago=1, conversation_id="t-m", persona="mara-field"),
        ]
        result = service.sync_provider()
        leona = result["personas"]["leona-voss"]
        self.assertEqual((leona["status"], leona["ingested"], leona["rejected"]), ("SYNCED", 1, 1))
        self.assertEqual(result["personas"]["mara-field"]["replies_sent"], 1)
        self.assertEqual([sent[0] for sent in provider.sent], ["mara-field"])
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_provider_sync"), 2
        )
        # The stale message stays visible but never produces a sendable reply.
        self.assertEqual(self.pipeline.db.scalar(
            """SELECT COUNT(*) FROM instagram_dm_outbox o
               JOIN instagram_dm_events e ON e.id=o.trigger_event_id
               WHERE e.external_event_id='stale'"""
        ), 0)

    def test_poll_batch_replies_once_per_conversation_turn(self) -> None:
        for order in ("newest_first", "oldest_first"):
            with self.subTest(order=order):
                provider = FakeProvider()
                pipeline = build_pipeline(self.root / f"{order}.db")
                pipeline.initialize()
                service = InstagramDMService(pipeline.db, provider=provider)
                batch = [
                    self.polled(f"{order}-3", hours_ago=0.01),
                    self.polled(f"{order}-2", hours_ago=0.02),
                    self.polled(f"{order}-1", hours_ago=0.03),
                ]
                if order == "oldest_first":
                    batch.reverse()
                provider.polled["leona-voss"] = batch
                result = service.sync_provider("leona-voss")
                self.assertEqual(result["personas"]["leona-voss"]["ingested"], 3)
                self.assertEqual(len(provider.sent), 1)
                self.assertEqual(pipeline.db.scalar(
                    """SELECT e.external_event_id FROM instagram_dm_outbox o
                       JOIN instagram_dm_events e ON e.id=o.trigger_event_id"""
                ), f"{order}-3")
                conversation = pipeline.db.one(
                    "SELECT last_received_at FROM instagram_dm_conversations"
                )
                newest = pipeline.db.scalar(
                    "SELECT MAX(received_at) FROM instagram_dm_events"
                )
                self.assertEqual(conversation["last_received_at"], newest)

                # Replayed poll: nothing new, nothing sent again.
                service.sync_provider("leona-voss")
                self.assertEqual(len(provider.sent), 1)
                # A genuine follow-up after the reply is a new turn.
                with pipeline.db.transaction() as connection:
                    connection.execute(
                        "UPDATE instagram_dm_conversations SET last_outbound_at=?",
                        ((datetime.now(UTC) - timedelta(seconds=30))
                         .isoformat(timespec="seconds"),),
                    )
                provider.polled["leona-voss"] = [
                    self.polled(f"{order}-4", hours_ago=0.005), *batch
                ]
                service.sync_provider("leona-voss")
                self.assertEqual(len(provider.sent), 2)

    def test_thread_already_answered_by_account_is_not_auto_replied(self) -> None:
        provider = FakeProvider()
        service = InstagramDMService(self.pipeline.db, provider=provider)
        provider.polled["leona-voss"] = [
            self.polled("answered", hours_ago=0.5, provider_answered=True)
        ]
        service.sync_provider("leona-voss")
        self.assertEqual(provider.sent, [])
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 1
        )

        transport = FakeTransport()
        now = datetime.now(UTC)
        messages = [
            {"id": "own-late", "from": {"id": "1784"}, "message": "Hi",
             "created_time": now.strftime("%Y-%m-%dT%H:%M:%S+0000")},
            {"id": "in-early", "from": {"id": "igsid-user"}, "message": "Hallo",
             "created_time": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S+0000")},
        ]
        transport.get = lambda path, params: (  # type: ignore[method-assign]
            transport.gets.append((path, params)) or (
                {"data": [{"id": "thread-1"}]} if path.endswith("/conversations")
                else {"messages": {"data": messages}}
            )
        )
        meta = MetaInstagramDMProvider(
            accounts={"leona-voss": ("1784", "not-returned")},
            graph_version="v24.0",
            graph_host="graph.instagram.com",
            transport_factory=lambda persona: transport,
        )
        polled = meta.poll("leona-voss")
        self.assertEqual([item["message_id"] for item in polled], ["in-early"])
        self.assertTrue(polled[0]["provider_answered"])
        self.assertIn("messages.limit(20)", transport.gets[1][1]["fields"])
        messages[0]["created_time"] = (now - timedelta(minutes=10)).strftime(
            "%Y-%m-%dT%H:%M:%S+0000"
        )
        self.assertFalse(meta.poll("leona-voss")[0]["provider_answered"])

    def test_webhook_igsid_is_not_used_as_provider_conversation_id(self) -> None:
        transport = FakeTransport()
        provider = MetaInstagramDMProvider(
            accounts={"leona-voss": ("1784", "not-returned")},
            graph_version="v24.0",
            graph_host="graph.instagram.com",
            app_secret="test-secret",
            verify_token="verify-token",
            auto_reply_enabled=True,
            transport_factory=lambda persona: transport,
        )
        service = InstagramDMService(self.pipeline.db, provider=provider)
        raw = json.dumps({
            "object": "instagram",
            "entry": [{
                "id": "1784",
                "messaging": [{
                    "sender": {"id": "igsid-user"},
                    "recipient": {"id": "1784"},
                    "timestamp": int(datetime.now(UTC).timestamp() * 1_000),
                    "message": {"mid": "webhook-mid", "text": "Hallo"},
                }],
            }],
        }).encode()
        signature = "sha256=" + hmac.new(
            b"test-secret", raw, hashlib.sha256
        ).hexdigest()
        processed = service.process_webhook(raw, signature)
        outbox_id = int(processed["results"][0]["processing"]["outbox_id"])
        conversation_ref = self.pipeline.db.scalar(
            "SELECT external_conversation_id FROM instagram_dm_conversations"
        )
        self.assertEqual(conversation_ref, "webhook-igsid:igsid-user")
        gets_before = len(transport.gets)
        reconciled = service.reconcile_reply(outbox_id)
        self.assertIsNone(reconciled["reconciled"])
        self.assertEqual(
            reconciled["reason"], "VERIFY_OFFICIAL_META_CONVERSATION_ID_REQUIRED"
        )
        self.assertEqual(reconciled["status"], "RECONCILE_REQUIRED")
        self.assertEqual(len(transport.gets), gets_before)

    def test_malformed_and_unsupported_webhook_events_do_not_persist(self) -> None:
        transport = FakeTransport()
        provider = MetaInstagramDMProvider(
            accounts={"leona-voss": ("1784", "not-returned")},
            graph_version="v24.0",
            graph_host="graph.instagram.com",
            app_secret="test-secret",
            verify_token="verify-token",
            auto_reply_enabled=True,
            transport_factory=lambda persona: transport,
        )
        service = InstagramDMService(self.pipeline.db, provider=provider)
        raw = json.dumps({
            "object": "instagram",
            "entry": [{"id": "1784", "messaging": [{"message": {"mid": "x", "attachments": []}}]}],
        }).encode()
        signature = "sha256=" + hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
        result = service.process_webhook(raw, signature)
        self.assertEqual(result["events"], 0)
        self.assertEqual(result["rejected"], 1)
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 0)
        with self.assertRaisesRegex(ValueError, "instagram_webhook_signature_invalid"):
            service.process_webhook(raw, "sha256=wrong")

    def test_owner_reply_action_requires_auth_and_csrf(self) -> None:
        provider = FakeProvider()
        server = create_server(
            self.root / "auth.db",
            port=0,
            asset_root=self.root,
            auth_password=PASSWORD,
            instagram_dm_provider=provider,
        )
        service = server.RequestHandlerClass.instagram_dm
        inbound = service.ingest(self.payload(event_id="auth-1"), provider_verified=True)
        draft = service.queue_reply(int(inbound["event_id"]))
        outbox_id = int(draft["outbox_id"])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            unauthenticated = Request(
                f"{base}/api/instagram-dm/{outbox_id}/reply/approve",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as raised:
                urlopen(unauthenticated, timeout=5)
            self.assertEqual(raised.exception.code, 401)

            jar = CookieJar()
            opener = build_opener(HTTPCookieProcessor(jar))
            login = Request(
                f"{base}/login",
                data=urlencode({"password": PASSWORD}).encode("ascii"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with opener.open(login, timeout=5):
                pass
            cookies = {cookie.name: cookie.value for cookie in jar}
            missing_csrf = Request(
                f"{base}/api/instagram-dm/{outbox_id}/reply/approve",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as raised:
                opener.open(missing_csrf, timeout=5)
            self.assertEqual(raised.exception.code, 403)
            authorized = Request(
                f"{base}/api/instagram-dm/{outbox_id}/reply/approve",
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "X-CSRF-Token": cookies[CSRF_COOKIE],
                },
                method="POST",
            )
            with opener.open(authorized, timeout=5) as response:
                self.assertEqual(json.load(response)["status"], "APPROVED")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_public_webhook_is_signature_gated_and_provider_verified(self) -> None:
        provider = FakeProvider()
        server = create_server(
            self.root / "webhook.db",
            port=0,
            asset_root=self.root,
            instagram_dm_provider=provider,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(
                f"{base}/webhooks/instagram?hub.mode=subscribe&hub.verify_token=x&hub.challenge=42",
                timeout=5,
            ) as response:
                self.assertEqual(response.read().decode(), "42")
            webhook = [
                {
                    "kind": "INBOUND",
                    "payload": self.payload(event_id="webhook-event"),
                }
            ]
            request = Request(
                f"{base}/webhooks/instagram",
                data=json.dumps(webhook).encode(),
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": "valid",
                },
                method="POST",
            )
            with urlopen(request, timeout=5) as response:
                body = json.load(response)
            self.assertTrue(body["accepted"])
            self.assertEqual(body["events"], 1)
            self.assertEqual(len(provider.sent), 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
