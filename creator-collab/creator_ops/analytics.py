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

ENGAGEMENT_WEIGHTS = {
    "saves": 25,
    "shares": 20,
    "comments": 15,
    "profile_visits": 15,
    "follows": 10,
    "link_clicks": 10,
    "likes": 5,
}


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

    @staticmethod
    def _metrics_present(metrics: dict) -> bool:
        return any(metrics.get(metric) is not None for metric in METRICS)

    @staticmethod
    def _score(metrics: dict) -> float | None:
        if not AnalyticsService._metrics_present(metrics):
            return None
        denominator = metrics.get("reach") or metrics.get("views")
        score = 0.0
        for metric, weight in ENGAGEMENT_WEIGHTS.items():
            value = metrics.get(metric)
            if value is None:
                continue
            score += weight * (float(value) / denominator if denominator else float(value))
        return round(score, 6)

    @staticmethod
    def _metric_totals(items: list[dict]) -> dict[str, int | float | None]:
        totals: dict[str, int | float | None] = {}
        for metric in METRICS:
            values = [item["metrics"][metric] for item in items if item["metrics"].get(metric) is not None]
            totals[metric] = sum(values) if values else None
        return totals

    @staticmethod
    def _best_value(rows: list[dict], key: str) -> dict | None:
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            value = row.get(key)
            if value:
                grouped.setdefault(str(value), []).append(row)
        candidates = [
            {"value": value, "sample_size": len(group), "average_score": round(sum(item["score"] for item in group) / len(group), 6)}
            for value, group in grouped.items()
            if len(group) >= 2
        ]
        return max(candidates, key=lambda item: item["average_score"], default=None)

    @staticmethod
    def _independent_content(rows: list[dict]) -> list[dict]:
        """Keep one strongest observation per content package for learning.

        A repost or later measurement of the same package is useful in the
        leaderboard, but must not manufacture a second independent content
        signal for recommendations or pattern detection.
        """
        selected: dict[int, dict] = {}
        for row in rows:
            content_id = int(row["content_id"])
            current = selected.get(content_id)
            if current is None or (row["score"], row["window_hours"]) > (
                current["score"], current["window_hours"]
            ):
                selected[content_id] = row
        return list(selected.values())

    def _learning(self, publications: list[dict], now: datetime) -> dict:
        observed = []
        for publication in publications:
            captured = [window for window in publication["windows"] if window["status"] == "CAPTURED"]
            if not captured:
                continue
            latest = max(captured, key=lambda item: item["window_hours"])
            score = self._score(latest["metrics"])
            if score is None:
                continue
            published = _parse_datetime(publication.get("published_at"))
            observed.append(
                {
                    "publication_id": publication["id"],
                    "content_id": publication["content_id"],
                    "persona": publication["persona"],
                    "title": publication["title"],
                    "format": publication["format"],
                    "hook": publication.get("hook"),
                    "window_hours": latest["window_hours"],
                    "score": score,
                    "metrics": latest["metrics"],
                    "published_at": publication.get("published_at"),
                    "published_hour": f"{published.astimezone().hour:02d}:00" if published else None,
                }
            )
        if not observed:
            return {
                "status": "UNKNOWN",
                "reason": "Noch keine echten Analytics-Snapshots mit Werten. Keine Empfehlung ableiten.",
                "recommendations": [{"decision": "UNKNOWN", "reason": "Echte Werte für ein fälliges 24h/72h/168h-Fenster importieren."}],
                "leaderboards": {"last_7_days": [], "last_30_days": []},
                "patterns": {"format": None, "theme": None, "hook": None, "posting_time": None},
                "trend": "UNKNOWN",
            }

        def recent(days: int) -> list[dict]:
            cutoff = now - timedelta(days=days)
            return sorted(
                [item for item in observed if (_parse_datetime(item["published_at"]) or now) >= cutoff],
                key=lambda item: (item["score"], item["published_at"] or ""), reverse=True,
            )[:3]

        independent = self._independent_content(observed)
        patterns = {
            "format": self._best_value(independent, "format"),
            "theme": self._best_value(independent, "title"),
            "hook": self._best_value(independent, "hook"),
            "posting_time": self._best_value(independent, "published_hour"),
        }
        if len(independent) < 2:
            decision = "UNKNOWN"
            reason = "Ein einzelnes unabhängiges Contentpaket reicht nicht für eine verlässliche Content-Änderung."
        else:
            decision = "VARIATE"
            reason = "Muster nur als kleine nächste Variation testen; keine große Strategieänderung aus wenigen Posts."
        return {
            "status": "OBSERVING",
            "reason": reason,
            "recommendations": [{"decision": decision, "reason": reason}],
            "leaderboards": {"last_7_days": recent(7), "last_30_days": recent(30)},
            "patterns": patterns,
            "trend": "INSUFFICIENT_HISTORY" if len(independent) < 3 else "OBSERVING",
        }

    def snapshot(self, *, now: datetime | None = None) -> dict:
        current = now or datetime.now(timezone.utc)
        rows = self.database.all(
            """
            SELECT p.id, p.content_id, p.external_id, p.external_url, p.published_at,
                   p.provider, cr.slug AS persona, c.title, v.format, v.hook
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
                "by_persona": [
                    {
                        "persona": persona,
                        "publications": len([item for item in publications if item["persona"] == persona]),
                        "captured_publications": len([
                            item for item in publications
                            if item["persona"] == persona
                            and any(window["status"] == "CAPTURED" for window in item["windows"])
                        ]),
                        "metrics": self._metric_totals([
                            max([window for window in item["windows"] if window["status"] == "CAPTURED"], key=lambda window: window["window_hours"])
                            for item in publications
                            if item["persona"] == persona and any(window["status"] == "CAPTURED" for window in item["windows"])
                        ]),
                    }
                    for persona in sorted({item["persona"] for item in publications})
                ],
                "learning": self._learning(publications, current),
            },
            "fiverr": {
                "status": "OWNER_GATE",
                "real_revenue_eur": real_revenue,
                "mock_revenue_eur": mock_revenue,
                "events": fiverr_events,
                "data_policy": "Keine Fiverr-Werte ohne echte Plattformdaten erfinden",
            },
        }
