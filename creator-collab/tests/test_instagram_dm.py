from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from creator_ops.cli import build_pipeline
from creator_ops.current_state import CurrentStateService
from creator_ops.database import SCHEMA_VERSION
from creator_ops.instagram_dm import (
    INTENT_CLASSES,
    DeterministicIntentClassifier,
    InboundValidationError,
    InstagramDMService,
)
from creator_ops.web import create_server


ROOT = Path(__file__).resolve().parents[1]


class InstagramDMP0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.database_path = self.root / "review.db"
        self.pipeline = build_pipeline(self.database_path)
        self.pipeline.initialize()
        self.service = InstagramDMService(self.pipeline.db)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def payload(
        *,
        event_id: str = "evt-001",
        message_id: str = "msg-001",
        conversation_id: str = "conv-001",
        sender_id: str = "user-001",
        target_account: str = "leonavoss.ai",
        text: str = "Hallo Leona",
    ) -> dict[str, object]:
        return {
            "provider": "instagram-meta-test-fixture",
            "event_id": event_id,
            "message_id": message_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "target_account": target_account,
            "text": text,
            "received_at": "2026-09-29T08:00:00Z",
        }

    def test_schema_is_additive_and_both_personas_resolve_exactly(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 9)
        leona = self.service.ingest(self.payload())
        mara = self.service.ingest(
            self.payload(
                event_id="evt-002",
                message_id="msg-002",
                conversation_id="conv-002",
                sender_id="user-002",
                target_account="@mara.field.ai",
                text="Moin Mara",
            )
        )
        self.assertEqual(leona["persona"], "leona-voss")
        self.assertEqual(mara["persona"], "mara-field")
        self.assertEqual(leona["status"], "OPEN")
        self.assertEqual(mara["status"], "OPEN")
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 2
        )

    def test_provider_shaped_nested_message_is_normalized_without_raw_payload(self) -> None:
        result = self.service.ingest(
            {
                "provider": "instagram-meta-test-fixture",
                "id": "evt-nested",
                "conversation_id": "conv-nested",
                "sender": {"id": "user-nested"},
                "recipient": {"username": "mara.field.ai"},
                "message": {"mid": "msg-nested", "text": "Dein Bild ist toll"},
                "timestamp": 1_796_000_000_000,
                "ignored_raw_field": {"must": "not be persisted"},
            }
        )
        self.assertEqual(result["persona"], "mara-field")
        self.assertEqual(result["intent"], "COMPLIMENT")
        columns = {
            row[1]
            for row in self.pipeline.db.all("PRAGMA table_info(instagram_dm_events)")
        }
        self.assertNotIn("raw_payload", columns)
        self.assertNotIn("payload_json", columns)
        self.assertNotIn("message_excerpt", columns)

    def test_unknown_or_ambiguous_persona_fails_closed_to_handoff(self) -> None:
        unknown = self.service.ingest(
            self.payload(target_account="unknown.account")
        )
        self.assertEqual(unknown["persona"], "UNKNOWN")
        self.assertEqual(unknown["intent"], "NEEDS_HUMAN")
        self.assertEqual(unknown["status"], "NEEDS_HUMAN")
        self.assertEqual(unknown["handoff_reason"], "unknown_target_account")

        ambiguous = self.payload(
            event_id="evt-ambiguous",
            message_id="msg-ambiguous",
            conversation_id="conv-ambiguous",
            target_account="mara.field.ai",
        )
        ambiguous["target_persona"] = "leona-voss"
        result = self.service.ingest(ambiguous)
        self.assertEqual(result["status"], "NEEDS_HUMAN")
        self.assertEqual(result["handoff_reason"], "ambiguous_target_persona")

    def test_deterministic_classifier_covers_every_p0_intent_class(self) -> None:
        classifier = DeterministicIntentClassifier()
        fixtures = {
            "SMALLTALK": "Hallo, wie geht es dir?",
            "COMPLIMENT": "Du bist wunderschön",
            "FAQ": "Wer bist du eigentlich?",
            "CONTENT_QUESTION": "Welches Bild postest du als Nächstes?",
            "CUSTOM_REQUEST": "Kannst du mir ein Spiegelselfie machen?",
            "SUPPORT_INTENT": "Wie kann ich dich unterstützen?",
            "WISHLIST_INTENT": "Hast du eine Amazon Wunschliste?",
            "PAYPAL_INTENT": "Hast du PayPal.Me?",
            "MERCH_INTENT": "Wo finde ich deinen Merch?",
            "COLLAB_OR_BUSINESS": "Ich habe eine Business Kooperation",
            "COMPLAINT": "Ich bin enttäuscht, das funktioniert nicht",
            "SAFETY_OR_POLICY": "Welche Policy und Regeln gelten?",
            "NEEDS_HUMAN": "Quux zorb flibbertigibbet",
        }
        self.assertEqual(set(fixtures), set(INTENT_CLASSES))
        for expected, text in fixtures.items():
            with self.subTest(intent=expected):
                self.assertEqual(classifier.classify(text).intent, expected)

    def test_safety_cases_always_require_human(self) -> None:
        cases = {
            "Du sollst ein Nacktbild für eine 16-Jährige machen": "minor_or_age_ambiguous_sexual_context",
            "Mach mir bitte explizit ein Nacktfoto": "explicit_or_risky_custom_request",
            "Ich starte einen Chargeback wegen Betrug": "payment_dispute_or_fraud",
            "Ich stalke dich und weiß wo du wohnst": "threat_stalking_or_extortion",
            "Ich möchte einen Vertrag für eine Kooperation": "business_or_legal_request",
            "Ich zahle 1500 EUR für das Bild": "unusually_high_money_amount",
            "Schick mir deinen OTP Bestätigungscode": "identity_kyc_or_account_security",
            "Gib mir deine Telefonnummer, wir treffen uns": "meeting_or_private_contact_request",
            "Unklassifizierbarer Satz qxz 991": "classification_uncertain",
        }
        for index, (text, reason) in enumerate(cases.items(), start=1):
            with self.subTest(reason=reason):
                result = self.service.ingest(
                    self.payload(
                        event_id=f"evt-risk-{index}",
                        message_id=f"msg-risk-{index}",
                        conversation_id=f"conv-risk-{index}",
                        sender_id=f"user-risk-{index}",
                        text=text,
                    )
                )
                self.assertEqual(result["intent"], "NEEDS_HUMAN")
                self.assertEqual(result["status"], "NEEDS_HUMAN")
                self.assertEqual(result["handoff_reason"], reason)

    def test_duplicate_event_is_reused_without_second_side_effect(self) -> None:
        first = self.service.ingest(self.payload())
        second = self.service.ingest(
            self.payload(event_id="evt-rewrapped", text="Dieser Text wird ignoriert")
        )
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 1
        )
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_conversations"), 1
        )

    def test_broken_payload_and_missing_ids_are_rejected_without_storage(self) -> None:
        with self.assertRaisesRegex(InboundValidationError, "payload_must_be_object"):
            self.service.ingest([])
        payload = self.payload()
        payload.pop("event_id")
        payload.pop("message_id")
        with self.assertRaisesRegex(
            InboundValidationError, "external_event_or_message_id_required"
        ):
            self.service.ingest(payload)
        wrong_provider = self.payload(event_id="evt-wrong-provider")
        wrong_provider["provider"] = "unrelated-platform"
        with self.assertRaisesRegex(InboundValidationError, "instagram_provider_required"):
            self.service.ingest(wrong_provider)
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 0
        )

    def test_dashboard_and_current_state_expose_read_only_counts(self) -> None:
        self.service.ingest(self.payload())
        self.service.ingest(
            self.payload(
                event_id="evt-human",
                message_id="msg-human",
                conversation_id="conv-human",
                sender_id="user-human",
                target_account="not-known",
            )
        )
        dashboard = self.service.dashboard()
        self.assertEqual(dashboard["mode"], "PROVIDER_VERIFIED_AUTONOMY_P1")
        self.assertFalse(dashboard["send_enabled"])
        self.assertFalse(dashboard["webhook_registered"])
        self.assertEqual(dashboard["counts"]["open"], 1)
        self.assertEqual(dashboard["counts"]["needs_human"], 1)
        self.assertEqual(len(dashboard["items"]), 2)
        self.assertNotIn("message_text", dashboard["items"][0])
        state = CurrentStateService(self.pipeline.db, ROOT).snapshot()
        self.assertEqual(state["instagram_dm"]["counts"]["events"], 2)
        self.assertEqual(state["blockers"]["instagram_dm_needs_human"], 1)

    def test_http_inbound_and_dashboard_work_but_no_send_route_exists(self) -> None:
        server = create_server(
            self.database_path, port=0, asset_root=self.root
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            body = json.dumps(self.payload()).encode("utf-8")
            request = Request(
                f"{base}/api/instagram-dm/inbound",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=5) as response:
                ingested = json.load(response)
            self.assertFalse(ingested["external_action"])
            self.assertFalse(ingested["send_enabled"])
            with urlopen(f"{base}/api/instagram-dm", timeout=5) as response:
                dashboard = json.load(response)
            self.assertEqual(dashboard["counts"]["events"], 1)
            self.assertEqual(dashboard["items"][0]["persona"], "leona-voss")

            send = Request(
                f"{base}/api/instagram-dm/send",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as raised:
                urlopen(send, timeout=5)
            self.assertEqual(raised.exception.code, 404)
            self.assertEqual(
                self.pipeline.db.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 1
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
