# Reusable and Application-Specific Parts

The reuse review is done at a smaller level than the six components. A single
component can contain a reusable security workflow and application-specific
rules at the same time.

## 1. Reusable Core

These parts contain the general authorization model and decision behavior. They
do not depend on the current Django models, tool names, chats, or file layout.

| Current code | What can be reused | Small change needed |
|---|---|---|
| `types.py`: `Effect`, `Principal`, `Resource`, `RequestContext`, `AuthorizationRequest`, `Decision` | The data used to describe an authorization request and its result. | No major change. Another application can use different values in the existing attribute mappings. |
| `engine.py`: `authorize()` | Default deny, deny overrides, and policy evaluation. | Require the application to pass its policies instead of loading the current `POLICIES` by default. |

## 2. Reusable With Application Inputs

These workflows are useful in another tool-based application, but they cannot
be copied exactly as they are. The security flow can stay the same while the
new application supplies its own policies, tools, state, storage, and resource
lookups.

| Current code | General workflow worth reusing | What another application must supply |
|---|---|---|
| `actions.py`: `ToolDefinition`, `action_for_tool()`, `tool_is_allowed_in_context()`, `is_side_effect_action()` | Map tool names to actions and contexts and identify side effects. | Its own `TOOL_DEFINITIONS`, valid contexts, and `SIDE_EFFECT_ACTIONS`. |
| `policies.py`: `Policy`, `Policy.matches()`, `validate_policies()` | Represent policies, match requests, and reject invalid policy definitions. | Its valid actions, resources, contexts, and request-consistency rules. `request_is_consistent()` must be separated from `Policy.matches()` or supplied by the application. |
| `tooling.py`: `can_expose_tool()`, `get_tools_for_context()` | Check each tool before exposing it to the model. | How users are converted, which tools exist, the policy set, and audit handling. |
| `enforcement.py`: `ToolCallAuthorization`, `authorize_tool_invocation()` | Check the selected tool immediately before execution and return trusted arguments. | Tool-to-action mapping, resource lookup, trusted argument construction, policies, and audit handling. |
| `side_effects.py`: `request_confirmation_if_needed()`, `handle_confirmation_message()`, `confirm_pending_side_effect()`, `clear_pending_side_effect()` | Store, confirm, recheck, execute once, and clear a pending side effect. | Session or state storage, protected actions, confirmation wording, execution function, and expiry rule. |
| `path_helpers.py`: general checks in `normalize_user_file_path()`; `files.py`: `build_mcp_path()`, `to_mcp_relative()` | Normalize a path and confirm that its resolved location stays under an allowed root. | Its storage root, path format, and deleted-file rules. |
| `audit.py`: `audit_decision()` | Create one consistent authorization event. | Where and how the event should be stored. |

## 3. What Stays In The Application

These parts describe the current users, features, access rules, data model,
storage, and user experience. They should stay in the application because a new
application will make different choices even if it reuses the security
workflows above.

| Application area | Current code | Why it stays here |
|---|---|---|
| Where identity comes from | `tooling.py`: `principal_from_user()` | It reads the current Django user fields. A different application may use another user model or identity service. |
| Which actions exist and where they are available | `actions.py`: action, resource, context, and tool constants, `TOOL_DEFINITIONS`, `SIDE_EFFECT_ACTIONS`; `policies.py`: `is_file_tool()`, `is_profile_tool()` | File operations, password reset, File Chat, and Profile Chat are features and contexts defined by this application. |
| Who is allowed to perform each action | `policies.py`: `POLICIES`, `request_is_consistent()`, `is_authenticated()`, `owns_resource()`, `owns_account()` | These are the application's business and ownership rules, not general authorization rules. |
| How file and account ownership is found | `enforcement.py`: `file_collection_resource()`, `file_resource()`, `account_resource()`, `resource_for_tool_call()` | These functions query the current `UploadedFile` and user models and depend on their fields. |
| Which values are safe to send to each tool | `enforcement.py`: `safe_args_for_tool_call()` | The trusted `path` and `email` values depend on the current tool inputs and database records. |
| How files are stored and deleted | `path_helpers.py`: `resolve_user_file_path()`; client `tools.py`: `user_mcp_root()`, file-tool wrappers, `get_tools()`; `client.py`: `build_custom_server_params()`; `config.py`: `MCP_ROOT`, `MCP_DELETED_ROOT` | The `users/<id>` layout, media root, deleted-file location, user-scoped MCP process, and current tool signatures are local storage choices. |
| How confirmation appears in the chat | `side_effects.py`: Django session handling and confirmation messages; `actions.py`: `SIDE_EFFECT_ACTIONS`; `views.py`: `chat_page()` | The Django session flow, `CONFIRM`/`CANCEL` wording, and selected side effects belong to the current user experience. |
| How enforcement is connected to the application | `service.py`: `run_agent()`; `views.py`: `chat_page()` | These functions connect the controls to the current LangChain agent and Django request flow. |
| Where audit records are written | `settings.py`: authorization logging configuration | Log files, rotation, retention, and the final audit destination are deployment choices. |
