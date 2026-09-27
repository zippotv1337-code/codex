from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(r"C:\Zippoworkz")
PATH = ROOT / "Context" / "Owner" / "PUBLISHING_AUTHORITY.json"
ALLOWED = {"ZIPPOWORKZ-VPS", "ZIPPOWORKZ-LOCALAI"}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, choices=sorted(ALLOWED))
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    reason = args.reason.strip()
    if len(reason) < 4:
        raise SystemExit("reason_required")
    current = {}
    if PATH.is_file():
        try:
            current = json.loads(PATH.read_text(encoding="utf-8-sig"))
        except Exception:
            current = {}
    payload = {
        "schema": "zippoworkz-publishing-authority-v1",
        "active_node": args.target,
        "standby_nodes": [node for node in sorted(ALLOWED) if node != args.target],
        "failover_mode": "owner_or_verified_outage",
        "updated_at": datetime.now(UTC).isoformat(),
        "reason": reason,
        "previous_active_node": current.get("active_node"),
    }
    PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(PATH)
    print(json.dumps({
        "ok": True,
        "active_node": payload["active_node"],
        "standby_nodes": payload["standby_nodes"],
        "updated_at": payload["updated_at"],
    }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
