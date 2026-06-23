"""
4. Policy/Authorization Layer/Engine
Policy Decision Point for the policy layer.

This module evaluates AuthorizationRequest objects against the policy set.

Decision semantics:
1. Default deny.
2. Explicit deny overrides permit.
3. Permit only if at least one permit policy matches.
4. Decisions are deterministic and independent of the LLM.
"""

from .policies import POLICIES, Policy
from .types import AuthorizationRequest, Decision, Effect


def authorize(
    request: AuthorizationRequest,
    policies: tuple[Policy, ...] = POLICIES,
) -> Decision:
    """
    Evaluate an authorization request and return an allow/deny decision.
    """

    # Check for explicit deny -- this will override any permit
    matching_denies = tuple(
        policy.id
        for policy in policies
        # This will override any permit by checking if the policy effect is deny and the request matches
        if policy.effect == Effect.DENY and policy.matches(request)
    )

    # Return denies if any match
    if matching_denies:
        return Decision(
            allowed=False,
            reason="Explicit deny policy matched.",
            code="explicit_deny",
            policy_ids=matching_denies,
        )

    # Check for permit
    matching_permits = tuple(
        policy.id
        for policy in policies
        # This will check if the policy effect is permit and the request matches
        if policy.effect == Effect.PERMIT and policy.matches(request)
    )

    # Return permits if any match
    if matching_permits:
        return Decision(
            allowed=True,
            reason="Permit policy matched.",
            code="allowed",
            policy_ids=matching_permits,
        )

    # Default deny
    return Decision(
        allowed=False,
        reason="No permit policy matched.",
        code="default_deny",
        policy_ids=(),
    )