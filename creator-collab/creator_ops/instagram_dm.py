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
REPLY_STATUSES = (
    "DRAFTED",
    "OWNER_REVIEW",
    "APPROVED",
    "SEND_PENDING",
    "SENT",
    "DELIVERED",
    "FAILED",
    "RECONCILE_REQUIRED",
    "CANCELLED",
)
PAYMENT_STATUSES = (
    "NOT_APPLICABLE",
    "OPEN",
    "CONFIRMED",
    "FAILED_OR_NOT_RECEIVED",
    "UNKNOWN",
)
SALES_INTENTS = {
    "CUSTOM_REQUEST",
    "SUPPORT_INTENT",
    "WISHLIST_INTENT",
    "PAYPAL_INTENT",
    "MERCH_INTENT",
}


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
                # Providers return history newest-first. An older message
                # must never move the conversation's reply window backwards.
                connection.execute(
                    """
                    UPDATE instagram_dm_conversations
                    SET external_user_id=?, creator_id=?,
                        last_intent=CASE WHEN ? >= last_received_at
                            THEN ? ELSE last_intent END,
                        status=?, handoff_reason=?,
                        last_received_at=MAX(last_received_at, ?), updated_at=?
                    WHERE id=?
                    """,
                    (
                        event.external_user_id,
                        next_creator,
                        event.received_at,
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
            result["processing"] = self.auto_process_event(event_id)
        return result

    def auto_process_event(
        self, event_id: int, *, provider_answered: bool = False
    ) -> dict[str, object]:
        """Reply at most once per conversation turn and never abort a batch.

        Only the newest inbound message of a conversation is answered, and
        only while nobody has answered it yet. Every refusal is local and
        leaves no provider write behind.
        """
        row = self.database.one(
            """
            SELECT e.id, e.received_at, c.last_outbound_at,
                   (SELECT e2.id FROM instagram_dm_events e2
                    WHERE e2.conversation_id=e.conversation_id
                      AND e2.direction='INBOUND'
                    ORDER BY e2.received_at DESC, e2.id DESC LIMIT 1) AS newest_id
            FROM instagram_dm_events e
            JOIN instagram_dm_conversations c ON c.id=e.conversation_id
            WHERE e.id=?
            """,
            (event_id,),
        )
        if row is None:
            raise KeyError("instagram_dm_event_not_found")
        reason = None
        if int(row["newest_id"]) != event_id:
            reason = "superseded_by_newer_inbound"
        elif provider_answered:
            reason = "already_answered_in_provider_thread"
        elif row["last_outbound_at"] and str(row["last_outbound_at"]) >= str(row["received_at"]):
            reason = "already_answered"
        elif not self._within_reply_window(str(row["received_at"])):
            reason = "instagram_24h_reply_window_closed"
        if reason is not None:
            return {"event_id": event_id, "status": "SKIPPED", "reason": reason, "external_action": False}
        try:
            return self.process_event(event_id, dispatch=True)
        except ValueError as error:
            # Raised only before a provider write was claimed.
            return {"event_id": event_id, "status": "NOT_DISPATCHED", "reason": str(error), "external_action": False}

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
        owner_review_reason = (
            "custom_request_requires_owner_review"
            if intent == "CUSTOM_REQUEST"
            else None
        )
        reply_status = "OWNER_REVIEW" if owner_review_reason else "DRAFTED"
        idempotency_key = hashlib.sha256(
            f"instagram-dm:{event_id}:{intent}:{persona}".encode("utf-8")
        ).hexdigest()
        now = utc_now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO instagram_dm_outbox
                    (conversation_id, trigger_event_id, response_type, reply_text,
                     idempotency_key, status, owner_review_reason, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["conversation_id"],
                    event_id,
                    intent,
                    reply,
                    idempotency_key,
                    reply_status,
                    owner_review_reason,
                    now,
                    now,
                ),
            )
            outbox_id = int(cursor.lastrowid)
            connection.execute(
                "UPDATE instagram_dm_events SET status=?, processed_at=? WHERE id=?",
                (
                    "OWNER_REVIEW" if owner_review_reason else "REPLY_DRAFTED",
                    now,
                    event_id,
                ),
            )
            connection.execute(
                "UPDATE instagram_dm_conversations SET status=?, updated_at=? WHERE id=?",
                (
                    "OWNER_REVIEW" if owner_review_reason else "REPLY_DRAFTED",
                    now,
                    row["conversation_id"],
                ),
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
            if intent in SALES_INTENTS:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO instagram_dm_sales_events
                        (conversation_id, trigger_event_id, event_type, link_type,
                         status, payment_status, created_at)
                    VALUES (?, ?, ?, ?, 'OPEN', 'OPEN', ?)
                    """,
                    (
                        row["conversation_id"],
                        event_id,
                        "CUSTOM_REQUEST" if intent == "CUSTOM_REQUEST" else "INTENT",
                        link_type,
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
            "owner_review_reason": row["owner_review_reason"],
            "external_action": False,
        }

    def request_owner_review(self, outbox_id: int, reason: str) -> dict[str, object]:
        normalized = str(reason or "").strip()
        if not normalized:
            raise ValueError("owner_review_reason_required")
        row = self.database.one(
            "SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)
        )
        if row is None:
            raise KeyError("instagram_dm_outbox_not_found")
        if row["status"] == "OWNER_REVIEW":
            return self._outbox_result(row, duplicate=True)
        if row["status"] != "DRAFTED":
            raise ValueError("reply_not_reviewable")
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE instagram_dm_outbox
                SET status='OWNER_REVIEW', owner_review_reason=?, updated_at=?
                WHERE id=?
                """,
                (normalized, now, outbox_id),
            )
            connection.execute(
                """
                UPDATE instagram_dm_conversations
                SET status='OWNER_REVIEW', updated_at=?
                WHERE id=(SELECT conversation_id FROM instagram_dm_outbox WHERE id=?)
                """,
                (now, outbox_id),
            )
        return self._outbox_result(
            self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)),
            duplicate=False,
        )

    def approve_reply(self, outbox_id: int) -> dict[str, object]:
        row = self.database.one(
            "SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)
        )
        if row is None:
            raise KeyError("instagram_dm_outbox_not_found")
        if row["status"] == "APPROVED":
            return self._outbox_result(row, duplicate=True)
        if row["status"] not in {"DRAFTED", "OWNER_REVIEW"}:
            raise ValueError("reply_not_approvable")
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE instagram_dm_outbox
                SET status='APPROVED', approved_at=?, last_error=NULL, updated_at=?
                WHERE id=?
                """,
                (now, now, outbox_id),
            )
            connection.execute(
                """
                UPDATE instagram_dm_conversations
                SET status='REPLY_APPROVED', updated_at=?
                WHERE id=(SELECT conversation_id FROM instagram_dm_outbox WHERE id=?)
                """,
                (now, outbox_id),
            )
        return self._outbox_result(
            self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)),
            duplicate=False,
        )

    def cancel_reply(self, outbox_id: int) -> dict[str, object]:
        row = self.database.one(
            "SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)
        )
        if row is None:
            raise KeyError("instagram_dm_outbox_not_found")
        if row["status"] == "CANCELLED":
            return self._outbox_result(row, duplicate=True)
        if row["status"] in {
            "SENT", "DELIVERED", "SEND_PENDING", "RECONCILE_REQUIRED"
        }:
            raise ValueError("reply_cannot_be_cancelled_after_send_started")
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE instagram_dm_outbox
                SET status='CANCELLED', cancelled_at=?, updated_at=? WHERE id=?
                """,
                (now, now, outbox_id),
            )
            connection.execute(
                """
                UPDATE instagram_dm_conversations
                SET status='OPEN', updated_at=?
                WHERE id=(SELECT conversation_id FROM instagram_dm_outbox WHERE id=?)
                """,
                (now, outbox_id),
            )
        return self._outbox_result(
            self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)),
            duplicate=False,
        )

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
        if status in {"SENT", "DELIVERED", "CANCELLED", "FAILED"}:
            return self._outbox_result(row, duplicate=True)
        if status in {"SEND_PENDING", "RECONCILE_REQUIRED"}:
            if status == "SEND_PENDING":
                self._mark_outbox(
                    outbox_id,
                    "RECONCILE_REQUIRED",
                    "send_started_without_confirmed_provider_receipt",
                )
                row = self.database.one(
                    "SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)
                )
            return {
                **self._outbox_result(row, duplicate=True),
                "reason": "reconcile_required_before_retry",
            }
        if status in {"DRAFTED", "OWNER_REVIEW"}:
            return {
                **self._outbox_result(row, duplicate=True),
                "reason": "reply_approval_required",
            }
        if status != "APPROVED":
            raise ValueError("reply_status_not_dispatchable")
        if not row["provider_verified"]:
            raise ValueError("provider_verified_inbound_required")
        if row["conversation_status"] == "NEEDS_HUMAN":
            raise ValueError("human_handoff_conversation_cannot_auto_reply")
        if not self._within_reply_window(str(row["last_received_at"])):
            self._mark_outbox(outbox_id, "FAILED", "instagram_24h_reply_window_closed")
            raise ValueError("instagram_24h_reply_window_closed")
        if self.provider is None or not self.provider.auto_reply_enabled:
            self._mark_outbox(outbox_id, "FAILED", "provider_or_auto_reply_not_ready")
            return {
                **self._outbox_result(
                    self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)),
                    duplicate=False,
                ),
                "reason": "provider_or_auto_reply_not_ready",
            }

        # Claim the approved reply before touching the provider. A second
        # execution can never issue a second send from this point onward.
        now = utc_now()
        with self.database.transaction() as connection:
            claimed = connection.execute(
                """
                UPDATE instagram_dm_outbox
                SET status='SEND_PENDING', attempt_count=attempt_count+1,
                    last_error=NULL, updated_at=?
                WHERE id=? AND status='APPROVED'
                """,
                (now, outbox_id),
            )
            if claimed.rowcount != 1:
                current = connection.execute(
                    "SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)
                ).fetchone()
                return {
                    **self._outbox_result(current, duplicate=True),
                    "reason": "reply_dispatch_already_claimed",
                }
        try:
            provider_message_id = self.provider.send_message(
                str(row["persona"]), str(row["external_user_id"]), str(row["reply_text"])
            )
        except InstagramDMProviderConnectionError as error:
            self._mark_outbox(outbox_id, "RECONCILE_REQUIRED", str(error))
            return {
                **self._outbox_result(
                    self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)),
                    duplicate=False,
                ),
                "reason": str(error),
            }
        except InstagramDMProviderError as error:
            self._mark_outbox(outbox_id, "FAILED", str(error))
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
                SET status='SENT', provider_message_id=?,
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
        if str(row["external_conversation_id"]).startswith("webhook-igsid:"):
            self._mark_outbox(
                outbox_id,
                "RECONCILE_REQUIRED",
                "VERIFY_OFFICIAL_META_CONVERSATION_ID_REQUIRED",
            )
            updated = self.database.one(
                "SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,)
            )
            return {
                **self._outbox_result(updated, duplicate=False),
                "reconciled": None,
                "reason": "VERIFY_OFFICIAL_META_CONVERSATION_ID_REQUIRED",
            }
        found = self.provider.reconcile_message(
            str(row["persona"]),
            str(row["external_conversation_id"]),
            str(row["provider_message_id"]),
        )
        if found is None:
            self._mark_outbox(
                outbox_id, "RECONCILE_REQUIRED", "provider_reconciliation_uncertain"
            )
            return {**self._outbox_result(row, duplicate=False), "reconciled": None}
        now = utc_now()
        next_status = "DELIVERED" if found else "RECONCILE_REQUIRED"
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE instagram_dm_outbox
                SET status=?, reconciled_at=?,
                    last_error=CASE WHEN ? THEN NULL ELSE 'provider_message_not_yet_confirmed' END,
                    updated_at=? WHERE id=?
                """,
                (next_status, now, 1 if found else 0, now, outbox_id),
            )
        updated = self.database.one("SELECT * FROM instagram_dm_outbox WHERE id=?", (outbox_id,))
        return {**self._outbox_result(updated, duplicate=False), "reconciled": found}

    def process_event(self, event_id: int, *, dispatch: bool) -> dict[str, object]:
        queued = self.queue_reply(event_id)
        if queued.get("status") in {"NEEDS_HUMAN", "OWNER_REVIEW"} or not dispatch:
            return queued
        if self.provider is None or not self.provider.auto_reply_enabled:
            return {
                **queued,
                "reason": "provider_or_auto_reply_not_ready",
            }
        approved = self.approve_reply(int(queued["outbox_id"]))
        if approved["status"] != "APPROVED":
            return approved
        return self.dispatch_reply(int(queued["outbox_id"]))

    def record_delivery(self, provider_message_id: str) -> dict[str, object]:
        row = self.database.one(
            "SELECT * FROM instagram_dm_outbox WHERE provider_message_id=?",
            (provider_message_id,),
        )
        if row is None:
            return {"matched": False, "external_action": False}
        if row["status"] not in {"SENT", "RECONCILE_REQUIRED", "DELIVERED"}:
            return {
                "matched": False,
                "outbox_id": int(row["id"]),
                "reason": "delivery_not_valid_for_reply_state",
                "external_action": False,
            }
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

    def set_payment_state(
        self,
        sales_event_id: int,
        status: str,
        *,
        expected_amount: float | None = None,
        expected_currency: str | None = None,
    ) -> dict[str, object]:
        """Update non-confirmed payment truth without creating revenue."""
        normalized = str(status or "").strip().upper()
        if normalized not in PAYMENT_STATUSES:
            raise ValueError("instagram_dm_payment_status_invalid")
        if normalized == "CONFIRMED":
            raise ValueError("confirmed_payment_requires_revenue_event")
        if expected_amount is not None and float(expected_amount) < 0:
            raise ValueError("expected_amount_must_be_non_negative")
        currency = str(expected_currency or "").strip().upper() or None
        if expected_amount is not None and currency is None:
            raise ValueError("expected_currency_required")
        existing = self.database.one(
            "SELECT id, revenue_event_id FROM instagram_dm_sales_events WHERE id=?",
            (sales_event_id,),
        )
        if existing is None:
            raise KeyError("instagram_dm_sales_event_not_found")
        if existing["revenue_event_id"] is not None:
            raise ValueError("confirmed_payment_cannot_be_downgraded")
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE instagram_dm_sales_events
                SET payment_status=?, status=?, expected_amount=?, expected_currency=?
                WHERE id=?
                """,
                (
                    normalized,
                    "OPEN" if normalized == "OPEN" else normalized,
                    expected_amount,
                    currency,
                    sales_event_id,
                ),
            )
        return self.payment_state(sales_event_id)

    def confirm_payment_from_revenue(
        self, sales_event_id: int, revenue_event_id: int
    ) -> dict[str, object]:
        """Bind a DM sales signal to one verified row in the existing ledger."""
        sales = self.database.one(
            """
            SELECT s.id, s.revenue_event_id, c.creator_id
            FROM instagram_dm_sales_events s
            JOIN instagram_dm_conversations c ON c.id=s.conversation_id
            WHERE s.id=?
            """,
            (sales_event_id,),
        )
        if sales is None:
            raise KeyError("instagram_dm_sales_event_not_found")
        revenue = self.database.one(
            "SELECT id, creator_id, amount, currency FROM revenue_events WHERE id=?",
            (revenue_event_id,),
        )
        if revenue is None:
            raise ValueError("verified_revenue_event_required")
        if int(revenue["creator_id"]) != int(sales["creator_id"]):
            raise ValueError("revenue_event_persona_mismatch")
        if float(revenue["amount"]) <= 0:
            raise ValueError("positive_revenue_event_required")
        if sales["revenue_event_id"] is not None:
            if int(sales["revenue_event_id"]) == int(revenue_event_id):
                return self.payment_state(sales_event_id, duplicate=True)
            raise ValueError("dm_sale_already_bound_to_revenue")
        duplicate = self.database.one(
            "SELECT id FROM instagram_dm_sales_events WHERE revenue_event_id=? AND id<>?",
            (revenue_event_id, sales_event_id),
        )
        if duplicate is not None:
            raise ValueError("revenue_event_already_attributed")
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE instagram_dm_sales_events
                SET payment_status='CONFIRMED', status='CONFIRMED', revenue_event_id=?
                WHERE id=? AND revenue_event_id IS NULL
                """,
                (revenue_event_id, sales_event_id),
            )
        return self.payment_state(sales_event_id)

    def payment_state(
        self, sales_event_id: int, *, duplicate: bool = False
    ) -> dict[str, object]:
        row = self.database.one(
            """
            SELECT s.id, s.payment_status, s.expected_amount, s.expected_currency,
                   s.offer_ref, s.revenue_event_id,
                   r.amount AS confirmed_revenue, r.currency AS confirmed_currency
            FROM instagram_dm_sales_events s
            LEFT JOIN revenue_events r ON r.id=s.revenue_event_id
            WHERE s.id=?
            """,
            (sales_event_id,),
        )
        if row is None:
            raise KeyError("instagram_dm_sales_event_not_found")
        return {
            "sales_event_id": int(row["id"]),
            "payment_status": str(row["payment_status"]),
            "expected_amount": row["expected_amount"],
            "expected_currency": row["expected_currency"],
            "offer_ref": row["offer_ref"],
            "revenue_event_id": row["revenue_event_id"],
            "confirmed_revenue": row["confirmed_revenue"],
            "confirmed_currency": row["confirmed_currency"],
            "duplicate": duplicate,
            "external_action": False,
        }

    def process_webhook(self, raw_body: bytes, signature: str | None) -> dict[str, object]:
        if self.provider is None or not self.provider.verify_signature(raw_body, signature):
            raise ValueError("instagram_webhook_signature_invalid")
        results: list[dict[str, object]] = []
        rejected = 0
        new_inbound: list[dict[str, object]] = []
        for event in self.provider.parse_webhook(raw_body):
            if event.get("kind") == "OUTBOUND_ECHO":
                results.append(self.record_delivery(str(event["provider_message_id"])))
            elif event.get("kind") == "INBOUND":
                try:
                    result = self.ingest(event["payload"], provider_verified=True)
                except InboundValidationError:
                    rejected += 1
                    continue
                results.append(result)
                if not result["duplicate"] and result["status"] == "OPEN":
                    new_inbound.append(result)
            else:
                rejected += 1
        # Store the whole batch first so only the newest message per
        # conversation can trigger a reply.
        for result in new_inbound:
            result["processing"] = self.auto_process_event(int(result["event_id"]))
        return {
            "accepted": True,
            "events": len(results),
            "rejected": rejected,
            "results": results,
        }

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
            rejected = 0
            replies_sent = 0
            try:
                events = self.provider.poll(slug)
                seen = len(events)
                new_inbound: list[tuple[int, bool]] = []
                for payload in events:
                    try:
                        result = self.ingest(payload, provider_verified=True)
                    except InboundValidationError:
                        rejected += 1
                        continue
                    if not result["duplicate"]:
                        ingested += 1
                        if result["status"] == "OPEN":
                            new_inbound.append((
                                int(result["event_id"]),
                                bool(payload.get("provider_answered")),
                            ))
                # Store the whole batch first so only the newest message per
                # conversation can trigger a reply.
                for event_id, answered in new_inbound:
                    processed = self.auto_process_event(
                        event_id, provider_answered=answered
                    )
                    if processed.get("status") == "SENT":
                        replies_sent += 1
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
            results[slug] = {
                "status": status, "seen": seen, "ingested": ingested,
                "rejected": rejected, "replies_sent": replies_sent, "error": error,
            }
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
            WITH latest_event AS (
                SELECT e.* FROM instagram_dm_events e
                WHERE e.id=(SELECT e2.id FROM instagram_dm_events e2
                            WHERE e2.conversation_id=e.conversation_id
                            ORDER BY e2.received_at DESC, e2.id DESC LIMIT 1)
            ), latest_reply AS (
                SELECT o.* FROM instagram_dm_outbox o
                WHERE o.id=(SELECT o2.id FROM instagram_dm_outbox o2
                            WHERE o2.conversation_id=o.conversation_id
                            ORDER BY o2.id DESC LIMIT 1)
            ), sales AS (
                SELECT s.conversation_id,
                       COUNT(*) AS sales_signal_count,
                       MAX(s.offer_ref) AS offer_ref,
                       MAX(CASE s.payment_status
                           WHEN 'CONFIRMED' THEN 5 WHEN 'OPEN' THEN 4
                           WHEN 'UNKNOWN' THEN 3 WHEN 'FAILED_OR_NOT_RECEIVED' THEN 2
                           ELSE 1 END) AS payment_rank,
                       SUM(CASE WHEN s.payment_status='OPEN' THEN s.expected_amount END)
                           AS expected_open_amount,
                       MAX(CASE WHEN s.payment_status='OPEN' THEN s.expected_currency END)
                           AS expected_currency,
                       SUM(CASE WHEN s.payment_status='CONFIRMED' THEN r.amount END)
                           AS confirmed_revenue,
                       MAX(CASE WHEN s.payment_status='CONFIRMED' THEN r.currency END)
                           AS confirmed_currency
                FROM instagram_dm_sales_events s
                LEFT JOIN revenue_events r ON r.id=s.revenue_event_id
                GROUP BY s.conversation_id
            )
            SELECT c.id AS conversation_id, c.external_conversation_id,
                   c.last_intent, c.status, c.handoff_reason,
                   c.last_received_at, c.last_outbound_at,
                   cr.slug AS persona, cr.display_name,
                   e.id AS event_id, e.provider_verified,
                   o.id AS outbox_id, o.status AS reply_status,
                   o.response_type, o.owner_review_reason, o.sent_at, o.reconciled_at,
                   COALESCE(s.sales_signal_count, 0) AS sales_signal_count,
                   s.offer_ref, s.payment_rank, s.expected_open_amount,
                   s.expected_currency, s.confirmed_revenue, s.confirmed_currency
            FROM instagram_dm_conversations c
            LEFT JOIN creators cr ON cr.id=c.creator_id
            LEFT JOIN latest_event e ON e.conversation_id=c.id
            LEFT JOIN latest_reply o ON o.conversation_id=c.id
            LEFT JOIN sales s ON s.conversation_id=c.id
            ORDER BY c.last_received_at DESC, c.id DESC
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
        payment_name = {
            5: "CONFIRMED", 4: "OPEN", 3: "UNKNOWN",
            2: "FAILED_OR_NOT_RECEIVED", 1: "NOT_APPLICABLE",
        }
        items: list[dict[str, object]] = []
        for row in rows:
            reply_status = str(row["reply_status"] or "") or None
            payment_status = payment_name.get(int(row["payment_rank"] or 1), "NOT_APPLICABLE")
            owner_review = bool(
                row["status"] == "NEEDS_HUMAN" or reply_status == "OWNER_REVIEW"
            )
            reconciliation = (
                "REQUIRED" if reply_status == "RECONCILE_REQUIRED"
                else "COMPLETE" if reply_status == "DELIVERED"
                else "NOT_REQUIRED"
            )
            if owner_review:
                next_action = "OWNER_REVIEW"
            elif reply_status == "DRAFTED":
                next_action = "APPROVE_OR_CHANGE"
            elif reply_status == "APPROVED":
                next_action = "DISPATCH"
            elif reply_status == "RECONCILE_REQUIRED":
                next_action = "RECONCILE"
            elif reply_status in {"SENT", "DELIVERED"}:
                next_action = "WAIT_OR_FOLLOW_UP"
            else:
                next_action = "PREPARE_REPLY"
            items.append({
                "id": int(row["event_id"] or 0),
                "conversation_id": int(row["conversation_id"]),
                "conversation_ref": str(row["external_conversation_id"]),
                "persona": str(row["persona"] or "UNKNOWN"),
                "display_name": str(row["display_name"] or "Nicht zugeordnet"),
                "intent": str(row["last_intent"]),
                "status": str(row["status"]),
                "sales_signal": bool(row["sales_signal_count"]),
                "sales_signal_count": int(row["sales_signal_count"]),
                "reply_status": reply_status,
                "outbox_id": row["outbox_id"],
                "response_type": row["response_type"],
                "owner_review": owner_review,
                "owner_review_reason": row["owner_review_reason"] or row["handoff_reason"],
                "known_offer": row["offer_ref"],
                "payment_status": payment_status,
                "confirmed_revenue": row["confirmed_revenue"],
                "confirmed_currency": row["confirmed_currency"],
                "expected_open_amount": row["expected_open_amount"],
                "expected_currency": row["expected_currency"],
                "last_contact": str(row["last_received_at"]),
                "last_outbound_at": row["last_outbound_at"],
                "next_action": next_action,
                "handoff_reason": row["handoff_reason"],
                "reconciliation_state": reconciliation,
                "provider_verified": bool(row["provider_verified"]),
                "sent_at": row["sent_at"],
                "reconciled_at": row["reconciled_at"],
            })

        confirmed_revenue_rows = self.database.all(
            """
            SELECT r.currency, SUM(r.amount) AS amount
            FROM instagram_dm_sales_events s
            JOIN revenue_events r ON r.id=s.revenue_event_id
            WHERE s.payment_status='CONFIRMED'
            GROUP BY r.currency ORDER BY r.currency
            """
        )
        confirmed_revenue_by_currency = {
            str(row["currency"]): float(row["amount"])
            for row in confirmed_revenue_rows
        }
        confirmed_dm_revenue = (
            next(iter(confirmed_revenue_by_currency.values()))
            if len(confirmed_revenue_by_currency) == 1 else None
        )
        owner_reviews = int(self.database.scalar(
            """
            SELECT COUNT(*) FROM instagram_dm_conversations c
            WHERE c.status='NEEDS_HUMAN'
               OR EXISTS (
                   SELECT 1 FROM instagram_dm_outbox o
                   WHERE o.conversation_id=c.id AND o.status='OWNER_REVIEW'
               )
            """
        ) or 0)
        failures = int(self.database.scalar(
            """
            SELECT COUNT(*) FROM instagram_dm_conversations c
            WHERE c.status='NEEDS_HUMAN'
               OR EXISTS (
                   SELECT 1 FROM instagram_dm_outbox o
                   WHERE o.conversation_id=c.id AND o.status='FAILED'
               )
            """
        ) or 0)
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
                "open_conversations": sum(
                    count for status, count in conversation_counts.items()
                    if status not in {"CLOSED", "ARCHIVED"}
                ),
                "owner_reviews": owner_reviews,
                "replies_pending": sum(outbox_counts.get(status, 0) for status in (
                    "DRAFTED", "OWNER_REVIEW", "APPROVED", "SEND_PENDING"
                )),
                "replies_sent": outbox_counts.get("SENT", 0) + outbox_counts.get("DELIVERED", 0),
                "replies_reconcile": outbox_counts.get("RECONCILE_REQUIRED", 0),
                "open_payments": int(self.database.scalar(
                    "SELECT COUNT(*) FROM instagram_dm_sales_events WHERE payment_status='OPEN'"
                ) or 0),
                "confirmed_dm_revenue": confirmed_dm_revenue,
                "confirmed_dm_revenue_by_currency": confirmed_revenue_by_currency,
                "failures_needs_human": failures,
                "queued": outbox_counts.get("DRAFTED", 0),
                "acknowledged": outbox_counts.get("SENT", 0),
                "delivered": outbox_counts.get("DELIVERED", 0),
                "uncertain": outbox_counts.get("RECONCILE_REQUIRED", 0),
                "custom_requests": int(self.database.scalar(
                    "SELECT COUNT(*) FROM instagram_dm_custom_requests"
                ) or 0),
                "sales_signals": int(self.database.scalar(
                    "SELECT COUNT(*) FROM instagram_dm_sales_events"
                ) or 0),
            },
            "by_intent": intent_counts,
            "items": items,
        }
