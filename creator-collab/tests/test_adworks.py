from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from creator_ops.adworks import AdWorksService
from creator_ops.cli import build_pipeline
from creator_ops.exporting import ExportBackupService
from creator_ops.review import ReviewDashboardService
from creator_ops.web import create_server


class AdWorksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db_path = self.root / "creator.db"
        self.pipeline = build_pipeline(self.db_path)
        self.pipeline.initialize()
        self.service = AdWorksService(self.pipeline.db)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_additive_schema_keeps_existing_content_and_seeds_owner_gated_packs(self) -> None:
        ReviewDashboardService(self.pipeline).ensure_date(date(2026, 9, 5))
        before = self.pipeline.db.scalar("SELECT COUNT(*) FROM content_items")
        self.pipeline.initialize()
        self.assertEqual(self.pipeline.db.schema_version(), 5)
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM content_items"), before)
        packs = self.service.seed_catalog()
        self.assertEqual([p["tier"] for p in packs], ["BASIC", "STANDARD", "PREMIUM"])
        self.assertTrue(all(p["price_eur"] is None for p in packs))
        self.assertTrue(all(not p["owner_approved"] for p in packs))

    def test_dry_run_is_traceable_idempotent_and_separate_from_real_revenue(self) -> None:
        first = self.service.dry_run()
        second = self.service.dry_run()
        self.assertFalse(first.reused)
        self.assertTrue(second.reused)
        self.assertEqual(first.event_keys, second.event_keys)
        events = self.pipeline.db.all(
            """
            SELECT e.event_type, e.is_mock, p.pack_key, c.campaign_key, l.link_key
            FROM funnel_events e
            JOIN product_packs p ON p.id=e.pack_id
            JOIN adworks_campaigns c ON c.id=e.campaign_id
            JOIN tracking_links l ON l.id=e.tracking_link_id
            ORDER BY e.id
            """
        )
        self.assertEqual([row["event_type"] for row in events], ["click", "landing_view", "lead", "purchase"])
        self.assertTrue(all(row["is_mock"] == 1 for row in events))
        self.assertTrue(all(row["pack_key"] == first.pack_key for row in events))
        self.assertTrue(all(row["campaign_key"] == first.campaign_key for row in events))
        self.assertTrue(all(row["link_key"] == first.link_key for row in events))
        board = self.service.dashboard()
        self.assertEqual(board["real_revenue_eur"], 0)
        self.assertEqual(board["mock_revenue_eur"], 123.45)
        self.assertEqual(board["paid_spend"], "OWNER_GATE")
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM product_feedback"), 1)

    def test_public_export_keeps_safe_lineage_but_omits_event_metadata(self) -> None:
        self.service.dry_run()
        target = ExportBackupService(self.pipeline.db).export_json(self.root, "adworks")
        payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "creator-ops-export-v4")
        self.assertEqual(len(payload["tables"]["product_packs"]), 3)
        self.assertEqual(len(payload["tables"]["funnel_events"]), 4)
        self.assertNotIn("metadata_json", payload["tables"]["funnel_events"][0])

    def test_http_offer_revenue_and_dry_run(self) -> None:
        server = create_server(self.db_path, port=0, asset_root=self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(f"{base}/offer", timeout=5) as response:
                self.assertIn("SFW-Pakete", response.read().decode("utf-8"))
            with urlopen(f"{base}/revenue", timeout=5) as response:
                self.assertIn("Revenue Board", response.read().decode("utf-8"))
            body = urlencode({"pack": "creator-sfw-basic"}).encode()
            with urlopen(Request(f"{base}/api/adworks/dry-run", data=body, method="POST"), timeout=5) as response:
                result = json.load(response)
            self.assertEqual(result["pack_key"], "creator-sfw-basic")
            with urlopen(f"{base}/api/adworks", timeout=5) as response:
                board = json.load(response)
            self.assertEqual(board["real_revenue_eur"], 0)
            self.assertEqual(board["mock_revenue_eur"], 123.45)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_unknown_pack_is_rejected(self) -> None:
        with self.assertRaisesRegex(KeyError, "pack_not_found"):
            self.service.dry_run("does-not-exist")


if __name__ == "__main__":
    unittest.main()
