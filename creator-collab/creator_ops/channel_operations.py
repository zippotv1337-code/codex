"""Channel accounts and real analytics on the existing schema-5 event ledger.

No parallel database, no automatic publication and no invented account identity.
The legacy Instagram queue/receipt state machine is deliberately untouched.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta

from .ai_ops import AiOpsService
from .channel_ops import ALLOWED_METRICS, ChannelOpsService
from .secret_provider import create_secret_provider
from .tiktok_api import TikTokAdapter, TikTokError


WINDOWS = (24, 72, 168)
SYNC_CODES = {"NEEDS_AUTH", "TOKEN_EXPIRED", "SCOPE_MISSING", "RATE_LIMITED", "API_HTTP_ERROR",
              "API_RESPONSE_UNCERTAIN", "API_REJECTED", "ACCOUNT_MISMATCH", "MALFORMED_PROFILE"}


def instant(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone_required")
    return result.astimezone(UTC)


def counter(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("invalid_metric")
    return value


class ChannelOperations:
    def __init__(self, db, project, *, provider=None, environ=None, adapter_factory=TikTokAdapter):
        self.db = db
        self.project = project
        self.events = AiOpsService(db, project)
        self.channels = ChannelOpsService(project)
        self.provider = provider if provider is not None else create_secret_provider()
        self.env = environ if environ is not None else os.environ
        self.adapter_factory = adapter_factory

    def _read(self, key, default=None):
        return self.events.read("channels." + key, default)

    def _write(self, key, value):
        return self.events.write("channels." + key, value)

    def accounts(self):
        # Existing creators are authoritative for Instagram. Milo's existing
        # brand config supplies its two accounts; no new persona is seeded.
        result = []
        for row in self.db.all("SELECT slug,display_name,instagram_handle FROM creators WHERE active=1"):
            result.append({"creator_id": row["slug"], "display_name": row["display_name"],
                           "platform": "instagram", "username": row["instagram_handle"].lstrip("@")})
        for slug, brand in self.channels._config()["brands"].items():
            for item in brand["accounts"]:
                result.append({"creator_id": slug, "display_name": brand["display_name"],
                               "platform": item["platform"], "username": item.get("public_handle"),
                               "native_connection": item.get("connection_status")})
        for item in result:
            item["id"] = item["creator_id"] + ":" + item["platform"]
            state = self._read("account." + item["id"])
            item.update({"account_type": "PROJECT_CREATOR", "owner_authorized": True,
                         "enabled": True, "posting_enabled": False, "analytics_enabled": False,
                         "connection_status": "NEEDS_AUTH", "scopes": [], "last_sync_at": None,
                         "last_error": None, "external_id": None, "token_expires_at": None,
                         "token_status": "UNKNOWN", "profile": {}, "video_sync": {}, **state})
            if item["platform"] == "tiktok":
                present = self.provider.has("secret://tiktok/" + item["creator_id"] + "/access-token")
                item["token_status"] = "PRESENT_NOT_VALIDATED" if present else "MISSING"
                item["scopes"] = sorted(filter(None, self.env.get("TIKTOK_MILO_SCOPES", "").split(",")))
                if not present:
                    item["connection_status"] = "NEEDS_AUTH"
                    item["analytics_enabled"] = False
                elif state.get("connection_status") == "CONNECTED":
                    item["token_status"] = "LAST_SYNC_ACCEPTED_NOT_CONTINUOUSLY_VERIFIED"
            item["capabilities"] = {
                "profile_sync": item["platform"] == "tiktok" and item["token_status"] != "MISSING"
                    and {"user.info.basic", "user.info.profile"}.issubset(item["scopes"]),
                "account_stats": "user.info.stats" in item["scopes"],
                "video_list": "video.list" in item["scopes"],
                "direct_post": False, "draft_upload": False,
                "publish_gate": "CONSENT_COMPOSER_AND_LIVE_PROOF_PENDING" if item["platform"] == "tiktok" else "EXISTING_META_ADAPTER_SEPARATE",
            }
        return result

    def sync(self, account_id):
        account = next((item for item in self.accounts() if item["id"] == account_id), None)
        if not account or account_id != "milo-der-zug:tiktok":
            raise ValueError("account_not_allowlisted_for_sync")
        scopes = account["scopes"]
        token = self.provider.get("secret://tiktok/milo-der-zug/access-token")
        expected = self.provider.get("secret://tiktok/milo-der-zug/open-id")
        old = self._read("account." + account_id)
        try:
            if token is None or expected is None:
                raise TikTokError("NEEDS_AUTH")
            adapter = self.adapter_factory(token, scopes=scopes)
            profile = adapter.profile()
            if not profile.get("open_id") or not profile.get("username"):
                raise TikTokError("MALFORMED_PROFILE")
            if profile["open_id"] != expected.reveal() or profile["username"].lower() != account["username"].lower():
                raise TikTokError("ACCOUNT_MISMATCH")
            for key in ("follower_count", "following_count", "likes_count", "video_count"):
                profile[key] = counter(profile.get(key))
            now = datetime.now(UTC).isoformat(timespec="seconds")
            videos, cursor, has_more, list_error = [], None, False, None
            if "video.list" in scopes:
                try:
                    # Bounded pagination. Honest partial result; no repeated cursors.
                    seen = set()
                    for _ in range(3):
                        page = adapter.videos(cursor)
                        videos.extend(page["videos"])
                        has_more, cursor = page["has_more"], page["cursor"]
                        if not has_more or cursor is None or cursor in seen:
                            break
                        seen.add(cursor)
                except TikTokError as error:
                    list_error = str(error) if str(error) in SYNC_CODES else "API_REJECTED"
            else:
                list_error = "SCOPE_MISSING"
            state = {"connection_status": "CONNECTED", "external_id": profile["open_id"],
                     "profile": profile, "last_sync_at": now, "last_error": list_error,
                     "analytics_enabled": "user.info.stats" in scopes or "video.list" in scopes,
                     "video_sync": {"items": videos, "partial": has_more or list_error is not None,
                                    "cursor": cursor, "captured_at": now, "source": "TIKTOK_API"}}
            self._write("account." + account_id, state)
            return {"status": "SYNCED_PARTIAL" if state["video_sync"]["partial"] else "SYNCED", "account_id": account_id,
                    "profile_verified": True, "posts_read": len(videos), "external_publish": False}
        except (TikTokError, ValueError) as error:
            code = str(error) if str(error) in SYNC_CODES else "API_REJECTED"
            self._write("account." + account_id, {**old, "connection_status": code if code in {"NEEDS_AUTH", "TOKEN_EXPIRED", "SCOPE_MISSING"} else "BLOCKED",
                                                "analytics_enabled": False, "last_error": code})
            return {"status": "BLOCKED", "account_id": account_id, "error": code, "external_publish": False}

    def publications(self, now=None):
        now = now or datetime.now(UTC)
        items = []
        for brand in self.channels.snapshot()["brands"]:
            for draft in brand["drafts"]:
                if draft.get("status") != "PUBLISHED" or not draft.get("external_post_id"):
                    continue
                published_value = draft.get("published_at")
                if not published_value:
                    # A historical receipt without a timestamp cannot be
                    # assigned honest 24/72/168-hour windows.
                    continue
                try:
                    published_at = instant(published_value)
                except (TypeError, ValueError):
                    continue
                windows = []
                for hours in WINDOWS:
                    event = self._read(f"metric.{draft['external_post_id']}.{hours}")
                    due = published_at + timedelta(hours=hours)
                    windows.append({"hours": hours, "due_at": due.isoformat(),
                                    "status": "CAPTURED" if event else "DUE" if now >= due else "WAITING",
                                    "metrics": event.get("metrics", {key: None for key in sorted(ALLOWED_METRICS)}),
                                    "captured_at": event.get("captured_at"), "source": event.get("source"),
                                    "late_by_hours": event.get("late_by_hours")})
                captured = [window for window in windows if window["status"] == "CAPTURED"]
                latest = max(captured, key=lambda item: item["captured_at"]) if captured else None
                metrics = latest["metrics"] if latest else {}
                views = metrics.get("views")
                age = max(0, ((instant(latest["captured_at"]) if latest else now) - published_at).total_seconds() / 3600)
                rates = {f"{key}_per_view": metrics[key] / views if views and metrics.get(key) is not None else None
                         for key in ("likes", "comments", "shares")}
                rates["views_per_hour"] = views / age if views is not None and age > 0 else None
                items.append({"creator_id": brand["slug"], "draft_id": draft["draft_id"], "title": draft["title"],
                              "platform": draft["platform"], "format": draft["format"],
                              "external_post_id": draft["external_post_id"], "permalink": draft.get("permalink"),
                              "published_at": draft["published_at"], "transport": draft.get("publish_transport"),
                              "public_visibility": "HISTORICAL_OWNER_SESSION_EVIDENCE_NOT_RECHECKED",
                              "windows": windows, "derived": rates, "learning": "UNKNOWN",
                              "learning_reason": "Comparable independent posts and real metrics required"})
        return items

    def capture(self, post_id, hours, metrics, *, now=None):
        now = now or datetime.now(UTC)
        if hours not in WINDOWS:
            raise ValueError("invalid_analytics_window")
        post = next((post for post in self.publications(now) if post["external_post_id"] == post_id), None)
        if post is None:
            raise ValueError("confirmed_publication_required")
        due = instant(post["published_at"]) + timedelta(hours=hours)
        if now < due:
            raise ValueError("analytics_window_not_due")
        cleaned = {key: counter(metrics.get(key)) for key in sorted(ALLOWED_METRICS)}
        if not any(value is not None for value in cleaned.values()):
            raise ValueError("real_metrics_required")
        return self._write(f"metric.{post_id}.{hours}", {"external_post_id": post_id, "window_hours": hours,
                           "source": "MANUAL_OWNER_OBSERVATION", "metrics": cleaned,
                           "captured_at": now.isoformat(), "late_by_hours": round((now - due).total_seconds() / 3600, 2)})

    def media_readiness(self):
        return [{"type": kind, "provider": name, "model": model,
                 "credential_present": self.provider.has(alias), "status": "OWNER_COST_GATE",
                 "live_adapter": "NOT_IMPLEMENTED", "rights_status": "REQUIRES_ASSET_REVIEW",
                 "generation_enabled": False, "jobs": []}
                for kind, name, model, alias in (
                    ("VIDEO", "Runway", "Gen-4.5", "secret://runway/api-key"),
                    ("AUDIO", "Stability AI", "Stable Audio", "secret://stability/api-key"))]

    def snapshot(self, now=None):
        posts = self.publications(now)
        accounts = self.accounts()
        return {"schema": "channel-operations-v1", "accounts": accounts, "publications": posts,
                "media": self.media_readiness(),
                "summary": {"accounts": len(accounts), "api_connected": sum(a["connection_status"] == "CONNECTED" for a in accounts),
                            "native_receipts": len(posts), "due_windows": sum(w["status"] == "DUE" for p in posts for w in p["windows"]),
                            "captured_windows": sum(w["status"] == "CAPTURED" for p in posts for w in p["windows"])},
                "api_publish_proof": "NOT_PROVEN", "automatic_publish": False,
                "local_ai": self.events.read("task.milo_master_brief", {"status": "NEXT"}),
                "owner_action": "Rotate exposed TikTok app secret; authorize miloderzug OAuth and set secure account token/open-id aliases plus granted scopes. No secrets in chat."}

    def local_brief_input(self):
        payload = self.snapshot()
        # Exclude account bio, remote URLs and opaque external IDs from model input.
        return {"character_lock": "MILO_REFERENCE_2026_09_14_V1",
                "reference": "assets/references/milo-der-zug/milo-character-reference-instagram-20260914.jpg",
                "character": "Small round blue steam engine, sky-blue round face, large eyes, yellow front, red roof. Never redesign.",
                "facts": payload["summary"], "existing_post_titles": [p["title"] for p in payload["publications"]],
                "measurements": [{"format": p["format"], "windows": p["windows"]} for p in payload["publications"]],
                "rules": "PUBLIC_SFW, fictional AI brand, no invented analytics/winners, no paid calls, no publish, no duplicate morning-station post."}

    def input_fingerprint(self):
        return hashlib.sha256(json.dumps(self.local_brief_input(), sort_keys=True).encode()).hexdigest()
