"""Explicit one-package dashboard push, independent of automatic scheduling."""
from __future__ import annotations

from datetime import UTC, datetime
import json
import os

from .database import utc_now
from .publishing import (MetaInstagramPublishingAdapter, PublishQueueService,
                         DispatchResult, BLOCKED_EXTERNAL_PUBLISHING)
from .secret_provider import create_secret_provider


class CheckedAdapter:
    """Fresh identity, quota and public-image checks at the send boundary."""
    def __init__(self, adapter):
        self.adapter = adapter
        self.provider = adapter.provider
        self.available = adapter.available

    def publish(self, publication_id, content_id, idempotency_key):
        check = self.adapter.preflight(publication_id, content_id)
        if check["status"] != "READY":
            return DispatchResult(status=BLOCKED_EXTERNAL_PUBLISHING, error="fresh_meta_preflight_failed")
        return self.adapter.publish(publication_id, content_id, idempotency_key)


class MetaPushService:
    def __init__(self, database, project, *, adapter_factory=None, provider=None):
        self.db = database
        self.project = project
        self.factory = adapter_factory or (lambda: MetaInstagramPublishingAdapter.from_environment(database, project))
        self.provider = provider or create_secret_provider()

    def _job(self, content_id):
        row = self.db.one("""SELECT q.*, c.status AS content_status,c.approved,p.external_id,p.external_url,
                         cr.slug,cr.display_name,c.title FROM publish_queue q
                         JOIN content_items c ON c.id=q.content_id
                         JOIN creators cr ON cr.id=c.creator_id
                         JOIN publications p ON p.id=q.publication_id
                         WHERE c.id=? ORDER BY q.approval_version DESC,q.id DESC LIMIT 1""", (content_id,))
        if row is None:
            raise ValueError("locally_approved_queue_item_required")
        return dict(row)

    @staticmethod
    def _safe_job(job):
        if job["external_id"] or job["external_schedule_id"] or job["content_status"] == "PUBLISHED":
            raise ValueError("already_published_or_external_state_present")
        if job["slug"] not in {"leona-voss", "mara-field"} or not job["approved"] or job["content_status"] != "SCHEDULED":
            raise ValueError("approved_project_package_required")
        if job["attempts"] != 0 or job["status"] not in {"LOCAL_SCHEDULED", "NEEDS_RESCHEDULE_REVIEW"}:
            raise ValueError("existing_attempt_requires_reconciliation_not_retry")
        if job["status"] == "NEEDS_RESCHEDULE_REVIEW" and job["last_error"] != "planned_slot_expired_owner_review_required":
            raise ValueError("queue_requires_manual_reconciliation")

    def preflight(self, content_id):
        job = self._job(content_id)
        self._safe_job(job)
        adapter = self.factory()
        if not adapter.available or not hasattr(adapter, "preflight"):
            return {"status": "BLOCKED", "content_id": content_id,
                    "errors": ["persona_access_token_user_id_version_or_https_manifest_missing"], "external_publish": False}
        result = adapter.preflight(job["publication_id"], content_id)
        return {**result, "external_publish": False}

    def push_one(self, content_id):
        job = self._job(content_id)
        self._safe_job(job)
        adapter = self.factory()
        if not adapter.available or not hasattr(adapter, "preflight"):
            return self.preflight(content_id)
        checked = adapter.preflight(job["publication_id"], content_id)
        if checked["status"] not in {"READY", "READY_FOR_OWNER_CONFIRMATION"}:
            return {**checked, "external_publish": False}
        now = datetime.now(UTC)
        # A push is an explicit request to send THIS package now, not to enable
        # all overdue jobs. Compare-and-set preserves concurrent workers/reviews.
        with self.db.transaction() as connection:
            changed = connection.execute("""UPDATE publish_queue SET planned_at=?,status='LOCAL_SCHEDULED',
                last_error=NULL,suggested_at=NULL,updated_at=? WHERE id=? AND status=? AND attempts=0
                AND external_schedule_id IS NULL""", (now.isoformat(), utc_now(), job["id"], job["status"])).rowcount
            if changed != 1:
                raise ValueError("queue_changed_recheck_required")
            connection.execute("UPDATE publications SET scheduled_at=?,schedule_status='LOCAL_SCHEDULED',schedule_error=NULL WHERE id=?",
                               (now.isoformat(), job["publication_id"]))
        queue = PublishQueueService(self.db, CheckedAdapter(adapter))
        queue.authorize_live_publish(content_id)
        result = queue.dispatch_due(now, queue_id=job["id"])
        final = self._job(content_id)
        return {"content_id": content_id, "queue_id": job["id"], "dispatch": result,
                "status": final["status"], "external_id": final["external_id"], "permalink": final["external_url"],
                "note": "PUBLISHED only with external confirmation; inspect native AI label on resulting post."}

    def snapshot(self):
        accounts = []
        for slug in ("leona-voss", "mara-field"):
            accounts.append({"creator": slug,
                             "user_id_present": self.provider.has(f"secret://meta/{slug}/ig-user-id"),
                             "token_present": self.provider.has(f"secret://meta/{slug}/access-token")})
        ids = self.db.all("SELECT DISTINCT content_id FROM publish_queue")
        items = []
        for row in ids:
            job = self._job(row["content_id"])
            try:
                self._safe_job(job)
                blocker = None
            except ValueError as error:
                blocker = str(error)
            items.append({key: job[key] for key in ("content_id", "title", "display_name", "status", "attempts", "external_url")} | {"local_blocker": blocker})
        manifest_path = self.project / "data" / "meta_media_urls.json"
        configured = os.environ.get("CREATOR_OPS_META_MEDIA_MANIFEST")
        if configured:
            from pathlib import Path
            manifest_path = Path(configured)
        return {"accounts": accounts, "packages": items, "graph_version_configured": bool(os.environ.get("META_GRAPH_API_VERSION")),
                "manifest_present": manifest_path.is_file(), "api_proof": "NOT_PROVEN_BY_CONFIGURATION",
                "scheduler_enabled_by_push": False, "scope": "ONE_EXPLICIT_PACKAGE_ONLY",
                "owner_step": "Instagram-Nutzerzugang für Leona/Mara sicher hinterlegen; App-ID/App-Geheimcode sind kein Nutzer-Token."}
