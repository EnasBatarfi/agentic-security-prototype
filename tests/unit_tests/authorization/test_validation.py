"""Check validation of authorization policy definitions."""

import pytest

from apps.authorization.actions import FILE_CONTEXT, FILE_READ, RESOURCE_FILE
from apps.authorization.policies import Policy, validate_policies
from apps.authorization.types import Effect


def policy(policy_id="policy-1", actions=frozenset({FILE_READ}), resource_type=RESOURCE_FILE, contexts=frozenset({FILE_CONTEXT})):
    """Create a policy used by validation tests."""

    return Policy(id=policy_id, effect=Effect.PERMIT, actions=actions, resource_type=resource_type, contexts=contexts, condition=lambda request: True)


def test_valid_policy_definition_is_accepted():
    """Check that validation accepts a complete known policy."""

    validate_policies((policy(),))


def test_duplicate_policy_ids_are_rejected():
    """Check that validation rejects duplicate policy identifiers."""

    with pytest.raises(ValueError, match="unique"):
        validate_policies((policy(), policy()))


def test_unknown_action_is_rejected():
    """Check that validation rejects an unknown business action."""

    with pytest.raises(ValueError, match="actions"):
        validate_policies((policy(actions=frozenset({"file:unknown"})),))


def test_unknown_effect_is_rejected():
    """Check that validation rejects an unknown policy effect."""

    invalid_policy = Policy(id="policy-1", effect="unknown", actions=frozenset({FILE_READ}), resource_type=RESOURCE_FILE, contexts=frozenset({FILE_CONTEXT}), condition=lambda request: True)

    with pytest.raises(ValueError, match="effect"):
        validate_policies((invalid_policy,))


def test_unknown_resource_type_is_rejected():
    """Check that validation rejects an unknown resource type."""

    with pytest.raises(ValueError, match="resource type"):
        validate_policies((policy(resource_type="unknown"),))


def test_unknown_context_is_rejected():
    """Check that validation rejects an unknown context."""

    with pytest.raises(ValueError, match="contexts"):
        validate_policies((policy(contexts=frozenset({"unknown"})),))
