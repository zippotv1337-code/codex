from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Any


META_ENV_VARS = (
    "META_IG_USER_ID_LEONA_VOSS",
    "META_ACCESS_TOKEN_LEONA_VOSS",
    "META_IG_USER_ID_MARA_FIELD",
    "META_ACCESS_TOKEN_MARA_FIELD",
    "META_GRAPH_API_VERSION",
    "META_GRAPH_HOST",
    "CREATOR_OPS_META_MEDIA_MANIFEST",
)


class ExternalReadinessService:
    """Secret-free readiness snapshot for external output lanes.

    The service intentionally reports only whether expected values are present
    and structurally plausible. It never returns tokens, passwords, cookies, or
    value lengths.
    """

    def __init__(self, project_root: Path, config_path: Path | None = None) -> None:
        self.project_root = project_root
        self.config_path = config_path or project_root / "config.toml"

    def snapshot(self) -> dict[str, Any]:
        meta = self._meta()
        fiverr = self._fiverr()
        handoff_zip = self._handoff_zip()
        next_actions = self._next_actions(meta, fiverr, handoff_zip)
        return {
            "schema": "creator-ops-external-readiness-v1",
            "meta": meta,
            "fiverr": fiverr,
            "handoff_zip": handoff_zip,
            "next_actions": next_actions,
        }

    def _meta(self) -> dict[str, Any]:
        config = self._config()
        env = [self._env_state(name) for name in META_ENV_VARS]
        missing = [item["name"] for item in env if not item["set"]]
        invalid = [item["name"] for item in env if item["set"] and not item["valid_hint"]]
        blockers: list[str] = []
        publishing = config.get("publishing", {})
        scheduler = config.get("scheduler", {})
        capabilities = config.get("capabilities", {})

        if missing:
            blockers.append("meta_required_env_missing")
        if invalid:
            blockers.append("meta_env_structural_hint_failed")
        if publishing.get("adapter") != "meta-graph":
            blockers.append("publishing_adapter_not_meta_graph")
        if not publishing.get("live_enabled", False):
            blockers.append("publishing_live_enabled_false")
        if not scheduler.get("dispatch_live", False):
            blockers.append("scheduler_dispatch_live_false")
        if not capabilities.get("official_instagram_publish", False):
            blockers.append("official_instagram_publish_false")
        if not capabilities.get("live_external_actions", False):
            blockers.append("live_external_actions_false")

        return {
            "status": ("DEFERRED_OWNER_VERIFICATION" if config.get("operations", {}).get("meta_api_status") == "DEFERRED_OWNER_VERIFICATION"
                       else "READY_FOR_PREFLIGHT" if not blockers else "BLOCKED"),
            "env": env,
            "config": {
                "adapter": publishing.get("adapter"),
                "live_enabled": bool(publishing.get("live_enabled", False)),
                "dispatch_live": bool(scheduler.get("dispatch_live", False)),
                "official_instagram_publish_adapter": bool(
                    capabilities.get("official_instagram_publish_adapter", False)
                ),
                "official_instagram_publish": bool(
                    capabilities.get("official_instagram_publish", False)
                ),
                "live_external_actions": bool(
                    capabilities.get("live_external_actions", False)
                ),
            },
            "blockers": blockers,
        }

    def _config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return tomllib.loads(self.config_path.read_text(encoding="utf-8"))

    def _env_state(self, name: str) -> dict[str, Any]:
        value = os.environ.get(name)
        return {
            "name": name,
            "set": bool(value),
            "valid_hint": self._valid_env_hint(name, value),
        }

    def _valid_env_hint(self, name: str, value: str | None) -> bool:
        if not value:
            return False
        if name.startswith("META_IG_USER_ID_"):
            return value.isdigit()
        if name == "META_GRAPH_API_VERSION":
            return re.fullmatch(r"v\d+\.\d+", value) is not None
        if name == "META_GRAPH_HOST":
            return value in {"graph.facebook.com", "graph.instagram.com"}
        if name == "CREATOR_OPS_META_MEDIA_MANIFEST":
            manifest = Path(value)
            if not manifest.is_absolute():
                manifest = self.project_root / manifest
            return manifest.exists() and manifest.is_file()
        return True

    def _fiverr(self) -> dict[str, Any]:
        evidence = "\n".join(
            self._read_optional(path)
            for path in (
                self.project_root / "CURRENT_HANDOFF.md",
                self.project_root / "LIVE_EVIDENCE.md",
                self.project_root / "docs" / "HUMAN_HANDOFF.md",
            )
        ).lower()
        draft = self.project_root / "docs" / "FIVERR_GIG_DRAFT.md"
        catalog = self.project_root / "docs" / "FIVERR_GIG1_PACKAGE_CATALOG.md"
        blockers: list[str] = []
        identity = self._config().get("operations", {}).get("fiverr_identity_status", "UNKNOWN")
        if identity != "OWNER_REPORTED_VERIFIED" and ("create your profile" in evidence or "owner_identity" in evidence):
            blockers.append("fiverr_waiting_for_owner_identity_or_seller_profile")
        if not draft.exists():
            blockers.append("fiverr_gig_draft_missing")
        return {
            "status": "READY_FOR_OWNER_PROFILE_CHECK" if not blockers else "BLOCKED",
            "identity_status": identity,
            "gig_status": self._config().get("operations", {}).get("fiverr_gig_status", "UNKNOWN"),
            "gig_draft_present": draft.exists(),
            "package_catalog_present": catalog.exists(),
            "blockers": blockers,
        }

    def _handoff_zip(self) -> dict[str, Any]:
        output_dir = self.project_root / "output"
        zips = sorted(output_dir.glob("CREATOR_OPS_LIVE_HANDOFF_NO_BACKUP_*.zip"))
        latest = zips[-1] if zips else None
        return {
            "status": "READY_LOCAL_FILE" if latest else "MISSING",
            "latest": str(latest) if latest else None,
            "mirror_status": "NEEDS_OWNER_UPLOAD_OR_REACHABLE_PRIVATE_TARGET",
        }

    def _next_actions(
        self,
        meta: dict[str, Any],
        fiverr: dict[str, Any],
        handoff_zip: dict[str, Any],
    ) -> list[str]:
        actions: list[str] = []
        if meta["status"] == "BLOCKED":
            actions.append(
                "Set missing Meta env/config gates, then run meta-preflight for one exact package."
            )
        elif meta["status"] != "DEFERRED_OWNER_VERIFICATION":
            actions.append("Run one controlled Meta preflight; reconcile before retrying any publish.")
        if fiverr["status"] == "BLOCKED":
            actions.append("Finish Fiverr seller profile / identity gate manually, then publish Gig 1.")
        if handoff_zip["status"] == "READY_LOCAL_FILE":
            actions.append("Upload the latest handoff ZIP to ChatGPT/Work mirror manually or provide a reachable target.")
        return actions

    @staticmethod
    def _read_optional(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
