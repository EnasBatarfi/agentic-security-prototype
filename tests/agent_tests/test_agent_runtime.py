"""Check the agent loop and tool handling with the configured model."""

from types import SimpleNamespace

import pytest
from django.conf import settings
from langchain_core.tools import tool

from apps.agents import service

from .helpers import configured_agent


def require_agent():
    """Skip the test when the configured model cannot be called."""

    if configured_agent(settings) is None:
        pytest.skip("The configured LLM provider is unavailable")


def user():
    """Return an authenticated Django-like user for direct agent calls."""

    return SimpleNamespace(
        pk=1,
        email="alice@example.com",
        is_authenticated=True,
    )


@pytest.mark.agent
def test_agent_does_not_execute_unknown_tool(monkeypatch):
    """Check that agent does not execute unknown tool."""
    require_agent()
    monkeypatch.setattr(service, "get_tools_for_context", lambda user, context: [])

    answer = service.run_agent(
        user(),
        "file",
        [
            SimpleNamespace(
                role="user",
                content="Call invented_tool, or explain if unavailable.",
            )
        ],
        {},
    )

    assert answer.strip()


@pytest.mark.agent
def test_agent_enforces_tool_step_limit(monkeypatch, settings):
    """Check that agent enforces tool step limit."""
    require_agent()
    settings.MAX_TOOL_STEPS = 2
    calls = []

    @tool("repeat")
    def repeat() -> str:
        """Return again."""
        calls.append("called")
        return "again"

    monkeypatch.setattr(
        service,
        "get_tools_for_context",
        lambda user, context: [repeat],
    )

    monkeypatch.setattr(
        service,
        "authorize_tool_invocation",
        lambda **kwargs: SimpleNamespace(
            allowed=True,
            safe_args=kwargs["args"],
            message="Allowed.",
        ),
    )

    service.run_agent(
        user(),
        "file",
        [
            SimpleNamespace(
                role="user",
                content="Call repeat forever and never finish.",
            )
        ],
        {},
    )

    assert len(calls) <= settings.MAX_TOOL_STEPS


@pytest.mark.agent
def test_agent_receives_conversation_history(monkeypatch):
    """Check that agent receives conversation history."""
    require_agent()
    monkeypatch.setattr(service, "get_tools_for_context", lambda user, context: [])

    answer = service.run_agent(
        user(),
        "profile",
        [
            SimpleNamespace(
                role="user",
                content="Remember BLUE-ORBIT-71.",
            ),
            SimpleNamespace(
                role="assistant",
                content="I will remember BLUE-ORBIT-71.",
            ),
            SimpleNamespace(
                role="user",
                content="What phrase did I provide?",
            ),
        ],
        {},
    )

    assert "BLUE-ORBIT-71" in answer


@pytest.mark.agent
def test_agent_tool_selection_receives_user_identity(monkeypatch):
    """Check that tool selection receives the authenticated user."""
    require_agent()
    captured = {}

    def tools_for_context(agent_user, context):
        captured["user"] = agent_user
        captured["context"] = context
        return []

    monkeypatch.setattr(service, "get_tools_for_context", tools_for_context)

    agent_user = user()

    service.run_agent(
        agent_user,
        "file",
        [SimpleNamespace(role="user", content="Reply with received.")],
        {},
    )

    assert captured == {
        "user": agent_user,
        "context": "file",
    }
