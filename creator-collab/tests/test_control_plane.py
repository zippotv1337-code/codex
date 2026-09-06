from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from creator_ops.cli import build_pipeline
from creator_ops.control_plane import ControlPlaneService
from creator_ops.review import ReviewDashboardService
from creator_ops.web import create_server


ROOT = Path(__file__).resolve().parents[1]


class ControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db_path = self.root / "review.db"
        self.pipeline = build_pipeline(self.db_path)
        self.pipeline.initialize()
        self.review = ReviewDashboardService(self.pipeline)
        self.review.ensure_date(date(2026, 9, 5))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_capability_contract_does_not_require_a_future_model(self) -> None:
        service = ControlPlaneService(self.review, self.root / "state.json")
        payload = service.snapshot()
        self.assertEqual(payload["contract"]["model_policy"], "stable-current-model")
        self.assertEqual(payload["contract"]["future_models"], "optional-capability-bonus")
        self.assertTrue(payload["contract"]["backward_compatible"])
        routing = payload["contract"]["model_routing"]
        self.assertEqual(routing["preferred_model"], "gpt-6-astra")
        self.assertEqual(routing["fallback_model"], "gpt-5.6-sol")
        self.assertEqual(routing["reasoning_effort"], "high")
        self.assertFalse(routing["preferred_required"])
        enhanced = next(item for item in payload["capabilities"] if item["id"] == "generation.enhanced")
        astra = next(item for item in payload["capabilities"] if item["id"] == "generation.astra")
        external = next(item for item in payload["capabilities"] if item["id"] == "publish.external")
        self.assertEqual(enhanced["state"], "OPTIONAL_BONUS")
        self.assertFalse(enhanced["required"])
        self.assertEqual(astra["state"], "OPTIONAL_BONUS")
        self.assertFalse(astra["required"])
        self.assertEqual(external["state"], "OWNER_GATE")

    def test_commands_are_atomic_and_pause_blocks_run(self) -> None:
        state_path = self.root / "state.json"
        service = ControlPlaneService(self.review, state_path)
        paused = service.command("pause")
        self.assertEqual(paused["state"]["status"], "PAUSED")
        with self.assertRaisesRegex(ValueError, "autopilot_is_paused"):
            service.command("run-once")
        service.command("resume")
        completed = service.command("run-once")
        self.assertEqual(completed["state"]["status"], "IDLE")
        self.assertEqual(completed["state"]["run_count"], 1)
        self.assertGreater(len(completed["queue"]), 0)
        self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))["run_count"], 1)

    def test_http_control_plane_and_large_preview_surface(self) -> None:
        server = create_server(self.db_path, port=0, asset_root=self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(f"{base}/control", timeout=5) as response:
                self.assertIn("Capability-basiert", response.read().decode("utf-8"))
            with urlopen(f"{base}/api/control-plane", timeout=5) as response:
                payload = json.load(response)
            self.assertEqual(payload["contract"]["execution"], "local-safe-only")
            with urlopen(Request(f"{base}/api/control-plane/checkpoint", method="POST"), timeout=5) as response:
                saved = json.load(response)
            self.assertIsNotNone(saved["state"]["checkpoint_at"])
            with urlopen(f"{base}/", timeout=5) as response:
                html = response.read().decode("utf-8")
            self.assertIn('id="large-preview"', html)
            self.assertIn("Große Instagram-Vorschau", (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_unknown_command_is_rejected(self) -> None:
        service = ControlPlaneService(self.review, self.root / "state.json")
        with self.assertRaisesRegex(ValueError, "unsupported_control_plane_action"):
            service.command("publish")

    def test_capacity_resume_reuses_the_same_background_run(self) -> None:
        service = ControlPlaneService(self.review, self.root / "state.json")
        waiting = service.command("wait-for-capacity")
        state = waiting["state"]
        self.assertEqual(state["status"], "WAITING_FOR_CAPACITY")
        self.assertEqual(state["active_run_key"], "control-plane:1")
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                UPDATE background_runs SET next_run_at='2000-01-01T00:00:00+00:00'
                WHERE run_key='control-plane:1'
                """
            )
        resumed = service.command("run-once")
        self.assertEqual(resumed["state"]["status"], "IDLE")
        self.assertIsNone(resumed["state"]["active_run_key"])
        self.assertEqual(resumed["state"]["run_count"], 1)
        self.assertEqual(
            self.pipeline.db.scalar("SELECT COUNT(*) FROM background_runs"),
            1,
        )


if __name__ == "__main__":
    unittest.main()
