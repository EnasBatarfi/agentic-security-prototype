"""Check policy-based tool exposure before tools are given to the LLM."""

from types import SimpleNamespace

from apps.agents import tooling
from apps.agents.tooling import can_expose_tool, get_tools_for_context, principal_from_user
from apps.authorization.actions import FILE_CONTEXT, PROFILE_CONTEXT
from apps.authorization.types import Principal


def user(user_id=1, email="user@example.com"):
    """Create an authenticated Django-like user for tool-exposure tests."""

    return SimpleNamespace(
        pk=user_id,
        is_authenticated=True,
        email=email,
    )


def tool_names(tools):
    """Return the names of a collection of LangChain tools."""

    return {tool.name for tool in tools}


def test_file_context_exposes_only_file_tools():
    """Check that file context exposes only file-management tools."""

    names = tool_names(get_tools_for_context(user(), FILE_CONTEXT))

    assert names == {
        "list_files",
        "search_files",
        "read_file",
        "delete_file",
    }


def test_profile_context_exposes_only_profile_tools():
    """Check that profile context exposes only the profile tool."""

    names = tool_names(get_tools_for_context(user(), PROFILE_CONTEXT))

    assert names == {
        "send_password_reset_email",
    }


def test_unknown_context_exposes_no_tools():
    """Check that default deny hides every tool in an unknown context."""

    names = tool_names(get_tools_for_context(user(), "unknown"))

    assert names == set()


def test_unauthenticated_user_gets_no_tools():
    """Check that an unauthenticated user cannot receive any tools."""

    anonymous = SimpleNamespace(
        pk=None,
        is_authenticated=False,
        email=None,
    )

    assert tool_names(get_tools_for_context(anonymous, FILE_CONTEXT)) == set()
    assert tool_names(get_tools_for_context(anonymous, PROFILE_CONTEXT)) == set()


def test_authenticated_user_without_primary_key_gets_no_tools():
    """Check that authentication without a stable user ID fails closed."""

    invalid_user = SimpleNamespace(
        pk=None,
        is_authenticated=True,
        email="user@example.com",
    )

    assert tool_names(get_tools_for_context(invalid_user, FILE_CONTEXT)) == set()
    assert tool_names(get_tools_for_context(invalid_user, PROFILE_CONTEXT)) == set()


def test_principal_is_built_from_authenticated_user():
    """Check that trusted Django user fields are copied into the principal."""

    principal = principal_from_user(user(user_id=7, email="seven@example.com"))

    assert principal == Principal(
        id="7",
        authenticated=True,
        email="seven@example.com",
    )


def test_principal_without_identity_has_no_id_or_email():
    """Check that a user without a primary key has no principal identity."""

    invalid_user = SimpleNamespace(
        pk=None,
        is_authenticated=True,
        email="user@example.com",
    )

    principal = principal_from_user(invalid_user)

    assert principal.id is None
    assert principal.authenticated is True
    assert principal.email is None


def test_unknown_tool_is_not_exposed():
    """Check that the PEP rejects a tool unknown to the policy layer."""

    principal = principal_from_user(user())

    assert can_expose_tool(principal, FILE_CONTEXT, "unknown_tool") is False
    assert can_expose_tool(principal, PROFILE_CONTEXT, "unknown_tool") is False


def test_filter_removes_unknown_tools(monkeypatch):
    """Check that an unknown registered tool is removed from the final list."""

    unknown_tool = SimpleNamespace(name="unknown_tool")
    monkeypatch.setattr(tooling, "get_tools", lambda: [unknown_tool])

    assert get_tools_for_context(user(), FILE_CONTEXT) == []
    assert get_tools_for_context(user(), PROFILE_CONTEXT) == []


def test_tools_are_not_exposed_in_wrong_context():
    """Check that tools are only exposed in their allowed context."""

    principal = principal_from_user(user())

    assert can_expose_tool(principal, FILE_CONTEXT, "send_password_reset_email") is False
    assert can_expose_tool(principal, PROFILE_CONTEXT, "read_file") is False
    assert can_expose_tool(principal, PROFILE_CONTEXT, "delete_file") is False