"""Check the authorization policy definitions directly."""

from apps.authorization.actions import (
    ACCOUNT_PASSWORD_RESET,
    FILE_DELETE,
    FILE_LIST,
    FILE_SEARCH,
    PROFILE_CONTEXT,
    RESOURCE_ACCOUNT,
    RESOURCE_FILE_COLLECTION,
    RESOURCE_TOOL,
    TOOL_DELETE_FILE,
    TOOL_EXPOSE,
    TOOL_LIST_FILES,
    TOOL_READ_FILE,
    TOOL_SEARCH_FILES,
    TOOL_SEND_PASSWORD_RESET_EMAIL,
)
from apps.authorization.engine import authorize

from .helpers import authorization_request, principal


# Tool exposure policy tests.


def test_file_tool_can_be_exposed_in_file_context():
    """Check that file context permits exposure of a file tool."""

    request = authorization_request(action=TOOL_EXPOSE, resource_type=RESOURCE_TOOL, resource_id=TOOL_READ_FILE, owner_id=None, tool=TOOL_READ_FILE)

    decision = authorize(request)

    assert decision.allowed is True
    assert decision.code == "allowed"
    assert "expose-file-tools-in-file-context" in decision.policy_ids


def test_file_tool_is_not_exposed_in_profile_context():
    """Check that profile context denies exposure of a file tool."""

    request = authorization_request(action=TOOL_EXPOSE, resource_type=RESOURCE_TOOL, resource_id=TOOL_DELETE_FILE, owner_id=None, context_name=PROFILE_CONTEXT, tool=TOOL_DELETE_FILE)

    decision = authorize(request)

    assert decision.allowed is False
    assert decision.code == "default_deny"


def test_profile_tool_can_be_exposed_in_profile_context():
    """Check that profile context permits exposure of a profile tool."""

    request = authorization_request(action=TOOL_EXPOSE, resource_type=RESOURCE_TOOL, resource_id=TOOL_SEND_PASSWORD_RESET_EMAIL, owner_id=None, context_name=PROFILE_CONTEXT, tool=TOOL_SEND_PASSWORD_RESET_EMAIL)

    decision = authorize(request)

    assert decision.allowed is True
    assert decision.code == "allowed"
    assert "expose-profile-tools-in-profile-context" in decision.policy_ids


def test_profile_tool_is_not_exposed_in_file_context():
    """Check that file context denies exposure of a profile tool."""

    request = authorization_request(action=TOOL_EXPOSE, resource_type=RESOURCE_TOOL, resource_id=TOOL_SEND_PASSWORD_RESET_EMAIL, owner_id=None, tool=TOOL_SEND_PASSWORD_RESET_EMAIL)

    decision = authorize(request)

    assert decision.allowed is False
    assert decision.code == "default_deny"


def test_unknown_tool_is_not_exposed():
    """Check that default deny rejects an unknown tool."""

    request = authorization_request(action=TOOL_EXPOSE, resource_type=RESOURCE_TOOL, resource_id="unknown_tool", owner_id=None, tool="unknown_tool")

    decision = authorize(request)

    assert decision.allowed is False
    assert decision.code == "default_deny"


# File resource policy tests.


def test_owner_may_list_own_files():
    """Check that an owner may list their own file resources."""

    request = authorization_request(action=FILE_LIST, resource_type=RESOURCE_FILE_COLLECTION, resource_id="user-files-1", tool=TOOL_LIST_FILES)

    decision = authorize(request)

    assert decision.allowed is True
    assert "owner-may-list-files" in decision.policy_ids


def test_owner_may_search_own_files():
    """Check that an owner may search their own file resources."""

    request = authorization_request(action=FILE_SEARCH, resource_type=RESOURCE_FILE_COLLECTION, resource_id="user-files-1", tool=TOOL_SEARCH_FILES)

    decision = authorize(request)

    assert decision.allowed is True
    assert "owner-may-search-files" in decision.policy_ids


def test_owner_may_read_own_file():
    """Check that an owner may read their own file."""

    decision = authorize(authorization_request())

    assert decision.allowed is True
    assert decision.code == "allowed"
    assert "owner-may-read-file" in decision.policy_ids


def test_user_cannot_read_another_users_file():
    """Check that ownership policy denies reading another user's file."""

    decision = authorize(authorization_request(resource_id="file-20", owner_id="2"))

    assert decision.allowed is False
    assert decision.code == "default_deny"


def test_owner_may_delete_own_file():
    """Check that an owner may delete their own file."""

    request = authorization_request(action=FILE_DELETE, tool=TOOL_DELETE_FILE)

    decision = authorize(request)

    assert decision.allowed is True
    assert decision.code == "allowed"
    assert "owner-may-delete-file" in decision.policy_ids


def test_user_cannot_delete_another_users_file():
    """Check that ownership policy denies deleting another user's file."""

    request = authorization_request(action=FILE_DELETE, resource_id="file-20", owner_id="2", tool=TOOL_DELETE_FILE)

    decision = authorize(request)

    assert decision.allowed is False
    assert decision.code == "default_deny"


def test_file_action_is_denied_in_profile_context():
    """Check that a file action is denied outside the file context."""

    decision = authorize(authorization_request(context_name=PROFILE_CONTEXT))

    assert decision.allowed is False
    assert decision.code == "default_deny"


def test_mismatched_tool_and_action_are_denied():
    """Check that a tool cannot be authorized under another action."""

    decision = authorize(authorization_request(tool=TOOL_DELETE_FILE))

    assert decision.allowed is False
    assert decision.code == "default_deny"


# Account policy tests.


def test_user_may_request_own_password_reset():
    """Check that a user may request a reset for their own account."""

    request = authorization_request(action=ACCOUNT_PASSWORD_RESET, resource_type=RESOURCE_ACCOUNT, resource_id="1", context_name=PROFILE_CONTEXT, tool=TOOL_SEND_PASSWORD_RESET_EMAIL, actor=principal("1", email="enas@example.com"))

    decision = authorize(request)

    assert decision.allowed is True
    assert decision.code == "allowed"
    assert "owner-may-request-own-password-reset" in decision.policy_ids


def test_user_cannot_request_password_reset_for_another_account():
    """Check that a user cannot request a reset for another account."""

    request = authorization_request(action=ACCOUNT_PASSWORD_RESET, resource_type=RESOURCE_ACCOUNT, resource_id="2", owner_id="2", context_name=PROFILE_CONTEXT, tool=TOOL_SEND_PASSWORD_RESET_EMAIL, actor=principal("1", email="enas@example.com"))

    decision = authorize(request)

    assert decision.allowed is False
    assert decision.code == "default_deny"


# Default-deny policy tests.


def test_unauthenticated_principal_is_denied():
    """Check that policy conditions deny an unauthenticated principal."""

    decision = authorize(authorization_request(actor=principal(None, email=None, authenticated=False)))

    assert decision.allowed is False
    assert decision.code == "default_deny"


def test_unknown_action_is_denied():
    """Check that default deny rejects an unknown business action."""

    decision = authorize(authorization_request(action="file:unknown"))

    assert decision.allowed is False
    assert decision.code == "default_deny"


def test_unknown_resource_type_is_denied():
    """Check that default deny rejects an unknown resource type."""

    decision = authorize(authorization_request(resource_type="unknown"))

    assert decision.allowed is False
    assert decision.code == "default_deny"


def test_unknown_context_is_denied():
    """Check that default deny rejects an unknown context."""

    decision = authorize(authorization_request(context_name="unknown"))

    assert decision.allowed is False
    assert decision.code == "default_deny"
