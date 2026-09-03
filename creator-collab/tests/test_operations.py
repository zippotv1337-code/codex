from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from creator_ops.database import CreatorDatabase
from creator_ops.evening import EveningRunCoordinator
from creator_ops.exporting import ExportBackupService
from creator_ops.pipeline import VerticalPipeline
from creator_ops.services import AudioService


ROOT = Path(__file__).resolve().parents[1]


class OperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.database_path = self.root / "creator_ops.db"
        self.database = CreatorDatabase(self.database_path)
        self.pipeline = VerticalPipeline(
            self.database,
            ROOT / "config" / "personas.json",
            ROOT / "config" / "prime_time.json",
        )
        self.pipeline.initialize()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_evening_run_enforces_berlin_window(self) -> None:
        result = EveningRunCoordinator(self.pipeline).run(datetime(2026, 9, 3, 18, 59))
        self.assertEqual(result.status, "SKIPPED_OUTSIDE_WINDOW")
        self.assertEqual(result.results, ())
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM content_items"), 0)
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM evening_batches"), 0)

    def test_evening_run_processes_both_and_is_idempotent(self) -> None:
        coordinator = EveningRunCoordinator(self.pipeline)
        first = coordinator.run(datetime(2026, 9, 3, 20, 0))
        second = coordinator.run(datetime(2026, 9, 3, 21, 0))
        self.assertEqual(first.status, "COMPLETE")
        self.assertEqual(len(first.results), 2)
        self.assertTrue(all(item.reused for item in second.results))
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM evening_batches"), 1)
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM content_items"), 2)

    def test_prime_time_switches_from_cold_start_to_history(self) -> None:
        self.pipeline.run("leona-voss", date(2026, 9, 3))
        self.pipeline.run("leona-voss", date(2026, 9, 4))
        windows = self.database.all(
            "SELECT source, local_time FROM posting_windows ORDER BY id"
        )
        self.assertEqual(windows[0]["source"], "cold-start-config")
        self.assertEqual(windows[1]["source"], "analytics-history")
        self.assertEqual(windows[1]["local_time"], "19:30")

    def test_prime_time_avoids_an_occupied_creator_slot(self) -> None:
        self.pipeline.run("leona-voss", date(2026, 9, 11))
        creator_id = self.database.scalar("SELECT id FROM creators WHERE slug = 'leona-voss'")
        with self.database.transaction() as connection:
            decision = self.pipeline.scheduler.choose(
                connection,
                creator_id,
                date(2026, 9, 11),
                "instagram",
                "carousel",
            )
        self.assertEqual(decision.local_time, "20:30")

    def test_asset_plan_has_primary_alternates_and_reserves(self) -> None:
        result = self.pipeline.run("mara-field", date(2026, 9, 6))
        roles = {
            row["role"]: row["amount"]
            for row in self.database.all(
                """
                SELECT role, COUNT(*) AS amount FROM asset_usage_plan
                WHERE content_id = ? GROUP BY role
                """,
                (result.content_id,),
            )
        }
        self.assertEqual(roles, {"PRIMARY": 1, "ALTERNATE": 2, "RESERVE": 2})

    def test_audio_uses_safe_fallback_when_adapter_fails(self) -> None:
        class BrokenAudioCatalog:
            provider = "broken-audio"

            def search(self, creator_slug: str, series_name: str) -> list[dict]:
                raise RuntimeError("catalog unavailable")

        self.pipeline.audio_service = AudioService(BrokenAudioCatalog())
        result = self.pipeline.run("leona-voss", date(2026, 9, 7))
        selected = self.database.one(
            """
            SELECT label, license_status FROM audio_candidates
            WHERE content_id = ? AND selected = 1
            """,
            (result.content_id,),
        )
        attempt = self.database.one(
            "SELECT status, fallback_provider FROM adapter_attempts WHERE adapter_type = 'audio'"
        )
        self.assertEqual(selected["license_status"], "SAFE_NO_AUDIO")
        self.assertEqual(attempt["status"], "FALLBACK")
        self.assertEqual(attempt["fallback_provider"], "safe-no-audio")

    def test_owned_audio_can_be_selected(self) -> None:
        class OwnedAudioCatalog:
            provider = "owned-library"

            def search(self, creator_slug: str, series_name: str) -> list[dict]:
                return [
                    {
                        "label": "Owned loop",
                        "reference": "owned://loop-1",
                        "license_status": "OWNED",
                        "fit_score": 0.95,
                    }
                ]

        self.pipeline.audio_service = AudioService(OwnedAudioCatalog())
        result = self.pipeline.run("mara-field", date(2026, 9, 8))
        selected = self.database.one(
            "SELECT label, license_status FROM audio_candidates WHERE content_id = ? AND selected = 1",
            (result.content_id,),
        )
        self.assertEqual(dict(selected), {"label": "Owned loop", "license_status": "OWNED"})

    def test_engagement_queue_is_proposal_only(self) -> None:
        self.pipeline.run_both(date(2026, 9, 9))
        with self.database.transaction() as connection:
            proposed = self.pipeline.engagement.list(connection)
            self.assertEqual(len(proposed), 4)
            self.pipeline.engagement.approve_for_manual_action(connection, proposed[0]["id"])
        self.assertEqual(
            self.database.scalar("SELECT COUNT(*) FROM engagement_queue WHERE status = 'APPROVED_MANUAL'"),
            1,
        )
        self.assertEqual(
            self.database.scalar("SELECT COUNT(*) FROM engagement_queue WHERE status = 'EXECUTED'"),
            0,
        )

    def test_mock_adapter_usage_is_audited(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 12))
        attempts = {
            row["adapter_type"]: row["status"]
            for row in self.database.all(
                "SELECT adapter_type, status FROM adapter_attempts WHERE content_id = ?",
                (result.content_id,),
            )
        }
        self.assertEqual(
            attempts,
            {"audio": "SUCCESS", "publisher": "SUCCESS", "analytics": "SUCCESS"},
        )

    def test_json_export_is_secret_free_and_backup_is_valid(self) -> None:
        self.pipeline.run_both(date(2026, 9, 10))
        marker = "must-not-leave-database"
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE platform_accounts SET secret_reference = ? WHERE id = 1",
                (marker,),
            )
        service = ExportBackupService(self.database)
        export_path = service.export_json(self.root / "exports", "test")
        backup_path = service.backup_sqlite(self.root / "exports", "test")
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["contains_secrets"])
        self.assertNotIn(marker, export_path.read_text(encoding="utf-8"))
        self.assertNotIn("secret_reference", payload["tables"]["platform_accounts"][0])
        check = sqlite3.connect(backup_path)
        try:
            self.assertEqual(check.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(check.execute("SELECT COUNT(*) FROM content_items").fetchone()[0], 2)
        finally:
            check.close()
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM export_jobs"), 2)

    def test_sqlite_backup_restores_into_fresh_database(self) -> None:
        self.pipeline.run_both(date(2026, 9, 13))
        service = ExportBackupService(self.database)
        backup_path = service.backup_sqlite(self.root / "backups", "restore-test")
        restored_path = self.root / "restored" / "creator_ops.db"
        service.restore_sqlite(backup_path, restored_path)
        restored = CreatorDatabase(restored_path)
        self.assertEqual(restored.scalar("PRAGMA integrity_check"), "ok")
        self.assertEqual(restored.scalar("SELECT COUNT(*) FROM creators"), 2)
        self.assertEqual(restored.scalar("SELECT COUNT(*) FROM content_items"), 2)
        self.assertEqual(restored.scalar("SELECT COUNT(*) FROM assets"), 10)
        with self.assertRaises(FileExistsError):
            service.restore_sqlite(backup_path, restored_path)


if __name__ == "__main__":
    unittest.main()
