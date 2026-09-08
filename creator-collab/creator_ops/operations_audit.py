from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from .archive import ArchiveService
from .publishing import PublishQueueService
from .review import ReviewDashboardService
from .stories import StoryReserveService


ANALYTICS_WINDOWS = (24, 72, 168)
BERLIN = ZoneInfo("Europe/Berlin")


def _as_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BERLIN)
    return parsed


class OperationsAuditService:
    """Read-only operating audit for the daily Instagram/Fiverr workspace."""

    def __init__(
        self,
        reviews: ReviewDashboardService,
        publishing: PublishQueueService,
    ) -> None:
        self.reviews = reviews
        self.publishing = publishing
        self.database = reviews.pipeline.db

    def _due_analytics(self, now: datetime) -> list[dict[str, object]]:
        current = now if now.tzinfo else now.replace(tzinfo=BERLIN)
        current_utc = current.astimezone(UTC)
        rows = self.database.all(
            """
            SELECT p.id AS publication_id, p.content_id, p.published_at,
                   p.external_url, p.provider, c.title, cr.slug AS creator_slug,
                   cr.display_name
            FROM publications p
            JOIN content_items c ON c.id=p.content_id
            JOIN creators cr ON cr.id=c.creator_id
            WHERE p.status='PUBLISHED'
              AND p.published_at IS NOT NULL
              AND p.provider NOT LIKE 'mock%'
            ORDER BY p.published_at, p.id
            """
        )
        due: list[dict[str, object]] = []
        for row in rows:
            published = _as_datetime(str(row["published_at"])).astimezone(UTC)
            missing_windows = []
            for hours in ANALYTICS_WINDOWS:
                if published + timedelta(hours=hours) > current_utc:
                    continue
                exists = self.database.scalar(
                    """
                    SELECT 1 FROM manual_analytics_events
                    WHERE publication_id=? AND window_hours=?
                    LIMIT 1
                    """,
                    (row["publication_id"], hours),
                )
                if not exists:
                    missing_windows.append(hours)
            if missing_windows:
                due.append(
                    {
                        "publication_id": row["publication_id"],
                        "content_id": row["content_id"],
                        "creator_slug": row["creator_slug"],
                        "display_name": row["display_name"],
                        "title": row["title"],
                        "published_at": row["published_at"],
                        "external_url": row["external_url"],
                        "provider": row["provider"],
                        "due_windows_hours": missing_windows,
                        "metrics_status": "UNKNOWN_UNTIL_OWNER_IMPORT",
                    }
                )
        return due

    @staticmethod
    def _ready_review_cards(queue: dict[str, object]) -> list[dict[str, object]]:
        return [
            {
                "content_id": card["content_id"],
                "creator_slug": card["creator_slug"],
                "display_name": card["display_name"],
                "series": card["series"],
                "status": card["status"],
                "format": card.get("format"),
                "prime_time": card.get("prime_time"),
            }
            for card in queue.get("active_cards", [])
            if card.get("can_approve")
        ]

    @staticmethod
    def _blocked_cards(queue: dict[str, object]) -> list[dict[str, object]]:
        return [
            {
                "content_id": card["content_id"],
                "creator_slug": card["creator_slug"],
                "series": card["series"],
                "status": card["status"],
                "reason": card.get("attention_reason"),
            }
            for card in queue.get("needs_attention", [])
        ]

    @staticmethod
    def _publish_queue_groups(items: list[dict[str, object]]) -> dict[str, int]:
        grouped: dict[str, int] = {}
        for item in items:
            status = str(item.get("status", "UNKNOWN"))
            grouped[status] = grouped.get(status, 0) + 1
        return grouped

    def snapshot(self, *, now: datetime | None = None) -> dict[str, object]:
        current = now or datetime.now(BERLIN)
        if current.tzinfo is None:
            current = current.replace(tzinfo=BERLIN)
        queue = self.reviews.review_queue()
        story_packages = StoryReserveService(self.reviews).packages()
        publish_jobs = self.publishing.list()
        due_analytics = self._due_analytics(current)
        engagement = ArchiveService(self.database).engagement(mode="real")
        ready_cards = self._ready_review_cards(queue)
        blocked_cards = self._blocked_cards(queue)
        local_scheduled = [
            item for item in publish_jobs if item.get("status") == "LOCAL_SCHEDULED"
        ]
        external_blocked = [
            item
            for item in publish_jobs
            if item.get("status") == "BLOCKED_EXTERNAL_PUBLISHING"
        ]

        next_actions: list[dict[str, object]] = []
        if due_analytics:
            next_actions.append(
                {
                    "priority": "P0",
                    "lane": "analytics",
                    "action": "Instagram Insights manuell/offiziell erfassen",
                    "count": len(due_analytics),
                    "blocked_by": "INSIGHTS_ACCESS",
                }
            )
        if local_scheduled:
            next_actions.append(
                {
                    "priority": "P0",
                    "lane": "instagram_output",
                    "action": "Lokal terminierte Pakete ueber offiziellen Weg veroeffentlichen",
                    "count": len(local_scheduled),
                    "blocked_by": "META_CREDENTIALS_OR_NATIVE_UPLOAD_SESSION",
                }
            )
        if ready_cards:
            next_actions.append(
                {
                    "priority": "P1",
                    "lane": "owner_review",
                    "action": "Reviewfertige Pakete pruefen und lokal freigeben",
                    "count": len(ready_cards),
                    "blocked_by": None,
                }
            )
        if story_packages:
            next_actions.append(
                {
                    "priority": "P1",
                    "lane": "stories",
                    "action": "Story-Kits nativ hochladen oder im Story-Review planen",
                    "count": len(story_packages),
                    "blocked_by": "NATIVE_UPLOAD_SESSION_FOR_LIVE_STORIES",
                }
            )
        if blocked_cards:
            next_actions.append(
                {
                    "priority": "P2",
                    "lane": "repair",
                    "action": "Needs-Attention-Karten gezielt reparieren oder archivieren",
                    "count": len(blocked_cards),
                    "blocked_by": "OWNER_CREATIVE_DIRECTION_WHERE_NEEDED",
                }
            )
        if not next_actions:
            next_actions.append(
                {
                    "priority": "IDLE",
                    "lane": "operations",
                    "action": "Keine lokale unblocked Output-Aufgabe gefunden",
                    "count": 0,
                    "blocked_by": None,
                }
            )

        return {
            "schema": "creator-ops-operations-audit-v1",
            "generated_at": current.astimezone(UTC).isoformat(timespec="seconds"),
            "timezone": "Europe/Berlin",
            "review": {
                "active_count": queue.get("counts", {}).get("active", 0),
                "needs_attention_count": queue.get("counts", {}).get(
                    "needs_attention", 0
                ),
                "ready_for_owner_review": ready_cards,
                "blocked_or_incomplete": blocked_cards,
            },
            "stories": {
                "ready_package_count": len(story_packages),
                "packages": [
                    {
                        "content_id": item["content_id"],
                        "creator_slug": item["creator_slug"],
                        "series": item["series"],
                        "frame_count": len(item.get("frames", [])),
                        "status": item["status"],
                    }
                    for item in story_packages
                ],
            },
            "publishing": {
                "queue_by_status": self._publish_queue_groups(publish_jobs),
                "local_scheduled_count": len(local_scheduled),
                "external_blocked_count": len(external_blocked),
                "live_posting": "BLOCKED_UNTIL_OFFICIAL_CREDENTIALS_OR_NATIVE_SESSION",
            },
            "analytics": {
                "due_count": len(due_analytics),
                "due": due_analytics,
            },
            "engagement": {
                "proposal_count": len(engagement),
                "execution": "manual-owner-only",
            },
            "next_actions": next_actions,
        }
