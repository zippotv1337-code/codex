from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping, Protocol

from .database import CreatorDatabase, utc_now
from .instagram_dm_provider import (
    InstagramDMProvider,
    InstagramDMProviderConnectionError,
    InstagramDMProviderError,
)


INTENT_CLASSES = (
    "SMALLTALK",
    "COMPLIMENT",
    "FAQ",
    "CONTENT_QUESTION",
    "CUSTOM_REQUEST",
    "SUPPORT_INTENT",
    "WISHLIST_INTENT",
    "PAYPAL_INTENT",
    "MERCH_INTENT",
    "COLLAB_OR_BUSINESS",
    "COMPLAINT",
    "SAFETY_OR_POLICY",
    "NEEDS_HUMAN",
)

MAX_IDENTIFIER_LENGTH = 255
MAX_MESSAGE_LENGTH = 2_000
HIGH_AMOUNT_THRESHOLD = 500.0


class InboundValidationError(ValueError):
    """The inbound envelope is unsafe or incomplete and must not be stored."""


@dataclass(frozen=True)
class NormalizedInstagramDM:
    provider: str
    external_event_id: str | None
    external_message_id: str | None
    dedupe_key: str
    external_conversation_id: str
    external_user_id: str
    target_account: str | None
    target_persona: str | None
    text: str
    received_at: str


@dataclass(frozen=True)
class IntentDecision:
    intent: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class SafetyDecision:
    needs_human: bool
    reason: str | None = None


class IntentClassifier(Protocol):
    def classify(self, text: str) -> IntentDecision: ...


def _clean_identifier(value: object, field: str, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise InboundValidationError(f"{field}_required")
        return None
    if not isinstance(value, (str, int)):
        raise InboundValidationError(f"{field}_invalid")
    cleaned = str(value).strip()
    if not cleaned:
        if required:
            raise InboundValidationError(f"{field}_required")
        return None
    if len(cleaned) > MAX_IDENTIFIER_LENGTH:
        raise InboundValidationError(f"{field}_too_long")
    return cleaned


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _timestamp(value: object) -> str:
    if value in (None, ""):
        return utc_now()
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1_000
        try:
            return datetime.fromtimestamp(seconds, tz=UTC).isoformat(timespec="seconds")
        except (OverflowError, OSError, ValueError) as error:
            raise InboundValidationError("received_at_invalid") from error
    if not isinstance(value, str):
        raise InboundValidationError("received_at_invalid")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as error:
        raise InboundValidationError("received_at_invalid") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="seconds")


class InstagramDMInboundNormalizer:
    """Normalize one provider envelope without retaining the raw payload."""

    def normalize(self, payload: object) -> NormalizedInstagramDM:
        if not isinstance(payload, Mapping):
            raise InboundValidationError("payload_must_be_object")

        message = _mapping(payload.get("message"))
        sender = _mapping(payload.get("sender"))
        recipient = _mapping(payload.get("recipient"))
        provider = _clean_identifier(payload.get("provider") or "instagram-meta", "provider", required=True)
        if provider is None or not provider.lower().startswith("instagram"):
            raise InboundValidationError("instagram_provider_required")
        event_id = _clean_identifier(
            payload.get("event_id") or payload.get("id"), "external_event_id"
        )
        message_id = _clean_identifier(
            payload.get("message_id") or message.get("id") or message.get("mid"),
            "external_message_id",
        )
        if event_id is None and message_id is None:
            raise InboundValidationError("external_event_or_message_id_required")

        sender_id = _clean_identifier(
            payload.get("sender_id") or sender.get("id"),
            "external_user_id",
            required=True,
        )
        conversation_id = _clean_identifier(
            payload.get("conversation_id") or payload.get("thread_id") or sender_id,
            "external_conversation_id",
            required=True,
        )
        target_account = _clean_identifier(
            payload.get("target_account")
            or payload.get("recipient_username")
            or recipient.get("username")
            or recipient.get("id"),
            "target_account",
        )
        target_persona = _clean_identifier(
            payload.get("target_persona"), "target_persona"
        )

        text = payload.get("text", message.get("text", ""))
        if text is None:
            text = ""
        if not isinstance(text, str):
            raise InboundValidationError("message_text_invalid")
        text = text.strip()
        if len(text) > MAX_MESSAGE_LENGTH:
            raise InboundValidationError("message_text_too_long")

        return NormalizedInstagramDM(
            provider=provider,
            external_event_id=event_id,
            external_message_id=message_id,
            dedupe_key=event_id or message_id or "",
            external_conversation_id=conversation_id or "",
            external_user_id=sender_id or "",
            target_account=target_account,
            target_persona=target_persona,
            text=text,
            received_at=_timestamp(payload.get("received_at") or payload.get("timestamp")),
        )


class DeterministicIntentClassifier:
    """Small deterministic baseline; later model classifiers implement the same protocol."""

    _patterns: tuple[tuple[str, re.Pattern[str], float], ...] = (
        ("PAYPAL_INTENT", re.compile(r"\bpaypal(?:\.me)?\b", re.I), 0.99),
        ("WISHLIST_INTENT", re.compile(r"\b(?:wishlist|wunschliste|amazon\s+liste)\b", re.I), 0.99),
        ("MERCH_INTENT", re.compile(r"\b(?:merch|merchandise|shirt|hoodie|shop)\b", re.I), 0.95),
        ("SUPPORT_INTENT", re.compile(r"\b(?:unterst[uü]tz|support|spend(?:e|en)|donat)\w*\b", re.I), 0.93),
        ("COLLAB_OR_BUSINESS", re.compile(r"\b(?:kooperation|collab|business|angebot|vertrag|anwalt|legal|markenpartner)\w*\b", re.I), 0.96),
        ("COMPLAINT", re.compile(r"\b(?:beschwer|unzufrieden|entt[aä]uscht|kaputt|funktioniert\s+nicht|schlecht)\w*\b", re.I), 0.91),
        ("SAFETY_OR_POLICY", re.compile(r"\b(?:policy|regeln?|erlaubt|18\+|adult|sicherheit|ki[- ]?kennzeichnung)\b", re.I), 0.91),
        ("CUSTOM_REQUEST", re.compile(r"\b(?:kannst\s+du|mach(?:st)?\s+(?:mir|mal)|wunsch(?:bild|content)?|custom)\b", re.I), 0.88),
        ("CONTENT_QUESTION", re.compile(r"\b(?:bild|foto|post|content|outfit|story|reel|carousel)\w*\b.*(?:\?|welch|warum|wann|wo)", re.I), 0.84),
        ("FAQ", re.compile(r"\b(?:wer\s+bist|bist\s+du\s+(?:echt|eine\s+ki)|wie\s+funktioniert|was\s+ist|h[aä]ufige\s+frage)\b", re.I), 0.90),
        ("COMPLIMENT", re.compile(r"\b(?:s[uü][sß]|h[uü]bsch|sch[oö]n|wundersch[oö]n|toll|liebe\s+dein|gef[aä]llt\s+mir)\w*\b", re.I), 0.88),
        ("SMALLTALK", re.compile(r"\b(?:hallo|hey|hi|moin|guten\s+(?:morgen|tag|abend)|wie\s+geht|was\s+machst)\b", re.I), 0.82),
    )

    def classify(self, text: str) -> IntentDecision:
        if not text.strip():
            return IntentDecision("NEEDS_HUMAN", 0.0, "empty_or_non_text_message")
        for intent, pattern, confidence in self._patterns:
            if pattern.search(text):
                return IntentDecision(intent, confidence, "deterministic_keyword_match")
        return IntentDecision("NEEDS_HUMAN", 0.25, "classification_uncertain")


class DMSafetyPolicy:
    _minor = re.compile(
        r"\b(?:minderj[aä]hrig\w*|unter\s*18|1[0-7](?:\s*[- ]?j[aä]hrig\w*)?|kind|sch[uü]ler(?:in)?)\b",
        re.I,
    )
    _sexual = re.compile(r"\b(?:nackt|nude|porn|sex(?:y|uell)?|fetisch|intim|oben\s+ohne|explicit)\w*\b", re.I)
    _payment_dispute = re.compile(r"\b(?:chargeback|r[uü]ckbuch|zahlungsstreit|betrug|scam|geld\s+zur[uü]ck)\w*\b", re.I)
    _threat = re.compile(r"\b(?:droh|erpress|stalk|verfolg|ich\s+finde\s+dich|ich\s+wei[sß]\s+wo)\w*\b", re.I)
    _business_legal = re.compile(r"\b(?:kooperation|collab|business|vertrag|anwalt|legal|markenpartner)\w*\b", re.I)
    _identity = re.compile(r"\b(?:kyc|ausweis|passport|identit[aä]t|otp|2fa|best[aä]tigungscode|passwort|password)\w*\b", re.I)
    _real_world = re.compile(r"\b(?:treffen|adresse|telefonnummer|handynummer|private\s+nummer|wohnst\s+du)\b", re.I)
    _amount = re.compile(r"(?<!\w)(\d{2,7}(?:[.,]\d{1,2})?)\s*(?:€|eur|\$|usd)\b", re.I)

    def evaluate(self, text: str, decision: IntentDecision) -> SafetyDecision:
        if self._minor.search(text) and self._sexual.search(text):
            return SafetyDecision(True, "minor_or_age_ambiguous_sexual_context")
        if self._sexual.search(text):
            return SafetyDecision(True, "explicit_or_risky_custom_request")
        if self._payment_dispute.search(text):
            return SafetyDecision(True, "payment_dispute_or_fraud")
        if self._threat.search(text):
            return SafetyDecision(True, "threat_stalking_or_extortion")
        if self._business_legal.search(text):
            return SafetyDecision(True, "business_or_legal_request")
        if self._identity.search(text):
            return SafetyDecision(True, "identity_kyc_or_account_security")
        if self._real_world.search(text):
            return SafetyDecision(True, "meeting_or_private_contact_request")
        for match in self._amount.finditer(text):
            if float(match.group(1).replace(",", ".")) >= HIGH_AMOUNT_THRESHOLD:
                return SafetyDecision(True, "unusually_high_money_amount")
        if decision.intent == "NEEDS_HUMAN" or decision.confidence < 0.70:
            return SafetyDecision(True, decision.reason or "classification_uncertain")
        return SafetyDecision(False)


class InstagramDMService:
    """Provider-verified Instagram DM intake, policy routing, and durable replies."""

    def __init__(
        self,
        database: CreatorDatabase,
        classifier: IntentClassifier | None = None,
        provider: InstagramDMProvider | None = None,
    ) -> None:
        self.database = database
        self.normalizer = InstagramDMInboundNormalizer()
        self.classifier = classifier or DeterministicIntentClassifier()
        self.safety = DMSafetyPolicy()
        self.provider = provider

    @staticmethod
    def _normalized_handle(value: str | None) -> str | None:
        return value.lower().removeprefix("@") if value else None

    def _resolve_persona(
        self, event: NormalizedInstagramDM
    ) -> tuple[int | None, str | None, str | None]:
        rows = self.database.all(
            """
            SELECT cr.id, cr.slug, cr.instagram_handle, pa.public_handle
            FROM creators cr
            LEFT JOIN platform_accounts pa
              ON pa.creator_id=cr.id AND pa.platform='instagram' AND pa.status='ACTIVE'
            WHERE cr.active=1 AND cr.slug IN ('leona-voss', 'mara-field')
            ORDER BY cr.id
            """
        )
        by_slug = {str(row["slug"]): row for row in rows}
        by_handle: dict[str, Any] = {}
        for row in rows:
            for value in (row["instagram_handle"], row["public_handle"]):
                if value:
                    by_handle[self._normalized_handle(str(value)) or ""] = row

        slug_row = by_slug.get(event.target_persona or "") if event.target_persona else None
        account_row = (
            by_handle.get(self._normalized_handle(event.target_account) or "")
            if event.target_account
            else None
        )
        if event.target_persona and slug_row is None:
            return None, None, "unknown_target_persona"
        if event.target_account and account_row is None:
            return None, None, "unknown_target_account"
        if slug_row is not None and account_row is not None and slug_row["id"] != account_row["id"]:
            return None, None, "ambiguous_target_persona"
        resolved = slug_row or account_row
        if resolved is None:
            return None, None, "target_persona_missing"
        return int(resolved["id"]), str(resolved["slug"]), None

    def _existing_result(self, row: Any) -> dict[str, object]:
        return {
            "event_id": int(row["id"]),
            "conversation_id": int(row["conversation_id"]),
            "duplicate": True,
            "persona": str(row["persona"] or "UNKNOWN"),
            "intent": str(row["intent"]),
            "status": str(row["status"]),
            "handoff_reason": row["handoff_reason"],
            "send_enabled": bool(self.provider and self.provider.auto_reply_enabled),
            "external_action": False,
        }

    def ingest(
        self,
        payload: object,
        *,
        provider_verified: bool = False,
        auto_process: bool = False,
    ) -> dict[str, object]:
        event = self.normalizer.normalize(payload)
        existing = self.database.one(
            """
            SELECT e.id, e.conversation_id, e.intent, e.status, e.handoff_reason,
                   cr.slug AS persona
            FROM instagram_dm_events e
            JOIN instagram_dm_conversations c ON c.id=e.conversation_id
            LEFT JOIN creators cr ON cr.id=c.creator_id
            WHERE e.provider=? AND (
                e.dedupe_key=?
                OR (? IS NOT NULL AND e.external_event_id=?)
                OR (? IS NOT NULL AND e.external_message_id=?)
            )
            """,
            (
                event.provider,
                event.dedupe_key,
                event.external_event_id,
                event.external_event_id,
                event.external_message_id,
                event.external_message_id,
            ),
        )
        if existing is not None:
            return self._existing_result(existing)

        creator_id, persona, persona_error = self._resolve_persona(event)
        intent = self.classifier.classify(event.text)
        safety = self.safety.evaluate(event.text, intent)
        handoff_reason = persona_error or safety.reason
        needs_human = handoff_reason is not None
        stored_intent = "NEEDS_HUMAN" if needs_human else intent.intent
        stored_confidence = 0.0 if persona_error else intent.confidence
        status = "NEEDS_HUMAN" if needs_human else "OPEN"
        created_at = utc_now()

        with self.database.transaction() as connection:
            duplicate = connection.execute(
                """
                SELECT e.id, e.conversation_id, e.intent, e.status, e.handoff_reason,
                       cr.slug AS persona
                FROM instagram_dm_events e
                JOIN instagram_dm_conversations c ON c.id=e.conversation_id
                LEFT JOIN creators cr ON cr.id=c.creator_id
                WHERE e.provider=? AND (
                    e.dedupe_key=?
                    OR (? IS NOT NULL AND e.external_event_id=?)
                    OR (? IS NOT NULL AND e.external_message_id=?)
                )
                """,
                (
                    event.provider,
                    event.dedupe_key,
                    event.external_event_id,
                    event.external_event_id,
                    event.external_message_id,
                    event.external_message_id,
                ),
            ).fetchone()
            if duplicate is not None:
                return self._existing_result(duplicate)

            conversation = connection.execute(
                """
                SELECT id, status, handoff_reason, creator_id
                FROM instagram_dm_conversations
                WHERE platform='instagram' AND external_conversation_id=?
                """,
                (event.external_conversation_id,),
            ).fetchone()
            if conversation is None:
                cursor = connection.execute(
                    """
                    INSERT INTO instagram_dm_conversations
                        (platform, external_conversation_id, external_user_id,
                         creator_id, last_intent, status, handoff_reason,
                         first_seen_at, last_received_at, updated_at)
                    VALUES ('instagram', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.external_conversation_id,
                        event.external_user_id,
                        creator_id,
                        stored_intent,
                        status,
                        handoff_reason,
                        event.received_at,
                        event.received_at,
                        created_at,
                    ),
                )
                conversation_id = int(cursor.lastrowid)
            else:
                conversation_id = int(conversation["id"])
                was_handoff = conversation["status"] == "NEEDS_HUMAN"
                next_status = "NEEDS_HUMAN" if was_handoff or needs_human else "OPEN"
                next_reason = conversation["handoff_reason"] if was_handoff else handoff_reason
                next_creator = conversation["creator_id"] or creator_id
                connection.execute(
                    """
                    UPDATE instagram_dm_conversations
                    SET external_user_id=?, creator_id=?, last_intent=?, status=?,
                        handoff_reason=?, last_received_at=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        event.external_user_id,
                        next_creator,
                        stored_intent,
                        next_status,
                        next_reason,
                        event.received_at,
                        created_at,
                        conversation_id,
                    ),
                )

            cursor = connection.execute(
                """
                INSERT INTO instagram_dm_events
                    (conversation_id, provider, external_event_id,
                     external_message_id, dedupe_key, intent, confidence,
                     status, handoff_reason, received_at, created_at,
                     provider_verified, direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'INBOUND')
                """,
                (
                    conversation_id,
                    event.provider,
                    event.external_event_id,
                    event.external_message_id,
                    event.dedupe_key,
                    stored_intent,
                    stored_confidence,
                    status,
                    handoff_reason,
                    event.received_at,
                    created_at,
                    1 if provider_verified else 0,
                ),
            )
            event_id = int(cursor.lastrowid)

        result: dict[str, object] = {
            "event_id": event_id,
            "conversation_id": conversation_id,
            "duplicate": False,
            "persona": persona or "UNKNOWN",
            "intent": stored_intent,
            "status": status,
            "handoff_reason": handoff_reason,
            "send_enabled": bool(self.provider and self.provider.auto_reply_enabled),
            "external_action": False,
        }
        if auto_process and provider_verified and status == "OPEN":
            result["processing"] = self.process_event(event_id, dispatch=True)
        return result

    @staticmethod
    def _reply_text(persona: str, intent: str, link: str | None = None) -> str:
        name = "Leona" if persona == "leona-voss" else "Mara"
        replies = {
            "SMALLTALK": f"Hey, danke für deine Nachricht! Hier ist {name} 😊 Was interessiert dich gerade am meisten?",
            "COMPLIMENT": "Danke dir, das freut mich wirklich sehr! 💛",
            "FAQ": (
                f"Ich bin {name}, eine virtuelle KI-Creatorin von ZippoWorkz. "
                "Meine Inhalte sind fiktiv und werden transparent als KI-Inhalte geführt."
            ),
            "CONTENT_QUESTION": "Danke für die Frage! Ich nehme sie gern als Idee für einen der nächsten Posts mit.",
            "CUSTOM_REQUEST": "Danke für die konkrete Idee! Ich habe den Wunsch als unverbindliche Anfrage aufgenommen und prüfe ihn im nächsten Content-Review.",
            "SUPPORT_INTENT": "Danke, dass du das Projekt unterstützen möchtest!" + (f" Hier findest du den freigegebenen Link: {link}" if link else " Aktuell ist dafür noch kein freigegebener Link hinterlegt."),
            "WISHLIST_INTENT": "Danke für dein Interesse!" + (f" Hier ist der freigegebene Wishlist-Link: {link}" if link else " Aktuell ist kein freigegebener Wishlist-Link hinterlegt."),
            "PAYPAL_INTENT": "Danke für dein Interesse!" + (f" Hier ist der freigegebene Support-Link: {link}" if link else " Aktuell ist kein freigegebener Zahlungslink hinterlegt."),
            "MERCH_INTENT": "Danke dir!" + (f" Hier ist der freigegebene Shop-Link: {link}" if link else " Aktuell ist noch kein freigegebener Merch-Link hinterlegt."),
        }
        return replies.get(intent, "Danke für deine Nachricht. Ich habe sie zur persönlichen Prüfung weitergegeben.")

    @staticmethod
    def _link_type(intent: str) -> str | None:
        return {
            "SUPPORT_INTENT": "SUPPORT",
            "WISHLIST_INTENT": "WISHLIST",
            "PAYPAL_INTENT": "PAYMENT",
            "MERCH_INTENT": "MERCH",
        }.get(intent)

    def _approved_link(self, creator_id: int, link_type: str | None) -> str | None:
        if link_type is None:
            return None
        row = self.database.one(
            """
            SELECT url FROM instagram_dm_approved_links
            WHERE link_type=? AND status='ACTIVE'
              AND (creator_id=? OR creator_id IS NULL)
            ORDER BY CASE WHEN creator_id=? THEN 0 ELSE 1 END, id DESC
            LIMIT 1
            """,
            (link_type, creator_id, creator_id),
        )
        return str(row["url"]) if row is not None else None

    def queue_reply(self, event_id: int) -> dict[str, object]:
        row = self.database.one(
            """
            SELECT e.id, e.intent, e.status, e.handoff_reason, e.provider_verified,
                   e.received_at, e.conversation_id, c.external_user_id,
                   c.external_conversation_id, c.creator_id, c.status AS conversation_status,
                   cr.slug AS persona
            FROM instagram_dm_events e
            JOIN instagram_dm_conversations c ON c.id=e.conversation_id
            LEFT JOIN creators cr ON cr.id=c.creator_id
            WHERE e.id=?
            """,
            (event_id,),
        )
        if row is None:
            raise KeyError("instagram_dm_event_not_found")
        existing = self.database.one(
            "SELECT * FROM instagram_dm_outbox WHERE trigger_event_id=?",
            (event_id,),
        )
        if existing is not None:
            return self._outbox_result(existing, duplicate=True)
        if row["status"] == "NEEDS_HUMAN" or row["conversation_status"] == "NEEDS_HUMAN":
            return {
                "event_id": event_id,
                "status": "NEEDS_HUMAN",
                "reason": row["handoff_reason"] or "human_review_required",
                "external_action": False,
            }
        persona = str(row["persona"] or "")
        if persona not in {"leona-voss", "mara-field"}:
            raise ValueError("instagram_dm_persona_not_resolved")
        intent = str(row["intent"])
        link_type = self._link_type(intent)
        link = self._approved_link(int(row["creator_id"]), link_type)
        reply = self._reply_text(persona, intent, link)
        idempotency_key = hashlib.sha256(
            f"instagram-dm:{event_id}:{intent}:{persona}".encode("utf-8")
        ).hexdigest()
        now = utc_now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO instagram_dm_outbox
                    (conversation_id, trigger_event_id, response_type, reply_text,
                     idempotency_key, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'QUEUED', ?, ?)
                """,
                (row["conversation_id"], event_id, intent, reply, idempotency_key, now, now),
            )
            outbox_id = int(cursor.lastrowid)
            connection.execute(
                "UPDATE instagram_dm_events SET status='REPLY_QUEUED', processed_at=? WHERE id=?",
                (now, event_id),
            )
            connection.execute(
                "UPDATE instagram_dm_conversations SET status='REPLY_QUEUED', updated_at=? WHERE id=?",
                (now, row["conversation_id"]),
            )
            if intent == "CUSTOM_REQUEST":
                connection.execute(
                    """
                    INSERT OR IGNORE INTO instagram_dm_custom_requests
                        (conversation_id, trigger_event_id, request_type, status, created_at, updated_at)
                    VALUES (?, ?, 'CONTENT_REQUEST', 'RECEIVED', ?, ?)
                    """,
                    (row["conversation_id"], event_id, now, now),
                )
            if link_type is not None:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO instagram_dm_sales_events
                        (conversation_id, trigger_event_id, event_type, link_type, status, created_at)
                    VALUES (?, ?, 'INTENT', ?, ?, ?)
                    """,
                    (
                        row["conversation_id"],
                        event_id,
                        link_type,
                        "LINK_READY" if link else "NO_APPROVED_LINK",
                        now,
                    ),
                )
        stored = self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,))
        return self._outbox_result(stored, duplicate=False)

    @staticmethod
    def _outbox_result(row: Any, *, duplicate: bool) -> dict[str, object]:
        return {
            "outbox_id": int(row["id"]),
            "status": str(row["status"]),
            "response_type": str(row["response_type"]),
            "duplicate": duplicate,
            "provider_message_id": row["provider_message_id"],
            "external_action": False,
        }

    @staticmethod
    def _within_reply_window(value: str) -> bool:
        try:
            received = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if received.tzinfo is None:
                received = received.replace(tzinfo=UTC)
        except ValueError:
            return False
        age = datetime.now(UTC) - received.astimezone(UTC)
        return timedelta(0) <= age <= timedelta(hours=24)

    def dispatch_reply(self, outbox_id: int) -> dict[str, object]:
        row = self.database.one(
            """
            SELECT o.*, c.external_user_id, c.external_conversation_id,
                   c.last_received_at, c.status AS conversation_status,
                   e.provider_verified, cr.slug AS persona
            FROM instagram_dm_outbox o
            JOIN instagram_dm_conversations c ON c.id=o.conversation_id
            JOIN instagram_dm_events e ON e.id=o.trigger_event_id
            LEFT JOIN creators cr ON cr.id=c.creator_id
            WHERE o.id=?
            """,
            (outbox_id,),
        )
        if row is None:
            raise KeyError("instagram_dm_outbox_not_found")
        status = str(row["status"])
        if status in {"ACKNOWLEDGED", "DELIVERED"}:
            return self._outbox_result(row, duplicate=True)
        if status == "UNKNOWN":
            return {
                **self._outbox_result(row, duplicate=True),
                "reason": "reconcile_required_before_retry",
            }
        if not row["provider_verified"]:
            raise ValueError("provider_verified_inbound_required")
        if row["conversation_status"] == "NEEDS_HUMAN":
            raise ValueError("human_handoff_conversation_cannot_auto_reply")
        if not self._within_reply_window(str(row["last_received_at"])):
            self._mark_outbox(outbox_id, "EXPIRED", "instagram_24h_reply_window_closed")
            raise ValueError("instagram_24h_reply_window_closed")
        if self.provider is None or not self.provider.auto_reply_enabled:
            self._mark_outbox(outbox_id, "WAITING_PROVIDER", "provider_or_auto_reply_not_ready")
            return {
                **self._outbox_result(
                    self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)),
                    duplicate=False,
                ),
                "reason": "provider_or_auto_reply_not_ready",
            }
        try:
            provider_message_id = self.provider.send_message(
                str(row["persona"]), str(row["external_user_id"]), str(row["reply_text"])
            )
        except InstagramDMProviderConnectionError as error:
            self._mark_outbox(outbox_id, "UNKNOWN", str(error), increment=True)
            return {
                **self._outbox_result(
                    self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)),
                    duplicate=False,
                ),
                "reason": str(error),
            }
        except InstagramDMProviderError as error:
            self._mark_outbox(outbox_id, "FAILED", str(error), increment=True)
            return {
                **self._outbox_result(
                    self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)),
                    duplicate=False,
                ),
                "reason": str(error),
            }
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE instagram_dm_outbox
                SET status='ACKNOWLEDGED', provider_message_id=?, attempt_count=attempt_count+1,
                    last_error=NULL, sent_at=?, updated_at=? WHERE id=?
                """,
                (provider_message_id, now, now, outbox_id),
            )
            connection.execute(
                """
                UPDATE instagram_dm_conversations
                SET status='RESPONDED', last_outbound_at=?, updated_at=? WHERE id=?
                """,
                (now, now, row["conversation_id"]),
            )
        sent = self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,))
        return {**self._outbox_result(sent, duplicate=False), "external_action": True}

    def _mark_outbox(
        self, outbox_id: int, status: str, error: str | None, *, increment: bool = False
    ) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE instagram_dm_outbox
                SET status=?, last_error=?,
                    attempt_count=attempt_count + ?, updated_at=?
                WHERE id=?
                """,
                (status, error, 1 if increment else 0, utc_now(), outbox_id),
            )

    def reconcile_reply(self, outbox_id: int) -> dict[str, object]:
        row = self.database.one(
            """
            SELECT o.*, c.external_conversation_id, cr.slug AS persona
            FROM instagram_dm_outbox o
            JOIN instagram_dm_conversations c ON c.id=o.conversation_id
            LEFT JOIN creators cr ON cr.id=c.creator_id
            WHERE o.id=?
            """,
            (outbox_id,),
        )
        if row is None:
            raise KeyError("instagram_dm_outbox_not_found")
        if row["status"] == "DELIVERED":
            return self._outbox_result(row, duplicate=True)
        if self.provider is None or not row["provider_message_id"]:
            return {**self._outbox_result(row, duplicate=False), "reconciled": False}
        found = self.provider.reconcile_message(
            str(row["persona"]),
            str(row["external_conversation_id"]),
            str(row["provider_message_id"]),
        )
        if found is None:
            return {**self._outbox_result(row, duplicate=False), "reconciled": None}
        now = utc_now()
        next_status = "DELIVERED" if found else "FAILED_RECONCILE"
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE instagram_dm_outbox SET status=?, reconciled_at=?, updated_at=? WHERE id=?
                """,
                (next_status, now, now, outbox_id),
            )
        updated = self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,))
        return {**self._outbox_result(updated, duplicate=False), "reconciled": found}

    def process_event(self, event_id: int, *, dispatch: bool) -> dict[str, object]:
        queued = self.queue_reply(event_id)
        if queued.get("status") == "NEEDS_HUMAN" or not dispatch:
            return queued
        return self.dispatch_reply(int(queued["outbox_id"]))

    def record_delivery(self, provider_message_id: str) -> dict[str, object]:
        row = self.database.one(
            "SELECT * FROM instagram_dm_outbox WHERE provider_message_id=?",
            (provider_message_id,),
        )
        if row is None:
            return {"matched": False, "external_action": False}
        if row["status"] != "DELIVERED":
            now = utc_now()
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    UPDATE instagram_dm_outbox SET status='DELIVERED', reconciled_at=?, updated_at=?
                    WHERE id=?
                    """,
                    (now, now, row["id"]),
                )
        return {"matched": True, "outbox_id": int(row["id"]), "external_action": False}

    def process_webhook(self, raw_body: bytes, signature: str | None) -> dict[str, object]:
        if self.provider is None or not self.provider.verify_signature(raw_body, signature):
            raise ValueError("instagram_webhook_signature_invalid")
        results: list[dict[str, object]] = []
        for event in self.provider.parse_webhook(raw_body):
            if event.get("kind") == "OUTBOUND_ECHO":
                results.append(self.record_delivery(str(event["provider_message_id"])))
            elif event.get("kind") == "INBOUND":
                results.append(
                    self.ingest(
                        event["payload"], provider_verified=True, auto_process=True
                    )
                )
        return {"accepted": True, "events": len(results), "results": results}

    def sync_provider(self, persona: str | None = None) -> dict[str, object]:
        if self.provider is None:
            return {"status": "WAITING_PROVIDER", "personas": {}, "external_action": False}
        targets = [persona] if persona else ["leona-voss", "mara-field"]
        results: dict[str, object] = {}
        for slug in targets:
            creator = self.database.one("SELECT id FROM creators WHERE slug=?", (slug,))
            if creator is None:
                results[slug] = {"status": "UNKNOWN_PERSONA"}
                continue
            started = utc_now()
            seen = 0
            ingested = 0
            try:
                events = self.provider.poll(slug)
                seen = len(events)
                for payload in events:
                    result = self.ingest(
                        payload, provider_verified=True, auto_process=True
                    )
                    if not result["duplicate"]:
                        ingested += 1
                status = "SYNCED"
                error = None
            except (InstagramDMProviderError, InstagramDMProviderConnectionError) as provider_error:
                status = "ERROR"
                error = str(provider_error)
            now = utc_now()
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO instagram_dm_provider_sync
                        (creator_id, provider, status, messages_seen, messages_ingested,
                         last_started_at, last_success_at, last_error, updated_at)
                    VALUES (?, 'instagram-meta-graph', ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(creator_id) DO UPDATE SET
                        provider=excluded.provider, status=excluded.status,
                        messages_seen=excluded.messages_seen,
                        messages_ingested=excluded.messages_ingested,
                        last_started_at=excluded.last_started_at,
                        last_success_at=CASE WHEN excluded.status='SYNCED'
                            THEN excluded.last_success_at ELSE instagram_dm_provider_sync.last_success_at END,
                        last_error=excluded.last_error, updated_at=excluded.updated_at
                    """,
                    (
                        creator["id"], status, seen, ingested, started,
                        now if status == "SYNCED" else None, error, now,
                    ),
                )
                if status == "SYNCED":
                    connection.execute(
                        "UPDATE instagram_dm_conversations SET last_provider_sync_at=? WHERE creator_id=?",
                        (now, creator["id"]),
                    )
            results[slug] = {"status": status, "seen": seen, "ingested": ingested, "error": error}
        return {"status": "COMPLETE", "personas": results, "external_action": False}

    def dashboard(self, *, limit: int = 50) -> dict[str, object]:
        limit = min(max(int(limit), 1), 100)
        conversation_counts = {
            str(row["status"]): int(row["count"])
            for row in self.database.all(
                """
                SELECT status, COUNT(*) AS count
                FROM instagram_dm_conversations
                GROUP BY status ORDER BY status
                """
            )
        }
        intent_counts = {
            str(row["intent"]): int(row["count"])
            for row in self.database.all(
                """
                SELECT intent, COUNT(*) AS count
                FROM instagram_dm_events
                GROUP BY intent ORDER BY intent
                """
            )
        }
        rows = self.database.all(
            """
            SELECT e.id, e.intent, e.status, e.handoff_reason, e.received_at,
                   e.provider_verified, cr.slug AS persona, cr.display_name,
                   o.id AS outbox_id, o.status AS reply_status,
                   o.response_type, o.sent_at, o.reconciled_at
            FROM instagram_dm_events e
            JOIN instagram_dm_conversations c ON c.id=e.conversation_id
            LEFT JOIN creators cr ON cr.id=c.creator_id
            LEFT JOIN instagram_dm_outbox o ON o.trigger_event_id=e.id
            ORDER BY e.received_at DESC, e.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        total = sum(conversation_counts.values())
        outbox_counts = {
            str(row["status"]): int(row["count"])
            for row in self.database.all(
                "SELECT status, COUNT(*) AS count FROM instagram_dm_outbox GROUP BY status"
            )
        }
        provider_sync = [dict(row) for row in self.database.all(
            """
            SELECT cr.slug AS persona, s.status, s.messages_seen, s.messages_ingested,
                   s.last_success_at, s.last_error
            FROM instagram_dm_provider_sync s
            JOIN creators cr ON cr.id=s.creator_id ORDER BY cr.slug
            """
        )]
        readiness = self.provider.readiness() if self.provider is not None else {
            "provider": "unconfigured", "webhook_ready": False,
            "auto_reply_enabled": False, "personas": {},
        }
        return {
            "schema": "zippoworkz-instagram-dm-p1-v1",
            "mode": "PROVIDER_VERIFIED_AUTONOMY_P1",
            "send_enabled": bool(readiness.get("auto_reply_enabled")),
            "webhook_registered": bool(readiness.get("webhook_ready")),
            "provider": readiness,
            "provider_sync": provider_sync,
            "counts": {
                "open": conversation_counts.get("OPEN", 0),
                "needs_human": conversation_counts.get("NEEDS_HUMAN", 0),
                "total": total,
                "events": int(
                    self.database.scalar("SELECT COUNT(*) FROM instagram_dm_events") or 0
                ),
                "queued": outbox_counts.get("QUEUED", 0),
                "acknowledged": outbox_counts.get("ACKNOWLEDGED", 0),
                "delivered": outbox_counts.get("DELIVERED", 0),
                "uncertain": outbox_counts.get("UNKNOWN", 0),
                "custom_requests": int(self.database.scalar(
                    "SELECT COUNT(*) FROM instagram_dm_custom_requests"
                ) or 0),
                "sales_signals": int(self.database.scalar(
                    "SELECT COUNT(*) FROM instagram_dm_sales_events"
                ) or 0),
            },
            "by_intent": intent_counts,
            "items": [
                {
                    "id": int(row["id"]),
                    "persona": str(row["persona"] or "UNKNOWN"),
                    "display_name": str(row["display_name"] or "Nicht zugeordnet"),
                    "intent": str(row["intent"]),
                    "status": str(row["status"]),
                    "received_at": str(row["received_at"]),
                    "handoff_reason": row["handoff_reason"],
                    "provider_verified": bool(row["provider_verified"]),
                    "outbox_id": row["outbox_id"],
                    "reply_status": row["reply_status"],
                    "response_type": row["response_type"],
                    "sent_at": row["sent_at"],
                    "reconciled_at": row["reconciled_at"],
                }
                for row in rows
            ],
        }
