from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.curation import qa_assets, select_diverse_top_picks
from creator_ops.database import CreatorDatabase, SCHEMA, utc_now
from creator_ops.models import (
    ComplianceInput,
    ContentStage,
    PoseSlot,
    SafetyClass,
    VisibilityScope,
)
from creator_ops.pipeline import check_compliance
from creator_ops.review import ReviewDashboardService


class ContentSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tempdir.name) / "creator-ops.db"
        self.pipeline = build_pipeline(self.database_path)
        self.pipeline.initialize()
        self.review = ReviewDashboardService(self.pipeline)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_compliance_matrix_keeps_adult_content_off_public_platforms(self) -> None:
        local_adult = check_compliance(
            ComplianceInput(
                platform="local-vault",
                safety_class=SafetyClass.ADULT,
                content_stage=ContentStage.ADULT_18,
                visibility_scope=VisibilityScope.ADULT_ONLY,
                ai_generated=True,
                needs_ai_disclosure=True,
                disclosure_present=True,
                rights_status="AI_GENERATED",
            )
        )
        public_adult = check_compliance(
            ComplianceInput(
                platform="instagram",
                safety_class=SafetyClass.ADULT,
                content_stage=ContentStage.ADULT_18,
                visibility_scope=VisibilityScope.ADULT_ONLY,
                ai_generated=True,
                needs_ai_disclosure=True,
                disclosure_present=True,
                rights_status="AI_GENERATED",
            )
        )
        public_teaser = check_compliance(
            ComplianceInput(
                platform="instagram",
                safety_class=SafetyClass.SFW,
                content_stage=ContentStage.TEASER,
                visibility_scope=VisibilityScope.PUBLIC_SFW,
                ai_generated=True,
                needs_ai_disclosure=True,
                disclosure_present=True,
                rights_status="AI_GENERATED",
            )
        )

        self.assertTrue(local_adult.allowed)
        self.assertFalse(public_adult.allowed)
        self.assertIn("public_platform_requires_public_sfw_visibility", public_adult.reasons)
        self.assertTrue(public_teaser.allowed)

    def test_sqlite_guards_reject_mismatched_stage_safety_and_visibility(self) -> None:
        card = self.review.ensure_date(date(2026, 9, 7))[0]
        with self.assertRaisesRegex(sqlite3.IntegrityError, "content_stage_safety_visibility_mismatch"):
            with self.pipeline.db.transaction() as connection:
                connection.execute(
                    "UPDATE content_items SET safety_class = 'ADULT' WHERE id = ?",
                    (card["content_id"],),
                )

        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                UPDATE content_items
                SET content_stage = 'ADULT_18', safety_class = 'ADULT',
                    visibility_scope = 'ADULT_ONLY', adult = 1
                WHERE id = ?
                """,
                (card["content_id"],),
            )
            connection.execute(
                """
                UPDATE assets
                SET content_stage = 'ADULT_18', safety_class = 'ADULT',
                    visibility_scope = 'ADULT_ONLY'
                WHERE content_id = ?
                """,
                (card["content_id"],),
            )

        with self.assertRaisesRegex(sqlite3.IntegrityError, "asset_content_scope_mismatch"):
            with self.pipeline.db.transaction() as connection:
                connection.execute(
                    "UPDATE assets SET visibility_scope = 'PUBLIC_SFW' WHERE content_id = ?",
                    (card["content_id"],),
                )

        protected_card = self.review.cards(date(2026, 9, 7))[0]
        self.assertTrue(protected_card["privacy_blur"])
        self.assertFalse(protected_card["checks"]["public_scope"])
        self.assertFalse(protected_card["ready"])

        with self.assertRaisesRegex(ValueError, "public_platform_requires_public_sfw_visibility"):
            self.review.approve(card["content_id"])

    def test_weighted_top_three_enforces_pose_and_similarity_diversity(self) -> None:
        card = self.review.ensure_date(date(2026, 9, 8))[0]
        with self.pipeline.db.transaction() as connection:
            rows = connection.execute(
                "SELECT id FROM assets WHERE content_id = ? ORDER BY id",
                (card["content_id"],),
            ).fetchall()
            for index, row in enumerate(rows):
                connection.execute(
                    """
                    UPDATE assets
                    SET similarity_group = ?, quality_score = ?, novelty_score = ?
                    WHERE id = ?
                    """,
                    ("portrait" if index < 2 else f"variety-{index}", 0.99 - index * 0.08, 0.4 + index * 0.1, row["id"]),
                )
            selected = select_diverse_top_picks(connection, card["content_id"])
            selected_rows = connection.execute(
                "SELECT pose_slot, similarity_group FROM assets WHERE is_top_pick = 1 AND content_id = ?",
                (card["content_id"],),
            ).fetchall()
            all_rows = connection.execute(
                "SELECT * FROM assets WHERE content_id = ? ORDER BY id",
                (card["content_id"],),
            ).fetchall()

        self.assertEqual(len(selected), 3)
        self.assertEqual(len({row["pose_slot"] for row in selected_rows}), 3)
        self.assertLessEqual(
            sum(row["similarity_group"] == "portrait" for row in selected_rows),
            2,
        )
        self.assertTrue(
            {row["pose_slot"] for row in selected_rows}
            & {PoseSlot.FULL_BODY_ACTION.value, PoseSlot.CANDID.value}
        )
        self.assertTrue(qa_assets(all_rows).ready)

        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                UPDATE assets SET similarity_group = 'too-similar'
                WHERE id IN (
                    SELECT id FROM assets WHERE content_id = ? ORDER BY id LIMIT 3
                )
                """,
                (card["content_id"],),
            )
            invalid_rows = connection.execute(
                "SELECT * FROM assets WHERE content_id = ? ORDER BY id",
                (card["content_id"],),
            ).fetchall()
        self.assertIn("too_many_similar_assets", qa_assets(invalid_rows).reasons)

    def test_initialize_repairs_asset_plan_without_changing_existing_top_order(self) -> None:
        card = self.review.ensure_date(date(2026, 9, 9))[0]
        rows = self.pipeline.db.all(
            "SELECT id FROM assets WHERE content_id=? ORDER BY id",
            (card["content_id"],),
        )
        asset_ids = [row["id"] for row in rows]
        expected_top_order = [asset_ids[3], asset_ids[0], asset_ids[4]]

        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "UPDATE assets SET is_top_pick=0, published_status='UNPUBLISHED' WHERE content_id=?",
                (card["content_id"],),
            )
            for priority, asset_id in enumerate(expected_top_order, start=1):
                connection.execute(
                    "UPDATE assets SET is_top_pick=1 WHERE id=?",
                    (asset_id,),
                )
                connection.execute(
                    """
                    UPDATE asset_usage_plan
                    SET role='RESERVE', priority=?, status='READY', trigger_reason='stale test plan'
                    WHERE content_id=? AND asset_id=?
                    """,
                    (priority, card["content_id"], asset_id),
                )
            connection.execute(
                "UPDATE assets SET is_top_pick=1, published_status='PUBLISHED' WHERE id=?",
                (asset_ids[1],),
            )
            connection.execute(
                """
                UPDATE asset_usage_plan
                SET role='PRIMARY', priority=4, status='READY', trigger_reason='stale published plan'
                WHERE content_id=? AND asset_id=?
                """,
                (card["content_id"], asset_ids[1]),
            )

        self.pipeline.db.initialize()
        repaired = self.pipeline.db.all(
            """
            SELECT p.asset_id, p.role, p.priority, p.status, a.published_status
            FROM asset_usage_plan p
            JOIN assets a ON a.id=p.asset_id
            WHERE p.content_id=?
            ORDER BY p.priority, p.asset_id
            """,
            (card["content_id"],),
        )
        active = [row for row in repaired if row["asset_id"] in expected_top_order]
        self.assertEqual([row["asset_id"] for row in active], expected_top_order)
        self.assertEqual([row["role"] for row in active], ["PRIMARY", "ALTERNATE", "ALTERNATE"])
        self.assertEqual([row["priority"] for row in active], [1, 2, 3])
        published = next(row for row in repaired if row["asset_id"] == asset_ids[1])
        self.assertEqual((published["role"], published["status"]), ("RESERVE", "PUBLISHED_USED"))
        reserves = [
            row for row in repaired
            if row["asset_id"] not in {*expected_top_order, asset_ids[1]}
        ]
        self.assertTrue(all(row["role"] == "RESERVE" for row in reserves))

        snapshot = [tuple(row) for row in repaired]
        self.pipeline.db.initialize()
        self.assertEqual(
            snapshot,
            [
                tuple(row)
                for row in self.pipeline.db.all(
                    """
                    SELECT p.asset_id, p.role, p.priority, p.status, a.published_status
                    FROM asset_usage_plan p
                    JOIN assets a ON a.id=p.asset_id
                    WHERE p.content_id=?
                    ORDER BY p.priority, p.asset_id
                    """,
                    (card["content_id"],),
                )
            ],
        )


class AdditiveMigrationTests(unittest.TestCase):
    def test_legacy_rows_are_migrated_without_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "legacy.db"
            legacy_schema = SCHEMA
            for line in (
                "    content_stage TEXT NOT NULL DEFAULT 'ALLTAG',\n",
                "    visibility_scope TEXT NOT NULL DEFAULT 'PUBLIC_SFW',\n",
                "    pose_slot TEXT NOT NULL DEFAULT 'UNASSIGNED',\n",
                "    similarity_group TEXT NOT NULL DEFAULT '',\n",
                "    stage_fit_score REAL NOT NULL DEFAULT 1,\n",
                "    novelty_score REAL NOT NULL DEFAULT 0.5,\n",
            ):
                legacy_schema = legacy_schema.replace(line, "")

            connection = sqlite3.connect(path)
            try:
                connection.executescript(legacy_schema)
                now = utc_now()
                creator_id = connection.execute(
                    """
                    INSERT INTO creators
                        (slug, display_name, instagram_handle, niche, tone, disclosure, created_at)
                    VALUES ('legacy', 'Legacy', 'legacy.ai', 'test', 'test', 'AI', ?)
                    """,
                    (now,),
                ).lastrowid
                series_id = connection.execute(
                    """
                    INSERT INTO series (creator_id, name, description, created_at)
                    VALUES (?, 'Legacy', 'Legacy', ?)
                    """,
                    (creator_id, now),
                ).lastrowid
                run_id = connection.execute(
                    """
                    INSERT INTO runs (run_key, creator_id, run_date, status, started_at)
                    VALUES ('legacy-run', ?, '2026-09-01', 'COMPLETE', ?)
                    """,
                    (creator_id, now),
                ).lastrowid
                content_id = connection.execute(
                    """
                    INSERT INTO content_items
                        (creator_id, series_id, run_id, run_key, title, idea, status,
                         safety_class, ai_generated, adult, needs_ai_disclosure,
                         approved, created_at, updated_at)
                    VALUES (?, ?, ?, 'legacy-content', 'Legacy', 'Legacy', 'PLANNED',
                            'ADULT', 1, 1, 1, 0, ?, ?)
                    """,
                    (creator_id, series_id, run_id, now, now),
                ).lastrowid
                connection.execute(
                    """
                    INSERT INTO assets
                        (asset_id, creator_id, content_id, series_id, asset_type,
                         safety_class, status, file_path, reference_version,
                         prompt_version, generator, created_at, estimated_cost,
                         rights_status, platform_allowed, published_status,
                         perceptual_hash, quality_score, persona_fit_score,
                         coherence_score, is_top_pick)
                    VALUES ('legacy-asset', ?, ?, ?, 'image', 'ADULT', 'GENERATED',
                            'legacy.png', 'v1', 'v1', 'legacy', ?, 0, 'OWNED',
                            'adult-only', 'UNPUBLISHED', 'legacy-hash', .8, .8, .8, 0)
                    """,
                    (creator_id, content_id, series_id, now),
                )
                connection.commit()
            finally:
                connection.close()

            database = CreatorDatabase(path)
            database.initialize()
            content = database.one(
                "SELECT content_stage, visibility_scope FROM content_items WHERE id = ?",
                (content_id,),
            )
            asset = database.one(
                "SELECT content_stage, visibility_scope, pose_slot FROM assets WHERE content_id = ?",
                (content_id,),
            )

            self.assertEqual(database.schema_version(), 5)
            self.assertEqual(tuple(content), ("ADULT_18", "ADULT_ONLY"))
            self.assertEqual(tuple(asset), ("ADULT_18", "ADULT_ONLY", "FRONTAL"))


if __name__ == "__main__":
    unittest.main()
