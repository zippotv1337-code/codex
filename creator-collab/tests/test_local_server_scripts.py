from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LocalServerScriptTests(unittest.TestCase):
    def test_start_wrapper_has_health_port_paths_and_logs(self) -> None:
        text = (ROOT / "START_CREATOR_OPS.ps1").read_text(encoding="utf-8")
        for marker in (
            "$PSScriptRoot", "Get-NetTCPConnection", "/api/health",
            "local_server.log", "creator_ops.pid", "-WorkingDirectory $projectRoot",
            "-WindowStyle Hidden", "if (-not $NoBrowser)",
        ):
            self.assertIn(marker, text)

    def test_management_wrappers_delegate_to_single_server_logic(self) -> None:
        self.assertIn("START_CREATOR_OPS.ps1", (ROOT / "run_dashboard.ps1").read_text(encoding="utf-8"))
        self.assertIn("STOP_CREATOR_OPS.ps1", (ROOT / "RESTART_CREATOR_OPS.ps1").read_text(encoding="utf-8"))
        stop = (ROOT / "STOP_CREATOR_OPS.ps1").read_text(encoding="utf-8")
        self.assertIn("creator_ops\\.web", stop)
        self.assertIn("$process.Kill()", stop)
        self.assertIn("/api/health", (ROOT / "STATUS_CREATOR_OPS.ps1").read_text(encoding="utf-8"))

    def test_lan_start_requires_auth_and_limits_optional_firewall_rule(self) -> None:
        text = (ROOT / "START_LAN_CREATOR_OPS.ps1").read_text(encoding="utf-8")
        for marker in (
            "CREATOR_OPS_PASSWORD", "mindestens 12", "RemoteAddress LocalSubnet",
            "-Profile Private", "/api/health", "ipconfig", "192\\.168",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
