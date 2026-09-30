from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import threading
import unittest
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
    MetaInstagramDMProvider,
)
from creator_ops.web import CSRF_COOKIE, create_server


PASSWORD = "test-only-correct-horse-battery-staple"


class FakeProvider:
    def __init__(self, *, uncertain: bool = False) -> None:
        self.auto_reply_enabled = True
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
            "auto_reply_enabled": True,
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

    def get(self, path: str, params: dict[str, str]) -> dict[str, object]:
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
