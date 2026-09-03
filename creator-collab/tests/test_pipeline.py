from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from creator_ops.database import CreatorDatabase
from creator_ops.models import ComplianceInput, ContentStatus, SafetyClass
from creator_ops.pipeline import MockPublisher, VerticalPipeline, check_compliance


ROOT = Path(__file__).resolve().parents[1]


class VerticalPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tempdir.name) / "creator_ops.db"
        self.database = CreatorDatabase(self.database_path)
        self.pipeline = VerticalPipeline(
            self.database,
            ROOT / "config" / "personas.json",
            ROOT / "config" / "prime_time.json",
        )
        self.pipeline.initialize()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_vertical_flow_for_both_personas(self) -> None:
        results = self.pipeline.run_both(date(2026, 9, 3))
        self.assertEqual([result.creator_slug for result in results], ["leona-voss", "mara-field"])
        self.assertTrue(all(result.final_status is ContentStatus.ANALYZED for result in results))
        self.assertTrue(all(result.mock_url.startswith("mock://publication/") for result in results))
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM content_items"), 2)
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM assets"), 10)
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM assets WHERE is_top_pick = 1"), 6)
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM publications"), 2)
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM analytics_snapshots"), 6)
        self.assertEqual(
            [row[0] for row in self.database.all("SELECT DISTINCT window_hours FROM analytics_snapshots ORDER BY window_hours")],
            [24, 72, 168],
        )

    def test_evening_run_is_idempotent(self) -> None:
        first = self.pipeline.run_both(date(2026, 9, 3))
        second = self.pipeline.run_both(date(2026, 9, 3))
        self.assertTrue(all(result.reused for result in second))
        self.assertEqual([result.content_id for result in first], [result.content_id for result in second])
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM content_items"), 2)
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM assets"), 10)

    def test_status_history_has_complete_happy_path(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 4))
        statuses = [
            row[0]
            for row in self.database.all(
                "SELECT new_status FROM content_status_events WHERE content_id = ? ORDER BY id",
                (result.content_id,),
            )
        ]
        self.assertEqual(
            statuses,
            [
                "PLANNED",
                "GENERATING",
                "CURATING",
                "READY_FOR_REVIEW",
                "OWNER_APPROVED",
                "SCHEDULED",
                "PUBLISHED",
                "ANALYZED",
            ],
        )

    def test_compliance_rejects_adult_instagram_content(self) -> None:
        result = check_compliance(
            ComplianceInput(
                platform="instagram",
                safety_class=SafetyClass.ADULT,
                ai_generated=True,
                needs_ai_disclosure=True,
                disclosure_present=True,
                rights_status="AI_GENERATED",
            )
        )
        self.assertFalse(result.allowed)
        self.assertIn("adult_content_not_allowed_on_public_sfw_platform", result.reasons)

    def test_compliance_requires_disclosure_and_rights(self) -> None:
        result = check_compliance(
            ComplianceInput(
                platform="threads",
                safety_class=SafetyClass.SFW,
                ai_generated=True,
                needs_ai_disclosure=True,
                disclosure_present=False,
                rights_status="UNKNOWN",
            )
        )
        self.assertEqual(
            set(result.reasons),
            {"missing_ai_disclosure", "unconfirmed_media_rights"},
        )

    def test_failure_ends_partial_ready_and_can_retry(self) -> None:
        class BrokenPublisher:
            provider = "mock"

            def publish(self, publication_id: int, creator_slug: str) -> tuple[str, str]:
                raise RuntimeError("simulated provider outage")

        self.pipeline.publisher = BrokenPublisher()
        result = self.pipeline.run_safe("mara-field", date(2026, 9, 5))
        self.assertIsNone(result)
        failed_run = self.database.one(
            "SELECT status, error_message FROM runs WHERE run_key LIKE '2026-09-05:mara-field:%'"
        )
        self.assertEqual(failed_run["status"], "PARTIAL_READY")
        self.assertIn("simulated provider outage", failed_run["error_message"])

        self.pipeline.publisher = MockPublisher()
        recovered = self.pipeline.run("mara-field", date(2026, 9, 5))
        self.assertEqual(recovered.final_status, ContentStatus.ANALYZED)
        self.assertEqual(
            self.database.scalar(
                "SELECT status FROM runs WHERE run_key LIKE '2026-09-05:mara-field:%'"
            ),
            "COMPLETE",
        )


if __name__ == "__main__":
    unittest.main()
