"""Official, bounded TikTok transport. No credentials or raw errors are persisted.

OAuth consent/rotation is an operator prerequisite, not simulated by this adapter.
Transport injection is for offline tests; production always uses the fixed host.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler


class TikTokError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a bearer credential to another host.


class TikTokAdapter:
    def __init__(self, secret, *, scopes, transport=None):
        self.secret = secret
        self.scopes = frozenset(scopes)
        self.transport = transport or self._http

    def _http(self, method, path, payload):
        if self.secret is None:
            raise TikTokError("NEEDS_AUTH")
        request = Request("https://open.tiktokapis.com" + path,
                          data=None if payload is None else json.dumps(payload).encode(),
                          method=method, headers={"Authorization": "Bearer " + self.secret.reveal(),
                                                  "Content-Type": "application/json"})
        try:
            with build_opener(NoRedirect()).open(request, timeout=20) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise TikTokError("RESPONSE_TOO_LARGE")
                return json.loads(raw)
        except HTTPError as error:
            raise TikTokError({401: "TOKEN_EXPIRED", 403: "SCOPE_MISSING", 429: "RATE_LIMITED"}.get(error.code, "API_HTTP_ERROR")) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise TikTokError("API_RESPONSE_UNCERTAIN") from None

    def call(self, method, path, payload=None):
        if self.secret is None:
            raise TikTokError("NEEDS_AUTH")
        reply = self.transport(method, path, payload)
        error = reply.get("error") if isinstance(reply, dict) else None
        if not isinstance(error, dict) or error.get("code") != "ok":
            code = error.get("code") if isinstance(error, dict) else None
            raise TikTokError({"access_token_invalid": "TOKEN_EXPIRED", "scope_not_authorized": "SCOPE_MISSING"}.get(code, "API_REJECTED"))
        if not isinstance(reply.get("data"), dict):
            raise TikTokError("API_REJECTED")
        return reply["data"]

    def require(self, *scopes):
        if not set(scopes).issubset(self.scopes):
            raise TikTokError("SCOPE_MISSING")

    def profile(self):
        self.require("user.info.basic", "user.info.profile")
        fields = ["open_id", "avatar_url", "display_name", "username", "bio_description", "is_verified"]
        if "user.info.stats" in self.scopes:
            fields += ["follower_count", "following_count", "likes_count", "video_count"]
        data = self.call("GET", "/v2/user/info/?" + urlencode({"fields": ",".join(fields)}))
        user = data.get("user")
        if not isinstance(user, dict):
            raise TikTokError("API_REJECTED")
        return {key: user.get(key) for key in fields}

    def videos(self, cursor=None):
        self.require("video.list")
        fields = "id,create_time,cover_image_url,share_url,video_description,duration,width,height,like_count,comment_count,share_count,view_count"
        body = {"max_count": 20}
        if cursor is not None:
            body["cursor"] = int(cursor)
        data = self.call("POST", "/v2/video/list/?" + urlencode({"fields": fields}), body)
        videos = data.get("videos")
        if not isinstance(videos, list):
            raise TikTokError("API_REJECTED")
        # Fixed field allowlist: never persist the whole upstream response.
        cleaned = []
        for item in videos:
            if not isinstance(item, dict):
                raise TikTokError("API_REJECTED")
            cleaned.append({key: item.get(key) for key in fields.split(",")})
        return {"videos": cleaned,
                "cursor": data.get("cursor"), "has_more": data.get("has_more") is True}

    def creator_info(self):
        self.require("video.publish")
        return self.call("POST", "/v2/post/publish/creator_info/query/", {})

    def status(self, publish_id):
        if not self.scopes.intersection({"video.publish", "video.upload"}):
            raise TikTokError("SCOPE_MISSING")
        data = self.call("POST", "/v2/post/publish/status/fetch/", {"publish_id": publish_id})
        ids = data.get("publicaly_available_post_id", [])
        ids = [str(value) for value in ids if str(value).isdigit()] if isinstance(ids, list) else []
        return {"platform_status": data.get("status"),
                "external_post_ids": ids,
                "public_confirmed": data.get("status") == "PUBLISH_COMPLETE" and bool(ids),
                "error": "PLATFORM_PUBLISH_FAILED" if data.get("status") == "FAILED" else None}
