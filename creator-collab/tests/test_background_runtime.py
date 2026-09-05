from __future__ import annotations

import tempfile
import threading
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from creator_ops.background import BackgroundCoordinator, COMPLETE, WAITING_FOR_CAPACITY
from creator_ops.database import CreatorDatabase


class BackgroundRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.database = CreatorDatabase(self.root / "runtime.db")
        self.database.initialize()
        self.runtime = BackgroundCoordinator(self.database, self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_complete_run_is_idempotent_and_writes_structured_state_and_journal(self) -> None:
        calls: list[str] = []
        first = self.runtime.run_once("daily:1", "safe-task", lambda: calls.append("x") or {"ok": True})
        second = self.runtime.run_once("daily:1", "safe-task", lambda: calls.append("y") or {})
        self.assertEqual(first.status, COMPLETE)
        self.assertTrue(second.reused)
        self.assertEqual(calls, ["x"])
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM runtime_events"), 2)
        journal = self.root / "sessions" / "runtime" / "daily-1.md"
        self.assertIn("`COMPLETE`", journal.read_text(encoding="utf-8"))

    def test_waiting_for_capacity_persists_resume_time_without_running_task(self) -> None:
        now = datetime(2026, 9, 5, 8, tzinfo=UTC)
        result = self.runtime.run_once(
            "capacity:1",
            "safe-task",
            lambda: self.fail("task must not run"),
            capacity_available=False,
            now=now,
            next_capacity_at=now + timedelta(hours=3),
        )
        self.assertEqual(result.status, WAITING_FOR_CAPACITY)
        self.assertEqual(result.next_run_at, (now + timedelta(hours=3)).isoformat())
        self.assertEqual(self.runtime.health(now)["waiting_for_capacity"], 1)

        calls: list[str] = []
        early = self.runtime.run_once(
            "capacity:1",
            "safe-task",
            lambda: calls.append("too-early") or {},
            now=now + timedelta(hours=1),
        )
        self.assertTrue(early.reused)
        self.assertEqual(early.status, WAITING_FOR_CAPACITY)
        self.assertEqual(calls, [])

        resumed = self.runtime.run_once(
            "capacity:1",
            "safe-task",
            lambda: calls.append("resumed") or {"ok": True},
            now=now + timedelta(hours=3),
        )
        self.assertEqual(resumed.status, COMPLETE)
        self.assertEqual(calls, ["resumed"])

    def test_active_lease_blocks_and_stale_lease_is_recovered(self) -> None:
        now = datetime(2026, 9, 5, 8, tzinfo=UTC)
        token = self.runtime._acquire(now)
        try:
            with self.assertRaisesRegex(RuntimeError, "background_run_already_active"):
                self.runtime._acquire(now + timedelta(minutes=1))
        finally:
            self.runtime._release(token)
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO run_leases VALUES
                    ('creator-ops-autopilot','dead','2026-09-05T06:00:00+00:00',
                     '2026-09-05T06:00:00+00:00','2026-09-05T06:15:00+00:00')
                """
            )
        recovered = self.runtime._acquire(now)
        self.runtime._release(recovered)
        self.assertEqual(
            self.database.scalar("SELECT COUNT(*) FROM runtime_events WHERE event_type='STALE_LEASE_RECOVERED'"),
            1,
        )

    def test_long_task_renews_lease_and_prevents_takeover(self) -> None:
        runtime = BackgroundCoordinator(
            self.database,
            self.root,
            lease_ttl=timedelta(milliseconds=150),
        )
        competitor = BackgroundCoordinator(
            self.database,
            self.root,
            lease_ttl=timedelta(milliseconds=150),
        )
        started = threading.Event()
        release = threading.Event()
        result: list[object] = []

        def task() -> dict[str, bool]:
            started.set()
            release.wait(timeout=2)
            return {"ok": True}

        thread = threading.Thread(
            target=lambda: result.append(runtime.run_once("long:1", "long-task", task)),
            daemon=True,
        )
        thread.start()
        self.assertTrue(started.wait(timeout=2))
        time.sleep(0.35)
        with self.assertRaisesRegex(RuntimeError, "background_run_already_active"):
            competitor._acquire(datetime.now(UTC))
        release.set()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result[0].status, COMPLETE)

    def test_lost_owner_cannot_mark_run_complete(self) -> None:
        runtime = BackgroundCoordinator(
            self.database,
            self.root,
            lease_ttl=timedelta(seconds=5),
        )

        def steal_lease() -> dict[str, bool]:
            now = datetime.now(UTC)
            with self.database.transaction() as connection:
                connection.execute(
                    "DELETE FROM run_leases WHERE lease_name=?",
                    (runtime.lease_name,),
                )
                connection.execute(
                    """
                    INSERT INTO run_leases
                        (lease_name, owner_token, acquired_at, heartbeat_at, expires_at)
                    VALUES (?, 'new-owner', ?, ?, ?)
                    """,
                    (
                        runtime.lease_name,
                        now.isoformat(),
                        now.isoformat(),
                        (now + timedelta(minutes=1)).isoformat(),
                    ),
                )
            return {"ok": True}

        with self.assertRaisesRegex(RuntimeError, "background_lease_lost"):
            runtime.run_once("stolen:1", "safe-task", steal_lease)
        self.assertNotEqual(
            self.database.scalar(
                "SELECT status FROM background_runs WHERE run_key='stolen:1'"
            ),
            COMPLETE,
        )

    def test_health_reports_blocked_and_orphaned_runs(self) -> None:
        now = datetime.now(UTC)
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO background_runs
                    (run_key, task_name, status, current_step, cursor_json,
                     attempts, started_at, updated_at)
                VALUES ('blocked:1','blocked-task','BLOCKED','RESUME','{}',1,?,?)
                """,
                (now.isoformat(), now.isoformat()),
            )
            connection.execute(
                """
                INSERT INTO background_runs
                    (run_key, task_name, status, current_step, cursor_json,
                     attempts, started_at, updated_at)
                VALUES ('orphan:1','orphan-task','RUNNING','RESUME','{}',1,?,?)
                """,
                (now.isoformat(), now.isoformat()),
            )
        health = self.runtime.health(now)
        self.assertEqual(health["status"], "degraded")
        self.assertEqual(health["blocked"], 1)
        self.assertEqual(health["orphaned_running"], 1)


if __name__ == "__main__":
    unittest.main()
