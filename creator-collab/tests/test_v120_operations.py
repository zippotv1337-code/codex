from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
import zipfile
from datetime import date, datetime
from pathlib import Path
from urllib.request import urlopen

from creator_ops.archive import ArchiveService
from creator_ops.cli import build_pipeline
from creator_ops.reconcile import ManualInstagramService
from creator_ops.recovery import RecoveryBackupService
from creator_ops.web import create_server


class V120OperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "sample.json").write_text('{"safe": true}\n', encoding="utf-8")
        self.database_path = self.root / "data" / "review.db"
        self.pipeline = build_pipeline(self.database_path)
        self.pipeline.initialize()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_recovery_archives_are_valid_secret_free_and_never_delete(self) -> None:
        self.pipeline.run_both(date(2026, 9, 4))
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE platform_accounts SET secret_reference='never-export-this' WHERE id=1"
            )
        service = RecoveryBackupService(self.pipeline.db, self.root)
        weekly = service.build(
            self.root / "backups", kind="weekly", now=datetime(2026, 9, 6, 3, 0)
        )
        monthly = service.build(
            self.root / "backups", kind="monthly", now=datetime(2026, 9, 1, 3, 30)
        )
        self.assertRegex(weekly.name, r"^Backup_Woche_KW36_2026_20260906-0300\.zip$")
        self.assertRegex(monthly.name, r"^Backup_Monat_2026-09_FULL_20260901-0330\.zip$")
        self.assertTrue(weekly.exists() and monthly.exists())
        with zipfile.ZipFile(weekly) as archive:
            self.assertIn("MANIFEST.json", archive.namelist())
            self.assertIn("SHA256SUMS.txt", archive.namelist())
            target = self.root / "restored.db"
            target.write_bytes(archive.read("recovery/creator_ops.db"))
        connection = sqlite3.connect(target)
        try:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertIsNone(connection.execute("SELECT secret_reference FROM platform_accounts WHERE id=1").fetchone()[0])
        finally:
            connection.close()
        self.assertEqual(service.validate(weekly)["path"], str(weekly))

    def test_native_reconcile_is_idempotent_and_analytics_append_only(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 4))
        service = ManualInstagramService(self.pipeline.db)
        first = service.reconcile(
            creator_slug="leona-voss",
            content_id=result.content_id,
            external_url="https://www.instagram.com/leonavoss.ai/p/Example123/",
            published_at="2026-09-04T19:30:00+02:00",
            asset_id=self.pipeline.db.scalar(
                "SELECT id FROM assets WHERE content_id=? AND pose_slot='FULL_BODY_ACTION'",
                (result.content_id,),
            ),
        )
        second = service.reconcile(
            creator_slug="leona-voss",
            content_id=result.content_id,
            external_url="https://www.instagram.com/leonavoss.ai/p/Example123/",
            published_at="2026-09-04T19:30:00+02:00",
        )
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(first["publication_id"], second["publication_id"])
        self.assertEqual(
            self.pipeline.db.scalar(
                "SELECT COUNT(*) FROM assets WHERE content_id=? AND published_status='PUBLISHED' AND is_top_pick=1",
                (result.content_id,),
            ),
            0,
        )
        self.assertEqual(
            self.pipeline.db.scalar(
                "SELECT COUNT(*) FROM engagement_queue WHERE publication_id=?",
                (first["publication_id"],),
            ),
            2,
        )
        service.append_analytics(first["publication_id"], 24, reach=100, likes=10)
        service.append_analytics(first["publication_id"], 24, reach=120, likes=14)
        self.assertEqual(self.pipeline.db.scalar("SELECT COUNT(*) FROM manual_analytics_events"), 2)
        archive = ArchiveService(self.pipeline.db).list()
        self.assertEqual(len(archive), 1)
        self.assertEqual(archive[0]["provider"], "instagram-native-manual")
        self.assertEqual(archive[0]["analytics"][0]["reach"], 120)
        ranking = ArchiveService(self.pipeline.db).top3()
        self.assertTrue(ranking["overall"][0]["uses_rates"])

    def test_initialize_preserves_explicit_missing_disclosure_on_historic_post(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 4))
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE content_items SET approved=1 WHERE id=?", (result.content_id,)
            )
        publication = ManualInstagramService(self.pipeline.db).reconcile(
            creator_slug="leona-voss",
            content_id=result.content_id,
            external_url="https://www.instagram.com/leonavoss.ai/p/NoDisclosure/",
            published_at="2026-09-04T19:30:00+02:00",
            ai_disclosure=False,
        )

        self.pipeline.db.initialize()

        self.assertEqual(
            self.pipeline.db.scalar(
                "SELECT ai_disclosure FROM publications WHERE id=?",
                (publication["publication_id"],),
            ),
            0,
        )

    def test_invalid_window_and_instagram_url_are_rejected(self) -> None:
        result = self.pipeline.run("mara-field", date(2026, 9, 4))
        service = ManualInstagramService(self.pipeline.db)
        with self.assertRaises(ValueError):
            service.reconcile(
                creator_slug="mara-field",
                content_id=result.content_id,
                external_url="https://example.com/not-instagram",
                published_at="2026-09-04T19:30:00+02:00",
            )
        with self.assertRaises(ValueError):
            service.append_analytics(99, 12, likes=1)

    def test_top3_distinguishes_missing_analytics_from_observed_zero_values(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 4))
        service = ManualInstagramService(self.pipeline.db)
        publication = service.reconcile(
            creator_slug="leona-voss",
            content_id=result.content_id,
            external_url="https://www.instagram.com/leonavoss.ai/p/ObservedZero/",
            published_at="2026-09-04T19:30:00+02:00",
        )
        archive = ArchiveService(self.pipeline.db)
        missing = archive.top3()
        self.assertEqual(missing["overall"], [])
        self.assertEqual(missing["by_persona"], {})
        self.assertEqual(len(missing["unranked"]), 1)
        self.assertEqual(missing["unranked"][0]["id"], publication["publication_id"])
        self.assertIsNone(missing["unranked"][0]["ranking_score"])
        self.assertEqual(missing["unranked"][0]["ranking_status"], "INSUFFICIENT_DATA")

        service.append_analytics(
            publication["publication_id"], 24, reach=0, views=0, likes=0,
            comments=0, shares=0, saves=0, profile_visits=0, follows=0,
            link_clicks=0,
        )
        observed = archive.top3()
        self.assertEqual(observed["unranked"], [])
        self.assertEqual(len(observed["overall"]), 1)
        ranked = observed["overall"][0]
        self.assertEqual(ranked["id"], publication["publication_id"])
        self.assertEqual(ranked["ranking_score"], 0)
        self.assertEqual(ranked["ranking_status"], "RANKED")
        self.assertFalse(ranked["uses_rates"])
        self.assertEqual(observed["by_persona"]["leona-voss"], [ranked])

    def test_archive_preview_prefers_published_asset_over_remaining_top_picks(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 4))
        published_asset_id = self.pipeline.db.scalar(
            "SELECT id FROM assets WHERE content_id=? AND pose_slot='FULL_BODY_ACTION'",
            (result.content_id,),
        )
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE assets SET generator='local-import' WHERE content_id=?",
                (result.content_id,),
            )
        ManualInstagramService(self.pipeline.db).reconcile(
            creator_slug="leona-voss",
            content_id=result.content_id,
            external_url="https://www.instagram.com/leonavoss.ai/p/PublishedPreview/",
            published_at="2026-09-04T19:30:00+02:00",
            asset_id=published_asset_id,
        )
        item = ArchiveService(self.pipeline.db).list()[0]
        published = item["assets"][0]
        self.assertEqual(published["id"], published_asset_id)
        self.assertEqual(published["published_status"], "PUBLISHED")
        self.assertFalse(published["is_top_pick"])
        remaining_top_picks = [asset for asset in item["assets"][1:] if asset["is_top_pick"]]
        self.assertEqual(len(remaining_top_picks), 3)
        self.assertTrue(all(asset["published_status"] == "UNPUBLISHED" for asset in remaining_top_picks))
        first_preview = next(asset["preview_url"] for asset in item["assets"] if asset["preview_url"])
        self.assertEqual(first_preview, f"/api/assets/{published_asset_id}/preview")

    def test_real_seven_day_analytics_take_priority_for_prime_time(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 4))
        service = ManualInstagramService(self.pipeline.db)
        publication = service.reconcile(
            creator_slug="leona-voss",
            content_id=result.content_id,
            external_url="https://www.instagram.com/leonavoss.ai/p/PrimeReal/",
            published_at="2026-09-04T20:30:00+02:00",
        )
        service.append_analytics(
            publication["publication_id"], 168, reach=1000, shares=100, saves=100, follows=50
        )
        creator_id = self.pipeline.db.scalar("SELECT id FROM creators WHERE slug='leona-voss'")
        with self.pipeline.db.transaction() as connection:
            decision = self.pipeline.scheduler.choose(
                connection, creator_id, date(2026, 9, 11), "instagram", "carousel"
            )
        self.assertEqual(decision.local_time, "20:30")
        self.assertEqual(decision.source, "analytics-history")

    def test_dashboard_sources_expose_archive_and_top3_navigation(self) -> None:
        dashboard = Path(__file__).resolve().parents[1] / "dashboard"
        for page in ("index.html", "archive.html", "top3.html", "engagement.html"):
            text = (dashboard / page).read_text(encoding="utf-8")
            self.assertIn('href="/archive"', text)
            self.assertIn('href="/top3"', text)
            self.assertIn('href="/engagement"', text)

    def test_archive_and_top3_http_endpoints_default_to_real(self) -> None:
        result = self.pipeline.run("leona-voss", date(2026, 9, 4))
        ManualInstagramService(self.pipeline.db).reconcile(
            creator_slug="leona-voss",
            content_id=result.content_id,
            external_url="https://www.instagram.com/leonavoss.ai/p/HttpExample/",
            published_at="2026-09-04",
        )
        server = create_server(self.database_path, port=0, asset_root=self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(f"{base}/api/archive", timeout=5) as response:
                archive = json.load(response)
            with urlopen(f"{base}/api/top3", timeout=5) as response:
                top3 = json.load(response)
            with urlopen(f"{base}/api/engagement", timeout=5) as response:
                engagement = json.load(response)
            self.assertEqual(len(archive["items"]), 1)
            self.assertFalse(archive["items"][0]["is_mock"])
            self.assertEqual(top3["mode"], "real")
            self.assertEqual(top3["overall"], [])
            self.assertEqual(top3["by_persona"], {})
            self.assertEqual(len(top3["unranked"]), 1)
            self.assertEqual(top3["unranked"][0]["id"], archive["items"][0]["id"])
            self.assertEqual(top3["unranked"][0]["ranking_status"], "INSUFFICIENT_DATA")
            self.assertEqual(engagement["execution"], "proposal-only")
            self.assertEqual(len(engagement["items"]), 2)
            for item in engagement["items"]:
                self.assertFalse(item["reaction_data_known"])
                self.assertFalse(item["comment_texts_available"])
                self.assertEqual(item["reply_drafts"], [])
                self.assertIn("nichts erfinden", item["action_recommendation"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
