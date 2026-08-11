# Components Added or Modified

A component is counted as one runtime security responsibility. Files and helper
functions are kept with the responsibility they support instead of being
counted as separate components.

## C1. Authorization Policy Layer — Added

Represents the user, action, resource, and context and returns an explicit allow
or deny decision.

| File | Main classes, functions, or definitions |
|---|---|
| `apps/authorization/types.py` | `Effect`, `Principal`, `Resource`, `RequestContext`, `AuthorizationRequest`, `Decision` |
| `apps/authorization/actions.py` | `ToolDefinition`, `action_for_tool()`, `tool_is_allowed_in_context()`, `is_side_effect_action()` |
| `apps/authorization/policies.py` | `Policy`, `Policy.matches()`, `request_is_consistent()`, `is_authenticated()`, `owns_resource()`, `owns_account()`, `is_file_tool()`, `is_profile_tool()`, `validate_policies()`, `POLICIES` |
| `apps/authorization/engine.py` | `authorize()` |

## C2. Context-Specific Tool Exposure — Modified

Checks which tools the signed-in user can receive in File Chat or Profile Chat.

| File | Main functions |
|---|---|
| `apps/agents/tooling.py` | `principal_from_user()`, `can_expose_tool()`, `get_tools_for_context()` |

## C3. Runtime Tool-Call Authorization — Added

Checks every selected tool immediately before execution, resolves the protected
resource, and replaces model arguments with trusted values.

| File | Main classes and functions |
|---|---|
| `apps/agents/enforcement.py` | `ToolCallAuthorization`, `file_collection_resource()`, `file_resource()`, `account_resource()`, `resource_for_tool_call()`, `safe_args_for_tool_call()`, `authorize_tool_invocation()` |
| `apps/agents/service.py` | `run_agent()` |

## C4. User-Scoped Filesystem Protection — Added and Modified

Normalizes paths, binds MCP file tools to one user, and checks the resolved path
again at the MCP server boundary.

| File | Main functions or configuration |
|---|---|
| `mcp_client/path_helpers.py` | `normalize_user_file_path()`, `resolve_user_file_path()` |
| `mcp_client/tools.py` | `user_mcp_root()`, `list_files()`, `search_files()`, `read_file()`, `delete_file()`, `get_tools()` |
| `mcp_client/client.py` | `build_custom_server_params()`, `_call_custom_tool()`, `call_custom_mcp_tool()` |
| `mcp_server/tools/files.py` | `build_mcp_path()`, `to_mcp_relative()`, `list_files_impl()`, `search_files_impl()`, `read_file_impl()`, `delete_file_impl()` |
| `mcp_server/config.py` | `MCP_ROOT`, `MCP_DELETED_ROOT` |

## C5. Side-Effect Confirmation — Added, With Chat Integration Modified

Stores file deletion and password reset as pending actions, waits for explicit
confirmation, reauthorizes, executes once, and clears the pending state.

| File | Main functions |
|---|---|
| `apps/agents/side_effects.py` | `request_confirmation_if_needed()`, `handle_confirmation_message()`, `confirm_pending_side_effect()`, `clear_pending_side_effect()` |
| `apps/conversations/views.py` | `chat_page()` |

## C6. Authorization Audit Logging — Added

Records allow and deny decisions so enforcement behavior can be inspected.

| File | Main function or configuration |
|---|---|
| `apps/authorization/audit.py` | `audit_decision()` |
| `config/settings.py` | Authorization logger, output file, rotation, and backup settings |

**Total: 6 logical security components.**

Resource lookup and safe argument construction remain inside runtime
authorization because they prepare trusted information for the final decision
and execution. Password reset is an application action protected by the policy,
runtime authorization, and confirmation components; it is not a separate
enforcement component.
