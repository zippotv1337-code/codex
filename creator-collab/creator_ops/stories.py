from __future__ import annotations

from .review import ReviewDashboardService


class StoryReserveService:
    """Derive owner-reviewable story packages from existing feed assets only."""

    def __init__(self, reviews: ReviewDashboardService):
        self.reviews = reviews

    @staticmethod
    def _preview(asset: dict) -> dict:
        return {key: asset[key] for key in ("id", "pose_slot", "preview_url", "quality")}

    def packages(self) -> list[dict]:
        result: list[dict] = []
        for card in self.reviews.review_queue()["cards"]:
            available = [asset for asset in card["assets"] if not asset["excluded"]]
            top = sorted(
                (asset for asset in available if asset["top_pick"]),
                key=lambda asset: asset["top_pick_order"],
            )
            alternates = [asset for asset in available if not asset["top_pick"]]
            if len(top) < 2:
                continue
            poll_asset = alternates[0] if alternates else top[1]
            frames = [
                {"kind": "TEASER", "copy": card["hook"], "interaction": "Keine - nur Einstieg", "asset": self._preview(top[0])},
                {"kind": "POLL", "copy": "Welche Richtung soll in den Feed?", "interaction": "A: näher dran · B: mehr Szene", "asset": self._preview(poll_asset)},
                {"kind": "COMMUNITY", "copy": card["cta"], "interaction": "Antwort-Sticker; später manuell prüfen", "asset": self._preview(top[-1])},
            ]
            result.append({
                "content_id": card["content_id"], "creator_slug": card["creator_slug"],
                "display_name": card["display_name"], "series": card["series"],
                "date": card["date"], "planned_at": card.get("planned_at"),
                "status": "READY_FOR_OWNER_REVIEW", "story_type": "TEASER/POLL/FRAGE",
                "cta": card["cta"], "highlight": None, "frames": frames,
                "published_assets_excluded": card["excluded_published_count"],
                "safety_note": "SFW; kein Auto-Posting; nativen KI-Hinweis vor Veröffentlichung prüfen",
            })
        return result
