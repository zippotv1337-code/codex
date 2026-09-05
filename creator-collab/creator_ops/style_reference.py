from __future__ import annotations

import json

from .database import CreatorDatabase, utc_now


ALLOWED_STRENGTHS = {"light", "medium"}
ALLOWED_FORMATS = {"fashion", "teaser", "humor_reel", "personality"}


class StyleReferenceService:
    """Internal experiment marker; never copies or contacts the source creator."""

    def __init__(self, database: CreatorDatabase) -> None:
        self.database = database

    def mark(
        self,
        content_id: int,
        *,
        strength: str,
        reference_format: str,
    ) -> dict[str, object]:
        if strength not in ALLOWED_STRENGTHS:
            raise ValueError("invalid_reference_strength")
        if reference_format not in ALLOWED_FORMATS:
            raise ValueError("invalid_reference_format")
        with self.database.transaction() as connection:
            content = connection.execute(
                """
                SELECT c.id, c.title, c.idea, c.safety_class, c.visibility_scope,
                       cr.slug AS creator_slug
                FROM content_items c JOIN creators cr ON cr.id=c.creator_id
                WHERE c.id=?
                """,
                (content_id,),
            ).fetchone()
            if content is None:
                raise KeyError("content_not_found")
            if content["safety_class"] != "SFW" or content["visibility_scope"] != "PUBLIC_SFW":
                raise ValueError("style_reference_public_sfw_only")
            if content["creator_slug"] == "mara-field" and reference_format not in {
                "humor_reel",
                "personality",
            }:
                context = f"{content['title']} {content['idea']}".lower()
                if not any(
                    word in context
                    for word in ("hof", "feld", "traktor", "werkstatt", "land", "küche")
                ):
                    raise ValueError("mara_reference_requires_farm_context")

            recent = connection.execute(
                """
                SELECT c.id,
                       EXISTS(
                           SELECT 1 FROM experiments e
                           WHERE e.content_id=c.id AND e.variable='style_reference'
                       ) AS referenced
                FROM content_items c ORDER BY c.created_at DESC, c.id DESC LIMIT 20
                """
            ).fetchall()
            recent_ids = [int(row["id"]) for row in recent]
            already = connection.execute(
                """
                SELECT id FROM experiments
                WHERE content_id=? AND variable='style_reference'
                """,
                (content_id,),
            ).fetchone()
            referenced_count = sum(int(row["referenced"]) for row in recent)
            if already is None and content_id in recent_ids and referenced_count >= 3:
                raise ValueError("style_reference_mix_cap_reached")
            newest_reference = next((row for row in recent if row["referenced"]), None)
            if (
                already is None
                and newest_reference is not None
                and recent
                and int(recent[0]["id"]) != content_id
                and int(newest_reference["id"]) == int(recent[0]["id"])
            ):
                raise ValueError("consecutive_style_reference_blocked")

            baseline = json.dumps(
                {
                    "reference_strength": strength,
                    "reference_format": reference_format,
                    "comparison_baseline": "same_persona_real_analytics",
                    "copying": "prohibited",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            if already is None:
                experiment_id = connection.execute(
                    """
                    INSERT INTO experiments
                        (content_id, variable, variant, baseline_json, decision, created_at)
                    VALUES (?, 'style_reference', 'mz_poke', ?, NULL, ?)
                    RETURNING id
                    """,
                    (content_id, baseline, utc_now()),
                ).fetchone()[0]
                reused = False
            else:
                experiment_id = already["id"]
                connection.execute(
                    "UPDATE experiments SET baseline_json=?, decision=NULL WHERE id=?",
                    (baseline, experiment_id),
                )
                reused = True
        return {
            "experiment_id": experiment_id,
            "content_id": content_id,
            "style_reference": "mz_poke",
            "reference_strength": strength,
            "reference_format": reference_format,
            "reused": reused,
        }

    def for_content(self, content_id: int) -> dict[str, object] | None:
        row = self.database.one(
            """
            SELECT variant, baseline_json FROM experiments
            WHERE content_id=? AND variable='style_reference'
            """,
            (content_id,),
        )
        if row is None:
            return None
        metadata = json.loads(row["baseline_json"])
        return {"style_reference": row["variant"], **metadata}
