import unittest
from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from pathlib import Path

from creator_ops.analytics import AnalyticsService
from creator_ops.database import CreatorDatabase


class AnalyticsServiceTests(unittest.TestCase):
    def test_snapshot_keeps_missing_windows_unknown(self):
        with TemporaryDirectory() as folder:
            db = CreatorDatabase(Path(folder) / "analytics.db")
            db.initialize()
            snapshot = AnalyticsService(db).snapshot(now=datetime.now(timezone.utc))
        self.assertIn("instagram", snapshot)
        self.assertEqual(snapshot["instagram"]["captured_windows"], 0)
        self.assertEqual(snapshot["fiverr"]["status"], "OWNER_GATE")


if __name__ == "__main__":
    unittest.main()
