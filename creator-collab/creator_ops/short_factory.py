from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from .analytics import AnalyticsService, WINDOWS
from .database import CreatorDatabase, utc_now
from .media_routing import MediaRoutingService


PIPELINE_STATES = (
    "RESEARCHED",
    "CONCEPT_READY",
    "SCRIPT_READY",
    "MEDIA_PLAN_READY",
    "QA_READY",
)


def _stable_key(prefix: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


class ShortFactoryService:
    """Virality intelligence and original short planning on the existing DB."""

    def __init__(self, database: CreatorDatabase) -> None:
        self.database = database
        self.media = MediaRoutingService(database)

    def ingest_trend(
        self,
        *,
        platform: str,
        source_url: str,
        observed_at: str,
        niche: str,
        source_summary: str,
        evidence: dict[str, Any],
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("trend_source_url_required")
        if not source_summary.strip():
            raise ValueError("trend_source_summary_required")
        required = {
            "hook_type",
            "tension_arc",
            "visual_rhythm",
            "cta_pattern",
            "format",
            "why_it_may_work",
        }
        if not required.issubset(analysis):
            raise ValueError("trend_analysis_fields_missing")
        try:
            datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("trend_observed_at_invalid") from None
        brief_payload = {
            "platform": platform.strip().lower(),
            "source_url": source_url,
            "observed_at": observed_at,
            "niche": niche.strip(),
        }
        brief_key = _stable_key("trend", brief_payload)
        pattern_payload = {
            "brief_key": brief_key,
            "hook_type": analysis["hook_type"],
            "tension_arc": analysis["tension_arc"],
            "visual_rhythm": analysis["visual_rhythm"],
            "cta_pattern": analysis["cta_pattern"],
            "format": analysis["format"],
        }
        pattern_key = _stable_key("pattern", pattern_payload)
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO trend_briefs
                    (brief_key, platform, source_url, observed_at, niche,
                     source_summary, evidence_json, analysis_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(brief_key) DO UPDATE SET
                    source_summary=excluded.source_summary,
                    evidence_json=excluded.evidence_json,
                    analysis_json=excluded.analysis_json
                """,
                (
                    brief_key,
                    brief_payload["platform"],
                    source_url,
                    observed_at,
                    brief_payload["niche"],
                    source_summary.strip(),
                    json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                    json.dumps(analysis, ensure_ascii=False, sort_keys=True),
                    now,
                ),
            )
            brief_id = int(
                connection.execute(
                    "SELECT id FROM trend_briefs WHERE brief_key=?", (brief_key,)
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO trend_patterns
                    (pattern_key, brief_id, hook_type, tension_arc, visual_rhythm,
                     cta_pattern, duration_seconds, format, analysis, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pattern_key) DO UPDATE SET
                    analysis=excluded.analysis,
                    duration_seconds=excluded.duration_seconds
                """,
                (
                    pattern_key,
                    brief_id,
                    str(analysis["hook_type"]),
                    str(analysis["tension_arc"]),
                    str(analysis["visual_rhythm"]),
                    str(analysis["cta_pattern"]),
                    int(analysis["duration_seconds"])
                    if analysis.get("duration_seconds") is not None
                    else None,
                    str(analysis["format"]),
                    str(analysis["why_it_may_work"]),
                    now,
                ),
            )
            pattern_id = int(
                connection.execute(
                    "SELECT id FROM trend_patterns WHERE pattern_key=?", (pattern_key,)
                ).fetchone()[0]
            )
        return {
            "brief_id": brief_id,
            "brief_key": brief_key,
            "pattern_id": pattern_id,
            "pattern_key": pattern_key,
            "source_separated_from_analysis": True,
        }

    def build_qa_ready(
        self,
        *,
        topic: str,
        audience: str,
        persona_slug: str,
        pattern_ids: list[int],
        format: str = "vertical-short",
    ) -> dict[str, Any]:
        if not topic.strip() or not audience.strip() or not persona_slug.strip():
            raise ValueError("short_factory_input_incomplete")
        unique_pattern_ids = list(dict.fromkeys(int(item) for item in pattern_ids))
        if not unique_pattern_ids:
            raise ValueError("short_factory_pattern_required")
        placeholders = ",".join("?" for _ in unique_pattern_ids)
        patterns = [
            dict(row)
            for row in self.database.all(
                f"SELECT * FROM trend_patterns WHERE id IN ({placeholders}) ORDER BY id",
                tuple(unique_pattern_ids),
            )
        ]
        if len(patterns) != len(unique_pattern_ids):
            raise KeyError("short_factory_pattern_not_found")
        creator = self.database.one(
            "SELECT id, display_name, tone FROM creators WHERE slug=?", (persona_slug,)
        )
        creator_id = int(creator["id"]) if creator else None
        display_name = str(creator["display_name"]) if creator else persona_slug
        tone = str(creator["tone"]) if creator else "klar und glaubwürdig"
        lead = patterns[0]
        hook_type = str(lead["hook_type"]).casefold()
        if "choice" in hook_type or "open_loop" in hook_type:
            hook = f"{topic.strip()}: Welche Seite passt heute wirklich zu deinem Tag?"
        else:
            hook = f"{topic.strip()}: Der kleine Moment, den {audience.strip()} oft übersieht."
        script = "\n".join(
            (
                f"0–3s — {hook}",
                f"3–8s — {display_name} zeigt zwei eigene, konkrete Alltagssituationen als sichtbare Wahl.",
                f"8–16s — Ein eigener, nachvollziehbarer Lösungs- oder Perspektivwechsel zu {topic.strip()}.",
                "16–22s — Belegbarer Abschluss und eine offene Frage statt eines erfundenen Erfolgsversprechens.",
            )
        )
        voice = {
            "tone": tone,
            "pace": "measured-fast",
            "disclosure": "AI persona/content disclosure remains required where applicable",
        }
        shot_plan = [
            {"beat": 1, "purpose": "hook", "framing": "close or decisive first frame"},
            {"beat": 2, "purpose": "context", "framing": "environment plus action"},
            {"beat": 3, "purpose": "payoff", "framing": "contrasting angle or B-roll"},
            {"beat": 4, "purpose": "cta", "framing": "calm final frame with readable safe text"},
        ]
        media_plan = {
            "aspect_ratio": "9:16",
            "preferred_worker": "higgsfield",
            "fallback_worker": "openai-image",
            "local_ai_role": "plan_route_evaluate",
            "execution": "NOT_STARTED",
            "cost_policy": "OWNER_GATE_IF_ADDITIONAL_COST_OR_INCLUDED_USE_UNCERTAIN",
        }
        captions = {
            "language": "de",
            "burn_in_required": False,
            "safe_area": "mobile vertical",
            "plan": ["Hook kurz", "Kernaussage zeilenweise", "CTA als Schlusszeile"],
        }
        cta = f"Wie würdest du {topic.strip()} in deinem Alltag lösen?"
        project_payload = {
            "topic": topic.strip(),
            "audience": audience.strip(),
            "persona_slug": persona_slug.strip(),
            "patterns": unique_pattern_ids,
            "format": format,
        }
        project_key = _stable_key("short", project_payload)
        now = utc_now()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO short_projects
                    (project_key, creator_id, persona_slug, topic, audience,
                     format, status, hook, script, voice_json, shot_plan_json,
                     media_plan_json, captions_json, cta, pattern_ids_json,
                     content_id, publication_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'RESEARCHED', ?, ?, ?, ?, ?, ?, ?, ?,
                        NULL, NULL, ?, ?)
                ON CONFLICT(project_key) DO NOTHING
                """,
                (
                    project_key,
                    creator_id,
                    persona_slug.strip(),
                    topic.strip(),
                    audience.strip(),
                    format,
                    hook,
                    script,
                    json.dumps(voice, ensure_ascii=False),
                    json.dumps(shot_plan, ensure_ascii=False),
                    json.dumps(media_plan, ensure_ascii=False),
                    json.dumps(captions, ensure_ascii=False),
                    cta,
                    json.dumps(unique_pattern_ids),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM short_projects WHERE project_key=?", (project_key,)
            ).fetchone()
            project_id = int(row["id"])
            current_status = str(row["status"])
        if current_status != "QA_READY":
            self._advance_all(project_id, current_status)
        media_job = self.media.plan(
            project_id,
            {
                "hook": hook,
                "shot_plan": shot_plan,
                "aspect_ratio": "9:16",
                "persona_slug": persona_slug,
                "safety": "PUBLIC_SFW_ONLY",
            },
            cost_included_confirmed=False,
        )
        return {**self.project(project_id), "media_job": media_job}

    def _advance_all(self, project_id: int, current_status: str) -> None:
        try:
            start = PIPELINE_STATES.index(current_status)
        except ValueError:
            raise ValueError("short_pipeline_state_invalid") from None
        evidence = {
            "source": "local-deterministic-planning",
            "external_action": False,
            "cost_eur": 0.0,
        }
        for new_status in PIPELINE_STATES[start + 1 :]:
            with self.database.transaction() as connection:
                previous = str(
                    connection.execute(
                        "SELECT status FROM short_projects WHERE id=?", (project_id,)
                    ).fetchone()[0]
                )
                if PIPELINE_STATES.index(new_status) != PIPELINE_STATES.index(previous) + 1:
                    raise ValueError("short_pipeline_transition_invalid")
                now = utc_now()
                connection.execute(
                    "UPDATE short_projects SET status=?, updated_at=? WHERE id=?",
                    (new_status, now, project_id),
                )
                connection.execute(
                    """
                    INSERT INTO short_pipeline_events
                        (short_project_id, previous_status, new_status,
                         evidence_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        previous,
                        new_status,
                        json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                        now,
                    ),
                )

    def link_publication(self, project_id: int, publication_id: int) -> dict[str, Any]:
        publication = self.database.one(
            "SELECT content_id FROM publications WHERE id=?", (publication_id,)
        )
        if publication is None:
            raise KeyError("publication_not_found")
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE short_projects SET publication_id=?, content_id=?, updated_at=?
                WHERE id=?
                """,
                (publication_id, int(publication["content_id"]), utc_now(), project_id),
            )
        return self.project(project_id)

    def refresh_learning(self, project_id: int | None = None) -> dict[str, Any]:
        query = "SELECT * FROM short_projects WHERE publication_id IS NOT NULL"
        parameters: tuple[Any, ...] = ()
        if project_id is not None:
            query += " AND id=?"
            parameters = (project_id,)
        projects = [dict(row) for row in self.database.all(query, parameters)]
        written = 0
        for project in projects:
            pattern_ids = json.loads(project["pattern_ids_json"] or "[]")
            for window in WINDOWS:
                event = self.database.one(
                    """
                    SELECT * FROM manual_analytics_events
                    WHERE publication_id=? AND window_hours=?
                    ORDER BY captured_at DESC, id DESC LIMIT 1
                    """,
                    (project["publication_id"], window),
                )
                if event is None:
                    continue
                metrics = {
                    name: event[name]
                    for name in (
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
                }
                score = AnalyticsService._score(metrics)
                action_metrics = (
                    "likes",
                    "comments",
                    "shares",
                    "saves",
                    "profile_visits",
                    "follows",
                    "link_clicks",
                )
                has_action_signal = any(metrics.get(name) is not None for name in action_metrics)
                decision = "VARIATE" if has_action_signal else "UNKNOWN"
                for pattern_id in pattern_ids:
                    with self.database.transaction() as connection:
                        connection.execute(
                            """
                            INSERT INTO pattern_learning
                                (pattern_id, short_project_id, publication_id,
                                 window_hours, observed_at, metrics_json, score,
                                 decision, evidence_source)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'manual_analytics_events')
                            ON CONFLICT(pattern_id, short_project_id, publication_id, window_hours)
                            DO UPDATE SET observed_at=excluded.observed_at,
                                          metrics_json=excluded.metrics_json,
                                          score=excluded.score,
                                          decision=excluded.decision,
                                          evidence_source=excluded.evidence_source
                            """,
                            (
                                int(pattern_id),
                                int(project["id"]),
                                int(project["publication_id"]),
                                window,
                                str(event["captured_at"]),
                                json.dumps(metrics, ensure_ascii=False, sort_keys=True),
                                score,
                                decision,
                            ),
                        )
                    written += 1
        return {
            "projects_considered": len(projects),
            "learning_rows_written": written,
            "missing_values_policy": "UNKNOWN_NULL_NEVER_ZERO",
            "views_alone_policy": "NOT_A_SUCCESS_SIGNAL",
        }

    def project(self, project_id: int) -> dict[str, Any]:
        row = self.database.one("SELECT * FROM short_projects WHERE id=?", (project_id,))
        if row is None:
            raise KeyError("short_project_not_found")
        item = dict(row)
        for source, target in (
            ("voice_json", "voice"),
            ("shot_plan_json", "shot_plan"),
            ("media_plan_json", "media_plan"),
            ("captions_json", "captions"),
            ("pattern_ids_json", "pattern_ids"),
        ):
            item[target] = json.loads(item.pop(source))
        item["events"] = [
            {
                **dict(event),
                "evidence": json.loads(event["evidence_json"]),
            }
            for event in self.database.all(
                "SELECT * FROM short_pipeline_events WHERE short_project_id=? ORDER BY id",
                (project_id,),
            )
        ]
        for event in item["events"]:
            event.pop("evidence_json", None)
        return item

    def dashboard(self) -> dict[str, Any]:
        latest_brief = self.database.one(
            "SELECT * FROM trend_briefs ORDER BY observed_at DESC, id DESC LIMIT 1"
        )
        latest_project = self.database.one(
            "SELECT id FROM short_projects ORDER BY updated_at DESC, id DESC LIMIT 1"
        )
        counts = {
            str(row["status"]): int(row["count"])
            for row in self.database.all(
                "SELECT status, COUNT(*) AS count FROM short_projects GROUP BY status"
            )
        }
        return {
            "schema": "zippoworkz-short-factory-v1",
            "trend_briefs": int(self.database.scalar("SELECT COUNT(*) FROM trend_briefs") or 0),
            "patterns": int(self.database.scalar("SELECT COUNT(*) FROM trend_patterns") or 0),
            "projects": int(self.database.scalar("SELECT COUNT(*) FROM short_projects") or 0),
            "by_status": counts,
            "latest_trend": (
                {
                    "id": int(latest_brief["id"]),
                    "platform": latest_brief["platform"],
                    "niche": latest_brief["niche"],
                    "observed_at": latest_brief["observed_at"],
                    "source_url": latest_brief["source_url"],
                }
                if latest_brief
                else None
            ),
            "latest_project": self.project(int(latest_project["id"])) if latest_project else None,
            "media_jobs": self.media.list(),
            "external_actions": 0,
            "cost_eur": 0.0,
        }
