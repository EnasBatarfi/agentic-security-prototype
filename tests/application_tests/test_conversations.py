"""Check that chat messages are saved and kept in the right context."""

import pytest
from django.urls import reverse

from apps.conversations.models import ChatMessage


def test_chat_saves_user_and_assistant_messages(client, alice, monkeypatch):
    """Check that chat saves user and assistant messages."""
    monkeypatch.setattr(
        "apps.conversations.views.run_agent",
        lambda context, history: "Assistant answer",
    )
    client.force_login(alice)

    response = client.post(reverse("file_chat"), {"message": "List my files"})

    messages = ChatMessage.objects.filter(user=alice).order_by("created_at")
    assert response.status_code == 302
    assert [(m.role, m.content) for m in messages] == [
        (ChatMessage.Role.USER, "List my files"),
        (ChatMessage.Role.ASSISTANT, "Assistant answer"),
    ]


def test_empty_chat_message_does_not_call_agent(client, alice, monkeypatch):
    """Check that empty chat message does not call agent."""
    def fail(*args, **kwargs):
        """Fail if an empty message reaches the agent."""

        raise AssertionError("Agent should not run")

    monkeypatch.setattr("apps.conversations.views.run_agent", fail)
    client.force_login(alice)

    response = client.post(reverse("file_chat"), {"message": "   "})

    assert response.status_code == 302
    assert not ChatMessage.objects.filter(user=alice).exists()


@pytest.mark.parametrize(
    ("url_name", "context"),
    [
        ("file_chat", ChatMessage.Context.FILE),
        ("profile_chat", ChatMessage.Context.PROFILE),
    ],
)
def test_chat_page_renders_requested_context(client, alice, url_name, context):
    """Check that chat page renders requested context."""
    ChatMessage.objects.create(
        user=alice,
        context=context,
        role=ChatMessage.Role.USER,
        content="hello",
    )
    client.force_login(alice)

    response = client.get(reverse(url_name))

    assert response.status_code == 200
    assert response.context["context"] == context
    assert [m.content for m in response.context["chat_messages"]] == ["hello"]
