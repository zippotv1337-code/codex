from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from creator_ops.node_status import AutonomyNodeStatus


class NodeStatusTests(unittest.TestCase):
    def test_idle_local_node_and_missing_vps_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            run = root / "Tasks" / "RUN_STATE.json"
            run.parent.mkdir(parents=True)
            run.write_text(
                json.dumps(
                    {
                        "state": "IDLE_CLEAN",
                        "active": False,
                        "machine_id": "local-test",
                        "updated_at": "2026-09-29T12:00:00+00:00",
                    }
                ),
                encoding="utf-8",
            )
            status = AutonomyNodeStatus(root).snapshot()
            self.assertEqual(status["local_ai"]["status"], "READY")
            self.assertEqual(status["vps"]["status"], "WAITING_EXTERNAL_NODE")
            self.assertFalse(status["global_blocked"])

    def test_structured_vps_status_is_read_without_network_or_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target = root / "Exchange" / "VPS_TO_CODEX" / "Current" / "NODE_STATUS.json"
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps(
                    {
                        "status": "READY",
                        "machine_id": "vps-test",
                        "updated_at": "2026-09-29T12:00:00+00:00",
                        "token": "must-not-be-projected",
                    }
                ),
                encoding="utf-8",
            )
            status = AutonomyNodeStatus(root).snapshot()
            self.assertEqual(status["vps"]["status"], "READY")
            self.assertNotIn("token", status["vps"])


if __name__ == "__main__":
    unittest.main()
