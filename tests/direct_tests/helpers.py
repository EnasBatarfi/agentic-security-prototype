""" Helper to execute the application enforcement logic in a test context. """

from pathlib import Path
from typing import Any

from apps.agents.enforcement import authorize_tool_invocation
from apps.agents.side_effects import handle_confirmation_message, request_confirmation_if_needed
from apps.agents.tooling import get_tools_for_context
from apps.files.models import UploadedFile


def run_direct_tool(user: Any, context: str, tool_name: str, args: dict[str, Any], *, confirm: bool = False):
    """Run one tool through PEP 1, PEP 2, confirmation, and the real client."""
    session = {}
    tools = {tool.name: tool for tool in get_tools_for_context(user, context)}
    selected_tool = tools.get(tool_name)

    if selected_tool is None:
        return "blocked", f"Unknown tool: {tool_name}"

    authorization = authorize_tool_invocation(user, context, tool_name, args)

    if not authorization.allowed:
        return "blocked", authorization.message

    confirmation = request_confirmation_if_needed(user, context, session, tool_name, authorization.safe_args)

    if confirmation is not None:
        if not confirm:
            return "confirmation_required", confirmation

        result = handle_confirmation_message(user, context, session, "CONFIRM")
        return "allowed", str(result)

    return "allowed", str(selected_tool.invoke(authorization.safe_args))


def list_files(user: Any, path: str = ""):
    return run_direct_tool(user, "file", "list_files", {"path": path})


def search_files(user: Any, query: str, path: str = ""):
    return run_direct_tool(user, "file", "search_files", {"query": query, "path": path})


def read_file(user: Any, path: str):
    return run_direct_tool(user, "file", "read_file", {"path": path})


def delete_file(user: Any, path: str, *, confirm: bool = False):
    return run_direct_tool(user, "file", "delete_file", {"path": path}, confirm=confirm)


def password_reset(user: Any, email: str, *, confirm: bool = False):
    return run_direct_tool(user, "profile", "send_password_reset_email", {"email": email}, confirm=confirm)


def register_uploaded_file(owner: Any, filename: str):
    """Create the trusted ownership row for an existing physical file."""
    stored_path = f"users/{owner.pk}/{filename}"
    return UploadedFile.objects.create(owner=owner, title=Path(filename).name, file=stored_path)


def create_uploaded_file(make_file, owner: Any, filename: str, content: str = "test content"):
    """Create both the physical file and its trusted ownership row."""
    path = make_file(f"users/{owner.pk}/{filename}", content)
    register_uploaded_file(owner, filename)
    return path
