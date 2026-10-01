from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creator_ops.database import CreatorDatabase, SCHEMA_VERSION
from creator_ops.instagram_dm_eventlog import record_bot_event


class InstagramDMOperationEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = CreatorDatabase(Path(self.tempdir.name) / "review.db")
        self.database.initialize()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_events_are_persona_scoped_metadata_not_a_second_message_ledger(self) -> None:
        mara_id = record_bot_event(
            self.database,
            persona="mara-field",
            account_id="178414000000002",
            action="DISPATCH_REPLY",
            job_id=42,
            provider_request_id="trace_123456",
            result="SUCCESS",
            retry_count=1,
        )
        record_bot_event(
            self.database,
            persona="leona-voss",
            account_id="178414000000001",
            action="PROVIDER_SYNC",
            result="SUCCESS",
        )
        row = self.database.one(
            "SELECT * FROM instagram_dm_operation_events WHERE id=?", (mara_id,)
        )
        self.assertEqual(row["persona"], "mara-field")
        self.assertEqual(row["account_id"], "178414000000002")
        self.assertEqual(row["job_id"], "42")
        self.assertEqual(row["provider_request_id"], "trace_123456")
        self.assertEqual(row["retry_count"], 1)
        self.assertEqual(row["result"], "SUCCESS")
        self.assertTrue(row["timestamp"].endswith("+00:00"))
        self.assertEqual(
            self.database.scalar(
                "SELECT COUNT(*) FROM instagram_dm_operation_events WHERE persona='leona-voss'"
            ),
            1,
        )
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM instagram_dm_events"), 0)
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM instagram_dm_outbox"), 0)

    def test_untrusted_details_are_redacted_or_discarded(self) -> None:
        record_bot_event(
            self.database,
            persona="wrong-persona",
            account_id="Bearer private-token",
            action="DISPATCH_REPLY",
            job_id="Bearer private-token",
            provider_request_id="sk-private-token",
            result="FAILED",
            error_code="Bearer private-token",
            error_summary="private DM text and token",
        )
        row = self.database.one("SELECT * FROM instagram_dm_operation_events")
        self.assertEqual(row["persona"], "UNKNOWN")
        self.assertIsNone(row["account_id"])
        self.assertIsNone(row["job_id"])
        self.assertIsNone(row["provider_request_id"])
        self.assertEqual(row["error_code"], "redacted_error")
        self.assertEqual(row["error_summary"], "redacted_error")
        self.assertNotIn("private-token", "|".join(str(value) for value in row))

    def test_error_summary_accepts_only_a_matching_safe_code(self) -> None:
        record_bot_event(
            self.database,
            persona="mara-field",
            action="PROVIDER_SYNC",
            result="RETRYING",
            retry_count=2,
            error_code="meta_graph_http_503",
            error_summary="meta_graph_http_503",
        )
        row = self.database.one("SELECT * FROM instagram_dm_operation_events")
        self.assertEqual(row["error_code"], "meta_graph_http_503")
        self.assertEqual(row["error_summary"], "meta_graph_http_503")

    def test_invalid_status_or_retry_does_not_write_an_event(self) -> None:
        with self.assertRaises(ValueError):
            record_bot_event(
                self.database, persona="mara-field", action="SEND", result="PUBLISHED"
            )
        with self.assertRaises(ValueError):
            record_bot_event(
                self.database,
                persona="mara-field",
                action="SEND",
                result="SUCCESS",
                retry_count=-1,
            )
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM instagram_dm_operation_events"), 0)

    def test_schema_8_database_migrates_additively(self) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO creators
                    (slug, display_name, instagram_handle, niche, tone,
                     disclosure, active, created_at)
                VALUES ('mara-field', 'Mara Field', 'mara.field.ai',
                        'test', 'test', 'AI', 1, '2026-10-01T00:00:00+00:00')
                """
            )
            connection.execute("DROP TABLE instagram_dm_operation_events")
            connection.execute("UPDATE schema_meta SET value='8' WHERE key='schema_version'")

        self.database.initialize()
        self.assertEqual(self.database.schema_version(), SCHEMA_VERSION)
        self.assertEqual(SCHEMA_VERSION, 9)
        self.assertEqual(
            self.database.scalar("SELECT instagram_handle FROM creators WHERE slug='mara-field'"),
            "mara.field.ai",
        )
        self.assertEqual(self.database.scalar("PRAGMA integrity_check"), "ok")
        self.assertEqual(len(self.database.all("PRAGMA foreign_key_check")), 0)


if __name__ == "__main__":
    unittest.main()
