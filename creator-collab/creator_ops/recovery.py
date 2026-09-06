from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from .database import CreatorDatabase


SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "cookies.txt"}
SKIP_PARTS = {".git", "__pycache__", "backups", "exports", ".pytest_cache"}


class RecoveryBackupService:
    """Build validated, secret-free recovery archives without deleting history."""

    def __init__(self, database: CreatorDatabase, project_root: Path):
        self.database = database
        self.project_root = Path(project_root).resolve()

    @staticmethod
    def _sha(path: Path) -> str:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return digest

    def _sanitized_database(self, destination: Path) -> None:
        source = self.database.connect()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
            target.execute("UPDATE platform_accounts SET secret_reference = NULL")
            target.commit()
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("sanitized_database_integrity_failed")
        finally:
            target.close()
            source.close()

    def _project_files(self, full: bool) -> list[Path]:
        roots = ["config", "docs", "sessions"]
        if full:
            roots += ["creator_ops", "dashboard", "data", "tests", "scripts"]
        files: list[Path] = []
        for root_name in roots:
            root = self.project_root / root_name
            if not root.exists():
                continue
            for path in root.rglob("*"):
                relative = path.relative_to(self.project_root)
                if not path.is_file() or any(part in SKIP_PARTS for part in relative.parts):
                    continue
                if path.name.lower() in SECRET_NAMES or path.suffix.lower() in {".pem", ".key"}:
                    continue
                if path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                    continue
                if path.name in {"remote_url.txt", "cloudflared.log", "cloudflared.err.log"}:
                    continue
                files.append(path)
        files.extend(self._meta_receipt_files())
        for name in (
            "README.md",
            "PROJECT_RESUME.md",
            "CURRENT_HANDOFF.md",
            "OWNER_DECISIONS.md",
            "JOURNAL_TEMPLATE.md",
            "VERSION",
            "CHANGELOG.md",
            "pyproject.toml",
            "AUTOPILOT_CHECKPOINT.md",
            ".env.example",
            "START_CREATOR_OPS.ps1",
            "STOP_CREATOR_OPS.ps1",
            "RESTART_CREATOR_OPS.ps1",
            "STATUS_CREATOR_OPS.ps1",
            "START_LAN_CREATOR_OPS.ps1",
        ):
            path = self.project_root / name
            if path.is_file():
                files.append(path)
        return sorted(set(files))

    def _meta_receipt_files(self) -> list[Path]:
        """Return only schema-validated, secret-free publish safety receipts."""
        root = self.project_root / "data" / "meta-receipts"
        if not root.is_dir():
            return []
        allowed = {
            "schema",
            "status",
            "idempotency_key",
            "creation_id",
            "creator_slug",
            "ig_user_id",
            "created_at",
            "external_id",
            "external_url",
            "confirmed_at",
        }
        receipts: list[Path] = []
        for path in sorted(root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise RuntimeError(f"invalid_meta_receipt:{path.name}") from error
            if (
                not isinstance(payload, dict)
                or payload.get("schema") != "creator-ops-meta-receipt-v1"
                or payload.get("status") not in {"PUBLISH_INTENT", "CONFIRMED"}
                or set(payload) - allowed
                or not re.fullmatch(r"[0-9a-f]{64}", path.stem)
                or payload.get("idempotency_key") != path.stem
            ):
                raise RuntimeError(f"unsafe_meta_receipt:{path.name}")
            lowered = path.read_text(encoding="utf-8").lower()
            if any(marker in lowered for marker in ("access_token", "password", "cookie")):
                raise RuntimeError(f"secret_marker_in_meta_receipt:{path.name}")
            receipts.append(path)
        return receipts

    def build(self, destination: Path, *, kind: str, now: datetime | None = None) -> Path:
        if kind not in {"weekly", "monthly", "milestone"}:
            raise ValueError("kind_must_be_weekly_monthly_or_milestone")
        now = now or datetime.now().astimezone()
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        stamp = now.strftime("%Y%m%d-%H%M")
        if kind == "weekly":
            filename = f"Backup_Woche_KW{now.isocalendar().week:02d}_{now.year}_{stamp}.zip"
        elif kind == "monthly":
            filename = f"Backup_Monat_{now:%Y-%m}_FULL_{stamp}.zip"
        else:
            filename = f"Backup_Meilenstein_{stamp}.zip"
        target = destination / filename
        if target.exists():
            return target

        with tempfile.TemporaryDirectory(prefix="creator-recovery-") as temp_name:
            temp = Path(temp_name)
            db_path = temp / "recovery" / "creator_ops.db"
            db_path.parent.mkdir(parents=True)
            self._sanitized_database(db_path)
            members = [(db_path, "recovery/creator_ops.db")]
            members.extend(
                (path, path.relative_to(self.project_root).as_posix())
                for path in self._project_files(kind in {"monthly", "milestone"})
                if path.resolve() != self.database.path.resolve()
            )
            checksums = {archive_name: self._sha(path) for path, archive_name in members}
            manifest = {
                "schema": "creator-ops-recovery-v1",
                "kind": kind,
                "created_at": now.isoformat(timespec="seconds"),
                "contains_secrets": False,
                "retention_action": "none",
                "database_integrity": "ok",
                "files": sorted(checksums),
            }
            (temp / "MANIFEST.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (temp / "SHA256SUMS.txt").write_text(
                "".join(f"{checksums[name]}  {name}\n" for name in sorted(checksums)),
                encoding="utf-8",
            )
            members += [
                (temp / "MANIFEST.json", "MANIFEST.json"),
                (temp / "SHA256SUMS.txt", "SHA256SUMS.txt"),
            ]
            temporary = target.with_suffix(".tmp")
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                for path, archive_name in members:
                    archive.write(path, archive_name)
            temporary.replace(target)

        self.validate(target)
        return target

    def build_patch(
        self,
        destination: Path,
        *,
        changed_files: list[str],
        base_backup: Path,
        reason: str,
        label: str,
        now: datetime | None = None,
    ) -> Path:
        """Create a manifest-backed patch ZIP; SQLite remains a full safe snapshot."""
        base_backup = Path(base_backup).resolve()
        if not base_backup.is_file():
            raise FileNotFoundError(base_backup)
        if not reason.strip():
            raise ValueError("patch_reason_required")
        selected: list[Path] = []
        for item in changed_files:
            path = (self.project_root / item).resolve()
            try:
                path.relative_to(self.project_root)
            except ValueError as error:
                raise ValueError("patch_path_outside_project") from error
            if not path.is_file():
                raise FileNotFoundError(path)
            relative = path.relative_to(self.project_root)
            if (
                path.name.lower() in SECRET_NAMES
                or path.suffix.lower() in {".pem", ".key", ".db", ".sqlite", ".sqlite3"}
                or any(part in SKIP_PARTS for part in relative.parts)
            ):
                raise ValueError(f"unsafe_patch_member:{relative.as_posix()}")
            selected.append(path)

        now = now or datetime.now().astimezone()
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / f"Patch_{label}_{now:%Y%m%d-%H%M}.zip"
        if target.exists():
            return target
        with tempfile.TemporaryDirectory(prefix="creator-patch-") as temp_name:
            temp = Path(temp_name)
            db_path = temp / "recovery" / "creator_ops.db"
            db_path.parent.mkdir(parents=True)
            self._sanitized_database(db_path)
            members = [(db_path, "recovery/creator_ops.db")]
            members.extend(
                (path, path.relative_to(self.project_root).as_posix())
                for path in sorted(set(selected))
            )
            checksums = {name: self._sha(path) for path, name in members}
            manifest = {
                "schema": "creator-ops-recovery-v2",
                "kind": "patch",
                "backup_id": target.stem,
                "created_at": now.isoformat(timespec="seconds"),
                "base_backup": base_backup.name,
                "base_sha256": self._sha(base_backup),
                "reason": reason.strip(),
                "contains_secrets": False,
                "database_integrity": "ok",
                "changed_files": sorted(
                    path.relative_to(self.project_root).as_posix() for path in set(selected)
                ),
                "restore_order": [base_backup.name, target.name],
                "files": sorted(checksums),
            }
            (temp / "MANIFEST.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (temp / "SHA256SUMS.txt").write_text(
                "".join(f"{checksums[name]}  {name}\n" for name in sorted(checksums)),
                encoding="utf-8",
            )
            temporary = target.with_suffix(".tmp")
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                for path, archive_name in members:
                    archive.write(path, archive_name)
                archive.write(temp / "MANIFEST.json", "MANIFEST.json")
                archive.write(temp / "SHA256SUMS.txt", "SHA256SUMS.txt")
            temporary.replace(target)
        self.validate(target)
        return target

    @staticmethod
    def validate(path: Path) -> dict[str, object]:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"zip_integrity_failed:{bad}")
            names = set(archive.namelist())
            if not {"MANIFEST.json", "SHA256SUMS.txt", "recovery/creator_ops.db"} <= names:
                raise RuntimeError("recovery_metadata_missing")
            manifest = json.loads(archive.read("MANIFEST.json"))
            if manifest.get("contains_secrets") is not False:
                raise RuntimeError("backup_secret_flag_invalid")
            expected: dict[str, str] = {}
            for line in archive.read("SHA256SUMS.txt").decode("utf-8").splitlines():
                checksum, separator, name = line.partition("  ")
                if not separator or not name:
                    raise RuntimeError("backup_checksum_manifest_invalid")
                expected[name] = checksum
            if set(expected) != set(manifest.get("files", [])):
                raise RuntimeError("backup_checksum_file_set_mismatch")
            for name, checksum in expected.items():
                if name not in names:
                    raise RuntimeError(f"backup_member_missing:{name}")
                actual = hashlib.sha256(archive.read(name)).hexdigest()
                if actual != checksum:
                    raise RuntimeError(f"backup_checksum_mismatch:{name}")
            with tempfile.TemporaryDirectory(prefix="creator-restore-check-") as temp_name:
                archive.extract("recovery/creator_ops.db", temp_name)
                connection = sqlite3.connect(Path(temp_name) / "recovery" / "creator_ops.db")
                try:
                    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                    secrets = connection.execute(
                        "SELECT COUNT(*) FROM platform_accounts WHERE secret_reference IS NOT NULL"
                    ).fetchone()[0]
                finally:
                    connection.close()
                if integrity != "ok" or secrets:
                    raise RuntimeError("recovery_database_validation_failed")
        return {"path": str(path), "size": path.stat().st_size, "sha256": RecoveryBackupService._sha(path)}
