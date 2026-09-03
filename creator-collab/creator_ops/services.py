from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Protocol

from .database import utc_now
from .models import AudioSelection


class AudioCatalogAdapter(Protocol):
    provider: str

    def search(self, creator_slug: str, series_name: str) -> list[dict]: ...


class AnalyticsAdapter(Protocol):
    provider: str

    def snapshots(self, creator_slug: str) -> list[dict]: ...


class MockAnalyticsAdapter:
    provider = "mock-analytics"

    def snapshots(self, creator_slug: str) -> list[dict]:
        base_views = 800 if creator_slug == "leona-voss" else 650
        results: list[dict] = []
        for window, multiplier in ((24, 1), (72, 2), (168, 3)):
            views = base_views * multiplier
            results.append(
                {
                    "window_hours": window,
                    "views": views,
                    "retention": 0.58 + multiplier * 0.01,
                    "completion": 0.42 + multiplier * 0.01,
                    "likes": int(views * 0.08),
                    "comments": max(3, int(views * 0.009)),
                    "shares": max(4, int(views * 0.014)),
                    "saves": max(5, int(views * 0.018)),
                    "profile_visits": max(6, int(views * 0.022)),
                    "follows": max(3, int(views * 0.011)),
                    "link_clicks": 0,
                    "revenue": 0,
                }
            )
        return results


class MockAudioCatalog:
    provider = "mock-audio-catalog"

    def search(self, creator_slug: str, series_name: str) -> list[dict]:
        return [
            {
                "label": f"{series_name} – Mock Original",
                "reference": f"mock-audio://{creator_slug}/original",
                "license_status": "MOCK_ONLY",
                "fit_score": 0.90,
            },
            {
                "label": "Plattform-Audio manuell prüfen",
                "reference": "platform-native-search",
                "license_status": "VERIFY_BEFORE_USE",
                "fit_score": 0.80,
            },
        ]


class AudioService:
    AUTO_SELECTABLE = {"OWNED", "LICENSED", "SAFE_NO_AUDIO"}

    def __init__(self, adapter: AudioCatalogAdapter | None = None):
        self.adapter = adapter or MockAudioCatalog()

    def register_candidates(
        self,
        connection: sqlite3.Connection,
        content_id: int,
        creator_slug: str,
        series_name: str,
    ) -> AudioSelection:
        fallback_used = False
        try:
            candidates = self.adapter.search(creator_slug, series_name)
            connection.execute(
                """
                INSERT INTO adapter_attempts
                    (content_id, adapter_type, provider, status, detail, created_at)
                VALUES (?, 'audio', ?, 'SUCCESS', ?, ?)
                """,
                (content_id, self.adapter.provider, f"{len(candidates)} candidates", utc_now()),
            )
        except Exception as error:
            candidates = []
            fallback_used = True
            connection.execute(
                """
                INSERT INTO adapter_attempts
                    (content_id, adapter_type, provider, status, fallback_provider,
                     detail, created_at)
                VALUES (?, 'audio', ?, 'FALLBACK', 'safe-no-audio', ?, ?)
                """,
                (content_id, self.adapter.provider, f"{type(error).__name__}: {error}", utc_now()),
            )

        candidates.append(
            {
                "label": "Option ohne Musik",
                "reference": None,
                "license_status": "SAFE_NO_AUDIO",
                "fit_score": 0.70,
            }
        )
        selectable = [item for item in candidates if item["license_status"] in self.AUTO_SELECTABLE]
        selected = max(selectable, key=lambda item: item["fit_score"])
        fallback_used = fallback_used or selected["license_status"] == "SAFE_NO_AUDIO"
        for candidate in candidates:
            connection.execute(
                """
                INSERT INTO audio_candidates
                    (content_id, label, reference, license_status, fit_score, selected)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    content_id,
                    candidate["label"],
                    candidate["reference"],
                    candidate["license_status"],
                    candidate["fit_score"],
                    int(candidate is selected),
                ),
            )
        return AudioSelection(
            label=selected["label"],
            reference=selected["reference"],
            license_status=selected["license_status"],
            provider=self.adapter.provider,
            fallback_used=fallback_used,
        )


class AssetFallbackService:
    def create_plan(self, connection: sqlite3.Connection, content_id: int) -> None:
        assets = connection.execute(
            """
            SELECT id, is_top_pick
            FROM assets WHERE content_id = ?
            ORDER BY is_top_pick DESC,
                     (quality_score + persona_fit_score + coherence_score) DESC,
                     id
            """,
            (content_id,),
        ).fetchall()
        for index, asset in enumerate(assets, start=1):
            if index == 1:
                role, reason = "PRIMARY", "highest combined QA score"
            elif asset["is_top_pick"]:
                role, reason = "ALTERNATE", "approved top-pick replacement"
            else:
                role, reason = "RESERVE", "fallback after primary and alternates"
            connection.execute(
                """
                INSERT INTO asset_usage_plan
                    (content_id, asset_id, role, priority, trigger_reason, status)
                VALUES (?, ?, ?, ?, ?, 'READY')
                """,
                (content_id, asset["id"], role, index, reason),
            )


class EngagementQueueService:
    """Create suggestions only. Nothing in this service performs social actions."""

    def seed(
        self,
        connection: sqlite3.Connection,
        creator_id: int,
        publication_id: int,
        platform: str,
        external_url: str,
        published_at: str,
    ) -> None:
        published = datetime.fromisoformat(published_at)
        suggestions = (
            (
                "REPLY_REVIEW",
                external_url,
                "Kommentare prüfen und nur passende Antworten zur manuellen Freigabe formulieren.",
                "Keine automatischen Antworten, kein Spam, keine privaten Daten übernehmen.",
                1,
                published + timedelta(hours=1),
            ),
            (
                "FOLLOWUP_IDEA",
                external_url,
                "Eine Story- oder Folgepost-Idee aus echten Rückfragen ableiten.",
                "Nur als Entwurf; Veröffentlichung benötigt eine separate Freigabe.",
                2,
                published + timedelta(hours=24),
            ),
        )
        for action_type, target, prompt, safety_note, priority, not_before in suggestions:
            connection.execute(
                """
                INSERT OR IGNORE INTO engagement_queue
                    (creator_id, publication_id, platform, action_type, target_ref,
                     prompt, safety_note, status, priority, not_before, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PROPOSED', ?, ?, ?)
                """,
                (
                    creator_id,
                    publication_id,
                    platform,
                    action_type,
                    target,
                    prompt,
                    safety_note,
                    priority,
                    not_before.isoformat(timespec="seconds"),
                    utc_now(),
                ),
            )

    def list(self, connection: sqlite3.Connection, status: str = "PROPOSED") -> list[dict]:
        rows = connection.execute(
            """
            SELECT q.id, c.slug AS creator_slug, q.platform, q.action_type,
                   q.target_ref, q.prompt, q.safety_note, q.status, q.priority,
                   q.not_before
            FROM engagement_queue q
            JOIN creators c ON c.id = q.creator_id
            WHERE q.status = ? ORDER BY q.priority, q.not_before, q.id
            """,
            (status,),
        ).fetchall()
        return [dict(row) for row in rows]

    def approve_for_manual_action(self, connection: sqlite3.Connection, item_id: int) -> None:
        changed = connection.execute(
            """
            UPDATE engagement_queue
            SET status = 'APPROVED_MANUAL', reviewed_at = ?
            WHERE id = ? AND status = 'PROPOSED'
            """,
            (utc_now(), item_id),
        ).rowcount
        if changed != 1:
            raise ValueError("engagement_item_not_proposed")
