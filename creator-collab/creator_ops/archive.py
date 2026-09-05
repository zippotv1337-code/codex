from __future__ import annotations

from collections import defaultdict

from .database import CreatorDatabase


METRIC_WEIGHTS = {
    "saves": 25,
    "shares": 20,
    "comments": 15,
    "profile_visits": 15,
    "follows": 10,
    "link_clicks": 10,
    "likes": 5,
}


class ArchiveService:
    def __init__(self, database: CreatorDatabase):
        self.database = database

    @staticmethod
    def _is_mock(provider: str) -> bool:
        return provider.startswith("mock")

    def list(self, *, persona: str | None = None, mode: str = "real") -> list[dict]:
        if mode not in {"real", "mock", "all"}:
            raise ValueError("mode_must_be_real_mock_or_all")
        parameters: list[object] = []
        where = []
        if persona:
            where.append("cr.slug = ?")
            parameters.append(persona)
        sql = """
            SELECT p.*, cr.slug AS creator_slug, cr.display_name, c.title,
                   c.content_stage, c.visibility_scope, c.safety_class,
                   v.format, v.caption, v.hook
            FROM publications p
            JOIN content_items c ON c.id = p.content_id
            JOIN creators cr ON cr.id = c.creator_id
            JOIN platform_variants v ON v.id = p.platform_variant_id
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY COALESCE(p.published_at, p.scheduled_at) DESC, p.id DESC"
        rows = self.database.all(sql, tuple(parameters))
        result = []
        for row in rows:
            item = dict(row)
            is_mock = self._is_mock(item["provider"])
            if mode == "real" and is_mock or mode == "mock" and not is_mock:
                continue
            assets = self.database.all(
                """
                SELECT id, asset_id, pose_slot, is_top_pick, generator, file_path,
                       published_status
                FROM assets WHERE content_id = ?
                ORDER BY CASE WHEN published_status='PUBLISHED' THEN 0 ELSE 1 END,
                         is_top_pick DESC, id
                """,
                (item["content_id"],),
            )
            latest = self.database.all(
                """
                SELECT e.* FROM manual_analytics_events e
                WHERE e.publication_id = ? AND e.id = (
                    SELECT e2.id FROM manual_analytics_events e2
                    WHERE e2.publication_id=e.publication_id
                      AND e2.window_hours=e.window_hours
                    ORDER BY e2.captured_at DESC, e2.id DESC LIMIT 1
                ) ORDER BY window_hours
                """,
                (item["id"],),
            )
            item["is_mock"] = is_mock
            item["assets"] = [
                {
                    **dict(asset),
                    "preview_url": (
                        f"/api/assets/{asset['id']}/preview"
                        if asset["generator"] == "local-import"
                        else None
                    ),
                }
                for asset in assets
            ]
            item["analytics"] = [dict(event) for event in latest]
            result.append(item)
        return result

    @staticmethod
    def _score(event: dict) -> tuple[float, bool]:
        denominator = event.get("reach") or event.get("views")
        use_rates = bool(denominator)
        score = 0.0
        for metric, weight in METRIC_WEIGHTS.items():
            value = float(event.get(metric) or 0)
            score += weight * (value / denominator if use_rates else value)
        return score, use_rates

    def top3(self, *, persona: str | None = None, mode: str = "real") -> dict:
        items = self.list(persona=persona, mode=mode)
        ranked = []
        unranked = []
        for item in items:
            if not item["analytics"]:
                unranked.append(
                    {
                        **item,
                        "ranking_score": None,
                        "uses_rates": False,
                        "ranking_status": "INSUFFICIENT_DATA",
                    }
                )
                continue
            latest = item["analytics"][-1]
            score, uses_rates = self._score(latest)
            ranked.append(
                {
                    **item,
                    "ranking_score": round(score, 6),
                    "uses_rates": uses_rates,
                    "ranking_status": "RANKED",
                }
            )
        ranked.sort(
            key=lambda value: (
                value["ranking_score"],
                value.get("published_at") or value.get("scheduled_at") or "",
            ),
            reverse=True,
        )
        by_persona: dict[str, list[dict]] = defaultdict(list)
        for item in ranked:
            if len(by_persona[item["creator_slug"]]) < 3:
                by_persona[item["creator_slug"]].append(item)
        return {
            "weights": METRIC_WEIGHTS,
            "mode": mode,
            "overall": ranked[:3],
            "by_persona": dict(by_persona),
            "unranked": unranked,
        }

    def engagement(self, *, status: str = "PROPOSED", mode: str = "real") -> list[dict]:
        if status not in {"PROPOSED", "APPROVED_MANUAL", "EXECUTED", "DISMISSED"}:
            raise ValueError("invalid_engagement_status")
        if mode not in {"real", "mock", "all"}:
            raise ValueError("mode_must_be_real_mock_or_all")
        items = [
            dict(row)
            for row in self.database.all(
                """
                SELECT q.id, cr.slug AS creator_slug, cr.display_name,
                       q.action_type, q.target_ref, q.prompt, q.safety_note,
                       q.status, q.priority, q.not_before, p.provider, p.id AS publication_id,
                       (SELECT COUNT(*) FROM manual_analytics_events e
                        WHERE e.publication_id=p.id) AS analytics_event_count,
                       (SELECT e.comments FROM manual_analytics_events e
                        WHERE e.publication_id=p.id
                        ORDER BY e.captured_at DESC,e.id DESC LIMIT 1) AS known_comment_count
                FROM engagement_queue q
                JOIN creators cr ON cr.id=q.creator_id
                JOIN publications p ON p.id=q.publication_id
                WHERE q.status=?
                  AND (?='all'
                       OR (?='real' AND p.provider NOT LIKE 'mock%')
                       OR (?='mock' AND p.provider LIKE 'mock%'))
                ORDER BY q.priority, q.not_before, q.id
                """,
                (status, mode, mode, mode),
            )
        ]
        for item in items:
            # The schema stores aggregate counts, not comment bodies. Never turn a
            # count into an invented conversation or individual reply.
            item["reaction_data_known"] = bool(item["analytics_event_count"])
            item["comment_texts_available"] = False
            item["reply_drafts"] = []
            if item["reaction_data_known"]:
                item["action_recommendation"] = (
                    "Instagram-Kommentare manuell öffnen und echte Texte erfassen; "
                    "erst danach individuell antworten."
                )
            else:
                item["action_recommendation"] = (
                    "Noch keine echten Reaktionen importiert; Insights prüfen, nichts erfinden."
                )
            item["followup_idea"] = (
                "Story-Folge erst aus einem tatsächlich beobachteten Kommentar oder "
                "Analytics-Signal ableiten."
            )
        return items
