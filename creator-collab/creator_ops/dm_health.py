"""Read-only, secret-free health projection for the existing Instagram DM lane."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .instagram_dm import InstagramDMService
from .instagram_dm import _safe_diagnostic_code
from .instagram_dm_provider import PERSONA_SECRET_NAMES


def _latest(*items: dict[str, object] | None) -> dict[str, object] | None:
    present = [item for item in items if item and item.get("timestamp")]
    # Eventlog entries are passed last and are the more precise source when
    # timestamps tie at SQLite's second-level precision.
    return max(enumerate(present), key=lambda pair: (str(pair[1]["timestamp"]), pair[0]))[1] if present else None


def _safe_error_code(value: object) -> str | None:
    if not value:
        return None
    code = str(value).strip().lower()
    if (
        len(code) <= 96
        and re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+", code)
        and not code.startswith((
            "eaa", "ghp_", "gho_", "ghu_", "github_pat_", "sk_", "sk-", "bearer_"
        ))
    ):
        return code
    return "redacted_error"


def bot_health_snapshot(service: InstagramDMService) -> dict[str, object]:
    """Report observed state; this endpoint never polls or sends to Meta."""
    dashboard = service.dashboard(limit=1)
    database = service.database
    readiness = dashboard["provider"]
    provider_personas = readiness.get("personas", {})
    if not isinstance(provider_personas, dict):
        provider_personas = {}

    sync_rows = database.all(
        """
        SELECT cr.slug AS persona, s.status, s.last_started_at,
               s.last_success_at, s.last_error, s.updated_at
        FROM instagram_dm_provider_sync s
        JOIN creators cr ON cr.id=s.creator_id
        """
    )
    sync_by_persona = {str(row["persona"]): row for row in sync_rows}
    handles = {
        str(row["persona"]): str(row["public_handle"])
        for row in database.all(
            """
            SELECT cr.slug AS persona, pa.public_handle
            FROM creators cr
            JOIN platform_accounts pa ON pa.creator_id=cr.id
            WHERE pa.platform='instagram' AND cr.slug IN ('leona-voss', 'mara-field')
            """
        )
    }
    personas: list[dict[str, object]] = []
    for slug in PERSONA_SECRET_NAMES:
        configured = provider_personas.get(slug, {})
        if not isinstance(configured, dict):
            configured = {}
        sync = sync_by_persona.get(slug)
        personas.append(
            {
                "persona": slug,
                "account": handles.get(slug),
                # These are provider configuration checks, not proof of a live send.
                "read_ready": configured.get("read_ready"),
                "write_ready": configured.get("write_ready"),
                "credentials_present": configured.get("configured"),
                "sync_status": str(sync["status"]) if sync else "UNKNOWN",
                "last_sync_started_at": sync["last_started_at"] if sync else None,
                "last_sync_success_at": sync["last_success_at"] if sync else None,
                "last_sync_error": _safe_error_code(sync["last_error"]) if sync else None,
            }
        )

    outbox_counts = {
        str(row["status"]): int(row["count"])
        for row in database.all(
            "SELECT status, COUNT(*) AS count FROM instagram_dm_outbox GROUP BY status"
        )
    }
    last_outbox = database.one(
        """
        SELECT o.id, o.status, o.updated_at, cr.slug AS persona
        FROM instagram_dm_outbox o
        JOIN instagram_dm_conversations c ON c.id=o.conversation_id
        LEFT JOIN creators cr ON cr.id=c.creator_id
        ORDER BY o.updated_at DESC, o.id DESC LIMIT 1
        """
    )
    last_inbound = database.one(
        """
        SELECT e.id, e.status, e.created_at, cr.slug AS persona
        FROM instagram_dm_events e
        JOIN instagram_dm_conversations c ON c.id=e.conversation_id
        LEFT JOIN creators cr ON cr.id=c.creator_id
        ORDER BY e.created_at DESC, e.id DESC LIMIT 1
        """
    )
    last_sync = max(sync_rows, key=lambda row: str(row["updated_at"])) if sync_rows else None
    last_action = _latest(
        {
            "timestamp": last_outbox["updated_at"],
            "persona": last_outbox["persona"],
            "action": "DM_REPLY",
            "job_id": int(last_outbox["id"]),
            "result": last_outbox["status"],
        } if last_outbox else None,
        {
            "timestamp": last_inbound["created_at"],
            "persona": last_inbound["persona"],
            "action": "DM_INBOUND",
            "job_id": None,
            "result": last_inbound["status"],
        } if last_inbound else None,
        {
            "timestamp": last_sync["updated_at"],
            "persona": last_sync["persona"],
            "action": "PROVIDER_SYNC",
            "job_id": None,
            "result": last_sync["status"],
        } if last_sync else None,
    )
    last_sent = database.one(
        """
        SELECT o.id, o.status, o.sent_at, cr.slug AS persona
        FROM instagram_dm_outbox o
        JOIN instagram_dm_conversations c ON c.id=o.conversation_id
        LEFT JOIN creators cr ON cr.id=c.creator_id
        WHERE o.sent_at IS NOT NULL AND o.status IN ('SENT', 'DELIVERED')
        ORDER BY o.sent_at DESC, o.id DESC LIMIT 1
        """
    )
    last_outbox_error = database.one(
        """
        SELECT o.id, o.last_error, o.updated_at, cr.slug AS persona
        FROM instagram_dm_outbox o
        JOIN instagram_dm_conversations c ON c.id=o.conversation_id
        LEFT JOIN creators cr ON cr.id=c.creator_id
        WHERE o.last_error IS NOT NULL AND o.last_error<>''
        ORDER BY o.updated_at DESC, o.id DESC LIMIT 1
        """
    )
    sync_errors = [row for row in sync_rows if row["last_error"]]
    last_sync_error = max(sync_errors, key=lambda row: str(row["updated_at"])) if sync_errors else None
    last_error = _latest(
        {
            "timestamp": last_outbox_error["updated_at"],
            "persona": last_outbox_error["persona"],
            "job_id": int(last_outbox_error["id"]),
            "code": _safe_error_code(last_outbox_error["last_error"]),
        } if last_outbox_error else None,
        {
            "timestamp": last_sync_error["updated_at"],
            "persona": last_sync_error["persona"],
            "job_id": None,
            "code": _safe_error_code(last_sync_error["last_error"]),
        } if last_sync_error else None,
    )

    # The operation ledger is additive. Older schema-8 databases have no table,
    # so the panel still works from the established sync/outbox records.
    event_columns = {
        str(row["name"])
        for row in database.all("PRAGMA table_info(instagram_dm_operation_events)")
    }
    if {
        "timestamp", "persona", "action", "job_id", "result",
        "error_code", "error_summary",
    }.issubset(event_columns):
        logged_action = database.one(
            """
            SELECT timestamp, persona, action, job_id, result
            FROM instagram_dm_operation_events
            ORDER BY timestamp DESC, id DESC LIMIT 1
            """
        )
        if logged_action:
            last_action = _latest(last_action, dict(logged_action))
        logged_error = database.one(
            """
            SELECT timestamp, persona, job_id, error_code, error_summary
            FROM instagram_dm_operation_events
            WHERE error_code IS NOT NULL OR error_summary IS NOT NULL
            ORDER BY timestamp DESC, id DESC LIMIT 1
            """
        )
        if logged_error:
            last_error = _latest(last_error, {
                "timestamp": logged_error["timestamp"],
                "persona": logged_error["persona"],
                "job_id": logged_error["job_id"],
                "code": _safe_error_code(
                    logged_error["error_code"] or logged_error["error_summary"]
                ),
            })

    if not any(persona["credentials_present"] for persona in personas):
        provider_status = "NOT_CONFIGURED"
    elif not all(persona["credentials_present"] for persona in personas):
        provider_status = "PARTIAL_CONFIG"
    elif any(persona["sync_status"] == "ERROR" for persona in personas):
        provider_status = "ERROR"
    elif all(persona["sync_status"] == "SYNCED" for persona in personas):
        provider_status = "LAST_SYNCED"
    else:
        provider_status = "UNKNOWN"

    return {
        "schema": "zippoworkz-instagram-dm-health-v1",
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        # This proves only that the web runtime and DB served this snapshot.
        # DM work runs inline; there is no separate worker heartbeat.
        "bot_online": "WEB_RUNTIME_ONLINE",
        "database": "ok",
        "dm_mode": dashboard["mode"],
        "send_enabled": dashboard["send_enabled"],
        "auto_reply_enabled": readiness.get("auto_reply_enabled"),
        "provider": {"name": readiness.get("provider"), "status": provider_status},
        "personas": personas,
        "last_action": last_action,
        "last_successful_message": {
            "timestamp": last_sent["sent_at"],
            "persona": last_sent["persona"],
            "job_id": int(last_sent["id"]),
            "status": last_sent["status"],
        } if last_sent else None,
        "last_error": last_error,
        "jobs": {
            "active": sum(outbox_counts.get(status, 0) for status in (
                "DRAFTED", "APPROVED", "SEND_PENDING"
            )),
            "retry": outbox_counts.get("RETRYING", 0),
            "blocked": outbox_counts.get("BLOCKED", 0)
                + outbox_counts.get("RECONCILE_REQUIRED", 0),
            "needs_owner": int(dashboard["counts"]["owner_reviews"]),
            "failed": outbox_counts.get("FAILED", 0),
        },
        "queue": "DB_OUTBOX_READABLE",
        "worker": {
            "mode": "INLINE_WEBHOOK_AND_ON_DEMAND",
            "dedicated_worker": False,
        },
    }


def bot_smoke_test(service: InstagramDMService, *, probe_provider: bool = True) -> dict[str, object]:
    """Read-only DB and provider preflight; never persists DMs or sends replies."""
    db = service.database
    integrity = str(db.scalar("PRAGMA integrity_check"))
    foreign_keys = len(db.all("PRAGMA foreign_key_check"))
    queue_count = int(db.scalar("SELECT COUNT(*) FROM instagram_dm_outbox") or 0)
    readiness = service.provider.readiness() if service.provider else {"personas": {}}
    mapped = readiness.get("personas", {})
    if not isinstance(mapped, dict):
        mapped = {}
    personas: dict[str, dict[str, object]] = {}
    for slug in PERSONA_SECRET_NAMES:
        creator = db.one("SELECT id FROM creators WHERE slug=? AND active=1", (slug,))
        config = mapped.get(slug, {})
        if not isinstance(config, dict):
            config = {}
        result: dict[str, object] = {
            "creator_mapped": creator is not None,
            "credentials_present": bool(config.get("configured")),
            "read_ready": bool(config.get("read_ready")),
            "write_ready": bool(config.get("write_ready")),
            "provider_probe": "NOT_REQUESTED" if not probe_provider else "NOT_READY",
        }
        if probe_provider and service.provider and result["read_ready"] and creator is not None:
            try:
                # Only a Graph GET. We deliberately return neither message
                # text nor sender identifiers and do not call ingest().
                result["messages_visible"] = len(service.provider.poll(slug))
                result["provider_probe"] = "REACHABLE"
            except Exception as error:
                result["provider_probe"] = "ERROR"
                result["error_code"] = _safe_diagnostic_code(error)
        personas[slug] = result
    return {
        "database": "OK" if integrity == "ok" and foreign_keys == 0 else "ERROR",
        "integrity_check": integrity,
        "foreign_key_errors": foreign_keys,
        "queue": "READABLE",
        "queued_items": queue_count,
        "worker": "INLINE_WEBHOOK_AND_ON_DEMAND",
        "personas": personas,
        "external_action": False,
        "message_sent": False,
    }
