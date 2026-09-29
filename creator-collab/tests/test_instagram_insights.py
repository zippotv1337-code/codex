from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from creator_ops.analytics import AnalyticsService
from creator_ops.cli import build_pipeline
from creator_ops.instagram_insights import MetaInstagramInsightsService
from creator_ops.publishing import MetaGraphError
from creator_ops.reconcile import ManualInstagramService
from creator_ops.review import ReviewDashboardService


class FakeInsightsTransport:
    def __init__(self, *, fail_metrics: set[str] | None = None) -> None:
        self.fail_metrics = fail_metrics or set()
        self.gets: list[tuple[str, dict[str, str]]] = []

    def post(self, path: str, data: dict[str, str]) -> dict[str, object]:
        raise AssertionError("Insights sync must never POST")

    def get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        self.gets.append((path, dict(params)))
        if path.endswith("/insights"):
            metric = params["metric"]
            if metric in self.fail_metrics:
                raise MetaGraphError("meta_graph_error_code_100")
            values = {
                "reach": 900,
                "views": 1200,
                "likes": 41,
                "comments": 7,
                "shares": 5,
                "saved": 13,
            }
            return {
                "data": [
                    {
                        "name": metric,
                        "total_value": {"value": values[metric]},
                    }
                ]
            }
        return {
            "id": path,
            "media_type": "CAROUSEL_ALBUM",
            "timestamp": "2026-09-20T10:00:00+0000",
            "permalink": "https://www.instagram.com/p/providerProof/",
            "like_count": 40,
            "comments_count": 6,
        }


class BrokenInsightsTransport(FakeInsightsTransport):
    def get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        raise MetaGraphError("meta_graph_error_code_190")


class InstagramInsightsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pipeline = build_pipeline(self.root / "insights.db")
        self.pipeline.initialize()
        card = ReviewDashboardService(self.pipeline).ensure_date(date(2026, 9, 1))[0]
        self.publication_id = ManualInstagramService(self.pipeline.db).reconcile(
            creator_slug="leona-voss",
            content_id=card["content_id"],
            external_url="https://www.instagram.com/p/providerProof/",
            published_at="2026-09-20T10:00:00+00:00",
        )["publication_id"]
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE publications SET provider='instagram-meta-graph', external_id='18000000000000001' WHERE id=?",
                (self.publication_id,),
            )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def service(self, transport: FakeInsightsTransport) -> MetaInstagramInsightsService:
        return MetaInstagramInsightsService(
            self.pipeline.db,
            self.root,
            transports={"leona-voss": transport},
        )

    def test_exact_due_capture_is_read_only_idempotent_and_preserves_unknowns(self) -> None:
        transport = FakeInsightsTransport(fail_metrics={"shares"})
        now = datetime(2026, 9, 21, 11, 0, tzinfo=timezone.utc)
        first = self.service(transport).sync_due(now=now)
        second = self.service(transport).sync_due(now=now)

        self.assertEqual(first["counts"]["captured"], 1)
        self.assertEqual(second["counts"]["captured"], 0)
        self.assertTrue(all(path for path, _ in transport.gets))
        row = self.pipeline.db.one(
            "SELECT * FROM manual_analytics_events WHERE publication_id=?",
            (self.publication_id,),
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["window_hours"], 24)
        self.assertEqual(row["source"], "META_GRAPH")
        self.assertEqual(row["reach"], 900)
        self.assertEqual(row["views"], 1200)
        self.assertEqual(row["saves"], 13)
        self.assertIsNone(row["shares"])
        self.assertIsNone(row["profile_visits"])
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM manual_analytics_events"),
            1,
        )

    def test_late_first_capture_uses_highest_due_window_and_marks_earlier_missed(self) -> None:
        now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
        result = self.service(FakeInsightsTransport()).sync_due(now=now)
        self.assertEqual(result["items"][0]["window_hours"], 168)
        self.assertEqual(result["items"][0]["source"], "META_GRAPH_LATE")

        snapshot = AnalyticsService(self.pipeline.db).snapshot(now=now)
        windows = snapshot["instagram"]["publications"][0]["windows"]
        self.assertEqual([item["status"] for item in windows], ["MISSED", "MISSED", "CAPTURED"])
        self.assertEqual(windows[2]["source"], "META_GRAPH_LATE")
        self.assertEqual(snapshot["instagram"]["due_windows"], 0)

    def test_provider_failure_never_invents_zero_or_writes_an_event(self) -> None:
        now = datetime(2026, 9, 21, 11, 0, tzinfo=timezone.utc)
        result = self.service(BrokenInsightsTransport()).sync_due(now=now)
        self.assertEqual(result["counts"]["provider_error"], 1)
        self.assertEqual(result["items"][0]["status"], "NO_SUPPORTED_METRICS")
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM manual_analytics_events"),
            0,
        )
        self.assertNotIn("access_token", str(result).lower())

    def test_official_168h_snapshot_feeds_existing_prime_time_learning(self) -> None:
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE publications SET published_at='2026-09-20T20:30:00+02:00' WHERE id=?",
                (self.publication_id,),
            )
        self.service(FakeInsightsTransport()).sync_due(
            now=datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
        )
        creator_id = self.pipeline.db.scalar(
            "SELECT id FROM creators WHERE slug='leona-voss'"
        )
        with self.pipeline.db.transaction() as connection:
            decision = self.pipeline.scheduler.choose(
                connection,
                creator_id,
                date(2026, 10, 2),
                "instagram",
                "carousel",
            )
        self.assertEqual(decision.local_time, "20:30")
        self.assertEqual(decision.source, "analytics-history")

    def test_existing_manual_snapshot_blocks_provider_duplicate_for_same_window(self) -> None:
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO manual_analytics_events
                    (publication_id,window_hours,captured_at,source,reach,note)
                VALUES (?,24,'2026-09-21T10:00:00+00:00','MANUAL_OWNER',100,'visible owner value')
                """,
                (self.publication_id,),
            )
        now = datetime(2026, 9, 21, 11, 0, tzinfo=timezone.utc)
        transport = FakeInsightsTransport()
        result = self.service(transport).sync_due(now=now)
        self.assertEqual(result["counts"]["waiting"], 1)
        self.assertEqual(transport.gets, [])
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM manual_analytics_events"),
            1,
        )


if __name__ == "__main__":
    unittest.main()
