from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.meta_push import MetaPushService
from creator_ops.publishing import DispatchResult, PUBLISHED
from creator_ops.review import ReviewDashboardService


class FakePushAdapter:
    provider = "instagram-meta-graph-fixture"
    available = True

    def __init__(self) -> None:
        self.preflight_calls: list[tuple[int, int]] = []
        self.publish_calls: list[tuple[int, int, str]] = []

    def preflight(self, publication_id: int, content_id: int) -> dict[str, object]:
        self.preflight_calls.append((publication_id, content_id))
        return {"status": "READY", "publication_id": publication_id, "content_id": content_id, "errors": []}

    def publish(self, publication_id: int, content_id: int, idempotency_key: str) -> DispatchResult:
        self.publish_calls.append((publication_id, content_id, idempotency_key))
        return DispatchResult(
            status=PUBLISHED,
            external_id="18000000000000001",
            external_url="https://www.instagram.com/p/fixture-meta-push/",
        )


class MetaPushServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.pipeline = build_pipeline(self.project / "review.db")
        self.pipeline.initialize()
        self.review = ReviewDashboardService(self.pipeline)
        self.card = self.review.ensure_date(date(2026, 9, 14))[0]
        self.review.approve(self.card["content_id"])
        self.adapter = FakePushAdapter()
        self.service = MetaPushService(
            self.pipeline.db,
            self.project,
            adapter_factory=lambda: self.adapter,
        )

    def test_preflight_is_read_only_and_push_targets_one_queue_item(self) -> None:
        before = self.pipeline.db.one(
            "SELECT status, attempts, planned_at FROM publish_queue WHERE content_id=?",
            (self.card["content_id"],),
        )
        result = self.service.preflight(self.card["content_id"])
        self.assertEqual(result["status"], "READY")
        after_preflight = self.pipeline.db.one(
            "SELECT status, attempts, planned_at FROM publish_queue WHERE content_id=?",
            (self.card["content_id"],),
        )
        self.assertEqual(tuple(after_preflight), tuple(before))
        self.assertEqual(self.adapter.publish_calls, [])

        pushed = self.service.push_one(self.card["content_id"])
        self.assertEqual(pushed["status"], PUBLISHED)
        self.assertEqual(pushed["external_id"], "18000000000000001")
        self.assertEqual(len(self.adapter.publish_calls), 1)
        self.assertGreaterEqual(len(self.adapter.preflight_calls), 2)
        publication = self.pipeline.db.one(
            "SELECT scheduled_at, status, external_id, external_url FROM publications WHERE content_id=?",
            (self.card["content_id"],),
        )
        self.assertEqual(publication["status"], PUBLISHED)
        self.assertEqual(publication["external_id"], "18000000000000001")
        self.assertEqual(publication["external_url"], "https://www.instagram.com/p/fixture-meta-push/")
        self.assertIsNotNone(publication["scheduled_at"])

    def test_push_never_retries_published_content(self) -> None:
        self.service.push_one(self.card["content_id"])
        with self.assertRaisesRegex(ValueError, "already_published_or_external_state_present"):
            self.service.push_one(self.card["content_id"])
        self.assertEqual(len(self.adapter.publish_calls), 1)


if __name__ == "__main__":
    unittest.main()
