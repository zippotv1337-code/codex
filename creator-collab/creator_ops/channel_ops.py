from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote


ALLOWED_DECISIONS = {"approve", "change", "reject"}
ALLOWED_UPLOAD_MODES = {"DRAFT_UPLOAD", "DIRECT_POST"}
ALLOWED_METRICS = {
    "views", "likes", "comments", "shares", "saves", "profile_visits",
    "follows", "link_clicks",
}
ASSET_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class ChannelOpsService:
    """Local multi-platform preparation without any platform transport."""

    def __init__(self, project_root: Path, state_path: Path | None = None) -> None:
        self.project_root = Path(project_root).resolve()
        self.config_path = self.project_root / "config" / "channels.json"
        self.state_path = state_path or self.project_root / "data" / "channel_ops.json"

    def _config(self) -> dict[str, Any]:
        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "1.0" or not isinstance(payload.get("brands"), dict):
            raise ValueError("invalid_channel_config")
        return payload

    def _state(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            payload = {"schema_version": "1.0", "drafts": {}, "analytics": [], "errors": []}
        if payload.get("schema_version") != "1.0":
            raise ValueError("invalid_channel_state")
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.state_path)

    def _brand(self, slug: str) -> dict[str, Any]:
        brand = self._config()["brands"].get(slug)
        if not isinstance(brand, dict):
            raise KeyError("brand_not_found")
        return brand

    def _starter_drafts(self, slug: str, brand: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            item["draft_id"]: {**item, "brand_slug": slug, "updated_at": None}
            for item in brand.get("starter_drafts", [])
        }

    def _drafts(self, slug: str) -> dict[str, dict[str, Any]]:
        brand = self._brand(slug)
        combined = self._starter_drafts(slug, brand)
        combined.update(self._state().get("drafts", {}))
        return {key: value for key, value in combined.items() if value.get("brand_slug") == slug}

    def decide(self, slug: str, draft_id: str, action: str, note: str = "") -> dict[str, Any]:
        action = action.lower()
        if action not in ALLOWED_DECISIONS:
            raise ValueError("unsupported_channel_decision")
        drafts = self._drafts(slug)
        if draft_id not in drafts:
            raise KeyError("draft_not_found")
        draft = dict(drafts[draft_id])
        draft["approval_status"] = {
            "approve": "OWNER_APPROVED",
            "change": "CHANGES_REQUESTED",
            "reject": "REJECTED",
        }[action]
        draft["review_note"] = re.sub(r"[\r\n]+", " ", note).strip()[:500]
        draft["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        state = self._state()
        state.setdefault("drafts", {})[draft_id] = draft
        self._write(state)
        return self._present_draft(slug, draft)

    def set_upload_mode(self, slug: str, draft_id: str, mode: str) -> dict[str, Any]:
        mode = mode.upper()
        if mode not in ALLOWED_UPLOAD_MODES:
            raise ValueError("invalid_upload_mode")
        drafts = self._drafts(slug)
        if draft_id not in drafts:
            raise KeyError("draft_not_found")
        draft = dict(drafts[draft_id])
        if mode == "DIRECT_POST" and draft.get("approval_status") != "OWNER_APPROVED":
            raise ValueError("owner_approval_required_for_direct_post")
        if mode == "DIRECT_POST" and not self._asset_exists(draft):
            raise ValueError("real_9_16_asset_required_for_direct_post")
        draft["upload_mode"] = mode
        draft["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        state = self._state()
        state.setdefault("drafts", {})[draft_id] = draft
        self._write(state)
        return self._present_draft(slug, draft)

    def append_analytics(
        self,
        slug: str,
        draft_id: str,
        metrics: dict[str, int | None],
        *,
        source: str,
    ) -> dict[str, Any]:
        if draft_id not in self._drafts(slug):
            raise KeyError("draft_not_found")
        cleaned: dict[str, int | None] = {}
        for key in ALLOWED_METRICS:
            value = metrics.get(key)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise ValueError("invalid_analytics_metric")
            cleaned[key] = value
        if not any(value is not None for value in cleaned.values()):
            raise ValueError("at_least_one_real_metric_required")
        event = {
            "brand_slug": slug,
            "draft_id": draft_id,
            "source": re.sub(r"[^A-Za-z0-9_.-]", "-", source)[:80],
            "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "metrics": cleaned,
        }
        state = self._state()
        state.setdefault("analytics", []).append(event)
        self._write(state)
        return event

    def record_error(self, slug: str, draft_id: str, code: str) -> dict[str, Any]:
        if draft_id not in self._drafts(slug):
            raise KeyError("draft_not_found")
        event = {
            "brand_slug": slug,
            "draft_id": draft_id,
            "code": re.sub(r"[^A-Z0-9_.-]", "_", code.upper())[:100],
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        state = self._state()
        state.setdefault("errors", []).append(event)
        self._write(state)
        return event

    def _resolved_asset(self, draft: dict[str, Any]) -> tuple[Path, str] | None:
        value = draft.get("asset_path")
        if not value:
            return None
        path = (self.project_root / str(value)).resolve()
        content_type = ASSET_MIME_TYPES.get(path.suffix.lower())
        if not path.is_relative_to(self.project_root) or not path.is_file() or content_type is None:
            return None
        return path, content_type

    def _asset_exists(self, draft: dict[str, Any]) -> bool:
        return self._resolved_asset(draft) is not None

    def asset_preview(self, slug: str, draft_id: str) -> tuple[Path, str] | None:
        drafts = self._drafts(slug)
        if draft_id not in drafts:
            raise KeyError("draft_not_found")
        return self._resolved_asset(drafts[draft_id])

    def _present_draft(self, slug: str, draft: dict[str, Any]) -> dict[str, Any]:
        account = next(
            (item for item in self._brand(slug).get("accounts", []) if item.get("platform") == draft.get("platform")),
            {},
        )
        asset_ready = self._asset_exists(draft)
        owner_approved = draft.get("approval_status") == "OWNER_APPROVED"
        connected = account.get("connection_status") == "CONNECTED"
        asset_url = (
            f"/api/channels/{quote(slug, safe='')}/drafts/"
            f"{quote(str(draft.get('draft_id', '')), safe='')}/asset"
            if asset_ready
            else None
        )
        return {
            **draft,
            "asset_ready": asset_ready,
            "account_connected": connected,
            "draft_upload_ready": asset_ready and connected,
            "direct_post_ready": asset_ready and connected and owner_approved,
            "direct_post_blockers": [
                reason
                for condition, reason in (
                    (not asset_ready, "real_9_16_asset_missing"),
                    (not connected, "platform_account_not_connected"),
                    (not owner_approved, "owner_approval_missing"),
                )
                if condition
            ],
            "preview": {
                "aspect_ratio": "9:16",
                "asset_available": asset_ready,
                "asset_url": asset_url,
            },
        }

    def snapshot(self) -> dict[str, Any]:
        config = self._config()
        state = self._state()
        brands = []
        for slug, brand in config["brands"].items():
            drafts = [self._present_draft(slug, draft) for draft in self._drafts(slug).values()]
            brands.append(
                {
                    "slug": slug,
                    "display_name": brand["display_name"],
                    "kind": brand["kind"],
                    "disclosure": brand["disclosure"],
                    "identity_status": brand["identity_status"],
                    "accounts": brand["accounts"],
                    "drafts": drafts,
                }
            )
        return {
            "schema": "zippoworkz-channel-ops-v1",
            "brands": brands,
            "analytics": state.get("analytics", []),
            "errors": state.get("errors", []),
            "external_actions": "NONE",
            "transport": {
                "draft_upload": "SEPARATE_NOT_CONNECTED",
                "direct_post": "SEPARATE_OWNER_AND_CONNECTION_GATED",
            },
        }
