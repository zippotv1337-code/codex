from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from urllib.parse import urlparse

from .database import CreatorDatabase, utc_now
from .curation import select_diverse_top_picks
from .services import EngagementQueueService


class ManualInstagramService:
    """Record owner-confirmed Instagram activity without calling Instagram."""

    PROVIDER = "instagram-native-manual"
    SOURCE = "MANUAL_OWNER"
    WINDOWS = {24, 72, 168}

    def __init__(self, database: CreatorDatabase):
        self.database = database

    @staticmethod
    def _shortcode(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "instagram.com",
            "www.instagram.com",
        }:
            raise ValueError("invalid_instagram_url")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2 or parts[-2] not in {"p", "reel"}:
            raise ValueError("invalid_instagram_post_url")
        return parts[-1]

    def reconcile(
        self,
        *,
        creator_slug: str,
        content_id: int,
        external_url: str,
        published_at: str,
        ai_disclosure: bool = True,
        asset_id: int | None = None,
        asset_ids: Iterable[int] | None = None,
    ) -> dict[str, object]:
        shortcode = self._shortcode(external_url)
        datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        resolved_asset_ids = tuple(
            dict.fromkeys(
                [int(value) for value in (asset_ids or ())]
                + ([int(asset_id)] if asset_id is not None else [])
            )
        )
        with self.database.transaction() as connection:
            row = connection.execute(
                """
                SELECT c.id, c.creator_id, c.status, v.id AS variant_id
                FROM content_items c
                JOIN creators cr ON cr.id = c.creator_id
                JOIN platform_variants v ON v.content_id = c.id AND v.platform = 'instagram'
                WHERE c.id = ? AND cr.slug = ?
                """,
                (content_id, creator_slug),
            ).fetchone()
            if row is None:
                raise KeyError("content_or_creator_not_found")
            existing = connection.execute(
                """
                SELECT id FROM publications
                WHERE provider LIKE ? AND (external_id = ? OR external_url = ?)
                """,
                (f"{self.PROVIDER}%", shortcode, external_url),
            ).fetchone()
            if existing:
                publication_id = int(existing["id"])
                self.refresh_after_native_publication(connection, publication_id)
                return {"publication_id": publication_id, "reused": True}
            if resolved_asset_ids:
                placeholders = ",".join("?" for _ in resolved_asset_ids)
                matched_assets = connection.execute(
                    f"SELECT COUNT(*) FROM assets WHERE content_id = ? AND id IN ({placeholders})",
                    (content_id, *resolved_asset_ids),
                ).fetchone()[0]
                if matched_assets != len(resolved_asset_ids):
                    raise KeyError("asset_not_in_content")
            provider = self.PROVIDER
            if connection.execute(
                "SELECT 1 FROM publications WHERE content_id=? AND provider=?",
                (content_id, self.PROVIDER),
            ).fetchone():
                provider = f"{self.PROVIDER}:{shortcode}"
            cursor = connection.execute(
                """
                INSERT INTO publications
                    (content_id, platform_variant_id, provider, scheduled_at,
                     published_at, external_id, external_url, source,
                     ai_disclosure, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PUBLISHED')
                """,
                (
                    content_id,
                    row["variant_id"],
                    provider,
                    published_at,
                    published_at,
                    shortcode,
                    external_url,
                    self.SOURCE,
                    int(ai_disclosure),
                ),
            )
            publication_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO adapter_attempts
                    (content_id, adapter_type, provider, status, detail, created_at)
                VALUES (?, 'publication-reconcile', ?, 'SUCCESS', ?, ?)
                """,
                (
                    content_id,
                    provider,
                    "owner-confirmed native post; no external API call",
                    utc_now(),
                ),
            )
            if resolved_asset_ids:
                placeholders = ",".join("?" for _ in resolved_asset_ids)
                connection.execute(
                    f"UPDATE assets SET published_status = 'PUBLISHED' WHERE id IN ({placeholders})",
                    resolved_asset_ids,
                )
            self.refresh_after_native_publication(connection, publication_id)
        return {
            "publication_id": publication_id,
            "reused": False,
            "provider": provider,
            "asset_ids": list(resolved_asset_ids),
        }

    @staticmethod
    def refresh_after_native_publication(connection, publication_id: int) -> tuple[int, ...]:
        publication = connection.execute(
            """
            SELECT p.*, c.creator_id, c.approved, c.status AS content_status
            FROM publications p JOIN content_items c ON c.id=p.content_id
            WHERE p.id=? AND p.provider LIKE 'instagram-native-manual%'
            """,
            (publication_id,),
        ).fetchone()
        if publication is None:
            raise KeyError("manual_publication_not_found")
        paused = connection.execute(
            """
            UPDATE publications SET status='PAUSED_DUPLICATE_RISK'
            WHERE content_id=? AND provider LIKE 'mock%' AND status='SCHEDULED'
            """,
            (publication["content_id"],),
        ).rowcount
        published_assets = connection.execute(
            "SELECT COUNT(*) FROM assets WHERE content_id=? AND published_status='PUBLISHED'",
            (publication["content_id"],),
        ).fetchone()[0]
        expected_top_picks = connection.execute(
            "SELECT COUNT(*) FROM assets WHERE content_id=? AND is_top_pick=1",
            (publication["content_id"],),
        ).fetchone()[0]
        published_top_picks = connection.execute(
            """
            SELECT COUNT(*) FROM assets
            WHERE content_id=? AND is_top_pick=1 AND published_status='PUBLISHED'
            """,
            (publication["content_id"],),
        ).fetchone()[0]
        complete_carousel = (
            expected_top_picks >= 2 and published_top_picks == expected_top_picks
        )
        if complete_carousel:
            published_ids = tuple(
                int(row["id"])
                for row in connection.execute(
                    """
                    SELECT id FROM assets
                    WHERE content_id=? AND is_top_pick=1 AND published_status='PUBLISHED'
                    ORDER BY id
                    """,
                    (publication["content_id"],),
                ).fetchall()
            )
            connection.execute(
                """
                UPDATE asset_usage_plan SET status='PUBLISHED_USED'
                WHERE asset_id IN (
                    SELECT id FROM assets
                    WHERE content_id=? AND published_status='PUBLISHED'
                )
                """,
                (publication["content_id"],),
            )
            connection.execute(
                """
                UPDATE publish_queue
                SET status='PUBLISHED', last_error=NULL, next_attempt_at=NULL,
                    suggested_at=NULL, external_schedule_id=?, updated_at=?
                WHERE content_id=? AND status NOT IN ('PUBLISHED','OWNER_REJECTED')
                """,
                (
                    publication["external_id"],
                    utc_now(),
                    publication["content_id"],
                ),
            )
            previous_status = publication["content_status"]
            connection.execute(
                "UPDATE content_items SET status='PUBLISHED', updated_at=? WHERE id=?",
                (utc_now(), publication["content_id"]),
            )
            if previous_status != "PUBLISHED":
                connection.execute(
                    """
                    INSERT INTO content_status_events
                        (content_id,previous_status,new_status,note,created_at)
                    VALUES (?,?,'PUBLISHED',
                            'owner-confirmed native carousel publication',?)
                    """,
                    (publication["content_id"], previous_status, utc_now()),
                )
                connection.execute(
                    """
                    INSERT INTO review_events(content_id,action,actor,note,created_at)
                    VALUES (?,'NATIVE_CAROUSEL_RECONCILED','owner',
                            'All selected carousel assets confirmed live on Instagram',?)
                    """,
                    (publication["content_id"], utc_now()),
                )
            EngagementQueueService().seed(
                connection,
                publication["creator_id"],
                publication_id,
                "instagram",
                publication["external_url"],
                publication["published_at"],
            )
            return published_ids
        selected = select_diverse_top_picks(
            connection, publication["content_id"], exclude_published=bool(published_assets)
        )
        connection.execute(
            "UPDATE asset_usage_plan SET status='PUBLISHED_USED' WHERE asset_id IN "
            "(SELECT id FROM assets WHERE content_id=? AND published_status='PUBLISHED')",
            (publication["content_id"],),
        )
        for priority, asset_id in enumerate(selected, start=1):
            role = "PRIMARY" if priority == 1 else "ALTERNATE"
            connection.execute(
                """
                UPDATE asset_usage_plan
                SET role=?, priority=?, trigger_reason='reselected after native single-asset post',
                    status='READY'
                WHERE content_id=? AND asset_id=?
                """,
                (role, priority, publication["content_id"], asset_id),
            )
        if paused and (publication["approved"] or publication["content_status"] == "SCHEDULED"):
            now = utc_now()
            connection.execute(
                """
                UPDATE publish_queue
                SET status='OWNER_ACTION_REQUIRED',
                    last_error='native_single_asset_published_carousel_review_required',
                    updated_at=?
                WHERE content_id=? AND status NOT IN ('PUBLISHED','OWNER_REJECTED')
                """,
                (now, publication["content_id"]),
            )
            connection.execute(
                "UPDATE content_items SET approved=0, status='READY_FOR_REVIEW', updated_at=? WHERE id=?",
                (now, publication["content_id"]),
            )
            connection.execute(
                """
                INSERT INTO review_events(content_id,action,actor,note,created_at)
                VALUES (?,'REVIEW_RESET_NATIVE_ASSET_PUBLISHED','creator-ops',
                        'Mock schedule paused; published asset excluded from refreshed Top 3',?)
                """,
                (publication["content_id"], now),
            )
            connection.execute(
                """
                INSERT INTO content_status_events(content_id,previous_status,new_status,note,created_at)
                VALUES (?,'SCHEDULED','READY_FOR_REVIEW',
                        'native single asset published; carousel requires refreshed owner review',?)
                """,
                (publication["content_id"], now),
            )
        EngagementQueueService().seed(
            connection,
            publication["creator_id"],
            publication_id,
            "instagram",
            publication["external_url"],
            publication["published_at"],
        )
        return selected

    def append_analytics(
        self,
        publication_id: int,
        window_hours: int,
        *,
        captured_at: str | None = None,
        note: str = "",
        **metrics: int | float | None,
    ) -> int:
        if window_hours not in self.WINDOWS:
            raise ValueError("window_hours_must_be_24_72_or_168")
        allowed = {
            "reach",
            "views",
            "likes",
            "comments",
            "shares",
            "saves",
            "profile_visits",
            "follows",
            "link_clicks",
            "revenue",
        }
        unknown = set(metrics) - allowed
        if unknown:
            raise ValueError(f"unknown_metrics:{','.join(sorted(unknown))}")
        values = {name: metrics.get(name) for name in sorted(allowed)}
        if any(value is not None and value < 0 for value in values.values()):
            raise ValueError("analytics_values_must_be_non_negative")
        if not self.database.one(
            "SELECT id FROM publications WHERE id = ? AND provider LIKE ?",
            (publication_id, f"{self.PROVIDER}%"),
        ):
            raise KeyError("manual_publication_not_found")
        columns = list(values)
        with self.database.transaction() as connection:
            cursor = connection.execute(
                f"""
                INSERT INTO manual_analytics_events
                    (publication_id, window_hours, captured_at, source,
                     {', '.join(columns)}, note)
                VALUES (?, ?, ?, 'MANUAL_OWNER', {', '.join('?' for _ in columns)}, ?)
                """,
                (
                    publication_id,
                    window_hours,
                    captured_at or utc_now(),
                    *(values[name] for name in columns),
                    note,
                ),
            )
        return int(cursor.lastrowid)
