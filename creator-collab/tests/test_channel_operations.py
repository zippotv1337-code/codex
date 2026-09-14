from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from creator_ops.channel_operations import ChannelOperations
from creator_ops.database import CreatorDatabase
from creator_ops.secret_provider import EnvironmentSecretProvider, SecretValue
from creator_ops.tiktok_api import TikTokAdapter, TikTokError


ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "milo-der-zug:tiktok"
POST = "10000000000000001"
PUBLISHED_AT = datetime(2026, 9, 14, 16, 48, tzinfo=UTC)
SCOPES = "user.info.basic,user.info.profile,user.info.stats,video.list"


class ChannelOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "Workspace" / "codex_ingest" / "creator-collab"
        (self.project / "config").mkdir(parents=True)
        shutil.copyfile(ROOT / "config" / "channels.json", self.project / "config" / "channels.json")
        self.db = CreatorDatabase(self.project / "data" / "review_dashboard.db")
        self.db.initialize()
        self.adapter = Mock()
        self.factory = Mock(return_value=self.adapter)
        self.service = self.make_service({})
        self.adapter.profile.return_value = {
            "open_id": "fixture-open-id", "username": "miloderzug", "display_name": "Milo",
            "follower_count": 7, "following_count": None, "likes_count": 0, "video_count": 1,
        }
        self.adapter.videos.return_value = {"videos": [], "cursor": None, "has_more": False}

    def make_service(self, credentials):
        return ChannelOperations(
            self.db, self.project, provider=EnvironmentSecretProvider(credentials),
            environ={"TIKTOK_MILO_SCOPES": SCOPES}, adapter_factory=self.factory,
        )

    def connected_service(self):
        return self.make_service({"TIKTOK_MILO_ACCESS_TOKEN": "fixture-only-token",
                                  "TIKTOK_MILO_OPEN_ID": "fixture-open-id"})

    def seed_publication(self, **overrides):
        draft = dict(self.service.channels._drafts("milo-der-zug")["milo-intro-001"])
        draft.update(status="PUBLISHED", external_post_id=POST,
                     permalink="https://www.tiktok.com/@miloderzug/photo/" + POST,
                     published_at=PUBLISHED_AT.isoformat(), publish_transport="TIKTOK_NATIVE_WEB",
                     approval_status="OWNER_APPROVED")
        draft.update(overrides)
        self.service.channels._write({"schema_version": "1.0", "drafts": {"milo-intro-001": draft},
                                      "analytics": [], "errors": []})
        return draft

    def test_missing_credentials_never_construct_transport(self):
        for credentials in ({}, {"TIKTOK_MILO_ACCESS_TOKEN": "fixture-only-token"},
                            {"TIKTOK_MILO_OPEN_ID": "fixture-open-id"}):
            with self.subTest(fields=tuple(credentials)):
                service = self.make_service(credentials)
                result = service.sync(ACCOUNT)
                self.assertEqual(result["error"], "NEEDS_AUTH")
                self.assertFalse(result["external_publish"])
        self.factory.assert_not_called()

    def test_other_account_sync_is_not_allowlisted(self):
        with self.assertRaisesRegex(ValueError, "account_not_allowlisted_for_sync"):
            self.service.sync("milo-der-zug:instagram")
        self.factory.assert_not_called()

    def test_account_identity_mismatch_preserves_prior_verified_data(self):
        service = self.connected_service()
        previous = {"profile": {"username": "miloderzug", "follower_count": 5},
                    "external_id": "fixture-open-id", "last_sync_at": "2026-09-13T12:00:00+00:00",
                    "video_sync": {"items": [{"id": "123"}]}, "connection_status": "CONNECTED"}
        for changed in ({"open_id": "someone-else"}, {"username": "someone_else"}):
            with self.subTest(changed=changed):
                service._write("account." + ACCOUNT, previous)
                self.adapter.profile.return_value = {
                    "open_id": "fixture-open-id", "username": "miloderzug", **changed,
                }
                result = service.sync(ACCOUNT)
                self.assertEqual(result["error"], "ACCOUNT_MISMATCH")
                state = service._read("account." + ACCOUNT)
                for key in ("profile", "external_id", "last_sync_at", "video_sync"):
                    self.assertEqual(state[key], previous[key])
                self.assertFalse(state["analytics_enabled"])
        self.adapter.videos.assert_not_called()

    def test_sync_stops_after_three_pages_and_reports_partial(self):
        service = self.connected_service()
        self.adapter.videos.side_effect = [
            {"videos": [{"id": str(index)}], "cursor": index, "has_more": True}
            for index in (1, 2, 3)
        ]
        result = service.sync(ACCOUNT)
        self.assertEqual(result["status"], "SYNCED_PARTIAL")
        self.assertEqual(result["posts_read"], 3)
        self.assertEqual(self.adapter.videos.call_count, 3)
        self.assertEqual([call.args for call in self.adapter.videos.call_args_list], [(None,), (1,), (2,)])
        state = service._read("account." + ACCOUNT)
        self.assertTrue(state["video_sync"]["partial"])
        self.assertEqual(state["video_sync"]["cursor"], 3)
        self.assertIsNone(state["profile"]["following_count"])

    def test_repeated_cursor_stops_pagination(self):
        service = self.connected_service()
        self.adapter.videos.return_value = {"videos": [], "cursor": 88, "has_more": True}
        self.assertEqual(service.sync(ACCOUNT)["status"], "SYNCED_PARTIAL")
        self.assertEqual(self.adapter.videos.call_count, 2)

    def test_known_and_unknown_errors_are_sanitized(self):
        service = self.connected_service()
        for raw, expected in (("TOKEN_EXPIRED", "TOKEN_EXPIRED"),
                              ("upstream secret=fixture-sensitive-detail", "API_REJECTED")):
            with self.subTest(expected=expected):
                self.adapter.profile.side_effect = TikTokError(raw)
                result = service.sync(ACCOUNT)
                self.assertEqual(result["error"], expected)
                self.assertNotIn("fixture-sensitive-detail", json.dumps(service.snapshot()))
                events = self.db.all("SELECT detail_json FROM runtime_events")
                self.assertTrue(all("fixture-sensitive-detail" not in row[0] for row in events))

    def test_video_error_keeps_verified_profile_and_reports_partial(self):
        service = self.connected_service()
        self.adapter.videos.side_effect = TikTokError("RATE_LIMITED")
        result = service.sync(ACCOUNT)
        self.assertEqual(result["status"], "SYNCED_PARTIAL")
        state = service._read("account." + ACCOUNT)
        self.assertEqual(state["connection_status"], "CONNECTED")
        self.assertEqual(state["last_error"], "RATE_LIMITED")
        self.assertEqual(state["profile"]["username"], "miloderzug")

    def test_missing_analytics_remain_null_and_windows_not_due(self):
        self.seed_publication()
        snapshot = self.service.snapshot(PUBLISHED_AT + timedelta(hours=23))
        post = snapshot["publications"][0]
        self.assertEqual([item["status"] for item in post["windows"]], ["WAITING"] * 3)
        self.assertTrue(all(value is None for item in post["windows"] for value in item["metrics"].values()))
        self.assertTrue(all(value is None for value in post["derived"].values()))
        self.assertEqual(post["learning"], "UNKNOWN")
        self.assertFalse(snapshot["automatic_publish"])
        self.assertEqual(self.db.schema_version(), 5)

    def test_capture_rejects_early_empty_invalid_and_unconfirmed(self):
        self.seed_publication()
        cases = [(POST, 24, {"views": 10}, PUBLISHED_AT, "analytics_window_not_due"),
                 (POST, 24, {}, PUBLISHED_AT + timedelta(days=1), "real_metrics_required"),
                 (POST, 24, {"views": True}, PUBLISHED_AT + timedelta(days=1), "invalid_metric"),
                 (POST, 24, {"views": -1}, PUBLISHED_AT + timedelta(days=1), "invalid_metric"),
                 (POST, 48, {"views": 1}, PUBLISHED_AT + timedelta(days=2), "invalid_analytics_window"),
                 ("not-a-post", 24, {"views": 1}, PUBLISHED_AT + timedelta(days=2), "confirmed_publication_required")]
        for post_id, hours, metrics, now, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.service.capture(post_id, hours, metrics, now=now)
        self.assertEqual(self.db.one("SELECT count(*) FROM runtime_events")[0], 0)

    def test_capture_is_append_only_and_derived_rates_use_real_measurement(self):
        self.seed_publication()
        self.service.capture(POST, 24, {"views": 100, "likes": 10}, now=PUBLISHED_AT + timedelta(hours=25))
        self.service.capture(POST, 24, {"views": 120, "likes": 12, "comments": 0},
                             now=PUBLISHED_AT + timedelta(hours=30))
        events = self.db.all("SELECT detail_json FROM runtime_events ORDER BY id")
        self.assertEqual(len(events), 2)
        self.assertEqual(json.loads(events[0][0])["metrics"]["views"], 100)
        post = self.service.publications(PUBLISHED_AT + timedelta(hours=90))[0]
        self.assertEqual([window["status"] for window in post["windows"]], ["CAPTURED", "DUE", "WAITING"])
        self.assertEqual(post["windows"][0]["late_by_hours"], 6)
        self.assertEqual(post["derived"]["likes_per_view"], 0.1)
        self.assertEqual(post["derived"]["comments_per_view"], 0)
        self.assertIsNone(post["derived"]["shares_per_view"])
        self.assertEqual(post["derived"]["views_per_hour"], 4)

    def test_zero_views_do_not_create_ratios(self):
        self.seed_publication()
        now = PUBLISHED_AT + timedelta(hours=24)
        self.service.capture(POST, 24, {"views": 0, "likes": 0}, now=now)
        rates = self.service.publications(now)[0]["derived"]
        self.assertIsNone(rates["likes_per_view"])
        self.assertEqual(rates["views_per_hour"], 0)

    def test_published_and_external_id_drafts_are_read_only(self):
        for overrides in ({}, {"status": "READY_FOR_REVIEW"}, {"external_post_id": None}):
            with self.subTest(overrides=overrides):
                self.seed_publication(**overrides)
                before = self.service.channels.state_path.read_bytes()
                for action in ("approve", "change", "reject"):
                    with self.assertRaisesRegex(ValueError, "published_content_is_read_only"):
                        self.service.channels.decide("milo-der-zug", "milo-intro-001", action)
                for mode in ("DIRECT_POST", "DRAFT_UPLOAD"):
                    with self.assertRaisesRegex(ValueError, "published_content_is_read_only"):
                        self.service.channels.set_upload_mode("milo-der-zug", "milo-intro-001", mode)
                self.assertEqual(before, self.service.channels.state_path.read_bytes())
                draft = self.service.channels.snapshot()["brands"][0]["drafts"][0]
                self.assertTrue(draft["read_only"])
                self.assertFalse(draft["direct_post_ready"])
                self.assertFalse(draft["draft_upload_ready"])


class TikTokAdapterTests(unittest.TestCase):
    def setUp(self):
        self.secret = SecretValue("secret://tiktok/milo-der-zug/access-token", "fixture-only-token")
        self.transport = Mock()
        self.adapter = TikTokAdapter(self.secret, scopes=SCOPES.split(",") + ["video.publish"],
                                     transport=self.transport)

    def test_missing_token_and_scopes_prevent_transport(self):
        adapter = TikTokAdapter(None, scopes=SCOPES.split(","), transport=self.transport)
        with self.assertRaisesRegex(TikTokError, "NEEDS_AUTH"):
            adapter.profile()
        adapter = TikTokAdapter(self.secret, scopes=["user.info.basic"], transport=self.transport)
        with self.assertRaisesRegex(TikTokError, "SCOPE_MISSING"):
            adapter.profile()
        self.transport.assert_not_called()

    def test_upstream_errors_do_not_include_raw_messages(self):
        for code, expected in (("access_token_invalid", "TOKEN_EXPIRED"),
                               ("scope_not_authorized", "SCOPE_MISSING"), ("unknown", "API_REJECTED")):
            with self.subTest(code=code):
                self.transport.return_value = {"error": {"code": code, "message": "fixture-sensitive-detail"}}
                with self.assertRaises(TikTokError) as result:
                    self.adapter.profile()
                self.assertEqual(str(result.exception), expected)

    def test_http_failures_are_sanitized_without_real_http(self):
        adapter = TikTokAdapter(self.secret, scopes=SCOPES.split(","))
        for status, expected in ((401, "TOKEN_EXPIRED"), (403, "SCOPE_MISSING"),
                                 (429, "RATE_LIMITED"), (500, "API_HTTP_ERROR")):
            with self.subTest(status=status), patch("creator_ops.tiktok_api.build_opener") as opener:
                opener.return_value.open.side_effect = HTTPError("https://open.tiktokapis.com", status,
                                                                "fixture-sensitive-detail", {}, None)
                with self.assertRaises(TikTokError) as result:
                    adapter.profile()
                self.assertEqual(str(result.exception), expected)

    def test_status_requires_valid_public_ids_and_complete_state(self):
        for status, ids, expected in (("PUBLISH_COMPLETE", [], False),
                                      ("PUBLISH_COMPLETE", ["invalid-id"], False),
                                      ("PROCESSING_UPLOAD", [POST], False),
                                      ("PUBLISH_COMPLETE", [POST], True)):
            with self.subTest(status=status, ids=ids):
                self.transport.return_value = {"error": {"code": "ok"},
                                               "data": {"status": status, "publicaly_available_post_id": ids}}
                result = self.adapter.status("fixture-publish-id")
                self.assertEqual(result["public_confirmed"], expected)
                if expected:
                    self.assertEqual(result["external_post_ids"], [POST])

    def test_malformed_upstream_envelopes_are_sanitized(self):
        for reply in (None, [], {"error": None}, {"error": []},
                      {"error": {"code": "ok"}, "data": None},
                      {"error": {"code": "ok"}, "data": []}):
            with self.subTest(reply=reply):
                self.transport.return_value = reply
                with self.assertRaises(TikTokError):
                    self.adapter.profile()

    def test_profile_and_video_fields_are_allowlisted(self):
        self.transport.return_value = {"error": {"code": "ok"},
                                       "data": {"user": {"open_id": "fixture-open-id", "username": "miloderzug",
                                                         "private_field": "must-not-persist"}}}
        self.assertNotIn("private_field", self.adapter.profile())
        self.transport.return_value = {"error": {"code": "ok"},
                                       "data": {"videos": [{"id": POST, "view_count": 0,
                                                            "private_field": "must-not-persist"}],
                                                "has_more": False, "cursor": 42}}
        result = self.adapter.videos()
        self.assertEqual(result["videos"][0]["view_count"], 0)
        self.assertIsNone(result["videos"][0]["like_count"])
        self.assertNotIn("private_field", result["videos"][0])
        self.assertEqual(self.transport.call_args.args[2], {"max_count": 20})


if __name__ == "__main__":
    unittest.main()
