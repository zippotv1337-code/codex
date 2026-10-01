from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from creator_ops.instagram_dm_provider import (
    InstagramDMProviderError,
    MetaInstagramDMProvider,
)
from creator_ops.publishing import MetaGraphError


class ScriptedTransport:
    def __init__(
        self, get_results: list[dict[str, object] | Exception],
        *, post_error: Exception | None = None,
    ) -> None:
        self.get_results = list(get_results)
        self.get_calls: list[str] = []
        self.post_calls: list[str] = []
        self.post_error = post_error

    def get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        self.get_calls.append(path)
        result = self.get_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def post(self, path: str, data: dict[str, str]) -> dict[str, object]:
        self.post_calls.append(path)
        if self.post_error is not None:
            raise self.post_error
        raise MetaGraphError("meta_graph_http_429")


def provider(
    transport: ScriptedTransport,
    *, accounts: dict[str, tuple[str, str]] | None = None,
) -> MetaInstagramDMProvider:
    return MetaInstagramDMProvider(
        accounts=accounts or {
            "leona-voss": ("leona-account", "test-leona-token"),
            "mara-field": ("mara-account", "test-mara-token"),
        },
        graph_version="v24.0",
        graph_host="graph.instagram.com",
        transport_factory=lambda persona: transport,
    )


class InstagramDMProviderHardeningTests(unittest.TestCase):
    def test_webhook_same_sender_is_scoped_to_each_target_account(self) -> None:
        adapter = provider(ScriptedTransport([]))
        raw = json.dumps({
            "object": "instagram",
            "entry": [
                {
                    "id": account_id,
                    "messaging": [{
                        "sender": {"id": "same-sender"},
                        "message": {"mid": message_id, "text": "Hallo"},
                    }],
                }
                for account_id, message_id in (
                    ("leona-account", "leona-message"),
                    ("mara-account", "mara-message"),
                )
            ],
        }).encode()

        events = adapter.parse_webhook(raw)

        self.assertEqual([item["kind"] for item in events], ["INBOUND", "INBOUND"])
        self.assertEqual(
            [item["payload"]["target_persona"] for item in events],
            ["leona-voss", "mara-field"],
        )
        self.assertEqual(
            [item["payload"]["conversation_id"] for item in events],
            [
                "webhook-igsid:leona-account:same-sender",
                "webhook-igsid:mara-account:same-sender",
            ],
        )
        self.assertEqual(adapter.account_id_for("mara-field"), "mara-account")

    def test_unknown_or_ambiguous_target_account_fails_closed(self) -> None:
        transport = ScriptedTransport([])
        unknown = provider(transport)
        raw = json.dumps({
            "object": "instagram",
            "entry": [{
                "id": "unknown-account",
                "messaging": [{
                    "sender": {"id": "same-sender"},
                    "message": {"mid": "one", "text": "Hallo"},
                }],
            }],
        }).encode()
        self.assertEqual(
            unknown.parse_webhook(raw),
            [{"kind": "UNSUPPORTED", "reason": "target_account_unmapped"}],
        )

        ambiguous = provider(transport, accounts={
            "leona-voss": ("shared-account", "test-leona-token"),
            "mara-field": ("shared-account", "test-mara-token"),
        })
        state = ambiguous.readiness()["personas"]
        self.assertFalse(state["leona-voss"]["read_ready"])
        self.assertFalse(state["mara-field"]["write_ready"])
        self.assertIsNone(ambiguous.account_id_for("leona-voss"))
        self.assertIsNone(ambiguous._persona_for_account("shared-account"))
        with self.assertRaisesRegex(
            InstagramDMProviderError, "instagram_dm_account_mapping_ambiguous"
        ):
            ambiguous.poll("leona-voss")
        with self.assertRaisesRegex(
            InstagramDMProviderError, "instagram_dm_account_mapping_ambiguous"
        ):
            ambiguous.send_message("mara-field", "recipient", "Hallo")
        self.assertEqual(transport.get_calls, [])
        self.assertEqual(transport.post_calls, [])

    def test_transient_poll_get_uses_bounded_backoff_then_succeeds(self) -> None:
        transport = ScriptedTransport([
            MetaGraphError("meta_graph_http_429"),
            ConnectionError("temporary network error"),
            {"data": []},
        ])
        adapter = provider(transport)

        with patch("creator_ops.instagram_dm_provider.time.sleep") as sleeper:
            self.assertEqual(adapter.poll("mara-field"), [])

        self.assertEqual(transport.get_calls, ["mara-account/conversations"] * 3)
        self.assertEqual([call.args[0] for call in sleeper.call_args_list], [0.25, 0.5])
        self.assertEqual(transport.post_calls, [])

    def test_transient_conversation_detail_get_retries_only_that_get(self) -> None:
        transport = ScriptedTransport([
            {"data": [{"id": "thread-one"}]},
            MetaGraphError("meta_graph_http_503"),
            {"messages": {"data": []}},
        ])

        with patch("creator_ops.instagram_dm_provider.time.sleep") as sleeper:
            self.assertEqual(provider(transport).poll("leona-voss"), [])

        self.assertEqual(
            transport.get_calls,
            ["leona-account/conversations", "thread-one", "thread-one"],
        )
        self.assertEqual([call.args[0] for call in sleeper.call_args_list], [0.25])

    def test_graph_transient_code_retries_even_with_http_400_or_403(self) -> None:
        for http_status, graph_code in ((400, 4), (403, 17), (400, 32), (403, 613)):
            with self.subTest(http_status=http_status, graph_code=graph_code):
                transport = ScriptedTransport([
                    MetaGraphError(
                        f"meta_graph_http_{http_status}",
                        http_status=http_status,
                        graph_code=graph_code,
                    ),
                    {"data": []},
                ])
                with patch("creator_ops.instagram_dm_provider.time.sleep") as sleeper:
                    self.assertEqual(provider(transport).poll("leona-voss"), [])
                self.assertEqual(
                    transport.get_calls, ["leona-account/conversations"] * 2
                )
                sleeper.assert_called_once_with(0.25)

    def test_exhausted_graph_transient_read_keeps_numeric_metadata(self) -> None:
        error = MetaGraphError(
            "meta_graph_http_403", http_status=403, graph_code=613,
            graph_subcode=199, request_id="requestABC123",
        )
        transport = ScriptedTransport([error] * 3)
        with patch("creator_ops.instagram_dm_provider.time.sleep") as sleeper:
            with self.assertRaises(InstagramDMProviderError) as caught:
                provider(transport).poll("mara-field")

        self.assertEqual(str(caught.exception), "meta_graph_http_403")
        self.assertEqual(caught.exception.http_status, 403)
        self.assertEqual(caught.exception.graph_code, 613)
        self.assertEqual(caught.exception.graph_subcode, 199)
        self.assertEqual(caught.exception.request_id, "requestABC123")
        self.assertEqual(transport.get_calls, ["mara-account/conversations"] * 3)
        self.assertEqual([call.args[0] for call in sleeper.call_args_list], [0.25, 0.5])

    def test_permanent_poll_error_is_not_retried(self) -> None:
        transport = ScriptedTransport([MetaGraphError("meta_graph_http_400")])
        with patch("creator_ops.instagram_dm_provider.time.sleep") as sleeper:
            with self.assertRaisesRegex(InstagramDMProviderError, "meta_graph_http_400"):
                provider(transport).poll("leona-voss")

        self.assertEqual(transport.get_calls, ["leona-account/conversations"])
        sleeper.assert_not_called()

    def test_transient_poll_error_stops_after_three_gets(self) -> None:
        transport = ScriptedTransport([
            MetaGraphError("meta_graph_http_503") for _ in range(3)
        ])
        with patch("creator_ops.instagram_dm_provider.time.sleep") as sleeper:
            with self.assertRaisesRegex(InstagramDMProviderError, "meta_graph_http_503"):
                provider(transport).poll("mara-field")

        self.assertEqual(transport.get_calls, ["mara-account/conversations"] * 3)
        self.assertEqual([call.args[0] for call in sleeper.call_args_list], [0.25, 0.5])

    def test_post_rate_limit_remains_single_write_attempt(self) -> None:
        transport = ScriptedTransport([])
        with patch("creator_ops.instagram_dm_provider.time.sleep") as sleeper:
            with self.assertRaisesRegex(InstagramDMProviderError, "meta_graph_http_429"):
                provider(transport).send_message("mara-field", "recipient", "Hallo")

        self.assertEqual(transport.post_calls, ["mara-account/messages"])
        sleeper.assert_not_called()

    def test_send_graph_error_keeps_numeric_metadata_without_retry(self) -> None:
        transport = ScriptedTransport(
            [], post_error=MetaGraphError(
                "meta_graph_http_400", http_status=400, graph_code=4,
                request_id="requestXYZ789",
            ),
        )
        with patch("creator_ops.instagram_dm_provider.time.sleep") as sleeper:
            with self.assertRaises(InstagramDMProviderError) as caught:
                provider(transport).send_message("leona-voss", "owner-test", "Hallo")

        self.assertEqual(str(caught.exception), "meta_graph_http_400")
        self.assertEqual(caught.exception.http_status, 400)
        self.assertEqual(caught.exception.graph_code, 4)
        self.assertEqual(caught.exception.request_id, "requestXYZ789")
        self.assertEqual(transport.post_calls, ["leona-account/messages"])
        sleeper.assert_not_called()


if __name__ == "__main__":
    unittest.main()
