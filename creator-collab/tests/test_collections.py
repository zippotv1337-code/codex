from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.collections import CollectionService
from creator_ops.review import ReviewDashboardService


class CollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.pipeline = build_pipeline(Path(self.tempdir.name) / "collections.db")
        self.pipeline.initialize()
        self.reviews = ReviewDashboardService(self.pipeline)
        self.reviews.ensure_date(date(2026, 9, 5))
        self.reviews.ensure_date(date(2026, 9, 6))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_collections_reuse_asset_ids_and_expose_unknown_performance(self) -> None:
        items = CollectionService(self.reviews).list()
        self.assertEqual(len(items), 4)
        for item in items:
            self.assertEqual(item["asset_count"], 5)
            self.assertEqual(len(item["top3"]), 3)
            self.assertIsNone(item["top_performer"])
            self.assertIn("Analytics", item["top_performer_note"])

    def test_persona_filter_is_exact(self) -> None:
        items = CollectionService(self.reviews).list("mara-field")
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item["creator_slug"] == "mara-field" for item in items))


if __name__ == "__main__":
    unittest.main()
