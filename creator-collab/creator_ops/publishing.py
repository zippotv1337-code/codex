from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
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


class PublishQueueService:
    """Durable, idempotent local scheduling queue behind the owner gate."""

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
            connection.execute(
                """
                UPDATE publish_queue
                SET status=?, last_error='stale_publishing_claim_recovered',
                    next_attempt_at=?, updated_at=?
                WHERE status=? AND updated_at < ?
                """,
                (
                    FAILED_RETRYABLE,
                    current.isoformat(),
                    utc_now(),
                    PUBLISHING,
                    stale_before,
                ),
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
                    SET status=?, attempts=attempts+1, updated_at=?
                    WHERE id=? AND status=?
                    """,
                    (PUBLISHING, utc_now(), candidate["id"], LOCAL_SCHEDULED),
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
                if result.status == PUBLISHED:
                    final_status = PUBLISHED
                    summary["published"] += 1
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
