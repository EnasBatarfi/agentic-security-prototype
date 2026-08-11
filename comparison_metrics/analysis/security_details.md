# Security Details That Were Easy to Miss

These are the main issues that appeared while implementing and testing the
manual enforcement. They are practical details that could easily be missed if
the developer relied only on the model prompt or checked only the normal path.

| ID | Easy-to-miss detail | Why it mattered here | How it is handled |
|---|---|---|---|
| H1 | Model refusal is not a security control. | Similar unsafe prompts produced different behavior. Some were refused, while others reached a tool. | The application makes the final security decision even when the model agrees to act. |
| H2 | Tool filtering and tool execution need separate checks. | The baseline exposed file tools in Profile Chat and password reset in File Chat. A hidden tool could also be reached through another code path. | Tools are filtered before model use and checked again immediately before execution. |
| H3 | Identity and ownership cannot come from tool arguments. | A model-supplied path, email, user ID, or owner could refer to another user's data. | The signed-in Django user supplies identity, and database records supply ownership. |
| H4 | Blocking only `../` is not enough for file paths. | Absolute paths, backslashes, duplicate separators, drive prefixes, normalized parent paths, and `users/<id>` paths can represent unsafe locations. | Paths are normalized, unsafe forms are rejected, and any supplied user ID must match the signed-in user. |
| H5 | Symlinks can escape a valid-looking folder. | A path under the user's directory can resolve to a file outside it. This affects read, list, search, and delete operations. | The MCP layer resolves the final path and checks that it remains inside the allowed root. |
| H6 | Listing and search can leak data without reading a file. | Root listing, parent listing, empty search, and deleted-file storage could reveal filenames or other resources. | MCP starts inside one user's root, and parent and deleted paths are rejected. |
| H7 | Password reset is also an ownership-sensitive action. | Trusting the email argument could let one user request a reset for another account. | The email is resolved using trusted account data and must belong to the signed-in user. |
| H8 | A model-selected destructive action should not run immediately. | A prompt could otherwise be enough to delete a file or send a password-reset email. | The application stores the action and waits for an explicit `CONFIRM` message. |
| H9 | Confirmation must stay tied to the original action. | A general confirmation could approve a different user, chat, tool, resource, or changed argument. Access may also change while the action is pending. | Pending state is tied to the user, context, tool, and trusted arguments. Authorization runs again before one-time execution. |
| H10 | Unknown or incomplete requests must fail closed. | A new tool, missing database record, malformed resource, or incomplete mapping could fall outside the intended allow rules. | Unknown tools and unresolved resources are denied, policies are validated, and decisions are logged. |

The existing tests cover cross-user access, wrong-context tools, prompt and
filename injection, traversal, absolute paths, duplicate separators, symlinks,
root enumeration, deleted resources, confirmation binding, and cross-user
password reset.

Remaining limitations are that pending confirmations do not have an explicit
expiry, filesystem checks may still have time-of-check/time-of-use risks, and
normal log files are not tamper-resistant audit storage.

## Related Code

| ID | Main files and functions |
|---|---|
| H1 | `service.py`: `run_agent()`; `enforcement.py`: `authorize_tool_invocation()` |
| H2 | `tooling.py`: `can_expose_tool()`, `get_tools_for_context()`; `enforcement.py`: `authorize_tool_invocation()` |
| H3 | `tooling.py`: `principal_from_user()`; `enforcement.py`: `file_resource()`, `account_resource()`, `resource_for_tool_call()` |
| H4 | `path_helpers.py`: `normalize_user_file_path()`, `resolve_user_file_path()`; server `files.py`: `build_mcp_path()` |
| H5 | Server `files.py`: `build_mcp_path()`, `to_mcp_relative()` |
| H6 | Client `tools.py`: `list_files()`, `search_files()`; server `files.py`: `list_files_impl()`, `search_files_impl()` |
| H7 | `enforcement.py`: `account_resource()`, `safe_args_for_tool_call()`; `policies.py`: `owns_account()`; client `tools.py`: `send_password_reset_email()` |
| H8 | `actions.py`: `is_side_effect_action()`; `side_effects.py`: `request_confirmation_if_needed()` |
| H9 | `side_effects.py`: `handle_confirmation_message()`, `confirm_pending_side_effect()`, `clear_pending_side_effect()`; `enforcement.py`: `authorize_tool_invocation()` |
| H10 | `actions.py`: `action_for_tool()`; `engine.py`: `authorize()`; `policies.py`: `validate_policies()`; `enforcement.py`: `resource_for_tool_call()`, `authorize_tool_invocation()` |
