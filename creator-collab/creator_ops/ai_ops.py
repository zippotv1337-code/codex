"""Local-only AI operations; state uses the existing schema-5 event ledger."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .database import CreatorDatabase, utc_now

PROTOCOL = "ai-ops-v1"
AGENTS = ("codex", "local_ai", "vps")
STATUSES = {"ONLINE", "WORKING", "IDLE", "PAUSED", "BLOCKED", "ERROR", "OFFLINE"}
TASKS = (
    {"id": "health", "title": "Systemgesundheit und Datenbestand prüfen", "priority": "P0", "dependencies": []},
    {"id": "tests", "title": "Fokussierte lokale Runtime-Tests", "priority": "P1", "dependencies": ["health"]},
    {"id": "triage", "title": "Vorhandene Content-/Analytics-Lücken zuordnen", "priority": "P1", "dependencies": ["health"]},
    {"id": "summary", "title": "Lokale KI: geprüfte Ergebnisse zusammenfassen", "priority": "P2", "dependencies": ["tests", "triage"]},
)


def default_root(project: Path) -> Path:
    configured = os.environ.get("ZIPPOWORKZ_ROOT")
    if configured:
        return Path(configured).resolve()
    # Reuse the ingested project in place. Tests/portable installs stay local.
    if project.parent.name == "codex_ingest" and project.parent.parent.name == "Workspace":
        return project.parent.parent.parent.resolve()
    return project.resolve()


def atomic_text(path: Path, text: str) -> None:
    """Unique temporary names avoid clashes; result writers have separate files."""
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temp = Path(handle.name)
    temp.replace(path)


class AiOpsService:
    def __init__(self, db: CreatorDatabase, project: Path, root: Path | None = None):
        self.db = db
        self.project = Path(project).resolve()
        self.root = (root or default_root(self.project)).resolve()

    def read(self, key: str, default: dict | None = None) -> dict:
        row = self.db.one(
            "SELECT detail_json FROM runtime_events WHERE event_type='AI_OPS_STATE' AND step=? ORDER BY id DESC LIMIT 1",
            ("aiops." + key,),
        )
        return json.loads(row[0]) if row else dict(default or {})

    def write(self, key: str, payload: dict) -> dict:
        value = {**payload, "updated_at": utc_now()}
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO runtime_events (event_type,severity,step,detail_json,created_at) VALUES ('AI_OPS_STATE','INFO',?,?,?)",
                ("aiops." + key, json.dumps(value, ensure_ascii=False), value["updated_at"]),
            )
        return value

    def command(self, action: str) -> dict:
        if action not in {"pause", "resume", "stop"}:
            raise ValueError("unsupported_ai_ops_command")
        # No process execution, model start, publishing or retry from HTTP input.
        self.write("control", {"mode": {"pause": "PAUSED", "resume": "RUN", "stop": "STOPPED"}[action]})
        return self.snapshot()

    def control(self) -> str:
        return self.read("control", {"mode": "RUN"})["mode"]

    def start_local_worker(self, model: str = "qwen3:8b") -> None:
        # No user-supplied command/paths. The durable lease rejects duplicate workers.
        # "Lokalen Lauf starten" is an explicit start action, so clear a prior
        # STOPPED/PAUSED control state before checking/spawning the lease owner.
        # The separate Fortsetzen button still remains useful for a paused run.
        if self.control() in {"STOPPED", "PAUSED"}:
            self.write("control", {"mode": "RUN"})
        lease = self.db.one("SELECT expires_at FROM run_leases WHERE lease_name='zippoworkz-local-ai'")
        if lease and datetime.fromisoformat(lease[0]) > datetime.now(UTC):
            return
        if not self.project.is_relative_to(self.root):
            raise ValueError("workspace_outside_runtime_root")
        log_path = self.root / "Logs" / "local_ai_process.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # A start respects PAUSED/STOPPED: use Resume explicitly first.
        with log_path.open("a", encoding="utf-8") as output:
            subprocess.Popen(
                [sys.executable, "-m", "creator_ops.local_ai_runtime", "--root", str(self.root), "--model", model, "--watch-seconds", "300"],
                cwd=self.project, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

    def agent(self, name: str, status: str, *, task: str | None = None, error: str | None = None, success: bool = False) -> None:
        if name not in AGENTS or status not in STATUSES:
            raise ValueError("invalid_agent_status")
        old = self.read("agent." + name)
        self.write("agent." + name, {
            "id": name, "status": status, "task": task, "heartbeat": utc_now(),
            "last_success": utc_now() if success else old.get("last_success"),
            # A completed run supersedes an earlier transient error; keeping it
            # visible makes a healthy worker look permanently blocked in AI Ops.
            "last_error": None if (success or (status == "ONLINE" and error is None)) else (error if error is not None else old.get("last_error")),
        })

    def task(self, task_id: str, status: str, **fields) -> None:
        if task_id not in {t["id"] for t in TASKS} or status not in {"NEXT", "WORKING", "PAUSED", "DONE", "BLOCKED", "ERROR"}:
            raise ValueError("invalid_local_task")
        old = self.read("task." + task_id)
        self.write("task." + task_id, {**old, **fields, "status": status})

    def snapshot(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        agents = []
        for name in AGENTS:
            state = self.read("agent." + name, {"id": name, "status": "OFFLINE", "heartbeat": None, "task": None, "last_success": None, "last_error": None})
            if state.get("heartbeat") and now - datetime.fromisoformat(state["heartbeat"]) > timedelta(seconds=120):
                state = {**state, "status": "OFFLINE"}
            agents.append(state)
        tasks = []
        for spec in TASKS:
            state = self.read("task." + spec["id"], {"status": "NEXT", "attempts": 0, "result": None})
            tasks.append({**spec, **state, "agent": "local_ai", "source": "CODEX_RUNTIME_HANDOFF.md", "project": "ZippoWorkz", "owner_gate": False})
        counts = {table: self.db.scalar(f"SELECT COUNT(*) FROM {table}") for table in ("content_items", "publications", "assets", "manual_analytics_events")}
        return {
            "protocol_version": PROTOCOL, "control": self.control(), "agents": agents, "tasks": tasks,
            "sync": self.read("sync", {"status": "UNKNOWN", "reason": "not_checked", "source_commit": None}),
            "counts": counts, "data_notice": "Kein operativer Content vorhanden. Vorherige Betriebsdatenbank/Backup fehlt." if not counts["content_items"] else None,
            "safety": "LOCAL_ONLY · keine Plattformaktionen · keine Persona-Änderungen",
            "handoff": str(self.root / "Handoff" / "CODEX_RUNTIME_HANDOFF.md"),
            "external_actions": "NONE", "vps_note": "Kein externer VPS verbunden; OFFLINE bleibt ehrlich.",
            "pause_note": "Pause wird am nächsten sicheren Schritt wirksam; begrenzte Prüfungen dürfen bis zu 60 Sekunden abschließen. Fortsetzen startet bei Bedarf einen Worker am gespeicherten Schritt; eine erledigte Queue wird nicht erneut ausgeführt.",
        }
