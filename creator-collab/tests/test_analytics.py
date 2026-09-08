import json
import tempfile
import threading
import unittest
from datetime import date, datetime, timezone
from tempfile import TemporaryDirectory
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from creator_ops.analytics import AnalyticsService
from creator_ops.cli import build_pipeline
from creator_ops.database import CreatorDatabase
from creator_ops.reconcile import ManualInstagramService
from creator_ops.review import ReviewDashboardService
from creator_ops.web import create_server


class AnalyticsServiceTests(unittest.TestCase):
    def test_snapshot_keeps_missing_windows_unknown(self):
        with TemporaryDirectory() as folder:
            db = CreatorDatabase(Path(folder) / "analytics.db")
            db.initialize()
            snapshot = AnalyticsService(db).snapshot(now=datetime.now(timezone.utc))
        self.assertIn("instagram", snapshot)
        self.assertEqual(snapshot["instagram"]["captured_windows"], 0)
        self.assertEqual(snapshot["fiverr"]["status"], "OWNER_GATE")

    def test_real_events_power_persona_totals_and_cautious_learning(self):
        with TemporaryDirectory() as folder:
            pipeline = build_pipeline(Path(folder) / "analytics.db")
            pipeline.initialize()
            cards = ReviewDashboardService(pipeline).ensure_date(date(2026, 9, 1))
            manual = ManualInstagramService(pipeline.db)
            leona = manual.reconcile(
                creator_slug="leona-voss", content_id=cards[0]["content_id"],
                external_url="https://www.instagram.com/p/realLeona1/", published_at="2026-09-01T10:00:00+02:00",
            )["publication_id"]
            mara = manual.reconcile(
                creator_slug="mara-field", content_id=cards[1]["content_id"],
                external_url="https://www.instagram.com/p/realMara01/", published_at="2026-09-01T11:00:00+02:00",
            )["publication_id"]
            manual.append_analytics(leona, 24, reach=100, likes=10, saves=8)
            manual.append_analytics(mara, 24, reach=200, likes=12, saves=9)
            snapshot = AnalyticsService(pipeline.db).snapshot(now=datetime(2026, 9, 8, tzinfo=timezone.utc))
        instagram = snapshot["instagram"]
        self.assertEqual(instagram["captured_windows"], 2)
        by_persona = {item["persona"]: item for item in instagram["by_persona"]}
        self.assertEqual(set(by_persona), {"leona-voss", "mara-field"})
        self.assertEqual(by_persona["leona-voss"]["captured_publications"], 1)
        self.assertEqual(by_persona["mara-field"]["captured_publications"], 1)
        self.assertEqual(instagram["learning"]["status"], "OBSERVING")
        self.assertEqual(instagram["learning"]["patterns"]["format"]["value"], "carousel")
        self.assertEqual(instagram["learning"]["recommendations"][0]["decision"], "VARIATE")

    def test_reposted_content_is_not_two_independent_learning_samples(self):
        with TemporaryDirectory() as folder:
            pipeline = build_pipeline(Path(folder) / "analytics.db")
            pipeline.initialize()
            card = ReviewDashboardService(pipeline).ensure_date(date(2026, 9, 1))[0]
            manual = ManualInstagramService(pipeline.db)
            first = manual.reconcile(
                creator_slug=card["creator_slug"], content_id=card["content_id"],
                external_url="https://www.instagram.com/p/sameContent01/", published_at="2026-09-01T10:00:00+02:00",
            )["publication_id"]
            second = manual.reconcile(
                creator_slug=card["creator_slug"], content_id=card["content_id"],
                external_url="https://www.instagram.com/p/sameContent02/", published_at="2026-09-02T10:00:00+02:00",
            )["publication_id"]
            manual.append_analytics(first, 24, reach=100, likes=10)
            manual.append_analytics(second, 72, reach=120, likes=12)
            snapshot = AnalyticsService(pipeline.db).snapshot(now=datetime(2026, 9, 8, tzinfo=timezone.utc))
        learning = snapshot["instagram"]["learning"]
        self.assertEqual(snapshot["instagram"]["captured_windows"], 2)
        self.assertEqual(learning["recommendations"][0]["decision"], "UNKNOWN")
        self.assertIsNone(learning["patterns"]["format"])

    def test_http_capture_requires_a_real_value_and_returns_it_to_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root / "analytics.db"
            server = create_server(database, port=0, asset_root=root)
            service = server.RequestHandlerClass.service
            card = service.ensure_date(date(2026, 9, 1))[0]
            publication_id = ManualInstagramService(service.pipeline.db).reconcile(
                creator_slug=card["creator_slug"], content_id=card["content_id"],
                external_url="https://www.instagram.com/p/realCapture1/", published_at="2026-09-01T10:00:00+02:00",
            )["publication_id"]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                empty = Request(f"{base}/api/analytics/{publication_id}/capture", data=urlencode({"window_hours": "24"}).encode(), method="POST")
                with self.assertRaises(HTTPError) as raised:
                    urlopen(empty)
                self.assertEqual(raised.exception.code, 409)
                request = Request(
                    f"{base}/api/analytics/{publication_id}/capture",
                    data=urlencode({"window_hours": "24", "reach": "120", "likes": "14", "note": "sichtbar in Insights"}).encode(),
                    method="POST",
                )
                with urlopen(request) as response:
                    result = json.load(response)
                self.assertFalse(result["external_action"])
                with urlopen(f"{base}/api/analytics") as response:
                    snapshot = json.load(response)
                captured = snapshot["instagram"]["publications"][0]["windows"][0]
                self.assertEqual(captured["status"], "CAPTURED")
                self.assertEqual(captured["metrics"]["reach"], 120)
                self.assertEqual(captured["metrics"]["likes"], 14)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
