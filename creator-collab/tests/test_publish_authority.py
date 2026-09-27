from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from creator_ops.authority import live_publish_error, status

class PublishingAuthorityTests(unittest.TestCase):
    def test_missing_machine_identity_is_not_enforced_for_dev(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ZIPPOWORKZ_ROOT": directory}, clear=False):
                self.assertTrue(status()["allowed"])
                self.assertIsNone(live_publish_error())

    def test_real_node_fails_closed_without_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "MACHINE_ID.json").write_text(
                json.dumps({"machine_id": "ZIPPOWORKZ-LOCALAI"}), encoding="utf-8"
            )
            with patch.dict(os.environ, {"ZIPPOWORKZ_ROOT": directory}, clear=False):
                self.assertEqual(live_publish_error(), "publishing_authority_missing")

    def test_standby_node_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Context" / "Owner").mkdir(parents=True)
            (root / "MACHINE_ID.json").write_text(
                json.dumps({"machine_id": "ZIPPOWORKZ-LOCALAI"}), encoding="utf-8"
            )
            (root / "Context" / "Owner" / "PUBLISHING_AUTHORITY.json").write_text(
                json.dumps({"active_node": "ZIPPOWORKZ-VPS", "standby_nodes": ["ZIPPOWORKZ-LOCALAI"]}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"ZIPPOWORKZ_ROOT": directory}, clear=False):
                self.assertEqual(live_publish_error(), "publishing_standby_node")

if __name__ == "__main__":
    unittest.main()
