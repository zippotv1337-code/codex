from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

from creator_ops.cli import build_pipeline
from creator_ops.asset_import import LocalAssetImportService
from creator_ops.database import CreatorDatabase
from creator_ops.review import ReviewDashboardService
from creator_ops.web import create_server


ROOT = Path(__file__).resolve().parents[1]


class ReviewDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tempdir.name) / "review.db"
        self.pipeline = build_pipeline(self.database_path)
        self.pipeline.initialize()
        self.service = ReviewDashboardService(self.pipeline)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_tomorrow_cards_are_complete_for_both_personas(self) -> None:
        cards = self.service.ensure_date(date(2026, 9, 4))
        self.assertEqual([card["creator_slug"] for card in cards], ["leona-voss", "mara-field"])
        for card in cards:
            self.assertEqual(card["asset_count"], 5)
            self.assertEqual(card["top_pick_count"], 3)
            self.assertTrue(card["ready"])
            self.assertFalse(card["approved"])
            self.assertTrue(all(card["checks"].values()))
            self.assertEqual(card["status"], "READY_FOR_REVIEW")
            self.assertNotIn(card["disclosure"], card["caption"])
            self.assertNotIn("kigeneriert", card["caption"].lower())

    def test_preparing_same_day_is_idempotent(self) -> None:
        first = self.service.ensure_date(date(2026, 9, 4))
        second = self.service.ensure_date(date(2026, 9, 4))
        self.assertEqual(
            [card["content_id"] for card in first],
            [card["content_id"] for card in second],
        )
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM content_items"), 2)
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM assets"), 10)

    def test_local_image_import_replaces_mock_slot_and_keeps_fallbacks(self) -> None:
        source = Path(self.tempdir.name) / "candidate.png"
        source.write_bytes(b"\x89PNG\r\n\x1a\nlocal-test-image")
        importer = LocalAssetImportService(self.pipeline, Path(self.tempdir.name))
        imported = importer.import_files(
            "leona-voss",
            date(2026, 9, 4),
            [source],
            rights_status="OWNED",
        )
        cards = self.service.cards(date(2026, 9, 4))
        leona = cards[0]
        mara = cards[1]
        self.assertEqual(len(imported), 1)
        self.assertEqual(leona["asset_count"], 5)
        self.assertEqual(sum(asset["preview_url"] is not None for asset in leona["assets"]), 1)
        self.assertTrue(all(asset["preview_url"] is None for asset in mara["assets"]))
        preview = importer.preview_path(imported[0]["asset_id"])
        self.assertIsNotNone(preview)
        self.assertEqual(preview[1], "image/png")
        stored = self.pipeline.db.one(
            "SELECT generator, safety_class, rights_status FROM assets WHERE id = ?",
            (imported[0]["asset_id"],),
        )
        self.assertEqual(dict(stored), {
            "generator": "local-import",
            "safety_class": "SFW",
            "rights_status": "OWNED",
        })

    def test_approval_creates_only_a_local_mock_draft(self) -> None:
        card = self.service.ensure_date(date(2026, 9, 4))[0]
        result = self.service.approve(card["content_id"])
        publication = self.pipeline.db.one(
            """
            SELECT provider, status, external_id, external_url
            FROM publications WHERE content_id = ?
            """,
            (card["content_id"],),
        )
        self.assertEqual(result["status"], "SCHEDULED")
        self.assertEqual(publication["provider"], "mock-draft")
        self.assertEqual(publication["status"], "SCHEDULED")
        self.assertIsNone(publication["external_id"])
        self.assertIsNone(publication["external_url"])
        self.assertEqual(
            self.pipeline.db.scalar(
                "SELECT COUNT(*) FROM review_events WHERE action = 'OWNER_APPROVED_UI'"
            ),
            1,
        )
        repeated = self.service.approve(card["content_id"])
        self.assertTrue(repeated["reused"])
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM publications"), 1)

    def test_http_surface_lists_and_approves_a_card(self) -> None:
        source = Path(self.tempdir.name) / "http-preview.png"
        source.write_bytes(b"\x89PNG\r\n\x1a\nhttp-preview")
        imported = LocalAssetImportService(
            self.pipeline, Path(self.tempdir.name)
        ).import_files("leona-voss", date(2026, 9, 4), [source])
        server = create_server(
            self.database_path, port=0, asset_root=Path(self.tempdir.name)
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(f"{base}/api/reviews?date=2026-09-04", timeout=5) as response:
                payload = json.load(response)
            self.assertEqual(len(payload["cards"]), 2)
            preview_url = payload["cards"][0]["assets"][0]["preview_url"]
            self.assertIsNotNone(preview_url)
            with urlopen(f"{base}{preview_url}", timeout=5) as response:
                self.assertEqual(response.headers.get_content_type(), "image/png")
                self.assertEqual(response.read(), source.read_bytes())
            content_id = payload["cards"][0]["content_id"]
            request = Request(f"{base}/api/reviews/{content_id}/approve", method="POST")
            with urlopen(request, timeout=5) as response:
                approved = json.load(response)
            self.assertEqual(approved["status"], "SCHEDULED")
            with urlopen(f"{base}/api/health", timeout=5) as response:
                health = json.load(response)
            self.assertEqual(health, {"status": "ok", "mode": "local-mock"})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
