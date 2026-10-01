"""Secret-free operational events for the Instagram DM bot.

This table is diagnostic metadata. Inbound messages and the send-once outbox
remain the only message ledger; no message text, payload or token is accepted.
"""

from __future__ import annotations

import re

from .database import CreatorDatabase, utc_now


_PERSONAS = {"leona-voss", "mara-field", "UNKNOWN"}
_RESULTS = {
    "STARTED",
    "SUCCESS",
    "RETRYING",
    "BLOCKED",
    "FAILED",
    "NEEDS_OWNER",
    "RECONCILE_REQUIRED",
    "SKIPPED",
}
_ACTION = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
_ACCOUNT_ID = re.compile(r"[0-9]{1,32}\Z")
_JOB_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9:_-]{0,95}\Z")
_PROVIDER = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{5,79}\Z")
_ERROR_CODE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+\Z")
_SECRET_PREFIXES = (
    "eaa", "ghp_", "gho_", "ghu_", "github_pat_", "sk_", "sk-", "bearer_"
)


def _optional_identifier(value: str | int | None, pattern: re.Pattern[str]) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    if not pattern.fullmatch(candidate) or candidate.lower().startswith(_SECRET_PREFIXES):
        return None
    return candidate


def _error_code(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip().lower()
    if len(candidate) > 96 or not _ERROR_CODE.fullmatch(candidate):
        return "redacted_error"
    if candidate.startswith(_SECRET_PREFIXES):
        return "redacted_error"
    return candidate


def record_bot_event(
    database: CreatorDatabase,
    *,
    persona: str | None,
    action: str,
    result: str,
    account_id: str | int | None = None,
    job_id: str | int | None = None,
    provider: str = "instagram-meta-graph",
    provider_request_id: str | None = None,
    retry_count: int = 0,
    error_code: str | None = None,
    error_summary: str | None = None,
) -> int:
    """Append one diagnostic event and return its row id.

    Caller-supplied identifiers are allowlisted. An unrecognized error summary
    is redacted rather than persisted as free text. A database failure is
    deliberately raised so the caller can report degraded observability.
    """

    if result not in _RESULTS:
        raise ValueError("bot_event_result_invalid")
    if isinstance(retry_count, bool) or not isinstance(retry_count, int) or retry_count < 0:
        raise ValueError("bot_event_retry_count_invalid")
    safe_persona = persona if persona in _PERSONAS else "UNKNOWN"
    safe_action = _optional_identifier(action.upper(), _ACTION) or "UNKNOWN_ACTION"
    safe_provider = _optional_identifier(provider.lower(), _PROVIDER) or "unknown"
    safe_error_code = _error_code(error_code)
    summary_code = _error_code(error_summary)
    safe_summary = (
        safe_error_code if error_summary is None else
        summary_code if summary_code == safe_error_code else "redacted_error"
    ) if safe_error_code is not None else None

    with database.transaction() as connection:
        cursor = connection.execute(
            """
            INSERT INTO instagram_dm_operation_events
                (timestamp, persona, account_id, action, job_id, provider,
                 provider_request_id, result, retry_count, error_code, error_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utc_now(),
                safe_persona,
                _optional_identifier(account_id, _ACCOUNT_ID),
                safe_action,
                _optional_identifier(job_id, _JOB_ID),
                safe_provider,
                _optional_identifier(provider_request_id, _REQUEST_ID),
                result,
                retry_count,
                safe_error_code,
                safe_summary,
            ),
        )
        return int(cursor.lastrowid)
