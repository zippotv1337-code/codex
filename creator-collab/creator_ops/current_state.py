from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .content_mix import ContentMixPlanner
from .database import CreatorDatabase


REMOTE_URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.IGNORECASE)


def _grouped(rows: list, key: str, value: str = "count") -> dict[str, int]:
    return {str(row[key]): int(row[value]) for row in rows}


class CurrentStateService:
    """Build a secret-free project snapshot from SQLite and local runtime signals."""

    def __init__(self, database: CreatorDatabase, root: Path) -> None:
        self.database = database
        self.root = Path(root)

    def _git(self) -> dict[str, str]:
        # The standalone runtime intentionally does not probe or mutate Git.
        # Repository sync is handled outside the application process.
        return {"state": "MANAGED_OUTSIDE_RUNTIME"}

    def _app_version(self) -> str:
        version_path = self.root / "VERSION"
        try:
            value = version_path.read_text(encoding="utf-8").strip()
        except OSError:
            return "unknown"
        return value or "unknown"

    def _remote(self, include_url: bool) -> dict[str, object]:
        path = self.root / "data" / "REMOTE_ACCESS_CURRENT.txt"
        result: dict[str, object] = {"active": False, "started_at": None}
        if not path.is_file():
            return result
        try:
            text = path.read_text(encoding="utf-8")
            match = REMOTE_URL_PATTERN.search(text)
            if match is None:
                return result
            result["active"] = True
            result["started_at"] = datetime.fromtimestamp(
                path.stat().st_mtime, tz=UTC
            ).isoformat(timespec="seconds")
            if include_url:
                result["url"] = match.group(0)
        except OSError:
            pass
        return result

    def snapshot(
        self,
        *,
        include_remote_url: bool = False,
        tests_passed: int | None = None,
        tests_failed: int | None = None,
    ) -> dict[str, object]:
        creators = [
            dict(row)
            for row in self.database.all(
                "SELECT slug, display_name, instagram_handle, active FROM creators ORDER BY id"
            )
        ]
        status_counts = _grouped(
            self.database.all(
                "SELECT status, COUNT(*) AS count FROM content_items GROUP BY status ORDER BY status"
            ),
            "status",
        )
        stage_counts = _grouped(
            self.database.all(
                "SELECT content_stage, COUNT(*) AS count FROM content_items GROUP BY content_stage ORDER BY content_stage"
            ),
            "content_stage",
        )
        mix = ContentMixPlanner().recommend(stage_counts)
        safety_counts = _grouped(
            self.database.all(
                "SELECT safety_class, COUNT(*) AS count FROM assets GROUP BY safety_class ORDER BY safety_class"
            ),
            "safety_class",
        )
        scope_counts = _grouped(
            self.database.all(
                "SELECT visibility_scope, COUNT(*) AS count FROM assets GROUP BY visibility_scope ORDER BY visibility_scope"
            ),
            "visibility_scope",
        )
        total_assets = int(self.database.scalar("SELECT COUNT(*) FROM assets") or 0)
        real_assets = int(
            self.database.scalar(
                "SELECT COUNT(*) FROM assets WHERE generator = 'local-import'"
            )
            or 0
        )
        review_required = sum(
            status_counts.get(status, 0)
            for status in ("READY_FOR_REVIEW", "PARTIAL_READY")
        )
        reserve_dates = [
            str(row[0])
            for row in self.database.all(
                """
                SELECT DISTINCT runs.run_date
                FROM runs JOIN content_items ON content_items.run_id = runs.id
                WHERE content_items.status IN ('READY_FOR_REVIEW', 'OWNER_APPROVED', 'SCHEDULED')
                ORDER BY runs.run_date
                """
            )
        ]
        unknown_rights = int(
            self.database.scalar(
                """
                SELECT COUNT(*) FROM assets
                WHERE rights_status NOT IN ('OWNED', 'LICENSED', 'AI_GENERATED')
                """
            )
            or 0
        )
        real_publications = int(
            self.database.scalar(
                "SELECT COUNT(*) FROM publications WHERE provider LIKE 'instagram-native-manual%'"
            )
            or 0
        )
        mock_publications = int(
            self.database.scalar(
                "SELECT COUNT(*) FROM publications WHERE provider LIKE 'mock%'"
            )
            or 0
        )
        manual_analytics = int(
            self.database.scalar("SELECT COUNT(*) FROM manual_analytics_events") or 0
        )
        real_engagement_proposals = int(
            self.database.scalar(
                """
                SELECT COUNT(*) FROM engagement_queue q
                JOIN publications p ON p.id=q.publication_id
                WHERE q.status='PROPOSED' AND p.provider NOT LIKE 'mock%'
                """
            )
            or 0
        )
        queue_counts = _grouped(
            self.database.all(
                "SELECT status, COUNT(*) AS count FROM publish_queue GROUP BY status ORDER BY status"
            ),
            "status",
        )
        background_counts = _grouped(
            self.database.all(
                "SELECT status, COUNT(*) AS count FROM background_runs GROUP BY status ORDER BY status"
            ),
            "status",
        )
        blockers = Counter()
        if review_required:
            blockers["owner_review_required"] = review_required
        if unknown_rights:
            blockers["rights_status_unknown"] = unknown_rights
        if total_assets > real_assets:
            blockers["mock_assets_remaining"] = total_assets - real_assets

        tests = {
            "status": "unknown" if tests_passed is None and tests_failed is None else "passed",
            "passed": tests_passed,
            "failed": tests_failed,
        }
        if tests_failed:
            tests["status"] = "failed"

        return {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "app_version": self._app_version(),
            "schema_version": self.database.schema_version(),
            "git": self._git(),
            "personas": creators,
            "content": {
                "total": sum(status_counts.values()),
                "by_status": status_counts,
                "by_stage": stage_counts,
                "review_required": review_required,
                "mix_target_percent": mix.target_percent,
                "next_recommended_stage": mix.next_stage.value,
            },
            "assets": {
                "total": total_assets,
                "real": real_assets,
                "mock": total_assets - real_assets,
                "by_safety": safety_counts,
                "by_visibility": scope_counts,
            },
            "reserve": {
                "dates": reserve_dates,
                "days": len(reserve_dates),
                "through": reserve_dates[-1] if reserve_dates else None,
            },
            "publications": {
                "owner_confirmed_native": real_publications,
                "mock": mock_publications,
                "manual_analytics_events": manual_analytics,
                "local_queue": queue_counts,
            },
            "background_runs": background_counts,
            "engagement": {
                "real_post_proposals": real_engagement_proposals,
                "execution": "manual-owner-only",
            },
            "finance": {
                "cost_eur": float(self.database.scalar("SELECT COALESCE(SUM(amount), 0) FROM cost_events") or 0),
                "revenue_eur": float(self.database.scalar("SELECT COALESCE(SUM(amount), 0) FROM revenue_events") or 0),
                "adworks_real_revenue_eur": float(self.database.scalar("SELECT COALESCE(SUM(amount), 0) FROM funnel_events WHERE event_type IN ('order','purchase','subscription','tip','other_revenue') AND is_mock=0") or 0),
                "adworks_dry_run_revenue_eur": float(self.database.scalar("SELECT COALESCE(SUM(amount), 0) FROM funnel_events WHERE event_type IN ('order','purchase','subscription','tip','other_revenue') AND is_mock=1") or 0),
                "funnel_events_real": int(self.database.scalar("SELECT COUNT(*) FROM funnel_events WHERE is_mock=0") or 0),
                "funnel_events_dry_run": int(self.database.scalar("SELECT COUNT(*) FROM funnel_events WHERE is_mock=1") or 0),
                "paid_spend": "OWNER_GATE",
            },
            "remote": self._remote(include_remote_url),
            "tests": tests,
            "blockers": dict(blockers),
            "owner_decisions": {
                "source": "OWNER_DECISIONS.md",
                "red_gates": [
                    "live_publishing",
                    "adult_generation_or_publishing",
                    "cloud_permission_changes",
                    "irreversible_external_actions",
                    "paid_services",
                ],
            },
            "publishing_mode": (
                "human-gated local queue; official adapter available; "
                "live state depends on current owner/config gates"
            ),
        }

    @staticmethod
    def write(path: Path, snapshot: dict[str, object]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
        return path
