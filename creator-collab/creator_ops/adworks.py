from __future__ import annotations

import json
from dataclasses import dataclass

from .database import CreatorDatabase, utc_now


PACK_DEFINITIONS = (
    {
        "pack_key": "creator-sfw-basic",
        "tier": "BASIC",
        "name": "SFW Social Content Pack",
        "summary": "Ein vollständiges, owner-reviewbares Content-Paket für eine virtuelle Persona oder Brandfigur.",
        "deliverables": [
            "5 vertikale Bildkandidaten mit Pose-Matrix",
            "visuelle QA und Top-3-Empfehlung",
            "Carousel-Reihenfolge, Caption, Hook, CTA und Hashtags",
        ],
        "exclusions": ["Live-Posting", "Accountmanagement", "Reichweiten- oder Umsatzgarantie", "Musiklizenz"],
    },
    {
        "pack_key": "creator-sfw-standard",
        "tier": "STANDARD",
        "name": "SFW Content Duo",
        "summary": "Zwei vollständige Content-Pakete für eine konsistente virtuelle Persona oder Brandfigur.",
        "deliverables": [
            "2 Pakete mit insgesamt 10 Bildkandidaten",
            "QA, Top 3, Texte und Carousel-Reihenfolge je Paket",
            "2 Story-Konzepte mit je 3 Frames",
        ],
        "exclusions": ["Live-Posting", "laufende Analytics", "unbegrenzte Revisionen", "Musikdateien"],
    },
    {
        "pack_key": "creator-sfw-premium",
        "tier": "PREMIUM",
        "name": "SFW Content Reserve",
        "summary": "Vier vollständige Pakete als strukturierte Content-Reserve mit Review-Übersicht.",
        "deliverables": [
            "4 Pakete mit insgesamt 20 Bildkandidaten",
            "4 Story-Sequenzen mit je 3 Frames",
            "Content-Reserve, Portfolio-Zuordnung und Review-Übersicht",
        ],
        "exclusions": ["SaaS-Zugang", "Live-Posting", "Performancegarantie", "Adult-Content"],
    },
)


@dataclass(frozen=True)
class DryRunResult:
    pack_key: str
    campaign_key: str
    link_key: str
    event_keys: list[str]
    feedback_key: str
    reused: bool


class AdWorksService:
    """Organic/dry-run attribution layer; it has no paid-spend capability."""

    def __init__(self, database: CreatorDatabase) -> None:
        self.database = database

    def seed_catalog(self) -> list[dict[str, object]]:
        now = utc_now()
        with self.database.transaction() as connection:
            for pack in PACK_DEFINITIONS:
                connection.execute(
                    """
                    INSERT INTO product_packs
                        (pack_key, tier, name, summary, deliverables_json,
                         exclusions_json, status, owner_approved, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'DRAFT_OWNER_GATES', 0, ?, ?)
                    ON CONFLICT(pack_key) DO UPDATE SET
                        tier=excluded.tier,
                        name=excluded.name,
                        summary=excluded.summary,
                        deliverables_json=excluded.deliverables_json,
                        exclusions_json=excluded.exclusions_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        pack["pack_key"], pack["tier"], pack["name"], pack["summary"],
                        json.dumps(pack["deliverables"], ensure_ascii=False),
                        json.dumps(pack["exclusions"], ensure_ascii=False), now, now,
                    ),
                )
        return self.catalog()

    def catalog(self) -> list[dict[str, object]]:
        rows = self.database.all("SELECT * FROM product_packs ORDER BY id")
        return [
            {
                "id": row["id"],
                "pack_key": row["pack_key"],
                "tier": row["tier"],
                "name": row["name"],
                "summary": row["summary"],
                "deliverables": json.loads(row["deliverables_json"]),
                "exclusions": json.loads(row["exclusions_json"]),
                "price_eur": row["price_eur"],
                "delivery_days": row["delivery_days"],
                "revisions": row["revisions"],
                "status": row["status"],
                "owner_approved": bool(row["owner_approved"]),
            }
            for row in rows
        ]

    def dry_run(self, pack_key: str = "creator-sfw-basic") -> DryRunResult:
        self.seed_catalog()
        campaign_key = f"dryrun:{pack_key}:organic"
        link_key = f"dryrun-{pack_key}"
        now = utc_now()
        event_specs = (
            ("click", None),
            ("landing_view", None),
            ("lead", None),
            ("purchase", 123.45),
        )
        with self.database.transaction() as connection:
            pack = connection.execute(
                "SELECT id FROM product_packs WHERE pack_key = ?", (pack_key,)
            ).fetchone()
            if pack is None:
                raise KeyError("pack_not_found")
            pack_id = int(pack["id"])
            connection.execute(
                """
                INSERT INTO adworks_campaigns
                    (campaign_key, name, pack_id, channel, source, medium,
                     campaign_token, content_token, destination_ref, organic,
                     approval_status, status, created_at)
                VALUES (?, ?, ?, 'LOCAL', 'creator_ops', 'organic_dry_run', ?,
                        'acceptance', '/offer', 1, 'DRY_RUN_ONLY', 'DRY_RUN', ?)
                ON CONFLICT(campaign_key) DO NOTHING
                """,
                (campaign_key, "Creator Ops Pack Acceptance", pack_id, pack_key, now),
            )
            campaign_id = int(connection.execute(
                "SELECT id FROM adworks_campaigns WHERE campaign_key = ?", (campaign_key,)
            ).fetchone()["id"])
            query = f"utm_source=creator_ops&utm_medium=organic_dry_run&utm_campaign={pack_key}&utm_content=acceptance"
            connection.execute(
                """
                INSERT INTO tracking_links
                    (link_key, campaign_id, destination_ref, query_string, active, created_at)
                VALUES (?, ?, '/offer', ?, 0, ?)
                ON CONFLICT(link_key) DO NOTHING
                """,
                (link_key, campaign_id, query, now),
            )
            link_id = int(connection.execute(
                "SELECT id FROM tracking_links WHERE link_key = ?", (link_key,)
            ).fetchone()["id"])
            reused = connection.execute(
                "SELECT COUNT(*) FROM funnel_events WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()[0] > 0
            event_keys: list[str] = []
            for index, (event_type, amount) in enumerate(event_specs, start=1):
                event_key = f"{campaign_key}:{index}:{event_type}"
                event_keys.append(event_key)
                connection.execute(
                    """
                    INSERT INTO funnel_events
                        (event_key, dedupe_key, tracking_link_id, campaign_id,
                         pack_id, event_type, source, attribution, amount,
                         currency, is_mock, occurred_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, 'ACCEPTANCE_TEST', 'last_touch',
                            ?, 'EUR', 1, ?, ?)
                    ON CONFLICT(dedupe_key) DO NOTHING
                    """,
                    (
                        event_key, event_key, link_id, campaign_id, pack_id,
                        event_type, amount, now,
                        json.dumps({"synthetic": True, "sequence": index}),
                    ),
                )
            feedback_key = f"{campaign_key}:feedback"
            connection.execute(
                """
                INSERT INTO product_feedback
                    (feedback_key, pack_id, campaign_id, signal, decision,
                     evidence_json, is_mock, created_at)
                VALUES (?, ?, ?, 'DRY_RUN_CONVERSION_PATH_OK', 'KEEP_TESTING', ?, 1, ?)
                ON CONFLICT(feedback_key) DO NOTHING
                """,
                (
                    feedback_key, pack_id, campaign_id,
                    json.dumps({"event_keys": event_keys, "mock_revenue_eur": 123.45}), now,
                ),
            )
        return DryRunResult(pack_key, campaign_key, link_key, event_keys, feedback_key, reused)

    def dashboard(self) -> dict[str, object]:
        packs = self.seed_catalog()
        event_rows = self.database.all(
            "SELECT event_type, is_mock, COUNT(*) AS count, COALESCE(SUM(amount), 0) AS amount FROM funnel_events GROUP BY event_type, is_mock"
        )
        events = [dict(row) for row in event_rows]
        return {
            "packs": packs,
            "events": events,
            "real_revenue_eur": float(self.database.scalar(
                "SELECT COALESCE(SUM(amount), 0) FROM funnel_events WHERE event_type IN ('order','purchase','subscription','tip','other_revenue') AND is_mock=0"
            ) or 0),
            "mock_revenue_eur": float(self.database.scalar(
                "SELECT COALESCE(SUM(amount), 0) FROM funnel_events WHERE event_type IN ('order','purchase','subscription','tip','other_revenue') AND is_mock=1"
            ) or 0),
            "paid_spend": "OWNER_GATE",
            "execution": "organic-and-dry-run-only",
        }
