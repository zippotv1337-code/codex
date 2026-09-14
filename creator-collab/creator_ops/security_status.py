from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .secret_provider import DEFAULT_ALIAS_ENV, create_secret_provider


class SecurityStatusService:
    """Value-free policy/provider status for the local owner dashboard."""

    def __init__(self, project_root: Path, system_root: Path | None = None) -> None:
        self.project_root = Path(project_root).resolve()
        self.system_root = (system_root or self._default_system_root()).resolve()

    def _default_system_root(self) -> Path:
        configured = os.environ.get("ZIPPOWORKZ_ROOT")
        if configured:
            return Path(configured)
        if (
            self.project_root.parent.name == "codex_ingest"
            and self.project_root.parent.parent.name == "Workspace"
        ):
            return self.project_root.parent.parent.parent
        return self.project_root

    @staticmethod
    def _json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _hook_path(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "config", "--local", "--get", "core.hooksPath"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip() or None

    def snapshot(self) -> dict[str, Any]:
        policy_path = self.system_root / "_system" / "PERMISSIONS_POLICY.json"
        schema_path = self.system_root / "_system" / "HANDOFF_SCHEMA.json"
        policy = self._json(policy_path)
        schema = self._json(schema_path)
        provider = create_secret_provider()
        aliases = []
        for alias in DEFAULT_ALIAS_ENV:
            try:
                configured = provider.has(alias)
            except (OSError, ValueError):
                configured = False
            aliases.append({"alias": alias, "configured": configured})
        hook_path = self._hook_path()
        hook_file = self.project_root / ".githooks" / "pre-push"
        return {
            "schema": "zippoworkz-security-status-v1",
            "policy": {
                "installed": bool(policy),
                "version": policy.get("version"),
                "mode": policy.get("mode", "MISSING"),
                "source": str(policy_path),
                "secret_values_exposed": False,
            },
            "secret_provider": {
                "provider": provider.provider_id,
                "ready": provider.ready,
                "configured_count": sum(1 for item in aliases if item["configured"]),
                "known_alias_count": len(aliases),
                "aliases": aliases,
                "values_exposed": False,
            },
            "handoff": {
                "schema_installed": bool(schema),
                "schema_version": schema.get("schema_version"),
                "required_fields": len(schema.get("required", [])),
            },
            "leak_check": {
                "script_installed": (self.project_root / "scripts" / "check_secret_leaks.py").is_file(),
                "hook_file_installed": hook_file.is_file(),
                "git_hook_path": hook_path,
                "active": hook_file.is_file() and hook_path == "creator-collab/.githooks",
            },
            "owner_action": (
                None
                if provider.ready and any(item["configured"] for item in aliases)
                else "Choose and connect one password manager or Windows Credential Manager entry set."
            ),
        }
