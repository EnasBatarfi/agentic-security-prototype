"""Check the authorization engine algorithm directly."""

from apps.authorization.engine import authorize
from apps.authorization.types import Effect

from .helpers import authorization_request, matching_policy


def test_empty_policy_set_returns_default_deny():
    """Check that the engine denies when no policies are available."""

    decision = authorize(authorization_request(), policies=())

    assert decision.allowed is False
    assert decision.code == "default_deny"
    assert decision.policy_ids == ()


def test_matching_permit_policy_allows_request():
    """Check that one matching permit policy allows a request."""

    decision = authorize(authorization_request(), policies=(matching_policy("permit-read"),))

    assert decision.allowed is True
    assert decision.code == "allowed"
    assert decision.policy_ids == ("permit-read",)


def test_explicit_deny_overrides_matching_permit():
    """Check that an explicit deny takes priority over a permit."""

    policies = (matching_policy("permit-read"), matching_policy("deny-read", Effect.DENY))

    decision = authorize(authorization_request(), policies=policies)

    assert decision.allowed is False
    assert decision.code == "explicit_deny"
    assert decision.policy_ids == ("deny-read",)


def test_multiple_matching_permits_return_all_policy_ids():
    """Check that the engine reports every matching permit policy."""

    policies = (matching_policy("permit-read-one"), matching_policy("permit-read-two"))

    decision = authorize(authorization_request(), policies=policies)

    assert decision.allowed is True
    assert decision.code == "allowed"
    assert decision.policy_ids == ("permit-read-one", "permit-read-two")
