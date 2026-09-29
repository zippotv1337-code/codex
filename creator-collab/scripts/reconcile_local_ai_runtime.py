from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable


def _read(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"object_required:{path.name}")
    return payload


def _write_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _agent_running() -> bool:
    command = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -in @('python.exe','pythonw.exe','py.exe') -and "
        "$_.CommandLine -like '*ZIPPOWORKZ_LOCAL_AGENT.py*' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError("local_ai_process_check_failed")
    return bool(result.stdout.strip())


def reconcile(
    root: Path,
    *,
    apply: bool,
    process_check: Callable[[], bool] = _agent_running,
    now: datetime | None = None,
) -> dict[str, object]:
    root = root.resolve()
    tasks_root = (root / "Tasks").resolve()
    run_state_path = tasks_root / "RUN_STATE.json"
    state = _read(run_state_path)
    task_id = str(state.get("task_id") or "")
    run_id = str(state.get("run_id") or "")
    if state.get("state") == "IDLE_CLEAN" and not state.get("active"):
        return {
            "status": "IDLE_CLEAN",
            "changed": False,
            "run_id": None,
            "task_id": None,
        }
    if state.get("state") != "BLOCKED" or state.get("active") is True:
        raise RuntimeError("only_inactive_blocked_run_can_be_reconciled")
    if state.get("resume_allowed") is not False or not task_id or not run_id:
        raise RuntimeError("blocked_run_not_terminal_or_identity_missing")
    task_dir = (tasks_root / "Runs" / task_id).resolve()
    task_path = task_dir / "TASK.json"
    task = _read(task_path)
    if (
        task.get("task_id") != task_id
        or task.get("run_id") != run_id
        or task.get("status") != "BLOCKED"
        or task.get("resume") is not False
    ):
        raise RuntimeError("run_task_binding_invalid")
    working = []
    for candidate in (tasks_root / "Runs").glob("*/TASK.json"):
        payload = _read(candidate)
        if payload.get("status") == "WORKING":
            working.append(str(payload.get("task_id")))
    if working:
        raise RuntimeError("working_task_present")
    if process_check():
        raise RuntimeError("local_ai_agent_process_still_running")

    preview = {
        "status": "READY_TO_RECONCILE",
        "changed": False,
        "run_id": run_id,
        "task_id": task_id,
        "blocked_reason": state.get("blocked_reason"),
        "action": "archive_blocked_task_and_reset_current_pointer_to_idle_clean",
    }
    if not apply:
        return preview

    stamp = (now or datetime.now().astimezone()).strftime("%Y%m%d-%H%M%S")
    backup_dir = root / "Backups" / "Milestones" / "AutonomyReconcile" / stamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    state_backup = backup_dir / "RUN_STATE.before.json"
    task_backup = backup_dir / "TASK.before.json"
    shutil.copy2(run_state_path, state_backup)
    shutil.copy2(task_path, task_backup)
    source_hashes = {
        "RUN_STATE.before.json": _sha256(state_backup),
        "TASK.before.json": _sha256(task_backup),
    }

    archive_dir = (tasks_root / "Archive" / task_id).resolve()
    archive_root = (tasks_root / "Archive").resolve()
    if archive_root not in archive_dir.parents or archive_dir.exists():
        raise RuntimeError("archive_target_invalid_or_exists")
    archive_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(task_dir), str(archive_dir))
    archived_task_path = archive_dir / "TASK.json"
    archived_task = _read(archived_task_path)
    archived_task["archived_at"] = datetime.now().astimezone().isoformat(
        timespec="milliseconds"
    )
    archived_task["archive_reason"] = (
        "Terminal BLOCKED run reconciled; evidence preserved; task was not marked DONE."
    )
    _write_atomic(archived_task_path, archived_task)

    timestamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
    final_state = {
        "state": "IDLE_CLEAN",
        "active": False,
        "run_id": None,
        "task_id": None,
        "machine_id": state.get("machine_id"),
        "machine_type": state.get("machine_type"),
        "hostname": state.get("hostname"),
        "phase": "IDLE_CLEAN",
        "resume_allowed": False,
        "blocked_reason": None,
        "started_at": None,
        "finished_at": timestamp,
        "updated_at": timestamp,
        "completed_steps": [],
        "expected_outputs": [],
        "last_write_step": {},
        "last_read_step": {},
        "last_action": {
            "action": "reconcile_terminal_blocked_run",
            "reason": "Current pointer cleared after preserving terminal BLOCKED evidence.",
        },
        "previous_run_evidence": {
            "run_id": run_id,
            "task_id": task_id,
            "state": "BLOCKED",
            "blocked_reason": state.get("blocked_reason"),
            "archive": str(archived_task_path.relative_to(root)),
            "backup": str(backup_dir.relative_to(root)),
        },
    }
    _write_atomic(run_state_path, final_state)
    evidence = {
        "schema": "zippoworkz-runtime-reconcile-v1",
        "status": "IDLE_CLEAN",
        "reconciled_at": timestamp,
        "previous_run": final_state["previous_run_evidence"],
        "source_hashes": source_hashes,
        "final_run_state_sha256": _sha256(run_state_path),
        "archived_task_status": _read(archived_task_path).get("status"),
        "done_was_not_invented": True,
    }
    _write_atomic(backup_dir / "EVIDENCE.json", evidence)
    readback = _read(run_state_path)
    if readback.get("state") != "IDLE_CLEAN" or readback.get("active") is not False:
        raise RuntimeError("runtime_reconcile_readback_failed")
    return {
        **preview,
        "status": "IDLE_CLEAN",
        "changed": True,
        "backup": str(backup_dir),
        "archive": str(archive_dir),
        "evidence": str(backup_dir / "EVIDENCE.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely reconcile one terminal BLOCKED Local-AI run"
    )
    parser.add_argument("--root", type=Path, default=Path(r"C:\Zippoworkz"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(reconcile(args.root, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
