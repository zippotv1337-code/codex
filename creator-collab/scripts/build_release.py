from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", "__pycache__", "backups", "exports", "data"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collect(kind: str) -> dict[str, bytes]:
    roots = ["docs", "sessions"]
    if kind == "codex":
        roots += ["creator_ops", "dashboard", "config", "scripts", "tests"]
    files: dict[str, bytes] = {}
    for root_name in roots:
        root = ROOT / root_name
        for path in root.rglob("*"):
            relative = path.relative_to(ROOT)
            if path.is_file() and not any(part in SKIP for part in relative.parts):
                files[relative.as_posix()] = path.read_bytes()
    for name in (
        "VERSION", "CHANGELOG.md", "README.md", "PROJECT_RESUME.md",
        "CURRENT_HANDOFF.md", "OWNER_DECISIONS.md", "JOURNAL_TEMPLATE.md",
        "AUTOPILOT_CHECKPOINT.md", ".env.example", ".gitignore", "pyproject.toml",
    ):
        path = ROOT / name
        if path.is_file():
            files[name] = path.read_bytes()
    return files


def build(destination: Path, kind: str) -> Path:
    files = collect(kind)
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    stamp = date.today().isoformat()
    prefix = "Codex_Work_Master" if kind == "codex" else "AdvisorAI_Review"
    target = destination / f"{prefix}_v{version}_FINAL_{stamp}.zip"
    checksums = {name: sha(data) for name, data in sorted(files.items())}
    manifest = {
        "schema": "creator-ops-release-v1",
        "kind": kind,
        "version": version,
        "status": "FINAL",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "contains_secrets": False,
        "files": sorted(files),
    }
    destination.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
        archive.writestr("MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        archive.writestr("SHA256SUMS.txt", "".join(f"{digest}  {name}\n" for name, digest in checksums.items()))
    temporary.replace(target)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("release_zip_integrity_failed")
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "exports")
    args = parser.parse_args()
    for kind in ("codex", "advisor"):
        path = build(args.out, kind)
        print(json.dumps({"kind": kind, "path": str(path), "sha256": sha(path.read_bytes())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
