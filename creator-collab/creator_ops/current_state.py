from __future__ import annotations

import hashlib
import json
import re
import tomllib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .content_mix import ContentMixPlanner
from .database import CreatorDatabase
from .fiverr import FiverrAutomationService
from .external_readiness import ExternalReadinessService
from .instagram_dm import InstagramDMService
from .short_factory import ShortFactoryService


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

    def _owner_policy_provenance(self) -> dict[str, object]:
        """Describe the canonical policy without copying it into runtime state."""
        path = self.root.parent / "ZIPPOWORKZ_OWNER_POLICY.md"
        result: dict[str, object] = {
            "path": "../ZIPPOWORKZ_OWNER_POLICY.md",
            "role": "CANONICAL_OWNER_POLICY",
            "loaded": False,
            "version": "NOT_VERIFIED",
            "sha256": "NOT_VERIFIED",
        }
        try:
            payload = path.read_bytes()
            text = payload.decode("utf-8")
        except (OSError, UnicodeError):
            return result
        match = re.search(r"^Version:\s*(\S+)", text, flags=re.MULTILINE)
        result.update(
            {
                "loaded": True,
                "version": match.group(1) if match else "NOT_VERIFIED",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
        return result

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
        generated_at = datetime.now(UTC).isoformat(timespec="seconds")
        config_path = self.root / "config.toml"
        config = tomllib.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
        operational_db = config.get("runtime", {}).get(
            "database", "data/review_dashboard.db"
        )
        owner_policy = self._owner_policy_provenance()
        operations = config.get("operations", {})
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
        owner_confirmed_native = int(
            self.database.scalar(
                "SELECT COUNT(*) FROM publications WHERE provider LIKE 'instagram-native-manual%'"
            )
            or 0
        )
        official_meta_graph = int(
            self.database.scalar(
                """
                SELECT COUNT(*) FROM publications
                WHERE provider='instagram-meta-graph'
                  AND status='PUBLISHED'
                  AND external_id IS NOT NULL
                  AND external_url LIKE 'https://%.instagram.com/%'
                """
            )
            or 0
        )
        real_publications = owner_confirmed_native + official_meta_graph
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
        fiverr_status = FiverrAutomationService(self.database).status("zippoworkz")
        external = ExternalReadinessService(self.root, config_path).snapshot()
        short_factory = ShortFactoryService(self.database).dashboard()
        instagram_dm = InstagramDMService(self.database).dashboard(limit=10)
        if instagram_dm["counts"]["needs_human"]:
            blockers["instagram_dm_needs_human"] = instagram_dm["counts"]["needs_human"]

        return {
            "generated_at": generated_at,
            "state_contract": {
                "schema": "zippoworkz-current-state-v1",
                "role": "DERIVED_SECRET_FREE_SNAPSHOT",
                "authoritative_operational_store": operational_db,
                "sources": {
                    "operational_database": {
                        "path": operational_db,
                        "role": "CANONICAL_CREATOR_OPS_OPERATIONAL_STATE",
                    },
                    "runtime_config": {
                        "path": "config.toml",
                        "role": "RUNTIME_CONFIGURATION",
                    },
                    "owner_policy": owner_policy,
                },
                "unknown_semantics": "UNKNOWN_OR_NOT_VERIFIED_IS_NEVER_ZERO",
            },
            "product": {"name": "ZippoWorkz", "dashboard_path": "/", "launcher": "START_ZIPPOWORKZ.ps1",
                        "database": operational_db,
                        "core": "Creator Ops", "legacy_databases": ["data/creator_ops.db", "data/verification.db"]},
            "operations": {key: operations.get(key, "UNKNOWN") for key in
                           ("meta_api_status", "fiverr_identity_status", "fiverr_gig_status")},
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
                "owner_confirmed_native": owner_confirmed_native,
                "official_meta_graph": official_meta_graph,
                "mock": mock_publications,
                "manual_analytics_events": manual_analytics,
                "local_queue": queue_counts,
                "instagram_channel_real_live": bool(real_publications),
                "meta_graph_automation_proof": (
                    "proven_live" if official_meta_graph else "not_yet_proven"
                ),
            },
            "background_runs": background_counts,
            "fiverr": fiverr_status,
            "tiktok": external["tiktok"],
            "short_factory": {
                "schema": short_factory["schema"],
                "trend_briefs": short_factory["trend_briefs"],
                "patterns": short_factory["patterns"],
                "projects": short_factory["projects"],
                "by_status": short_factory["by_status"],
                "external_actions": short_factory["external_actions"],
                "cost_eur": short_factory["cost_eur"],
            },
            "engagement": {
                "real_post_proposals": real_engagement_proposals,
                "execution": "policy-controlled; no invented interactions or spam",
            },
            "instagram_dm": {
                "schema": instagram_dm["schema"],
                "mode": instagram_dm["mode"],
                "send_enabled": instagram_dm["send_enabled"],
                "webhook_registered": instagram_dm["webhook_registered"],
                "provider": instagram_dm["provider"],
                "provider_sync": instagram_dm["provider_sync"],
                "counts": instagram_dm["counts"],
                "by_intent": instagram_dm["by_intent"],
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
                "source": "ZIPPOWORKZ_OWNER_POLICY.md v1.2",
                "authoritative": False,
                "role": "DERIVED_COMPATIBILITY_SUMMARY",
                "source_sha256": owner_policy["sha256"],
                "pre_approved_actions": {
                    "instagram_official_live_publish": "PRE_APPROVED_WITH_SAFETY_GATES",
                    "instagram_normal_comments": "AUTONOMOUS_WITH_ANTI_SPAM_GUARDS",
                    "instagram_project_dms_and_targeted_outreach": "AUTONOMOUS_WITH_ANTI_SPAM_GUARDS",
                    "fiverr_existing_gig_optimization": "PRE_APPROVED_REVERSIBLE",
                    "tiktok_configured_project_workflows": "AUTONOMOUS_WITH_PLATFORM_AND_SAFETY_GATES",
                    "git_project_branches_commits_pushes": "PRE_APPROVED_NO_FORCE_PUSH",
                },
                "owner_only_gates": [
                    "new_accounts_or_new_external_identity",
                    "kyc_otp_or_personal_verification",
                    "new_format_offer_or_cost_class",
                    "critical_security_auth_schema_or_publishing_core_merge_to_main",
                ],
                "red_gates": [
                    "new_costs_paid_services_ads_or_credits",
                    "adult_pipeline_without_separate_explicit_authorization",
                    "force_push_or_history_rewrite",
                    "destructive_irreversible_or_account_deletion_actions",
                    "secret_values_in_git_logs_prompts_or_docs",
                ],
            },
            "publishing_mode": (
                "DO_LOG_VERIFY; known SFW/PUBLIC_SFW lanes may run autonomously "
                "through official configured adapters; reconcile uncertain writes; "
                "new identity, cost and critical merge classes remain owner gates"
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
