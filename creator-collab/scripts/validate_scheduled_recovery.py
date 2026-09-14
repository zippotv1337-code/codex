"""Restore one backup and prove scheduled publishes fail closed, locally only."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import tempfile


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from creator_ops.database import CreatorDatabase  # noqa: E402
from creator_ops.exporting import ExportBackupService  # noqa: E402
from creator_ops.publishing import (  # noqa: E402
    BLOCKED_EXTERNAL_PUBLISHING,
    LOCAL_SCHEDULED,
    PublishQueueService,
    UnconfiguredInstagramAdapter,
)


CORE_TABLES = (
    "creators",
    "content_items",
    "assets",
    "platform_variants",
    "publications",
    "publish_queue",
)


def _counts(database: CreatorDatabase) -> dict[str, int]:
    return {
        table: int(database.scalar(f'SELECT COUNT(*) FROM "{table}"') or 0)
        for table in CORE_TABLES
    }


def validate(backup: Path, canonical: Path) -> dict[str, object]:
    backup = backup.resolve()
    canonical = canonical.resolve()
    if not backup.is_file():
        raise FileNotFoundError(backup)
    if not canonical.is_file():
        raise FileNotFoundError(canonical)

    live = CreatorDatabase(canonical)
    live_counts = _counts(live)
    with tempfile.TemporaryDirectory(prefix="zippoworkz-restore-proof-") as folder:
        restored_path = Path(folder) / "restored.db"
        ExportBackupService.restore_sqlite(backup, restored_path)
        restored = CreatorDatabase(restored_path)
        restored_counts = _counts(restored)
        if restored.scalar("PRAGMA integrity_check") != "ok":
            raise RuntimeError("restored_integrity_failed")
        if restored.all("PRAGMA foreign_key_check"):
            raise RuntimeError("restored_foreign_key_check_failed")
        if restored.schema_version() != live.schema_version():
            raise RuntimeError("restored_schema_mismatch")
        if restored_counts != live_counts:
            raise RuntimeError("restored_core_counts_mismatch")

        before = PublishQueueService(
            restored, UnconfiguredInstagramAdapter()
        ).list()
        scheduled = [item for item in before if item["status"] == LOCAL_SCHEDULED]
        if not scheduled:
            raise RuntimeError("no_local_scheduled_jobs")
        planned = [datetime.fromisoformat(str(item["planned_at"])) for item in scheduled]
        if max(planned) - min(planned) > timedelta(minutes=10):
            raise RuntimeError("scheduled_jobs_not_in_one_safe_test_window")

        service = PublishQueueService(restored, UnconfiguredInstagramAdapter())
        first = service.dispatch_due(max(planned) + timedelta(minutes=1))
        second = service.dispatch_due(max(planned) + timedelta(minutes=2))
        reconciliation = service.reconcile(max(planned) + timedelta(minutes=3))
        after = service.list()
        publications = restored.all(
            """
            SELECT id, status, schedule_status, external_id, external_url,
                   published_at FROM publications ORDER BY id
            """
        )

        original_keys = {str(item["queue_key"]) for item in before}
        final_keys = {str(item["queue_key"]) for item in after}
        all_blocked = all(
            item["status"] == BLOCKED_EXTERNAL_PUBLISHING for item in after
        )
        no_receipts = all(
            row["external_id"] is None
            and row["external_url"] is None
            and row["published_at"] is None
            and row["status"] != "PUBLISHED"
            for row in publications
        )
        duplicate_safe = (
            len(after) == len(before)
            and original_keys == final_keys
            and second["due"] == 0
        )
        if first["blocked"] != len(scheduled) or not all_blocked:
            raise RuntimeError("unconfigured_publish_did_not_fail_closed")
        if not no_receipts:
            raise RuntimeError("fake_publish_receipt_detected")
        if not duplicate_safe:
            raise RuntimeError("queue_idempotency_failed")

        return {
            "schema": "zippoworkz-scheduled-recovery-proof-v1",
            "backup": str(backup),
            "canonical": str(canonical),
            "schema_version": restored.schema_version(),
            "integrity": "ok",
            "foreign_key_violations": 0,
            "core_counts_match": True,
            "core_counts": restored_counts,
            "scheduled_jobs_tested": len(scheduled),
            "first_dispatch": first,
            "second_dispatch": second,
            "reconciliation": reconciliation,
            "final_queue_status": BLOCKED_EXTERNAL_PUBLISHING,
            "queue_keys_preserved": original_keys == final_keys,
            "duplicate_safe": duplicate_safe,
            "fake_receipts": False,
            "canonical_database_mutated": False,
            "external_actions": "NONE",
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a ZippoWorkz backup and fail-closed publish queue on a temporary restore."
    )
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument(
        "--canonical",
        type=Path,
        default=PROJECT / "data" / "review_dashboard.db",
    )
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments.backup, arguments.canonical), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
