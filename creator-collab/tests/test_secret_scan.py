from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creator_ops.secret_scan import scan_file, scan_text


class SecretScanTests(unittest.TestCase):
    def test_reports_location_without_retaining_secret_value(self) -> None:
        fake_value = "actually-" + "sensitive-looking-value"
        candidate = "API" + "_KEY = " + chr(34) + fake_value + chr(34)

        findings = scan_text(candidate, "fixture.env")

        self.assertEqual(
            [(item.path, item.line, item.kind) for item in findings],
            [("fixture.env", 1, "literal-secret-assignment")],
        )
        self.assertNotIn(fake_value, repr(findings))

    def test_accepts_aliases_placeholders_and_test_only_values(self) -> None:
        safe = "\n".join(
            (
                'TOKEN_ALIAS="secret://meta/leona/access-token"',
                'API_KEY="${OPENAI_API_KEY}"',
                'CLIENT_SECRET="test-only-client-secret"',
                "META_ACCESS_TOKEN=<set-locally>",
            )
        )

        self.assertEqual(scan_text(safe, "safe.example"), [])

    def test_detects_fixed_token_and_environment_assignment(self) -> None:
        github_token = "ghp_" + "A" * 36
        text = f"note={github_token}\nSERVICE_PASSWORD=actual-sensitive-password"

        findings = scan_text(text, "unsafe.txt")

        self.assertEqual(
            [(item.line, item.kind) for item in findings],
            [(1, "github-token"), (2, "literal-secret-environment")],
        )

    def test_binary_or_unsupported_files_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            binary = Path(tempdir) / "image.png"
            binary.write_bytes(b"\x89PNG\x00\xff")

            self.assertEqual(scan_file(binary), [])


if __name__ == "__main__":
    unittest.main()
