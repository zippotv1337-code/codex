from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.current_state import CurrentStateService
from creator_ops.database import utc_now
from creator_ops.review import ReviewDashboardService


class CurrentStateTests(unittest.TestCase):
    def test_snapshot_is_dynamic_and_secret_free_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir)
            root = project_root / "creator-collab"
            root.mkdir()
            policy = project_root / "ZIPPOWORKZ_OWNER_POLICY.md"
            policy.write_text(
                "# ZIPPOWORKZ_OWNER_POLICY\n\nVersion: 1.2\n",
                encoding="utf-8",
            )
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
            self.assertEqual(
                stored["state_contract"]["role"],
                "DERIVED_SECRET_FREE_SNAPSHOT",
            )
            self.assertEqual(
                stored["state_contract"]["authoritative_operational_store"],
                "data/review_dashboard.db",
            )
            policy_source = stored["state_contract"]["sources"]["owner_policy"]
            self.assertTrue(policy_source["loaded"])
            self.assertEqual(policy_source["version"], "1.2")
            self.assertRegex(policy_source["sha256"], r"^[0-9a-f]{64}$")
            self.assertFalse(stored["owner_decisions"]["authoritative"])
            self.assertEqual(
                stored["owner_decisions"]["source"],
                "ZIPPOWORKZ_OWNER_POLICY.md v1.2",
            )
            self.assertEqual(stored["node_authority"]["machine_id"], "UNKNOWN")
            self.assertFalse(stored["node_authority"]["is_active_node"])
            self.assertEqual(
                stored["owner_decisions"]["source_sha256"],
                policy_source["sha256"],
            )
            self.assertNotIn("live_publishing", stored["owner_decisions"]["red_gates"])
            self.assertEqual(
                stored["owner_decisions"]["pre_approved_actions"]
                ["instagram_official_live_publish"],
                "PRE_APPROVED_WITH_SAFETY_GATES",
            )
            self.assertEqual(
                stored["owner_decisions"]["pre_approved_actions"]
                ["fiverr_existing_gig_optimization"],
                "PRE_APPROVED_REVERSIBLE",
            )
            self.assertIn(
                "kyc_otp_or_personal_verification",
                stored["owner_decisions"]["owner_only_gates"],
            )
            self.assertFalse(
                stored["publications"]["instagram_channel_real_live"]
            )
            self.assertEqual(
                stored["publications"]["meta_graph_automation_proof"],
                "not_yet_proven",
            )
            self.assertEqual(stored["publications"]["official_meta_graph"], 0)
            self.assertIn("DO_LOG_VERIFY", stored["publishing_mode"])
            self.assertIn("official configured adapters", stored["publishing_mode"])
            self.assertNotIn("adapter unavailable", stored["publishing_mode"])
            self.assertTrue(stored["remote"]["active"])
            self.assertNotIn("url", stored["remote"])

            local_snapshot = service.snapshot(include_remote_url=True)
            self.assertEqual(
                local_snapshot["remote"]["url"],
                "https://temporary-demo.trycloudflare.com",
            )

    def test_confirmed_meta_publication_proves_live_channel(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            pipeline = build_pipeline(root / "state.db")
            pipeline.initialize()
            ReviewDashboardService(pipeline).ensure_date(date(2026, 9, 9))
            with pipeline.db.transaction() as connection:
                content = connection.execute(
                    "SELECT id FROM content_items ORDER BY id LIMIT 1"
                ).fetchone()
                variant = connection.execute(
                    "SELECT id FROM platform_variants WHERE content_id=?",
                    (content["id"],),
                ).fetchone()
                connection.execute(
                    """
                    INSERT INTO publications
                        (content_id, platform_variant_id, provider, scheduled_at,
                         published_at, external_id, external_url, status)
                    VALUES (?, ?, 'instagram-meta-graph', ?, ?, ?, ?, 'PUBLISHED')
                    """,
                    (
                        content["id"],
                        variant["id"],
                        utc_now(),
                        utc_now(),
                        "18000000000000000",
                        "https://www.instagram.com/p/ConfirmedMetaProof/",
                    ),
                )

            snapshot = CurrentStateService(pipeline.db, root).snapshot()

            self.assertTrue(snapshot["publications"]["instagram_channel_real_live"])
            self.assertEqual(snapshot["publications"]["official_meta_graph"], 1)
            self.assertEqual(
                snapshot["publications"]["meta_graph_automation_proof"],
                "proven_live",
            )


if __name__ == "__main__":
    unittest.main()
