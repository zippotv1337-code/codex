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
    "experiments",
    "audio_candidates",
    "adapter_attempts",
    "engagement_queue",
    "evening_batches",
    "link_campaigns",
    "revenue_events",
    "cost_events",
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
        tables, counts = self._snapshot()
        payload = {
            "schema": "creator-ops-export-v1",
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
