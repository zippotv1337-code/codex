from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from creator_ops.handoff import HandoffService, HandoffValidationError, build_handoff
from creator_ops.secret_provider import (
    EnvironmentSecretProvider,
    SecretBroker,
    SecretValue,
    create_secret_provider,
    validate_alias,
)
from creator_ops.secret_scan import scan_text
from creator_ops.security_status import SecurityStatusService


ROOT = Path(__file__).resolve().parents[1]


class SecurityAndHandoffTests(unittest.TestCase):
    def test_secret_value_is_redacted_and_environment_fallback_is_explicit(self) -> None:
        fake_value = "runtime-" + "credential-value"
        provider = EnvironmentSecretProvider(
            {"EXAMPLE_RUNTIME_TOKEN": fake_value},
            {"secret://example/token": "EXAMPLE_RUNTIME_TOKEN"},
        )
        value = provider.get("secret://example/token")
        self.assertIsInstance(value, SecretValue)
        self.assertEqual(str(value), "<redacted>")
        self.assertNotIn(fake_value, repr(value))
        self.assertEqual(value.reveal(), fake_value)
        with self.assertRaisesRegex(ValueError, "invalid_secret_alias"):
            validate_alias("plain-text-secret")

    def test_broker_audit_contains_alias_but_never_value(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            audit = Path(tempdir) / "secret-access.jsonl"
            fake_value = "broker-" + "credential-value"
            provider = EnvironmentSecretProvider(
                {"EXAMPLE_RUNTIME_TOKEN": fake_value},
                {"secret://example/token": "EXAMPLE_RUNTIME_TOKEN"},
            )
            SecretBroker(provider, audit).get("secret://example/token", agent="test-agent")
            text = audit.read_text(encoding="utf-8")
            self.assertIn("secret://example/token", text)
            self.assertIn("test-agent", text)
            self.assertNotIn(fake_value, text)

    def test_provider_factory_fails_closed_for_unknown_selection(self) -> None:
        provider = create_secret_provider({"ZIPPOWORKZ_SECRET_PROVIDER": "unknown-provider"})
        self.assertFalse(provider.ready)
        self.assertIsNone(provider.get("secret://example/token"))

    def test_leak_scanner_reports_location_not_secret_value(self) -> None:
        fake_value = "actually-" + "sensitive-looking-value"
        candidate = "API" + "_KEY = " + chr(34) + fake_value + chr(34)
        findings = scan_text(candidate, "fixture.env")
        self.assertEqual([(item.path, item.line, item.kind) for item in findings], [
            ("fixture.env", 1, "literal-secret-assignment")
        ])
        self.assertNotIn(fake_value, repr(findings))
        self.assertEqual(scan_text('TOKEN_ALIAS="secret://example/token"'), [])

    def test_handoff_is_validated_atomic_and_archived_without_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            exchange = Path(tempdir) / "Exchange" / "Codex"
            service = HandoffService(ROOT / "config" / "security" / "HANDOFF_SCHEMA.json", exchange)
            payload = build_handoff(
                run_id="security-p0-001",
                objective="Integrate the security package",
                changes=["Provider and local channel gate implemented"],
                tests={"passed": 4, "failed": 0},
                blockers=["platform accounts are not connected"],
                owner_actions=["Choose one primary secret provider"],
                next_step="Connect the provider aliases when ready",
                status="NEEDS_OWNER_ACTION",
            )
            payload["secret_aliases_used"] = ["secret://meta/leona-voss/access-token"]
            first = service.write(payload)
            service.write({**payload, "run_id": "security-p0-002"})
            current = json.loads(Path(first["current_json"]).read_text(encoding="utf-8"))
            self.assertEqual(current["run_id"], "security-p0-002")
            self.assertGreaterEqual(len(list((exchange / "Archive").glob("*.json"))), 2)
            self.assertGreaterEqual(len(list((exchange / "Archive").glob("*.md"))), 1)
            self.assertNotIn("credential-value", Path(first["current_markdown"]).read_text(encoding="utf-8"))

            bad = dict(payload)
            bad["changes"] = ['access_token="' + "unsafe-credential-value" + '"']
            with self.assertRaisesRegex(HandoffValidationError, "possible_secret"):
                service.validate(bad)

    def test_dashboard_security_status_is_value_free(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            project = root / "Workspace" / "codex_ingest" / "creator-collab"
            (root / "_system").mkdir(parents=True)
            project.mkdir(parents=True)
            (root / "_system" / "PERMISSIONS_POLICY.json").write_text(
                json.dumps({"version": "2.1", "mode": "AUTONOMOUS_WITH_OWNER_GATES"}),
                encoding="utf-8",
            )
            (root / "_system" / "HANDOFF_SCHEMA.json").write_text(
                json.dumps({"schema_version": "1.0", "required": ["run_id"]}),
                encoding="utf-8",
            )
            fake_value = "dashboard-" + "credential-value"
            provider = EnvironmentSecretProvider(
                {"META_ACCESS_TOKEN_LEONA_VOSS": fake_value}
            )
            with patch("creator_ops.security_status.create_secret_provider", return_value=provider):
                snapshot = SecurityStatusService(project, root).snapshot()
            serialized = json.dumps(snapshot)
            self.assertTrue(snapshot["policy"]["installed"])
            self.assertFalse(snapshot["secret_provider"]["values_exposed"])
            self.assertNotIn(fake_value, serialized)


if __name__ == "__main__":
    unittest.main()
