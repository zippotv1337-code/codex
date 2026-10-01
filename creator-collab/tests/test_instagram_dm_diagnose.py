import json
from unittest.mock import Mock, patch

import pytest

from creator_ops.cli import main
from creator_ops.instagram_dm_provider import InstagramDMProviderError, MetaInstagramDMProvider
from creator_ops.publishing import MetaGraphError


def provider(identity=None, conversations=None):
    transport = Mock()
    transport.get.side_effect = [
        identity if identity is not None else {"user_id": "account-id", "username": "leonavoss.ai"},
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
        "username": "leonavoss.ai", "expected_username": "leonavoss.ai",
        "expected_username_match": True, "conversations_call_ok": True,
        "response_has_data_list": True, "conversation_count": 0, "paging_present": False,
    }
    assert transport.get.call_count == 2
    assert transport.get.call_args_list[0].args == ("me", {"fields": "user_id,username"})
    transport.post.assert_not_called()
    assert "account-id" not in json.dumps(result)


@pytest.mark.parametrize("identity,id_match,user_match", [
    ({"user_id": "wrong", "username": "leonavoss.ai"}, False, True),
    ({"user_id": "account-id", "username": "other.account"}, True, False),
    ({"id": "account-id", "username": "leonavoss.ai"}, False, True),
])
def test_identity_mismatches(identity, id_match, user_match):
    adapter, _ = provider(identity)
    result = adapter.diagnose("leona-voss")
    assert result["account_id_match"] is id_match
    assert result["expected_username_match"] is user_match


@pytest.mark.parametrize("payload", [{}, {"data": None}, {"data": {}}, [], {"data": ["bad"]}])
def test_malformed_conversations_fail_closed(payload):
    adapter, transport = provider(conversations=payload)
    result = adapter.diagnose("leona-voss")
    assert result["conversations_call_ok"] is True
    assert result["conversation_count"] is None
    assert result["conversations_error"] == "meta_graph_invalid_response"
    transport.get.side_effect = [payload]
    with pytest.raises(InstagramDMProviderError, match="response_data_invalid"):
        adapter.poll("leona-voss")


@pytest.mark.parametrize("payload", [{}, {"messages": {}}, {"messages": {"data": None}}])
def test_malformed_message_lists_fail_closed(payload):
    adapter, transport = provider()
    transport.get.side_effect = [{"data": [{"id": "thread"}]}, payload]
    with pytest.raises(InstagramDMProviderError, match="response_data_invalid"):
        adapter.poll("leona-voss")
    transport.get.side_effect = [payload]
    with pytest.raises(InstagramDMProviderError, match="response_data_invalid"):
        adapter.reconcile_message("leona-voss", "thread", "message")


def test_valid_empty_poll_and_message_lists():
    adapter, transport = provider()
    transport.get.side_effect = [{"data": []}]
    assert adapter.poll("leona-voss") == []
    transport.get.side_effect = [{"data": [{"id": "thread"}]}, {"messages": {"data": []}}]
    assert adapter.poll("leona-voss") == []


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
                                         "paging": {"next": "test-secret-value"}})
    result = adapter.diagnose("leona-voss")
    assert result["conversation_count"] == 1
    assert result["paging_present"] is True
    for private in ("private-id", "private-text", "test-secret-value"):
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
