from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .database import CreatorDatabase, utc_now


LOCAL_SCHEDULED = "LOCAL_SCHEDULED"
PUBLISH_DUE = "PUBLISH_DUE"
PUBLISHING = "PUBLISHING"
PUBLISHED = "PUBLISHED"
NEEDS_RESCHEDULE_REVIEW = "NEEDS_RESCHEDULE_REVIEW"
FAILED_RETRYABLE = "FAILED_RETRYABLE"
BLOCKED_EXTERNAL_PUBLISHING = "BLOCKED_EXTERNAL_PUBLISHING"


@dataclass(frozen=True)
class DispatchResult:
    status: str
    external_id: str | None = None
    external_url: str | None = None
    error: str | None = None


class InstagramPublishingAdapter(Protocol):
    provider: str

    @property
    def available(self) -> bool: ...

    def publish(
        self, publication_id: int, content_id: int, idempotency_key: str
    ) -> DispatchResult: ...


class UnconfiguredInstagramAdapter:
    """Fail-closed placeholder for the future official Meta adapter.

    It deliberately cannot schedule or publish. The local queue remains fully
    testable without credentials while the dashboard reports the real blocker.
    """

    provider = "instagram-official-unconfigured"
    available = False

    def publish(
        self, publication_id: int, content_id: int, idempotency_key: str
    ) -> DispatchResult:
        return DispatchResult(
            status=BLOCKED_EXTERNAL_PUBLISHING,
            error="official_instagram_adapter_not_configured",
        )


class MetaGraphTransport(Protocol):
    def post(self, path: str, data: dict[str, str]) -> dict[str, object]: ...

    def get(self, path: str, params: dict[str, str]) -> dict[str, object]: ...


class MetaGraphError(RuntimeError):
    """Sanitized Graph API failure that never includes tokens or response bodies."""


class UrllibMetaGraphTransport:
    """Small stdlib-only transport for the official Instagram Graph endpoints."""

    def __init__(self, graph_version: str, access_token: str, *, timeout: float = 20) -> None:
        if not re.fullmatch(r"v\d+\.\d+", graph_version):
            raise ValueError("meta_graph_version_required")
        self.base_url = f"https://graph.facebook.com/{graph_version}"
        self.access_token = access_token
        self.timeout = timeout

    def _decode(self, response: object) -> dict[str, object]:
        payload = json.loads(response.read().decode("utf-8"))  # type: ignore[attr-defined]
        if not isinstance(payload, dict):
            raise MetaGraphError("meta_graph_invalid_response")
        error = payload.get("error")
        if isinstance(error, dict):
            code = error.get("code", "unknown")
            raise MetaGraphError(f"meta_graph_error_code_{code}")
        return payload

    def post(self, path: str, data: dict[str, str]) -> dict[str, object]:
        payload = dict(data)
        payload["access_token"] = self.access_token
        request = urllib.request.Request(
            f"{self.base_url}/{path.lstrip('/')}",
            data=urllib.parse.urlencode(payload).encode("utf-8"),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return self._decode(response)
        except urllib.error.HTTPError as error:
            raise MetaGraphError(f"meta_graph_http_{error.code}") from error
        except urllib.error.URLError as error:
            raise ConnectionError("meta_graph_unreachable") from error

    def get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        query = dict(params)
        query["access_token"] = self.access_token
        url = f"{self.base_url}/{path.lstrip('/')}?{urllib.parse.urlencode(query)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                return self._decode(response)
        except urllib.error.HTTPError as error:
            raise MetaGraphError(f"meta_graph_http_{error.code}") from error
        except urllib.error.URLError as error:
            raise ConnectionError("meta_graph_unreachable") from error


class MetaInstagramPublishingAdapter:
    """Official Meta Graph carousel adapter with explicit owner/live gates.

    Public image URLs are deliberately supplied through an ignored local
    manifest. Creator Ops never uploads local files to an unapproved host and
    never persists the Meta access token. An uncertain publish response blocks
    automatic retries so the same carousel cannot be posted twice.
    """

    provider = "instagram-meta-graph"
    manifest_schema = "creator-ops-meta-publish-v1"

    def __init__(
        self,
        database: CreatorDatabase,
        *,
        account_credentials: dict[str, tuple[str, str]],
        graph_version: str,
        manifest_path: Path,
        receipt_directory: Path,
        transport: MetaGraphTransport | None = None,
        poll_attempts: int = 10,
        poll_delay_seconds: float = 1,
    ) -> None:
        self.database = database
        self.account_credentials = {
            slug.strip(): (ig_user_id.strip(), access_token.strip())
            for slug, (ig_user_id, access_token) in account_credentials.items()
            if slug.strip() and ig_user_id.strip() and access_token.strip()
        }
        self.graph_version = graph_version.strip()
        self.manifest_path = manifest_path
        self.receipt_directory = receipt_directory
        self.poll_attempts = max(1, poll_attempts)
        self.poll_delay_seconds = max(0, poll_delay_seconds)
        self.transport = transport

    @classmethod
    def from_environment(
        cls, database: CreatorDatabase, project_root: Path
    ) -> MetaInstagramPublishingAdapter | UnconfiguredInstagramAdapter:
        accounts: dict[str, tuple[str, str]] = {}
        for creator_slug, suffix in (
            ("leona-voss", "LEONA_VOSS"),
            ("mara-field", "MARA_FIELD"),
        ):
            ig_user_id = os.environ.get(f"META_IG_USER_ID_{suffix}", "").strip()
            access_token = os.environ.get(f"META_ACCESS_TOKEN_{suffix}", "").strip()
            if ig_user_id and access_token:
                accounts[creator_slug] = (ig_user_id, access_token)
        graph_version = os.environ.get("META_GRAPH_API_VERSION", "").strip()
        configured_manifest = os.environ.get("CREATOR_OPS_META_MEDIA_MANIFEST", "").strip()
        manifest_path = (
            Path(configured_manifest)
            if configured_manifest
            else project_root / "data" / "meta_media_urls.json"
        )
        if not (accounts and graph_version and manifest_path.is_file()):
            return UnconfiguredInstagramAdapter()
        try:
            return cls(
                database,
                account_credentials=accounts,
                graph_version=graph_version,
                manifest_path=manifest_path,
                receipt_directory=project_root / "data" / "meta-receipts",
            )
        except ValueError:
            return UnconfiguredInstagramAdapter()

    @property
    def available(self) -> bool:
        return bool(
            self.account_credentials
            and all(
                ig_user_id.isdigit() and bool(access_token)
                for ig_user_id, access_token in self.account_credentials.values()
            )
            and re.fullmatch(r"v\d+\.\d+", self.graph_version)
            and self.manifest_path.is_file()
        )

    @staticmethod
    def _valid_instagram_confirmation(external_id: object, external_url: object) -> bool:
        if not isinstance(external_id, str) or not external_id.strip():
            return False
        if not isinstance(external_url, str):
            return False
        parsed = urlparse(external_url)
        return (
            parsed.scheme == "https"
            and parsed.hostname is not None
            and (
                parsed.hostname == "instagram.com"
                or parsed.hostname.endswith(".instagram.com")
            )
        )

    def _receipt_path(self, idempotency_key: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", idempotency_key):
            raise ValueError("invalid_publish_idempotency_key")
        return self.receipt_directory / f"{idempotency_key}.json"

    def _read_receipt(self, idempotency_key: str) -> DispatchResult | None:
        path = self._receipt_path(idempotency_key)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("schema") != "creator-ops-meta-receipt-v1"
            or payload.get("idempotency_key") != idempotency_key
        ):
            raise ValueError("invalid_meta_publish_receipt")
        receipt_status = payload.get("status")
        if receipt_status == "PUBLISH_INTENT":
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                error="meta_publish_intent_exists_owner_reconcile_required",
            )
        if receipt_status != "CONFIRMED":
            raise ValueError("invalid_meta_publish_receipt")
        external_id = payload.get("external_id")
        external_url = payload.get("external_url")
        if not self._valid_instagram_confirmation(external_id, external_url):
            raise ValueError("invalid_meta_publish_receipt")
        return DispatchResult(
            status=PUBLISHED,
            external_id=str(external_id),
            external_url=str(external_url),
        )

    def _write_receipt(
        self,
        idempotency_key: str,
        external_id: str,
        external_url: str,
        *,
        creation_id: str,
        creator_slug: str,
        ig_user_id: str,
    ) -> None:
        destination = self._receipt_path(idempotency_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "schema": "creator-ops-meta-receipt-v1",
                    "status": "CONFIRMED",
                    "idempotency_key": idempotency_key,
                    "external_id": external_id,
                    "external_url": external_url,
                    "creation_id": creation_id,
                    "creator_slug": creator_slug,
                    "ig_user_id": ig_user_id,
                    "confirmed_at": utc_now(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(destination)

    def _write_publish_intent(
        self,
        idempotency_key: str,
        *,
        creation_id: str,
        creator_slug: str,
        ig_user_id: str,
    ) -> None:
        destination = self._receipt_path(idempotency_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "schema": "creator-ops-meta-receipt-v1",
                    "status": "PUBLISH_INTENT",
                    "idempotency_key": idempotency_key,
                    "creation_id": creation_id,
                    "creator_slug": creator_slug,
                    "ig_user_id": ig_user_id,
                    "created_at": utc_now(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(destination)

    def _content_payload(self, publication_id: int, content_id: int) -> dict[str, object]:
        publication = self.database.one(
            """
            SELECT v.caption, v.hashtags_json, p.ai_disclosure,
                   cr.slug AS creator_slug,
                   (
                       SELECT e.action FROM review_events e
                       WHERE e.content_id=p.content_id
                         AND e.action IN (
                             'OWNER_LIVE_PUBLISH_APPROVED_UI',
                             'OWNER_LIVE_PUBLISH_REVOKED_UI',
                             'OWNER_CHANGE_REQUESTED_UI',
                             'OWNER_REJECTED_UI'
                         )
                       ORDER BY e.id DESC LIMIT 1
                   ) AS live_gate_action
            FROM publications p
            JOIN platform_variants v ON v.id=p.platform_variant_id
            JOIN content_items c ON c.id=p.content_id
            JOIN creators cr ON cr.id=c.creator_id
            WHERE p.id=? AND p.content_id=?
            """,
            (publication_id, content_id),
        )
        if publication is None:
            raise ValueError("publication_not_found")
        assets = self.database.all(
            """
            SELECT a.asset_id, COALESCE(plan.priority, 9999) AS priority
            FROM assets a
            LEFT JOIN asset_usage_plan plan
              ON plan.asset_id=a.id AND plan.content_id=a.content_id
            WHERE a.content_id=? AND a.is_top_pick=1
              AND a.published_status!='PUBLISHED'
              AND a.safety_class='SFW'
              AND a.visibility_scope='PUBLIC_SFW'
            ORDER BY priority, a.id
            """,
            (content_id,),
        )
        if len(assets) != 3:
            raise ValueError("three_unpublished_public_top_picks_required")
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema") != self.manifest_schema:
            raise ValueError("meta_manifest_schema_invalid")
        content_section = manifest.get("content")
        if not isinstance(content_section, dict):
            raise ValueError("meta_content_manifest_missing")
        content_manifest = content_section.get(str(content_id), {})
        if not isinstance(content_manifest, dict):
            raise ValueError("meta_content_manifest_missing")
        if not content_manifest.get("native_ai_disclosure_confirmed"):
            raise ValueError("native_ai_disclosure_owner_confirmation_required")
        if not publication["ai_disclosure"]:
            raise ValueError("publication_ai_disclosure_required")
        if publication["live_gate_action"] != "OWNER_LIVE_PUBLISH_APPROVED_UI":
            raise ValueError("per_content_live_publish_owner_authorization_required")
        url_map = content_manifest.get("asset_urls", {})
        if not isinstance(url_map, dict):
            raise ValueError("meta_asset_url_map_missing")
        media_urls: list[str] = []
        for asset in assets:
            url = url_map.get(asset["asset_id"])
            parsed = urlparse(str(url or ""))
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError(f"public_https_url_required_for_{asset['asset_id']}")
            media_urls.append(str(url))
        hashtags = json.loads(publication["hashtags_json"])
        if not isinstance(hashtags, list):
            raise ValueError("publication_hashtags_invalid")
        caption = publication["caption"].strip()
        if hashtags:
            normalized_hashtags = [
                value if value.startswith("#") else f"#{value}"
                for value in (str(item).strip() for item in hashtags)
                if value
            ]
            caption = f"{caption}\n\n{' '.join(normalized_hashtags)}"
        return {
            "caption": caption,
            "media_urls": media_urls,
            "creator_slug": publication["creator_slug"],
        }

    def _wait_until_ready(self, transport: MetaGraphTransport, creation_id: str) -> None:
        for attempt in range(self.poll_attempts):
            payload = transport.get(creation_id, {"fields": "status_code"})
            status = str(payload.get("status_code", "")).upper()
            if status == "FINISHED":
                return
            if status in {"ERROR", "EXPIRED"}:
                raise MetaGraphError(f"meta_container_{status.lower()}")
            if attempt + 1 < self.poll_attempts and self.poll_delay_seconds:
                time.sleep(self.poll_delay_seconds)
        raise TimeoutError("meta_container_not_ready")

    def publish(
        self, publication_id: int, content_id: int, idempotency_key: str
    ) -> DispatchResult:
        if not self.available:
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                error="official_instagram_adapter_not_configured",
            )
        try:
            prior = self._read_receipt(idempotency_key)
            if prior is not None:
                return prior
            payload = self._content_payload(publication_id, content_id)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                error=str(error),
            )

        creator_slug = str(payload["creator_slug"])
        account = self.account_credentials.get(creator_slug)
        if account is None:
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                error=f"meta_account_not_configured_for_{creator_slug}",
            )
        ig_user_id, access_token = account
        transport = self.transport or UrllibMetaGraphTransport(
            self.graph_version, access_token
        )

        child_ids: list[str] = []
        try:
            for media_url in payload["media_urls"]:
                response = transport.post(
                    f"{ig_user_id}/media",
                    {"image_url": str(media_url), "is_carousel_item": "true"},
                )
                child_id = str(response.get("id", ""))
                if not child_id:
                    raise MetaGraphError("meta_child_container_id_missing")
                child_ids.append(child_id)
            parent = transport.post(
                f"{ig_user_id}/media",
                {
                    "media_type": "CAROUSEL",
                    "children": ",".join(child_ids),
                    "caption": str(payload["caption"]),
                    "is_ai_generated": "true",
                },
            )
            creation_id = str(parent.get("id", ""))
            if not creation_id:
                raise MetaGraphError("meta_parent_container_id_missing")
            self._wait_until_ready(transport, creation_id)
        except (ConnectionError, TimeoutError, MetaGraphError) as error:
            return DispatchResult(status=FAILED_RETRYABLE, error=str(error))

        try:
            self._write_publish_intent(
                idempotency_key,
                creation_id=creation_id,
                creator_slug=creator_slug,
                ig_user_id=ig_user_id,
            )
        except OSError:
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                error="meta_publish_intent_write_failed_no_publish_attempt",
            )

        try:
            published = transport.post(
                f"{ig_user_id}/media_publish", {"creation_id": creation_id}
            )
        except (ConnectionError, TimeoutError, MetaGraphError):
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                error="meta_publish_outcome_unknown_owner_reconcile_required",
            )
        external_id = str(published.get("id", ""))
        if not external_id:
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                error="meta_publish_confirmation_id_missing",
            )
        try:
            confirmation = transport.get(
                external_id, {"fields": "id,permalink"}
            )
        except (ConnectionError, TimeoutError, MetaGraphError):
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                external_id=external_id,
                error="meta_publish_confirmation_unknown_owner_reconcile_required",
            )
        confirmed_id = confirmation.get("id")
        external_url = confirmation.get("permalink")
        if (
            str(confirmed_id or "") != external_id
            or not self._valid_instagram_confirmation(confirmed_id, external_url)
        ):
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                external_id=external_id,
                error="meta_publish_confirmation_incomplete",
            )
        try:
            self._write_receipt(
                idempotency_key,
                str(confirmed_id),
                str(external_url),
                creation_id=creation_id,
                creator_slug=creator_slug,
                ig_user_id=ig_user_id,
            )
        except OSError:
            # The post is already confirmed externally. Never turn this into an
            # automatic retry: without a durable receipt, an owner must
            # reconcile the known permalink before the queue can continue.
            return DispatchResult(
                status=BLOCKED_EXTERNAL_PUBLISHING,
                external_id=str(confirmed_id),
                external_url=str(external_url),
                error="meta_publish_confirmed_receipt_write_failed_owner_reconcile_required",
            )
        return DispatchResult(
            status=PUBLISHED,
            external_id=str(confirmed_id),
            external_url=str(external_url),
        )


class PublishQueueService:
    """Durable, idempotent local scheduling queue behind the owner gate."""

    SAFE_PREFLIGHT_ERRORS = {
        "official_instagram_adapter_not_configured",
        "publication_not_found",
        "three_unpublished_public_top_picks_required",
        "meta_manifest_schema_invalid",
        "meta_content_manifest_missing",
        "native_ai_disclosure_owner_confirmation_required",
        "publication_ai_disclosure_required",
        "per_content_live_publish_owner_authorization_required",
        "meta_asset_url_map_missing",
        "publication_hashtags_invalid",
        "meta_publish_intent_write_failed_no_publish_attempt",
    }
    SAFE_PREFLIGHT_PREFIXES = (
        "public_https_url_required_for_",
        "meta_account_not_configured_for_",
    )

    def __init__(
        self,
        database: CreatorDatabase,
        adapter: InstagramPublishingAdapter | None = None,
        *,
        missed_slot_grace: timedelta = timedelta(minutes=15),
        retry_delay: timedelta = timedelta(minutes=5),
    ) -> None:
        self.database = database
        self.adapter = adapter or UnconfiguredInstagramAdapter()
        self.missed_slot_grace = missed_slot_grace
        self.retry_delay = retry_delay
        self.timezone = ZoneInfo("Europe/Berlin")

    @staticmethod
    def _as_utc(value: datetime | None = None) -> datetime:
        current = value or datetime.now(UTC)
        if current.tzinfo is None:
            return current.replace(tzinfo=UTC)
        return current.astimezone(UTC)

    @staticmethod
    def _queue_key(
        platform: str,
        content_id: int,
        approval_version: int,
        planned_at: str,
    ) -> str:
        source = f"{platform}|{content_id}|{approval_version}|{planned_at}"
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def _next_local_suggestion(self, planned: datetime, current: datetime) -> datetime:
        """Keep the local wall-clock slot and always propose a future Berlin date."""
        local_planned = planned.astimezone(self.timezone)
        local_current = current.astimezone(self.timezone)
        candidate_date = max(
            local_planned.date() + timedelta(days=1),
            local_current.date(),
        )
        candidate = datetime.combine(
            candidate_date,
            local_planned.time().replace(tzinfo=None),
            self.timezone,
        )
        if candidate <= local_current:
            candidate = datetime.combine(
                candidate_date + timedelta(days=1),
                local_planned.time().replace(tzinfo=None),
                self.timezone,
            )
        return candidate

    @classmethod
    def is_safe_preflight_error(cls, error: object) -> bool:
        value = str(error or "")
        return value in cls.SAFE_PREFLIGHT_ERRORS or value.startswith(
            cls.SAFE_PREFLIGHT_PREFIXES
        )

    @staticmethod
    def _validate_approved(connection: sqlite3.Connection, content_id: int) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT c.id, c.approved, c.status, c.safety_class,
                   c.visibility_scope, v.platform
            FROM content_items c
            JOIN platform_variants v ON v.content_id=c.id
            WHERE c.id=?
            """,
            (content_id,),
        ).fetchone()
        if row is None:
            raise KeyError("content_not_found")
        if not row["approved"]:
            raise ValueError("owner_approval_required")
        if row["safety_class"] != "SFW" or row["visibility_scope"] != "PUBLIC_SFW":
            raise ValueError("public_sfw_content_required")
        return row

    def enqueue_approved(
        self,
        connection: sqlite3.Connection,
        *,
        content_id: int,
        publication_id: int,
        planned_at: str,
        approval_version: int = 1,
        schedule_source: str = "creator-ops-prime-time",
    ) -> dict[str, object]:
        content = self._validate_approved(connection, content_id)
        planned = datetime.fromisoformat(planned_at)
        if planned.tzinfo is None:
            raise ValueError("planned_at_requires_timezone")
        queue_key = self._queue_key(
            content["platform"], content_id, approval_version, planned_at
        )
        now = utc_now()
        connection.execute(
            """
            INSERT INTO publish_queue
                (queue_key, publication_id, content_id, platform, planned_at,
                 timezone, approval_version, status, attempts, adapter_provider,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Europe/Berlin', ?, ?, 0, ?, ?, ?)
            ON CONFLICT(publication_id, approval_version) DO NOTHING
            """,
            (
                queue_key,
                publication_id,
                content_id,
                content["platform"],
                planned_at,
                approval_version,
                LOCAL_SCHEDULED,
                self.adapter.provider,
                now,
                now,
            ),
        )
        row = connection.execute(
            "SELECT * FROM publish_queue WHERE publication_id=? AND approval_version=?",
            (publication_id, approval_version),
        ).fetchone()
        # The queue is authoritative once it exists. Reconciliation must never
        # turn a blocked, retryable or owner-review state back into scheduled.
        connection.execute(
            """
            UPDATE publications
            SET schedule_status=?, schedule_timezone=?,
                schedule_source=COALESCE(schedule_source, ?),
                approval_version=?, schedule_error=?,
                external_schedule_id=COALESCE(?, external_schedule_id)
            WHERE id=?
            """,
            (
                row["status"],
                row["timezone"],
                schedule_source,
                row["approval_version"],
                row["last_error"],
                row["external_schedule_id"],
                publication_id,
            ),
        )
        return dict(row)

    def reconcile(self, now: datetime | None = None) -> dict[str, int]:
        current = self._as_utc(now)
        created = 0
        reschedule = 0
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE publish_queue
                SET status='PUBLISHED', last_error=NULL, updated_at=?
                WHERE publication_id IN (
                    SELECT id FROM publications WHERE status='PUBLISHED'
                ) AND status!='PUBLISHED'
                """,
                (utc_now(),),
            )
            stale_before = (current - self.missed_slot_grace).isoformat()
            stale_claims = connection.execute(
                """
                SELECT id, publication_id FROM publish_queue
                WHERE status=? AND updated_at < ?
                """,
                (PUBLISHING, stale_before),
            ).fetchall()
            connection.execute(
                """
                UPDATE publish_queue
                SET status=?,
                    last_error='stale_publishing_claim_owner_reconcile_required',
                    next_attempt_at=NULL, suggested_at=NULL, updated_at=?
                WHERE status=? AND updated_at < ?
                """,
                (
                    BLOCKED_EXTERNAL_PUBLISHING,
                    utc_now(),
                    PUBLISHING,
                    stale_before,
                ),
            )
            for stale in stale_claims:
                connection.execute(
                    """
                    UPDATE publications
                    SET schedule_status=?,
                        schedule_error='stale_publishing_claim_owner_reconcile_required'
                    WHERE id=?
                    """,
                    (BLOCKED_EXTERNAL_PUBLISHING, stale["publication_id"]),
                )
            connection.execute(
                """
                UPDATE publish_queue
                SET status=?, updated_at=?
                WHERE status=? AND next_attempt_at IS NOT NULL AND next_attempt_at <= ?
                """,
                (LOCAL_SCHEDULED, utc_now(), FAILED_RETRYABLE, current.isoformat()),
            )
            rows = connection.execute(
                """
                SELECT c.id AS content_id, p.id AS publication_id, p.scheduled_at,
                       CASE WHEN p.approval_version > 0 THEN p.approval_version ELSE 1 END
                           AS approval_version,
                       p.schedule_source
                FROM content_items c
                JOIN publications p ON p.content_id=c.id
                WHERE c.approved=1
                  AND c.status IN ('OWNER_APPROVED','SCHEDULED')
                  AND p.status NOT IN ('PUBLISHED','PAUSED_OWNER_REVIEW')
                  AND p.provider='mock-draft'
                ORDER BY p.id
                """
            ).fetchall()
            for row in rows:
                existed = connection.execute(
                    """
                    SELECT 1 FROM publish_queue
                    WHERE publication_id=? AND approval_version=?
                    """,
                    (row["publication_id"], row["approval_version"]),
                ).fetchone()
                self.enqueue_approved(
                    connection,
                    content_id=row["content_id"],
                    publication_id=row["publication_id"],
                    planned_at=row["scheduled_at"],
                    approval_version=row["approval_version"],
                    schedule_source=row["schedule_source"] or "startup-reconcile",
                )
                if existed is None:
                    created += 1

            queued = connection.execute(
                "SELECT id, publication_id, planned_at FROM publish_queue WHERE status=?",
                (LOCAL_SCHEDULED,),
            ).fetchall()
            for row in queued:
                planned = datetime.fromisoformat(row["planned_at"])
                if self._as_utc(planned) < current - self.missed_slot_grace:
                    suggestion = self._next_local_suggestion(planned, current)
                    connection.execute(
                        """
                        UPDATE publish_queue
                        SET status=?, last_error='planned_slot_expired_owner_review_required',
                            suggested_at=?, updated_at=? WHERE id=?
                        """,
                        (
                            NEEDS_RESCHEDULE_REVIEW,
                            suggestion.isoformat(),
                            utc_now(),
                            row["id"],
                        ),
                    )
                    connection.execute(
                        """
                        UPDATE publications
                        SET schedule_status=?, schedule_error=? WHERE id=?
                        """,
                        (
                            NEEDS_RESCHEDULE_REVIEW,
                            "planned_slot_expired_owner_review_required",
                            row["publication_id"],
                        ),
                    )
                    reschedule += 1
        return {"created": created, "needs_reschedule_review": reschedule}

    def dispatch_due(self, now: datetime | None = None) -> dict[str, int]:
        current = self._as_utc(now)
        summary = {
            "due": 0,
            "published": 0,
            "blocked": 0,
            "failed_retryable": 0,
            "needs_reschedule_review": 0,
        }
        candidates = self.database.all(
            """
            SELECT q.*, p.status AS publication_status
            FROM publish_queue q
            JOIN publications p ON p.id=q.publication_id
            WHERE q.status=?
            ORDER BY q.planned_at, q.id
            """,
            (LOCAL_SCHEDULED,),
        )
        for candidate in candidates:
            planned = self._as_utc(datetime.fromisoformat(candidate["planned_at"]))
            if planned > current:
                continue
            if planned < current - self.missed_slot_grace:
                continue
            # Claim and commit before any adapter call. A real adapter must use
            # queue_key as its external idempotency token.
            with self.database.transaction() as connection:
                claimed = connection.execute(
                    """
                    UPDATE publish_queue
                    SET status=?, attempts=attempts+1, adapter_provider=?, updated_at=?
                    WHERE id=? AND status=?
                    """,
                    (
                        PUBLISHING,
                        self.adapter.provider,
                        utc_now(),
                        candidate["id"],
                        LOCAL_SCHEDULED,
                    ),
                ).rowcount
                if claimed != 1:
                    continue
                connection.execute(
                    "UPDATE publications SET schedule_status=? WHERE id=?",
                    (PUBLISHING, candidate["publication_id"]),
                )
            summary["due"] += 1
            try:
                result = self.adapter.publish(
                    candidate["publication_id"],
                    candidate["content_id"],
                    candidate["queue_key"],
                )
            except (ConnectionError, TimeoutError) as error:
                result = DispatchResult(
                    status=FAILED_RETRYABLE,
                    error=f"{type(error).__name__}: {error}",
                )
            except Exception as error:
                result = DispatchResult(
                    status=FAILED_RETRYABLE,
                    error=f"unexpected_adapter_error:{type(error).__name__}",
                )
            with self.database.transaction() as connection:
                row = connection.execute(
                """
                SELECT * FROM publish_queue WHERE id=? AND status=?
                """,
                    (candidate["id"], PUBLISHING),
                ).fetchone()
                if row is None:
                    continue
                confirmed_publication = (
                    result.status == PUBLISHED
                    and MetaInstagramPublishingAdapter._valid_instagram_confirmation(
                        result.external_id, result.external_url
                    )
                )
                if confirmed_publication:
                    final_status = PUBLISHED
                    summary["published"] += 1
                elif result.status == PUBLISHED:
                    final_status = BLOCKED_EXTERNAL_PUBLISHING
                    result = DispatchResult(
                        status=BLOCKED_EXTERNAL_PUBLISHING,
                        error="official_publish_confirmation_incomplete",
                    )
                    summary["blocked"] += 1
                elif result.status == BLOCKED_EXTERNAL_PUBLISHING:
                    final_status = BLOCKED_EXTERNAL_PUBLISHING
                    summary["blocked"] += 1
                else:
                    final_status = FAILED_RETRYABLE
                    summary["failed_retryable"] += 1
                next_attempt_at = None
                suggested_at = None
                if final_status == FAILED_RETRYABLE:
                    retry_at = current + self.retry_delay
                    planned = self._as_utc(datetime.fromisoformat(row["planned_at"]))
                    if retry_at <= planned + self.missed_slot_grace:
                        next_attempt_at = retry_at.isoformat()
                    else:
                        final_status = NEEDS_RESCHEDULE_REVIEW
                        summary["failed_retryable"] -= 1
                        summary["needs_reschedule_review"] += 1
                        result = DispatchResult(
                            status=NEEDS_RESCHEDULE_REVIEW,
                            error="retry_window_expired_owner_review_required",
                        )
                        suggested_at = self._next_local_suggestion(
                            datetime.fromisoformat(row["planned_at"]), current
                        ).isoformat()
                connection.execute(
                    """
                    UPDATE publish_queue
                    SET status=?, last_error=?, external_schedule_id=?,
                        next_attempt_at=?, suggested_at=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        final_status,
                        result.error,
                        result.external_id,
                        next_attempt_at,
                        suggested_at,
                        utc_now(),
                        row["id"],
                    ),
                )
                connection.execute(
                    """
                    UPDATE publications
                    SET schedule_status=?, schedule_error=?, external_schedule_id=?,
                        external_id=COALESCE(?, external_id),
                        external_url=COALESCE(?, external_url),
                        published_at=CASE WHEN ?=? THEN ? ELSE published_at END,
                        status=CASE WHEN ?=? THEN 'PUBLISHED' ELSE status END
                    WHERE id=?
                    """,
                    (
                        final_status,
                        result.error,
                        result.external_id,
                        result.external_id,
                        result.external_url,
                        final_status,
                        PUBLISHED,
                        utc_now(),
                        final_status,
                        PUBLISHED,
                        row["publication_id"],
                    ),
                )
                if final_status == PUBLISHED:
                    previous = connection.execute(
                        "SELECT status FROM content_items WHERE id=?",
                        (row["content_id"],),
                    ).fetchone()[0]
                    connection.execute(
                        "UPDATE content_items SET status='PUBLISHED', updated_at=? WHERE id=?",
                        (utc_now(), row["content_id"]),
                    )
                    connection.execute(
                        """
                        INSERT INTO content_status_events
                            (content_id, previous_status, new_status, note, created_at)
                        VALUES (?, ?, 'PUBLISHED', 'official adapter confirmed publication', ?)
                        """,
                        (row["content_id"], previous, utc_now()),
                    )
                    connection.execute(
                        """
                        UPDATE assets SET published_status='PUBLISHED'
                        WHERE content_id=? AND is_top_pick=1
                        """,
                        (row["content_id"],),
                    )
                    connection.execute(
                        "UPDATE publications SET provider=? WHERE id=?",
                        (self.adapter.provider, row["publication_id"]),
                    )
                connection.execute(
                    """
                    INSERT INTO adapter_attempts
                        (content_id, adapter_type, provider, status, detail, created_at)
                    VALUES (?, 'publisher', ?, ?, ?, ?)
                    """,
                    (
                        row["content_id"],
                        self.adapter.provider,
                        final_status,
                        result.error or "official adapter publication succeeded",
                        utc_now(),
                    ),
                    )
        return summary

    def accept_suggested_reschedule(
        self, content_id: int, now: datetime | None = None
    ) -> dict[str, object]:
        """Apply a future suggested slot only after an explicit owner action."""
        current = self._as_utc(now)
        with self.database.transaction() as connection:
            row = connection.execute(
                """
                SELECT q.*, c.approved
                FROM publish_queue q
                JOIN content_items c ON c.id=q.content_id
                WHERE q.content_id=?
                ORDER BY q.approval_version DESC, q.id DESC LIMIT 1
                """,
                (content_id,),
            ).fetchone()
            if row is None:
                raise KeyError("publish_queue_job_not_found")
            if row["status"] != NEEDS_RESCHEDULE_REVIEW:
                raise ValueError("reschedule_review_not_required")
            if not row["approved"]:
                raise ValueError("owner_approval_required")
            if row["external_schedule_id"]:
                raise ValueError("external_schedule_owner_action_required")
            if not row["suggested_at"]:
                raise ValueError("reschedule_suggestion_missing")
            suggested = datetime.fromisoformat(row["suggested_at"])
            if self._as_utc(suggested) <= current:
                raise ValueError("reschedule_suggestion_expired")
            planned_at = suggested.isoformat()
            connection.execute(
                """
                UPDATE publish_queue
                SET planned_at=?, status=?, last_error=NULL,
                    suggested_at=NULL, next_attempt_at=NULL,
                    adapter_provider=?, updated_at=?
                WHERE id=?
                """,
                (
                    planned_at,
                    LOCAL_SCHEDULED,
                    self.adapter.provider,
                    utc_now(),
                    row["id"],
                ),
            )
            connection.execute(
                """
                UPDATE publications
                SET scheduled_at=?, schedule_status=?, schedule_error=NULL,
                    schedule_source='owner-reschedule-confirmed'
                WHERE id=?
                """,
                (planned_at, LOCAL_SCHEDULED, row["publication_id"]),
            )
            connection.execute(
                """
                INSERT INTO review_events(content_id,action,actor,note,created_at)
                VALUES (?,'OWNER_RESCHEDULED_UI','owner-dashboard',?,?)
                """,
                (
                    content_id,
                    f"Owner accepted suggested local slot {planned_at}; no live post",
                    utc_now(),
                ),
            )
        return {
            "content_id": content_id,
            "status": LOCAL_SCHEDULED,
            "planned_at": planned_at,
            "external_action": False,
        }

    def authorize_live_publish(self, content_id: int) -> dict[str, object]:
        """Record a separate, auditable owner gate without publishing anything."""
        with self.database.transaction() as connection:
            row = connection.execute(
                """
                SELECT c.approved, c.status, q.id AS queue_id,
                       q.publication_id, q.status AS queue_status,
                       q.planned_at, q.last_error, q.external_schedule_id
                FROM content_items c
                JOIN publish_queue q ON q.content_id=c.id
                WHERE c.id=?
                ORDER BY q.approval_version DESC, q.id DESC LIMIT 1
                """,
                (content_id,),
            ).fetchone()
            if row is None:
                raise KeyError("publish_queue_job_not_found")
            if not row["approved"] or row["status"] != "SCHEDULED":
                raise ValueError("local_owner_approval_required_first")
            missing_live_gate_block = (
                row["queue_status"] == BLOCKED_EXTERNAL_PUBLISHING
                and row["last_error"]
                == "per_content_live_publish_owner_authorization_required"
            )
            safe_preflight_block = (
                row["queue_status"] == BLOCKED_EXTERNAL_PUBLISHING
                and self.is_safe_preflight_error(row["last_error"])
            )
            if row["queue_status"] != LOCAL_SCHEDULED and not safe_preflight_block:
                raise ValueError("local_schedule_must_be_ready_before_live_authorization")
            if row["external_schedule_id"]:
                raise ValueError("external_schedule_already_exists")
            latest = connection.execute(
                """
                SELECT action FROM review_events
                WHERE content_id=? AND action IN (
                    'OWNER_LIVE_PUBLISH_APPROVED_UI',
                    'OWNER_LIVE_PUBLISH_REVOKED_UI',
                    'OWNER_CHANGE_REQUESTED_UI',
                    'OWNER_REJECTED_UI'
                )
                ORDER BY id DESC LIMIT 1
                """,
                (content_id,),
            ).fetchone()
            if latest and latest["action"] == "OWNER_LIVE_PUBLISH_APPROVED_UI":
                return {
                    "content_id": content_id,
                    "live_publish_authorized": True,
                    "external_action": False,
                    "reused": True,
                }
            connection.execute(
                """
                INSERT INTO review_events(content_id,action,actor,note,created_at)
                VALUES (?,'OWNER_LIVE_PUBLISH_APPROVED_UI','owner-dashboard',?,?)
                """,
                (
                    content_id,
                    "Owner authorized this exact locally scheduled package for official live dispatch; no external action performed yet",
                    utc_now(),
                ),
            )
            resulting_status = row["queue_status"]
            if missing_live_gate_block:
                current = self._as_utc()
                planned = datetime.fromisoformat(row["planned_at"])
                if self._as_utc(planned) < current - self.missed_slot_grace:
                    resulting_status = NEEDS_RESCHEDULE_REVIEW
                    suggestion = self._next_local_suggestion(planned, current).isoformat()
                    error = "live_authorized_after_expired_slot_owner_reschedule_required"
                else:
                    resulting_status = LOCAL_SCHEDULED
                    suggestion = None
                    error = None
                connection.execute(
                    """
                    UPDATE publish_queue
                    SET status=?, last_error=?, suggested_at=?, updated_at=?
                    WHERE id=?
                    """,
                    (resulting_status, error, suggestion, utc_now(), row["queue_id"]),
                )
                connection.execute(
                    """
                    UPDATE publications SET schedule_status=?, schedule_error=?
                    WHERE id=?
                    """,
                    (resulting_status, error, row["publication_id"]),
                )
        return {
            "content_id": content_id,
            "live_publish_authorized": True,
            "external_action": False,
            "reused": False,
            "schedule_status": resulting_status,
        }

    def rearm_blocked_preflight(
        self, content_id: int, now: datetime | None = None
    ) -> dict[str, object]:
        """Owner-triggered retry for provably pre-publish failures only."""
        current = self._as_utc(now)
        with self.database.transaction() as connection:
            row = connection.execute(
                """
                SELECT q.*, c.approved,
                       (
                           SELECT e.action FROM review_events e
                           WHERE e.content_id=q.content_id AND e.action IN (
                               'OWNER_LIVE_PUBLISH_APPROVED_UI',
                               'OWNER_LIVE_PUBLISH_REVOKED_UI',
                               'OWNER_CHANGE_REQUESTED_UI',
                               'OWNER_REJECTED_UI'
                           )
                           ORDER BY e.id DESC LIMIT 1
                       ) AS live_gate_action
                FROM publish_queue q
                JOIN content_items c ON c.id=q.content_id
                WHERE q.content_id=?
                ORDER BY q.approval_version DESC, q.id DESC LIMIT 1
                """,
                (content_id,),
            ).fetchone()
            if row is None:
                raise KeyError("publish_queue_job_not_found")
            if row["status"] != BLOCKED_EXTERNAL_PUBLISHING:
                raise ValueError("blocked_preflight_job_required")
            if not self.is_safe_preflight_error(row["last_error"]):
                raise ValueError("unsafe_publish_outcome_requires_manual_reconcile")
            if row["external_schedule_id"]:
                raise ValueError("external_schedule_owner_action_required")
            if not row["approved"]:
                raise ValueError("owner_approval_required")
            if row["live_gate_action"] != "OWNER_LIVE_PUBLISH_APPROVED_UI":
                raise ValueError("per_content_live_publish_owner_authorization_required")
            planned = datetime.fromisoformat(row["planned_at"])
            if self._as_utc(planned) < current - self.missed_slot_grace:
                final_status = NEEDS_RESCHEDULE_REVIEW
                suggested_at = self._next_local_suggestion(planned, current).isoformat()
                error = "preflight_rearmed_after_expired_slot_owner_reschedule_required"
            else:
                final_status = LOCAL_SCHEDULED
                suggested_at = None
                error = None
            connection.execute(
                """
                UPDATE publish_queue
                SET status=?, last_error=?, suggested_at=?, next_attempt_at=NULL,
                    adapter_provider=?, updated_at=? WHERE id=?
                """,
                (
                    final_status,
                    error,
                    suggested_at,
                    self.adapter.provider,
                    utc_now(),
                    row["id"],
                ),
            )
            connection.execute(
                """
                UPDATE publications SET schedule_status=?, schedule_error=?
                WHERE id=?
                """,
                (final_status, error, row["publication_id"]),
            )
            connection.execute(
                """
                INSERT INTO review_events(content_id,action,actor,note,created_at)
                VALUES (?,'OWNER_REARMED_SAFE_PREFLIGHT_UI','owner-dashboard',?,?)
                """,
                (
                    content_id,
                    f"Owner re-armed safe preflight block; new status {final_status}; no external action",
                    utc_now(),
                ),
            )
        return {
            "content_id": content_id,
            "status": final_status,
            "suggested_at": suggested_at,
            "external_action": False,
        }

    def list(self) -> list[dict[str, object]]:
        return [
            dict(row)
            for row in self.database.all(
                """
                SELECT q.*, cr.slug AS creator_slug, c.title,
                       p.provider, p.status AS publication_status
                FROM publish_queue q
                JOIN content_items c ON c.id=q.content_id
                JOIN creators cr ON cr.id=c.creator_id
                JOIN publications p ON p.id=q.publication_id
                ORDER BY q.planned_at, q.id
                """
            )
        ]
