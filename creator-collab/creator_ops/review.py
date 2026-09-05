from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

from .curation import qa_assets, select_diverse_top_picks
from .database import utc_now
from .models import (
    ComplianceInput,
    ContentStage,
    ContentStatus,
    POSE_SLOT_ORDER,
    SafetyClass,
    VisibilityScope,
)
from .pipeline import VerticalPipeline, check_compliance
from .services import AudioService


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
                     safety_class, content_stage, visibility_scope, ai_generated,
                     adult, needs_ai_disclosure, approved, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'PLANNED', 'SFW', 'ALLTAG',
                        'PUBLIC_SFW', 1, 0, 1, 0, ?, ?)
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
            for index, pose_slot in enumerate(POSE_SLOT_ORDER, start=1):
                file_path = (
                    f"assets/review/{creator_slug}/{run_date.isoformat()}/"
                    f"asset-{index}.mock"
                )
                perceptual_hash = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:16]
                connection.execute(
                    """
                    INSERT INTO assets
                        (asset_id, creator_id, content_id, series_id, asset_type,
                         safety_class, content_stage, visibility_scope, pose_slot,
                         similarity_group, status, file_path, reference_version,
                         prompt_version, generator, created_at, estimated_cost,
                         rights_status, platform_allowed, published_status,
                         perceptual_hash, quality_score, persona_fit_score,
                         coherence_score, stage_fit_score, novelty_score,
                         is_top_pick)
                    VALUES (?, ?, ?, ?, 'image', 'SFW', 'ALLTAG', 'PUBLIC_SFW',
                            ?, '', 'GENERATED', ?, 'v1', 'review-v1',
                            'mock-generator', ?, 0, 'AI_GENERATED',
                            'instagram,threads,tiktok', 'UNPUBLISHED', ?, ?, ?,
                            ?, ?, ?, 0)
                    """,
                    (
                        f"review-{creator_slug}-{run_date.isoformat()}-{index}",
                        creator["id"],
                        content_id,
                        series_id,
                        pose_slot.value,
                        file_path,
                        now,
                        perceptual_hash,
                        0.96 - index * 0.025,
                        0.97 - index * 0.02,
                        0.95 - index * 0.015,
                        1.0,
                        0.80 + index * 0.025,
                    ),
                )
            self.pipeline._transition(
                connection, content_id, ContentStatus.CURATING, "five review assets registered"
            )
            select_diverse_top_picks(connection, content_id)
            self.pipeline.asset_fallbacks.create_plan(connection, content_id)

            compliance = check_compliance(
                ComplianceInput(
                    platform="instagram",
                    safety_class=SafetyClass.SFW,
                    ai_generated=True,
                    needs_ai_disclosure=True,
                    disclosure_present=bool(persona["disclosure"]),
                    rights_status="AI_GENERATED",
                    content_stage=ContentStage.ALLTAG,
                    visibility_scope=VisibilityScope.PUBLIC_SFW,
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
        queue = connection.execute(
            """
            SELECT planned_at
            FROM publish_queue
            WHERE content_id=?
              AND status NOT IN ('OWNER_CHANGE_REQUESTED','OWNER_REJECTED')
            ORDER BY approval_version DESC, id DESC
            LIMIT 1
            """,
            (content_row["id"],),
        ).fetchone()
        if queue and queue["planned_at"]:
            value = datetime.fromisoformat(queue["planned_at"])
            if value.tzinfo is None:
                value = value.replace(tzinfo=self.pipeline.scheduler.timezone)
            else:
                value = value.astimezone(self.pipeline.scheduler.timezone)
            return value.strftime("%H:%M"), "local-publish-queue", 1.0
        publication = connection.execute(
            """
            SELECT scheduled_at
            FROM publications
            WHERE content_id=? AND provider='mock-draft' AND status='SCHEDULED'
            ORDER BY id DESC
            LIMIT 1
            """,
            (content_row["id"],),
        ).fetchone()
        if publication and publication["scheduled_at"]:
            value = datetime.fromisoformat(publication["scheduled_at"])
            if value.tzinfo is None:
                value = value.replace(tzinfo=self.pipeline.scheduler.timezone)
            else:
                value = value.astimezone(self.pipeline.scheduler.timezone)
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
                       cr.disclosure, r.run_date, v.format, v.caption,
                       v.hook, v.cta, v.hashtags_json
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
                    SELECT a.id, a.asset_id, a.is_top_pick, a.quality_score, a.status,
                           a.generator, a.perceptual_hash, a.pose_slot,
                           similarity_group, safety_class, content_stage,
                           visibility_scope, a.published_status,
                           COALESCE(plan.priority, 99) AS plan_priority
                    FROM assets a
                    LEFT JOIN asset_usage_plan plan
                      ON plan.asset_id=a.id AND plan.content_id=a.content_id
                    WHERE a.content_id = ?
                    ORDER BY a.id
                    """,
                    (row["id"],),
                ).fetchall()
                audio_options = connection.execute(
                    """
                    SELECT label, license_status, fit_score, selected
                    FROM audio_candidates WHERE content_id = ?
                    ORDER BY CASE WHEN license_status='SAFE_NO_AUDIO' THEN 3
                                  WHEN license_status='VERIFY_BEFORE_USE' THEN 2
                                  ELSE 1 END, fit_score DESC, id
                    """,
                    (row["id"],),
                ).fetchall()
                audio = next((item for item in audio_options if item["selected"]), None)
                local_time, schedule_source, schedule_confidence = self._schedule_for_card(
                    connection, row
                )
                queue_state = connection.execute(
                    """
                    SELECT status, planned_at, suggested_at, last_error, adapter_provider
                    FROM publish_queue WHERE content_id=?
                    ORDER BY approval_version DESC, id DESC LIMIT 1
                    """,
                    (row["id"],),
                ).fetchone()
                style_row = connection.execute(
                    """
                    SELECT variant, baseline_json FROM experiments
                    WHERE content_id=? AND variable='style_reference'
                    """,
                    (row["id"],),
                ).fetchone()
                style_metadata = json.loads(style_row["baseline_json"]) if style_row else {}
                checks = {
                    "carousel": row["format"] == "carousel",
                    "caption": bool(row["caption"].strip()),
                    "music": bool(
                        audio
                        and audio["license_status"] in AudioService.AUTO_SELECTABLE
                    ),
                    "prime_time": bool(local_time),
                }
                qa = qa_assets(assets)
                checks["pose_matrix"] = "pose_matrix_incomplete" not in qa.reasons
                checks["top3_diversity"] = not any(
                    reason.startswith("top_pick") or reason == "top_picks_need_action_or_candid"
                    for reason in qa.reasons
                )
                checks["public_scope"] = (
                    row["safety_class"] == SafetyClass.SFW.value
                    and row["visibility_scope"] == VisibilityScope.PUBLIC_SFW.value
                )
                top_order = {
                    int(asset["id"]): index
                    for index, asset in enumerate(
                        sorted(
                            (item for item in assets if item["is_top_pick"]),
                            key=lambda item: (item["plan_priority"], item["id"]),
                        ),
                        start=1,
                    )
                }
                qa_ready = qa.ready and all(checks.values())
                cards.append(
                    {
                        "content_id": row["id"],
                        "creator_slug": row["creator_slug"],
                        "display_name": row["display_name"],
                        "series": row["title"],
                        "niche": row["niche"],
                        "date": row["run_date"],
                        "status": row["status"],
                        "content_stage": row["content_stage"],
                        "safety_class": row["safety_class"],
                        "visibility_scope": row["visibility_scope"],
                        "privacy_blur": row["content_stage"] == ContentStage.ADULT_18.value,
                        "approved": bool(row["approved"]),
                        "ready": qa_ready,
                        "can_approve": (
                            qa_ready
                            and row["status"] == ContentStatus.READY_FOR_REVIEW.value
                            and not bool(row["approved"])
                        ),
                        "qa_reasons": list(qa.reasons),
                        "asset_count": len(assets),
                        "available_asset_count": sum(
                            asset["published_status"] != "PUBLISHED" for asset in assets
                        ),
                        "excluded_published_count": sum(
                            asset["published_status"] == "PUBLISHED" for asset in assets
                        ),
                        "top_pick_count": sum(asset["is_top_pick"] for asset in assets),
                        "assets": [
                            {
                                "id": asset["id"],
                                "label": f"Bild {index}",
                                "top_pick": bool(asset["is_top_pick"]),
                                "top_pick_order": top_order.get(int(asset["id"])),
                                "quality": round(asset["quality_score"] * 100),
                                "pose_slot": asset["pose_slot"],
                                "safety_class": asset["safety_class"],
                                "visibility_scope": asset["visibility_scope"],
                                "published_status": asset["published_status"],
                                "excluded": asset["published_status"] == "PUBLISHED",
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
                        "hook": row["hook"],
                        "cta": row["cta"],
                        "hashtags": json.loads(row["hashtags_json"]),
                        "audio": audio["label"] if audio else None,
                        "audio_license": audio["license_status"] if audio else None,
                        "prime_time": local_time,
                        "schedule_source": schedule_source,
                        "schedule_confidence": schedule_confidence,
                        "schedule_status": queue_state["status"] if queue_state else "NOT_READY",
                        "planned_at": queue_state["planned_at"] if queue_state else None,
                        "suggested_at": queue_state["suggested_at"] if queue_state else None,
                        "schedule_error": queue_state["last_error"] if queue_state else None,
                        "schedule_adapter": queue_state["adapter_provider"] if queue_state else None,
                        "style_reference": style_row["variant"] if style_row else None,
                        "reference_strength": style_metadata.get("reference_strength"),
                        "reference_format": style_metadata.get("reference_format"),
                        "disclosure": row["disclosure"],
                        "audio_options": [
                            {
                                "label": option["label"],
                                "license_status": option["license_status"],
                                "selected": bool(option["selected"]),
                            }
                            for option in audio_options
                        ],
                        "review_guidance": {
                            "approve": "legt einen lokal terminierten Queue-Eintrag an; kein Live-Post",
                            "reject": "blockiert dieses Paket lokal",
                            "change": "setzt das Paket auf Änderungen erforderlich",
                        },
                    }
                )
            return cards
        finally:
            connection.close()

    def review_queue(self) -> dict:
        """Return the actionable post-publish reserve across its planned dates."""
        connection = self.pipeline.db.connect()
        try:
            rows = connection.execute(
                """
                SELECT c.id AS content_id, r.run_date,
                       (SELECT COUNT(*) FROM assets a
                        WHERE a.content_id=c.id AND a.generator='local-import')
                           AS real_asset_count,
                       (SELECT COUNT(*) FROM assets a
                        WHERE a.content_id=c.id AND a.generator='local-import'
                          AND a.published_status!='PUBLISHED')
                           AS available_real_asset_count
                FROM runs r
                JOIN content_items c ON c.run_id=r.id
                WHERE c.run_key LIKE 'review:%'
                  AND c.status IN ('READY_FOR_REVIEW','PARTIAL_READY','BLOCKED',
                                   'OWNER_APPROVED','SCHEDULED')
                ORDER BY r.run_date, c.id
                """
            ).fetchall()
        finally:
            connection.close()
        productive = [
            row
            for row in rows
            if int(row["real_asset_count"]) >= 3
            and int(row["available_real_asset_count"]) >= 3
        ]
        selected = productive or list(rows)
        selected_ids = {int(row["content_id"]) for row in selected}
        dates = list(dict.fromkeys(row["run_date"] for row in selected))
        return {
            "dates": dates,
            "cards": [
                card
                for value in dates
                for card in self.cards(date.fromisoformat(value))
                if int(card["content_id"]) in selected_ids
            ],
        }

    def approve(self, content_id: int) -> dict:
        with self.pipeline.db.transaction() as connection:
            row = connection.execute(
                """
                SELECT c.*, cr.slug AS creator_slug, r.run_date,
                       v.id AS variant_id, v.platform, v.disclosure
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
            assets = connection.execute(
                """
                SELECT is_top_pick, perceptual_hash, pose_slot, similarity_group,
                       rights_status, safety_class, content_stage, visibility_scope
                FROM assets WHERE content_id = ? ORDER BY id
                """,
                (content_id,),
            ).fetchall()
            qa = qa_assets(assets)
            if not qa.ready:
                raise ValueError(f"review_card_qa_failed: {','.join(qa.reasons)}")
            reasons: set[str] = set()
            for asset in assets:
                compliance = check_compliance(
                    ComplianceInput(
                        platform=row["platform"],
                        safety_class=SafetyClass(asset["safety_class"]),
                        ai_generated=bool(row["ai_generated"]),
                        needs_ai_disclosure=bool(row["needs_ai_disclosure"]),
                        disclosure_present=bool(row["disclosure"]),
                        rights_status=asset["rights_status"],
                        content_stage=ContentStage(asset["content_stage"]),
                        visibility_scope=VisibilityScope(asset["visibility_scope"]),
                    )
                )
                reasons.update(compliance.reasons)
            if reasons:
                raise ValueError(f"review_card_compliance_failed: {','.join(sorted(reasons))}")
            schedule = self.pipeline.scheduler.choose(
                connection,
                row["creator_id"],
                date.fromisoformat(row["run_date"]),
                "instagram",
                "carousel",
            )
            approval_version = int(
                connection.execute(
                    """
                    SELECT COUNT(*) + 1 FROM review_events
                    WHERE content_id=? AND action='OWNER_APPROVED_UI'
                    """,
                    (content_id,),
                ).fetchone()[0]
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
            publication_id = connection.execute(
                """
                INSERT INTO publications
                    (content_id, platform_variant_id, provider, scheduled_at,
                     schedule_status, schedule_timezone, schedule_source,
                     approval_version, status)
                VALUES (?, ?, 'mock-draft', ?, 'LOCAL_SCHEDULED',
                        'Europe/Berlin', ?, ?, 'SCHEDULED')
                RETURNING id
                """,
                (
                    content_id,
                    row["variant_id"],
                    schedule.scheduled_at.isoformat(),
                    schedule.source,
                    approval_version,
                ),
            ).fetchone()[0]
            from .publishing import PublishQueueService

            PublishQueueService(self.pipeline.db).enqueue_approved(
                connection,
                content_id=content_id,
                publication_id=publication_id,
                planned_at=schedule.scheduled_at.isoformat(),
                approval_version=approval_version,
                schedule_source=schedule.source,
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
        return {
            "content_id": content_id,
            "status": "SCHEDULED",
            "schedule_status": "LOCAL_SCHEDULED",
            "reused": False,
        }

    def record_owner_decision(self, content_id: int, action: str, note: str = "") -> dict:
        actions = {
            "reject": (ContentStatus.BLOCKED.value, "OWNER_REJECTED_UI"),
            "change": (ContentStatus.PARTIAL_READY.value, "OWNER_CHANGE_REQUESTED_UI"),
        }
        if action not in actions:
            raise ValueError("invalid_review_action")
        note = note.strip()[:500] or (
            "Owner rejected package" if action == "reject" else "Owner requested changes"
        )
        target, event_action = actions[action]
        with self.pipeline.db.transaction() as connection:
            row = connection.execute(
                "SELECT id, status FROM content_items WHERE id=? AND run_key LIKE 'review:%'",
                (content_id,),
            ).fetchone()
            if row is None:
                raise KeyError("review_card_not_found")
            previous = row["status"]
            queued = connection.execute(
                """
                SELECT id, external_schedule_id FROM publish_queue
                WHERE content_id=? ORDER BY approval_version DESC, id DESC LIMIT 1
                """,
                (content_id,),
            ).fetchone()
            queue_status = (
                "OWNER_ACTION_REQUIRED"
                if queued is not None and queued["external_schedule_id"]
                else ("OWNER_CHANGE_REQUESTED" if action == "change" else "OWNER_REJECTED")
            )
            if queued is not None:
                connection.execute(
                    """
                    UPDATE publish_queue SET status=?, last_error=?, updated_at=?
                    WHERE id=?
                    """,
                    (queue_status, note, utc_now(), queued["id"]),
                )
            connection.execute(
                """
                UPDATE publications
                SET status='PAUSED_OWNER_REVIEW', schedule_status=?, schedule_error=?
                WHERE content_id=? AND provider LIKE 'mock%' AND status='SCHEDULED'
                """,
                (queue_status, note, content_id),
            )
            connection.execute(
                "UPDATE content_items SET approved=0,status=?,updated_at=? WHERE id=?",
                (target, utc_now(), content_id),
            )
            connection.execute(
                """
                INSERT INTO review_events(content_id,action,actor,note,created_at)
                VALUES (?,?,'owner-dashboard',?,?)
                """,
                (content_id, event_action, note, utc_now()),
            )
            connection.execute(
                """
                INSERT INTO content_status_events
                    (content_id,previous_status,new_status,note,created_at)
                VALUES (?,?,?,?,?)
                """,
                (content_id, previous, target, note, utc_now()),
            )
        return {"content_id": content_id, "status": target, "action": action}
