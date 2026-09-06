from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from creator_ops.cli import build_pipeline, build_publish_queue
from creator_ops.publishing import (
    BLOCKED_EXTERNAL_PUBLISHING,
    PUBLISHED,
    DispatchResult,
    MetaInstagramPublishingAdapter,
    PublishQueueService,
    UnconfiguredInstagramAdapter,
)
from creator_ops.review import ReviewDashboardService


class FakeMetaTransport:
    def __init__(self, *, uncertain_publish: bool = False) -> None:
        self.posts: list[tuple[str, dict[str, str]]] = []
        self.gets: list[tuple[str, dict[str, str]]] = []
        self.uncertain_publish = uncertain_publish
        self.child_count = 0

    def post(self, path: str, data: dict[str, str]) -> dict[str, object]:
        self.posts.append((path, data))
        if path.endswith("/media_publish"):
            if self.uncertain_publish:
                raise TimeoutError("response lost")
            return {"id": "18000000000000123"}
        if data.get("media_type") == "CAROUSEL":
            return {"id": "17900000000000999"}
        self.child_count += 1
        return {"id": f"1790000000000000{self.child_count}"}

    def get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        self.gets.append((path, params))
        if params.get("fields") == "status_code":
            return {"status_code": "FINISHED"}
        return {
            "id": "18000000000000123",
            "permalink": "https://www.instagram.com/p/Confirmed123/",
        }


class InvalidConfirmationAdapter:
    provider = "instagram-invalid-confirmation-test"
    available = True

    def publish(
        self, publication_id: int, content_id: int, idempotency_key: str
    ) -> DispatchResult:
        return DispatchResult(status=PUBLISHED, external_id=None, external_url=None)


class MetaPublishingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pipeline = build_pipeline(self.root / "review.db")
        self.pipeline.initialize()
        self.review = ReviewDashboardService(self.pipeline)
        self.card = self.review.ensure_date(date(2026, 9, 8))[0]
        self.review.approve(self.card["content_id"])
        PublishQueueService(self.pipeline.db).authorize_live_publish(
            self.card["content_id"]
        )
        self.creator_slug = self.pipeline.db.one(
            """
            SELECT cr.slug FROM content_items c
            JOIN creators cr ON cr.id=c.creator_id WHERE c.id=?
            """,
            (self.card["content_id"],),
        )["slug"]
        self.account_ids = {
            "leona-voss": "17841400000000001",
            "mara-field": "17841400000000002",
        }
        self.publication = self.pipeline.db.one(
            "SELECT id, scheduled_at FROM publications WHERE content_id=?",
            (self.card["content_id"],),
        )
        self.asset_ids = [
            row["asset_id"]
            for row in self.pipeline.db.all(
                """
                SELECT a.asset_id
                FROM assets a
                LEFT JOIN asset_usage_plan plan
                  ON plan.asset_id=a.id AND plan.content_id=a.content_id
                WHERE a.content_id=? AND a.is_top_pick=1
                ORDER BY COALESCE(plan.priority, 9999), a.id
                """,
                (self.card["content_id"],),
            )
        ]
        self.manifest_path = self.root / "meta_media_urls.json"
        self.receipts = self.root / "receipts"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_manifest(self, *, omit_last: bool = False) -> None:
        selected = self.asset_ids[:-1] if omit_last else self.asset_ids
        self.manifest_path.write_text(
            json.dumps(
                {
                    "schema": "creator-ops-meta-publish-v1",
                    "content": {
                        str(self.card["content_id"]): {
                            "native_ai_disclosure_confirmed": True,
                            "asset_urls": {
                                asset_id: f"https://cdn.example.test/{index}.jpg"
                                for index, asset_id in enumerate(selected, start=1)
                            },
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

    def _adapter(self, transport: FakeMetaTransport) -> MetaInstagramPublishingAdapter:
        return MetaInstagramPublishingAdapter(
            self.pipeline.db,
            account_credentials={
                slug: (ig_user_id, f"test-token-{slug}")
                for slug, ig_user_id in self.account_ids.items()
            },
            graph_version="v99.0",
            manifest_path=self.manifest_path,
            receipt_directory=self.receipts,
            transport=transport,
            poll_attempts=1,
            poll_delay_seconds=0,
        )

    def test_official_carousel_requires_confirmation_and_receipt_prevents_duplicate(self) -> None:
        self._write_manifest()
        transport = FakeMetaTransport()
        adapter = self._adapter(transport)

        first = adapter.publish(
            self.publication["id"], self.card["content_id"], "a" * 64
        )
        calls_after_first = len(transport.posts)
        second = adapter.publish(
            self.publication["id"], self.card["content_id"], "a" * 64
        )

        self.assertEqual(first.status, PUBLISHED)
        self.assertEqual(second, first)
        self.assertEqual(transport.child_count, 3)
        self.assertEqual(calls_after_first, 5)
        self.assertEqual(len(transport.posts), calls_after_first)
        self.assertTrue(
            all(
                path == f"{self.account_ids[self.creator_slug]}/media"
                for path, payload in transport.posts
                if not path.endswith("/media_publish")
            )
        )
        receipt = json.loads(
            (self.receipts / f"{'a' * 64}.json").read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["status"], "CONFIRMED")
        self.assertEqual(receipt["external_id"], "18000000000000123")
        self.assertEqual(receipt["creator_slug"], self.creator_slug)
        self.assertEqual(receipt["ig_user_id"], self.account_ids[self.creator_slug])
        self.assertEqual(receipt["creation_id"], "17900000000000999")
        parent_payload = next(
            data for _, data in transport.posts if data.get("media_type") == "CAROUSEL"
        )
        self.assertEqual(len(parent_payload["children"].split(",")), 3)
        self.assertIn("#", parent_payload["caption"])
        self.assertEqual(parent_payload["is_ai_generated"], "true")
        child_payloads = [
            data for _, data in transport.posts if data.get("is_carousel_item") == "true"
        ]
        self.assertTrue(all("is_ai_generated" not in data for data in child_payloads))

    def test_missing_public_asset_url_blocks_without_external_call(self) -> None:
        self._write_manifest(omit_last=True)
        transport = FakeMetaTransport()
        result = self._adapter(transport).publish(
            self.publication["id"], self.card["content_id"], "b" * 64
        )
        self.assertEqual(result.status, BLOCKED_EXTERNAL_PUBLISHING)
        self.assertIn("public_https_url_required", result.error)
        self.assertEqual(transport.posts, [])

    def test_uncertain_media_publish_response_blocks_automatic_retry(self) -> None:
        self._write_manifest()
        transport = FakeMetaTransport(uncertain_publish=True)
        result = self._adapter(transport).publish(
            self.publication["id"], self.card["content_id"], "c" * 64
        )
        self.assertEqual(result.status, BLOCKED_EXTERNAL_PUBLISHING)
        self.assertEqual(
            result.error,
            "meta_publish_outcome_unknown_owner_reconcile_required",
        )
        intent = self.receipts / f"{'c' * 64}.json"
        self.assertEqual(
            json.loads(intent.read_text(encoding="utf-8"))["status"],
            "PUBLISH_INTENT",
        )
        calls_after_uncertain_result = len(transport.posts)
        replay = self._adapter(transport).publish(
            self.publication["id"], self.card["content_id"], "c" * 64
        )
        self.assertEqual(replay.status, BLOCKED_EXTERNAL_PUBLISHING)
        self.assertEqual(
            replay.error,
            "meta_publish_intent_exists_owner_reconcile_required",
        )
        self.assertEqual(len(transport.posts), calls_after_uncertain_result)

    def test_confirmed_publish_with_failed_receipt_never_becomes_retryable(self) -> None:
        self._write_manifest()
        transport = FakeMetaTransport()
        adapter = self._adapter(transport)

        with patch.object(
            adapter,
            "_write_receipt",
            side_effect=OSError("disk unavailable"),
        ):
            result = adapter.publish(
                self.publication["id"], self.card["content_id"], "d" * 64
            )

        self.assertEqual(result.status, BLOCKED_EXTERNAL_PUBLISHING)
        self.assertEqual(result.external_id, "18000000000000123")
        self.assertEqual(
            result.error,
            "meta_publish_confirmed_receipt_write_failed_owner_reconcile_required",
        )
        self.assertEqual(
            json.loads(
                (self.receipts / f"{'d' * 64}.json").read_text(encoding="utf-8")
            )["status"],
            "PUBLISH_INTENT",
        )

    def test_failed_intent_checkpoint_blocks_before_media_publish_request(self) -> None:
        self._write_manifest()
        transport = FakeMetaTransport()
        adapter = self._adapter(transport)

        with patch.object(
            adapter,
            "_write_publish_intent",
            side_effect=OSError("disk unavailable"),
        ):
            result = adapter.publish(
                self.publication["id"], self.card["content_id"], "9" * 64
            )

        self.assertEqual(result.status, BLOCKED_EXTERNAL_PUBLISHING)
        self.assertEqual(
            result.error,
            "meta_publish_intent_write_failed_no_publish_attempt",
        )
        self.assertFalse(any(path.endswith("/media_publish") for path, _ in transport.posts))

    def test_persona_without_explicit_account_mapping_is_blocked(self) -> None:
        self._write_manifest()
        transport = FakeMetaTransport()
        other_slug = "mara-field" if self.creator_slug == "leona-voss" else "leona-voss"
        adapter = MetaInstagramPublishingAdapter(
            self.pipeline.db,
            account_credentials={
                other_slug: (self.account_ids[other_slug], "test-token-other")
            },
            graph_version="v99.0",
            manifest_path=self.manifest_path,
            receipt_directory=self.receipts,
            transport=transport,
        )

        result = adapter.publish(
            self.publication["id"], self.card["content_id"], "e" * 64
        )

        self.assertEqual(result.status, BLOCKED_EXTERNAL_PUBLISHING)
        self.assertIn("meta_account_not_configured", result.error)
        self.assertEqual(transport.posts, [])

    def test_local_approval_alone_does_not_authorize_live_publish(self) -> None:
        self._write_manifest()
        with self.pipeline.db.transaction() as connection:
            connection.execute(
                "DELETE FROM review_events WHERE content_id=? AND action='OWNER_LIVE_PUBLISH_APPROVED_UI'",
                (self.card["content_id"],),
            )
        transport = FakeMetaTransport()

        result = self._adapter(transport).publish(
            self.publication["id"], self.card["content_id"], "f" * 64
        )

        self.assertEqual(result.status, BLOCKED_EXTERNAL_PUBLISHING)
        self.assertEqual(
            result.error,
            "per_content_live_publish_owner_authorization_required",
        )
        self.assertEqual(transport.posts, [])

    def test_factory_requires_all_live_gates_before_loading_meta_adapter(self) -> None:
        self._write_manifest()
        config = self.root / "config.toml"
        environment = {
            "META_IG_USER_ID_LEONA_VOSS": "17841400000000001",
            "META_ACCESS_TOKEN_LEONA_VOSS": "test-token-leona",
            "META_IG_USER_ID_MARA_FIELD": "17841400000000002",
            "META_ACCESS_TOKEN_MARA_FIELD": "test-token-mara",
            "META_GRAPH_API_VERSION": "v99.0",
            "CREATOR_OPS_META_MEDIA_MANIFEST": str(self.manifest_path),
            "CREATOR_OPS_PASSWORD": "",
        }
        with patch.dict(os.environ, environment, clear=False):
            config.write_text(
                '[scheduler]\ndispatch_live = true\n[publishing]\nadapter = "meta-graph"\nlive_enabled = false\n',
                encoding="utf-8",
            )
            gated = build_publish_queue(self.pipeline, config)
            self.assertIsInstance(gated.adapter, UnconfiguredInstagramAdapter)

            config.write_text(
                '[scheduler]\ndispatch_live = true\n[publishing]\nadapter = "meta-graph"\nlive_enabled = true\n[capabilities]\nofficial_instagram_publish = false\nlive_external_actions = true\n',
                encoding="utf-8",
            )
            still_gated = build_publish_queue(self.pipeline, config)
            self.assertIsInstance(still_gated.adapter, UnconfiguredInstagramAdapter)

            config.write_text(
                '[scheduler]\ndispatch_live = true\n[publishing]\nadapter = "meta-graph"\nlive_enabled = true\n[capabilities]\nofficial_instagram_publish = true\nlive_external_actions = true\n',
                encoding="utf-8",
            )
            enabled = build_publish_queue(self.pipeline, config)
            self.assertIsInstance(enabled.adapter, UnconfiguredInstagramAdapter)

            os.environ["CREATOR_OPS_PASSWORD"] = "correct horse battery staple"
            enabled = build_publish_queue(self.pipeline, config)
            self.assertIsInstance(enabled.adapter, MetaInstagramPublishingAdapter)

    def test_queue_refuses_published_state_without_external_confirmation(self) -> None:
        service = PublishQueueService(self.pipeline.db, InvalidConfirmationAdapter())
        planned = datetime.fromisoformat(self.publication["scheduled_at"])
        summary = service.dispatch_due(planned + timedelta(minutes=1))
        publication = self.pipeline.db.one(
            "SELECT status, external_id, external_url FROM publications WHERE id=?",
            (self.publication["id"],),
        )
        self.assertEqual(summary["published"], 0)
        self.assertEqual(summary["blocked"], 1)
        self.assertNotEqual(publication["status"], PUBLISHED)
        self.assertIsNone(publication["external_id"])
        self.assertIsNone(publication["external_url"])


if __name__ == "__main__":
    unittest.main()
