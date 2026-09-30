from __future__ import annotations

import hashlib
import hmac
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .publishing import MetaGraphError, MetaGraphTransport, UrllibMetaGraphTransport
from .secrets import get_secret


PERSONA_SECRET_NAMES = {
    "leona-voss": ("META_IG_USER_ID_LEONA_VOSS", "META_ACCESS_TOKEN_LEONA_VOSS"),
    "mara-field": ("META_IG_USER_ID_MARA_FIELD", "META_ACCESS_TOKEN_MARA_FIELD"),
}


class InstagramDMProviderError(RuntimeError):
    """Sanitized provider failure. It never contains tokens or response bodies."""


class InstagramDMProviderConnectionError(InstagramDMProviderError):
    """The write result may be uncertain and must be reconciled before retry."""


class InstagramDMProvider(Protocol):
    auto_reply_enabled: bool

    def readiness(self) -> dict[str, object]: ...

    def verify_challenge(self, mode: str, token: str, challenge: str) -> str: ...

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool: ...

    def parse_webhook(self, raw_body: bytes) -> list[dict[str, object]]: ...

    def poll(self, persona: str) -> list[dict[str, object]]: ...

    def send_message(self, persona: str, recipient_id: str, text: str) -> str: ...

    def reconcile_message(
        self, persona: str, conversation_id: str, provider_message_id: str
    ) -> bool | None: ...


@dataclass(frozen=True)
class _Account:
    persona: str
    account_id: str
    access_token: str


class MetaInstagramDMProvider:
    """Official Meta Graph adapter for Instagram conversations and replies.

    Credentials remain in process environment or the node-local Secret Broker.
    This adapter returns only secret-free readiness and sanitized error codes.
    """

    provider = "instagram-meta-graph"

    def __init__(
        self,
        *,
        accounts: dict[str, tuple[str, str]],
        graph_version: str,
        graph_host: str,
        app_secret: str = "",
        verify_token: str = "",
        auto_reply_enabled: bool = False,
        transport_factory: Callable[[str], MetaGraphTransport] | None = None,
    ) -> None:
        if not re.fullmatch(r"v\d+\.\d+", graph_version):
            raise ValueError("meta_graph_version_required")
        self.graph_version = graph_version
        self.graph_host = graph_host
        self.app_secret = app_secret
        self.verify_token = verify_token
        self.auto_reply_enabled = bool(auto_reply_enabled)
        self._accounts = {
            persona: _Account(persona, str(values[0]), str(values[1]))
            for persona, values in accounts.items()
            if values[0] and values[1]
        }
        self._transport_factory = transport_factory

    @classmethod
    def from_runtime(
        cls, project_root: Path, config_path: Path | None = None
    ) -> "MetaInstagramDMProvider":
        config: dict[str, object] = {}
        path = config_path or project_root / "config.toml"
        if path.is_file():
            config = tomllib.loads(path.read_text(encoding="utf-8"))
        dm_config = config.get("instagram_dm", {})
        if not isinstance(dm_config, dict):
            dm_config = {}
        node_root = cls._node_root(project_root)
        graph_version = get_secret("META_GRAPH_API_VERSION", "v24.0", root=node_root)
        graph_host = get_secret(
            "META_GRAPH_HOST", "graph.instagram.com", root=node_root
        )
        accounts: dict[str, tuple[str, str]] = {}
        for persona, (id_name, token_name) in PERSONA_SECRET_NAMES.items():
            account_id = get_secret(id_name, root=node_root)
            token = get_secret(token_name, root=node_root)
            if account_id and token:
                accounts[persona] = (account_id, token)
        return cls(
            accounts=accounts,
            graph_version=graph_version,
            graph_host=graph_host,
            app_secret=get_secret("META_APP_SECRET", root=node_root),
            verify_token=get_secret("META_DM_WEBHOOK_VERIFY_TOKEN", root=node_root),
            auto_reply_enabled=bool(dm_config.get("auto_reply_enabled", False)),
        )

    @staticmethod
    def _node_root(project_root: Path) -> Path:
        current = project_root.resolve()
        for candidate in (current, *current.parents):
            if (candidate / "_system" / "SECRET_BROKER.py").is_file():
                return candidate
        return project_root

    def _transport(self, persona: str) -> MetaGraphTransport:
        account = self._accounts.get(persona)
        if account is None:
            raise InstagramDMProviderError("instagram_dm_persona_credentials_missing")
        if self._transport_factory is not None:
            return self._transport_factory(persona)
        return UrllibMetaGraphTransport(
            self.graph_version,
            account.access_token,
            graph_host=self.graph_host,
        )

    def _persona_for_account(self, account_id: str) -> str | None:
        for persona, account in self._accounts.items():
            if hmac.compare_digest(account.account_id, account_id):
                return persona
        return None

    def readiness(self) -> dict[str, object]:
        personas = {
            persona: {
                "configured": persona in self._accounts,
                "read_ready": persona in self._accounts,
                "write_ready": persona in self._accounts,
            }
            for persona in PERSONA_SECRET_NAMES
        }
        return {
            "provider": self.provider,
            "personas": personas,
            "webhook_secret_present": bool(self.app_secret),
            "verify_token_present": bool(self.verify_token),
            "webhook_ready": bool(self.app_secret and self.verify_token),
            "auto_reply_enabled": self.auto_reply_enabled,
        }

    def verify_challenge(self, mode: str, token: str, challenge: str) -> str:
        if mode != "subscribe" or not challenge:
            raise InstagramDMProviderError("instagram_webhook_challenge_invalid")
        if not self.verify_token or not hmac.compare_digest(token, self.verify_token):
            raise InstagramDMProviderError("instagram_webhook_verify_token_invalid")
        return challenge

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not self.app_secret or not signature or not signature.startswith("sha256="):
            return False
        supplied = signature.split("=", 1)[1]
        expected = hmac.new(self.app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(supplied, expected)

    def parse_webhook(self, raw_body: bytes) -> list[dict[str, object]]:
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InstagramDMProviderError("instagram_webhook_json_invalid") from error
        if not isinstance(payload, dict) or payload.get("object") != "instagram":
            raise InstagramDMProviderError("instagram_webhook_object_invalid")
        entries = payload.get("entry")
        if not isinstance(entries, list):
            raise InstagramDMProviderError("instagram_webhook_entries_invalid")
        normalized: list[dict[str, object]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                normalized.append({"kind": "UNSUPPORTED", "reason": "entry_invalid"})
                continue
            target_id = str(entry.get("id") or "")
            persona = self._persona_for_account(target_id)
            messaging = entry.get("messaging")
            if not isinstance(messaging, list):
                normalized.append({"kind": "UNSUPPORTED", "reason": "messaging_invalid"})
                continue
            for message_event in messaging:
                if not isinstance(message_event, dict):
                    normalized.append({"kind": "UNSUPPORTED", "reason": "event_invalid"})
                    continue
                message = message_event.get("message")
                if not isinstance(message, dict):
                    normalized.append({"kind": "UNSUPPORTED", "reason": "message_unsupported"})
                    continue
                mid = str(message.get("mid") or "").strip()
                if not mid:
                    normalized.append({"kind": "UNSUPPORTED", "reason": "message_id_missing"})
                    continue
                if message.get("is_echo"):
                    normalized.append(
                        {
                            "kind": "OUTBOUND_ECHO",
                            "provider_message_id": mid,
                            "persona": persona,
                            "timestamp": message_event.get("timestamp"),
                        }
                    )
                    continue
                sender = message_event.get("sender")
                sender_id = str(sender.get("id") or "") if isinstance(sender, dict) else ""
                if not sender_id:
                    normalized.append({"kind": "UNSUPPORTED", "reason": "sender_id_missing"})
                    continue
                text = message.get("text")
                if not isinstance(text, str) or not text.strip():
                    normalized.append({"kind": "UNSUPPORTED", "reason": "non_text_message"})
                    continue
                normalized.append(
                    {
                        "kind": "INBOUND",
                        "payload": {
                            "provider": self.provider,
                            "event_id": mid,
                            "message_id": mid,
                            "conversation_id": sender_id,
                            "sender_id": sender_id,
                            "target_persona": persona or "",
                            "text": text,
                            "received_at": message_event.get("timestamp"),
                        },
                    }
                )
        return normalized

    @staticmethod
    def _data(payload: object) -> list[dict[str, object]]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data", [])
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    def poll(self, persona: str) -> list[dict[str, object]]:
        account = self._accounts.get(persona)
        if account is None:
            raise InstagramDMProviderError("instagram_dm_persona_credentials_missing")
        transport = self._transport(persona)
        try:
            conversations = transport.get(
                f"{account.account_id}/conversations",
                {
                    "platform": "instagram",
                    "fields": "id,updated_time,participants",
                    "limit": "25",
                },
            )
            inbound: list[dict[str, object]] = []
            for conversation in self._data(conversations):
                conversation_id = str(conversation.get("id") or "")
                if not conversation_id:
                    continue
                details = transport.get(
                    conversation_id,
                    {
                        "fields": "messages.limit(25){id,from,to,message,created_time}",
                    },
                )
                messages = details.get("messages", {}) if isinstance(details, dict) else {}
                for message in self._data(messages):
                    sender = message.get("from")
                    sender_id = str(sender.get("id") or "") if isinstance(sender, dict) else ""
                    if not sender_id or sender_id == account.account_id:
                        continue
                    message_id = str(message.get("id") or "")
                    if not message_id:
                        continue
                    inbound.append(
                        {
                            "provider": self.provider,
                            "event_id": message_id,
                            "message_id": message_id,
                            "conversation_id": conversation_id,
                            "sender_id": sender_id,
                            "target_persona": persona,
                            "text": str(message.get("message") or ""),
                            "received_at": message.get("created_time"),
                        }
                    )
            return inbound
        except ConnectionError as error:
            raise InstagramDMProviderConnectionError("meta_graph_unreachable") from error
        except MetaGraphError as error:
            raise InstagramDMProviderError(str(error)) from error

    def send_message(self, persona: str, recipient_id: str, text: str) -> str:
        account = self._accounts.get(persona)
        if account is None:
            raise InstagramDMProviderError("instagram_dm_persona_credentials_missing")
        if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 1000:
            raise InstagramDMProviderError("instagram_message_text_invalid")
        try:
            result = self._transport(persona).post(
                f"{account.account_id}/messages",
                {
                    "recipient": json.dumps({"id": recipient_id}, separators=(",", ":")),
                    "message": json.dumps({"text": text}, ensure_ascii=False, separators=(",", ":")),
                },
            )
        except ConnectionError as error:
            raise InstagramDMProviderConnectionError("meta_graph_write_uncertain") from error
        except MetaGraphError as error:
            raise InstagramDMProviderError(str(error)) from error
        message_id = str(result.get("message_id") or result.get("id") or "").strip()
        if not message_id:
            raise InstagramDMProviderConnectionError("meta_graph_message_id_missing")
        return message_id

    def reconcile_message(
        self, persona: str, conversation_id: str, provider_message_id: str
    ) -> bool | None:
        try:
            result = self._transport(persona).get(
                conversation_id,
                {"fields": "messages.limit(50){id}"},
            )
        except ConnectionError:
            return None
        except MetaGraphError as error:
            raise InstagramDMProviderError(str(error)) from error
        messages = result.get("messages", {}) if isinstance(result, dict) else {}
        ids = {str(item.get("id")) for item in self._data(messages) if item.get("id")}
        return provider_message_id in ids
