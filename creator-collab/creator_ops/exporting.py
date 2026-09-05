from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from .database import CreatorDatabase, utc_now


EXPORT_TABLES = (
    "creators",
    "character_versions",
    "series",
    "runs",
    "content_items",
    "content_status_events",
    "assets",
    "asset_usage_plan",
    "platform_variants",
    "review_events",
    "posting_windows",
    "publications",
    "analytics_snapshots",
    "manual_analytics_events",
    "experiments",
    "audio_candidates",
    "adapter_attempts",
    "engagement_queue",
    "evening_batches",
    "link_campaigns",
    "revenue_events",
    "cost_events",
    "product_packs",
    "adworks_campaigns",
    "tracking_links",
    "funnel_events",
    "product_feedback",
    "publish_queue",
    "background_runs",
    "runtime_events",
)


class ExportBackupService:
    def __init__(self, database: CreatorDatabase):
        self.database = database

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _snapshot(self) -> tuple[dict[str, list[dict]], dict[str, int]]:
        connection = self.database.connect()
        try:
            tables = {
                table: [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]
                for table in EXPORT_TABLES
            }
            public_accounts = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT creator_id, platform, public_handle, status
                    FROM platform_accounts
                    """
                )
            ]
            tables["platform_accounts"] = public_accounts
            return tables, {name: len(rows) for name, rows in tables.items()}
        finally:
            connection.close()

    def _public_snapshot(self) -> tuple[dict[str, list[dict]], dict[str, int]]:
        """Export only SFW/public data; adult and local-only rows stay local."""
        connection = self.database.connect()
        try:
            def rows(sql: str) -> list[dict]:
                return [dict(row) for row in connection.execute(sql)]

            public_content = """
                SELECT id FROM content_items
                WHERE safety_class = 'SFW' AND visibility_scope = 'PUBLIC_SFW'
            """
            public_assets = f"SELECT id FROM assets WHERE content_id IN ({public_content})"
            public_publications = f"SELECT id FROM publications WHERE content_id IN ({public_content})"
            tables: dict[str, list[dict]] = {
                "creators": rows("SELECT * FROM creators"),
                "character_versions": rows("SELECT * FROM character_versions"),
                "series": rows("SELECT * FROM series"),
                "runs": rows(f"SELECT * FROM runs WHERE id IN (SELECT run_id FROM content_items WHERE id IN ({public_content}))"),
                "content_items": rows(f"SELECT * FROM content_items WHERE id IN ({public_content})"),
                "content_status_events": rows(f"SELECT * FROM content_status_events WHERE content_id IN ({public_content})"),
                "assets": rows(f"SELECT * FROM assets WHERE id IN ({public_assets})"),
                "asset_usage_plan": rows(f"SELECT * FROM asset_usage_plan WHERE content_id IN ({public_content}) AND asset_id IN ({public_assets})"),
                "platform_variants": rows(f"SELECT * FROM platform_variants WHERE content_id IN ({public_content})"),
                "review_events": rows(f"SELECT * FROM review_events WHERE content_id IN ({public_content})"),
                "posting_windows": rows("SELECT * FROM posting_windows"),
                "publications": rows(f"SELECT * FROM publications WHERE id IN ({public_publications})"),
                "analytics_snapshots": rows(f"SELECT * FROM analytics_snapshots WHERE publication_id IN ({public_publications})"),
                "manual_analytics_events": rows(f"SELECT * FROM manual_analytics_events WHERE publication_id IN ({public_publications})"),
                "experiments": rows(f"SELECT * FROM experiments WHERE content_id IN ({public_content})"),
                "audio_candidates": rows(f"SELECT * FROM audio_candidates WHERE content_id IN ({public_content})"),
                "adapter_attempts": rows(f"SELECT * FROM adapter_attempts WHERE content_id IS NULL OR content_id IN ({public_content})"),
                "engagement_queue": rows(f"SELECT * FROM engagement_queue WHERE publication_id IN ({public_publications})"),
                # Batch result JSON can contain non-public content identifiers.
                "evening_batches": [],
                "link_campaigns": rows("SELECT * FROM link_campaigns"),
                "revenue_events": rows(f"SELECT * FROM revenue_events WHERE content_id IS NULL OR content_id IN ({public_content})"),
                "cost_events": rows(f"SELECT * FROM cost_events WHERE content_id IS NULL OR content_id IN ({public_content})"),
                "product_packs": rows("SELECT * FROM product_packs"),
                "adworks_campaigns": rows(f"SELECT * FROM adworks_campaigns WHERE content_id IS NULL OR content_id IN ({public_content})"),
                "tracking_links": rows("SELECT * FROM tracking_links WHERE campaign_id IN (SELECT id FROM adworks_campaigns WHERE content_id IS NULL OR content_id IN (SELECT id FROM content_items WHERE safety_class='SFW' AND visibility_scope='PUBLIC_SFW'))"),
                "funnel_events": rows(f"SELECT id, event_key, tracking_link_id, campaign_id, pack_id, content_id, publication_id, event_type, source, attribution, amount, currency, is_mock, occurred_at FROM funnel_events WHERE content_id IS NULL OR content_id IN ({public_content})"),
                "product_feedback": rows("SELECT id, feedback_key, pack_id, campaign_id, signal, decision, is_mock, created_at FROM product_feedback"),
                "publish_queue": rows(f"SELECT * FROM publish_queue WHERE content_id IN ({public_content})"),
                # Operational cursors and structured runtime details stay local.
                "background_runs": [],
                "runtime_events": [],
            }
            tables["platform_accounts"] = rows(
                "SELECT creator_id, platform, public_handle, status FROM platform_accounts"
            )
            return tables, {name: len(items) for name, items in tables.items()}
        finally:
            connection.close()

    def _record(self, kind: str, path: Path, checksum: str, counts: dict[str, int]) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO export_jobs
                    (kind, file_path, sha256, row_counts_json, status, created_at)
                VALUES (?, ?, ?, ?, 'COMPLETE', ?)
                """,
                (kind, str(path), checksum, json.dumps(counts, sort_keys=True), utc_now()),
            )

    def export_json(self, destination: str | Path, label: str | None = None) -> Path:
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        stamp = label or datetime.now().strftime("%Y%m%d-%H%M%S")
        target = destination / f"creator-ops-export-{stamp}.json"
        tables, counts = self._public_snapshot()
        payload = {
            "schema": "creator-ops-export-v4",
            "scope": "PUBLIC_SFW",
            "created_at": utc_now(),
            "contains_secrets": False,
            "row_counts": counts,
            "tables": tables,
        }
        handle, temporary_name = tempfile.mkstemp(prefix="creator-export-", suffix=".tmp", dir=destination)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as output:
                json.dump(payload, output, ensure_ascii=False, indent=2)
                output.write("\n")
            os.replace(temporary_name, target)
        except Exception:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
            raise
        checksum = self._sha256(target)
        self._record("JSON_EXPORT", target, checksum, counts)
        return target

    def backup_sqlite(self, destination: str | Path, label: str | None = None) -> Path:
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        stamp = label or datetime.now().strftime("%Y%m%d-%H%M%S")
        target = destination / f"creator-ops-backup-{stamp}.db"
        handle, temporary_name = tempfile.mkstemp(prefix="creator-backup-", suffix=".tmp", dir=destination)
        os.close(handle)
        source = self.database.connect()
        backup = sqlite3.connect(temporary_name)
        try:
            source.backup(backup)
            backup.commit()
        finally:
            backup.close()
            source.close()
        os.replace(temporary_name, target)
        check = sqlite3.connect(target)
        try:
            integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            check.close()
        if integrity != "ok":
            target.unlink(missing_ok=True)
            raise RuntimeError(f"backup_integrity_failed: {integrity}")
        _, counts = self._snapshot()
        checksum = self._sha256(target)
        self._record("SQLITE_BACKUP", target, checksum, counts)
        return target

    @classmethod
    def restore_sqlite(cls, backup_path: str | Path, destination: str | Path) -> Path:
        """Restore a verified backup into a fresh SQLite database atomically."""
        backup_path = Path(backup_path).resolve()
        destination = Path(destination).resolve()
        if not backup_path.is_file():
            raise FileNotFoundError(backup_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"restore_destination_exists: {destination}")

        source = sqlite3.connect(backup_path)
        try:
            integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"backup_integrity_failed: {integrity}")
            handle, temporary_name = tempfile.mkstemp(
                prefix="creator-restore-", suffix=".tmp", dir=destination.parent
            )
            os.close(handle)
            restored = sqlite3.connect(temporary_name)
            try:
                source.backup(restored)
                restored.commit()
                restored_integrity = restored.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                restored.close()
        finally:
            source.close()

        if restored_integrity != "ok":
            Path(temporary_name).unlink(missing_ok=True)
            raise RuntimeError(f"restored_integrity_failed: {restored_integrity}")
        os.replace(temporary_name, destination)
        return destination
