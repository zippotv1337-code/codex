from __future__ import annotations

from .review import ReviewDashboardService


class CollectionService:
    """Read-only album view over existing review packages and asset IDs."""

    def __init__(self, reviews: ReviewDashboardService):
        self.reviews = reviews

    def list(self, persona: str | None = None) -> list[dict]:
        cards = self.reviews.review_queue()["cards"]
        if persona:
            cards = [card for card in cards if card["creator_slug"] == persona]
        result = []
        for card in cards:
            ordered = sorted(
                card["assets"],
                key=lambda asset: (
                    asset["excluded"],
                    asset["top_pick_order"] if asset["top_pick_order"] is not None else 99,
                    asset["id"],
                ),
            )
            cover = next((asset for asset in ordered if asset["preview_url"] and not asset["excluded"]), None)
            result.append({
                "content_id": card["content_id"],
                "creator_slug": card["creator_slug"],
                "display_name": card["display_name"],
                "title": card["series"],
                "date": card["date"],
                "status": card["status"],
                "cover": cover,
                "tags": [card["content_stage"], card["safety_class"], card["visibility_scope"], "INSTAGRAM"],
                "asset_count": card["asset_count"],
                "reserve_count": card["available_asset_count"],
                "published_count": card["excluded_published_count"],
                "top3": [asset for asset in ordered if asset["top_pick"]],
                "top_performer": None,
                "top_performer_note": "Unbekannt - echte Analytics fehlen" if not card["approved"] else "Noch nicht aus echten Analytics bestimmt",
            })
        return result
