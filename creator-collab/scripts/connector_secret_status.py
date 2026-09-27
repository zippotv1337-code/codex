from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(r"C:\Zippoworkz")
PROJECT = ROOT / "Workspace" / "codex_ingest" / "creator-collab"
CATALOG = PROJECT / "config" / "connector_secret_catalog.json"
BROKER = ROOT / "_system" / "SECRET_BROKER.py"


def load_broker():
    spec = importlib.util.spec_from_file_location("zippoworkz_secret_broker", BROKER)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    broker = load_broker()
    metadata: dict[str, dict[str, object]] = {}
    if broker is not None:
        metadata = {
            str(item.get("name")): item
            for item in broker.metadata()
            if item.get("name")
        }

    rows: dict[str, dict[str, object]] = {}
    for name, spec in catalog.get("connectors", {}).items():
        worker = str(spec.get("worker") or "")
        names = [str(item) for item in spec.get("secret_names", []) if str(item)]
        present = {
            secret: bool(
                isinstance(metadata.get(secret), dict)
                and metadata[secret].get("present")
                and worker in (metadata[secret].get("allowed_workers") or [])
            )
            for secret in names
        }
        missing = [secret for secret, ok in present.items() if not ok]
        managed_auth = spec.get("status") == "MANAGED_AUTH"
        broker_ready = bool(names) and not missing
        rows[name] = {
            "configured_status": spec.get("status"),
            "worker": worker,
            "replicate": bool(spec.get("replicate")),
            "accounts": spec.get("accounts", []),
            "owner_gate": spec.get("owner_gate"),
            "required_names": names,
            "present_names": [secret for secret, ok in present.items() if ok],
            "missing_names": missing,
            "broker_ready": broker_ready,
            "ready": managed_auth or broker_ready,
        }

    payload = {
        "schema": "zippoworkz-connector-secret-status-v2",
        "machine_id": json.loads(
            (ROOT / "MACHINE_ID.json").read_text(encoding="utf-8-sig")
        ).get("machine_id"),
        "catalog_schema": catalog.get("schema"),
        "connectors": rows,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
