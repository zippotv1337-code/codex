from __future__ import annotations

import unittest
from collections import Counter

from creator_ops.content_mix import ContentMixPlanner
from creator_ops.models import ContentStage


class ContentMixPlannerTests(unittest.TestCase):
    def test_twenty_slot_plan_matches_owner_mix(self) -> None:
        plan = ContentMixPlanner().plan(20)
        self.assertEqual(
            Counter(plan),
            {
                ContentStage.ALLTAG: 8,
                ContentStage.TEASER: 7,
                ContentStage.ADULT_18: 5,
            },
        )

    def test_largest_deficit_is_recommended(self) -> None:
        recommendation = ContentMixPlanner().recommend(
            {"ALLTAG": 8, "TEASER": 2, "ADULT_18": 5}
        )
        self.assertEqual(recommendation.next_stage, ContentStage.TEASER)


if __name__ == "__main__":
    unittest.main()
