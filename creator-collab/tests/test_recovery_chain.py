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
