from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Any

from .secrets import get_secret


META_ENV_VARS = (
    "META_IG_USER_ID_LEONA_VOSS",
    "META_ACCESS_TOKEN_LEONA_VOSS",
    "META_IG_USER_ID_MARA_FIELD",
    "META_ACCESS_TOKEN_MARA_FIELD",
    "META_GRAPH_API_VERSION",
    "META_GRAPH_HOST",
    "CREATOR_OPS_META_MEDIA_MANIFEST",
)

TIKTOK_ENV_VARS = (
    "TIKTOK_CLIENT_KEY",
    "TIKTOK_CLIENT_SECRET",
    "TIKTOK_REDIRECT_URI",
    "TIKTOK_ACCESS_TOKEN",
    "TIKTOK_REFRESH_TOKEN",
    "TIKTOK_OPEN_ID",
    "TIKTOK_SCOPES",
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
        tiktok = self._tiktok()
        fiverr = self._fiverr()
        handoff_zip = self._handoff_zip()
        next_actions = self._next_actions(meta, tiktok, fiverr, handoff_zip)
        return {
            "schema": "creator-ops-external-readiness-v1",
            "meta": meta,
            "tiktok": tiktok,
            "fiverr": fiverr,
            "handoff_zip": handoff_zip,
            "next_actions": next_actions,
        }

    def _meta(self) -> dict[str, Any]:
        config = self._config()
        env = [self._env_state(name) for name in META_ENV_VARS]
        default_manifest = self.project_root / "data" / "meta_media_urls.json"
        manifest_available = any(
            item["name"] == "CREATOR_OPS_META_MEDIA_MANIFEST"
            and item["valid_hint"]
            for item in env
        ) or default_manifest.is_file()
        missing = [
            item["name"]
            for item in env
            if not item["set"]
            and not (
                item["name"] == "CREATOR_OPS_META_MEDIA_MANIFEST"
                and manifest_available
            )
        ]
        invalid = [item["name"] for item in env if item["set"] and not item["valid_hint"]]
        blockers: list[str] = []
        publishing = config.get("publishing", {})
        scheduler = config.get("scheduler", {})
        capabilities = config.get("capabilities", {})
        meta_api_status = str(
            config.get("operations", {}).get("meta_api_status", "UNKNOWN")
        )
        controlled_publish_proven = meta_api_status.startswith("PROVEN_LIVE")

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
            "status": (
                "DEFERRED_OWNER_VERIFICATION"
                if meta_api_status == "DEFERRED_OWNER_VERIFICATION"
                else "PROVEN_CONTROLLED_ONLY"
                if controlled_publish_proven
                else "READY_FOR_PREFLIGHT"
                if not blockers
                else "BLOCKED"
            ),
            "env": env,
            "manifest": {
                "available": manifest_available,
                "source": (
                    "environment"
                    if any(
                        item["name"] == "CREATOR_OPS_META_MEDIA_MANIFEST"
                        and item["valid_hint"]
                        for item in env
                    )
                    else "default-local"
                    if default_manifest.is_file()
                    else "missing"
                ),
            },
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
            "controlled_publish_proven": controlled_publish_proven,
            "unattended_automation_enabled": not blockers,
            "blockers": blockers,
        }

    def _config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return tomllib.loads(self.config_path.read_text(encoding="utf-8"))

    def _node_root(self) -> Path | None:
        current = self.project_root.resolve()
        for candidate in (current, *current.parents):
            if (candidate / "_system" / "SECRET_BROKER.py").is_file():
                return candidate
        return None

    def _env_state(self, name: str) -> dict[str, Any]:
        node_root = self._node_root()
        if name == "CREATOR_OPS_META_MEDIA_MANIFEST" or node_root is None:
            value = os.environ.get(name)
        else:
            value = get_secret(name, root=node_root)
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

    def _tiktok_env_state(self, name: str) -> dict[str, Any]:
        node_root = self._node_root()
        value = (
            os.environ.get(name)
            if node_root is None
            else get_secret(name, worker="creator-ops-tiktok", root=node_root)
        )
        valid = bool(value)
        if name == "TIKTOK_REDIRECT_URI" and value:
            parsed = urllib_parse(value)
            valid = parsed[0] == "https" and bool(parsed[1])
        elif name == "TIKTOK_SCOPES" and value:
            scopes = {item.strip() for item in value.split(",") if item.strip()}
            valid = bool(scopes & {"video.upload", "video.publish"})
        return {"name": name, "set": bool(value), "valid_hint": valid}

    def _tiktok(self) -> dict[str, Any]:
        env = [self._tiktok_env_state(name) for name in TIKTOK_ENV_VARS]
        states = {item["name"]: item for item in env}
        configuration_names = {
            "TIKTOK_CLIENT_KEY",
            "TIKTOK_CLIENT_SECRET",
            "TIKTOK_REDIRECT_URI",
        }
        connection_names = {
            "TIKTOK_ACCESS_TOKEN",
            "TIKTOK_REFRESH_TOKEN",
            "TIKTOK_OPEN_ID",
            "TIKTOK_SCOPES",
        }
        config_ready = all(states[name]["valid_hint"] for name in configuration_names)
        connected = config_ready and all(
            states[name]["valid_hint"] for name in connection_names
        )
        node_root = self._node_root()
        scope_value = (
            get_secret(
                "TIKTOK_SCOPES",
                worker="creator-ops-tiktok",
                root=node_root,
            )
            if node_root is not None
            else os.environ.get("TIKTOK_SCOPES", "")
        )
        scopes = {item.strip() for item in scope_value.split(",") if item.strip()}
        blockers: list[str] = []
        if not config_ready:
            blockers.append("tiktok_app_or_redirect_configuration_missing")
        elif not connected:
            blockers.append("tiktok_owner_oauth_consent_required")
        return {
            "status": (
                "CONNECTED" if connected else "READY_FOR_OWNER_OAUTH" if config_ready else "BLOCKED"
            ),
            "env": env,
            "oauth_configured": config_ready,
            "credentials_connected": connected,
            "direct_post_ready": connected and "video.publish" in scopes,
            "blockers": blockers,
            "secrets_exposed": False,
        }

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
        tiktok: dict[str, Any],
        fiverr: dict[str, Any],
        handoff_zip: dict[str, Any],
    ) -> list[str]:
        actions: list[str] = []
        if meta["status"] == "PROVEN_CONTROLLED_ONLY":
            actions.append(
                "Controlled Meta publishing is proven; rotate exposed tokens locally before long-term production."
            )
        elif meta["status"] == "BLOCKED":
            actions.append(
                "Set missing Meta env/config gates, then run meta-preflight for one exact package."
            )
        elif meta["status"] != "DEFERRED_OWNER_VERIFICATION":
            actions.append("Run one controlled Meta preflight; reconcile before retrying any publish.")
        if tiktok["status"] == "READY_FOR_OWNER_OAUTH":
            actions.append(
                "Complete one TikTok OAuth consent for the configured app; ZippoWorkz resumes automatically after callback."
            )
        elif tiktok["status"] == "BLOCKED":
            actions.append(
                "Configure the TikTok app client and registered HTTPS redirect in the node-local Secret Broker."
            )
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


def urllib_parse(value: str) -> tuple[str, str]:
    """Return only scheme/netloc so readiness never echoes URL details."""
    from urllib.parse import urlparse

    parsed = urlparse(value)
    return parsed.scheme, parsed.netloc
