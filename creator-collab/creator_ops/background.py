from __future__ import annotations

import json
import re
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable

from .database import CreatorDatabase, utc_now


PENDING = "PENDING"
RUNNING = "RUNNING"
WAITING_FOR_CAPACITY = "WAITING_FOR_CAPACITY"
FAILED_RETRYABLE = "FAILED_RETRYABLE"
BLOCKED = "BLOCKED"
COMPLETE = "COMPLETE"


class CapacityUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class BackgroundRunResult:
    run_key: str
    status: str
    current_step: str
    attempts: int
    next_run_at: str | None
    error_class: str | None
    reused: bool


class MiniJournalService:
    """Atomic run journal. A STARTED file survives abrupt process termination."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    @staticmethod
    def _safe_name(run_key: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_.-]+", "-", run_key).strip("-")[:100] or "run"

    def write(self, payload: dict[str, object]) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / f"{self._safe_name(str(payload['run_key']))}.md"
        body = f"""# Autopilot Mini-Journal

- Run: `{payload['run_key']}`
- Task: {payload['task_name']}
- Status: `{payload['status']}`
- Aktueller Schritt: `{payload['current_step']}`
- Versuche: {payload['attempts']}
- Aktualisiert: {payload['updated_at']}
- Nächster Lauf: {payload.get('next_run_at') or 'nicht gesetzt'}
- Fehlerklasse: {payload.get('error_class') or 'keine'}
- Fehlercode: {payload.get('error_code') or 'keiner'}

Dieser Eintrag enthält keine Secrets und dokumentiert nur den lokalen Runtime-Status.
"""
        with NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", delete=False, dir=self.directory
        ) as handle:
            handle.write(body)
            temporary = Path(handle.name)
        temporary.replace(target)
        return target


class BackgroundCoordinator:
    """Durable local run state with a cross-process SQLite lease."""

    def __init__(
        self,
        database: CreatorDatabase,
        project_root: Path,
        *,
        lease_name: str = "creator-ops-autopilot",
        lease_ttl: timedelta = timedelta(minutes=15),
    ) -> None:
        self.database = database
        self.project_root = Path(project_root)
        self.lease_name = lease_name
        self.lease_ttl = lease_ttl
        self.journal = MiniJournalService(self.project_root / "sessions" / "runtime")

    @staticmethod
    def _now(value: datetime | None = None) -> datetime:
        current = value or datetime.now(UTC)
        return current.replace(tzinfo=UTC) if current.tzinfo is None else current.astimezone(UTC)

    @staticmethod
    def _classify(error: Exception) -> tuple[str, str, str]:
        if isinstance(error, CapacityUnavailable):
            return WAITING_FOR_CAPACITY, "CAPACITY", "capacity_unavailable"
        if isinstance(error, (ConnectionError, TimeoutError)):
            return FAILED_RETRYABLE, "RETRYABLE_EXTERNAL", type(error).__name__
        if isinstance(error, (KeyError, ValueError, PermissionError)):
            return BLOCKED, "INPUT_OR_POLICY", type(error).__name__
        return FAILED_RETRYABLE, "UNEXPECTED_RETRYABLE", type(error).__name__

    def _event(
        self,
        connection: sqlite3.Connection,
        run_id: int | None,
        event_type: str,
        severity: str,
        step: str,
        detail: dict[str, object] | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO runtime_events
                (run_id, event_type, severity, step, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                event_type,
                severity,
                step,
                json.dumps(detail or {}, ensure_ascii=False, sort_keys=True),
                utc_now(),
            ),
        )

    def _acquire(self, now: datetime) -> str:
        token = secrets.token_urlsafe(24)
        connection = self.database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT owner_token, expires_at FROM run_leases WHERE lease_name=?",
                (self.lease_name,),
            ).fetchone()
            if row is not None and datetime.fromisoformat(row["expires_at"]) > now:
                raise RuntimeError("background_run_already_active")
            if row is not None:
                connection.execute(
                    "DELETE FROM run_leases WHERE lease_name=?", (self.lease_name,)
                )
                self._event(
                    connection, None, "STALE_LEASE_RECOVERED", "WARNING", "lease"
                )
            connection.execute(
                """
                INSERT INTO run_leases
                    (lease_name, owner_token, acquired_at, heartbeat_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self.lease_name,
                    token,
                    now.isoformat(),
                    now.isoformat(),
                    (now + self.lease_ttl).isoformat(),
                ),
            )
            connection.commit()
            return token
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def heartbeat(self, token: str, now: datetime | None = None) -> None:
        current = self._now(now)
        with self.database.transaction() as connection:
            changed = connection.execute(
                """
                UPDATE run_leases SET heartbeat_at=?, expires_at=?
                WHERE lease_name=? AND owner_token=?
                """,
                (
                    current.isoformat(),
                    (current + self.lease_ttl).isoformat(),
                    self.lease_name,
                    token,
                ),
            ).rowcount
            if changed != 1:
                raise RuntimeError("background_lease_lost")

    def _release(self, token: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM run_leases WHERE lease_name=? AND owner_token=?",
                (self.lease_name, token),
            )

    def _owns_lease(self, token: str) -> bool:
        return bool(
            self.database.scalar(
                "SELECT COUNT(*) FROM run_leases WHERE lease_name=? AND owner_token=?",
                (self.lease_name, token),
            )
        )

    def _start_heartbeat(
        self, token: str
    ) -> tuple[threading.Event, threading.Thread, list[Exception]]:
        stop = threading.Event()
        errors: list[Exception] = []
        interval = max(0.05, min(30.0, self.lease_ttl.total_seconds() / 3))

        def renew() -> None:
            while not stop.wait(interval):
                try:
                    self.heartbeat(token)
                except Exception as error:  # surfaced by the owning run thread
                    errors.append(error)
                    return

        thread = threading.Thread(
            target=renew,
            name=f"creator-ops-heartbeat-{self.lease_name}",
            daemon=True,
        )
        thread.start()
        return stop, thread, errors

    def _payload(self, row: sqlite3.Row) -> dict[str, object]:
        return dict(row)

    def _result(self, row: sqlite3.Row, *, reused: bool) -> BackgroundRunResult:
        return BackgroundRunResult(
            run_key=row["run_key"],
            status=row["status"],
            current_step=row["current_step"],
            attempts=int(row["attempts"]),
            next_run_at=row["next_run_at"],
            error_class=row["error_class"],
            reused=reused,
        )

    def run_once(
        self,
        run_key: str,
        task_name: str,
        task: Callable[[], dict[str, object] | None],
        *,
        capacity_available: bool = True,
        now: datetime | None = None,
        next_capacity_at: datetime | None = None,
    ) -> BackgroundRunResult:
        current = self._now(now)
        existing = self.database.one(
            "SELECT * FROM background_runs WHERE run_key=?", (run_key,)
        )
        if existing is not None and existing["status"] == COMPLETE:
            return self._result(existing, reused=True)
        if (
            existing is not None
            and existing["status"] in {WAITING_FOR_CAPACITY, FAILED_RETRYABLE}
            and existing["next_run_at"]
            and datetime.fromisoformat(existing["next_run_at"]) > current
        ):
            return self._result(existing, reused=True)

        token = self._acquire(current)
        run_id: int | None = None
        heartbeat_stop: threading.Event | None = None
        heartbeat_thread: threading.Thread | None = None
        heartbeat_errors: list[Exception] = []
        try:
            # Another process may have completed the same idempotency key while
            # this process waited for the shared lease. Re-read after acquire.
            existing = self.database.one(
                "SELECT * FROM background_runs WHERE run_key=?", (run_key,)
            )
            if existing is not None and existing["status"] == COMPLETE:
                return self._result(existing, reused=True)
            if (
                existing is not None
                and existing["status"] in {WAITING_FOR_CAPACITY, FAILED_RETRYABLE}
                and existing["next_run_at"]
                and datetime.fromisoformat(existing["next_run_at"]) > current
            ):
                return self._result(existing, reused=True)

            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO background_runs
                        (run_key, task_name, status, current_step, cursor_json,
                         attempts, started_at, updated_at)
                    VALUES (?, ?, ?, 'START', '{}', 1, ?, ?)
                    ON CONFLICT(run_key) DO UPDATE SET
                        task_name=excluded.task_name,
                        status=excluded.status,
                        current_step='RESUME',
                        attempts=background_runs.attempts+1,
                        error_class=NULL,
                        error_code=NULL,
                        updated_at=excluded.updated_at
                    """,
                    (run_key, task_name, RUNNING, current.isoformat(), current.isoformat()),
                )
                row = connection.execute(
                    "SELECT * FROM background_runs WHERE run_key=?", (run_key,)
                ).fetchone()
                run_id = int(row["id"])
                self._event(connection, run_id, "RUN_STARTED", "INFO", row["current_step"])
            row = self.database.one("SELECT * FROM background_runs WHERE id=?", (run_id,))
            self.journal.write(self._payload(row))

            if not capacity_available:
                raise CapacityUnavailable("capacity_unavailable")

            heartbeat_stop, heartbeat_thread, heartbeat_errors = self._start_heartbeat(token)
            output = task() or {}
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=2)
            if heartbeat_errors:
                raise RuntimeError("background_lease_lost") from heartbeat_errors[0]
            self.heartbeat(token)
            with self.database.transaction() as connection:
                changed = connection.execute(
                    """
                    UPDATE background_runs
                    SET status=?, current_step='COMPLETE', cursor_json=?,
                        next_run_at=NULL, error_class=NULL, error_code=NULL,
                        updated_at=?, completed_at=?
                    WHERE id=? AND EXISTS (
                        SELECT 1 FROM run_leases
                        WHERE lease_name=? AND owner_token=?
                    )
                    """,
                    (
                        COMPLETE,
                        json.dumps(output, ensure_ascii=False, sort_keys=True),
                        utc_now(),
                        utc_now(),
                        run_id,
                        self.lease_name,
                        token,
                    ),
                ).rowcount
                if changed != 1:
                    raise RuntimeError("background_lease_lost")
                self._event(connection, run_id, "RUN_COMPLETED", "INFO", "COMPLETE")
        except Exception as error:
            if heartbeat_stop is not None:
                heartbeat_stop.set()
            if heartbeat_thread is not None and heartbeat_thread.is_alive():
                heartbeat_thread.join(timeout=2)
            status, error_class, error_code = self._classify(error)
            resume_at = next_capacity_at or (current + timedelta(hours=1))
            if run_id is not None and self._owns_lease(token):
                with self.database.transaction() as connection:
                    changed = connection.execute(
                        """
                        UPDATE background_runs
                        SET status=?, current_step='RESUME', next_run_at=?,
                            error_class=?, error_code=?, updated_at=?
                        WHERE id=? AND EXISTS (
                            SELECT 1 FROM run_leases
                            WHERE lease_name=? AND owner_token=?
                        )
                        """,
                        (
                            status,
                            resume_at.isoformat()
                            if status in {WAITING_FOR_CAPACITY, FAILED_RETRYABLE}
                            else None,
                            error_class,
                            error_code,
                            utc_now(),
                            run_id,
                            self.lease_name,
                            token,
                        ),
                    ).rowcount
                    if changed == 1:
                        self._event(
                            connection,
                            run_id,
                            "RUN_WAITING" if status == WAITING_FOR_CAPACITY else "RUN_FAILED",
                            "WARNING" if status != BLOCKED else "ERROR",
                            "RESUME",
                            {"error_class": error_class, "error_code": error_code},
                        )
            if status != WAITING_FOR_CAPACITY:
                row = self.database.one("SELECT * FROM background_runs WHERE id=?", (run_id,))
                if row is not None:
                    self.journal.write(self._payload(row))
                raise
        finally:
            if heartbeat_stop is not None:
                heartbeat_stop.set()
            if heartbeat_thread is not None and heartbeat_thread.is_alive():
                heartbeat_thread.join(timeout=2)
            self._release(token)

        row = self.database.one("SELECT * FROM background_runs WHERE id=?", (run_id,))
        self.journal.write(self._payload(row))
        return self._result(row, reused=False)

    def health(self, now: datetime | None = None) -> dict[str, object]:
        current = self._now(now)
        lease = self.database.one(
            "SELECT heartbeat_at, expires_at FROM run_leases WHERE lease_name=?",
            (self.lease_name,),
        )
        waiting = int(
            self.database.scalar(
                "SELECT COUNT(*) FROM background_runs WHERE status=?",
                (WAITING_FOR_CAPACITY,),
            )
            or 0
        )
        retryable = int(
            self.database.scalar(
                "SELECT COUNT(*) FROM background_runs WHERE status=?",
                (FAILED_RETRYABLE,),
            )
            or 0
        )
        blocked = int(
            self.database.scalar(
                "SELECT COUNT(*) FROM background_runs WHERE status=?",
                (BLOCKED,),
            )
            or 0
        )
        running = int(
            self.database.scalar(
                "SELECT COUNT(*) FROM background_runs WHERE status=?",
                (RUNNING,),
            )
            or 0
        )
        lease_state = "none"
        if lease is not None:
            lease_state = (
                "active"
                if datetime.fromisoformat(lease["expires_at"]) > current
                else "stale"
            )
        orphaned_running = running if lease_state != "active" else 0
        return {
            "status": "degraded"
            if lease_state == "stale" or retryable or blocked or orphaned_running
            else "ok",
            "lease": lease_state,
            "waiting_for_capacity": waiting,
            "failed_retryable": retryable,
            "blocked": blocked,
            "orphaned_running": orphaned_running,
        }
