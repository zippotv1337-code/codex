from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_ROOT = Path(r"C:\Zippoworkz")

def _root() -> Path:
    configured = os.environ.get("ZIPPOWORKZ_ROOT", "").strip()
    return Path(configured) if configured else DEFAULT_ROOT

def status() -> dict[str, object]:
    root = _root()
    machine_path = root / "MACHINE_ID.json"
    authority_path = root / "Context" / "Owner" / "PUBLISHING_AUTHORITY.json"
    if not machine_path.is_file():
        return {"enforced": False, "allowed": True, "reason": "machine_identity_not_present"}
    try:
        machine = json.loads(machine_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"enforced": True, "allowed": False, "error": "machine_identity_invalid"}
    current = str(machine.get("machine_id") or "").strip()
    if not current:
        return {"enforced": True, "allowed": False, "error": "machine_id_missing"}
    if not authority_path.is_file():
        return {
            "enforced": True,
            "allowed": False,
            "current_node": current,
            "error": "publishing_authority_missing",
        }
    try:
        authority = json.loads(authority_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {
            "enforced": True,
            "allowed": False,
            "current_node": current,
            "error": "publishing_authority_invalid",
        }
    active = str(authority.get("active_node") or "").strip()
    if not active:
        return {
            "enforced": True,
            "allowed": False,
            "current_node": current,
            "error": "publishing_active_node_missing",
        }
    allowed = current == active
    return {
        "enforced": True,
        "allowed": allowed,
        "current_node": current,
        "active_node": active,
        "standby_nodes": authority.get("standby_nodes") or [],
        "error": None if allowed else "publishing_standby_node",
    }

def live_publish_error() -> str | None:
    state = status()
    if state.get("allowed"):
        return None
    return str(state.get("error") or "publishing_authority_blocked")
