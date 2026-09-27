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
    present = set()
    if broker is not None:
        present = {
            str(item.get("name"))
            for item in broker.metadata()
            if item.get("present")
        }
    rows = {}
    for name, spec in catalog.get("connectors", {}).items():
        names = [str(item) for item in spec.get("secret_names", [])]
        missing = [item for item in names if item not in present]
        rows[name] = {
            "configured_status": spec.get("status"),
            "worker": spec.get("worker"),
            "replicate": bool(spec.get("replicate")),
            "required_names": names,
            "present_names": [item for item in names if item in present],
            "missing_names": missing,
            "broker_ready": bool(names) and not missing,
        }
    payload = {
        "schema": "zippoworkz-connector-secret-status-v1",
        "machine_id": json.loads(
            (ROOT / "MACHINE_ID.json").read_text(encoding="utf-8-sig")
        ).get("machine_id"),
        "connectors": rows,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
