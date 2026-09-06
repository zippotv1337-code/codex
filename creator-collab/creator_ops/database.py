from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS creators (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    instagram_handle TEXT NOT NULL UNIQUE,
    niche TEXT NOT NULL,
    tone TEXT NOT NULL,
    disclosure TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS character_versions (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (creator_id, version)
);

CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE (creator_id, name)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    run_key TEXT NOT NULL UNIQUE,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    run_date TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS content_items (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    series_id INTEGER NOT NULL REFERENCES series(id),
    run_id INTEGER NOT NULL REFERENCES runs(id),
    run_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    idea TEXT NOT NULL,
    status TEXT NOT NULL,
    safety_class TEXT NOT NULL,
    content_stage TEXT NOT NULL DEFAULT 'ALLTAG',
    visibility_scope TEXT NOT NULL DEFAULT 'PUBLIC_SFW',
    ai_generated INTEGER NOT NULL,
    adult INTEGER NOT NULL DEFAULT 0,
    needs_ai_disclosure INTEGER NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_status_events (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content_items(id),
    previous_status TEXT,
    new_status TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    asset_id TEXT NOT NULL UNIQUE,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    content_id INTEGER NOT NULL REFERENCES content_items(id),
    series_id INTEGER NOT NULL REFERENCES series(id),
    asset_type TEXT NOT NULL,
    safety_class TEXT NOT NULL,
    content_stage TEXT NOT NULL DEFAULT 'ALLTAG',
    visibility_scope TEXT NOT NULL DEFAULT 'PUBLIC_SFW',
    pose_slot TEXT NOT NULL DEFAULT 'UNASSIGNED',
    similarity_group TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    reference_version TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    generator TEXT NOT NULL,
    created_at TEXT NOT NULL,
    estimated_cost REAL NOT NULL DEFAULT 0,
    rights_status TEXT NOT NULL,
    platform_allowed TEXT NOT NULL,
    published_status TEXT NOT NULL,
    perceptual_hash TEXT NOT NULL,
    quality_score REAL NOT NULL,
    persona_fit_score REAL NOT NULL,
    coherence_score REAL NOT NULL,
    stage_fit_score REAL NOT NULL DEFAULT 1,
    novelty_score REAL NOT NULL DEFAULT 0.5,
    is_top_pick INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS platform_variants (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content_items(id),
    platform TEXT NOT NULL,
    format TEXT NOT NULL,
    hook TEXT NOT NULL,
    caption TEXT NOT NULL,
    hashtags_json TEXT NOT NULL,
    cta TEXT NOT NULL,
    disclosure TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (content_id, platform)
);

CREATE TABLE IF NOT EXISTS review_events (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content_items(id),
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posting_windows (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    platform TEXT NOT NULL,
    format TEXT NOT NULL,
    weekday INTEGER NOT NULL,
    timezone TEXT NOT NULL,
    local_time TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL,
    UNIQUE (creator_id, platform, format, weekday, local_time)
);

CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content_items(id),
    platform_variant_id INTEGER NOT NULL REFERENCES platform_variants(id),
    provider TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    published_at TEXT,
    external_id TEXT,
    external_url TEXT,
    source TEXT NOT NULL DEFAULT 'SYSTEM',
    ai_disclosure INTEGER NOT NULL DEFAULT 0,
    schedule_status TEXT NOT NULL DEFAULT 'NOT_READY',
    schedule_timezone TEXT NOT NULL DEFAULT 'Europe/Berlin',
    schedule_source TEXT NOT NULL DEFAULT 'unknown',
    external_schedule_id TEXT,
    schedule_error TEXT,
    approval_version INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    UNIQUE (content_id, provider)
);

CREATE TABLE IF NOT EXISTS publish_queue (
    id INTEGER PRIMARY KEY,
    queue_key TEXT NOT NULL UNIQUE,
    publication_id INTEGER NOT NULL REFERENCES publications(id),
    content_id INTEGER NOT NULL REFERENCES content_items(id),
    platform TEXT NOT NULL,
    planned_at TEXT NOT NULL,
    timezone TEXT NOT NULL,
    approval_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    adapter_provider TEXT NOT NULL,
    external_schedule_id TEXT,
    suggested_at TEXT,
    next_attempt_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (publication_id, approval_version)
);

CREATE INDEX IF NOT EXISTS publish_queue_due
ON publish_queue(status, planned_at);

CREATE TABLE IF NOT EXISTS background_runs (
    id INTEGER PRIMARY KEY,
    run_key TEXT NOT NULL UNIQUE,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL,
    current_step TEXT NOT NULL,
    cursor_json TEXT NOT NULL DEFAULT '{}',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_run_at TEXT,
    error_class TEXT,
    error_code TEXT,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS run_leases (
    lease_name TEXT PRIMARY KEY,
    owner_token TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_events (
    id INTEGER PRIMARY KEY,
    run_id INTEGER REFERENCES background_runs(id),
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    step TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS runtime_events_run
ON runtime_events(run_id, created_at, id);

CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id INTEGER PRIMARY KEY,
    publication_id INTEGER NOT NULL REFERENCES publications(id),
    window_hours INTEGER NOT NULL,
    captured_at TEXT NOT NULL,
    views INTEGER NOT NULL,
    retention REAL NOT NULL,
    completion REAL NOT NULL,
    likes INTEGER NOT NULL,
    comments INTEGER NOT NULL,
    shares INTEGER NOT NULL,
    saves INTEGER NOT NULL,
    profile_visits INTEGER NOT NULL,
    follows INTEGER NOT NULL,
    link_clicks INTEGER NOT NULL,
    revenue REAL NOT NULL,
    UNIQUE (publication_id, window_hours)
);

CREATE TABLE IF NOT EXISTS manual_analytics_events (
    id INTEGER PRIMARY KEY,
    publication_id INTEGER NOT NULL REFERENCES publications(id),
    window_hours INTEGER NOT NULL,
    captured_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'MANUAL_OWNER',
    reach INTEGER,
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    saves INTEGER,
    profile_visits INTEGER,
    follows INTEGER,
    link_clicks INTEGER,
    revenue REAL,
    note TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS manual_analytics_publication_window
ON manual_analytics_events(publication_id, window_hours, captured_at DESC);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content_items(id),
    variable TEXT NOT NULL,
    variant TEXT NOT NULL,
    baseline_json TEXT NOT NULL,
    decision TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_candidates (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content_items(id),
    label TEXT NOT NULL,
    reference TEXT,
    license_status TEXT NOT NULL,
    fit_score REAL NOT NULL,
    selected INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS link_campaigns (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    name TEXT NOT NULL,
    destination_ref TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0,
    UNIQUE (creator_id, name)
);

CREATE TABLE IF NOT EXISTS product_packs (
    id INTEGER PRIMARY KEY,
    pack_key TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL,
    name TEXT NOT NULL,
    summary TEXT NOT NULL,
    deliverables_json TEXT NOT NULL,
    exclusions_json TEXT NOT NULL,
    price_eur REAL,
    delivery_days INTEGER,
    revisions INTEGER,
    status TEXT NOT NULL DEFAULT 'DRAFT_OWNER_GATES',
    owner_approved INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS adworks_campaigns (
    id INTEGER PRIMARY KEY,
    campaign_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    pack_id INTEGER NOT NULL REFERENCES product_packs(id),
    creator_id INTEGER REFERENCES creators(id),
    content_id INTEGER REFERENCES content_items(id),
    publication_id INTEGER REFERENCES publications(id),
    channel TEXT NOT NULL,
    source TEXT NOT NULL,
    medium TEXT NOT NULL,
    campaign_token TEXT NOT NULL,
    content_token TEXT NOT NULL DEFAULT '',
    destination_ref TEXT NOT NULL,
    organic INTEGER NOT NULL DEFAULT 1,
    approval_status TEXT NOT NULL DEFAULT 'DRAFT',
    status TEXT NOT NULL DEFAULT 'DRY_RUN',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tracking_links (
    id INTEGER PRIMARY KEY,
    link_key TEXT NOT NULL UNIQUE,
    campaign_id INTEGER NOT NULL REFERENCES adworks_campaigns(id),
    destination_ref TEXT NOT NULL,
    query_string TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS funnel_events (
    id INTEGER PRIMARY KEY,
    event_key TEXT NOT NULL UNIQUE,
    dedupe_key TEXT NOT NULL UNIQUE,
    tracking_link_id INTEGER REFERENCES tracking_links(id),
    campaign_id INTEGER NOT NULL REFERENCES adworks_campaigns(id),
    pack_id INTEGER NOT NULL REFERENCES product_packs(id),
    content_id INTEGER REFERENCES content_items(id),
    publication_id INTEGER REFERENCES publications(id),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    attribution TEXT NOT NULL DEFAULT 'unknown',
    amount REAL,
    currency TEXT,
    is_mock INTEGER NOT NULL DEFAULT 1,
    occurred_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS product_feedback (
    id INTEGER PRIMARY KEY,
    feedback_key TEXT NOT NULL UNIQUE,
    pack_id INTEGER NOT NULL REFERENCES product_packs(id),
    campaign_id INTEGER NOT NULL REFERENCES adworks_campaigns(id),
    signal TEXT NOT NULL,
    decision TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    is_mock INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS revenue_events (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    content_id INTEGER REFERENCES content_items(id),
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    source TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cost_events (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    content_id INTEGER REFERENCES content_items(id),
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    category TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_accounts (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    platform TEXT NOT NULL,
    public_handle TEXT NOT NULL,
    secret_reference TEXT,
    status TEXT NOT NULL,
    UNIQUE (creator_id, platform)
);

CREATE TABLE IF NOT EXISTS asset_usage_plan (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content_items(id),
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    role TEXT NOT NULL,
    priority INTEGER NOT NULL,
    trigger_reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'READY',
    UNIQUE (content_id, asset_id)
);

CREATE TABLE IF NOT EXISTS adapter_attempts (
    id INTEGER PRIMARY KEY,
    content_id INTEGER REFERENCES content_items(id),
    adapter_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    fallback_provider TEXT,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engagement_queue (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id),
    publication_id INTEGER NOT NULL REFERENCES publications(id),
    platform TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    prompt TEXT NOT NULL,
    safety_note TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    priority INTEGER NOT NULL,
    not_before TEXT NOT NULL,
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    UNIQUE (publication_id, action_type, target_ref)
);

CREATE TABLE IF NOT EXISTS evening_batches (
    id INTEGER PRIMARY KEY,
    batch_key TEXT NOT NULL UNIQUE,
    run_date TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    status TEXT NOT NULL,
    results_json TEXT NOT NULL,
    reason TEXT,
    completed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS export_jobs (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    file_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    row_counts_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


SCHEMA_VERSION = 5

COLUMN_MIGRATIONS = {
    "content_items": (
        ("content_stage", "TEXT NOT NULL DEFAULT 'ALLTAG'"),
        ("visibility_scope", "TEXT NOT NULL DEFAULT 'PUBLIC_SFW'"),
    ),
    "assets": (
        ("content_stage", "TEXT NOT NULL DEFAULT 'ALLTAG'"),
        ("visibility_scope", "TEXT NOT NULL DEFAULT 'PUBLIC_SFW'"),
        ("pose_slot", "TEXT NOT NULL DEFAULT 'UNASSIGNED'"),
        ("similarity_group", "TEXT NOT NULL DEFAULT ''"),
        ("stage_fit_score", "REAL NOT NULL DEFAULT 1"),
        ("novelty_score", "REAL NOT NULL DEFAULT 0.5"),
    ),
    "publications": (
        ("source", "TEXT NOT NULL DEFAULT 'SYSTEM'"),
        ("ai_disclosure", "INTEGER NOT NULL DEFAULT 0"),
        ("schedule_status", "TEXT NOT NULL DEFAULT 'NOT_READY'"),
        ("schedule_timezone", "TEXT NOT NULL DEFAULT 'Europe/Berlin'"),
        ("schedule_source", "TEXT NOT NULL DEFAULT 'unknown'"),
        ("external_schedule_id", "TEXT"),
        ("schedule_error", "TEXT"),
        ("approval_version", "INTEGER NOT NULL DEFAULT 0"),
    ),
}

GUARD_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS content_scope_guard_insert
BEFORE INSERT ON content_items
WHEN NOT (
    (NEW.content_stage IN ('ALLTAG', 'TEASER')
        AND NEW.safety_class = 'SFW'
        AND NEW.visibility_scope IN ('PUBLIC_SFW', 'LOCAL_ONLY'))
    OR
    (NEW.content_stage = 'ADULT_18'
        AND NEW.safety_class = 'ADULT'
        AND NEW.visibility_scope = 'ADULT_ONLY')
)
BEGIN
    SELECT RAISE(ABORT, 'content_stage_safety_visibility_mismatch');
END;

CREATE TRIGGER IF NOT EXISTS content_scope_guard_update
BEFORE UPDATE OF content_stage, safety_class, visibility_scope ON content_items
WHEN NOT (
    (NEW.content_stage IN ('ALLTAG', 'TEASER')
        AND NEW.safety_class = 'SFW'
        AND NEW.visibility_scope IN ('PUBLIC_SFW', 'LOCAL_ONLY'))
    OR
    (NEW.content_stage = 'ADULT_18'
        AND NEW.safety_class = 'ADULT'
        AND NEW.visibility_scope = 'ADULT_ONLY')
)
BEGIN
    SELECT RAISE(ABORT, 'content_stage_safety_visibility_mismatch');
END;

CREATE TRIGGER IF NOT EXISTS asset_scope_guard_insert
BEFORE INSERT ON assets
WHEN NOT (
    (NEW.content_stage IN ('ALLTAG', 'TEASER')
        AND NEW.safety_class = 'SFW'
        AND NEW.visibility_scope IN ('PUBLIC_SFW', 'LOCAL_ONLY'))
    OR
    (NEW.content_stage = 'ADULT_18'
        AND NEW.safety_class = 'ADULT'
        AND NEW.visibility_scope = 'ADULT_ONLY')
)
OR EXISTS (
    SELECT 1 FROM content_items content
    WHERE content.id = NEW.content_id
      AND (
        content.content_stage != NEW.content_stage
        OR content.safety_class != NEW.safety_class
        OR content.visibility_scope != NEW.visibility_scope
      )
)
BEGIN
    SELECT RAISE(ABORT, 'asset_content_scope_mismatch');
END;

CREATE TRIGGER IF NOT EXISTS asset_scope_guard_update
BEFORE UPDATE OF content_stage, safety_class, visibility_scope, content_id ON assets
WHEN NOT (
    (NEW.content_stage IN ('ALLTAG', 'TEASER')
        AND NEW.safety_class = 'SFW'
        AND NEW.visibility_scope IN ('PUBLIC_SFW', 'LOCAL_ONLY'))
    OR
    (NEW.content_stage = 'ADULT_18'
        AND NEW.safety_class = 'ADULT'
        AND NEW.visibility_scope = 'ADULT_ONLY')
)
OR EXISTS (
    SELECT 1 FROM content_items content
    WHERE content.id = NEW.content_id
      AND (
        content.content_stage != NEW.content_stage
        OR content.safety_class != NEW.safety_class
        OR content.visibility_scope != NEW.visibility_scope
      )
)
BEGIN
    SELECT RAISE(ABORT, 'asset_content_scope_mismatch');
END;
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class CreatorDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        connection = self.connect()
        try:
            connection.executescript(SCHEMA)
            self._migrate(connection)
            connection.executescript(GUARD_TRIGGERS)
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
        return {
            str(row[1])
            for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
        }

    @classmethod
    def _migrate(cls, connection: sqlite3.Connection) -> None:
        """Apply small additive migrations without replacing an existing database."""
        for table, columns in COLUMN_MIGRATIONS.items():
            present = cls._columns(connection, table)
            for name, definition in columns:
                if name not in present:
                    connection.execute(
                        f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'
                    )

        connection.execute(
            """
            UPDATE content_items
            SET content_stage = CASE
                    WHEN adult = 1 OR safety_class = 'ADULT' THEN 'ADULT_18'
                    ELSE COALESCE(NULLIF(content_stage, ''), 'ALLTAG')
                END,
                visibility_scope = CASE
                    WHEN adult = 1 OR safety_class = 'ADULT' THEN 'ADULT_ONLY'
                    ELSE COALESCE(NULLIF(visibility_scope, ''), 'PUBLIC_SFW')
                END
            """
        )
        connection.execute(
            """
            UPDATE assets
            SET content_stage = COALESCE(
                    (SELECT content_stage FROM content_items WHERE id = assets.content_id),
                    'ALLTAG'
                ),
                visibility_scope = COALESCE(
                    (SELECT visibility_scope FROM content_items WHERE id = assets.content_id),
                    'PUBLIC_SFW'
                )
            """
        )

        pose_slots = (
            "FRONTAL",
            "LEFT_3Q",
            "RIGHT_3Q",
            "FULL_BODY_ACTION",
            "CANDID",
        )
        content_ids = connection.execute(
            "SELECT DISTINCT content_id FROM assets ORDER BY content_id"
        ).fetchall()
        for content_row in content_ids:
            assets = connection.execute(
                "SELECT id, pose_slot FROM assets WHERE content_id = ? ORDER BY id",
                (content_row[0],),
            ).fetchall()
            for index, asset in enumerate(assets):
                if not asset[1] or asset[1] == "UNASSIGNED":
                    connection.execute(
                        "UPDATE assets SET pose_slot = ? WHERE id = ?",
                        (pose_slots[index % len(pose_slots)], asset[0]),
                    )

        # A silent fallback has no external audio rights to verify. Older
        # imported briefs occasionally labelled the same null-audio option as
        # REVIEW_REQUIRED, which made the review checklist contradict itself.
        connection.execute(
            """
            UPDATE audio_candidates
            SET license_status='SAFE_NO_AUDIO', reference=NULL
            WHERE lower(trim(label)) IN ('option ohne musik','ohne musik')
              AND (reference IS NULL OR trim(reference)='')
            """
        )

        # Approved AI publications carry the explicit disclosure intent. The
        # official adapter still requires a separate owner-confirmed native
        # platform disclosure in its ignored local media manifest.
        connection.execute(
            """
            UPDATE publications
            SET ai_disclosure=1
            WHERE content_id IN (
                SELECT id FROM content_items
                WHERE approved=1 AND needs_ai_disclosure=1
            )
              AND provider='mock-draft'
              AND status!='PUBLISHED'
            """
        )

        # Keep fallback roles aligned with the already selected Top 3 without
        # changing their owner-visible order. This repairs legacy plans after a
        # published asset was excluded or a production import changed picks.
        planned_content = connection.execute(
            "SELECT DISTINCT content_id FROM asset_usage_plan ORDER BY content_id"
        ).fetchall()
        for content_row in planned_content:
            assets = connection.execute(
                """
                SELECT a.id, a.is_top_pick, a.published_status,
                       COALESCE(p.priority, 9999) AS plan_priority
                FROM assets a
                LEFT JOIN asset_usage_plan p
                  ON p.content_id=a.content_id AND p.asset_id=a.id
                WHERE a.content_id=?
                ORDER BY plan_priority, a.id
                """,
                (content_row[0],),
            ).fetchall()
            selected = [
                row
                for row in assets
                if row["is_top_pick"] and row["published_status"] != "PUBLISHED"
            ]
            reserve = [
                row
                for row in assets
                if not row["is_top_pick"] and row["published_status"] != "PUBLISHED"
            ]
            published = [row for row in assets if row["published_status"] == "PUBLISHED"]
            ordered = selected + reserve + published
            for priority, asset in enumerate(ordered, start=1):
                if asset["published_status"] == "PUBLISHED":
                    role, status = "RESERVE", "PUBLISHED_USED"
                elif asset["is_top_pick"]:
                    role, status = ("PRIMARY" if priority == 1 else "ALTERNATE"), "READY"
                else:
                    role, status = "RESERVE", "READY"
                connection.execute(
                    """
                    INSERT INTO asset_usage_plan
                        (content_id, asset_id, role, priority, trigger_reason, status)
                    VALUES (?, ?, ?, ?, 'synchronized with current Top 3', ?)
                    ON CONFLICT(content_id, asset_id) DO UPDATE SET
                        role=excluded.role,
                        priority=excluded.priority,
                        trigger_reason=excluded.trigger_reason,
                        status=excluded.status
                    """,
                    (content_row[0], asset["id"], role, priority, status),
                )

        connection.execute(
            """
            INSERT INTO schema_meta (key, value)
            VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(SCHEMA_VERSION),),
        )

    def schema_version(self) -> int:
        value = self.scalar(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        )
        return int(value or 0)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def one(self, sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        connection = self.connect()
        try:
            return connection.execute(sql, parameters).fetchone()
        finally:
            connection.close()

    def all(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        connection = self.connect()
        try:
            return list(connection.execute(sql, parameters).fetchall())
        finally:
            connection.close()

    def scalar(self, sql: str, parameters: tuple[Any, ...] = ()) -> Any:
        row = self.one(sql, parameters)
        return None if row is None else row[0]

    def seed_personas(self, config_path: str | Path) -> None:
        payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
        with self.transaction() as connection:
            for slug, persona in payload.items():
                now = utc_now()
                connection.execute(
                    """
                    INSERT INTO creators
                        (slug, display_name, instagram_handle, niche, tone, disclosure, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                        display_name=excluded.display_name,
                        instagram_handle=excluded.instagram_handle,
                        niche=excluded.niche,
                        tone=excluded.tone,
                        disclosure=excluded.disclosure
                    """,
                    (
                        slug,
                        persona["display_name"],
                        persona["instagram_handle"],
                        persona["niche"],
                        persona["tone"],
                        persona["disclosure"],
                        now,
                    ),
                )
                creator_id = connection.execute(
                    "SELECT id FROM creators WHERE slug = ?", (slug,)
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO character_versions (creator_id, version, payload_json, created_at)
                    VALUES (?, 'v1', ?, ?)
                    ON CONFLICT(creator_id, version) DO UPDATE SET payload_json=excluded.payload_json
                    """,
                    (creator_id, json.dumps(persona, ensure_ascii=False), now),
                )
                connection.execute(
                    """
                    INSERT INTO platform_accounts
                        (creator_id, platform, public_handle, secret_reference, status)
                    VALUES (?, 'instagram', ?, NULL, 'ACTIVE')
                    ON CONFLICT(creator_id, platform) DO UPDATE SET
                        public_handle=excluded.public_handle,
                        status=excluded.status
                    """,
                    (creator_id, persona["instagram_handle"]),
                )

    def table_counts(self) -> dict[str, int]:
        tables = (
            "creators",
            "series",
            "content_items",
            "assets",
            "platform_variants",
            "review_events",
            "publications",
            "analytics_snapshots",
            "experiments",
            "cost_events",
            "revenue_events",
            "audio_candidates",
            "asset_usage_plan",
            "adapter_attempts",
            "engagement_queue",
            "evening_batches",
            "export_jobs",
            "product_packs",
            "adworks_campaigns",
            "tracking_links",
            "funnel_events",
            "product_feedback",
            "publish_queue",
            "background_runs",
            "run_leases",
            "runtime_events",
        )
        return {table: int(self.scalar(f"SELECT COUNT(*) FROM {table}") or 0) for table in tables}
