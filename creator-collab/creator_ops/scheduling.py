from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .models import ScheduleDecision


class PrimeTimePlanner:
    """Choose a configured evening slot and learn from completed 7-day metrics."""

    def __init__(self, config: dict):
        self.config = config
        self.timezone = ZoneInfo(config["timezone"])

    @staticmethod
    def _clock(value: str) -> time:
        hour, minute = (int(part) for part in value.split(":"))
        return time(hour, minute)

    def in_evening_window(self, value: datetime) -> bool:
        local = value.astimezone(self.timezone) if value.tzinfo else value.replace(tzinfo=self.timezone)
        settings = self.config["evening_run"]
        return self._clock(settings["start"]) <= local.time().replace(tzinfo=None) <= self._clock(
            settings["end"]
        )

    def _is_occupied(
        self,
        connection: sqlite3.Connection,
        creator_id: int,
        candidate: datetime,
    ) -> bool:
        minimum_spacing = int(self.config["evening_run"]["minimum_spacing_minutes"])
        rows = connection.execute(
            """
            SELECT p.scheduled_at
            FROM publications p
            JOIN content_items c ON c.id = p.content_id
            WHERE c.creator_id = ? AND p.status IN ('SCHEDULED', 'PUBLISHED')
            """,
            (creator_id,),
        ).fetchall()
        for row in rows:
            existing = datetime.fromisoformat(row[0])
            if existing.tzinfo is None:
                # Legacy/local rows were stored without an offset. They represent
                # the configured local scheduling timezone.
                existing = existing.replace(tzinfo=self.timezone)
            else:
                existing = existing.astimezone(self.timezone)
            if abs((existing - candidate).total_seconds()) < minimum_spacing * 60:
                return True
        return False

    def _history_score(
        self,
        connection: sqlite3.Connection,
        creator_id: int,
        platform: str,
        content_format: str,
        local_time: str,
    ) -> tuple[float | None, int]:
        real = connection.execute(
            """
            SELECT AVG((COALESCE(a.shares,0) + COALESCE(a.saves,0) + COALESCE(a.follows,0)) * 1.0 /
                       CASE WHEN COALESCE(a.reach,a.views,0) = 0 THEN 1
                            ELSE COALESCE(a.reach,a.views) END) AS quality,
                   COUNT(*) AS samples
            FROM manual_analytics_events a
            JOIN publications p ON p.id = a.publication_id
            JOIN platform_variants v ON v.id = p.platform_variant_id
            JOIN content_items c ON c.id = p.content_id
            WHERE c.creator_id = ? AND v.platform = ? AND v.format = ?
              AND a.window_hours = 168 AND p.provider = 'instagram-native-manual'
              AND substr(COALESCE(p.published_at,p.scheduled_at), 12, 5) = ?
            """,
            (creator_id, platform, content_format, local_time),
        ).fetchone()
        if real and int(real["samples"]):
            return real["quality"], int(real["samples"])
        row = connection.execute(
            """
            SELECT AVG((a.shares + a.saves + a.follows) * 1.0 /
                       CASE WHEN a.views = 0 THEN 1 ELSE a.views END) AS quality,
                   COUNT(*) AS samples
            FROM analytics_snapshots a
            JOIN publications p ON p.id = a.publication_id
            JOIN platform_variants v ON v.id = p.platform_variant_id
            JOIN content_items c ON c.id = p.content_id
            WHERE c.creator_id = ? AND v.platform = ? AND v.format = ?
              AND a.window_hours = 168 AND substr(p.scheduled_at, 12, 5) = ?
            """,
            (creator_id, platform, content_format, local_time),
        ).fetchone()
        return (row["quality"], int(row["samples"])) if row else (None, 0)

    def choose(
        self,
        connection: sqlite3.Connection,
        creator_id: int,
        run_date: date,
        platform: str,
        content_format: str,
    ) -> ScheduleDecision:
        candidates = self.config["cold_start_windows"][platform][content_format]
        ranked: list[tuple[float, datetime, str, float]] = []
        for index, local_time in enumerate(candidates):
            clock = self._clock(local_time)
            candidate = datetime.combine(run_date, clock, self.timezone)
            if not self.in_evening_window(candidate) or self._is_occupied(
                connection, creator_id, candidate
            ):
                continue
            history, samples = self._history_score(
                connection, creator_id, platform, content_format, local_time
            )
            if history is None:
                score = 1.0 - index * 0.05
                source = "cold-start-config"
                confidence = 0.45
            else:
                score = 1.0 + history * 10 + min(samples, 10) * 0.02
                source = "analytics-history"
                confidence = min(0.90, 0.50 + samples * 0.05)
            ranked.append((score, candidate, source, confidence))

        if not ranked:
            settings = self.config["evening_run"]
            cursor = datetime.combine(run_date, self._clock(settings["start"]), self.timezone)
            end = datetime.combine(run_date, self._clock(settings["end"]), self.timezone)
            while cursor <= end and self._is_occupied(connection, creator_id, cursor):
                cursor += timedelta(minutes=15)
            if cursor > end:
                raise RuntimeError("no_prime_time_slot_available")
            return ScheduleDecision(cursor, cursor.strftime("%H:%M"), "spacing-fallback", 0.30, 0.0)

        score, selected, source, confidence = max(ranked, key=lambda item: (item[0], -item[1].hour))
        return ScheduleDecision(
            scheduled_at=selected,
            local_time=selected.strftime("%H:%M"),
            source=source,
            confidence=confidence,
            score=score,
        )
