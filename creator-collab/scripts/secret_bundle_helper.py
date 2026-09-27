from __future__ import annotations

import argparse
import importlib.util
import json
import os
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(r"C:\Zippoworkz")
PROJECT = ROOT / "Workspace" / "codex_ingest" / "creator-collab"
BROKER_PATH = ROOT / "_system" / "SECRET_BROKER.py"
CATALOG_PATH = PROJECT / "config" / "connector_secret_catalog.json"
SCHEMA = "zippoworkz-secret-bundle-v2"


def load_broker():
    spec = importlib.util.spec_from_file_location(
        "zippoworkz_secret_broker", BROKER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("secret_broker_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def load_catalog() -> dict[str, object]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8-sig"))
    if payload.get("schema") != "zippoworkz-connector-secret-catalog-v1":
        raise RuntimeError("connector_secret_catalog_invalid")
    connectors = payload.get("connectors")
    if not isinstance(connectors, dict):
        raise RuntimeError("connector_secret_catalog_invalid")
    return connectors


def connector_config(scope: str) -> tuple[str, list[str]]:
    item = load_catalog().get(scope)
    if not isinstance(item, dict):
        raise SystemExit("connector_scope_unknown")
    worker = str(item.get("worker") or "").strip()
    names = [
        str(name).strip()
        for name in item.get("secret_names", [])
        if str(name).strip()
    ]
    if not worker:
        raise SystemExit("connector_worker_missing")
    return worker, names
def status_payload(scope: str) -> int:
    worker, names = connector_config(scope)
    broker = load_broker()
    metadata = {item.get("name"): item for item in broker.metadata()}
    present = {
        name: bool(
            isinstance(metadata.get(name), dict)
            and metadata[name].get("present")
            and worker in (metadata[name].get("allowed_workers") or [])
        )
        for name in names
    }
    print(
        json.dumps(
            {
                "scope": scope,
                "worker": worker,
                "secret_names": names,
                "present": present,
                "ready": bool(names) and all(present.values()),
            },
            ensure_ascii=False,
        )
    )
    return 0
def export_payload(scope: str) -> int:
    if os.environ.get("ZW_SECRET_EXPORT_INTERNAL") != "1":
        raise SystemExit("secret_export_internal_guard_required")
    worker, names = connector_config(scope)
    if not names:
        raise SystemExit("connector_has_no_replicated_secrets")
    broker = load_broker()
    secrets = {name: broker.get_for_broker(name, worker) for name in names}
    payload = {
        "schema": SCHEMA,
        "scope": scope,
        "worker": worker,
        "created_at": datetime.now(UTC).isoformat(),
        "secret_names": names,
        "secrets": secrets,
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0
def import_payload(scope: str) -> int:
    raw = os.environ.get("ZW_SECRET_PAYLOAD", "")
    if not raw:
        raise SystemExit("secret_payload_missing")
    payload = json.loads(raw)
    worker, names = connector_config(scope)
    if payload.get("schema") != SCHEMA or payload.get("scope") != scope:
        raise SystemExit("secret_payload_schema_invalid")
    if payload.get("worker") != worker:
        raise SystemExit("secret_payload_worker_mismatch")
    secrets = payload.get("secrets")
    if not isinstance(secrets, dict):
        raise SystemExit("secret_payload_invalid")
    missing = [name for name in names if not str(secrets.get(name, "")).strip()]
    if missing:
        raise SystemExit("secret_payload_incomplete")
    broker = load_broker()
    for name in names:
        value = str(secrets[name])
        broker.set_secret(name, value, allowed_workers=[worker])
        if broker.get_for_broker(name, worker) != value:
            raise RuntimeError(f"secret_roundtrip_failed:{name}")
    print(
        json.dumps(
            {"ok": True, "scope": scope, "imported": names, "worker": worker},
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("status", "export", "import-env"))
    parser.add_argument("scope")
    args = parser.parse_args()
    if args.action == "status":
        return status_payload(args.scope)
    if args.action == "export":
        return export_payload(args.scope)
    return import_payload(args.scope)


if __name__ == "__main__":
    raise SystemExit(main())
