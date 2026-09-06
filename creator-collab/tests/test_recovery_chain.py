from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from creator_ops.database import CreatorDatabase
from creator_ops.exporting import ExportBackupService
from creator_ops.recovery import RecoveryBackupService


class RecoveryChainTests(unittest.TestCase):
    def test_weekly_backup_preserves_publish_intent_and_confirmed_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            database = CreatorDatabase(root / "data" / "active.db")
            database.initialize()
            receipts = root / "data" / "meta-receipts"
            receipts.mkdir(parents=True)
            intent_key = "a" * 64
            confirmed_key = "b" * 64
            (receipts / f"{intent_key}.json").write_text(
                json.dumps(
                    {
                        "schema": "creator-ops-meta-receipt-v1",
                        "status": "PUBLISH_INTENT",
                        "idempotency_key": intent_key,
                        "creation_id": "container-1",
                        "creator_slug": "leona-voss",
                        "ig_user_id": "17841400000000001",
                        "created_at": "2026-09-06T00:00:00+00:00",
                    }
                ),
                encoding="utf-8",
            )
            (receipts / f"{confirmed_key}.json").write_text(
                json.dumps(
                    {
                        "schema": "creator-ops-meta-receipt-v1",
                        "status": "CONFIRMED",
                        "idempotency_key": confirmed_key,
                        "external_id": "18000000000000123",
                        "external_url": "https://www.instagram.com/p/Confirmed123/",
                        "confirmed_at": "2026-09-06T00:01:00+00:00",
                    }
                ),
                encoding="utf-8",
            )

            backup = RecoveryBackupService(database, root).build(
                root / "backups", kind="weekly"
            )

            with zipfile.ZipFile(backup) as archive:
                names = set(archive.namelist())
                self.assertIn(f"data/meta-receipts/{intent_key}.json", names)
                self.assertIn(f"data/meta-receipts/{confirmed_key}.json", names)

    def test_patch_links_base_contains_safe_db_and_validates_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "docs").mkdir()
            (root / "docs" / "delta.md").write_text("safe delta\n", encoding="utf-8")
            database = CreatorDatabase(root / "data" / "active.db")
            database.initialize()
            base = ExportBackupService(database).backup_sqlite(root / "backups", "base")
            service = RecoveryBackupService(database, root)
            patch = service.build_patch(
                root / "backups",
                changed_files=["docs/delta.md"],
                base_backup=base,
                reason="targeted documentation and runtime delta",
                label="v14-test",
            )
            validated = service.validate(patch)
            self.assertEqual(validated["path"], str(patch))
            with zipfile.ZipFile(patch) as archive:
                manifest = json.loads(archive.read("MANIFEST.json"))
                self.assertEqual(manifest["kind"], "patch")
                self.assertEqual(manifest["base_backup"], base.name)
                self.assertEqual(manifest["restore_order"], [base.name, patch.name])
                self.assertIn("docs/delta.md", archive.namelist())
                self.assertIn("recovery/creator_ops.db", archive.namelist())

    def test_patch_rejects_members_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            database = CreatorDatabase(root / "data" / "active.db")
            database.initialize()
            base = ExportBackupService(database).backup_sqlite(root / "backups", "base")
            outside = root.parent / "outside-secret.txt"
            outside.write_text("not included", encoding="utf-8")
            try:
                with self.assertRaisesRegex(ValueError, "outside_project"):
                    RecoveryBackupService(database, root).build_patch(
                        root / "backups",
                        changed_files=[str(outside)],
                        base_backup=base,
                        reason="test",
                        label="bad",
                    )
            finally:
                outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
