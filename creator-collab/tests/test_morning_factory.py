from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from creator_ops.cli import build_pipeline
from creator_ops.morning import MorningContentFactory
from creator_ops.review import ReviewDashboardService


class MorningFactoryTests(unittest.TestCase):
    def test_0530_flow_prepares_two_five_candidate_packages_once(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            pipeline = build_pipeline(root / "morning.db")
            pipeline.initialize()
            factory = MorningContentFactory(ReviewDashboardService(pipeline), root)
            berlin = ZoneInfo("Europe/Berlin")
            early = factory.run(datetime(2026, 9, 7, 5, 20, tzinfo=berlin))
            self.assertEqual(early["status"], "WAITING_FOR_SLOT")
            first = factory.run(datetime(2026, 9, 7, 5, 30, tzinfo=berlin))
            second = factory.run(datetime(2026, 9, 7, 5, 45, tzinfo=berlin))
            self.assertEqual(first["status"], "COMPLETE")
            self.assertTrue(second["reused"])
            self.assertEqual(pipeline.db.scalar("SELECT COUNT(*) FROM content_items"), 2)
            self.assertEqual(pipeline.db.scalar("SELECT COUNT(*) FROM assets"), 10)


if __name__ == "__main__":
    unittest.main()
