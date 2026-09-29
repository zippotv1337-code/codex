from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.reconcile_local_ai_runtime import reconcile


class RuntimeReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.task_id = "20260921-195306-154281"
        task_dir = self.root / "Tasks" / "Runs" / self.task_id
        task_dir.mkdir(parents=True)
        (self.root / "Tasks" / "RUN_STATE.json").write_text(
            json.dumps(
                {
                    "state": "BLOCKED",
                    "active": False,
                    "resume_allowed": False,
                    "run_id": "run-1",
                    "task_id": self.task_id,
                    "blocked_reason": "MODEL_ACTION_JSON_INVALID",
                    "completed_steps": [{"step": 1}],
                }
            ),
            encoding="utf-8",
        )
        (task_dir / "TASK.json").write_text(
            json.dumps(
                {
                    "task_id": self.task_id,
                    "run_id": "run-1",
                    "status": "BLOCKED",
                    "resume": False,
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_dry_run_is_read_only_and_apply_preserves_blocked_evidence(self) -> None:
        preview = reconcile(self.root, apply=False, process_check=lambda: False)
        self.assertEqual(preview["status"], "READY_TO_RECONCILE")
        self.assertTrue((self.root / "Tasks" / "Runs" / self.task_id).exists())

        result = reconcile(self.root, apply=True, process_check=lambda: False)
        self.assertEqual(result["status"], "IDLE_CLEAN")
        state = json.loads((self.root / "Tasks" / "RUN_STATE.json").read_text())
        self.assertEqual(state["state"], "IDLE_CLEAN")
        self.assertIsNone(state["task_id"])
        archived = json.loads(
            (self.root / "Tasks" / "Archive" / self.task_id / "TASK.json").read_text()
        )
        self.assertEqual(archived["status"], "BLOCKED")
        self.assertIn("not marked DONE", archived["archive_reason"])
        evidence = json.loads(Path(result["evidence"]).read_text())
        self.assertTrue(evidence["done_was_not_invented"])
        self.assertEqual(evidence["archived_task_status"], "BLOCKED")

    def test_active_or_resumable_run_is_refused(self) -> None:
        path = self.root / "Tasks" / "RUN_STATE.json"
        state = json.loads(path.read_text())
        state["active"] = True
        path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "only_inactive_blocked"):
            reconcile(self.root, apply=True, process_check=lambda: False)


if __name__ == "__main__":
    unittest.main()
