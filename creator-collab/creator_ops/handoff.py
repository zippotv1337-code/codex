from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .secret_provider import validate_alias
from .secret_scan import scan_text


class HandoffValidationError(ValueError):
    pass


class HandoffService:
    def __init__(self, schema_path: Path, exchange_root: Path) -> None:
        self.schema_path = Path(schema_path)
        self.exchange_root = Path(exchange_root)

    def schema(self) -> dict[str, Any]:
        payload = json.loads(self.schema_path.read_text(encoding="utf-8"))
        if not isinstance(payload.get("required"), list) or not isinstance(
            payload.get("status_values"), list
        ):
            raise HandoffValidationError("invalid_handoff_schema")
        return payload

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        schema = self.schema()
        missing = [key for key in schema["required"] if key not in payload]
        if missing:
            raise HandoffValidationError("missing_handoff_fields:" + ",".join(missing))
        if payload["status"] not in schema["status_values"]:
            raise HandoffValidationError("invalid_handoff_status")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,100}", str(payload["run_id"])):
            raise HandoffValidationError("invalid_run_id")
        try:
            datetime.fromisoformat(str(payload["timestamp"]).replace("Z", "+00:00"))
        except ValueError as error:
            raise HandoffValidationError("invalid_handoff_timestamp") from error
        aliases = payload.get("secret_aliases_used")
        if not isinstance(aliases, list):
            raise HandoffValidationError("secret_aliases_used_must_be_list")
        for alias in aliases:
            validate_alias(str(alias))
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        findings = scan_text(serialized, "handoff")

        # JSON escaping can hide a quoted assignment from a line-based scan
        # (for example access_token=\"...\"). Scan each original string too.
        def strings(value: Any):
            if isinstance(value, str):
                yield value
            elif isinstance(value, list):
                for item in value:
                    yield from strings(item)
            elif isinstance(value, dict):
                for item in value.values():
                    yield from strings(item)

        for value in strings(payload):
            findings.extend(scan_text(value, "handoff-field"))
        if findings:
            raise HandoffValidationError("handoff_contains_possible_secret")
        return payload

    @staticmethod
    def _markdown(payload: dict[str, Any]) -> str:
        def render(value: Any) -> str:
            if isinstance(value, list):
                return "\n".join(f"- {item}" for item in value) if value else "- NONE"
            if isinstance(value, dict):
                return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"
            return str(value)

        labels = (
            ("run_id", "Run-ID"),
            ("agent", "Agent / Rolle"),
            ("timestamp", "Zeit"),
            ("objective", "Ziel"),
            ("inputs", "Gelesene Inputs"),
            ("changes", "Änderungen"),
            ("tests", "Tests / Verifikation"),
            ("external_actions", "Externe Aktionen"),
            ("secret_aliases_used", "Verwendete Secret-Aliase"),
            ("blockers", "Blocker"),
            ("owner_actions", "Owner-Aktionen"),
            ("next_agent", "Nächster Agent"),
            ("next_step", "Nächster Schritt"),
            ("status", "Status"),
        )
        parts = ["# ZippoWorkz — Codex Handoff", ""]
        for key, label in labels:
            parts.extend((f"## {label}", "", render(payload[key]), ""))
        return "\n".join(parts).rstrip() + "\n"

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)

    def write(self, payload: dict[str, Any]) -> dict[str, str]:
        self.validate(payload)
        current = self.exchange_root / "Current"
        archive = self.exchange_root / "Archive"
        current.mkdir(parents=True, exist_ok=True)
        archive.mkdir(parents=True, exist_ok=True)
        markdown_path = current / "CODEX_HANDOFF_CURRENT.md"
        json_path = current / "CODEX_HANDOFF_CURRENT.json"
        # Microseconds avoid archive collisions when two agents/checkpoints
        # complete within the same second.
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        if markdown_path.is_file():
            archived = archive / f"CODEX_HANDOFF_{stamp}.md"
            self._atomic_write(archived, markdown_path.read_text(encoding="utf-8"))
        markdown = self._markdown(payload)
        serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        self._atomic_write(markdown_path, markdown)
        self._atomic_write(json_path, serialized)
        self._atomic_write(archive / f"CODEX_HANDOFF_{stamp}.json", serialized)
        return {"current_markdown": str(markdown_path), "current_json": str(json_path)}


def build_handoff(
    *,
    run_id: str,
    objective: str,
    changes: list[str],
    tests: dict[str, Any],
    blockers: list[str],
    owner_actions: list[str],
    next_step: str,
    status: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "agent": "Codex",
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "objective": objective,
        "inputs": ["ZIPPOWORKZ_CODEX_PACKAGE_20260914.zip", "current workspace handoff"],
        "changes": changes,
        "tests": tests,
        "external_actions": [],
        "secret_aliases_used": [],
        "blockers": blockers,
        "owner_actions": owner_actions,
        "next_agent": "Owner or next Codex run",
        "next_step": next_step,
        "status": status,
    }
