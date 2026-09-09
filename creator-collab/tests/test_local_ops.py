import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import shutil
import subprocess
import time
import sys
from creator_ops.database import CreatorDatabase
from creator_ops.recovery import RecoveryBackupService
from creator_ops.local_ops import (backup_inventory, database_check, due_backup,
    healthcheck, local_lock, run, runtime_check)


class LocalOpsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = CreatorDatabase(self.root / "data" / "review_dashboard.db")
        self.database.initialize()
        self.service = RecoveryBackupService(self.database, self.root)
        self.config = self.root / "config.toml"
        self.config.write_text('[runtime]\nhost="127.0.0.1"\nport=4180\ndatabase="data/review_dashboard.db"\n')
        self.now = datetime(2026, 9, 9, 10, 0)

    def test_weekly_monthly_period_guard_and_integrity(self):
        for kind in ("weekly", "monthly"):
            first = due_backup(self.service, self.root / "backups", kind, self.now)
            second = due_backup(self.service, self.root / "backups", kind, self.now)
            self.assertEqual(first["status"], "CREATED")
            self.assertEqual(second["status"], "CURRENT")
            self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(len(list((self.root / "backups").glob("*.zip"))), 2)

    def test_iso_week_year(self):
        receipt = due_backup(self.service, self.root / "backups", "weekly", datetime(2027, 1, 1))
        self.assertIn("KW53_2026", receipt["path"])

    def test_corrupt_backup_not_accepted(self):
        backups = self.root / "backups"
        backups.mkdir()
        (backups / "Backup_Woche_KW37_2026_old.zip").write_bytes(b"broken")
        result = due_backup(self.service, backups, "weekly", self.now)
        self.assertEqual(result["status"], "CREATED")
        self.assertEqual(backup_inventory([backups]), {"found": 2, "healthy": 1, "warnings": 1})

    def test_active_integrity_failure_is_error_and_no_creation(self):
        missing = self.root / "data" / "missing.db"
        self.assertFalse(database_check(missing))
        self.assertFalse(missing.exists())
        self.database.path.write_bytes(b"broken")
        with self.assertRaises(RuntimeError):
            run(self.root, self.config, "weekly", self.root / "backups", now=self.now)

    def test_full_excludes_venv_secrets_wal_and_logs(self):
        for name in ("scripts/.venv/binary.exe", "data/.env", "data/tokens.json",
                     "data/local.db-wal", "data/logs/unsafe.log", "data/temp/tmp.txt"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("sensitive-test-marker")
        backup = self.service.build(self.root / "backups", kind="monthly", now=self.now)
        with zipfile.ZipFile(backup) as archive:
            for name in archive.namelist():
                self.assertNotIn(b"sensitive-test-marker", archive.read(name))

    def test_idle_is_bounded_second_run_clean_and_preserves_content(self):
        healthy = {"overall": "HEALTHY", "checks": {"Database": "OK"}}
        before = self.database.path.read_bytes()
        with patch("creator_ops.local_ops.healthcheck", return_value=healthy):
            first = run(self.root, self.config, "idle", self.root / "backups", now=self.now)
            second = run(self.root, self.config, "idle", self.root / "backups", now=self.now)
        self.assertEqual(first["status"], "COMPLETED")
        self.assertEqual(second["status"], "IDLE_CLEAN")
        self.assertEqual(before, self.database.path.read_bytes())
        self.assertFalse(second["external_actions"])

    def test_pause_and_action_allowlist(self):
        (self.root / "data" / "autopilot_control.json").write_text('{"status":"PAUSED"}')
        self.assertEqual(run(self.root, self.config, "idle", self.root / "backups")["status"], "PAUSED")
        with self.assertRaises(ValueError):
            run(self.root, self.config, "publish", self.root / "backups")

    def test_local_health_cannot_follow_external_host(self):
        with self.assertRaises(ValueError):
            runtime_check({"runtime": {"host": "8.8.8.8", "port": 80}})

    def test_lock_excludes_concurrent_job(self):
        with local_lock(self.root / "data" / "ops.lock"):
            with self.assertRaises(OSError):
                with local_lock(self.root / "data" / "ops.lock"):
                    self.fail("second lock entered")

    def test_old_backup_warning_does_not_fail_active_db(self):
        backup = self.root / "backups"
        backup.mkdir()
        (backup / "old.db").write_bytes(b"corrupt")
        with patch("creator_ops.local_ops.runtime_check", return_value=True), patch(
                "creator_ops.local_ops.sys.prefix", str(self.root / ".venv")):
            report = healthcheck(self.root, {"runtime": {"database": "data/review_dashboard.db"}}, [backup])
        self.assertEqual(report["overall"], "HEALTHY_WITH_WARNINGS")
        self.assertEqual(report["checks"]["Database"], "OK")

    @unittest.skipUnless(sys.platform == "win32", "Windows watchdog integration")
    def test_watchdog_backoff_then_circuit_without_real_backend(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        source = Path(__file__).resolve().parents[1]
        for name in ("creator_ops_watchdog.ps1", "runtime_config.ps1"):
            shutil.copyfile(source / "scripts" / name, scripts / name)
        shutil.copyfile(source / "config.toml", self.config)
        self.config.write_text(self.config.read_text().replace('host = "192.168.188.131"', 'host = "127.0.0.1"'))
        (self.root / "START_CREATOR_OPS.ps1").write_text("param([switch]$NoBrowser,[string]$Config)\nWrite-Output 'stub only'\n")
        command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(scripts / "creator_ops_watchdog.ps1"),
                   "-Port", "9", "-MaximumRestarts", "1", "-BackoffSeconds", "1"]
        started = time.monotonic()
        first = subprocess.run(command, capture_output=True, timeout=20)
        self.assertEqual(first.returncode, 0, first.stderr.decode(errors="replace"))
        self.assertGreaterEqual(time.monotonic() - started, 1)
        second = subprocess.run(command, capture_output=True, timeout=20)
        self.assertEqual(second.returncode, 2)
        state = json.loads((self.root / "data" / "watchdog_state.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(state["status"], "CIRCUIT_OPEN")
        self.assertEqual(len(state["restart_attempts"]), 1)


if __name__ == "__main__":
    unittest.main()
