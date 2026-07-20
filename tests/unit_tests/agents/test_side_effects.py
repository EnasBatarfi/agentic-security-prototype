"""Check confirmation handling for state-changing agent tools."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.agents import side_effects
from apps.agents.enforcement import ToolCallAuthorization
from apps.authorization.actions import FILE_CONTEXT, PROFILE_CONTEXT, TOOL_DELETE_FILE
from apps.authorization.actions import TOOL_READ_FILE, TOOL_SEND_PASSWORD_RESET_EMAIL


def test_read_only_tool_does_not_require_confirmation(alice):
    """Check that read-only actions are not stored as pending actions."""

    session = {}

    message = side_effects.request_confirmation_if_needed(
        alice,
        FILE_CONTEXT,
        session,
        TOOL_READ_FILE,
        {"path": f"users/{alice.pk}/note.txt"},
    )

    assert message is None
    assert side_effects.PENDING_SIDE_EFFECT_KEY not in session


# Parametrize the test to check multiple contexts and tools that require confirmation
@pytest.mark.parametrize(
    ("context", "tool_name", "message_text"),
    [
        (FILE_CONTEXT, TOOL_DELETE_FILE, "Deleting"),
        (PROFILE_CONTEXT, TOOL_SEND_PASSWORD_RESET_EMAIL, "password-reset"),
    ],
)
def test_side_effect_is_stored_with_trusted_arguments(alice, context, tool_name, message_text):
    """Check that an allowed side effect is stored before execution."""

    session = {}

    if tool_name == TOOL_DELETE_FILE:
        safe_args = {"path": f"users/{alice.pk}/note.txt"}
    else:
        safe_args = {"email": alice.email}

    message = side_effects.request_confirmation_if_needed(
        alice,
        context,
        session,
        tool_name,
        safe_args,
    )

    assert message is not None
    assert message_text in message
    assert session[side_effects.PENDING_SIDE_EFFECT_KEY] == {
        "user_id": str(alice.pk),
        "context": context,
        "tool_name": tool_name,
        "safe_args": safe_args,
    }


def test_wrong_confirmation_command_does_not_execute_or_clear(alice):
    """Check that vague confirmation text cannot approve an action."""

    session = {}

    side_effects.request_confirmation_if_needed(
        alice,
        FILE_CONTEXT,
        session,
        TOOL_DELETE_FILE,
        {"path": f"users/{alice.pk}/note.txt"},
    )

    message = side_effects.handle_confirmation_message(
        alice,
        FILE_CONTEXT,
        session,
        "okay confirm",
    )

    assert message == (
        "Wrong command. Reply CONFIRM to continue or CANCEL to stop."
    )
    assert side_effects.PENDING_SIDE_EFFECT_KEY in session


def test_cancel_clears_pending_action(alice):
    """Check that CANCEL removes a pending action without execution."""

    session = {}

    side_effects.request_confirmation_if_needed(
        alice,
        FILE_CONTEXT,
        session,
        TOOL_DELETE_FILE,
        {"path": f"users/{alice.pk}/note.txt"},
    )

    message = side_effects.handle_confirmation_message(
        alice,
        FILE_CONTEXT,
        session,
        "        cancel ",
    )

    assert message == "The pending action was cancelled."
    assert side_effects.PENDING_SIDE_EFFECT_KEY not in session


def test_confirm_reauthorizes_and_executes_once(alice, monkeypatch):
    """Check that CONFIRM applies both PEPs and executes only once."""

    session = {}
    safe_args = {"path": f"users/{alice.pk}/note.txt"}

    side_effects.request_confirmation_if_needed(
        alice,
        FILE_CONTEXT,
        session,
        TOOL_DELETE_FILE,
        safe_args,
    )

    # We are using mocks to simulate the behavior of the tool invocation and authorization process 
    # Bc we wanna test the side effect handling logic without actually performing the file deletion or authorization checks 
    # so we can isolate the logic and any potential bugs in the side effect handling code itself

    # First, we create a mock for the tool invocation that returns a specific message when called
    invoke_mock = Mock(return_value="Deleted")

    # Then we create a SimpleNamespace to represent the selected tool, which includes the name of the tool and the mock invocation function
    selected_tool = SimpleNamespace(
        name=TOOL_DELETE_FILE,
        invoke=invoke_mock,
    )

    # Next, we create a mock for the first PEP (tool exposure)that returns a list containing the selected tool when called
    pep1_mock = Mock(return_value=[selected_tool])

    # Finally, we create a mock for the second PEP (enforcement) that returns a ToolCallAuthorization object
    pep2_mock = Mock(
        return_value=ToolCallAuthorization(
            allowed=True,
            safe_args=safe_args,
            message="Allowed.",
        )
    )

    monkeypatch.setattr(
        side_effects.tooling,
        "get_tools_for_context",
        pep1_mock,
    )
    monkeypatch.setattr(
        side_effects.enforcement,
        "authorize_tool_invocation",
        pep2_mock,
    )

    message = side_effects.handle_confirmation_message(
        alice,
        FILE_CONTEXT,
        session,
        "CONFIRM",
    )

    assert message == "Deleted"

    pep1_mock.assert_called_once_with(
        alice,
        FILE_CONTEXT,
    )

    pep2_mock.assert_called_once_with(
        alice,
        FILE_CONTEXT,
        TOOL_DELETE_FILE,
        safe_args,
    )

    invoke_mock.assert_called_once_with(safe_args)

    assert side_effects.PENDING_SIDE_EFFECT_KEY not in session

    second_message = side_effects.handle_confirmation_message(
        alice,
        FILE_CONTEXT,
        session,
        "CONFIRM",
    )

    assert second_message == "There is no pending action to confirm."
    # Check that the mocks were called only once, ensuring no double execution
    assert pep1_mock.call_count == 1
    assert pep2_mock.call_count == 1
    assert invoke_mock.call_count == 1


def test_confirmation_stops_when_reauthorization_is_denied(
    alice,
    monkeypatch,
):
    """Check that a previously pending action can still be denied."""

    session = {}
    safe_args = {"path": f"users/{alice.pk}/note.txt"}

    side_effects.request_confirmation_if_needed(
        alice,
        FILE_CONTEXT,
        session,
        TOOL_DELETE_FILE,
        safe_args,
    )

    invoke_mock = Mock()

    selected_tool = SimpleNamespace(
        name=TOOL_DELETE_FILE,
        invoke=invoke_mock,
    )

    pep1_mock = Mock(return_value=[selected_tool])

    pep2_mock = Mock(
        return_value=ToolCallAuthorization(
            allowed=False,
            safe_args={},
            message="The application did not allow this request.",
        )
    )

    monkeypatch.setattr(
        side_effects.tooling,
        "get_tools_for_context",
        pep1_mock,
    )
    monkeypatch.setattr(
        side_effects.enforcement,
        "authorize_tool_invocation",
        pep2_mock,
    )

    message = side_effects.handle_confirmation_message(
        alice,
        FILE_CONTEXT,
        session,
        "CONFIRM",
    )

    assert message == "The application did not allow this request."

    pep1_mock.assert_called_once_with(
        alice,
        FILE_CONTEXT,
    )

    pep2_mock.assert_called_once_with(
        alice,
        FILE_CONTEXT,
        TOOL_DELETE_FILE,
        safe_args,
    )

    invoke_mock.assert_not_called()
    assert side_effects.PENDING_SIDE_EFFECT_KEY not in session


def test_confirmation_requires_same_user_and_context(alice, bob):
    """Check that pending confirmation cannot cross users or chats."""

    session = {}
    safe_args = {"path": f"users/{alice.pk}/note.txt"}

    side_effects.request_confirmation_if_needed(
        alice,
        FILE_CONTEXT,
        session,
        TOOL_DELETE_FILE,
        safe_args,
    )

    user_message = side_effects.confirm_pending_side_effect(
        bob,
        FILE_CONTEXT,
        session,
    )

    assert user_message == "The pending action is no longer valid."
    assert side_effects.PENDING_SIDE_EFFECT_KEY not in session

    side_effects.request_confirmation_if_needed(
        alice,
        FILE_CONTEXT,
        session,
        TOOL_DELETE_FILE,
        safe_args,
    )

    context_message = side_effects.confirm_pending_side_effect(
        alice,
        PROFILE_CONTEXT,
        session,
    )

    assert context_message == (
        "The pending action is no longer valid in this chat."
    )
    assert side_effects.PENDING_SIDE_EFFECT_KEY not in session