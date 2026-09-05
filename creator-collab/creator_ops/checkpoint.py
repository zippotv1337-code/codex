from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo


class AutopilotCheckpointService:
    """Write one atomic, current savegame for a later local autopilot run."""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    @staticmethod
    def _lines(values: list[str], empty: str = "Keine.") -> str:
        clean = [value.strip() for value in values if value.strip()]
        return "\n".join(f"- {value}" for value in clean) if clean else f"- {empty}"

    def write(
        self,
        path: Path,
        *,
        last_completed_task: str,
        current_task: str,
        continuation_point: str,
        changed_files: list[str],
        tests_passed: int,
        tests_failed: int,
        backup_status: str,
        blockers: list[str],
        owner_gates: list[str],
        parked_tasks: list[str],
        next_tasks: list[str],
        generated_at: datetime | None = None,
    ) -> Path:
        if len(next_tasks) != 3:
            raise ValueError("checkpoint_requires_exactly_three_next_tasks")
        stamp = (generated_at or datetime.now(ZoneInfo("Europe/Berlin"))).isoformat(timespec="minutes")
        resume = (
            "Lies zuerst AUTOPILOT_CHECKPOINT.md, PROJECT_RESUME.md, CURRENT_HANDOFF.md "
            "und das neueste Sitzungsjournal. Prüfe den lokalen Zustand und setze bei "
            f"folgendem Punkt fort: {continuation_point} Git/GitHub bleiben geparkt. "
            "Keine externen Aktionen ohne Owner-Freigabe; rechtzeitig erneut checkpointen."
        )
        body = f"""# AUTOPILOT CHECKPOINT

Aktueller Speicherstand, ersetzt bei jedem abgeschlossenen Autopilot-Run.

## Zeitpunkt

{stamp} · Europe/Berlin

## Letzter vollständig erledigter Task

{last_completed_task}

## Aktuell angefangener Task

{current_task}

## Exakter Fortsetzungspunkt

{continuation_point}

## Geänderte Dateien

{self._lines(changed_files)}

## Teststatus

- Bestanden: {tests_passed}
- Fehlgeschlagen: {tests_failed}

## Backupstatus

{backup_status}

## Bekannte Blocker

{self._lines(blockers)}

## Owner-Gates

{self._lines(owner_gates)}

## Geparkte Aufgaben

{self._lines(parked_tasks)}

## Nächste 3 priorisierte Aufgaben

{self._lines(next_tasks)}

## Exakter Resume-Auftrag

> {resume}
"""
        destination = path if path.is_absolute() else self.project_root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", delete=False, dir=destination.parent
        ) as handle:
            handle.write(body)
            temporary = Path(handle.name)
        temporary.replace(destination)
        return destination
