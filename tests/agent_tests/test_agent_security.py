"""Run the security cases through the real application agent flow."""

import time

import pytest
from django.conf import settings
from django.urls import reverse

from apps.agents import service, side_effects
from apps.conversations.models import ChatMessage

from .helpers import (
    action_executed,
    configured_agent,
    load_cases,
    render_case,
    reset_state,
    traced_tools,
)


CASES = load_cases()


@pytest.mark.agent
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("raw_case", CASES, ids=lambda case: case["id"])
def test_agent_security_case(raw_case, request, client, alice, bob, isolated_storage, monkeypatch):
    """Check the agent action and resulting state for each security case."""
    configured = configured_agent(settings)
    if configured is None:
        pytest.skip("The configured LLM provider is unavailable")
    provider, model = configured

    trials = request.config.getoption("--agent-trials")
    if trials < 1:
        pytest.fail("--agent-trials must be at least 1")

    case = render_case(
        raw_case,
        {
            "alice_id": alice.pk,
            "bob_id": bob.pk,
            "alice_email": alice.email,
            "bob_email": bob.email,
            "absolute_read_path": str(
                isolated_storage.parent / "outside-read.txt"
            ),
            "absolute_delete_path": str(
                isolated_storage.parent / "outside-delete.txt"
            ),
            "absolute_bob_path": str(
                isolated_storage / f"users/{bob.pk}/bob-secret.txt"
            ),
        },
    )

    original_get_tools = service.get_tools_for_context
    trace = []

    def instrumented_tools(user, context):
        """Return the real tools wrapped with trace recording."""

        return traced_tools(original_get_tools(user, context), trace)

    monkeypatch.setattr(service, "get_tools_for_context", instrumented_tools)
    monkeypatch.setattr(
        side_effects.tooling,
        "get_tools_for_context",
        instrumented_tools,
    )
    client.force_login(alice)

    observed = []
    for trial in range(1, trials + 1):
        reset_state(isolated_storage, alice, bob)
        ChatMessage.objects.all().delete()
        trace.clear()
        
        session = client.session
        session.pop(side_effects.PENDING_SIDE_EFFECT_KEY, None)
        session.save()

        started = time.perf_counter()
        url = reverse(
            "profile_chat"
            if case["context"] == "profile"
            else "file_chat"
        )

        response = client.post(
            url,
            {"message": case["prompt"]},
        )

        if (
            case["secure_behaviour"] == "allowed"
            and case["action"] in {"delete", "password_reset"}
        ):
            response = client.post(
                url,
                {"message": "CONFIRM"},
            )

        latency = round(time.perf_counter() - started, 4)
        assert response.status_code == 302

        answer = ChatMessage.objects.filter(
            user=alice,
            context=case["context"],
            role=ChatMessage.Role.ASSISTANT,
        ).latest("created_at").content

        executed = action_executed(case, trace, isolated_storage)
        actual = "allowed" if executed else "blocked"
        passed = actual == case["secure_behaviour"]
        
        request.config.agent_security_results.append(
            {
                "id": case["id"],
                "test_type": "agent_security",
                "category": case["category"],
                "attack_type": case["attack_type"],
                "action": case["action"],
                "baseline_behaviour": case["baseline_behaviour"],
                "secure_behaviour": case["secure_behaviour"],
                "evaluation": case["evaluation"],
                "actual": actual,
                "passed": passed,
                "trial": trial,
                "context": case["context"],
                "prompt": case["prompt"],
                "tool_trace": list(trace),
                "assistant_answer": answer,
                "provider": provider,
                "model": model,
                "latency_sec": latency,
            }
        )
        observed.append(actual)

    if case["evaluation"] == "assert":
        assert all(value == case["secure_behaviour"] for value in observed)
    else:
        assert len(observed) == trials
