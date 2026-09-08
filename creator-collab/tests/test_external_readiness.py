from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from unittest import TestCase
from urllib.request import urlopen

from creator_ops.cli import build_pipeline
from creator_ops.external_readiness import ExternalReadinessService, META_ENV_VARS
from creator_ops.web import create_server


class ExternalReadinessTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "docs").mkdir()
        (self.root / "output").mkdir()
        self.config = self.root / "config.toml"
        self.config.write_text(
            """
[publishing]
adapter = "unconfigured"
live_enabled = false

[scheduler]
dispatch_live = false

[capabilities]
official_instagram_publish_adapter = true
official_instagram_publish = false
live_external_actions = false
""".strip(),
            encoding="utf-8",
        )
        (self.root / "CURRENT_HANDOFF.md").write_text(
            "Fiverr browser still shows Create your profile.",
            encoding="utf-8",
        )
        (self.root / "docs" / "FIVERR_GIG1_PACKAGE_CATALOG.md").write_text(
            "# Packages\n",
            encoding="utf-8",
        )
        (self.root / "output" / "CREATOR_OPS_LIVE_HANDOFF_NO_BACKUP_1.zip").write_bytes(
            b"PK"
        )
        self._env_backup = {name: os.environ.get(name) for name in META_ENV_VARS}
        for name in META_ENV_VARS:
            os.environ.pop(name, None)

    def tearDown(self) -> None:
        for name, value in self._env_backup.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp_dir.cleanup()

    def test_snapshot_is_secret_free_and_reports_missing_meta_gates(self) -> None:
        snapshot = ExternalReadinessService(self.root, self.config).snapshot()

        self.assertEqual(snapshot["schema"], "creator-ops-external-readiness-v1")
        self.assertEqual(snapshot["meta"]["status"], "BLOCKED")
        self.assertIn("meta_required_env_missing", snapshot["meta"]["blockers"])
        self.assertEqual(snapshot["fiverr"]["status"], "BLOCKED")
        self.assertTrue(snapshot["handoff_zip"]["latest"].endswith(".zip"))
        self.assertEqual(
            set(snapshot["meta"]["env"][0].keys()),
            {"name", "set", "valid_hint"},
        )
        self.assertNotIn("secret-token", json.dumps(snapshot))

    def test_ready_meta_requires_valid_config_env_and_manifest(self) -> None:
        manifest = self.root / "public_manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        self.config.write_text(
            """
[publishing]
adapter = "meta-graph"
live_enabled = true

[scheduler]
dispatch_live = true

[capabilities]
official_instagram_publish_adapter = true
official_instagram_publish = true
live_external_actions = true
""".strip(),
            encoding="utf-8",
        )
        os.environ.update(
            {
                "META_IG_USER_ID_LEONA_VOSS": "12345",
                "META_ACCESS_TOKEN_LEONA_VOSS": "secret-token-leona",
                "META_IG_USER_ID_MARA_FIELD": "67890",
                "META_ACCESS_TOKEN_MARA_FIELD": "secret-token-mara",
                "META_GRAPH_API_VERSION": "v24.0",
                "META_GRAPH_HOST": "graph.facebook.com",
                "CREATOR_OPS_META_MEDIA_MANIFEST": str(manifest),
            }
        )

        snapshot = ExternalReadinessService(self.root, self.config).snapshot()

        self.assertEqual(snapshot["meta"]["status"], "READY_FOR_PREFLIGHT")
        self.assertEqual(snapshot["meta"]["blockers"], [])
        serialized = json.dumps(snapshot)
        self.assertNotIn("secret-token-leona", serialized)
        self.assertNotIn("secret-token-mara", serialized)

    def test_current_owner_policy_overrides_historical_identity_blocker(self) -> None:
        with self.config.open('a', encoding='utf-8') as output:
            output.write('\n[operations]\nmeta_api_status = "DEFERRED_OWNER_VERIFICATION"\nfiverr_identity_status = "OWNER_REPORTED_VERIFIED"\n')
        (self.root / 'docs' / 'FIVERR_GIG_DRAFT.md').write_text('Known draft', encoding='utf-8')
        snapshot = ExternalReadinessService(self.root, self.config).snapshot()
        self.assertEqual(snapshot['meta']['status'], 'DEFERRED_OWNER_VERIFICATION')
        self.assertEqual(snapshot['fiverr']['identity_status'], 'OWNER_REPORTED_VERIFIED')
        self.assertEqual(snapshot['fiverr']['blockers'], [])
        self.assertFalse(any('Meta' in action for action in snapshot['next_actions']))

    def test_http_endpoint_exposes_external_readiness(self) -> None:
        database = self.root / "creator_ops.db"
        pipeline = build_pipeline(database)
        pipeline.initialize()
        server = create_server(
            database,
            port=0,
            asset_root=self.root,
            config_path=self.config,
            auth_password=None,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            with urlopen(f"http://127.0.0.1:{port}/api/external-readiness", timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(payload["schema"], "creator-ops-external-readiness-v1")
        self.assertEqual(payload["meta"]["status"], "BLOCKED")
