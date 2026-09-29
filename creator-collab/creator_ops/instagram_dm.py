from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Protocol

from .database import CreatorDatabase, utc_now


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
    """Read-only-outbound DM P0: ingest, classify, persist, and display only."""

    def __init__(
        self,
        database: CreatorDatabase,
        classifier: IntentClassifier | None = None,
    ) -> None:
        self.database = database
        self.normalizer = InstagramDMInboundNormalizer()
        self.classifier = classifier or DeterministicIntentClassifier()
        self.safety = DMSafetyPolicy()

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
            "duplicate": True,
            "persona": str(row["persona"] or "UNKNOWN"),
            "intent": str(row["intent"]),
            "status": str(row["status"]),
            "handoff_reason": row["handoff_reason"],
            "send_enabled": False,
            "external_action": False,
        }

    def ingest(self, payload: object) -> dict[str, object]:
        event = self.normalizer.normalize(payload)
        existing = self.database.one(
            """
            SELECT e.id, e.intent, e.status, e.handoff_reason, cr.slug AS persona
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
                SELECT e.id, e.intent, e.status, e.handoff_reason, cr.slug AS persona
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
                     status, handoff_reason, received_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
            event_id = int(cursor.lastrowid)

        return {
            "event_id": event_id,
            "duplicate": False,
            "persona": persona or "UNKNOWN",
            "intent": stored_intent,
            "status": status,
            "handoff_reason": handoff_reason,
            "send_enabled": False,
            "external_action": False,
        }

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
                   cr.slug AS persona, cr.display_name
            FROM instagram_dm_events e
            JOIN instagram_dm_conversations c ON c.id=e.conversation_id
            LEFT JOIN creators cr ON cr.id=c.creator_id
            ORDER BY e.received_at DESC, e.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        total = sum(conversation_counts.values())
        return {
            "schema": "zippoworkz-instagram-dm-p0-v1",
            "mode": "SEND_DISABLED_READ_ONLY_P0",
            "send_enabled": False,
            "webhook_registered": False,
            "counts": {
                "open": conversation_counts.get("OPEN", 0),
                "needs_human": conversation_counts.get("NEEDS_HUMAN", 0),
                "total": total,
                "events": int(
                    self.database.scalar("SELECT COUNT(*) FROM instagram_dm_events") or 0
                ),
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
                }
                for row in rows
            ],
        }
