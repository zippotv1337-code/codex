from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError
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
        self.root = Path(self.tempdir.name)
        self.database_path = self.root / "review.db"
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
            self.assertEqual(card["content_stage"], "ALLTAG")
            self.assertEqual(card["safety_class"], "SFW")
            self.assertEqual(card["visibility_scope"], "PUBLIC_SFW")
            self.assertFalse(card["privacy_blur"])
            self.assertTrue(card["checks"]["pose_matrix"])
            self.assertTrue(card["checks"]["top3_diversity"])
            self.assertTrue(card["hook"])
            self.assertTrue(card["cta"])
            self.assertIsInstance(card["hashtags"], list)
            self.assertEqual(sorted(a["top_pick_order"] for a in card["assets"] if a["top_pick"]), [1, 2, 3])
            self.assertIn("without", "without music")

    def test_owner_change_and_reject_are_audited_without_external_action(self) -> None:
        cards = self.service.ensure_date(date(2026, 9, 4))
        changed = self.service.record_owner_decision(cards[0]["content_id"], "change", "Neuer Hook")
        rejected = self.service.record_owner_decision(cards[1]["content_id"], "reject", "Nicht passend")
        self.assertEqual(changed["status"], "PARTIAL_READY")
        self.assertEqual(rejected["status"], "BLOCKED")
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM publications"), 0)
        self.assertEqual(
            self.pipeline.db.scalar(
                "SELECT COUNT(*) FROM review_events WHERE action IN ('OWNER_CHANGE_REQUESTED_UI','OWNER_REJECTED_UI')"
            ),
            2,
        )
        refreshed = self.service.cards(date(2026, 9, 4))
        self.assertFalse(refreshed[0]["can_approve"])
        self.assertFalse(refreshed[1]["can_approve"])

    def test_review_queue_spans_all_actionable_dates(self) -> None:
        self.service.ensure_date(date(2026, 9, 5))
        self.service.ensure_date(date(2026, 9, 6))
        queue = self.service.review_queue()
        self.assertEqual(queue["dates"], ["2026-09-05", "2026-09-06"])
        self.assertEqual(len(queue["cards"]), 4)

    def test_review_queue_prefers_real_productive_packages_without_global_date_cutoff(self) -> None:
        self.service.ensure_date(date(2026, 9, 4))
        current = self.service.ensure_date(date(2026, 9, 5))
        sources = []
        for index in range(3):
            source = self.root / f"candidate-{index}.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([index]))
            sources.append(source)
        importer = LocalAssetImportService(self.pipeline, self.root)
        importer.import_files("leona-voss", date(2026, 9, 5), sources)
        importer.import_files("mara-field", date(2026, 9, 5), sources)
        with self.pipeline.db.transaction() as connection:
            variant_id = connection.execute(
                "SELECT id FROM platform_variants WHERE content_id=?",
                (current[0]["content_id"],),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO publications
                    (content_id, platform_variant_id, provider, scheduled_at,
                     published_at, external_id, external_url, status)
                VALUES (?, ?, 'instagram-native-manual', '2026-09-06',
                        '2026-09-06', 'later-native',
                        'https://www.instagram.com/p/later-native/', 'PUBLISHED')
                """,
                (current[0]["content_id"], variant_id),
            )
        queue = self.service.review_queue()
        self.assertEqual(queue["dates"], ["2026-09-05"])
        self.assertEqual(
            {card["content_id"] for card in queue["cards"]},
            {card["content_id"] for card in current},
        )

    def test_queue_time_wins_over_native_date_only_publication(self) -> None:
        cards = self.service.ensure_date(date(2026, 9, 8))
        approved = cards[0]
        self.service.approve(approved["content_id"])
        planned_at = self.pipeline.db.scalar(
            "SELECT planned_at FROM publish_queue WHERE content_id=?",
            (approved["content_id"],),
        )
        with self.pipeline.db.transaction() as connection:
            for card in cards:
                variant_id = connection.execute(
                    "SELECT id FROM platform_variants WHERE content_id=?",
                    (card["content_id"],),
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO publications
                        (content_id, platform_variant_id, provider, scheduled_at,
                         published_at, external_id, external_url, status)
                    VALUES (?, ?, 'instagram-native-manual', '2026-09-04',
                            '2026-09-04', ?, ?, 'PUBLISHED')
                    """,
                    (
                        card["content_id"],
                        variant_id,
                        f"native-{card['content_id']}",
                        f"https://www.instagram.com/p/native-{card['content_id']}/",
                    ),
                )
        refreshed = self.service.cards(date(2026, 9, 8))
        self.assertEqual(
            refreshed[0]["prime_time"],
            datetime.fromisoformat(planned_at).strftime("%H:%M"),
        )
        self.assertEqual(refreshed[0]["schedule_source"], "local-publish-queue")
        self.assertNotEqual(refreshed[1]["prime_time"], "00:00")
        self.assertNotEqual(refreshed[1]["schedule_source"], "approved-draft")

    def test_music_check_requires_safe_selected_license_and_repairs_silent_fallback(self) -> None:
        card = self.service.ensure_date(date(2026, 9, 4))[0]
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE audio_candidates SET selected=0 WHERE content_id=?",
                (card["content_id"],),
            )
            connection.execute(
                """
                UPDATE audio_candidates SET selected=1
                WHERE content_id=? AND license_status='VERIFY_BEFORE_USE'
                """,
                (card["content_id"],),
            )
        unsafe = self.service.cards(date(2026, 9, 4))[0]
        self.assertFalse(unsafe["checks"]["music"])
        self.assertFalse(unsafe["can_approve"])
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                UPDATE audio_candidates
                SET selected=CASE WHEN lower(label)='option ohne musik' THEN 1 ELSE 0 END,
                    license_status=CASE WHEN lower(label)='option ohne musik'
                                        THEN 'REVIEW_REQUIRED' ELSE license_status END
                WHERE content_id=?
                """,
                (card["content_id"],),
            )
        self.pipeline.db.initialize()
        repaired = self.service.cards(date(2026, 9, 4))[0]
        self.assertEqual(repaired["audio_license"], "SAFE_NO_AUDIO")
        self.assertTrue(repaired["checks"]["music"])

    def test_dashboard_has_stage_filter_and_protected_preview_controls(self) -> None:
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "dashboard" / "app.css").read_text(encoding="utf-8")
        self.assertIn('data-stage-filter="ADULT_18"', html)
        self.assertIn("data-reveal", script)
        self.assertIn("privacy-blur", script)
        self.assertIn(".privacy-protected .asset.privacy-blur", styles)
        self.assertIn("if (response === null) return", script)
        self.assertIn("card.can_approve", script)
        self.assertNotIn("window.prompt", script)
        self.assertIn("requestDecisionNote", script)
        self.assertIn('data-action="reschedule"', script)
        self.assertIn('data-action="live-authorize"', script)
        self.assertIn('dataset.sensitiveConfirm = "armed"', script)
        self.assertIn('data-action="rearm-preflight"', script)
        self.assertNotIn("window.confirm", script)
        self.assertIn("Neuer Termin lokal übernommen", script)
        self.assertIn('id="decision-dialog"', html)
        self.assertNotIn(".status-pill { display: none; }", styles)
        self.assertIn("Slides ausgewählt", script)

    def test_active_review_slots_exclude_blocked_and_expose_attention_inbox(self) -> None:
        queue = self.service.review_queue()
        allowed = {"READY_FOR_REVIEW", "PARTIAL_READY", "OWNER_APPROVED", "SCHEDULED"}
        self.assertTrue(all(card["status"] in allowed for card in queue["active_cards"]))
        self.assertTrue(all(card["status"] != "BLOCKED" for card in queue["active_cards"]))
        self.assertIn("needs_attention", queue)
        self.assertTrue(all("attention_reason" in card for card in queue["needs_attention"]))
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="needs-attention"', html)
        self.assertIn("active_cards", script)

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
            live_request = Request(
                f"{base}/api/reviews/{content_id}/live-authorize", method="POST"
            )
            with self.assertRaises(HTTPError) as raised:
                urlopen(live_request, timeout=5)
            self.assertEqual(raised.exception.code, 403)
            with urlopen(f"{base}/api/health", timeout=5) as response:
                health = json.load(response)
            self.assertEqual(health["status"], "ok")
            self.assertEqual(health["mode"], "local-mock")
            self.assertFalse(health["auth"])
            self.assertEqual(health["database"], "ok")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_http_owner_can_accept_a_suggested_local_reschedule(self) -> None:
        card = self.service.ensure_date(date(2026, 9, 8))[0]
        self.service.approve(card["content_id"])
        suggested = "2026-09-09T19:30:00+02:00"
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                UPDATE publish_queue
                SET status='NEEDS_RESCHEDULE_REVIEW', suggested_at=?,
                    last_error='planned_slot_expired_owner_review_required'
                WHERE content_id=?
                """,
                (suggested, card["content_id"]),
            )
        server = create_server(
            self.database_path, port=0, asset_root=Path(self.tempdir.name)
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            request = Request(
                f"{base}/api/reviews/{card['content_id']}/reschedule",
                method="POST",
            )
            with urlopen(request, timeout=5) as response:
                payload = json.load(response)
            self.assertEqual(payload["status"], "LOCAL_SCHEDULED")
            self.assertEqual(payload["planned_at"], suggested)
            self.assertFalse(payload["external_action"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
