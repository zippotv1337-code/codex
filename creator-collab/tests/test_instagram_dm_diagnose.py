import json
from unittest.mock import Mock, patch

import pytest

from creator_ops.cli import main
from creator_ops.instagram_dm_provider import (
    InstagramDMProviderConnectionError,
    InstagramDMProviderError,
    MetaInstagramDMProvider,
)
from creator_ops.publishing import MetaGraphError

# Answer to the identity GET that poll() needs once per provider instance.
BOUND = {"user_id": "account-id", "username": "leonavoss.ai"}


def provider(identity=None, conversations=None):
    transport = Mock()
    transport.get.side_effect = [
        identity if identity is not None else {
            "id": "different-app-scoped-id", "user_id": "account-id", "username": "leonavoss.ai"
        },
        conversations if conversations is not None else {"data": []},
    ]
    adapter = MetaInstagramDMProvider(
        accounts={"leona-voss": ("account-id", "test-secret-value")},
        graph_version="v24.0", graph_host="graph.instagram.com",
        transport_factory=lambda persona: transport,
    )
    return adapter, transport


def test_identity_and_empty_page_are_only_read_facts():
    adapter, transport = provider()
    result = adapter.diagnose("leona-voss")
    assert result == {
        "persona": "leona-voss", "credentials_present": True,
        "identity_call_ok": True, "account_id_match": True,
        "configured_id_kind": "ig_professional_account_id",
        "username": "leonavoss.ai", "expected_username": "leonavoss.ai",
        "expected_username_match": True, "conversations_call_ok": True,
        "response_has_data_list": True, "conversation_count": 0, "paging_present": False,
    }
    assert transport.get.call_count == 2
    assert transport.get.call_args_list[0].args == ("me", {"fields": "id,user_id,username"})
    assert transport.get.call_args_list[1].args == (
        "account-id/conversations",
        {"platform": "instagram", "fields": "id,updated_time,participants", "limit": "25"},
    )
    transport.post.assert_not_called()
    assert "account-id" not in json.dumps(result)
    assert "different-app-scoped-id" not in json.dumps(result)


# Meta: `user_id` is the IG professional account ID (IG_ID); `id` is app-scoped.
@pytest.mark.parametrize("identity,id_match,kind,user_match", [
    ({"id": "other-id", "user_id": "account-id", "username": "leonavoss.ai"},
     True, "ig_professional_account_id", True),
    ({"user_id": "account-id", "username": "leonavoss.ai"},
     True, "ig_professional_account_id", True),
    ({"id": "account-id", "user_id": "different-user-id", "username": "leonavoss.ai"},
     False, "app_scoped_id", True),
    ({"id": "account-id", "username": "leonavoss.ai"}, False, "app_scoped_id", True),
    ({"id": "", "user_id": "", "username": "leonavoss.ai"}, False, "unknown", True),
    ({"id": "x", "user_id": "y", "username": "leonavoss.ai"}, False, "unknown", True),
    ({"user_id": "account-id", "username": "other.account"},
     True, "ig_professional_account_id", False),
])
def test_identity_mismatches(identity, id_match, kind, user_match):
    adapter, _ = provider(identity)
    result = adapter.diagnose("leona-voss")
    assert result["account_id_match"] is id_match
    assert result["configured_id_kind"] == kind
    assert result["expected_username_match"] is user_match


def test_two_read_only_gets_per_configured_persona():
    accounts = {
        "leona-voss": ("leona-id", "leona-test-secret"),
        "mara-field": ("mara-id", "mara-test-secret"),
    }
    handles = {"leona-voss": "leonavoss.ai", "mara-field": "mara.field.ai"}
    transports = {}
    for persona, (account_id, _) in accounts.items():
        transport = Mock()
        transport.get.side_effect = [
            {"id": f"other-{persona}", "user_id": account_id, "username": handles[persona]},
            {"data": []},
        ]
        transports[persona] = transport
    adapter = MetaInstagramDMProvider(
        accounts=accounts,
        graph_version="v24.0", graph_host="graph.instagram.com",
        transport_factory=lambda persona: transports[persona],
    )
    for persona, (account_id, _) in accounts.items():
        result = adapter.diagnose(persona)
        assert result["account_id_match"] is True
        assert result["expected_username_match"] is True
        transport = transports[persona]
        assert transport.get.call_count == 2
        assert transport.get.call_args_list[0].args == ("me", {"fields": "id,user_id,username"})
        assert transport.get.call_args_list[1].args == (
            f"{account_id}/conversations",
            {"platform": "instagram", "fields": "id,updated_time,participants", "limit": "25"},
        )
        transport.post.assert_not_called()
        serialized = json.dumps(result)
        assert account_id not in serialized
        assert f"other-{persona}" not in serialized


@pytest.mark.parametrize("payload", [{}, {"data": None}, {"data": {}}, [], {"data": ["bad"]}])
def test_malformed_conversations_fail_closed(payload):
    adapter, transport = provider(conversations=payload)
    result = adapter.diagnose("leona-voss")
    assert result["conversations_call_ok"] is True
    assert result["conversation_count"] is None
    assert result["conversations_error"] == "meta_graph_invalid_response"
    transport.get.side_effect = [BOUND, payload]
    with pytest.raises(InstagramDMProviderError, match="response_data_invalid"):
        adapter.poll("leona-voss")


@pytest.mark.parametrize("payload", [
    None, [], {"messages": None}, {"messages": {}},
    {"messages": {"data": None}}, {"messages": {"data": {}}},
    {"messages": {"data": ["bad"]}},
])
def test_malformed_message_lists_fail_closed(payload):
    adapter, transport = provider()
    transport.get.side_effect = [BOUND, {"data": [{"id": "thread"}]}, payload]
    with pytest.raises(InstagramDMProviderError, match="response_data_invalid"):
        adapter.poll("leona-voss")
    transport.get.side_effect = [payload]
    with pytest.raises(InstagramDMProviderError, match="response_data_invalid"):
        adapter.reconcile_message("leona-voss", "thread", "message")


def test_absent_messages_skips_thread_but_reconciliation_stays_strict():
    adapter, transport = provider()
    transport.get.side_effect = [
        BOUND,
        {"data": [{"id": "empty-thread"}, {"id": "next-thread"}]},
        {},
        {"messages": {"data": [{
            "id": "inbound", "from": {"id": "sender"}, "message": "hello",
            "created_time": "2026-10-01T10:00:00+00:00",
        }]}},
    ]
    assert [item["message_id"] for item in adapter.poll("leona-voss")] == ["inbound"]
    transport.get.side_effect = [{}]
    with pytest.raises(InstagramDMProviderError, match="response_data_invalid"):
        adapter.reconcile_message("leona-voss", "empty-thread", "message")


def test_valid_empty_poll_and_message_lists():
    adapter, transport = provider()
    transport.get.side_effect = [BOUND, {"data": []}]
    assert adapter.poll("leona-voss") == []
    # The identity is bound once per instance; the second poll skips it.
    transport.get.side_effect = [{"data": [{"id": "thread"}]}, {"messages": {"data": []}}]
    assert adapter.poll("leona-voss") == []
    assert [call.args[0] for call in transport.get.call_args_list] == [
        "me", "account-id/conversations", "account-id/conversations", "thread",
    ]


def test_poll_fails_closed_when_configured_id_is_app_scoped():
    adapter, transport = provider()
    transport.get.side_effect = [
        {"user_id": "real-ig-id", "username": "leonavoss.ai"}, {"data": []},
    ]
    with pytest.raises(InstagramDMProviderError, match="^instagram_dm_account_id_not_ig_id$"):
        adapter.poll("leona-voss")
    assert transport.get.call_count == 1
    assert transport.get.call_args.args == ("me", {"fields": "user_id,username"})
    transport.post.assert_not_called()


@pytest.mark.parametrize("identity,error", [
    ({"user_id": "account-id", "username": "mara.field.ai"}, "instagram_dm_account_username_mismatch"),
    ({"username": "leonavoss.ai"}, "instagram_dm_account_id_not_ig_id"),
    (["not", "a", "dict"], "instagram_dm_identity_invalid"),
])
def test_poll_identity_mismatch_never_reads_conversations(identity, error):
    adapter, transport = provider()
    transport.get.side_effect = [identity, {"data": []}]
    with pytest.raises(InstagramDMProviderError, match=f"^{error}$"):
        adapter.poll("leona-voss")
    assert transport.get.call_count == 1
    transport.post.assert_not_called()


def test_identity_errors_are_sanitized_and_not_cached():
    adapter, transport = provider()
    transport.get.side_effect = [ConnectionError("test-secret-value RAW BODY")]
    with pytest.raises(InstagramDMProviderConnectionError, match="^meta_graph_unreachable$"):
        adapter.poll("leona-voss")
    transport.get.side_effect = [MetaGraphError("meta_graph_error_code_test-secret-value RAW BODY")]
    with pytest.raises(InstagramDMProviderError, match="^meta_graph_error$"):
        adapter.poll("leona-voss")
    # A failed check is retried on the next poll instead of being remembered.
    transport.get.side_effect = [BOUND, {"data": []}]
    assert adapter.poll("leona-voss") == []
    transport.post.assert_not_called()


@pytest.mark.parametrize("error,expected", [
    (MetaGraphError("meta_graph_http_403"), "meta_graph_http_403"),
    (MetaGraphError("meta_graph_error_code_123"), "meta_graph_error_code_123"),
    (MetaGraphError("meta_graph_error_code_test-secret-value RAW BODY"), "meta_graph_error"),
    (ConnectionError("test-secret-value RAW BODY"), "meta_graph_unreachable"),
    (ValueError("test-secret-value RAW BODY"), "meta_graph_invalid_response"),
])
def test_errors_are_sanitized(error, expected):
    adapter, transport = provider()
    transport.get.side_effect = [error, error]
    result = adapter.diagnose("leona-voss")
    assert result["identity_error"] == expected
    assert result["conversations_error"] == expected
    assert result["identity_call_ok"] is False
    assert result["conversations_call_ok"] is False
    assert "test-secret-value" not in json.dumps(result)
    assert "RAW BODY" not in json.dumps(result)
    transport.post.assert_not_called()


def test_nonempty_page_does_not_expose_ids_text_or_paging_values():
    adapter, _ = provider(conversations={"data": [{"id": "private-id", "message": "private-text"}],
                                         "paging": {"next": "https://private.example/next?token=test-secret-value"}})
    result = adapter.diagnose("leona-voss")
    assert result["conversation_count"] == 1
    assert result["paging_present"] is True
    for private in ("account-id", "different-app-scoped-id", "private-id", "private-text",
                    "test-secret-value", "https://private.example/next"):
        assert private not in json.dumps(result)


def test_readiness_remains_compatible_and_missing_credentials_make_no_calls():
    adapter, transport = provider()
    readiness = adapter.readiness()["personas"]
    for persona, present in (("leona-voss", True), ("mara-field", False)):
        for key in ("configured", "read_ready", "write_ready", "credentials_present"):
            assert readiness[persona][key] is present
        assert readiness[persona]["read_ready_basis"] == "credentials_present_only"
        assert readiness[persona]["write_ready_basis"] == "credentials_present_only"
    assert adapter.diagnose("mara-field")["credentials_present"] is False
    transport.get.assert_not_called()


@pytest.mark.parametrize("args,personas", [([], ["leona-voss", "mara-field"]),
                                         (["--persona", "mara-field"], ["mara-field"])])
def test_cli_never_initializes_db_or_syncs(args, personas, capsys):
    adapter = Mock()
    adapter.diagnose.side_effect = lambda persona: {"persona": persona}
    with patch("sys.argv", ["creator-ops", "instagram-dm-diagnose", *args]), \
         patch("creator_ops.cli.MetaInstagramDMProvider.from_runtime", return_value=adapter), \
         patch("creator_ops.cli.build_pipeline") as pipeline, \
         patch("creator_ops.cli.InstagramDMService") as service:
        assert main() == 0
    assert json.loads(capsys.readouterr().out) == [{"persona": p} for p in personas]
    pipeline.assert_not_called()
    service.assert_not_called()
