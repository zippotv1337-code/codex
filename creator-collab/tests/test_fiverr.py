from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creator_ops.database import CreatorDatabase
from creator_ops.fiverr import (
    HUMAN_GATE,
    WRITE_READY,
    FiverrAutomationService,
    FiverrGigSnapshot,
    FiverrPlaywrightWriteProvider,
)


class FiverrAutomationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = CreatorDatabase(Path(self.temp.name) / "fiverr.db")
        self.database.initialize()
        self.service = FiverrAutomationService(self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def gig() -> FiverrGigSnapshot:
        return FiverrGigSnapshot(
            gig_key="ai-workflow-automation",
            title="I will build AI workflow automation for your business",
            status="ACTIVE",
            public_url="https://www.fiverr.com/zippoworkz/example",
            edit_url="https://www.fiverr.com/users/zippoworkz/manage_gigs/example/edit",
            packages={"basic_usd": 149, "standard_usd": 349, "premium_usd": 699},
            metrics={"impressions": 13, "clicks": 0, "orders": 0},
            assets=["docs/assets/fiverr-gig-cover-ai-workflow-automation-v1.png"],
        )

    def test_browser_snapshot_is_durable_and_write_ready(self) -> None:
        payload = self.service.record_browser_snapshot(
            username="zippoworkz", gigs=(self.gig(),)
        )
        self.assertEqual(payload["status"], WRITE_READY)
        self.assertEqual(payload["active_gig_count"], 1)
        self.assertEqual(payload["gigs"][0]["metrics"]["impressions"], 13)
        self.assertEqual(payload["gigs"][0]["packages"]["premium_usd"], 699)

    def test_sync_updates_same_gig_without_duplication(self) -> None:
        self.service.record_browser_snapshot(username="zippoworkz", gigs=(self.gig(),))
        self.service.record_browser_snapshot(username="zippoworkz", gigs=(self.gig(),))
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM fiverr_accounts"), 1)
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM fiverr_gigs"), 1)

    def test_operation_key_prevents_duplicate_writes(self) -> None:
        self.service.record_browser_snapshot(username="zippoworkz", gigs=(self.gig(),))
        first = self.service.reserve_operation(
            username="zippoworkz", kind="UPDATE_GIG", fingerprint="copy-v1",
            gig_key="ai-workflow-automation",
        )
        second = self.service.reserve_operation(
            username="zippoworkz", kind="UPDATE_GIG", fingerprint="copy-v1",
            gig_key="ai-workflow-automation",
        )
        self.assertEqual(first["operation_id"], second["operation_id"])
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM fiverr_operations"), 1)

    def test_dashboard_assets_expose_status_and_human_gate(self) -> None:
        root = Path(__file__).resolve().parents[1]
        page = (root / "dashboard" / "fiverr.html").read_text(encoding="utf-8")
        script = (root / "dashboard" / "fiverr.js").read_text(encoding="utf-8")
        studio = (root / "dashboard" / "studio.js").read_text(encoding="utf-8")
        self.assertIn("Fiverr Ops", page)
        self.assertIn("/api/fiverr", script)
        self.assertIn("FIVERR HUMAN GATE", script)
        self.assertIn('["/fiverr","Seller Ops"]', studio)

    def test_human_gate_is_persisted_without_secrets(self) -> None:
        self.service.record_browser_snapshot(username="zippoworkz", gigs=(self.gig(),))
        payload = self.service.record_human_gate(
            username="zippoworkz", gate_type="CAPTCHA",
            page_url="https://www.fiverr.com/users/zippoworkz/manage_gigs/example/edit",
            action="Challenge im normalen Browser abschließen",
            reason="Fiverr fordert persönliche Browser-Interaktion",
            after_action="Gig-Felder lesen, korrigieren und verifizieren",
        )
        self.assertEqual(payload["status"], HUMAN_GATE)
        self.assertEqual(len(payload["human_gates"]), 1)
        self.assertNotIn("cookie", str(payload).lower())

    def test_write_provider_classifies_session_states(self) -> None:
        self.assertEqual(
            FiverrPlaywrightWriteProvider("AUTHENTICATED_SELLER").readiness(),
            WRITE_READY,
        )
        self.assertEqual(FiverrPlaywrightWriteProvider("CAPTCHA").readiness(), HUMAN_GATE)

    def test_resolved_gate_restores_write_ready_without_new_account(self) -> None:
        self.service.record_browser_snapshot(username="zippoworkz", gigs=(self.gig(),))
        self.service.record_human_gate(
            username="zippoworkz", gate_type="CAPTCHA",
            page_url="https://www.fiverr.com/example/edit",
            action="Challenge abschließen", reason="Challenge sichtbar",
            after_action="Felder verifizieren",
        )
        payload = self.service.resolve_human_gate(
            username="zippoworkz", gate_type="CAPTCHA"
        )
        self.assertEqual(payload["status"], WRITE_READY)
        self.assertEqual(payload["human_gates"], [])
        self.assertEqual(self.database.scalar("SELECT COUNT(*) FROM fiverr_accounts"), 1)


if __name__ == "__main__":
    unittest.main()
