from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.review import ReviewDashboardService
from creator_ops.stories import StoryReserveService


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


if __name__ == "__main__":
    unittest.main()
