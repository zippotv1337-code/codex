from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from creator_ops.database import CreatorDatabase
from creator_ops.tiktok import (
    TikTokError,
    TikTokOAuthService,
    TikTokPublishingAdapter,
    TikTokPublishService,
)


class FakeTransport:
    def __init__(self) -> None:
        self.forms: list[tuple[str, dict]] = []
        self.json_calls: list[tuple[str, dict]] = []
        self.form_response = {
            "access_token": "access-secret",
            "refresh_token": "refresh-secret",
            "open_id": "open-id-secret",
            "scope": "user.info.basic,video.publish",
            "expires_in": 86400,
            "refresh_expires_in": 31536000,
        }
        self.status = "PUBLISH_COMPLETE"

    def post_form(self, path: str, data: dict[str, str]) -> dict:
        self.forms.append((path, data))
        return dict(self.form_response)

    def post_json(self, path: str, data: dict, *, access_token: str) -> dict:
        assert access_token == "access-secret"
        self.json_calls.append((path, data))
        if path.endswith("creator_info/query/"):
            return {
                "data": {
                    "creator_username": "project-account",
                    "creator_nickname": "Project",
                    "privacy_level_options": ["SELF_ONLY", "PUBLIC_TO_EVERYONE"],
                    "comment_disabled": False,
                    "duet_disabled": True,
                    "stitch_disabled": False,
                    "max_video_post_duration_sec": 180,
                },
                "error": {"code": "ok"},
            }
        if path.endswith("video/init/"):
            return {"data": {"publish_id": "v_pub_123"}, "error": {"code": "ok"}}
        if path.endswith("inbox/video/init/"):
            return {"data": {"publish_id": "v_draft_123"}, "error": {"code": "ok"}}
        if path.endswith("status/fetch/"):
            return {
                "data": {
                    "status": self.status,
                    "publicaly_available_post_id": ["post-1"] if self.status == "PUBLISH_COMPLETE" else [],
                },
                "error": {"code": "ok"},
            }
        raise AssertionError(path)

    def put_binary(self, *args, **kwargs) -> int:
        return 201


class TikTokAdapterTests(TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = CreatorDatabase(self.root / "test.db")
        self.db.initialize()
        self.transport = FakeTransport()

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def secret(name: str, **kwargs) -> str:
        values = {
            "TIKTOK_CLIENT_KEY": "public-client-key",
            "TIKTOK_CLIENT_SECRET": "client-secret",
            "TIKTOK_REDIRECT_URI": "https://ops.example.test/api/tiktok/oauth/callback",
            "TIKTOK_ACCESS_TOKEN": "access-secret",
            "TIKTOK_REFRESH_TOKEN": "refresh-secret-old",
        }
        return values.get(name, "")

    @patch("creator_ops.tiktok.set_secret")
    @patch("creator_ops.tiktok.get_secret")
    def test_oauth_state_scope_and_token_storage_are_fail_closed(
        self, get_secret_mock, set_secret_mock
    ) -> None:
        get_secret_mock.side_effect = self.secret
        service = TikTokOAuthService(self.db, self.root, self.transport)

        start = service.begin(("user.info.basic", "video.publish"))
        query = parse_qs(urlparse(start["authorization_url"]).query)
        state = query["state"][0]
        self.assertNotIn(state, str(self.db.all("SELECT * FROM oauth_states")))
        result = service.complete(
            code="one-time-code",
            state=state,
            granted_scopes="user.info.basic,video.publish",
        )

        self.assertEqual(result["status"], "CONNECTED")
        self.assertNotIn("access-secret", str(result))
        self.assertNotIn("refresh-secret", str(result))
        stored_names = [call.args[0] for call in set_secret_mock.call_args_list]
        self.assertEqual(
            stored_names,
            [
                "TIKTOK_OPEN_ID",
                "TIKTOK_SCOPES",
                "TIKTOK_REFRESH_TOKEN",
                "TIKTOK_ACCESS_TOKEN",
            ],
        )
        row = self.db.one("SELECT consumed_at FROM oauth_states")
        self.assertIsNotNone(row["consumed_at"])
        with self.assertRaises(TikTokError):
            service.complete(
                code="another-code",
                state=state,
                granted_scopes="user.info.basic,video.publish",
            )

    @patch("creator_ops.tiktok.get_secret")
    def test_direct_post_checks_creator_constraints_and_is_idempotent(
        self, get_secret_mock
    ) -> None:
        get_secret_mock.side_effect = self.secret
        adapter = TikTokPublishingAdapter(self.root, self.transport)
        service = TikTokPublishService(self.db, adapter)
        source = adapter.pull_source("https://media.example.test/short.mp4")
        post_info = {
            "title": "Eigener KI-Short #zippoworkz",
            "privacy_level": "SELF_ONLY",
            "disable_comment": False,
            "disable_duet": True,
            "disable_stitch": False,
            "duration_seconds": 22,
            "is_aigc": True,
            "explicit_user_consent": True,
        }

        first = service.initialize_video(
            idempotency_key="short-1-v1",
            account_key="project-account",
            mode="DIRECT_POST",
            source_info=source,
            post_info=post_info,
        )
        second = service.initialize_video(
            idempotency_key="short-1-v1",
            account_key="project-account",
            mode="DIRECT_POST",
            source_info=source,
            post_info=post_info,
        )

        self.assertEqual(first["attempt_count"], 1)
        self.assertTrue(second["reused"])
        self.assertEqual(len([call for call in self.transport.json_calls if call[0].endswith("video/init/")]), 1)
        init_payload = next(data for path, data in self.transport.json_calls if path.endswith("video/init/"))
        self.assertTrue(init_payload["post_info"]["is_aigc"])
        self.assertTrue(init_payload["post_info"]["disable_duet"])
        reconciled = service.reconcile(first["id"])
        self.assertEqual(reconciled["status"], "PUBLISH_COMPLETE")
        self.assertEqual(reconciled["external_post_ids"], ["post-1"])

    @patch("creator_ops.tiktok.get_secret")
    def test_direct_post_refuses_wrong_connected_account(self, get_secret_mock) -> None:
        get_secret_mock.side_effect = self.secret
        adapter = TikTokPublishingAdapter(self.root, self.transport)
        with self.assertRaisesRegex(TikTokError, "tiktok_connected_account_mismatch"):
            adapter.init_direct_video(
                source_info=adapter.pull_source("https://media.example.test/short.mp4"),
                title="Test",
                privacy_level="SELF_ONLY",
                disable_comment=False,
                disable_duet=True,
                disable_stitch=False,
                duration_seconds=22,
                is_aigc=True,
                explicit_user_consent=True,
                expected_username="another-account",
            )

    def test_file_upload_chunk_count_uses_ceiling(self) -> None:
        size = 70 * 1024 * 1024
        source = TikTokPublishingAdapter.file_upload_source(size)
        self.assertEqual(source["chunk_size"], 64 * 1024 * 1024)
        self.assertEqual(source["total_chunk_count"], 2)

    @patch("creator_ops.tiktok.get_secret")
    def test_upload_failure_keeps_publish_id_for_reconciliation(
        self, get_secret_mock
    ) -> None:
        get_secret_mock.side_effect = self.secret

        class UploadFails(FakeTransport):
            def post_json(self, path: str, data: dict, *, access_token: str) -> dict:
                if path.endswith("inbox/video/init/"):
                    return {
                        "data": {
                            "publish_id": "v_upload_123",
                            "upload_url": "https://open-upload.tiktokapis.com/upload/123",
                        },
                        "error": {"code": "ok"},
                    }
                return super().post_json(path, data, access_token=access_token)

            def put_binary(self, *args, **kwargs) -> int:
                raise TikTokError("tiktok_upload_transport_error")

        path = self.root / "short.mp4"
        path.write_bytes(b"video")
        adapter = TikTokPublishingAdapter(self.root, UploadFails())
        service = TikTokPublishService(self.db, adapter)
        source = adapter.file_upload_source(path.stat().st_size)
        kwargs = dict(
            idempotency_key="upload-failure",
            account_key="project-account",
            mode="MEDIA_UPLOAD",
            source_info=source,
            file_path=path,
        )
        with self.assertRaisesRegex(TikTokError, "tiktok_upload_transport_error"):
            service.initialize_video(**kwargs)
        intent = service.initialize_video(**kwargs)
        self.assertEqual(intent["status"], "RECONCILE_REQUIRED")
        self.assertTrue(intent["publish_id_present"])
        self.assertEqual(intent["attempt_count"], 1)

    @patch("creator_ops.tiktok.get_secret")
    def test_direct_post_rejects_constraint_override_and_missing_consent(
        self, get_secret_mock
    ) -> None:
        get_secret_mock.side_effect = self.secret
        adapter = TikTokPublishingAdapter(self.root, self.transport)
        source = adapter.pull_source("https://media.example.test/short.mp4")
        with self.assertRaises(ValueError):
            adapter.init_direct_video(
                source_info=source,
                title="Test",
                privacy_level="PUBLIC_TO_EVERYONE",
                disable_comment=False,
                disable_duet=False,
                disable_stitch=False,
                duration_seconds=22,
                is_aigc=True,
                explicit_user_consent=True,
            )
        with self.assertRaises(TikTokError):
            adapter.init_direct_video(
                source_info=source,
                title="Test",
                privacy_level="SELF_ONLY",
                disable_comment=False,
                disable_duet=True,
                disable_stitch=False,
                duration_seconds=22,
                is_aigc=True,
                explicit_user_consent=False,
            )

    @patch("creator_ops.tiktok.get_secret")
    def test_unknown_init_state_is_not_blindly_retried(self, get_secret_mock) -> None:
        get_secret_mock.side_effect = self.secret

        class Broken(FakeTransport):
            def post_json(self, path: str, data: dict, *, access_token: str) -> dict:
                if path.endswith("creator_info/query/"):
                    return super().post_json(path, data, access_token=access_token)
                raise TikTokError("tiktok_transport_error")

        broken = Broken()
        service = TikTokPublishService(
            self.db, TikTokPublishingAdapter(self.root, broken)
        )
        source = TikTokPublishingAdapter.pull_source(
            "https://media.example.test/short.mp4"
        )
        kwargs = dict(
            idempotency_key="uncertain-write",
            account_key="project-account",
            mode="DIRECT_POST",
            source_info=source,
            post_info={
                "title": "Test",
                "privacy_level": "SELF_ONLY",
                "disable_comment": False,
                "disable_duet": True,
                "disable_stitch": False,
                "duration_seconds": 20,
                "is_aigc": True,
                "explicit_user_consent": True,
            },
        )
        with self.assertRaises(TikTokError):
            service.initialize_video(**kwargs)
        reused = service.initialize_video(**kwargs)
        self.assertEqual(reused["status"], "RECONCILE_REQUIRED")
        self.assertEqual(reused["attempt_count"], 1)
