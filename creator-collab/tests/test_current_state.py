from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.current_state import CurrentStateService
from creator_ops.review import ReviewDashboardService


class CurrentStateTests(unittest.TestCase):
    def test_snapshot_is_dynamic_and_secret_free_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            database = root / "state.db"
            pipeline = build_pipeline(database)
            pipeline.initialize()
            ReviewDashboardService(pipeline).ensure_date(date(2026, 9, 9))
            runtime = root / "data"
            runtime.mkdir()
            (root / "VERSION").write_text("1.6.4-beta\n", encoding="utf-8")
            (runtime / "REMOTE_ACCESS_CURRENT.txt").write_text(
                "https://temporary-demo.trycloudflare.com\n", encoding="utf-8"
            )

            service = CurrentStateService(pipeline.db, root)
            snapshot = service.snapshot(tests_passed=36, tests_failed=0)
            output = service.write(root / "CURRENT_STATE.json", snapshot)
            stored = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(stored["content"]["total"], 2)
            self.assertEqual(stored["content"]["by_stage"], {"ALLTAG": 2})
            self.assertEqual(stored["assets"]["total"], 10)
            self.assertEqual(stored["tests"]["status"], "passed")
            self.assertEqual(stored["app_version"], "1.6.4-beta")
            self.assertEqual(stored["git"]["state"], "MANAGED_OUTSIDE_RUNTIME")
            self.assertNotIn("live_publishing", stored["owner_decisions"]["red_gates"])
            self.assertEqual(
                stored["owner_decisions"]["pre_approved_actions"]
                ["instagram_official_live_publish"],
                "PRE_APPROVED_WITH_SAFETY_GATES",
            )
            self.assertEqual(
                stored["owner_decisions"]["pre_approved_actions"]
                ["fiverr_public_gig_publish"],
                "PRE_APPROVED_AFTER_IDENTITY_GATE",
            )
            self.assertIn(
                "personal_identity_or_verification",
                stored["owner_decisions"]["owner_only_gates"],
            )
            self.assertFalse(
                stored["publications"]["instagram_channel_real_live"]
            )
            self.assertEqual(
                stored["publications"]["meta_graph_automation_proof"],
                "not_yet_proven",
            )
            self.assertIn("official adapter available", stored["publishing_mode"])
            self.assertIn("pre-approved with safety gates", stored["publishing_mode"])
            self.assertNotIn("adapter unavailable", stored["publishing_mode"])
            self.assertTrue(stored["remote"]["active"])
            self.assertNotIn("url", stored["remote"])

            local_snapshot = service.snapshot(include_remote_url=True)
            self.assertEqual(
                local_snapshot["remote"]["url"],
                "https://temporary-demo.trycloudflare.com",
            )


if __name__ == "__main__":
    unittest.main()
