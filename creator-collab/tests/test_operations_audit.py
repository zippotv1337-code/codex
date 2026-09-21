from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date, datetime
from pathlib import Path
from urllib.request import urlopen

from creator_ops.cli import build_pipeline
from creator_ops.operations_audit import OperationsAuditService
from creator_ops.publishing import PublishQueueService
from creator_ops.reconcile import ManualInstagramService
from creator_ops.review import ReviewDashboardService
from creator_ops.web import create_server


class OperationsAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.database_path = self.root / "review.db"
        self.pipeline = build_pipeline(self.database_path)
        self.pipeline.initialize()
        self.reviews = ReviewDashboardService(self.pipeline)
        self.audit = OperationsAuditService(
            self.reviews,
            PublishQueueService(self.pipeline.db),
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_due_analytics_are_reported_without_invented_metrics(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 4))
        publication = ManualInstagramService(self.pipeline.db).reconcile(
            creator_slug="leona-voss",
            content_id=result.content_id,
            external_url="https://www.instagram.com/leonavoss.ai/p/AuditDue/",
            published_at="2026-09-04T19:30:00+02:00",
        )

        payload = self.audit.snapshot(now=datetime.fromisoformat("2026-09-05T20:00:00+02:00"))

        self.assertEqual(payload["analytics"]["due_count"], 1)
        due = payload["analytics"]["due"][0]
        self.assertEqual(due["publication_id"], publication["publication_id"])
        self.assertEqual(due["due_windows_hours"], [24])
        self.assertEqual(due["metrics_status"], "UNKNOWN_UNTIL_OWNER_IMPORT")
        self.assertNotIn("reach", due)

    def test_recorded_window_is_not_reported_as_due_again(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 4))
        service = ManualInstagramService(self.pipeline.db)
        publication = service.reconcile(
            creator_slug="leona-voss",
            content_id=result.content_id,
            external_url="https://www.instagram.com/leonavoss.ai/p/AuditRecorded/",
            published_at="2026-09-04T19:30:00+02:00",
        )
        service.append_analytics(publication["publication_id"], 24, reach=120, likes=14)

        payload = self.audit.snapshot(now=datetime.fromisoformat("2026-09-05T20:00:00+02:00"))

        self.assertEqual(payload["analytics"]["due_count"], 0)
        self.assertNotIn(
            "analytics",
            [action["lane"] for action in payload.get("next_actions", [])],
        )

    def test_confirmed_meta_publish_is_reported_as_controlled_proof(self) -> None:
        card = self.reviews.ensure_date(date(2026, 9, 8))[0]
        with self.pipeline.db.transaction() as connection:
            variant = connection.execute(
                "SELECT id FROM platform_variants WHERE content_id=?",
                (card["content_id"],),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO publications
                    (content_id, platform_variant_id, provider, scheduled_at,
                     published_at, external_id, external_url, status)
                VALUES (?, ?, 'instagram-meta-graph', ?, ?, ?, ?, 'PUBLISHED')
                """,
                (
                    card["content_id"],
                    variant["id"],
                    "2026-09-08T19:30:00+02:00",
                    "2026-09-08T19:30:00+02:00",
                    "18000000000000000",
                    "https://www.instagram.com/p/AuditMetaProof/",
                ),
            )

        payload = self.audit.snapshot(
            now=datetime.fromisoformat("2026-09-08T20:00:00+02:00")
        )

        self.assertEqual(payload["publishing"]["official_meta_published_count"], 1)
        self.assertEqual(
            payload["publishing"]["live_posting"],
            "PROVEN_CONTROLLED_PACKAGE_ONLY_GLOBAL_AUTOMATION_OFF",
        )

    def test_audit_prioritizes_local_publish_and_story_ready_state(self) -> None:
        card = self.reviews.ensure_date(date(2026, 9, 8))[0]
        self.reviews.approve(card["content_id"])

        payload = self.audit.snapshot(now=datetime.fromisoformat("2026-09-07T14:30:00+02:00"))

        self.assertEqual(payload["publishing"]["local_scheduled_count"], 1)
        self.assertEqual(payload["publishing"]["due_local_scheduled_count"], 0)
        self.assertEqual(payload["publishing"]["future_local_scheduled_count"], 1)
        self.assertGreaterEqual(payload["stories"]["ready_package_count"], 1)
        lanes = [action["lane"] for action in payload["next_actions"]]
        self.assertIn("instagram_schedule", lanes)
        self.assertNotIn("instagram_output", lanes)
        self.assertIn("stories", lanes)
        scheduled = next(
            action for action in payload["next_actions"]
            if action["lane"] == "instagram_schedule"
        )
        self.assertEqual(scheduled["blocked_by"], "PLANNED_TIME_NOT_REACHED")

    def test_due_publish_with_meta_proof_requires_package_preflight_not_credentials(self) -> None:
        proof_card, due_card = self.reviews.ensure_date(date(2026, 9, 8))
        self.reviews.approve(due_card["content_id"])
        with self.pipeline.db.transaction() as connection:
            variant = connection.execute(
                "SELECT id FROM platform_variants WHERE content_id=?",
                (proof_card["content_id"],),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO publications
                    (content_id, platform_variant_id, provider, scheduled_at,
                     published_at, external_id, external_url, status)
                VALUES (?, ?, 'instagram-meta-graph', ?, ?, ?, ?, 'PUBLISHED')
                """,
                (
                    proof_card["content_id"],
                    variant["id"],
                    "2026-09-08T18:00:00+02:00",
                    "2026-09-08T18:00:00+02:00",
                    "18000000000000001",
                    "https://www.instagram.com/p/AuditMetaDue/",
                ),
            )

        payload = self.audit.snapshot(
            now=datetime.fromisoformat("2026-09-09T22:00:00+02:00")
        )

        action = next(
            item for item in payload["next_actions"]
            if item["lane"] == "instagram_output"
        )
        self.assertEqual(action["blocked_by"], "PACKAGE_BOUND_PREFLIGHT_REQUIRED")
        self.assertNotEqual(action["blocked_by"], "META_CREDENTIALS_OR_NATIVE_UPLOAD_SESSION")

    def test_http_endpoint_exposes_operations_audit(self) -> None:
        self.reviews.ensure_date(date(2026, 9, 8))
        server = create_server(self.database_path, port=0, asset_root=self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(f"{base}/api/operations-audit", timeout=5) as response:
                payload = json.load(response)
            self.assertEqual(payload["schema"], "creator-ops-operations-audit-v1")
            self.assertIn("next_actions", payload)
            self.assertIn("review", payload)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
