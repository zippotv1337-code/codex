from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .database import CreatorDatabase, utc_now


@dataclass(frozen=True)
class MediaRoute:
    provider: str
    fallback_provider: str | None
    status: str
    owner_gate: str | None
    execution: str


class MediaRoutingService:
    """Persist plan-only media jobs without invoking a paid/cloud worker."""

    def __init__(self, database: CreatorDatabase) -> None:
        self.database = database

    @staticmethod
    def choose(*, cost_included_confirmed: bool = False) -> MediaRoute:
        if cost_included_confirmed:
            return MediaRoute(
                provider="higgsfield",
                fallback_provider="openai-image",
                status="READY_FOR_WORKER",
                owner_gate=None,
                execution="NOT_STARTED",
            )
        return MediaRoute(
            provider="higgsfield",
            fallback_provider="openai-image",
            status="AWAITING_COST_CONFIRMATION",
            owner_gate="OWNER_APPROVAL_BEFORE_ANY_PAID_OR_UNCERTAIN_COST_CALL",
            execution="NOT_STARTED",
        )

    def plan(
        self,
        short_project_id: int,
        request: dict[str, Any],
        *,
        media_kind: str = "SHORT_VIDEO",
        cost_included_confirmed: bool = False,
    ) -> dict[str, Any]:
        if self.database.one(
            "SELECT id FROM short_projects WHERE id=?", (short_project_id,)
        ) is None:
            raise KeyError("short_project_not_found")
        route = self.choose(cost_included_confirmed=cost_included_confirmed)
        request_json = json.dumps(request, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(
            f"{short_project_id}:{media_kind}:{request_json}".encode("utf-8")
        ).hexdigest()[:24]
        job_key = f"media-{short_project_id}-{digest}"
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO media_jobs
                    (job_key, short_project_id, provider, fallback_provider,
                     media_kind, status, owner_gate, request_json, receipt_json,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)
                ON CONFLICT(job_key) DO NOTHING
                """,
                (
                    job_key,
                    short_project_id,
                    route.provider,
                    route.fallback_provider,
                    media_kind,
                    route.status,
                    route.owner_gate,
                    request_json,
                    now,
                    now,
                ),
            )
        return {
            "job_key": job_key,
            "short_project_id": short_project_id,
            "provider": route.provider,
            "fallback_provider": route.fallback_provider,
            "status": route.status,
            "owner_gate": route.owner_gate,
            "execution": route.execution,
            "cost_eur": 0.0,
        }

    def list(self, short_project_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM media_jobs"
        parameters: tuple[Any, ...] = ()
        if short_project_id is not None:
            query += " WHERE short_project_id=?"
            parameters = (short_project_id,)
        query += " ORDER BY id DESC"
        result = []
        for row in self.database.all(query, parameters):
            item = dict(row)
            item["request"] = json.loads(item.pop("request_json"))
            item["receipt"] = json.loads(item.pop("receipt_json"))
            result.append(item)
        return result
