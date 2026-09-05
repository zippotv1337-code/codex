from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from creator_ops.checkpoint import AutopilotCheckpointService


class AutopilotCheckpointTests(unittest.TestCase):
    def test_checkpoint_contains_required_resume_state(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = AutopilotCheckpointService(root).write(
                Path("AUTOPILOT_CHECKPOINT.md"),
                last_completed_task="Owner Review vorbereitet",
                current_task="Run abgeschlossen; kein halber Task",
                continuation_point="Echte Analytics nach Owner-Eingabe prüfen.",
                changed_files=["dashboard/app.js"],
                tests_passed=49,
                tests_failed=0,
                backup_status="Backup geprüft.",
                blockers=["Keine echten Analytics."],
                owner_gates=["Vier Pakete prüfen."],
                parked_tasks=["Git/GitHub."],
                next_tasks=["Owner Review", "Analytics", "Neue Produktion"],
                generated_at=datetime(2026, 9, 4, 22, 0, tzinfo=ZoneInfo("Europe/Berlin")),
            )
            text = path.read_text(encoding="utf-8")
            for heading in (
                "## Zeitpunkt", "## Letzter vollständig erledigter Task",
                "## Aktuell angefangener Task", "## Exakter Fortsetzungspunkt",
                "## Geänderte Dateien", "## Teststatus", "## Backupstatus",
                "## Bekannte Blocker", "## Owner-Gates", "## Geparkte Aufgaben",
                "## Nächste 3 priorisierte Aufgaben", "## Exakter Resume-Auftrag",
            ):
                self.assertIn(heading, text)
            self.assertIn("Git/GitHub bleiben geparkt", text)
            self.assertIn("Bestanden: 49", text)

    def test_checkpoint_requires_exactly_three_next_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            service = AutopilotCheckpointService(Path(folder))
            with self.assertRaisesRegex(ValueError, "exactly_three"):
                service.write(
                    Path("checkpoint.md"), last_completed_task="x", current_task="y",
                    continuation_point="z", changed_files=[], tests_passed=0,
                    tests_failed=0, backup_status="none", blockers=[], owner_gates=[],
                    parked_tasks=[], next_tasks=["only one"],
                )


if __name__ == "__main__":
    unittest.main()
