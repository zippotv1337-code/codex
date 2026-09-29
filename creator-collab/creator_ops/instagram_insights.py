from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analytics import METRICS, WINDOWS, _parse_datetime
from .database import CreatorDatabase, utc_now
from .publishing import MetaGraphError, MetaGraphTransport, UrllibMetaGraphTransport
from .secrets import get_secret


PROVIDER_METRICS = {
    "reach": "reach",
    "views": "views",
    "likes": "likes",
    "comments": "comments",
    "shares": "shares",
    "saves": "saved",
}


class MetaInstagramInsightsService:
    """Capture real Instagram media insights without publishing or guessing.

    The service deliberately writes into the existing append-only analytics
    table.  No second analytics store is introduced.  A late first read is
    recorded only for the highest already-due window; lower historical windows
    stay ``MISSED``/unknown because current cumulative values cannot recreate
    an exact earlier snapshot.
    """

    schema = "creator-ops-meta-insights-sync-v1"
    source = "META_GRAPH"
    late_source = "META_GRAPH_LATE"

    def __init__(
        self,
        database: CreatorDatabase,
        project_root: Path,
        *,
        transports: Mapping[str, MetaGraphTransport] | None = None,
        grace_hours: float = 6.0,
    ) -> None:
        self.database = database
        self.project_root = project_root
        self.grace_hours = max(0.0, grace_hours)
        self.transports = dict(transports or self._from_secret_broker())

    def _from_secret_broker(self) -> dict[str, MetaGraphTransport]:
        graph_version = get_secret("META_GRAPH_API_VERSION")
        graph_host = get_secret("META_GRAPH_HOST", "graph.instagram.com").strip().lower()
        if not graph_version:
            return {}
        result: dict[str, MetaGraphTransport] = {}
        for creator_slug, suffix in (
            ("leona-voss", "LEONA_VOSS"),
            ("mara-field", "MARA_FIELD"),
        ):
            token = get_secret(f"META_ACCESS_TOKEN_{suffix}")
            if not token:
                continue
            try:
                result[creator_slug] = UrllibMetaGraphTransport(
                    graph_version,
                    token,
                    graph_host=graph_host,
                )
            except ValueError:
                continue
        return result

    @staticmethod
    def _number(value: object) -> int | float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if value < 0:
            return None
        return int(value) if float(value).is_integer() else float(value)

    @classmethod
    def _insight_value(cls, payload: dict[str, object], provider_name: str) -> int | float | None:
        data = payload.get("data")
        if not isinstance(data, list):
            return None
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", ""))
            if name and name != provider_name:
                continue
            total = item.get("total_value")
            if isinstance(total, dict):
                value = cls._number(total.get("value"))
                if value is not None:
                    return value
            values = item.get("values")
            if isinstance(values, list):
                for observation in reversed(values):
                    if isinstance(observation, dict):
                        value = cls._number(observation.get("value"))
                        if value is not None:
                            return value
        return None

    def _read_metrics(
        self,
        transport: MetaGraphTransport,
        external_id: str,
    ) -> tuple[dict[str, int | float | None], list[str]]:
        metrics: dict[str, int | float | None] = {metric: None for metric in METRICS}
        errors: list[str] = []
        try:
            basic = transport.get(
                external_id,
                {"fields": "id,media_type,timestamp,permalink,like_count,comments_count"},
            )
            if str(basic.get("id", "")) != external_id:
                errors.append("media_id_mismatch")
                return metrics, errors
            metrics["likes"] = self._number(basic.get("like_count"))
            metrics["comments"] = self._number(basic.get("comments_count"))
        except (MetaGraphError, ConnectionError, TimeoutError, OSError, ValueError) as error:
            errors.append(str(error))

        for local_name, provider_name in PROVIDER_METRICS.items():
            try:
                payload = transport.get(
                    f"{external_id}/insights",
                    {"metric": provider_name},
                )
                value = self._insight_value(payload, provider_name)
                if value is not None:
                    metrics[local_name] = value
            except (MetaGraphError, ConnectionError, TimeoutError, OSError, ValueError) as error:
                errors.append(f"{local_name}:{error}")
        return metrics, sorted(set(errors))

    def _captured_windows(self, publication_id: int) -> set[int]:
        return {
            int(row["window_hours"])
            for row in self.database.all(
                "SELECT DISTINCT window_hours FROM manual_analytics_events WHERE publication_id=?",
                (publication_id,),
            )
        }

    def _target_window(
        self,
        publication_id: int,
        published_at: str,
        now: datetime,
    ) -> tuple[int, str] | None:
        published = _parse_datetime(published_at)
        if published is None:
            return None
        age_hours = max(0.0, (now - published.astimezone(timezone.utc)).total_seconds() / 3600)
        due = [window for window in WINDOWS if age_hours >= window]
        if not due:
            return None
        captured = self._captured_windows(publication_id)
        highest_captured = max(captured, default=0)
        candidates = [window for window in due if window not in captured and window > highest_captured]
        if not candidates:
            return None
        target = max(candidates)
        source = self.source if age_hours - target <= self.grace_hours else self.late_source
        return target, source

    def _store(
        self,
        publication_id: int,
        window_hours: int,
        source: str,
        metrics: dict[str, int | float | None],
        errors: list[str],
    ) -> tuple[str, int | None]:
        if not any(value is not None for value in metrics.values()):
            return "NO_SUPPORTED_METRICS", None
        columns = list(METRICS)
        note_parts = ["official Meta Graph read-only snapshot"]
        if source == self.late_source:
            note_parts.append("late cumulative capture; earlier windows remain unknown")
        if errors:
            note_parts.append("partial provider response")
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT id FROM manual_analytics_events WHERE publication_id=? AND window_hours=? LIMIT 1",
                (publication_id, window_hours),
            ).fetchone()
            if existing:
                return "ALREADY_CAPTURED", int(existing["id"])
            cursor = connection.execute(
                f"""
                INSERT INTO manual_analytics_events
                    (publication_id, window_hours, captured_at, source,
                     {', '.join(columns)}, note)
                VALUES (?, ?, ?, ?, {', '.join('?' for _ in columns)}, ?)
                """,
                (
                    publication_id,
                    window_hours,
                    utc_now(),
                    source,
                    *(metrics[name] for name in columns),
                    "; ".join(note_parts),
                ),
            )
        return "CAPTURED", int(cursor.lastrowid)

    def sync_due(self, *, now: datetime | None = None) -> dict[str, Any]:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        rows = self.database.all(
            """
            SELECT p.id, p.external_id, p.external_url, p.published_at,
                   p.provider, cr.slug AS persona
            FROM publications p
            JOIN content_items c ON c.id=p.content_id
            JOIN creators cr ON cr.id=c.creator_id
            WHERE p.status='PUBLISHED'
              AND p.provider LIKE 'instagram-meta-graph%'
              AND p.external_id IS NOT NULL
              AND p.published_at IS NOT NULL
            ORDER BY p.published_at, p.id
            """
        )
        items: list[dict[str, Any]] = []
        counts = {
            "captured": 0,
            "already_captured": 0,
            "waiting": 0,
            "blocked_configuration": 0,
            "provider_error": 0,
        }
        for row in rows:
            publication = dict(row)
            target = self._target_window(
                int(publication["id"]),
                str(publication["published_at"]),
                current,
            )
            if target is None:
                counts["waiting"] += 1
                continue
            window_hours, source = target
            transport = self.transports.get(str(publication["persona"]))
            if transport is None:
                counts["blocked_configuration"] += 1
                items.append(
                    {
                        "publication_id": publication["id"],
                        "persona": publication["persona"],
                        "window_hours": window_hours,
                        "status": "BLOCKED_CONFIGURATION",
                        "errors": ["meta_access_token_unavailable"],
                    }
                )
                continue
            metrics, errors = self._read_metrics(
                transport,
                str(publication["external_id"]),
            )
            status, event_id = self._store(
                int(publication["id"]),
                window_hours,
                source,
                metrics,
                errors,
            )
            if status == "CAPTURED":
                counts["captured"] += 1
            elif status == "ALREADY_CAPTURED":
                counts["already_captured"] += 1
            else:
                counts["provider_error"] += 1
            items.append(
                {
                    "publication_id": publication["id"],
                    "persona": publication["persona"],
                    "window_hours": window_hours,
                    "source": source,
                    "status": status,
                    "analytics_event_id": event_id,
                    "metrics_present": sorted(
                        name for name, value in metrics.items() if value is not None
                    ),
                    "errors": errors,
                }
            )
        return {
            "schema": self.schema,
            "generated_at": current.isoformat(),
            "external_action": "READ_ONLY_META_GRAPH",
            "counts": counts,
            "items": items,
            "secrets_exposed": False,
        }
