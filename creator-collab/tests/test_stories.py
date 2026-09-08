from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.review import ReviewDashboardService
from creator_ops.stories import StoryReserveService
from creator_ops.asset_import import LocalAssetImportService


class StoryReserveTests(unittest.TestCase):
    def test_four_feed_packages_become_safe_review_only_story_packages(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            pipeline = build_pipeline(Path(folder) / "stories.db")
            pipeline.initialize()
            reviews = ReviewDashboardService(pipeline)
            reviews.ensure_date(date(2026, 9, 5))
            reviews.ensure_date(date(2026, 9, 6))
            packages = StoryReserveService(reviews).packages()
            self.assertEqual(len(packages), 4)
            for package in packages:
                self.assertEqual(package["status"], "READY_FOR_OWNER_REVIEW")
                self.assertEqual([frame["kind"] for frame in package["frames"]], ["TEASER", "POLL", "COMMUNITY"])
                self.assertEqual(len({frame["asset"]["id"] for frame in package["frames"]}), 3)
                self.assertIn("kein Auto-Posting", package["safety_note"])

    def test_published_assets_never_enter_story_frames(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            pipeline = build_pipeline(Path(folder) / "stories.db")
            pipeline.initialize()
            reviews = ReviewDashboardService(pipeline)
            card = reviews.ensure_date(date(2026, 9, 5))[0]
            published_id = card["assets"][0]["id"]
            with pipeline.db.transaction() as connection:
                connection.execute("UPDATE assets SET published_status='PUBLISHED' WHERE id=?", (published_id,))
            package = next(item for item in StoryReserveService(reviews).packages() if item["content_id"] == card["content_id"])
            self.assertNotIn(published_id, [frame["asset"]["id"] for frame in package["frames"]])

    def test_story_decisions_are_local_and_do_not_change_feed_state(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            pipeline = build_pipeline(Path(folder) / "stories.db")
            pipeline.initialize()
            reviews = ReviewDashboardService(pipeline)
            card = reviews.ensure_date(date(2026, 9, 5))[0]
            before = pipeline.db.scalar("SELECT status FROM content_items WHERE id=?", (card["content_id"],))
            sources = []
            for index in range(5):
                source = Path(folder) / f"story-{index}.png"
                source.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([index]))
                sources.append(source)
            LocalAssetImportService(pipeline, Path(folder)).import_files("leona-voss", date(2026, 9, 5), sources)
            result = reviews.story_decision(card["content_id"], "approve")
            after = pipeline.db.scalar("SELECT status FROM content_items WHERE id=?", (card["content_id"],))
            self.assertEqual(result["action"], "STORY_APPROVED_UI")
            self.assertEqual(before, after)
            self.assertEqual(
                pipeline.db.scalar("SELECT action FROM review_events WHERE content_id=? ORDER BY id DESC LIMIT 1", (card["content_id"],)),
                "STORY_APPROVED_UI",
            )
            def refreshed():
                return next(item for item in StoryReserveService(ReviewDashboardService(pipeline)).packages()
                            if item["content_id"] == card["content_id"])
            self.assertEqual(refreshed()["status"], "APPROVED")
            planned_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            reviews.story_decision(card["content_id"], "plan", fields={"planned_at": planned_at})
            self.assertEqual(refreshed()["status"], "LOCAL_PLANNED")
            self.assertIsNotNone(refreshed()["planned_at"])
            for action, status in [("pause", "PAUSED"), ("change", "CHANGE_REQUESTED"), ("reject", "REJECTED")]:
                reviews.story_decision(card["content_id"], action)
                self.assertEqual(refreshed()["status"], status)
            self.assertEqual(pipeline.db.scalar("SELECT COUNT(*) FROM publications"), 0)
            self.assertEqual(pipeline.db.scalar("SELECT COUNT(*) FROM publish_queue"), 0)
            self.assertEqual(before, pipeline.db.scalar("SELECT status FROM content_items WHERE id=?", (card["content_id"],)))

    def test_story_edit_is_persistent_and_cannot_change_assets_or_fake_publish(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            pipeline = build_pipeline(Path(folder) / "stories.db")
            pipeline.initialize()
            reviews = ReviewDashboardService(pipeline)
            reviews.ensure_date(date(2026, 9, 5))
            package = StoryReserveService(reviews).packages()[0]
            fields = {"cta": "Am Fenster oder auf dem Weg?", "highlight": "Berlin", "status": "PUBLISHED",
                      "frames": [{"kind": "BTS", "copy": "Kaffee am Fenster", "interaction": "Eine ruhige Minute",
                                  "asset_id": 99999} for _ in package["frames"]]}
            reviews.story_decision(package["content_id"], "edit", fields=fields)
            after = StoryReserveService(ReviewDashboardService(pipeline)).packages()[0]
            self.assertEqual(after["status"], "READY_FOR_OWNER_REVIEW")
            self.assertEqual(after["cta"], fields["cta"])
            self.assertEqual(after["highlight"], "Berlin")
            self.assertTrue(all(frame["copy"] == "Kaffee am Fenster" for frame in after["frames"]))
            self.assertEqual([f["asset"]["id"] for f in after["frames"]], [f["asset"]["id"] for f in package["frames"]])
            fields["frames"][0]["link"] = "javascript:alert(1)"
            with self.assertRaises(ValueError):
                reviews.story_decision(package["content_id"], "edit", fields=fields)
            self.assertEqual(pipeline.db.scalar("SELECT COUNT(*) FROM review_events WHERE action='STORY_EDITED_UI'"), 1)

    def test_mock_approval_and_missing_schedule_are_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            pipeline = build_pipeline(Path(folder) / "stories.db")
            pipeline.initialize()
            reviews = ReviewDashboardService(pipeline)
            card = reviews.ensure_date(date(2026, 9, 5))[0]
            with self.assertRaisesRegex(ValueError, "real_previews"):
                reviews.story_decision(card["content_id"], "approve")
            with pipeline.db.transaction() as connection:
                connection.execute("INSERT INTO review_events(content_id,action,actor,note,created_at) VALUES (?,'STORY_PLANNED_UI','owner-dashboard','legacy plan without date','2026-09-05')", (card["content_id"],))
            package = StoryReserveService(reviews).packages()[0]
            self.assertEqual(package["status"], "NEEDS_SCHEDULE")
            self.assertIsNone(package["planned_at"])


if __name__ == "__main__":
    unittest.main()
