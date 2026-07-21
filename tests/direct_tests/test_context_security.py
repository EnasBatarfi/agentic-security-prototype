"""Check user and chat-context boundaries without using the agent."""

import pytest
from django.urls import reverse

from apps.agents.tooling import get_tools_for_context
from apps.conversations.models import ChatMessage
from apps.files.models import UploadedFile


def security_case(attack_type, action, baseline_behaviour, secure_behaviour):
    """Add the result details used by the security report."""

    return pytest.mark.security_case(
        category="access_control",
        attack_type=attack_type,
        action=action,
        baseline_behaviour=baseline_behaviour,
        secure_behaviour=secure_behaviour,
    )


@security_case(
    "cross_context_password_reset",
    "password_reset",
    "allowed",
    "blocked",
)
def test_password_reset_is_exposed_in_file_context(alice):
    """Check whether file chat exposes password reset."""
    names = {
        tool.name for tool in get_tools_for_context(alice, ChatMessage.Context.FILE)
    }

    assert "send_password_reset_email" not in names


def profile_tools(user):
    """Return the tool names currently available in profile chat."""

    names = {
        tool.name for tool in get_tools_for_context(user, ChatMessage.Context.PROFILE)
    }
    return names


@security_case("cross_context_list", "list", "allowed", "blocked")
def test_list_is_exposed_in_profile_context(alice):
    """Check whether profile chat exposes file listing."""
    assert "list_files" not in profile_tools(alice)


@security_case("cross_context_search", "search", "allowed", "blocked")
def test_search_is_exposed_in_profile_context(alice):
    """Check whether profile chat exposes file search."""
    assert "search_files" not in profile_tools(alice)


@security_case("cross_context_read", "read", "allowed", "blocked")
def test_read_is_exposed_in_profile_context(alice):
    """Check whether profile chat exposes file reading."""
    assert "read_file" not in profile_tools(alice)


@security_case("cross_context_delete", "delete", "allowed", "blocked")
def test_delete_is_exposed_in_profile_context(alice):
    """Check whether profile chat exposes file deletion."""
    assert "delete_file" not in profile_tools(alice)


@security_case("cross_user_ui_delete", "delete", "blocked", "blocked")
def test_ui_blocks_cross_user_delete(client, alice, bob, isolated_storage, monkeypatch):
    """Check that the UI blocks cross user delete."""
    bob_file = UploadedFile.objects.create(
        owner=bob,
        title="Bob file",
        file=f"users/{bob.pk}/bob.txt",
    )
    calls = []
    monkeypatch.setattr(
        "apps.files.views.mcp_delete_file",
        lambda path: calls.append(path),
    )
    client.force_login(alice)

    response = client.post(reverse("file_delete", args=[bob_file.pk]))

    assert response.status_code == 404
    assert calls == []


@security_case(
    "conversation_history_isolation",
    "chat_history",
    "blocked",
    "blocked",
)
def test_chat_history_is_isolated_by_user_and_context(client, alice, bob, monkeypatch):
    """Check that chat history is isolated by user and context."""
    ChatMessage.objects.create(
        user=alice,
        context=ChatMessage.Context.PROFILE,
        role=ChatMessage.Role.USER,
        content="alice-profile-secret",
    )
    ChatMessage.objects.create(
        user=bob,
        context=ChatMessage.Context.FILE,
        role=ChatMessage.Role.USER,
        content="bob-secret",
    )
    captured = {}

    def agent(user, context, history, session):
        """Capture the history passed into the agent."""

        captured["user"] = user
        captured["context"] = context
        captured["history"] = history
        return "done"

    monkeypatch.setattr("apps.conversations.views.run_agent", agent)
    client.force_login(alice)

    client.post(reverse("file_chat"), {"message": "hello"})
    assert captured["user"] == alice
    assert captured["context"] == ChatMessage.Context.FILE

    contents = [message.content for message in captured["history"]]
    assert "bob-secret" not in contents
    assert "alice-profile-secret" not in contents
