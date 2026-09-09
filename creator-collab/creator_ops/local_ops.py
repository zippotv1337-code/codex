"""Bounded local maintenance; deliberately no platform adapters or dispatch."""
from __future__ import annotations
import argparse
from contextlib import contextmanager, closing
from datetime import datetime
import ipaddress
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from tempfile import NamedTemporaryFile
import tomllib
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler
from zoneinfo import ZoneInfo
from .database import CreatorDatabase
from .recovery import RecoveryBackupService


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


@contextmanager
def local_lock(path):
    """One OS lock shared by idle and scheduled jobs, released on process exit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def database_check(path):
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            return (connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
                    and not connection.execute("PRAGMA foreign_key_check").fetchall())
    except (OSError, sqlite3.Error):
        return False


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def runtime_check(config):
    runtime = config["runtime"]
    host = runtime["host"]
    if host in {"0.0.0.0", "::", "localhost"}:
        host = "127.0.0.1"
    address = ipaddress.ip_address(host)
    if not (address.is_private or address.is_loopback) or address.is_unspecified:
        raise ValueError("health_endpoint_must_be_local")
    if runtime.get("health_path", "/api/health") != "/api/health":
        raise ValueError("unexpected_health_path")
    host = f"[{host}]" if address.version == 6 else host
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open(
                f"http://{host}:{int(runtime['port'])}/api/health", timeout=5) as response:
            return response.status == 200 and json.load(response).get("status") == "ok"
    except (OSError, ValueError):
        return False


def backup_inventory(roots):
    files = set()
    for root in roots:
        for pattern in ("*.db", "*.sqlite", "*.sqlite3", "Backup_*.zip", "Patch_*.zip"):
            files.update(root.glob(pattern))
    healthy = 0
    for path in files:
        try:
            if path.suffix == ".zip":
                RecoveryBackupService.validate(path)
                healthy += 1
            else:
                healthy += int(database_check(path))
        except Exception:
            pass
    return {"found": len(files), "healthy": healthy, "warnings": len(files) - healthy}


def healthcheck(root, config, backup_dirs):
    checks = {
        "Runtime": "OK" if runtime_check(config) else "ERROR",
        "Python": "OK" if sys.version_info >= (3, 12) else "ERROR",
        "VENV": "OK" if Path(sys.prefix).resolve() == (root / ".venv").resolve() else "ERROR",
        "SQLite": "OK" if sqlite3.sqlite_version else "ERROR",
        "Database": "OK" if database_check(root / config["runtime"]["database"]) else "ERROR",
        "Disk": "OK" if shutil.disk_usage(root).free >= 2 * 1024**3 else "ERROR",
    }
    backups = backup_inventory(backup_dirs)
    overall = ("ERROR" if "ERROR" in checks.values() else
               "HEALTHY_WITH_WARNINGS" if backups["warnings"] or not backups["healthy"] else "HEALTHY")
    return {"checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "checks": checks, "python_version": sys.version.split()[0],
            "sqlite_version": sqlite3.sqlite_version, "backups": backups, "overall": overall}


def compact_health(report):
    return "\n".join(["ZIPPOWORKZ LOCAL HEALTH", ""] +
        [f"{key}: {value}" for key, value in report["checks"].items()] +
        ["", "Backups:"] + [f"{key.title()}: {value}" for key, value in report["backups"].items()] +
        ["", "Overall:", report["overall"]])


def due_backup(service, destination, kind, now):
    if kind not in {"weekly", "monthly"}:
        raise ValueError("automatic_backup_kind_invalid")
    period = (f"KW{now.isocalendar().week:02d}_{now.isocalendar().year}" if kind == "weekly"
              else now.strftime("%Y-%m"))
    pattern = f"Backup_Woche_{period}_*.zip" if kind == "weekly" else f"Backup_Monat_{period}_FULL_*.zip"
    for path in sorted(destination.glob(pattern)):
        try:
            return {"status": "CURRENT", "period": period, **service.validate(path)}
        except Exception:
            continue
    path = service.build(destination, kind=kind, now=now)
    return {"status": "CREATED", "period": period, **service.validate(path)}


def status_snapshot(root):
    result = {}
    for key, filename in (("maintenance", "local_ops_status.json"),
                          ("watchdog", "watchdog_state.json"),
                          ("tasks", "runtime_tasks_status.json"),
                          ("last_failure", "local_ops_failure.json")):
        try:
            result[key] = read_json(root / "data" / filename)
        except (OSError, ValueError):
            result[key] = {"status": "ERROR", "reason": "unreadable_local_status"}
    return result


def run(root, config_path, action, destination, *, now=None):
    if action not in {"idle", "health", "weekly", "monthly"}:
        raise ValueError("local_action_not_allowed")
    now = now or datetime.now(ZoneInfo("Europe/Berlin"))
    config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    state_path = root / "data" / "local_ops_status.json"
    with local_lock(root / "data" / "local_ops.lock"):
        state = read_json(state_path)
        if read_json(root / "data" / "autopilot_control.json").get("status") == "PAUSED":
            return {"status": "PAUSED", "external_actions": False}
        today, work = now.date().isoformat(), []
        if action == "health" or (action == "idle" and
                (state.get("health_date") != today or state.get("last_healthcheck", {}).get("overall") == "ERROR")):
            report = healthcheck(root, config, [root / "backups", destination])
            state["last_healthcheck"], state["health_date"] = report, today
            work.append("health")
        if action in {"weekly", "monthly"} or (action == "idle" and state.get("backup_check_date") != today):
            database_path = root / config["runtime"]["database"]
            if not database_check(database_path):
                raise RuntimeError("active_database_integrity_failed")
            service = RecoveryBackupService(CreatorDatabase(database_path), root)
            for kind in (("weekly", "monthly") if action == "idle" else (action,)):
                receipt = due_backup(service, destination, kind, now)
                state[f"last_{kind}_backup"] = {**receipt, "verified_at": now.isoformat()}
                work.append(f"{kind}:{receipt['status']}")
            if action == "idle":
                state["backup_check_date"] = today
        result = {"status": "COMPLETED" if work else "IDLE_CLEAN",
                  "checked_at": now.isoformat(), "action": action, "work": work, "external_actions": False}
        if state.get("last_healthcheck", {}).get("overall") == "ERROR":
            result["status"] = "ERROR"
        state["last_run"] = result
        write_json(state_path, state)
        write_json(root / "data" / "local_ops_failure.json", {"status": "NONE", "checked_at": now.isoformat()})
        if work:
            write_json(root / "sessions" / "runtime" / f"local-ops-{today}-{action}.json", result)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("idle", "health", "weekly", "monthly"))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        result = run(root, args.config or root / "config.toml", args.action,
                     args.destination or root / "backups")
        if args.action == "health" and result["status"] != "PAUSED":
            print(compact_health(read_json(root / "data" / "local_ops_status.json")["last_healthcheck"]))
        else:
            print(json.dumps(result, ensure_ascii=False))
        return 1 if result["status"] == "ERROR" else 0
    except (BlockingIOError, PermissionError):
        print('{"status":"BUSY_OR_ACCESS_DENIED","external_actions":false}')
        return 2
    except Exception as error:
        failure = {"status": "ERROR", "error_type": type(error).__name__,
                   "checked_at": datetime.now().astimezone().isoformat(), "external_actions": False}
        write_json(root / "data" / "local_ops_failure.json", failure)
        print(json.dumps(failure))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
