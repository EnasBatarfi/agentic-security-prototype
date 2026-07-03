"""
Tool selection for the agent.

This module is the LLM-layer Policy Enforcement Point (PEP).

It controls which tools are exposed to the LLM before model.bind_tools(...).
The policy decision is made by the application authorization engine.
"""

from typing import Any

from apps.authorization.actions import RESOURCE_TOOL, TOOL_EXPOSE
from apps.authorization.engine import authorize
from apps.authorization.types import AuthorizationRequest, Principal, RequestContext, Resource
from mcp_client.tools import get_tools


def principal_from_user(user: Any) -> Principal:
    """
    Build an authorization Principal from the authenticated Django user.

    The user must come from Django request.user, not from the LLM.
    """

    # Read trusted identity values from Django request.user.
    is_authenticated = bool(getattr(user, "is_authenticated", False))
    user_pk = getattr(user, "pk", None)
    email = getattr(user, "email", None)

    # The principal has 3 attributes: id, authenticated, email 
    # if the user primary key is none or the user is not authenticated, the engine will deny the request to any tool
    return Principal(
        id=str(user_pk) if is_authenticated and user_pk is not None else None,
        authenticated=is_authenticated,# already has checks using is_authenticated method in the policies 
        email=email if is_authenticated and user_pk is not None else None,
    )



def can_expose_tool(principal: Principal, context: str, tool_name: str) -> bool:
    """
    Return whether a tool may be exposed to the LLM in this context.

    This creates an authorization request for the action:

        tool:expose

    Example:
        principal = current user
        action = tool:expose
        resource = tool/read_file
        context = file
    """
    # In this PEP, the protected resource is the tool itself
    # We are only checking whether this tool can be shown to the LLM in the current chat context
    # So the resource id is the tool name for example "read_file"
    # There is no owner check bc the tool is not owned by any user and it is a system resource
    request = AuthorizationRequest(
        principal=principal,
        action=TOOL_EXPOSE,
        resource=Resource(type=RESOURCE_TOOL,id=tool_name,),
        context=RequestContext(name=context,tool=tool_name,),
    )

    # Ask the policy decision engine to make the decision (PDP)
    decision = authorize(request)
    return decision.allowed


def get_tools_for_context(user: Any, context: str):
    """
    Return only tools allowed for the current user and chat context.

    This function enforces least-privilege tool exposure before the LLM
    receives tools through model.bind_tools(...).
    """

    principal = principal_from_user(user)
    allowed_tools = []

    # Each available MCP tool is checked against the policy engine before it is bound to the model
    for tool in get_tools(principal.id):
        if can_expose_tool(principal, context, tool.name):
            allowed_tools.append(tool)

    return allowed_tools
