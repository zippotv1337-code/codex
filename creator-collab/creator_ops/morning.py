from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from .background import BackgroundCoordinator
from .review import ReviewDashboardService


class MorningContentFactory:
    """Idempotently prepares the existing five-shot review flow around 05:30."""

    def __init__(
        self,
        review: ReviewDashboardService,
        project_root: Path,
        start_time: str = "05:30",
    ) -> None:
        self.review = review
        self.project_root = Path(project_root)
        hour, minute = (int(part) for part in start_time.split(":"))
        self.start_time = time(hour, minute)
        self.timezone = ZoneInfo("Europe/Berlin")
        self.background = BackgroundCoordinator(review.pipeline.db, self.project_root)

    def run(
        self,
        requested_at: datetime,
        *,
        capacity_available: bool = True,
    ) -> dict[str, object]:
        local = (
            requested_at.replace(tzinfo=self.timezone)
            if requested_at.tzinfo is None
            else requested_at.astimezone(self.timezone)
        )
        if local.time().replace(tzinfo=None) < self.start_time:
            next_at = datetime.combine(local.date(), self.start_time, self.timezone)
            return {
                "status": "WAITING_FOR_SLOT",
                "next_run_at": next_at.isoformat(),
                "date": local.date().isoformat(),
            }

        target_date = local.date()

        def prepare() -> dict[str, object]:
            cards = self.review.ensure_date(target_date)
            return {
                "date": target_date.isoformat(),
                "personas": len(cards),
                "content_ids": [card["content_id"] for card in cards],
                "candidates": sum(card["asset_count"] for card in cards),
                "external_action": False,
            }

        result = self.background.run_once(
            f"morning:{target_date.isoformat()}",
            "morning-content-preparation",
            prepare,
            capacity_available=capacity_available,
            now=local,
        )
        return {**asdict(result), "date": target_date.isoformat()}
