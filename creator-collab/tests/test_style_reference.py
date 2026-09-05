from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.review import ReviewDashboardService
from creator_ops.style_reference import StyleReferenceService


class StyleReferenceTests(unittest.TestCase):
    def test_internal_marker_is_idempotent_and_visible_without_retro_tagging(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            pipeline = build_pipeline(Path(tempdir) / "style.db")
            pipeline.initialize()
            review = ReviewDashboardService(pipeline)
            cards = review.ensure_date(date(2026, 9, 7))
            leona = next(card for card in cards if card["creator_slug"] == "leona-voss")
            service = StyleReferenceService(pipeline.db)
            first = service.mark(
                leona["content_id"], strength="light", reference_format="fashion"
            )
            second = service.mark(
                leona["content_id"], strength="medium", reference_format="personality"
            )
            self.assertFalse(first["reused"])
            self.assertTrue(second["reused"])
            self.assertEqual(
                pipeline.db.scalar("SELECT COUNT(*) FROM experiments WHERE variable='style_reference'"),
                1,
            )
            updated = review.cards(date(2026, 9, 7))[0]
            self.assertEqual(updated["style_reference"], "mz_poke")
            self.assertEqual(updated["reference_strength"], "medium")

    def test_invalid_or_non_public_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            pipeline = build_pipeline(Path(tempdir) / "style.db")
            pipeline.initialize()
            review = ReviewDashboardService(pipeline)
            card = review.ensure_date(date(2026, 9, 7))[0]
            service = StyleReferenceService(pipeline.db)
            with self.assertRaisesRegex(ValueError, "invalid_reference_strength"):
                service.mark(card["content_id"], strength="strong", reference_format="fashion")
            with pipeline.db.transaction() as connection:
                connection.execute(
                    "UPDATE content_items SET visibility_scope='LOCAL_ONLY' WHERE id=?",
                    (card["content_id"],),
                )
                connection.execute(
                    "UPDATE assets SET visibility_scope='LOCAL_ONLY' WHERE content_id=?",
                    (card["content_id"],),
                )
            with self.assertRaisesRegex(ValueError, "public_sfw_only"):
                service.mark(card["content_id"], strength="light", reference_format="fashion")


if __name__ == "__main__":
    unittest.main()
