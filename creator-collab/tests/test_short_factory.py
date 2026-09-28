from __future__ import annotations

import tempfile
import json
import threading
from pathlib import Path
from unittest import TestCase
from urllib.request import urlopen

from creator_ops.database import CreatorDatabase, utc_now
from creator_ops.short_factory import PIPELINE_STATES, ShortFactoryService
from creator_ops.web import create_server


class ShortFactoryTests(TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = CreatorDatabase(Path(self.temp.name) / "factory.db")
        self.db.initialize()
        now = utc_now()
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO creators
                    (slug, display_name, instagram_handle, niche, tone,
                     disclosure, active, created_at)
                VALUES ('leona-voss', 'Leona Voss', 'leonavoss.ai', 'Berlin',
                        'selbstbewusst und nahbar', 'Fiktive KI-Persona', 1, ?)
                """,
                (now,),
            )
        self.service = ShortFactoryService(self.db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def ingest(self) -> dict:
        return self.service.ingest_trend(
            platform="tiktok",
            source_url="https://www.tiktok.com/@reference/video/123",
            observed_at="2026-09-28T09:00:00+00:00",
            niche="urban lifestyle",
            source_summary="A short opens on an unresolved everyday choice.",
            evidence={"observed_fields": ["opening", "cuts", "cta"]},
            analysis={
                "hook_type": "open_loop",
                "tension_arc": "choice_then_payoff",
                "visual_rhythm": "three_fast_then_one_calm",
                "cta_pattern": "audience_choice",
                "format": "vertical_short",
                "duration_seconds": 22,
                "why_it_may_work": "The first frame creates a concrete question.",
            },
        )

    def test_trend_source_analysis_and_pattern_are_separate(self) -> None:
        result = self.ingest()
        brief = self.db.one("SELECT * FROM trend_briefs WHERE id=?", (result["brief_id"],))
        pattern = self.db.one("SELECT * FROM trend_patterns WHERE id=?", (result["pattern_id"],))

        self.assertTrue(result["source_separated_from_analysis"])
        self.assertIn("unresolved everyday choice", brief["source_summary"])
        self.assertEqual(pattern["hook_type"], "open_loop")
        self.assertNotIn(brief["source_summary"], pattern["analysis"])

    def test_builds_original_project_to_qa_ready_with_plan_only_media_job(self) -> None:
        trend = self.ingest()
        project = self.service.build_qa_ready(
            topic="Drei ehrliche Berlin-Morgenroutinen",
            audience="berufstätige Berlinerinnen",
            persona_slug="leona-voss",
            pattern_ids=[trend["pattern_id"]],
        )

        self.assertEqual(project["status"], "QA_READY")
        self.assertEqual(
            [event["new_status"] for event in project["events"]],
            list(PIPELINE_STATES[1:]),
        )
        self.assertIn("Berlin-Morgenroutinen", project["script"])
        self.assertNotIn("unresolved everyday choice", project["script"])
        self.assertEqual(project["media_job"]["provider"], "higgsfield")
        self.assertEqual(
            project["media_job"]["status"], "AWAITING_COST_CONFIRMATION"
        )
        self.assertEqual(project["media_job"]["cost_eur"], 0.0)
        repeated = self.service.build_qa_ready(
            topic="Drei ehrliche Berlin-Morgenroutinen",
            audience="berufstätige Berlinerinnen",
            persona_slug="leona-voss",
            pattern_ids=[trend["pattern_id"]],
        )
        self.assertEqual(repeated["id"], project["id"])
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM media_jobs"), 1)

    def test_learning_uses_real_windows_and_never_invents_zero(self) -> None:
        trend = self.ingest()
        project = self.service.build_qa_ready(
            topic="Berlin nach Feierabend",
            audience="urbane Berufstätige",
            persona_slug="leona-voss",
            pattern_ids=[trend["pattern_id"]],
        )
        now = utc_now()
        with self.db.transaction() as connection:
            creator_id = int(connection.execute("SELECT id FROM creators").fetchone()[0])
            series_id = int(connection.execute(
                "INSERT INTO series (creator_id,name,description,active,created_at) VALUES (?, 'Test', 'Test', 1, ?)",
                (creator_id, now),
            ).lastrowid)
            run_id = int(connection.execute(
                "INSERT INTO runs (run_key,creator_id,run_date,status,started_at,completed_at) VALUES ('run-test',?,'2026-09-28','COMPLETE',?,?)",
                (creator_id, now, now),
            ).lastrowid)
            content_id = int(connection.execute(
                """
                INSERT INTO content_items
                    (creator_id,series_id,run_id,run_key,title,idea,status,
                     safety_class,content_stage,visibility_scope,ai_generated,
                     adult,needs_ai_disclosure,approved,created_at,updated_at)
                VALUES (?,?,?,'content-test','Test Short','Test','PUBLISHED','SFW',
                        'ALLTAG','PUBLIC_SFW',1,0,1,1,?,?)
                """,
                (creator_id, series_id, run_id, now, now),
            ).lastrowid)
            variant_id = int(connection.execute(
                """
                INSERT INTO platform_variants
                    (content_id,platform,format,hook,caption,hashtags_json,cta,disclosure,created_at)
                VALUES (?,'instagram','reel','Hook','Caption','[]','CTA','AI',?)
                """,
                (content_id, now),
            ).lastrowid)
            publication_id = int(connection.execute(
                """
                INSERT INTO publications
                    (content_id,platform_variant_id,provider,scheduled_at,published_at,
                     external_id,external_url,status)
                VALUES (?,?,'instagram-meta-graph',?,?, 'media-1',
                        'https://www.instagram.com/reel/test/','PUBLISHED')
                """,
                (content_id, variant_id, now, now),
            ).lastrowid)
            connection.execute(
                """
                INSERT INTO manual_analytics_events
                    (publication_id,window_hours,captured_at,source,reach,views,
                     likes,comments,shares,saves,profile_visits,follows,link_clicks,
                     revenue,note)
                VALUES (?,24,?,'MANUAL_OWNER',120,150,8,2,3,4,1,NULL,NULL,NULL,'real')
                """,
                (publication_id, now),
            )
        self.service.link_publication(project["id"], publication_id)
        result = self.service.refresh_learning(project["id"])

        self.assertEqual(result["learning_rows_written"], 1)
        learned = self.db.one("SELECT * FROM pattern_learning")
        self.assertEqual(learned["window_hours"], 24)
        self.assertEqual(learned["decision"], "VARIATE")
        self.assertNotIn('"follows": 0', learned["metrics_json"])
        self.assertIn('"follows": null', learned["metrics_json"])

    def test_existing_dashboard_exposes_short_factory_status(self) -> None:
        trend = self.ingest()
        self.service.build_qa_ready(
            topic="Ein eigener Test-Short",
            audience="bestehende Community",
            persona_slug="leona-voss",
            pattern_ids=[trend["pattern_id"]],
        )
        server = create_server(
            self.db.path,
            port=0,
            asset_root=Path(self.temp.name),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/api/short-factory",
                timeout=3,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(payload["schema"], "zippoworkz-short-factory-v1")
        self.assertEqual(payload["by_status"]["QA_READY"], 1)
        self.assertEqual(payload["external_actions"], 0)
