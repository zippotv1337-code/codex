from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RemoteScriptTests(unittest.TestCase):
    def test_script_captures_checks_and_clears_ephemeral_url(self) -> None:
        script = (ROOT / "run_remote_free.ps1").read_text(encoding="utf-8")
        self.assertIn("REMOTE_ACCESS_CURRENT.txt", script)
        self.assertIn("trycloudflare", script)
        self.assertIn("Set-Clipboard", script)
        self.assertIn("$publicUrl/api/health", script)
        self.assertIn("Remove-Item -LiteralPath $remoteStatePath", script)
        self.assertIn("$NotificationScript -Url $publicUrl", script)


if __name__ == "__main__":
    unittest.main()
