# Manual Security Effort Analysis

This analysis compares the insecure baseline with the version that adds manual
security enforcement. It answers the three questions needed for the project
review:

1. How much code, how many components, and how much complexity did the security
   work add?
2. What security details could a developer easily miss or implement
   incorrectly?
3. Which parts can be reused in another application, and which parts depend on
   this application?

## Main Results

| Result | Finding |
|---|---:|
| Production Python code | 647 to 1,309 lines |
| Code added | +662 lines (+102.3%) |
| Production files changed | 18 |
| Security components | 6 |
| Average cyclomatic complexity | 1.77 to 2.72 |
| Maximum cyclomatic complexity | 9 to 14 |
| Supporting Python test change | +1,364 net lines |

The production code approximately doubled. This happened because enforcement
was added across Django, the agent, the MCP client, and the MCP server.

## How The Analysis Was Done

Git was used to measure changed files and physical lines. `cloc` was used to
compare final Python code size, and Radon was used for cyclomatic complexity.
Production code and tests were measured separately.

For the manual part, an LLM was used to create the first classification. Each
item was then checked against the changed code, imports, database models, and
existing tests.

The full measurement boundary is in [`scope.md`](scope.md). Detailed reviews
and generated summaries are under [`analysis/`](analysis/), commands are under
[`scripts/`](scripts/), and raw tool outputs are under [`outputs/`](outputs/).

## Production Effort

### Final Code Size

| Metric | Baseline | Enforcement | Difference |
|---|---:|---:|---:|
| Python files | 32 | 41 | +9 |
| Code lines | 647 | 1,309 | +662 (+102.3%) |
| Comment lines | 330 | 781 | +451 |
| Blank lines | 336 | 651 | +315 |

### Changed Production Code

| Metric | Result |
|---|---:|
| Files changed | 18 |
| Lines inserted | 1,545 |
| Lines deleted | 117 |
| Net change | 1,428 |

Git includes comments and blank lines, so the clearest code-size number is the
`cloc` result of 662 additional production code lines.

### Supporting Test Work

| Metric | Result |
|---|---:|
| Python test files changed | 26 |
| Lines inserted | 1,666 |
| Lines deleted | 302 |
| Net change | 1,364 |

Tests are not included in the production total. They are shown separately
because cross-user access, context separation, unsafe paths, confirmation,
prompt injection, and normal behavior all needed verification.

Detailed LoC results are in
[`analysis/loc_results.md`](analysis/loc_results.md).

## Security Components

The implementation adds or substantially changes six security responsibilities.

| Component | Change | Purpose | Main code |
|---|---|---|---|
| Authorization policy layer | Added | Represent the user, action, resource, and context and return an allow or deny decision. | `types.py`, `actions.py`, `policies.py`, `engine.py`: `AuthorizationRequest`, `Policy`, `authorize()` |
| Context-specific tool exposure | Modified | Give each chat only the tools that belong in that context. | `tooling.py`: `principal_from_user()`, `can_expose_tool()`, `get_tools_for_context()` |
| Runtime tool-call authorization | Added, with agent integration modified | Check the selected tool again immediately before it runs. | `enforcement.py`: `resource_for_tool_call()`, `safe_args_for_tool_call()`, `authorize_tool_invocation()`; `service.py`: `run_agent()` |
| User-scoped filesystem protection | Added and modified | Normalize paths and keep file operations inside the signed-in user's root. | `path_helpers.py`: `normalize_user_file_path()`, `resolve_user_file_path()`; server `files.py`: `build_mcp_path()`, `to_mcp_relative()` |
| Side-effect confirmation | Added, with chat integration modified | Hold deletion and password reset until the user confirms the pending action. | `side_effects.py`: `request_confirmation_if_needed()`, `confirm_pending_side_effect()`; `views.py`: `chat_page()` |
| Authorization audit logging | Added | Record allow and deny decisions for inspection. | `audit.py`: `audit_decision()`; `settings.py`: logger configuration |

The total is based on responsibilities, not the number of files or helper
functions. The file grouping is in
[`analysis/components.md`](analysis/components.md).

## Complexity

| Metric | Baseline | Enforcement | Difference |
|---|---:|---:|---:|
| Analyzed blocks | 60 | 95 | +35 |
| Average complexity | 1.77 | 2.72 | +0.95 |
| Maximum complexity | 9 | 14 | +5 |
| Rank A blocks | 58 | 85 | +27 |
| Rank B blocks | 2 | 6 | +4 |
| Rank C blocks | 0 | 4 | +4 |
| Rank D-F blocks | 0 | 0 | 0 |

The four Rank C areas are:

| File and function | Score | Main reason |
|---|---:|---|
| `path_helpers.py`: `normalize_user_file_path()` | 14 | Handles several unsafe path formats and normalization rules. |
| `side_effects.py`: `confirm_pending_side_effect()` | 12 | Validates, reauthorizes, executes once, and clears pending state. |
| `service.py`: `run_agent()` | 12 | Coordinates model output, tool calls, authorization, confirmation, and execution. |
| `policies.py`: `validate_policies()` | 12 | Checks policy definitions and consistency. |

Most functions remain Rank A. Radon does not show all of the extra work
required to carry trusted user, context, resource, argument, and confirmation
information across the application.

Detailed results are in
[`analysis/complexity_results.md`](analysis/complexity_results.md).

## Security Details That Were Easy To Miss

The main lessons from implementing and testing the controls were:

1. Model refusal is inconsistent and cannot be the final security control.
2. Tool exposure and tool execution need separate checks.
3. Identity, ownership, paths, and emails must come from trusted application
   data, not model arguments.
4. File protection must handle absolute paths, backslashes, duplicate
   separators, canonical user paths, parent normalization, and symlinks.
5. List and search operations can leak data without opening a file.
6. Password reset needs ownership checks just like file access.
7. Destructive actions need application-controlled confirmation.
8. Confirmation must remain tied to the original user, context, tool,
   resource, and arguments and must be rechecked before execution.
9. Unknown tools and unresolved resources must fail closed.

The real examples, current handling, and remaining limitations are in
[`analysis/security_details.md`](analysis/security_details.md).

## What Can Be Reused

The review found three practical groups:

| Group | What belongs here |
|---|---|
| Reusable foundation | Authorization request and decision types, default deny, deny overrides, and policy evaluation. |
| Reusable after separating application details | Tool exposure checks, pre-execution authorization, confirmation flow, path confinement, policy validation, and audit-event creation. |
| Stays in the application | User identity mapping, available actions and chats, ownership rules, database lookups, trusted tool values, storage layout, confirmation wording, and log destination. |

This boundary is more accurate than calling an entire component reusable or
application-specific. For example, checking a tool before execution is a
reusable workflow, but the `UploadedFile` query used to prove ownership belongs
to this application.

The exact files, functions, and reasons are in
[`analysis/reuse.md`](analysis/reuse.md).

## Main Finding

Manual enforcement required much more than adding policy rules. The application
needed checks before and after model tool selection, trusted user and ownership
data, safe tool arguments, filesystem confinement, confirmation state, and
authorization logging.

For a reusable enforcement system, the best boundary is the general
authorization model and the workflows that control when checks, confirmation,
path confinement, and auditing happen. Each application should still define its
own users, features, access rules, database lookups, safe execution values,
storage choices, and user-facing behavior.

## Limitations

- Lines of code measure code volume, not implementation difficulty or security
  quality.
- Cyclomatic complexity measures control flow but not every cross-layer design
  dependency.
- Component grouping and reuse classification require engineering judgment.
- The comparison uses final committed snapshots, not development time.
- Existing automated and manual tests support the analysis, but they were not
  rerun for this comparison.
