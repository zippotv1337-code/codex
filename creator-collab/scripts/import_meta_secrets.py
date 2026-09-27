from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(r"C:\Zippoworkz")
PROJECT = ROOT / "Workspace" / "codex_ingest" / "creator-collab"
BROKER_PATH = ROOT / "_system" / "SECRET_BROKER.py"
WORKER = "creator-ops-meta"
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


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in EXPECTED:
            values[key] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(PROJECT / ".env.meta.local"))
    parser.add_argument("--delete-source", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    broker = load_broker()
    if args.status:
        rows = []
        for item in broker.metadata():
            if item.get("name") in EXPECTED:
                rows.append({
                    "name": item.get("name"),
                    "present": bool(item.get("present")),
                    "allowed_workers": item.get("allowed_workers") or [],
                    "updated_at": item.get("updated_at"),
                })
        print(json.dumps({"worker": WORKER, "secrets": rows}, ensure_ascii=False))
        return 0

    source = Path(args.source)
    if not source.is_file():
        raise SystemExit("source_file_missing")
    values = parse_env(source)
    missing = [name for name in EXPECTED if not values.get(name)]
    if missing:
        print(json.dumps({"ok": False, "missing": missing}, ensure_ascii=False))
        return 2

    for name in EXPECTED:
        broker.set_secret(name, values[name], allowed_workers=[WORKER])
        if broker.get_for_broker(name, WORKER) != values[name]:
            raise RuntimeError(f"secret_roundtrip_failed:{name}")

    if args.delete_source:
        source.unlink()

    print(json.dumps({
        "ok": True,
        "imported": list(EXPECTED),
        "source_deleted": bool(args.delete_source and not source.exists()),
        "worker": WORKER,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
