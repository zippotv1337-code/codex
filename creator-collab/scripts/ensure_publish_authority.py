from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(r"C:\Zippoworkz")
PATH = ROOT / "Context" / "Owner" / "PUBLISHING_AUTHORITY.json"
SCHEMA = "zippoworkz-publishing-authority-v1"
NODES = {"ZIPPOWORKZ-VPS", "ZIPPOWORKZ-LOCALAI"}

def validate(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("schema") != SCHEMA:
        return False
    active = str(payload.get("active_node") or "")
    standby = set(payload.get("standby_nodes") or [])
    return active in NODES and standby.issubset(NODES) and active not in standby

def main() -> int:
    if PATH.is_file():
        try:
            payload = json.loads(PATH.read_text(encoding="utf-8-sig"))
        except Exception:
            raise SystemExit("publishing_authority_invalid_json")
        if not validate(payload):
            raise SystemExit("publishing_authority_invalid")
        print(json.dumps({"ok": True, "changed": False, "active_node": payload["active_node"]}))
        return 0

    payload = {
        "schema": SCHEMA,
        "active_node": "ZIPPOWORKZ-VPS",
        "standby_nodes": ["ZIPPOWORKZ-LOCALAI"],
        "failover_mode": "owner_or_verified_outage",
        "updated_at": datetime.now(UTC).isoformat(),
        "reason": "Safe default: VPS primary, Local AI standby.",
    }
    PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(PATH)
    print(json.dumps({"ok": True, "changed": True, "active_node": payload["active_node"]}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
