from __future__ import annotations

import json
import tempfile
import tomllib
import unittest
from datetime import date
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.offline import OfflineSnapshotService
from creator_ops.review import ReviewDashboardService


class StandaloneRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.database = self.root / "runtime.db"
        self.pipeline = build_pipeline(self.database)
        self.pipeline.initialize()
        self.review = ReviewDashboardService(self.pipeline)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_offline_snapshot_is_static_read_only_and_redacted(self) -> None:
        cards = self.review.ensure_date(date(2026, 9, 8))
        self.review.approve(cards[0]["content_id"])
        (self.root / "AUTOPILOT_CHECKPOINT.md").write_text(
            "Passwort: qwertz\nKontakt: owner@example.com\n",
            encoding="utf-8",
        )

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            result = OfflineSnapshotService(self.pipeline.db, self.root).build(destination)
            payload = json.loads((destination / "snapshot.json").read_text(encoding="utf-8"))
            page = (destination / "index.html").read_text(encoding="utf-8")

        self.assertTrue(result["read_only"])
        self.assertEqual(result["queue_jobs"], 1)
        self.assertEqual(payload["schema"], "creator-ops-offline-v1")
        self.assertNotIn("qwertz", json.dumps(payload))
        self.assertNotIn("owner@example.com", json.dumps(payload))
        self.assertIn("[REDACTED]", json.dumps(payload))
        self.assertNotIn("<form", page.lower())
        self.assertIn("Nur Lesen", page)

    def test_runtime_task_scripts_are_bounded_and_owner_gated(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        installer = (project_root / "scripts" / "install_runtime_tasks.ps1").read_text(
            encoding="utf-8"
        )
        scheduler = (project_root / "scripts" / "creator_ops_scheduler.ps1").read_text(
            encoding="utf-8"
        )
        watchdog = (project_root / "scripts" / "creator_ops_watchdog.ps1").read_text(
            encoding="utf-8"
        )
        supervisor = (project_root / "scripts" / "creator_ops_supervisor.ps1").read_text(
            encoding="utf-8"
        )
        standalone = (project_root / "START_STANDALONE_CREATOR_OPS.ps1").read_text(
            encoding="utf-8"
        )
        config = (project_root / "config.toml").read_text(encoding="utf-8")
        helper = (project_root / "scripts" / "runtime_config.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("[switch]$Apply", installer)
        self.assertIn("if (-not $Apply)", installer)
        self.assertIn("MultipleInstances IgnoreNew", installer)
        self.assertIn("publish-dispatch-due", scheduler)
        self.assertNotIn("while ($true)", scheduler.lower())
        self.assertIn("runtimeConfig.MaximumRestarts", watchdog)
        self.assertIn("restart circuit open", watchdog)
        self.assertIn("port = 4180", config)
        self.assertIn("dispatch_live = false", config)
        self.assertIn("live_enabled = false", config)
        self.assertIn("Read-CreatorOpsToml", helper)
        self.assertIn("live dispatch skipped by config.toml owner gate", scheduler)
        self.assertIn("Local\\CreatorOpsStandaloneSupervisor", supervisor)
        self.assertIn("Invoke-BoundedChild", supervisor)
        self.assertIn("while ($true)", supervisor.lower())
        self.assertIn("START_CREATOR_OPS.ps1", standalone)
        self.assertIn("GetFolderPath('Startup')", installer)
        self.assertIn("CreatorOpsStandalone.cmd", installer)

        parsed = tomllib.loads(config)
        self.assertEqual(parsed["runtime"]["port"], 4180)
        self.assertEqual(parsed["runtime"]["database"], "data/review_dashboard.db")
        self.assertFalse(parsed["scheduler"]["dispatch_live"])
        self.assertFalse(parsed["publishing"]["live_enabled"])
        self.assertTrue(parsed["capabilities"]["standalone_runtime"])


if __name__ == "__main__":
    unittest.main()
