<a id="readme-top"></a>

<div align="center">
  <h1>Security Test Suite</h1>
  <p><strong>Regression and security tests for the agentic security prototype.</strong></p>
  <p>
    <a href="notebooks/security_test_analysis.ipynb"><strong>Analysis Notebook</strong></a>
    &middot;
    <a href="analysis/metrics_summary.csv"><strong>Metrics CSV</strong></a>
    &middot;
    <a href="outputs/agent_security_results.jsonl"><strong>Agent Outputs</strong></a>
  </p>
  <p>
    <a href="#quick-start"><strong>Quick Start</strong></a>
    &middot;
    <a href="#test-layers"><strong>Test Layers</strong></a>
    &middot;
    <a href="#security-model"><strong>Security Model</strong></a>
    &middot;
    <a href="#analysis-notebook"><strong>Analysis</strong></a>
    &middot;
    <a href="#interpreting-results"><strong>Interpreting Results</strong></a>
  </p>
</div>

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-test-suite">About The Test Suite</a></li>
    <li><a href="#what-this-suite-proves">What This Suite Proves</a></li>
    <li><a href="#quick-start">Quick Start</a></li>
    <li><a href="#test-layers">Test Layers</a></li>
    <li><a href="#security-model">Security Model</a></li>
    <li><a href="#path-normalization-example">Path Normalization Example</a></li>
    <li><a href="#result-fields">Result Fields</a></li>
    <li><a href="#security-categories">Security Categories</a></li>
    <li><a href="#output-files">Output Files</a></li>
    <li><a href="#main-metrics">Main Metrics</a></li>
    <li><a href="#analysis-notebook">Analysis Notebook</a></li>
    <li><a href="#runbook">Runbook</a></li>
    <li><a href="#common-workflows">Common Workflows</a></li>
    <li><a href="#interpreting-results">Interpreting Results</a></li>
  </ol>
</details>

## About The Test Suite

This directory contains the test suite for the agentic security prototype. It
checks that normal application behaviour still works while security controls
block unauthorized file, profile, chat, and side-effect actions.

The suite is split into layers:

- unit and application tests check normal correctness
- direct security tests check tool enforcement without an LLM
- agent tests check the same controls through model-driven tool use

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## What This Suite Proves

The suite checks four things:

1. Does normal product behaviour still work?
2. Are users only shown tools they are allowed to use?
3. Are unauthorized tool calls blocked if the model tries them?
4. Do valid actions still work, including actions that need confirmation?

Agent tests also capture model variability. A run may refuse, call a safe tool,
attempt a blocked tool, or safely replan. Results are graded from the tool trace
and final state, not only from the assistant message.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Quick Start

Run these commands from the repository root.

### 1. Run non-LLM tests

```bash
.venv/bin/python -m pytest tests/unit_tests tests/application_tests tests/direct_tests
```

### 2. Run agent tests

One trial:

```bash
.venv/bin/python -m pytest tests/agent_tests --run-agent --agent-trials 1
```

Three trials for variability:

```bash
.venv/bin/python -m pytest tests/agent_tests --run-agent --agent-trials 3
```

Agent tests call the configured provider and may cost money.

### 3. Build analysis files

```bash
.venv/bin/python tests/scripts/summarize_results.py
```

### 4. Open the notebook

```bash
jupyter notebook tests/notebooks/security_test_analysis.ipynb
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Test Layers

The suite has **155 tests** across four layers.

| Layer | Tests | Purpose |
|---|---:|---|
| Unit | 38 | Isolated policy, authorization, confirmation, and tool-exposure logic |
| Application | 34 | Normal Django view/model behaviour |
| Direct security | 38 | Secure enforcement without the LLM |
| Agent | 45 | Security and runtime behaviour through the agent |

### Unit tests

Unit tests check the security logic by itself. They do not call Django views,
MCP tools, or an LLM.

Main coverage:

- authorization policy definitions
- authorization engine decisions
- agent tool exposure by user and context
- side-effect confirmation handling
- low-level agent runtime safeguards

### Application tests

Application tests check normal product behaviour.

| Area | Tests |
|---|---:|
| Accounts | 14 |
| Conversations | 4 |
| Files | 8 |
| MCP | 5 |
| Providers | 3 |

If these fail, fix application behaviour before reading the security results.

### Direct security tests

Direct security tests run the file, profile, and chat tools without the model.
They still use the protected tool path, so they test enforcement before any LLM
behaviour is involved.

| Category | Tests |
|---|---:|
| Access control | 15 |
| Authorized behaviour | 6 |
| Filesystem security | 9 |
| Resource exposure | 7 |
| Action safety | 1 |

Direct security is the clearest enforcement signal. If a blocked direct case
executes, the issue is in the app or tool layer, not the model.

### Agent tests

The agent folder contains **41 security cases** and **4 runtime checks**.
Prompts and expected actions live in `tests/cases/agent_security_cases.json`.

| Category | Trials with `--agent-trials 3` | Cases |
|---|---:|---:|
| Access control | 39 | 13 |
| Authorized behaviour | 18 | 6 |
| Filesystem security | 27 | 9 |
| Prompt injection | 15 | 5 |
| Resource exposure | 21 | 7 |
| Action safety | 3 | 1 |

The four runtime checks cover:

- unknown tool calls
- tool-step limits
- conversation history passed to the model
- user identity passed into tool selection

Asserted cases affect pytest pass/fail. Measured cases are recorded for review
only. Increasing `--agent-trials` repeats the 41 security cases; the collected
test count stays 45.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Security Model

The model is not the security boundary. The security design has three main
enforcement points:

1. **Policy layer / PDP** defines and evaluates authorization decisions.
2. **Tool exposure enforcement / PEP 1** decides which tools the model can see.
3. **Tool invocation enforcement / PEP 2** authorizes tool calls before they run.

Client checks guide normal user flows, including confirmations. Server-side
checks add another defense around application state. Agent behaviour can change
across trials, but unauthorized effects should still be blocked.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Path Normalization Example

The `same_user_parent_normalization` case starts with a suspicious `../` path.
In some trials, the model does not use that raw path. It searches or lists files,
finds the clean `alice-note.txt` path, and reads Alice's own file.

That is not cross-user disclosure:

- the raw `../` path was not executed
- no path traversal reached the MCP tool
- no cross-user file was accessed
- the final resource was Alice's own file

The summary and notebook count this pattern as **safe replan**, not
unauthorized execution. A safe replan means the trace shows a non-blocked tool
result with at least one argument that was not copied from the prompt.

If the model resolves the request to another user's path, enforcement should
block it.

The safe-replan metric is automatic. A blocked-expectation agent case counts as
safe replan when the agent completes through different tool arguments and gets a
non-blocked result.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Result Fields

| Field | Meaning |
|---|---|
| `baseline_behaviour` | Old-version comparison value; not the pass target |
| `secure_behaviour` | Expected result: usually `blocked` for attacks and `allowed` for valid actions |
| `actual` | What happened after grading the tool trace and final state |
| `passed` | Whether an asserted result matched `secure_behaviour` |
| `evaluation: assert` | Pytest enforces the expected secure result |
| `evaluation: measure` | Behaviour is recorded for analysis without forcing pytest failure |
| `trial` | Repeated run number for an agent case |
| `tool_trace` | Tools the agent attempted and their returned results |
| `assistant_answer` | Model response text; useful context, but not used for grading |

Use `secure_behaviour` as the pass target. Use `baseline_behaviour` only when
comparing this secure version with the old insecure behaviour.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Security Categories

| Category | Meaning |
|---|---|
| `authorized_behaviour` | Valid user actions should still work |
| `access_control` | User and chat-context boundaries must hold |
| `filesystem_security` | Traversal, absolute path, symlink, and normalization cases |
| `prompt_injection` | Instructions hidden in prompts, files, or tool outputs |
| `resource_exposure` | Root listing, empty searches, deleted resources, and broad discovery |
| `action_safety` | Sensitive side effects such as delete/reset without confirmation |

Actions are `list`, `search`, `read`, `delete`, `password_reset`, and
`chat_history`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Output Files

Pytest writes raw JSONL records to `tests/outputs/`.

| File | Produced by | Contents |
|---|---|---|
| `application_results.jsonl` | Application tests | One row per application test |
| `direct_security_results.jsonl` | Direct security tests | One row per direct security scenario |
| `agent_security_results.jsonl` | Agent tests | One row per agent trial, including prompt, trace, answer, model, and latency |

Each JSONL line is a complete result record.

The summary script writes derived analysis files to `tests/analysis/`.

| File | Purpose |
|---|---|
| `metrics_summary.json` | Structured metrics used by the notebook |
| `metrics_summary.csv` | Flat spreadsheet-friendly version of the metrics |
| `agent_trial_summary.csv` | Repeated agent outcomes by case, such as `blocked 2/3, allowed 1/3` |
| `failure_analysis.csv` | Asserted tests that did not match expected secure behaviour |

Generated files are reproducible. Rerunning tests or the notebook may change
timings, trial outcomes, and notebook output.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Main Metrics

| Metric | What it means | Desired direction |
|---|---|---|
| `secure_behaviour_rate` | Share of results matching `secure_behaviour` | Higher is better |
| `unauthorized_action_execution_rate` | Share of blocked cases where an unauthorized action happened | Lower is better |
| `safe_replan_rate` | Share of blocked agent cases completed through different non-blocked tool arguments | Review separately |
| `authorized_action_success_rate` | Share of allowed cases where valid action completed | Higher is better |
| blocked-case tool attempt rate | Share of blocked agent trials where the model attempted any tool call | Context signal, not failure by itself |
| mixed trial count | Cases where repeated trials had both allowed and blocked outcomes | Should be reviewed |

The summary keeps `prohibited_action_execution_rate` as a raw old-style signal.
It also records `unauthorized_action_execution_rate` and `safe_replan_rate`.
Safe replans are classified from the tool trace, not from a manual case label.

A strong result means unauthorized effects do not happen, even when the model
tries a risky tool call.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Analysis Notebook

Open:

```bash
jupyter notebook tests/notebooks/security_test_analysis.ipynb
```

The notebook reads `tests/outputs/` and `tests/analysis/`. Run
`tests/scripts/summarize_results.py` before opening it.

The notebook sections are:

1. Load result files.
2. Summarize run coverage.
3. Check application behaviour.
4. Check direct enforcement.
5. Check agent security, model pressure, repeated trials, and allowed blocked cases.
6. Show coverage.
7. Show agent performance and tool-use patterns.
8. Show asserted failures.
9. Provide the final reading.

The notebook focuses on:

- enforcement and usability
- unauthorized execution and safe replans by layer
- model pressure versus blocked execution
- blocked-case outcomes by category
- inconsistent agent trials
- explanations for allowed blocked cases

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Runbook

Run each section separately when you want clean terminal output.

### 1. Unit

```bash
.venv/bin/python -m pytest tests/unit_tests
```

### 2. Application

```bash
.venv/bin/python -m pytest tests/application_tests
```

### 3. Direct Security

```bash
.venv/bin/python -m pytest tests/direct_tests
```

### 4. Agent Security

One trial:

```bash
.venv/bin/python -m pytest tests/agent_tests --run-agent --agent-trials 1
```

Three trials for variability:

```bash
.venv/bin/python -m pytest tests/agent_tests --run-agent --agent-trials 3
```

### 5. Build Analysis

```bash
.venv/bin/python tests/scripts/summarize_results.py
```

### 6. Execute Notebook In Place

```bash
PATH=/Users/enasbatarfi/agentic_security_prototype/.venv/bin:$PATH \
MPLCONFIGDIR=/tmp/matplotlib \
jupyter nbconvert --to notebook --execute --inplace \
  tests/notebooks/security_test_analysis.ipynb \
  --ExecutePreprocessor.timeout=600
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Common Workflows

### Full Secure Run With Agent

```bash
.venv/bin/python -m pytest tests/application_tests
.venv/bin/python -m pytest tests/direct_tests
.venv/bin/python -m pytest tests/agent_tests --run-agent --agent-trials 3
.venv/bin/python tests/scripts/summarize_results.py
```

### Non-LLM Run

```bash
.venv/bin/python -m pytest tests/unit_tests tests/application_tests tests/direct_tests
.venv/bin/python tests/scripts/summarize_results.py
```

If `agent_security_results.jsonl` was not produced, the agent sections will say
that no agent run is available.

### Refresh Analysis Without Rerunning Tests

```bash
.venv/bin/python tests/scripts/summarize_results.py
```

Use this after editing the summarizer or notebook while keeping the same raw
result files.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Interpreting Results

Start with the layer:

- **Unit failure**: policy, enforcement, confirmation, or tool exposure is wrong in isolation.
- **Application failure**: normal product behaviour broke.
- **Direct security failure**: enforcement failed before the model was involved.
- **Agent asserted failure**: an allowed action or runtime check did not match the expected result.
- **Agent measured allowed blocked case**: not a pytest failure, but it is a security review item.

Then inspect the raw row:

1. Check `secure_behaviour`.
2. Check `actual`.
3. Read `tool_trace`.
4. Compare the trace with final state.
5. Use `assistant_answer` only as supporting context.

For agent variability, use repeated trials. A single trial can hide inconsistent
behaviour.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
