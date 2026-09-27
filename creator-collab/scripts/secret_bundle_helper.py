from __future__ import annotations

import importlib.util
import json
import os
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(r"C:\Zippoworkz")
BROKER_PATH = ROOT / "_system" / "SECRET_BROKER.py"
WORKER = "creator-ops-meta"
SCHEMA = "zippoworkz-secret-bundle-v1"
SCOPE = "meta-instagram"
EXPECTED = (
    "META_IG_USER_ID_LEONA_VOSS",
    "META_ACCESS_TOKEN_LEONA_VOSS",
    "META_IG_USER_ID_MARA_FIELD",
    "META_ACCESS_TOKEN_MARA_FIELD",
    "META_GRAPH_API_VERSION",
    "META_GRAPH_HOST",
)

def load_broker():
    spec = importlib.util.spec_from_file_location("zippoworkz_secret_broker", BROKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("secret_broker_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def export_payload() -> int:
    broker = load_broker()
    secrets = {name: broker.get_for_broker(name, WORKER) for name in EXPECTED}
    payload = {
        "schema": SCHEMA,
        "scope": SCOPE,
        "created_at": datetime.now(UTC).isoformat(),
        "secrets": secrets,
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0

def import_payload() -> int:
    raw = os.environ.get("ZW_SECRET_PAYLOAD", "")
    if not raw:
        raise SystemExit("secret_payload_missing")
    payload = json.loads(raw)
    if payload.get("schema") != SCHEMA or payload.get("scope") != SCOPE:
        raise SystemExit("secret_payload_schema_invalid")
    secrets = payload.get("secrets")
    if not isinstance(secrets, dict):
        raise SystemExit("secret_payload_invalid")
    missing = [name for name in EXPECTED if not str(secrets.get(name, "")).strip()]
    if missing:
        raise SystemExit("secret_payload_incomplete")
    broker = load_broker()
    for name in EXPECTED:
        value = str(secrets[name])
        broker.set_secret(name, value, allowed_workers=[WORKER])
        if broker.get_for_broker(name, WORKER) != value:
            raise RuntimeError(f"secret_roundtrip_failed:{name}")
    print(json.dumps({"ok": True, "imported": list(EXPECTED), "worker": WORKER}))
    return 0

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "export":
        raise SystemExit(export_payload())
    if action == "import-env":
        raise SystemExit(import_payload())
    raise SystemExit("usage: secret_bundle_helper.py export|import-env")
