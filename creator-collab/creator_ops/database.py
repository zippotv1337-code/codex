from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

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
    status TEXT NOT NULL,
    UNIQUE (content_id, provider)
);

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
            connection.commit()
        finally:
            connection.close()

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
        )
        return {table: int(self.scalar(f"SELECT COUNT(*) FROM {table}") or 0) for table in tables}
