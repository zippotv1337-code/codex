from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\Zippoworkz")
PROJECT = ROOT / "Workspace" / "codex_ingest" / "creator-collab"
sys.path.insert(0, str(PROJECT))

from creator_ops.authority import status as authority_status
from creator_ops.publishing import UrllibMetaGraphTransport
from creator_ops.secrets import get_secret

EXPECTED = (
    "META_IG_USER_ID_LEONA_VOSS",
    "META_ACCESS_TOKEN_LEONA_VOSS",
    "META_IG_USER_ID_MARA_FIELD",
    "META_ACCESS_TOKEN_MARA_FIELD",
    "META_GRAPH_API_VERSION",
    "META_GRAPH_HOST",
)

def machine() -> dict[str, object]:
    try:
        return json.loads((ROOT / "MACHINE_ID.json").read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    values = {name: get_secret(name) for name in EXPECTED}
    result: dict[str, object] = {
        "machine_id": machine().get("machine_id"),
        "secrets_present": {name: bool(values[name]) for name in EXPECTED},
        "ready_local": all(bool(values[name]) for name in EXPECTED),
        "accounts": [],
        "publishing_authority": authority_status(),
    }
    if not args.live or not result["ready_local"]:
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ready_local"] else 2

    version = values["META_GRAPH_API_VERSION"]
    host = values["META_GRAPH_HOST"] or "graph.instagram.com"
    accounts = (
        ("leona-voss", "LEONA_VOSS", "leonavoss.ai"),
        ("mara-field", "MARA_FIELD", "mara.field.ai"),
    )
    rows = []
    for slug, suffix, expected in accounts:
        uid = values[f"META_IG_USER_ID_{suffix}"]
        token = values[f"META_ACCESS_TOKEN_{suffix}"]
        transport = UrllibMetaGraphTransport(version, token, graph_host=host, timeout=25)
        identity = transport.get(uid, {"fields": "id,username,account_type"})
        quota = transport.get(f"{uid}/content_publishing_limit", {"fields": "quota_usage,config"})
        rows.append({
            "slug": slug,
            "username": identity.get("username"),
            "username_match": str(identity.get("username", "")).lower() == expected.lower(),
            "account_type": identity.get("account_type"),
            "quota": quota.get("data"),
        })
    result["accounts"] = rows
    result["ready_live"] = all(bool(row["username_match"]) for row in rows)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ready_live"] else 3

if __name__ == "__main__":
    raise SystemExit(main())
