from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from creator_ops.secrets import get_secret


class SecretResolutionTests(unittest.TestCase):
    def test_environment_override_is_preserved(self) -> None:
        with patch.dict(os.environ, {"META_TEST_VALUE": "from-env"}, clear=False):
            self.assertEqual(get_secret("META_TEST_VALUE"), "from-env")

    def test_missing_broker_fails_closed_to_default(self) -> None:
        with patch.dict(os.environ, {"ZIPPOWORKZ_ROOT": r"Z:\definitely-missing-root"}, clear=False):
            os.environ.pop("META_TEST_MISSING", None)
            self.assertEqual(get_secret("META_TEST_MISSING", "fallback"), "fallback")

    def test_broker_value_is_used_when_environment_is_empty(self) -> None:
        class FakeBroker:
            @staticmethod
            def get_for_broker(name: str, worker: str) -> str:
                self.assertEqual(name, "META_TEST_BROKER")
                self.assertEqual(worker, "creator-ops-meta")
                return "from-broker"

        with patch("creator_ops.secrets._load_broker", return_value=FakeBroker()):
            with patch.dict(os.environ, {"META_TEST_BROKER": ""}, clear=False):
                self.assertEqual(get_secret("META_TEST_BROKER"), "from-broker")


if __name__ == "__main__":
    unittest.main()
