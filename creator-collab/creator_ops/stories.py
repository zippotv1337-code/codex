from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urlsplit

from .review import ReviewDashboardService


class StoryReserveService:
    """Derive owner-reviewable story packages from existing feed assets only."""

    def __init__(self, reviews: ReviewDashboardService):
        self.reviews = reviews

    @staticmethod
    def _preview(asset: dict) -> dict:
        return {key: asset[key] for key in ("id", "pose_slot", "preview_url", "quality")}

    def packages(self) -> list[dict]:
        result: list[dict] = []
        events = self.reviews.pipeline.db.all(
            "SELECT content_id, action, note FROM review_events WHERE action LIKE 'STORY_%' ORDER BY id"
        )
        for card in self.reviews.review_queue()["cards"]:
            if card["status"] == "BLOCKED" or card["safety_class"] != "SFW" or card["visibility_scope"] != "PUBLIC_SFW":
                continue
            available = [asset for asset in card["assets"] if not asset["excluded"]
                         and asset["safety_class"] == "SFW" and asset["visibility_scope"] == "PUBLIC_SFW"]
            top = sorted(
                (asset for asset in available if asset["top_pick"]),
                key=lambda asset: asset["top_pick_order"],
            )
            alternates = [asset for asset in available if not asset["top_pick"]]
            if len(top) < 2:
                continue
            poll_asset = alternates[0] if alternates else top[1]
            frames = [
                {"kind": "TEASER", "copy": card["hook"], "interaction": "Keine - nur Einstieg", "asset": self._preview(top[0])},
                {"kind": "POLL", "copy": "Welche Richtung soll in den Feed?", "interaction": "A: näher dran · B: mehr Szene", "asset": self._preview(poll_asset)},
                {"kind": "COMMUNITY", "copy": card["cta"], "interaction": "Antwort-Sticker; später manuell prüfen", "asset": self._preview(top[-1])},
            ]
            package = {
                "content_id": card["content_id"], "creator_slug": card["creator_slug"],
                "display_name": card["display_name"], "series": card["series"],
                "date": card["date"], "planned_at": None,
                "status": "READY_FOR_OWNER_REVIEW", "story_type": "TEASER/POLL/FRAGE",
                "cta": card["cta"], "highlight": None, "frames": frames,
                "published_assets_excluded": card["excluded_published_count"],
                "safety_note": "SFW; kein Auto-Posting; nativen KI-Hinweis vor Veröffentlichung prüfen",
            }
            states = {"STORY_APPROVED_UI": "APPROVED", "STORY_CHANGE_REQUESTED_UI": "CHANGE_REQUESTED",
                      "STORY_REJECTED_UI": "REJECTED", "STORY_PLANNED_UI": "LOCAL_PLANNED",
                      "STORY_PAUSED_UI": "PAUSED", "STORY_EDITED_UI": "READY_FOR_OWNER_REVIEW"}
            for event in events:
                if event["content_id"] != card["content_id"] or event["action"] not in states:
                    continue
                package["status"] = states[event["action"]]
                try:
                    saved = json.loads(event["note"])
                except (ValueError, TypeError):
                    saved = {}
                if isinstance(saved, dict) and saved.get("schema") == "story-review-v1":
                    # Never restore asset references or a published state from editable metadata.
                    for key in ("cta", "highlight", "planned_at"):
                        if key in saved:
                            package[key] = saved[key]
                    edits = saved.get("frames", [])
                    for frame, edit in zip(package["frames"], edits):
                        if edit.get("asset_id") == frame["asset"]["id"]:
                            frame.update({key: edit[key] for key in ("copy", "kind", "interaction", "link") if key in edit})
            if package["status"] == "LOCAL_PLANNED" and not package["planned_at"]:
                package["status"] = "NEEDS_SCHEDULE"
            package["story_type"] = "/".join(frame["kind"] for frame in package["frames"])
            package["can_review"] = all(frame["asset"]["preview_url"] for frame in package["frames"])
            result.append(package)
        return result

    def decision_payload(self, content_id: int, action: str, note: str, fields: dict | None) -> str:
        """Validate local edits against current assets; store them in the existing event ledger."""
        package = next((item for item in self.packages() if item["content_id"] == content_id), None)
        if package is None:
            raise KeyError("story_review_card_not_found")
        if action in {"approve", "plan"} and not package["can_review"]:
            raise ValueError("story_real_previews_required")
        payload = {"schema": "story-review-v1", "note": note.strip()[:500]}
        fields = fields or {}
        if not isinstance(fields, dict):
            raise ValueError("invalid_story_fields")
        if action == "edit":
            for key, limit in (("cta", 500), ("highlight", 80)):
                value = fields.get(key, "")
                if not isinstance(value, str) or len(value) > limit:
                    raise ValueError(f"invalid_story_{key}")
                payload[key] = value.strip()
            edits = fields.get("frames", [])
            if not isinstance(edits, list) or len(edits) != len(package["frames"]):
                raise ValueError("invalid_story_frames")
            payload["frames"] = []
            for frame, edit in zip(package["frames"], edits):
                if not isinstance(edit, dict) or edit.get("kind") not in {"NORMAL", "TEASER", "POLL", "COMMUNITY", "FRAGE", "LINK", "BTS"}:
                    raise ValueError("invalid_story_type")
                clean = {"asset_id": frame["asset"]["id"], "kind": edit["kind"]}
                for key in ("copy", "interaction", "link"):
                    value = edit.get(key, "")
                    if not isinstance(value, str) or len(value) > 1000:
                        raise ValueError(f"invalid_story_{key}")
                    clean[key] = value.strip()
                if not clean["copy"]:
                    raise ValueError("story_text_required")
                if clean["link"]:
                    url = urlsplit(clean["link"])
                    if url.scheme != "https" or not url.hostname or url.username or url.password:
                        raise ValueError("story_link_requires_public_https")
                payload["frames"].append(clean)
            # Editing invalidates any earlier local plan; the feed schedule is untouched.
            payload["planned_at"] = None
        elif action == "plan":
            if package["status"] not in {"APPROVED", "LOCAL_PLANNED", "NEEDS_SCHEDULE"}:
                raise ValueError("story_approval_required_before_planning")
            try:
                planned = datetime.fromisoformat(fields.get("planned_at", ""))
            except (ValueError, TypeError):
                raise ValueError("story_planned_time_required") from None
            if planned.tzinfo is None or planned <= datetime.now().astimezone():
                raise ValueError("story_future_time_with_timezone_required")
            payload["planned_at"] = planned.isoformat(timespec="seconds")
        return json.dumps(payload, ensure_ascii=False)
