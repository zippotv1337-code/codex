from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .curation import select_diverse_top_picks
from .database import CreatorDatabase, utc_now
from .models import (
    ComplianceInput,
    ComplianceResult,
    ContentStage,
    ContentStatus,
    POSE_SLOT_ORDER,
    SafetyClass,
    VerticalRunResult,
    VisibilityScope,
)
from .scheduling import PrimeTimePlanner
from .services import (
    AssetFallbackService,
    AudioService,
    EngagementQueueService,
    MockAnalyticsAdapter,
)


PUBLIC_SFW_PLATFORMS = {"instagram", "threads", "tiktok", "youtube"}

ALLOWED_TRANSITIONS = {
    ContentStatus.PLANNED: {ContentStatus.GENERATING, ContentStatus.BLOCKED},
    ContentStatus.GENERATING: {ContentStatus.CURATING, ContentStatus.FAILED_RETRYABLE},
    ContentStatus.CURATING: {ContentStatus.READY_FOR_REVIEW, ContentStatus.PARTIAL_READY},
    ContentStatus.READY_FOR_REVIEW: {ContentStatus.OWNER_APPROVED, ContentStatus.BLOCKED},
    ContentStatus.OWNER_APPROVED: {ContentStatus.SCHEDULED},
    ContentStatus.SCHEDULED: {ContentStatus.PUBLISHED, ContentStatus.FAILED_RETRYABLE},
    ContentStatus.PUBLISHED: {ContentStatus.ANALYZED},
}


def check_compliance(item: ComplianceInput) -> ComplianceResult:
    reasons: list[str] = []
    public_platform = item.platform.lower() in PUBLIC_SFW_PLATFORMS
    if item.content_stage is ContentStage.ADULT_18:
        if item.safety_class is not SafetyClass.ADULT:
            reasons.append("adult_stage_requires_adult_safety")
        if item.visibility_scope is not VisibilityScope.ADULT_ONLY:
            reasons.append("adult_stage_requires_adult_only_visibility")
    elif item.safety_class is SafetyClass.ADULT:
        reasons.append("adult_safety_requires_adult_stage")
    if item.safety_class is SafetyClass.ADULT and item.visibility_scope is not VisibilityScope.ADULT_ONLY:
        reasons.append("adult_content_requires_adult_only_visibility")
    if item.visibility_scope is VisibilityScope.PUBLIC_SFW and item.safety_class is not SafetyClass.SFW:
        reasons.append("public_sfw_visibility_requires_sfw_content")
    if public_platform and item.visibility_scope is not VisibilityScope.PUBLIC_SFW:
        reasons.append("public_platform_requires_public_sfw_visibility")
    if public_platform and item.safety_class is SafetyClass.ADULT:
        reasons.append("adult_content_not_allowed_on_public_sfw_platform")
    if item.ai_generated and item.needs_ai_disclosure and not item.disclosure_present:
        reasons.append("missing_ai_disclosure")
    if item.rights_status not in {"OWNED", "LICENSED", "AI_GENERATED"}:
        reasons.append("unconfirmed_media_rights")
    return ComplianceResult(allowed=not reasons, reasons=tuple(reasons))


class MockPublisher:
    provider = "mock"

    def publish(self, publication_id: int, creator_slug: str) -> tuple[str, str]:
        external_id = f"mock-{creator_slug}-{publication_id}"
        return external_id, f"mock://publication/{external_id}"


class VerticalPipeline:
    def __init__(
        self,
        database: CreatorDatabase,
        persona_config: str | Path,
        prime_time_config: str | Path,
    ):
        self.db = database
        self.persona_config_path = Path(persona_config)
        self.prime_time_config_path = Path(prime_time_config)
        self.personas = json.loads(self.persona_config_path.read_text(encoding="utf-8"))
        self.prime_time = json.loads(self.prime_time_config_path.read_text(encoding="utf-8"))
        self.publisher = MockPublisher()
        self.scheduler = PrimeTimePlanner(self.prime_time)
        self.audio_service = AudioService()
        self.analytics = MockAnalyticsAdapter()
        self.asset_fallbacks = AssetFallbackService()
        self.engagement = EngagementQueueService()

    def initialize(self) -> None:
        self.db.initialize()
        self.db.seed_personas(self.persona_config_path)

    def _transition(
        self,
        connection,
        content_id: int,
        target: ContentStatus,
        note: str,
    ) -> None:
        row = connection.execute(
            "SELECT status FROM content_items WHERE id = ?", (content_id,)
        ).fetchone()
        current = ContentStatus(row[0])
        if target not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(f"Invalid status transition: {current} -> {target}")
        now = utc_now()
        connection.execute(
            "UPDATE content_items SET status = ?, updated_at = ? WHERE id = ?",
            (target.value, now, content_id),
        )
        connection.execute(
            """
            INSERT INTO content_status_events
                (content_id, previous_status, new_status, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (content_id, current.value, target.value, note, now),
        )

    def _existing_result(self, run_key: str) -> VerticalRunResult | None:
        row = self.db.one(
            """
            SELECT c.id AS content_id, c.status, cr.slug, p.id AS publication_id,
                   p.external_url, e.decision
            FROM runs r
            JOIN creators cr ON cr.id = r.creator_id
            JOIN content_items c ON c.run_id = r.id
            JOIN publications p ON p.content_id = c.id
            LEFT JOIN experiments e ON e.content_id = c.id AND e.variable='vertical-demo'
            WHERE r.run_key = ? AND r.status = 'COMPLETE'
            """,
            (run_key,),
        )
        if row is None:
            return None
        return VerticalRunResult(
            run_key=run_key,
            creator_slug=row["slug"],
            content_id=row["content_id"],
            publication_id=row["publication_id"],
            final_status=ContentStatus(row["status"]),
            learning_decision=row["decision"] or "KEEP_TESTING",
            mock_url=row["external_url"],
            reused=True,
        )

    def run(self, creator_slug: str, run_date: date) -> VerticalRunResult:
        if creator_slug not in self.personas:
            raise KeyError(f"Unknown creator: {creator_slug}")
        persona = self.personas[creator_slug]
        run_key = f"{run_date.isoformat()}:{creator_slug}:{persona['default_series']}"
        existing = self._existing_result(run_key)
        if existing:
            return existing

        with self.db.transaction() as connection:
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
                VALUES (?, ?, ?, 'RUNNING', ?)
                ON CONFLICT(run_key) DO UPDATE SET
                    status='RUNNING',
                    started_at=excluded.started_at,
                    completed_at=NULL,
                    error_message=NULL
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
                VALUES (?, ?, ?, ?, ?, ?, ?, 'SFW', 'ALLTAG', 'PUBLIC_SFW',
                        1, 0, 1, 0, ?, ?)
                RETURNING id
                """,
                (
                    creator["id"],
                    series_id,
                    run_id,
                    run_key,
                    persona["default_series"],
                    f"Five-image coherent package: {persona['default_series']}",
                    ContentStatus.PLANNED.value,
                    now,
                    now,
                ),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO content_status_events
                    (content_id, previous_status, new_status, note, created_at)
                VALUES (?, NULL, ?, 'idea and series created', ?)
                """,
                (content_id, ContentStatus.PLANNED.value, now),
            )
            self._transition(connection, content_id, ContentStatus.GENERATING, "asset jobs started")

            hashes: set[str] = set()
            for index, pose_slot in enumerate(POSE_SLOT_ORDER, start=1):
                file_path = (
                    f"assets/{creator_slug}/{run_date.isoformat()}/"
                    f"{persona['default_series'].lower().replace(' ', '-')}-{index}.mock"
                )
                perceptual_hash = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:16]
                if perceptual_hash in hashes:
                    raise ValueError("duplicate asset detected in content package")
                hashes.add(perceptual_hash)
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
                            ?, '', 'GENERATED', ?, 'v1', 'v1', 'mock-generator',
                            ?, 0, 'AI_GENERATED', 'instagram,threads,tiktok',
                            'UNPUBLISHED', ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        f"{creator_slug}-{run_date.isoformat()}-{index}",
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

            self._transition(connection, content_id, ContentStatus.CURATING, "five assets registered")
            select_diverse_top_picks(connection, content_id)
            self.asset_fallbacks.create_plan(connection, content_id)

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

            caption = f"{persona['default_series']} — {persona['default_hook']}"
            variant_id = connection.execute(
                """
                INSERT INTO platform_variants
                    (content_id, platform, format, hook, caption, hashtags_json,
                     cta, disclosure, created_at)
                VALUES (?, 'instagram', 'carousel', ?, ?, ?, ?, ?, ?)
                RETURNING id
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
            ).fetchone()[0]
            self.audio_service.register_candidates(
                connection,
                content_id,
                creator_slug,
                persona["default_series"],
            )
            self._transition(
                connection,
                content_id,
                ContentStatus.READY_FOR_REVIEW,
                "QA, duplicate and compliance checks passed",
            )
            connection.execute(
                """
                INSERT INTO review_events (content_id, action, actor, note, created_at)
                VALUES (?, 'APPROVED_SIMULATION', 'owner-simulator',
                        'Mock approval only; no live posting authorization', ?)
                """,
                (content_id, now),
            )
            connection.execute(
                "UPDATE content_items SET approved = 1 WHERE id = ?", (content_id,)
            )
            self._transition(
                connection,
                content_id,
                ContentStatus.OWNER_APPROVED,
                "approval simulation recorded",
            )

            schedule = self.scheduler.choose(
                connection,
                creator["id"],
                run_date,
                "instagram",
                "carousel",
            )
            scheduled_at = schedule.scheduled_at.isoformat()
            connection.execute(
                """
                INSERT OR IGNORE INTO posting_windows
                    (creator_id, platform, format, weekday, timezone, local_time,
                     source, confidence)
                VALUES (?, 'instagram', 'carousel', ?, 'Europe/Berlin', ?, ?, ?)
                """,
                (
                    creator["id"],
                    run_date.weekday(),
                    schedule.local_time,
                    schedule.source,
                    schedule.confidence,
                ),
            )
            publication_id = connection.execute(
                """
                INSERT INTO publications
                    (content_id, platform_variant_id, provider, scheduled_at, status)
                VALUES (?, ?, ?, ?, 'SCHEDULED')
                RETURNING id
                """,
                (content_id, variant_id, self.publisher.provider, scheduled_at),
            ).fetchone()[0]
            self._transition(connection, content_id, ContentStatus.SCHEDULED, "prime-time slot selected")

            external_id, mock_url = self.publisher.publish(publication_id, creator_slug)
            published_at = utc_now()
            connection.execute(
                """
                UPDATE publications
                SET published_at = ?, external_id = ?, external_url = ?, status = 'PUBLISHED'
                WHERE id = ?
                """,
                (published_at, external_id, mock_url, publication_id),
            )
            connection.execute(
                """
                INSERT INTO adapter_attempts
                    (content_id, adapter_type, provider, status, detail, created_at)
                VALUES (?, 'publisher', ?, 'SUCCESS', 'mock publication created', ?)
                """,
                (content_id, self.publisher.provider, utc_now()),
            )
            self.engagement.seed(
                connection,
                creator["id"],
                publication_id,
                "instagram",
                mock_url,
                published_at,
            )
            self._transition(connection, content_id, ContentStatus.PUBLISHED, "MockPublisher succeeded")

            snapshots = self.analytics.snapshots(creator_slug)
            for snapshot in snapshots:
                connection.execute(
                    """
                    INSERT INTO analytics_snapshots
                        (publication_id, window_hours, captured_at, views, retention,
                         completion, likes, comments, shares, saves, profile_visits,
                         follows, link_clicks, revenue)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        publication_id,
                        snapshot["window_hours"],
                        utc_now(),
                        snapshot["views"],
                        snapshot["retention"],
                        snapshot["completion"],
                        snapshot["likes"],
                        snapshot["comments"],
                        snapshot["shares"],
                        snapshot["saves"],
                        snapshot["profile_visits"],
                        snapshot["follows"],
                        snapshot["link_clicks"],
                    ),
                )
            connection.execute(
                """
                INSERT INTO adapter_attempts
                    (content_id, adapter_type, provider, status, detail, created_at)
                VALUES (?, 'analytics', ?, 'SUCCESS', ?, ?)
                """,
                (content_id, self.analytics.provider, f"{len(snapshots)} mock snapshots", utc_now()),
            )

            metrics = connection.execute(
                """
                SELECT retention, completion, shares * 1.0 / views AS share_rate,
                       follows * 1.0 / views AS follow_rate
                FROM analytics_snapshots
                WHERE publication_id = ? AND window_hours = 168
                """,
                (publication_id,),
            ).fetchone()
            positives = sum(
                (
                    metrics["retention"] > 0.55,
                    metrics["completion"] > 0.40,
                    metrics["share_rate"] > 0.01,
                    metrics["follow_rate"] > 0.008,
                )
            )
            decision = "SCALE_WITH_VARIANTS" if positives >= 2 else "KEEP_TESTING"
            connection.execute(
                """
                INSERT INTO experiments
                    (content_id, variable, variant, baseline_json, decision, created_at)
                VALUES (?, 'vertical-demo', 'A', ?, ?, ?)
                """,
                (
                    content_id,
                    json.dumps(
                        {
                            "retention": 0.55,
                            "completion": 0.40,
                            "share_rate": 0.01,
                            "follow_rate": 0.008,
                        }
                    ),
                    decision,
                    utc_now(),
                ),
            )
            connection.execute(
                """
                INSERT INTO cost_events
                    (creator_id, content_id, amount, currency, category, occurred_at)
                VALUES (?, ?, 0, 'EUR', 'mock_generation', ?)
                """,
                (creator["id"], content_id, utc_now()),
            )
            connection.execute(
                """
                INSERT INTO revenue_events
                    (creator_id, content_id, amount, currency, source, occurred_at)
                VALUES (?, ?, 0, 'EUR', 'mock_publication', ?)
                """,
                (creator["id"], content_id, utc_now()),
            )
            self._transition(connection, content_id, ContentStatus.ANALYZED, "learning decision recorded")
            connection.execute(
                "UPDATE runs SET status = 'COMPLETE', completed_at = ? WHERE id = ?",
                (utc_now(), run_id),
            )

        return VerticalRunResult(
            run_key=run_key,
            creator_slug=creator_slug,
            content_id=content_id,
            publication_id=publication_id,
            final_status=ContentStatus.ANALYZED,
            learning_decision=decision,
            mock_url=mock_url,
        )

    def run_safe(self, creator_slug: str, run_date: date) -> VerticalRunResult | None:
        """Run once and persist a retryable partial state instead of losing the error."""
        try:
            return self.run(creator_slug, run_date)
        except Exception as error:
            if creator_slug not in self.personas:
                raise
            persona = self.personas[creator_slug]
            run_key = f"{run_date.isoformat()}:{creator_slug}:{persona['default_series']}"
            creator = self.db.one("SELECT id FROM creators WHERE slug = ?", (creator_slug,))
            if creator is None:
                raise
            with self.db.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO runs
                        (run_key, creator_id, run_date, status, started_at,
                         completed_at, error_message)
                    VALUES (?, ?, ?, 'PARTIAL_READY', ?, ?, ?)
                    ON CONFLICT(run_key) DO UPDATE SET
                        status='PARTIAL_READY',
                        completed_at=excluded.completed_at,
                        error_message=excluded.error_message
                    """,
                    (
                        run_key,
                        creator["id"],
                        run_date.isoformat(),
                        utc_now(),
                        utc_now(),
                        f"{type(error).__name__}: {error}",
                    ),
                )
            return None

    def run_both(self, run_date: date) -> list[VerticalRunResult]:
        return [self.run(slug, run_date) for slug in ("leona-voss", "mara-field")]

    @staticmethod
    def serialize_results(results: list[VerticalRunResult]) -> str:
        return json.dumps(
            [
                {
                    **asdict(result),
                    "final_status": result.final_status.value,
                }
                for result in results
            ],
            ensure_ascii=False,
            indent=2,
        )
