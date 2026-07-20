"""Check tool mappings, contexts, and side-effect classification."""

import pytest

from apps.authorization.actions import (
    ACCOUNT_PASSWORD_RESET,
    FILE_CONTEXT,
    FILE_DELETE,
    FILE_LIST,
    FILE_READ,
    FILE_SEARCH,
    PROFILE_CONTEXT,
    TOOL_DELETE_FILE,
    TOOL_LIST_FILES,
    TOOL_READ_FILE,
    TOOL_SEARCH_FILES,
    TOOL_SEND_PASSWORD_RESET_EMAIL,
    action_for_tool,
    is_side_effect_action,
    tool_is_allowed_in_context,
)


# Tool mappings
@pytest.mark.parametrize(
    ("tool_name", "expected_action"),
    [
        (TOOL_LIST_FILES, FILE_LIST),
        (TOOL_SEARCH_FILES, FILE_SEARCH),
        (TOOL_READ_FILE, FILE_READ),
        (TOOL_DELETE_FILE, FILE_DELETE),
        (TOOL_SEND_PASSWORD_RESET_EMAIL, ACCOUNT_PASSWORD_RESET),
    ],
)
def test_tool_maps_to_business_action(tool_name, expected_action):
    """Check that every known tool maps to its business action."""

    assert action_for_tool(tool_name) == expected_action


# Tool contexts
@pytest.mark.parametrize(
    ("tool_name", "allowed_context", "blocked_context"),
    [
        (TOOL_LIST_FILES, FILE_CONTEXT, PROFILE_CONTEXT),
        (TOOL_SEARCH_FILES, FILE_CONTEXT, PROFILE_CONTEXT),
        (TOOL_READ_FILE, FILE_CONTEXT, PROFILE_CONTEXT),
        (TOOL_DELETE_FILE, FILE_CONTEXT, PROFILE_CONTEXT),
        (TOOL_SEND_PASSWORD_RESET_EMAIL, PROFILE_CONTEXT, FILE_CONTEXT),
    ],
)
def test_tool_is_only_allowed_in_its_context(tool_name,allowed_context,blocked_context):
    """Check that tools cannot be exposed in the wrong context."""

    assert tool_is_allowed_in_context(tool_name, allowed_context) is True
    assert tool_is_allowed_in_context(tool_name, blocked_context) is False


# Side-effect actions
@pytest.mark.parametrize(
    "action",
    [
        FILE_DELETE,
        ACCOUNT_PASSWORD_RESET,
    ],
)
def test_state_changing_actions_are_side_effects(action):
    """Check that state-changing actions require confirmation."""

    assert is_side_effect_action(action) is True


# Non-side-effect actions
@pytest.mark.parametrize(
    "action",
    [
        FILE_LIST,
        FILE_SEARCH,
        FILE_READ,
    ],
)
def test_read_only_actions_are_not_side_effects(action):
    """Check that read-only actions do not require confirmation."""

    assert is_side_effect_action(action) is False


def test_unknown_tool_is_rejected():
    """Check that unknown tools have no mapping or allowed context."""

    assert action_for_tool("unknown_tool") is None
    assert tool_is_allowed_in_context("unknown_tool", FILE_CONTEXT) is False