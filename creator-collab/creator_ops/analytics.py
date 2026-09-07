from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .database import CreatorDatabase


WINDOWS = (24, 72, 168)
METRICS = (
    "reach",
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "profile_visits",
    "follows",
    "link_clicks",
    "revenue",
)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


class AnalyticsService:
    """Read-only operations view for real Instagram and Fiverr signals."""

    def __init__(self, database: CreatorDatabase):
        self.database = database

    def _manual_event(self, publication_id: int, window: int) -> dict | None:
        row = self.database.one(
            """
            SELECT * FROM manual_analytics_events
            WHERE publication_id = ? AND window_hours = ?
            ORDER BY captured_at DESC, id DESC LIMIT 1
            """,
            (publication_id, window),
        )
        return dict(row) if row else None

    def _windows(self, publication: dict, now: datetime) -> list[dict]:
        published = _parse_datetime(publication.get("published_at"))
        result = []
        for window in WINDOWS:
            event = self._manual_event(publication["id"], window)
            due = bool(published and now >= published + timedelta(hours=window))
            metrics = {metric: (event.get(metric) if event else None) for metric in METRICS}
            result.append(
                {
                    "window_hours": window,
                    "due": due,
                    "status": "CAPTURED" if event else ("DUE" if due else "WAITING"),
                    "captured_at": event.get("captured_at") if event else None,
                    "source": "manual_owner_import" if event else "UNKNOWN",
                    "metrics": metrics,
                }
            )
        return result

    def snapshot(self, *, now: datetime | None = None) -> dict:
        current = now or datetime.now(timezone.utc)
        rows = self.database.all(
            """
            SELECT p.id, p.content_id, p.external_id, p.external_url, p.published_at,
                   p.provider, cr.slug AS persona, c.title, v.format
            FROM publications p
            JOIN content_items c ON c.id = p.content_id
            JOIN creators cr ON cr.id = c.creator_id
            JOIN platform_variants v ON v.id = p.platform_variant_id
            WHERE p.status = 'PUBLISHED' AND p.provider NOT LIKE 'mock%'
            ORDER BY p.published_at DESC, p.id DESC
            """
        )
        publications = []
        due_count = 0
        captured_count = 0
        for row in rows:
            item = dict(row)
            windows = self._windows(item, current)
            due_count += sum(window["status"] == "DUE" for window in windows)
            captured_count += sum(window["status"] == "CAPTURED" for window in windows)
            publications.append({**item, "windows": windows})

        real_revenue = float(
            self.database.scalar(
                "SELECT COALESCE(SUM(amount), 0) FROM revenue_events"
            )
            or 0
        ) + float(
            self.database.scalar(
                "SELECT COALESCE(SUM(amount), 0) FROM funnel_events WHERE is_mock = 0"
            )
            or 0
        )
        mock_revenue = float(
            self.database.scalar(
                "SELECT COALESCE(SUM(amount), 0) FROM funnel_events WHERE is_mock = 1"
            )
            or 0
        )
        fiverr_events = [dict(row) for row in self.database.all(
            """
            SELECT event_type, is_mock, COUNT(*) AS count
            FROM funnel_events
            WHERE source = 'fiverr' OR event_type LIKE 'fiverr%'
            GROUP BY event_type, is_mock ORDER BY event_type, is_mock
            """
        )]
        return {
            "generated_at": current.isoformat(),
            "instagram": {
                "published_count": len(publications),
                "captured_windows": captured_count,
                "due_windows": due_count,
                "unknown_until_owner_import": len(publications) * len(WINDOWS) - captured_count,
                "publications": publications,
                "data_policy": "REAL_ONLY; fehlende Werte bleiben UNKNOWN/NULL",
            },
            "fiverr": {
                "status": "OWNER_GATE",
                "real_revenue_eur": real_revenue,
                "mock_revenue_eur": mock_revenue,
                "events": fiverr_events,
                "data_policy": "Keine Fiverr-Werte ohne echte Plattformdaten erfinden",
            },
        }
