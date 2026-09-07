from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from creator_ops.cli import build_pipeline
from creator_ops.publishing import (
    MetaInstagramPublishingAdapter,
    PublicAssetProbeResult,
    PublishQueueService,
    UrllibPublicAssetProbe,
)
from creator_ops.review import ReviewDashboardService


class FakePublicAssetProbe:
    def __init__(self, *, failing_index: int | None = None) -> None:
        self.failing_index = failing_index
        self.urls: list[str] = []

    def probe(self, url: str) -> PublicAssetProbeResult:
        self.urls.append(url)
        index = len(self.urls)
        if index == self.failing_index:
            return PublicAssetProbeResult(
                ok=False,
                requested_host="cdn.example.test",
                final_host="cdn.example.test",
                http_status=200,
                content_type="image/png",
                jpeg_magic=False,
                error="public_asset_content_type_not_jpeg",
            )
        return PublicAssetProbeResult(
            ok=True,
            requested_host="cdn.example.test",
            final_host="cdn.example.test",
            http_status=200,
            content_type="image/jpeg",
            jpeg_magic=True,
        )


class ReadOnlyMetaTransport:
    def __init__(
        self,
        ig_user_id: str,
        *,
        returned_id: str | None = None,
        username: str = "verified.creator",
        quota_usage: int = 4,
        quota_total: int = 100,
    ) -> None:
        self.ig_user_id = ig_user_id
        self.returned_id = returned_id or ig_user_id
        self.username = username
        self.quota_usage = quota_usage
        self.quota_total = quota_total
        self.gets: list[tuple[str, dict[str, str]]] = []

    def post(self, path: str, data: dict[str, str]) -> dict[str, object]:
        raise AssertionError("preflight must never issue a Graph POST")

    def get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        self.gets.append((path, params))
        if path.endswith("/content_publishing_limit"):
            return {
                "data": [
                    {
                        "quota_usage": self.quota_usage,
                        "config": {
                            "quota_total": self.quota_total,
                            "quota_duration": 86400,
                        },
                    }
                ]
            }
        return {
            "id": self.returned_id,
            "username": self.username,
            "account_type": "BUSINESS",
        }


class FakeUrlResponse:
    status = 200
    headers = {"Content-Type": "image/jpeg; charset=binary"}

    def __enter__(self) -> "FakeUrlResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def geturl(self) -> str:
        return "https://media.example.test/final.jpg"

    def read(self, amount: int) -> bytes:
        assert amount == 3
        return b"\xff\xd8\xff"


class MetaPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pipeline = build_pipeline(self.root / "review.db")
        self.pipeline.initialize()
        self.review = ReviewDashboardService(self.pipeline)
        self.card = self.review.ensure_date(date(2026, 9, 9))[0]
        self.content_id = self.card["content_id"]
        self.review.approve(self.content_id)
        PublishQueueService(self.pipeline.db).authorize_live_publish(self.content_id)
        self.creator_slug = self.pipeline.db.one(
            """
            SELECT cr.slug FROM content_items c
            JOIN creators cr ON cr.id=c.creator_id WHERE c.id=?
            """,
            (self.content_id,),
        )["slug"]
        self.ig_user_id = "17841400000000001"
        self.expected_username = self.pipeline.db.one(
            """
            SELECT pa.public_handle
            FROM content_items c
            JOIN platform_accounts pa
              ON pa.creator_id=c.creator_id AND pa.platform='instagram'
            WHERE c.id=?
            """,
            (self.content_id,),
        )["public_handle"]
        self.publication_id = self.pipeline.db.one(
            "SELECT id FROM publications WHERE content_id=?", (self.content_id,)
        )["id"]
        self.asset_ids = [
            row["asset_id"]
            for row in self.pipeline.db.all(
                """
                SELECT a.asset_id FROM assets a
                LEFT JOIN asset_usage_plan plan
                  ON plan.asset_id=a.id AND plan.content_id=a.content_id
                WHERE a.content_id=? AND a.is_top_pick=1
                ORDER BY COALESCE(plan.priority, 9999), a.id
                """,
                (self.content_id,),
            )
        ]
        self.manifest = self.root / "meta_media_urls.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "schema": "creator-ops-meta-publish-v1",
                    "content": {
                        str(self.content_id): {
                            "native_ai_disclosure_confirmed": True,
                            "asset_urls": {
                                asset_id: f"https://cdn.example.test/{index}.jpg"
                                for index, asset_id in enumerate(self.asset_ids, start=1)
                            },
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _adapter(
        self,
        transport: ReadOnlyMetaTransport,
        probe: FakePublicAssetProbe,
    ) -> MetaInstagramPublishingAdapter:
        return MetaInstagramPublishingAdapter(
            self.pipeline.db,
            account_credentials={
                self.creator_slug: (self.ig_user_id, "TOP-SECRET-TEST-TOKEN")
            },
            graph_version="v99.0",
            manifest_path=self.manifest,
            receipt_directory=self.root / "receipts",
            transport=transport,
            asset_probe=probe,
        )

    def test_ready_preflight_is_read_only_exact_and_secret_free(self) -> None:
        transport = ReadOnlyMetaTransport(
            self.ig_user_id, username=self.expected_username.upper()
        )
        probe = FakePublicAssetProbe()
        adapter = self._adapter(transport, probe)
        event_count = self.pipeline.db.one("SELECT COUNT(*) AS n FROM review_events")["n"]

        result = adapter.preflight(self.publication_id, self.content_id)

        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["checks"]["package"]["asset_ids"], self.asset_ids)
        self.assertEqual(result["checks"]["package"]["media_count"], 3)
        self.assertTrue(result["checks"]["public_assets"]["ok"])
        self.assertEqual(result["checks"]["account"]["id"], self.ig_user_id)
        self.assertEqual(
            result["checks"]["account"]["expected_username"],
            self.expected_username,
        )
        self.assertTrue(result["checks"]["account"]["username_matches"])
        self.assertEqual(
            result["checks"]["content_publishing_limit"]["quota_usage"], 4
        )
        self.assertEqual(
            transport.gets,
            [
                (self.ig_user_id, {"fields": "id,username,account_type"}),
                (
                    f"{self.ig_user_id}/content_publishing_limit",
                    {"fields": "quota_usage,config"},
                ),
            ],
        )
        self.assertNotIn("TOP-SECRET-TEST-TOKEN", json.dumps(result))
        self.assertFalse((self.root / "receipts").exists())
        self.assertEqual(
            self.pipeline.db.one("SELECT COUNT(*) AS n FROM review_events")["n"],
            event_count,
        )

    def test_bad_public_jpeg_blocks_even_when_graph_identity_is_valid(self) -> None:
        transport = ReadOnlyMetaTransport(
            self.ig_user_id, username=self.expected_username
        )
        result = self._adapter(
            transport, FakePublicAssetProbe(failing_index=2)
        ).preflight(self.publication_id, self.content_id)

        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["checks"]["public_assets"]["ok"])
        self.assertIn(
            f"{self.asset_ids[1]}:public_asset_content_type_not_jpeg",
            result["errors"],
        )
        self.assertTrue(result["checks"]["account"]["ok"])

    def test_account_mismatch_and_exhausted_quota_block(self) -> None:
        transport = ReadOnlyMetaTransport(
            self.ig_user_id,
            returned_id="17841499999999999",
            username=self.expected_username,
            quota_usage=100,
            quota_total=100,
        )
        result = self._adapter(transport, FakePublicAssetProbe()).preflight(
            self.publication_id, self.content_id
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("meta_account_id_mismatch", result["errors"])
        self.assertIn("meta_content_publishing_quota_exhausted", result["errors"])

    def test_missing_live_gate_still_completes_every_read_only_check(self) -> None:
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                """
                DELETE FROM review_events
                WHERE content_id=? AND action='OWNER_LIVE_PUBLISH_APPROVED_UI'
                """,
                (self.content_id,),
            )
        transport = ReadOnlyMetaTransport(
            self.ig_user_id, username=self.expected_username
        )
        probe = FakePublicAssetProbe()

        result = self._adapter(transport, probe).preflight(
            self.publication_id, self.content_id
        )

        self.assertEqual(result["status"], "READY_FOR_OWNER_CONFIRMATION")
        self.assertFalse(result["checks"]["live_authorization"]["authorized"])
        self.assertTrue(result["checks"]["package"]["ok"])
        self.assertTrue(result["checks"]["public_assets"]["ok"])
        self.assertTrue(result["checks"]["account"]["ok"])
        self.assertTrue(result["checks"]["content_publishing_limit"]["ok"])
        self.assertEqual(len(probe.urls), 3)
        self.assertEqual(len(transport.gets), 2)

    def test_meta_username_must_match_expected_platform_account(self) -> None:
        transport = ReadOnlyMetaTransport(
            self.ig_user_id, username="wrong.creator"
        )

        result = self._adapter(transport, FakePublicAssetProbe()).preflight(
            self.publication_id, self.content_id
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["checks"]["account"]["username_matches"])
        self.assertEqual(
            result["checks"]["account"]["expected_username"],
            self.expected_username,
        )
        self.assertIn("meta_account_username_mismatch", result["errors"])

    def test_default_url_probe_uses_anonymous_get_and_checks_jpeg_magic(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(request: object, *, timeout: float) -> FakeUrlResponse:
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeUrlResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = UrllibPublicAssetProbe(timeout=7).probe(
                "https://origin.example.test/image.jpg"
            )

        request = captured["request"]
        self.assertTrue(result.ok)
        self.assertEqual(result.final_host, "media.example.test")
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertIsNone(request.get_header("Cookie"))

    def test_default_url_probe_rejects_non_public_url_without_network(self) -> None:
        with patch("urllib.request.urlopen") as urlopen:
            result = UrllibPublicAssetProbe().probe("https://127.0.0.1/image.jpg")

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "public_asset_https_host_required")
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
