from __future__ import annotations

import hashlib
import json
import math
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from .database import CreatorDatabase, utc_now
from .secrets import get_secret, set_secret


TIKTOK_WORKER = "creator-ops-tiktok"
AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
API_ROOT = "https://open.tiktokapis.com"
TOKEN_PATH = "/v2/oauth/token/"
CREATOR_INFO_PATH = "/v2/post/publish/creator_info/query/"
DIRECT_VIDEO_PATH = "/v2/post/publish/video/init/"
DRAFT_VIDEO_PATH = "/v2/post/publish/inbox/video/init/"
STATUS_PATH = "/v2/post/publish/status/fetch/"

ALLOWED_SCOPES = frozenset(
    {"user.info.basic", "video.list", "video.upload", "video.publish"}
)
TERMINAL_STATUSES = frozenset({"PUBLISH_COMPLETE", "FAILED"})


class TikTokError(RuntimeError):
    """Sanitized TikTok failure; messages never include tokens or bodies."""

    def __init__(self, code: str, *, http_status: int | None = None) -> None:
        self.code = code
        self.http_status = http_status
        super().__init__(code)


class TikTokTransport(Protocol):
    def post_form(self, path: str, data: dict[str, str]) -> dict[str, Any]: ...

    def post_json(
        self, path: str, data: dict[str, Any], *, access_token: str
    ) -> dict[str, Any]: ...

    def put_binary(
        self,
        url: str,
        data: bytes,
        *,
        content_type: str,
        first_byte: int,
        total_size: int,
    ) -> int: ...


class UrllibTikTokTransport:
    def __init__(self, *, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def _request(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise TikTokError(
                f"tiktok_http_{error.code}", http_status=error.code
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise TikTokError("tiktok_transport_error") from None
        if not isinstance(payload, dict):
            raise TikTokError("tiktok_invalid_response")
        api_error = payload.get("error")
        if isinstance(api_error, dict) and api_error.get("code") not in (None, "ok"):
            raise TikTokError(str(api_error.get("code") or "tiktok_api_error"))
        if payload.get("error") and not isinstance(payload.get("error"), dict):
            raise TikTokError(str(payload.get("error")))
        return payload

    def post_form(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        request = urllib.request.Request(
            API_ROOT + path,
            data=urllib.parse.urlencode(data).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        return self._request(request)

    def post_json(
        self, path: str, data: dict[str, Any], *, access_token: str
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            API_ROOT + path,
            data=json.dumps(data, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            method="POST",
        )
        return self._request(request)

    def put_binary(
        self,
        url: str,
        data: bytes,
        *,
        content_type: str,
        first_byte: int,
        total_size: int,
    ) -> int:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (
            host == "tiktokapis.com" or host.endswith(".tiktokapis.com")
        ):
            raise TikTokError("tiktok_upload_url_rejected")
        last_byte = first_byte + len(data) - 1
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": content_type,
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {first_byte}-{last_byte}/{total_size}",
            },
            method="PUT",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return int(getattr(response, "status", response.getcode()))
        except urllib.error.HTTPError as error:
            raise TikTokError(
                f"tiktok_upload_http_{error.code}", http_status=error.code
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise TikTokError("tiktok_upload_transport_error") from None


def _scope_set(value: str | list[str] | tuple[str, ...]) -> set[str]:
    raw = value.split(",") if isinstance(value, str) else value
    return {str(item).strip() for item in raw if str(item).strip()}


def _data(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("data", payload)
    if not isinstance(value, dict):
        raise TikTokError("tiktok_invalid_response")
    return value


def _utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


@dataclass(frozen=True)
class TikTokCreatorInfo:
    username: str
    nickname: str
    privacy_level_options: tuple[str, ...]
    comment_disabled: bool
    duet_disabled: bool
    stitch_disabled: bool
    max_video_post_duration_sec: int


class TikTokOAuthService:
    def __init__(
        self,
        database: CreatorDatabase,
        root: Path,
        transport: TikTokTransport | None = None,
    ) -> None:
        self.database = database
        self.root = Path(root)
        self.transport = transport or UrllibTikTokTransport()

    def _secret(self, name: str) -> str:
        return get_secret(name, worker=TIKTOK_WORKER, root=self.root)

    def begin(self, scopes: tuple[str, ...], *, ttl_minutes: int = 10) -> dict[str, Any]:
        requested = _scope_set(scopes)
        if not requested or not requested.issubset(ALLOWED_SCOPES):
            raise ValueError("invalid_tiktok_oauth_scopes")
        client_key = self._secret("TIKTOK_CLIENT_KEY")
        redirect_uri = self._secret("TIKTOK_REDIRECT_URI")
        parsed = urllib.parse.urlparse(redirect_uri)
        if not client_key or parsed.scheme != "https" or not parsed.netloc:
            raise TikTokError("tiktok_oauth_configuration_incomplete")

        state = secrets.token_urlsafe(32)
        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=max(1, min(ttl_minutes, 30)))
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO oauth_states
                    (provider, state_hash, redirect_uri, scopes_json,
                     expires_at, consumed_at, created_at)
                VALUES ('tiktok', ?, ?, ?, ?, NULL, ?)
                """,
                (
                    state_hash,
                    redirect_uri,
                    json.dumps(sorted(requested)),
                    expires_at.isoformat(timespec="seconds"),
                    now.isoformat(timespec="seconds"),
                ),
            )
        query = urllib.parse.urlencode(
            {
                "client_key": client_key,
                "response_type": "code",
                "scope": ",".join(sorted(requested)),
                "redirect_uri": redirect_uri,
                "state": state,
            }
        )
        return {
            "authorization_url": f"{AUTHORIZE_URL}?{query}",
            "expires_at": expires_at.isoformat(timespec="seconds"),
            "scopes": sorted(requested),
        }

    def complete(
        self,
        *,
        code: str,
        state: str,
        granted_scopes: str | tuple[str, ...],
    ) -> dict[str, Any]:
        if not code or not state:
            raise TikTokError("tiktok_oauth_callback_incomplete")
        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        row = self.database.one(
            """
            SELECT * FROM oauth_states
            WHERE provider='tiktok' AND state_hash=?
            """,
            (state_hash,),
        )
        now = datetime.now(UTC)
        if row is None or row["consumed_at"] is not None:
            raise TikTokError("tiktok_oauth_state_invalid")
        expires_at = datetime.fromisoformat(str(row["expires_at"]))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if now >= expires_at:
            raise TikTokError("tiktok_oauth_state_expired")
        requested = set(json.loads(str(row["scopes_json"])))
        granted = _scope_set(granted_scopes)
        if not requested.issubset(granted):
            raise TikTokError("tiktok_oauth_required_scope_not_granted")

        # Claim the one-time state before the external token exchange.  A
        # failed exchange requires a new authorization attempt; it must never
        # make the same callback replayable.
        with self.database.transaction() as connection:
            claimed = connection.execute(
                "UPDATE oauth_states SET consumed_at=? WHERE id=? AND consumed_at IS NULL",
                (utc_now(), int(row["id"])),
            )
            if claimed.rowcount != 1:
                raise TikTokError("tiktok_oauth_state_invalid")

        client_key = self._secret("TIKTOK_CLIENT_KEY")
        client_secret = self._secret("TIKTOK_CLIENT_SECRET")
        if not client_key or not client_secret:
            raise TikTokError("tiktok_oauth_configuration_incomplete")
        payload = _data(
            self.transport.post_form(
                TOKEN_PATH,
                {
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": str(row["redirect_uri"]),
                },
            )
        )
        return self._store_tokens(payload)

    def refresh(self) -> dict[str, Any]:
        client_key = self._secret("TIKTOK_CLIENT_KEY")
        client_secret = self._secret("TIKTOK_CLIENT_SECRET")
        refresh_token = self._secret("TIKTOK_REFRESH_TOKEN")
        if not client_key or not client_secret or not refresh_token:
            raise TikTokError("tiktok_refresh_configuration_incomplete")
        payload = _data(
            self.transport.post_form(
                TOKEN_PATH,
                {
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
        )
        return self._store_tokens(payload)

    def _store_tokens(self, payload: dict[str, Any]) -> dict[str, Any]:
        access_token = str(payload.get("access_token") or "")
        refresh_token = str(payload.get("refresh_token") or "")
        open_id = str(payload.get("open_id") or "")
        scopes = _scope_set(str(payload.get("scope") or ""))
        if not access_token or not refresh_token or not open_id or not scopes:
            raise TikTokError("tiktok_token_response_incomplete")
        access_expiry = datetime.now(UTC) + timedelta(
            seconds=max(1, int(payload.get("expires_in") or 0))
        )
        refresh_expiry = datetime.now(UTC) + timedelta(
            seconds=max(1, int(payload.get("refresh_expires_in") or 0))
        )
        # Access token is written last and acts as the local commit marker.
        # A broker failure therefore cannot advertise a half-written session
        # as connected/readable.
        values = (
            ("TIKTOK_OPEN_ID", open_id, None),
            ("TIKTOK_SCOPES", ",".join(sorted(scopes)), None),
            ("TIKTOK_REFRESH_TOKEN", refresh_token, refresh_expiry),
            ("TIKTOK_ACCESS_TOKEN", access_token, access_expiry),
        )
        for name, value, expiry in values:
            set_secret(
                name,
                value,
                worker=TIKTOK_WORKER,
                root=self.root,
                expires_at=expiry.isoformat(timespec="seconds") if expiry else None,
            )
        return {
            "status": "CONNECTED",
            "open_id_present": True,
            "scopes": sorted(scopes),
            "access_expires_at": access_expiry.isoformat(timespec="seconds"),
            "refresh_expires_at": refresh_expiry.isoformat(timespec="seconds"),
        }


class TikTokPublishingAdapter:
    provider = "tiktok-content-posting-v2"

    def __init__(
        self,
        root: Path,
        transport: TikTokTransport | None = None,
    ) -> None:
        self.root = Path(root)
        self.transport = transport or UrllibTikTokTransport()

    @property
    def available(self) -> bool:
        return bool(self._access_token())

    def _access_token(self) -> str:
        return get_secret(
            "TIKTOK_ACCESS_TOKEN", worker=TIKTOK_WORKER, root=self.root
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        token = self._access_token()
        if not token:
            raise TikTokError("tiktok_access_token_missing")
        return _data(self.transport.post_json(path, payload, access_token=token))

    def creator_info(self) -> TikTokCreatorInfo:
        data = self._post(CREATOR_INFO_PATH, {})
        options = tuple(str(item) for item in data.get("privacy_level_options", []))
        if not data.get("creator_username") or not options:
            raise TikTokError("tiktok_creator_info_incomplete")
        return TikTokCreatorInfo(
            username=str(data["creator_username"]),
            nickname=str(data.get("creator_nickname") or ""),
            privacy_level_options=options,
            comment_disabled=bool(data.get("comment_disabled", False)),
            duet_disabled=bool(data.get("duet_disabled", False)),
            stitch_disabled=bool(data.get("stitch_disabled", False)),
            max_video_post_duration_sec=int(data.get("max_video_post_duration_sec") or 0),
        )

    @staticmethod
    def file_upload_source(video_size: int) -> dict[str, Any]:
        if video_size <= 0 or video_size > 4 * 1024 * 1024 * 1024:
            raise ValueError("tiktok_video_size_out_of_range")
        chunk_size = video_size if video_size <= 64 * 1024 * 1024 else 64 * 1024 * 1024
        total_chunk_count = max(1, math.ceil(video_size / chunk_size))
        return {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunk_count,
        }

    @staticmethod
    def pull_source(video_url: str) -> dict[str, Any]:
        parsed = urllib.parse.urlparse(video_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError("tiktok_verified_https_video_url_required")
        return {"source": "PULL_FROM_URL", "video_url": video_url}

    @staticmethod
    def _validate_post_info(
        creator: TikTokCreatorInfo,
        *,
        title: str,
        privacy_level: str,
        disable_comment: bool,
        disable_duet: bool,
        disable_stitch: bool,
        duration_seconds: int,
    ) -> None:
        if privacy_level not in creator.privacy_level_options:
            raise ValueError("tiktok_privacy_option_not_allowed")
        if creator.comment_disabled and not disable_comment:
            raise ValueError("tiktok_comments_must_remain_disabled")
        if creator.duet_disabled and not disable_duet:
            raise ValueError("tiktok_duet_must_remain_disabled")
        if creator.stitch_disabled and not disable_stitch:
            raise ValueError("tiktok_stitch_must_remain_disabled")
        if creator.max_video_post_duration_sec <= 0:
            raise ValueError("tiktok_max_duration_unknown")
        if duration_seconds <= 0 or duration_seconds > creator.max_video_post_duration_sec:
            raise ValueError("tiktok_video_duration_not_allowed")
        if _utf16_units(title) > 2200:
            raise ValueError("tiktok_title_too_long")

    def init_direct_video(
        self,
        *,
        source_info: dict[str, Any],
        title: str,
        privacy_level: str,
        disable_comment: bool,
        disable_duet: bool,
        disable_stitch: bool,
        duration_seconds: int,
        is_aigc: bool,
        explicit_user_consent: bool,
        expected_username: str | None = None,
    ) -> dict[str, Any]:
        if not explicit_user_consent:
            raise TikTokError("tiktok_explicit_user_consent_required")
        creator = self.creator_info()
        if expected_username and creator.username.lstrip("@").casefold() != expected_username.lstrip("@").casefold():
            raise TikTokError("tiktok_connected_account_mismatch")
        self._validate_post_info(
            creator,
            title=title,
            privacy_level=privacy_level,
            disable_comment=disable_comment,
            disable_duet=disable_duet,
            disable_stitch=disable_stitch,
            duration_seconds=duration_seconds,
        )
        data = self._post(
            DIRECT_VIDEO_PATH,
            {
                "post_info": {
                    "title": title,
                    "privacy_level": privacy_level,
                    "disable_comment": disable_comment,
                    "disable_duet": disable_duet,
                    "disable_stitch": disable_stitch,
                    "is_aigc": is_aigc,
                },
                "source_info": source_info,
            },
        )
        if not data.get("publish_id"):
            raise TikTokError("tiktok_publish_init_incomplete")
        return data

    def init_draft_video(
        self,
        *,
        source_info: dict[str, Any],
        expected_username: str | None = None,
    ) -> dict[str, Any]:
        creator = self.creator_info()
        if expected_username and creator.username.lstrip("@").casefold() != expected_username.lstrip("@").casefold():
            raise TikTokError("tiktok_connected_account_mismatch")
        data = self._post(DRAFT_VIDEO_PATH, {"source_info": source_info})
        if not data.get("publish_id"):
            raise TikTokError("tiktok_draft_init_incomplete")
        return data

    def fetch_status(self, publish_id: str) -> dict[str, Any]:
        if not publish_id:
            raise ValueError("tiktok_publish_id_required")
        data = self._post(STATUS_PATH, {"publish_id": publish_id})
        if not data.get("status"):
            raise TikTokError("tiktok_status_incomplete")
        return data

    def upload_file(self, upload_url: str, path: Path) -> None:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        content_types = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".webm": "video/webm",
        }
        content_type = content_types.get(path.suffix.lower())
        if content_type is None:
            raise ValueError("tiktok_video_format_not_supported")
        total = path.stat().st_size
        source = self.file_upload_source(total)
        chunk_size = int(source["chunk_size"])
        offset = 0
        with path.open("rb") as handle:
            while offset < total:
                data = handle.read(chunk_size)
                if not data:
                    raise TikTokError("tiktok_upload_incomplete")
                status = self.transport.put_binary(
                    upload_url,
                    data,
                    content_type=content_type,
                    first_byte=offset,
                    total_size=total,
                )
                offset += len(data)
                expected = 201 if offset == total else 206
                if status != expected:
                    raise TikTokError(f"tiktok_upload_unexpected_http_{status}")


class TikTokPublishService:
    """Idempotent TikTok intent owner; uncertain writes are reconciled, not retried."""

    def __init__(self, database: CreatorDatabase, adapter: TikTokPublishingAdapter) -> None:
        self.database = database
        self.adapter = adapter

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def initialize_video(
        self,
        *,
        idempotency_key: str,
        account_key: str,
        mode: str,
        source_info: dict[str, Any],
        post_info: dict[str, Any] | None = None,
        content_id: int | None = None,
        file_path: Path | None = None,
    ) -> dict[str, Any]:
        mode = mode.upper()
        if mode not in {"DIRECT_POST", "MEDIA_UPLOAD"}:
            raise ValueError("tiktok_mode_invalid")
        source_method = str(source_info.get("source") or "")
        if source_method not in {"FILE_UPLOAD", "PULL_FROM_URL"}:
            raise ValueError("tiktok_source_invalid")
        safe_request = {
            "account_key": account_key,
            "mode": mode,
            "source_info": source_info,
            "post_info": post_info or {},
            "file_sha256": self._file_hash(file_path) if file_path else None,
        }
        fingerprint = self._fingerprint(safe_request)
        existing = self.database.one(
            "SELECT * FROM tiktok_publish_intents WHERE idempotency_key=?",
            (idempotency_key,),
        )
        if existing:
            if str(existing["request_fingerprint"]) != fingerprint:
                raise TikTokError("tiktok_idempotency_payload_conflict")
            return self._public_intent(dict(existing), reused=True)

        now = utc_now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tiktok_publish_intents
                    (idempotency_key, content_id, account_key, mode, media_kind,
                     source_method, request_fingerprint, publish_id, status,
                     attempt_count, external_post_ids_json, last_error_code,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, 'VIDEO', ?, ?, NULL, 'INITIATING',
                        0, '[]', NULL, ?, ?)
                """,
                (
                    idempotency_key,
                    content_id,
                    account_key,
                    mode,
                    source_method,
                    fingerprint,
                    now,
                    now,
                ),
            )
            intent_id = int(cursor.lastrowid)
        try:
            if mode == "DIRECT_POST":
                if post_info is None:
                    raise ValueError("tiktok_post_info_required")
                data = self.adapter.init_direct_video(
                    source_info=source_info,
                    title=str(post_info.get("title") or ""),
                    privacy_level=str(post_info.get("privacy_level") or ""),
                    disable_comment=bool(post_info.get("disable_comment", False)),
                    disable_duet=bool(post_info.get("disable_duet", False)),
                    disable_stitch=bool(post_info.get("disable_stitch", False)),
                    duration_seconds=int(post_info.get("duration_seconds") or 0),
                    is_aigc=bool(post_info.get("is_aigc", False)),
                    explicit_user_consent=bool(
                        post_info.get("explicit_user_consent", False)
                    ),
                    expected_username=account_key,
                )
            else:
                data = self.adapter.init_draft_video(
                    source_info=source_info,
                    expected_username=account_key,
                )
            publish_id = str(data["publish_id"])
            upload_url = str(data.get("upload_url") or "")
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    UPDATE tiktok_publish_intents
                    SET publish_id=?, status=?, attempt_count=1,
                        last_error_code=NULL, updated_at=? WHERE id=?
                    """,
                    (
                        publish_id,
                        "UPLOADING" if source_method == "FILE_UPLOAD" else "PROCESSING",
                        utc_now(),
                        intent_id,
                    ),
                )
            if source_method == "FILE_UPLOAD":
                if file_path is None or not upload_url:
                    raise TikTokError("tiktok_file_upload_handoff_incomplete")
                self.adapter.upload_file(upload_url, file_path)
                with self.database.transaction() as connection:
                    connection.execute(
                        """
                        UPDATE tiktok_publish_intents
                        SET status='PROCESSING', updated_at=? WHERE id=?
                        """,
                        (utc_now(), intent_id),
                    )
        except Exception as error:
            code = error.code if isinstance(error, TikTokError) else type(error).__name__
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    UPDATE tiktok_publish_intents
                    SET status='RECONCILE_REQUIRED', attempt_count=1,
                        last_error_code=?, updated_at=? WHERE id=?
                    """,
                    (str(code), utc_now(), intent_id),
                )
            raise
        row = self.database.one("SELECT * FROM tiktok_publish_intents WHERE id=?", (intent_id,))
        return self._public_intent(dict(row), reused=False)

    def reconcile(self, intent_id: int) -> dict[str, Any]:
        row = self.database.one(
            "SELECT * FROM tiktok_publish_intents WHERE id=?", (intent_id,)
        )
        if row is None:
            raise KeyError("tiktok_intent_not_found")
        publish_id = str(row["publish_id"] or "")
        if not publish_id:
            raise TikTokError("tiktok_publish_id_unknown_manual_review_required")
        data = self.adapter.fetch_status(publish_id)
        status = str(data.get("status") or "UNKNOWN")
        post_ids = data.get("publicaly_available_post_id") or data.get(
            "publicly_available_post_id"
        ) or []
        if not isinstance(post_ids, list):
            post_ids = []
        error_code = str(data.get("fail_reason") or "") or None
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE tiktok_publish_intents
                SET status=?, external_post_ids_json=?, last_error_code=?, updated_at=?
                WHERE id=?
                """,
                (status, json.dumps(post_ids), error_code, utc_now(), intent_id),
            )
        current = self.database.one(
            "SELECT * FROM tiktok_publish_intents WHERE id=?", (intent_id,)
        )
        return self._public_intent(dict(current), reused=False)

    def list(self) -> list[dict[str, Any]]:
        return [
            self._public_intent(dict(row), reused=False)
            for row in self.database.all(
                "SELECT * FROM tiktok_publish_intents ORDER BY id DESC"
            )
        ]

    @staticmethod
    def _file_hash(path: Path | None) -> str | None:
        if path is None:
            return None
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _public_intent(row: dict[str, Any], *, reused: bool) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "idempotency_key": row["idempotency_key"],
            "content_id": row["content_id"],
            "account_key": row["account_key"],
            "mode": row["mode"],
            "media_kind": row["media_kind"],
            "source_method": row["source_method"],
            "publish_id_present": bool(row["publish_id"]),
            "status": row["status"],
            "attempt_count": int(row["attempt_count"]),
            "external_post_ids": json.loads(row["external_post_ids_json"] or "[]"),
            "last_error_code": row["last_error_code"],
            "updated_at": row["updated_at"],
            "reused": reused,
            "retry_policy": "RECONCILE_BEFORE_ANY_RETRY",
        }
