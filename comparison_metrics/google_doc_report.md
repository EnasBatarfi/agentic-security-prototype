# Manual Security Effort Analysis

## Baseline vs Application-Policy Enforcement

## 1. Purpose

This report compares the insecure baseline with the version that adds manual
security enforcement.

It answers three questions:

1. How much code, how many components, and how much complexity were added?
2. What security details could a developer easily miss?
3. Which parts can be reused and which parts depend on this application?

Compared branches:

- `impl/baseline`
- `impl/application-policy-enforcement`

## 2. Method

- **Git** measured changed files and physical inserted and deleted lines.
- **cloc** measured final Python code size.
- **Radon** measured cyclomatic complexity.
- An LLM produced the first manual classification. The final groups were then
  checked against the changed code, imports, Django models, and existing tests.

Production and test code were measured separately. Migrations, notebooks,
manual-testing files, generated results, and documentation were excluded from
the production total. `apps/conversations/models.py` was also excluded because
its only change was a final newline.

## 3. Main Results

| Measurement | Result |
|---|---:|
| Final production code | 647 to 1,309 lines |
| Code increase | +662 lines (+102.3%) |
| Production files changed | 18 |
| Physical production change | 1,545 inserted, 117 deleted |
| Net physical production change | +1,428 lines |
| Supporting Python test change | +1,364 net lines across 26 files |
| Security components | 6 |
| Average complexity | 1.77 to 2.72 |
| Maximum complexity | 9 to 14 |
| Rank C blocks | 0 to 4 |
| Rank D-F blocks | 0 to 0 |

The production code approximately doubled. The security work was spread across
Django, the agent, the MCP client, and the MCP server. It was not limited to one
policy file.

Git counts physical lines, including comments and blank lines. `cloc` counts
final code lines. This is why the Git and `cloc` numbers are different.

## 4. Security Components

Files and helper functions were grouped by responsibility instead of being
counted as separate components.

| Component | Change | What it does | Main code |
|---|---|---|---|
| C1. Authorization policy layer | Added | Represents the user, action, resource, and context and returns allow or deny. | `types.py`: `Principal`, `Resource`, `AuthorizationRequest`, `Decision`; `actions.py`: `ToolDefinition`; `policies.py`: `Policy`, `POLICIES`; `engine.py`: `authorize()` |
| C2. Context-specific tool exposure | Modified | Gives each chat only the tools allowed in that context. | `tooling.py`: `principal_from_user()`, `can_expose_tool()`, `get_tools_for_context()` |
| C3. Runtime tool-call authorization | Added, with agent integration modified | Checks every selected tool immediately before execution and replaces unsafe arguments with trusted values. | `enforcement.py`: `resource_for_tool_call()`, `safe_args_for_tool_call()`, `authorize_tool_invocation()`; `service.py`: `run_agent()` |
| C4. User-scoped filesystem protection | Added and modified | Normalizes paths, scopes MCP to one user, and prevents the resolved path from leaving the allowed root. | `path_helpers.py`: `normalize_user_file_path()`, `resolve_user_file_path()`; client `tools.py`: `user_mcp_root()`; server `files.py`: `build_mcp_path()`, `to_mcp_relative()` |
| C5. Side-effect confirmation | Added, with chat integration modified | Holds file deletion and password reset until the user confirms the pending action. | `side_effects.py`: `request_confirmation_if_needed()`, `handle_confirmation_message()`, `confirm_pending_side_effect()`, `clear_pending_side_effect()`; `views.py`: `chat_page()` |
| C6. Authorization audit logging | Added | Records allow and deny decisions. | `audit.py`: `audit_decision()`; `settings.py`: logger configuration |

**Total: 6 logical security components.**

Resource lookup and safe argument construction are part of runtime
authorization because they prepare trusted information for the final check and
execution. Password reset is an action protected by several components, not a
separate enforcement component.

## 5. Complexity

| Metric | Baseline | Enforcement | Difference |
|---|---:|---:|---:|
| Analyzed blocks | 60 | 95 | +35 |
| Average complexity | 1.77 | 2.72 | +0.95 |
| Maximum complexity | 9 | 14 | +5 |
| Rank A blocks | 58 | 85 | +27 |
| Rank B blocks | 2 | 6 | +4 |
| Rank C blocks | 0 | 4 | +4 |
| Rank D-F blocks | 0 | 0 | 0 |

The four Rank C areas were:

| File and function | Score | Why it is more complex |
|---|---:|---|
| `path_helpers.py`: `normalize_user_file_path()` | 14 | Handles several unsafe path formats and normalization rules. |
| `side_effects.py`: `confirm_pending_side_effect()` | 12 | Validates, reauthorizes, executes once, and clears pending state. |
| `service.py`: `run_agent()` | 12 | Coordinates the model, tools, authorization, confirmation, and execution. |
| `policies.py`: `validate_policies()` | 12 | Checks policy definitions and consistency. |

Most functions remained Rank A. The larger difficulty was connecting trusted
user, context, resource, argument, and confirmation data across several layers.

## 6. Security Details That Were Easy to Miss

| Detail | Why it mattered | Main code |
|---|---|---|
| Model refusal is not enforcement. | Similar unsafe prompts produced different model behavior. The application must make the final decision. | `service.py`: `run_agent()`; `enforcement.py`: `authorize_tool_invocation()` |
| Tool exposure and execution need separate checks. | Hiding a tool reduces risk, but another execution path could still reach it. | `tooling.py`: `can_expose_tool()`, `get_tools_for_context()`; `enforcement.py`: `authorize_tool_invocation()` |
| Identity and ownership cannot come from tool arguments. | A model-supplied path, email, user ID, or owner could point to another user's data. | `tooling.py`: `principal_from_user()`; `enforcement.py`: `file_resource()`, `account_resource()` |
| Blocking only `../` is not enough. | Absolute paths, backslashes, duplicate separators, drive prefixes, and user-folder paths can also be unsafe. | `path_helpers.py`: `normalize_user_file_path()`, `resolve_user_file_path()` |
| Symlinks can escape a valid-looking folder. | A path inside the user folder can resolve outside it. | Server `files.py`: `build_mcp_path()`, `to_mcp_relative()` |
| List and search can leak information. | Filenames and deleted resources can be exposed without reading a file. | Client `tools.py`: `list_files()`, `search_files()`; server `files.py`: `list_files_impl()`, `search_files_impl()` |
| Password reset needs ownership checks. | Trusting the email argument could target another user's account. | `enforcement.py`: `account_resource()`, `safe_args_for_tool_call()`; `policies.py`: `owns_account()` |
| Destructive actions should not run immediately. | A prompt alone should not delete a file or send a reset email. | `actions.py`: `is_side_effect_action()`; `side_effects.py`: `request_confirmation_if_needed()` |
| Confirmation must remain tied to the original action. | A confirmation should not approve a different user, context, tool, or arguments. | `side_effects.py`: `confirm_pending_side_effect()`, `clear_pending_side_effect()` |
| Unknown or incomplete requests must fail closed. | Unknown tools, missing resources, and invalid mappings should be denied. | `actions.py`: `action_for_tool()`; `engine.py`: `authorize()`; `policies.py`: `validate_policies()` |

Remaining limitations:

- Pending confirmations do not have an explicit expiry.
- Filesystem checks may still have time-of-check/time-of-use risks.
- Normal log files are not tamper-resistant audit storage.

## 7. Reusable and Application-Specific Parts

Reuse was reviewed at a smaller level than the six components. One component
can contain both reusable behavior and application-specific rules.

### Reusable Core

| Current code | What can be reused | Change needed |
|---|---|---|
| `types.py`: `Effect`, `Principal`, `Resource`, `RequestContext`, `AuthorizationRequest`, `Decision` | General authorization request and decision data. | No major structural change. |
| `engine.py`: `authorize()` | Default deny, deny overrides, and policy evaluation. | Pass or configure the policy set instead of loading the current `POLICIES` by default. |

### Reusable With Application Inputs

| Current code | Reusable behavior | What each application supplies |
|---|---|---|
| `actions.py`: `ToolDefinition` and mapping helpers | Map tools to actions and contexts and identify side effects. | Tool definitions, contexts, and side-effect actions. |
| `policies.py`: `Policy`, `Policy.matches()`, `validate_policies()` | Represent, match, and validate policies. | Actions, resources, contexts, consistency checks, and ownership rules. |
| `tooling.py`: `can_expose_tool()`, `get_tools_for_context()` | Check tools before exposing them to the model. | User conversion, tools, policies, and audit handling. |
| `enforcement.py`: `ToolCallAuthorization`, `authorize_tool_invocation()` | Check the selected tool before execution and return trusted arguments. | Tool-action mapping, resource lookup, trusted arguments, policies, and audit handling. |
| `side_effects.py`: confirmation functions | Store, confirm, reauthorize, execute once, and clear a pending action. | State storage, protected actions, wording, execution, expiry, and UI integration. |
| `path_helpers.py` and server `files.py` | Normalize a path and keep the resolved location inside an allowed root. | Storage root, path format, user-root convention, and deleted-resource rules. |
| `audit.py`: `audit_decision()` | Create a consistent authorization event. | Audit destination, format, retention, and monitoring. |

`request_is_consistent()` currently runs inside `Policy.matches()`. It should be
separated or supplied by the application before the policy object is reused.

### What Stays in the Application

| Application area | Current code | Why it stays here |
|---|---|---|
| Identity source | `tooling.py`: `principal_from_user()` | It reads the current Django user fields. |
| Actions and chat contexts | `actions.py`: constants, `TOOL_DEFINITIONS`, `SIDE_EFFECT_ACTIONS`; `policies.py`: `is_file_tool()`, `is_profile_tool()` | File operations, password reset, File Chat, and Profile Chat are current application features. |
| Access and ownership rules | `policies.py`: `POLICIES`, `request_is_consistent()`, `is_authenticated()`, `owns_resource()`, `owns_account()` | These are the application's business decisions. |
| Resource lookup | `enforcement.py`: file and account resource functions | These query the current `UploadedFile` and user models. |
| Trusted tool values | `enforcement.py`: `safe_args_for_tool_call()` | Trusted path and email values depend on the current tools and database records. |
| File storage and MCP setup | `path_helpers.py`: `resolve_user_file_path()`; client `tools.py`: `user_mcp_root()`; `config.py`: `MCP_ROOT`, `MCP_DELETED_ROOT` | The `users/<id>` layout, media root, and deleted-file location are local choices. |
| Confirmation experience | `side_effects.py`, `actions.py`, `views.py`: `chat_page()` | Django sessions, confirmation wording, and selected side effects belong to the current user experience. |
| Application integration | `service.py`: `run_agent()`; `views.py`: `chat_page()` | These connect the controls to the current agent and Django request flow. |
| Audit destination | `settings.py` | Log location, rotation, and retention are deployment choices. |

### Reuse Finding

The reusable system should contain the general authorization model and the
workflows that decide when checks, confirmation, path confinement, and auditing
happen.

Each application should still provide its own users, actions, contexts, access
rules, database lookups, trusted tool values, storage, and user-facing behavior.

## 8. Main Conclusion

Manual enforcement required more than adding policy rules. It needed:

- Tool checks before exposure and execution
- Trusted identity and database-backed ownership
- Trusted tool arguments
- Filesystem confinement
- Confirmation and reauthorization
- Audit logging
- Integration across Django, the agent, MCP client, and MCP server

The production code approximately doubled, but most functions remained low
complexity.

The main design decision for the meeting is where to draw the boundary between
the reusable security workflows and the application-specific users, tools,
policies, resources, and storage rules.

## 9. Questions for the Meeting

1. What is the smallest reusable enforcement core?
2. Should tool-exposure and pre-execution checks both be required?
3. How should an application supply its `Principal`, `Resource`, policies, and
   trusted arguments?
4. Should confirmation and path confinement be part of the reusable system or
   optional workflows?
5. Should pending confirmations have an expiry?
6. What evidence should show that the final design is reusable?
