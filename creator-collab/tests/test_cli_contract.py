from __future__ import annotations

import unittest
from unittest.mock import patch

from creator_ops.cli import CANONICAL_OPERATIONAL_DB, main, parser


class CliDataContractTests(unittest.TestCase):
    def test_default_database_is_canonical_operational_store(self) -> None:
        args = parser().parse_args(["status"])

        self.assertEqual(args.db, CANONICAL_OPERATIONAL_DB)
        self.assertEqual(args.db.name, "review_dashboard.db")

    def test_demo_refuses_canonical_operational_store(self) -> None:
        with patch("sys.argv", ["creator-ops", "demo"]):
            with self.assertRaisesRegex(
                SystemExit,
                "Refusing to run demo against the canonical operational database",
            ):
                main()


if __name__ == "__main__":
    unittest.main()
