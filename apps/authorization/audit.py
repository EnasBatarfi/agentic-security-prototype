"""
5. Policy/Authorization Layer/Audit
Lightweight authorization audit helper.

This logs authorization decisions for debugging, testing, and evidence.
A database-backed audit model can be added later if needed.
"""

import logging

from .types import AuthorizationRequest, Decision


logger = logging.getLogger("authorization")


def audit_decision(request: AuthorizationRequest, decision: Decision) -> None:
    """
    Log an authorization decision.

    This is useful for debugging, tests, and evidence.
    """

    # Log the decision for debugging later
    logger.info(
        (
            f"authorization_decision "
            f"principal={request.principal.id} "
            f"action={request.action} "
            f"resource_type={request.resource.type} "
            f"resource_id={request.resource.id} "
            f"resource_owner={request.resource.owner_id} "
            f"context={request.context.name} "
            f"tool={request.context.tool} "
            f"allowed={decision.allowed} "
            f"reason={decision.reason} "
            f"code={decision.code} "
            f"policies={decision.policy_ids}"
        ),
        extra={
            "principal_id": request.principal.id,
            "action": request.action,
            "resource_type": request.resource.type,
            "resource_id": request.resource.id,
            "resource_owner_id": request.resource.owner_id,
            "context": request.context.name,
            "tool": request.context.tool,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "code": decision.code,
            "policy_ids": decision.policy_ids,
        },
    )
