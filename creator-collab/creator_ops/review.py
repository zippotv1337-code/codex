from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

from .database import utc_now
from .models import ComplianceInput, ContentStatus, SafetyClass
from .pipeline import VerticalPipeline, check_compliance


class ReviewDashboardService:
    """Prepare tomorrow's drafts and expose a human approval read model."""

    def __init__(self, pipeline: VerticalPipeline):
        self.pipeline = pipeline

    def ensure_date(self, run_date: date) -> list[dict]:
        for slug in ("leona-voss", "mara-field"):
            self._ensure_creator_draft(slug, run_date)
        return self.cards(run_date)

    def _ensure_creator_draft(self, creator_slug: str, run_date: date) -> int:
        persona = self.pipeline.personas[creator_slug]
        run_key = f"review:{run_date.isoformat()}:{creator_slug}:{persona['default_series']}"
        existing = self.pipeline.db.one(
            "SELECT id FROM content_items WHERE run_key = ?", (run_key,)
        )
        if existing:
            return int(existing["id"])

        with self.pipeline.db.transaction() as connection:
            creator = connection.execute(
                "SELECT * FROM creators WHERE slug = ?", (creator_slug,)
            ).fetchone()
            if creator is None:
                raise RuntimeError("Database has not been initialized")
            now = utc_now()
            series_id = connection.execute(
                """
                INSERT INTO series (creator_id, name, description, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(creator_id, name) DO UPDATE SET description=excluded.description
                RETURNING id
                """,
                (
                    creator["id"],
                    persona["default_series"],
                    f"Repeatable series for {persona['niche']}",
                    now,
                ),
            ).fetchone()[0]
            run_id = connection.execute(
                """
                INSERT INTO runs (run_key, creator_id, run_date, status, started_at)
                VALUES (?, ?, ?, 'REVIEW_READY', ?)
                RETURNING id
                """,
                (run_key, creator["id"], run_date.isoformat(), now),
            ).fetchone()[0]
            content_id = connection.execute(
                """
                INSERT INTO content_items
                    (creator_id, series_id, run_id, run_key, title, idea, status,
                     safety_class, ai_generated, adult, needs_ai_disclosure,
                     approved, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'PLANNED', 'SFW', 1, 0, 1, 0, ?, ?)
                RETURNING id
                """,
                (
                    creator["id"],
                    series_id,
                    run_id,
                    run_key,
                    persona["default_series"],
                    f"Tomorrow review package: {persona['default_series']}",
                    now,
                    now,
                ),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO content_status_events
                    (content_id, previous_status, new_status, note, created_at)
                VALUES (?, NULL, 'PLANNED', 'review package created', ?)
                """,
                (content_id, now),
            )
            self.pipeline._transition(
                connection, content_id, ContentStatus.GENERATING, "review assets prepared"
            )
            for index in range(1, 6):
                file_path = (
                    f"assets/review/{creator_slug}/{run_date.isoformat()}/"
                    f"asset-{index}.mock"
                )
                perceptual_hash = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:16]
                connection.execute(
                    """
                    INSERT INTO assets
                        (asset_id, creator_id, content_id, series_id, asset_type,
                         safety_class, status, file_path, reference_version,
                         prompt_version, generator, created_at, estimated_cost,
                         rights_status, platform_allowed, published_status,
                         perceptual_hash, quality_score, persona_fit_score,
                         coherence_score, is_top_pick)
                    VALUES (?, ?, ?, ?, 'image', 'SFW', 'GENERATED', ?, 'v1',
                            'review-v1', 'mock-generator', ?, 0, 'AI_GENERATED',
                            'instagram,threads,tiktok', 'UNPUBLISHED', ?, ?, ?, ?, 0)
                    """,
                    (
                        f"review-{creator_slug}-{run_date.isoformat()}-{index}",
                        creator["id"],
                        content_id,
                        series_id,
                        file_path,
                        now,
                        perceptual_hash,
                        0.96 - index * 0.025,
                        0.97 - index * 0.02,
                        0.95 - index * 0.015,
                    ),
                )
            self.pipeline._transition(
                connection, content_id, ContentStatus.CURATING, "five review assets registered"
            )
            connection.execute(
                """
                UPDATE assets SET is_top_pick = 1, status = 'CURATED'
                WHERE id IN (
                    SELECT id FROM assets WHERE content_id = ?
                    ORDER BY (quality_score + persona_fit_score + coherence_score) DESC
                    LIMIT 3
                )
                """,
                (content_id,),
            )
            self.pipeline.asset_fallbacks.create_plan(connection, content_id)

            compliance = check_compliance(
                ComplianceInput(
                    platform="instagram",
                    safety_class=SafetyClass.SFW,
                    ai_generated=True,
                    needs_ai_disclosure=True,
                    disclosure_present=bool(persona["disclosure"]),
                    rights_status="AI_GENERATED",
                )
            )
            if not compliance.allowed:
                raise ValueError(f"compliance failed: {compliance.reasons}")
            # Keep disclosure as structured publishing metadata. Do not append the
            # same AI notice to every organic caption; the owner reviews the native
            # platform disclosure separately.
            caption = f"{persona['default_series']} — {persona['default_hook']}"
            connection.execute(
                """
                INSERT INTO platform_variants
                    (content_id, platform, format, hook, caption, hashtags_json,
                     cta, disclosure, created_at)
                VALUES (?, 'instagram', 'carousel', ?, ?, ?, ?, ?, ?)
                """,
                (
                    content_id,
                    persona["default_hook"],
                    caption,
                    json.dumps(["virtualcreator", creator_slug]),
                    persona["default_hook"],
                    persona["disclosure"],
                    now,
                ),
            )
            self.pipeline.audio_service.register_candidates(
                connection, content_id, creator_slug, persona["default_series"]
            )
            self.pipeline._transition(
                connection,
                content_id,
                ContentStatus.READY_FOR_REVIEW,
                "dashboard checklist complete",
            )
        return int(content_id)

    def _schedule_for_card(self, connection, content_row) -> tuple[str, str, float]:
        publication = connection.execute(
            "SELECT scheduled_at FROM publications WHERE content_id = ?",
            (content_row["id"],),
        ).fetchone()
        if publication:
            value = datetime.fromisoformat(publication["scheduled_at"])
            return value.strftime("%H:%M"), "approved-draft", 1.0
        decision = self.pipeline.scheduler.choose(
            connection,
            content_row["creator_id"],
            date.fromisoformat(content_row["run_date"]),
            "instagram",
            "carousel",
        )
        return decision.local_time, decision.source, decision.confidence

    def cards(self, run_date: date) -> list[dict]:
        connection = self.pipeline.db.connect()
        try:
            rows = connection.execute(
                """
                SELECT c.*, cr.slug AS creator_slug, cr.display_name, cr.niche,
                       cr.disclosure, r.run_date, v.format, v.caption
                FROM content_items c
                JOIN creators cr ON cr.id = c.creator_id
                JOIN runs r ON r.id = c.run_id
                JOIN platform_variants v ON v.content_id = c.id
                WHERE r.run_date = ? AND c.run_key LIKE 'review:%'
                ORDER BY CASE cr.slug WHEN 'leona-voss' THEN 1 ELSE 2 END
                """,
                (run_date.isoformat(),),
            ).fetchall()
            cards: list[dict] = []
            for row in rows:
                assets = connection.execute(
                    """
                    SELECT id, asset_id, is_top_pick, quality_score, status, generator
                    FROM assets WHERE content_id = ?
                    ORDER BY (quality_score + persona_fit_score + coherence_score) DESC
                    """,
                    (row["id"],),
                ).fetchall()
                audio = connection.execute(
                    """
                    SELECT label, license_status FROM audio_candidates
                    WHERE content_id = ? AND selected = 1
                    """,
                    (row["id"],),
                ).fetchone()
                local_time, schedule_source, schedule_confidence = self._schedule_for_card(
                    connection, row
                )
                checks = {
                    "carousel": row["format"] == "carousel",
                    "caption": bool(row["caption"].strip()),
                    "music": audio is not None,
                    "prime_time": bool(local_time),
                }
                cards.append(
                    {
                        "content_id": row["id"],
                        "creator_slug": row["creator_slug"],
                        "display_name": row["display_name"],
                        "series": row["title"],
                        "niche": row["niche"],
                        "date": row["run_date"],
                        "status": row["status"],
                        "approved": bool(row["approved"]),
                        "ready": len(assets) == 5
                        and sum(asset["is_top_pick"] for asset in assets) == 3
                        and all(checks.values()),
                        "asset_count": len(assets),
                        "top_pick_count": sum(asset["is_top_pick"] for asset in assets),
                        "assets": [
                            {
                                "id": asset["id"],
                                "label": f"Bild {index}",
                                "top_pick": bool(asset["is_top_pick"]),
                                "quality": round(asset["quality_score"] * 100),
                                "preview_url": (
                                    f"/api/assets/{asset['id']}/preview"
                                    if asset["generator"] == "local-import"
                                    else None
                                ),
                            }
                            for index, asset in enumerate(assets, start=1)
                        ],
                        "checks": checks,
                        "caption": row["caption"],
                        "audio": audio["label"] if audio else None,
                        "audio_license": audio["license_status"] if audio else None,
                        "prime_time": local_time,
                        "schedule_source": schedule_source,
                        "schedule_confidence": schedule_confidence,
                        "disclosure": row["disclosure"],
                    }
                )
            return cards
        finally:
            connection.close()

    def approve(self, content_id: int) -> dict:
        with self.pipeline.db.transaction() as connection:
            row = connection.execute(
                """
                SELECT c.*, cr.slug AS creator_slug, r.run_date, v.id AS variant_id
                FROM content_items c
                JOIN creators cr ON cr.id = c.creator_id
                JOIN runs r ON r.id = c.run_id
                JOIN platform_variants v ON v.content_id = c.id
                WHERE c.id = ? AND c.run_key LIKE 'review:%'
                """,
                (content_id,),
            ).fetchone()
            if row is None:
                raise KeyError("review_card_not_found")
            if row["approved"]:
                return {"content_id": content_id, "status": row["status"], "reused": True}
            if row["status"] != ContentStatus.READY_FOR_REVIEW.value:
                raise ValueError(f"review_card_not_ready: {row['status']}")
            schedule = self.pipeline.scheduler.choose(
                connection,
                row["creator_id"],
                date.fromisoformat(row["run_date"]),
                "instagram",
                "carousel",
            )
            connection.execute(
                """
                INSERT INTO review_events (content_id, action, actor, note, created_at)
                VALUES (?, 'OWNER_APPROVED_UI', 'owner-dashboard',
                        'Approved in local dashboard; no live publishing authorization', ?)
                """,
                (content_id, utc_now()),
            )
            connection.execute(
                "UPDATE content_items SET approved = 1 WHERE id = ?", (content_id,)
            )
            self.pipeline._transition(
                connection,
                content_id,
                ContentStatus.OWNER_APPROVED,
                "owner approved in local dashboard",
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO posting_windows
                    (creator_id, platform, format, weekday, timezone, local_time,
                     source, confidence)
                VALUES (?, 'instagram', 'carousel', ?, 'Europe/Berlin', ?, ?, ?)
                """,
                (
                    row["creator_id"],
                    date.fromisoformat(row["run_date"]).weekday(),
                    schedule.local_time,
                    schedule.source,
                    schedule.confidence,
                ),
            )
            connection.execute(
                """
                INSERT INTO publications
                    (content_id, platform_variant_id, provider, scheduled_at, status)
                VALUES (?, ?, 'mock-draft', ?, 'SCHEDULED')
                """,
                (content_id, row["variant_id"], schedule.scheduled_at.isoformat()),
            )
            self.pipeline._transition(
                connection,
                content_id,
                ContentStatus.SCHEDULED,
                "approved mock draft scheduled; no external action",
            )
            connection.execute(
                "UPDATE runs SET status = 'APPROVED_DRAFT', completed_at = ? WHERE id = ?",
                (utc_now(), row["run_id"]),
            )
        return {"content_id": content_id, "status": "SCHEDULED", "reused": False}
