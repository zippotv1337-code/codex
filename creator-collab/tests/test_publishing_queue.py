from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from creator_ops.cli import build_pipeline
from creator_ops.publishing import (
    BLOCKED_EXTERNAL_PUBLISHING,
    FAILED_RETRYABLE,
    LOCAL_SCHEDULED,
    NEEDS_RESCHEDULE_REVIEW,
    PUBLISHED,
    DispatchResult,
    PublishQueueService,
)
from creator_ops.review import ReviewDashboardService


class SuccessfulIdempotentAdapter:
    provider = "instagram-official-test"
    available = True

    def __init__(self) -> None:
        self.calls: list[str] = []

    def publish(self, publication_id: int, content_id: int, idempotency_key: str) -> DispatchResult:
        self.calls.append(idempotency_key)
        return DispatchResult(
            status=PUBLISHED,
            external_id=f"official-{idempotency_key[:12]}",
            external_url=f"https://www.instagram.com/p/{idempotency_key[:12]}/",
        )


class RetryOnceAdapter(SuccessfulIdempotentAdapter):
    def publish(self, publication_id: int, content_id: int, idempotency_key: str) -> DispatchResult:
        self.calls.append(idempotency_key)
        if len(self.calls) == 1:
            raise TimeoutError("temporary")
        return DispatchResult(
            status=PUBLISHED,
            external_id=f"official-{idempotency_key[:12]}",
            external_url=f"https://www.instagram.com/p/{idempotency_key[:12]}/",
        )


class PublishQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pipeline = build_pipeline(self.root / "review.db")
        self.pipeline.initialize()
        self.review = ReviewDashboardService(self.pipeline)
        self.card = self.review.ensure_date(date(2026, 9, 8))[0]

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _approve(self) -> dict:
        return self.review.approve(self.card["content_id"])

    def test_owner_approval_creates_one_local_queue_job(self) -> None:
        result = self._approve()
        jobs = PublishQueueService(self.pipeline.db).list()
        self.assertEqual(result["schedule_status"], LOCAL_SCHEDULED)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["status"], LOCAL_SCHEDULED)
        self.assertEqual(jobs[0]["timezone"], "Europe/Berlin")
        self.assertEqual(self.review.approve(self.card["content_id"])["reused"], True)
        self.assertEqual(len(PublishQueueService(self.pipeline.db).list()), 1)

    def test_startup_reconcile_is_idempotent_and_missed_slots_need_review(self) -> None:
        self._approve()
        service = PublishQueueService(self.pipeline.db)
        planned = datetime.fromisoformat(service.list()[0]["planned_at"])
        first = service.reconcile(planned + timedelta(hours=1))
        second = service.reconcile(planned + timedelta(hours=1))
        job = service.list()[0]
        self.assertEqual(first["needs_reschedule_review"], 1)
        self.assertEqual(second["needs_reschedule_review"], 0)
        self.assertEqual(job["status"], NEEDS_RESCHEDULE_REVIEW)
        self.assertIsNotNone(job["suggested_at"])
        publication = self.pipeline.db.one(
            "SELECT schedule_status, schedule_error FROM publications WHERE id=?",
            (job["publication_id"],),
        )
        self.assertEqual(publication["schedule_status"], NEEDS_RESCHEDULE_REVIEW)
        self.assertEqual(
            publication["schedule_error"],
            "planned_slot_expired_owner_review_required",
        )

    def test_owner_can_accept_future_reschedule_suggestion_once(self) -> None:
        self._approve()
        service = PublishQueueService(self.pipeline.db)
        original = service.list()[0]
        planned = datetime.fromisoformat(original["planned_at"])
        service.reconcile(planned + timedelta(hours=1))
        suggested = service.list()[0]["suggested_at"]

        result = service.accept_suggested_reschedule(
            self.card["content_id"], planned + timedelta(hours=1)
        )
        updated = service.list()[0]

        self.assertEqual(result["status"], LOCAL_SCHEDULED)
        self.assertEqual(result["planned_at"], suggested)
        self.assertFalse(result["external_action"])
        self.assertEqual(updated["status"], LOCAL_SCHEDULED)
        self.assertIsNone(updated["suggested_at"])
        # Rescheduling is the same approved publication attempt. Keeping the
        # key ensures a durable intent/receipt can never be bypassed by moving
        # the local slot.
        self.assertEqual(updated["queue_key"], original["queue_key"])
        self.assertEqual(
            self.pipeline.db.scalar(
                "SELECT COUNT(*) FROM review_events WHERE action='OWNER_RESCHEDULED_UI'"
            ),
            1,
        )
        with self.assertRaisesRegex(ValueError, "reschedule_review_not_required"):
            service.accept_suggested_reschedule(
                self.card["content_id"], planned + timedelta(hours=1)
            )

    def test_stale_publishing_claim_blocks_without_rekey_or_automatic_retry(self) -> None:
        self._approve()
        service = PublishQueueService(self.pipeline.db)
        original = service.list()[0]
        planned = datetime.fromisoformat(original["planned_at"])
        stale_at = planned.astimezone(UTC) - timedelta(hours=1)
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                UPDATE publish_queue
                SET status=?, attempts=1, updated_at=?
                WHERE id=?
                """,
                ("PUBLISHING", stale_at.isoformat(), original["id"]),
            )

        service.reconcile(planned + timedelta(hours=1))
        blocked = service.list()[0]

        self.assertEqual(blocked["status"], BLOCKED_EXTERNAL_PUBLISHING)
        self.assertEqual(blocked["queue_key"], original["queue_key"])
        self.assertEqual(
            blocked["last_error"],
            "stale_publishing_claim_owner_reconcile_required",
        )
        self.assertIsNone(blocked["suggested_at"])
        self.assertIsNone(blocked["next_attempt_at"])
        with self.assertRaisesRegex(ValueError, "manual_reconcile"):
            service.rearm_blocked_preflight(
                self.card["content_id"], planned + timedelta(hours=1)
            )
        with self.assertRaisesRegex(ValueError, "reschedule_review_not_required"):
            service.accept_suggested_reschedule(
                self.card["content_id"], planned + timedelta(hours=1)
            )

    def test_due_without_official_adapter_is_honestly_blocked(self) -> None:
        self._approve()
        service = PublishQueueService(self.pipeline.db)
        planned = datetime.fromisoformat(service.list()[0]["planned_at"])
        summary = service.dispatch_due(planned + timedelta(minutes=1))
        self.assertEqual(summary["blocked"], 1)
        self.assertEqual(service.list()[0]["status"], BLOCKED_EXTERNAL_PUBLISHING)
        publication = self.pipeline.db.one(
            "SELECT external_id, schedule_status FROM publications WHERE content_id=?",
            (self.card["content_id"],),
        )
        self.assertIsNone(publication["external_id"])
        self.assertEqual(publication["schedule_status"], BLOCKED_EXTERNAL_PUBLISHING)
        service.reconcile(planned + timedelta(minutes=2))
        preserved = self.pipeline.db.one(
            "SELECT schedule_status, schedule_error FROM publications WHERE content_id=?",
            (self.card["content_id"],),
        )
        self.assertEqual(preserved["schedule_status"], BLOCKED_EXTERNAL_PUBLISHING)
        self.assertEqual(
            preserved["schedule_error"],
            "official_instagram_adapter_not_configured",
        )

    def test_owner_can_rearm_only_a_safe_preflight_block(self) -> None:
        self._approve()
        service = PublishQueueService(self.pipeline.db)
        planned = datetime.fromisoformat(service.list()[0]["planned_at"])
        service.dispatch_due(planned + timedelta(minutes=1))
        authorization = service.authorize_live_publish(self.card["content_id"])
        self.assertTrue(authorization["live_publish_authorized"])
        self.assertEqual(
            authorization["schedule_status"], BLOCKED_EXTERNAL_PUBLISHING
        )

        safe = service.rearm_blocked_preflight(
            self.card["content_id"], planned - timedelta(minutes=5)
        )
        self.assertEqual(safe["status"], LOCAL_SCHEDULED)
        self.assertFalse(safe["external_action"])

        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                UPDATE publish_queue
                SET status=?, last_error='meta_publish_outcome_unknown_owner_reconcile_required'
                WHERE content_id=?
                """,
                (BLOCKED_EXTERNAL_PUBLISHING, self.card["content_id"]),
            )
        with self.assertRaisesRegex(ValueError, "manual_reconcile"):
            service.rearm_blocked_preflight(
                self.card["content_id"], planned - timedelta(minutes=4)
            )

    def test_retry_stays_inside_grace_window_and_succeeds_once(self) -> None:
        self._approve()
        adapter = RetryOnceAdapter()
        service = PublishQueueService(self.pipeline.db, adapter)
        planned = datetime.fromisoformat(service.list()[0]["planned_at"])
        first = service.dispatch_due(planned + timedelta(minutes=1))
        self.assertEqual(first["failed_retryable"], 1)
        job = service.list()[0]
        self.assertEqual(job["status"], FAILED_RETRYABLE)
        retry_at = datetime.fromisoformat(job["next_attempt_at"])
        self.assertLessEqual(retry_at, planned + timedelta(minutes=15))
        service.reconcile(retry_at)
        second = service.dispatch_due(retry_at)
        self.assertEqual(second["published"], 1)
        self.assertEqual(len(adapter.calls), 2)

    def test_late_retry_becomes_future_berlin_owner_suggestion(self) -> None:
        self._approve()
        adapter = RetryOnceAdapter()
        service = PublishQueueService(self.pipeline.db, adapter)
        planned = datetime.fromisoformat(service.list()[0]["planned_at"])
        summary = service.dispatch_due(planned + timedelta(minutes=14))
        self.assertEqual(summary["needs_reschedule_review"], 1)
        job = service.list()[0]
        self.assertEqual(job["status"], NEEDS_RESCHEDULE_REVIEW)
        self.assertIsNone(job["next_attempt_at"])
        self.assertGreater(datetime.fromisoformat(job["suggested_at"]), planned)

    def test_old_slot_suggestion_is_future_and_dst_correct(self) -> None:
        self._approve()
        service = PublishQueueService(self.pipeline.db)
        current = datetime(2026, 10, 25, 22, 0, tzinfo=UTC)
        service.reconcile(current)
        suggestion = datetime.fromisoformat(service.list()[0]["suggested_at"])
        self.assertGreater(suggestion.astimezone(UTC), current)
        self.assertEqual(suggestion.strftime("%H:%M"), "19:30")
        self.assertEqual(suggestion.utcoffset(), timedelta(hours=1))

    def test_successful_adapter_claims_once_and_closes_content(self) -> None:
        self._approve()
        adapter = SuccessfulIdempotentAdapter()
        service = PublishQueueService(self.pipeline.db, adapter)
        planned = datetime.fromisoformat(service.list()[0]["planned_at"])
        first = service.dispatch_due(planned + timedelta(minutes=1))
        second = service.dispatch_due(planned + timedelta(minutes=1))
        self.assertEqual(first["published"], 1)
        self.assertEqual(second["due"], 0)
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(
            self.pipeline.db.scalar("SELECT status FROM content_items WHERE id=?", (self.card["content_id"],)),
            "PUBLISHED",
        )

    def test_change_invalidates_local_queue_without_external_action(self) -> None:
        self._approve()
        self.review.record_owner_decision(self.card["content_id"], "change", "Neue Caption")
        job = PublishQueueService(self.pipeline.db).list()[0]
        self.assertEqual(job["status"], "OWNER_CHANGE_REQUESTED")


if __name__ == "__main__":
    unittest.main()
