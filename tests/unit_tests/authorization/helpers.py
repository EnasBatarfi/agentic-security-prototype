"""Shared builders for authorization unit tests."""

from apps.authorization.actions import FILE_CONTEXT, FILE_READ, RESOURCE_FILE, TOOL_READ_FILE
from apps.authorization.policies import Policy
from apps.authorization.types import AuthorizationRequest, Effect, Principal, RequestContext, Resource


def principal(user_id="1", email="user@example.com", authenticated=True):
    """Create the principal used by authorization tests."""

    return Principal(id=str(user_id) if user_id is not None else None, authenticated=authenticated, email=email)


def authorization_request(action=FILE_READ, resource_type=RESOURCE_FILE, resource_id="file-10", owner_id="1", context_name=FILE_CONTEXT, tool=TOOL_READ_FILE, actor=None):
    """Create an authorization request with safe default values."""

    return AuthorizationRequest(
        principal=actor or principal(),
        action=action,
        resource=Resource(type=resource_type, id=resource_id, owner_id=owner_id),
        context=RequestContext(name=context_name, tool=tool),
    )


def matching_policy(policy_id, effect=Effect.PERMIT):
    """Create an artificial policy that matches the default request."""

    return Policy(
        id=policy_id,
        effect=effect,
        actions=frozenset({FILE_READ}),
        resource_type=RESOURCE_FILE,
        contexts=frozenset({FILE_CONTEXT}),
        condition=lambda request: True,
    )
