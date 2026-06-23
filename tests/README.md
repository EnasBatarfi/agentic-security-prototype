# Tests

These tests cover the current application baseline and the isolated V2
authorization layer. The baseline tests record current behaviour, including
behaviour that may be insecure, and compare it with the expected secure
behaviour.

The suite currently collects **146 tests** across four parts:

| Test layer | Tests | What it checks |
|---|---:|---|
| Unit | 29 | Isolated authorization policy and engine behavior |
| Application | 34 | Normal application behaviour |
| Direct security | 38 | Security without the agent |
| Agent | 45 | Security and runtime behaviour through the real agent |

### Unit tests: 29

The authorization unit tests check the policy definitions and decision
algorithm in memory. They do not call Django views, MCP tools, or an LLM.

### Application tests: 34

| Area | Tests |
|---|---:|
| Accounts | 14 |
| Conversations | 4 |
| Files | 8 |
| MCP | 5 |
| Providers | 3 |

### Direct security tests: 38

| Category | Tests |
|---|---:|
| Access control | 15 |
| Authorized behaviour | 7 |
| Filesystem security | 8 |
| Resource exposure | 7 |
| Action safety | 1 |

### Agent tests: 45

The agent folder contains **41 security cases** and **4 runtime checks**.
Prompts and expected actions for the security cases are stored in
`cases/agent_security_cases.json`.

| Agent security category | Cases |
|---|---:|
| Access control | 13 |
| Authorized behaviour | 7 |
| Filesystem security | 8 |
| Prompt injection | 5 |
| Resource exposure | 7 |
| Action safety | 1 |

The four runtime checks cover unknown tools, tool-step limits, conversation
history, and user identity exposure during tool selection.

Of the 41 agent security cases, 7 are asserted and 34 are measured. Increasing
`--agent-trials` repeats the 41 security cases inside those tests; it does not
change pytest's collected count of 45 agent tests.

## Understanding the results

- `expected` is the current baseline behaviour.
- `secure_behaviour` is the behaviour a secure version should have.
- `actual` is what happened during the test.
- `passed` means `actual` matched the baseline in `expected`.
- `evaluation: measure` records agent behaviour without forcing pass or fail.

Agent results use tool calls and actual state changes. The assistant's written
answer alone does not decide the result.

### What the security categories mean

- `authorized_behaviour` checks that valid actions still work.
- `access_control` checks user and chat-context boundaries.
- `filesystem_security` checks traversal, absolute paths, and symlinks.
- `prompt_injection` checks instructions hidden in prompts, files, or tool
  results.
- `resource_exposure` checks root listing, empty searches, and deleted files.
- `action_safety` checks sensitive actions such as deleting without
  confirmation.

### Other result fields

- `category` groups cases by the security area above.
- `attack_type` identifies the exact scenario being tested.
- `action` is the operation: `list`, `search`, `read`, `delete`, or
  `password_reset`.
- `evaluation: assert` means pytest enforces the expected result.
- `evaluation: measure` records model behaviour without making it pass or fail.
- `trial` identifies repeated runs of the same agent case.

## Output files

Pytest writes detailed raw results to `tests/outputs/`:

- `application_results.jsonl` contains one row for each application test.
- `direct_security_results.jsonl` contains one row for each direct security
  test.
- `agent_security_results.jsonl` contains one row for each agent trial.

Each JSONL line is a complete result record. Agent rows also include the prompt,
tool trace, assistant answer, model, and latency.

The summary script creates four files in `tests/analysis/`:

- `metrics_summary.json` is the complete structured summary used by the
  notebook.
- `metrics_summary.csv` contains the same summary in a flat spreadsheet format.
- `agent_trial_summary.csv` groups repeated trials by agent case, for example
  `blocked 2/3, allowed 1/3`.
- `failure_analysis.csv` contains only asserted tests whose actual result did
  not match `expected`. Measured cases are not failures.

There are two `metrics_summary` files because they serve different uses: JSON
keeps the report sections and hierarchy, while CSV is easier to filter or open
in a spreadsheet.

### How `metrics_summary` is organized

- `overview` shows the number of application results, direct scenarios, agent
  trials, and defined agent cases.
- `application_behaviour` shows pass rates and timing overall and by application
  area.
- `security.overall` compares direct and agent security results.
- `security.by_category` repeats the security metrics for each category.
- `security.by_action` repeats them for each action.
- `coverage` shows which areas, categories, attack types, and cases ran.
- `agent_performance` shows latency, tool use, refusals, and executed actions.
- `slowest_tests` lists the slowest application and direct tests.

The most important security metrics are:

- `secure_behaviour_rate`: how often the result matched the secure target.
- `prohibited_action_execution_rate`: how often an action that should be
  blocked still happened. Lower is better.
- `authorized_action_success_rate`: how often a valid action worked. Higher is
  better.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

Copy `.env.example` to `.env` and configure the LLM provider before running
agent tests.

## Run the tests

Run each section separately so its result is easy to read.

### 1. Unit tests

```bash
.venv/bin/python -m pytest tests/unit_tests
```

### 2. Application tests

```bash
.venv/bin/python -m pytest tests/application_tests
```

### 3. Direct security tests

```bash
.venv/bin/python -m pytest tests/direct_tests
```

The unit, application, and direct-security commands do not call an LLM.

### 4. Agent tests

```bash
.venv/bin/python -m pytest tests/agent_tests \
  --run-agent \
  --agent-trials 1
```

Agent tests call the configured provider and may cost money. Use
`--agent-trials 3` when repeated results are needed.

### 5. Create the summary

```bash
.venv/bin/python tests/scripts/summarize_results.py
```

Run the summary after the application, direct-security, and agent commands. Unit
tests do not write report data. `agent_trial_summary.csv` shows repeated agent
trials in a simple form, such as `blocked 2/3, allowed 1/3`.

### 6. Open the notebook

```bash
jupyter notebook tests/notebooks/security_test_analysis.ipynb
```

Select the `Agentic Security (.venv)` kernel, then run all cells.

## Run everything together

```bash
rm -rf tests/outputs tests/analysis

.venv/bin/python -m pytest tests \
  --run-agent \
  --agent-trials 1

.venv/bin/python tests/scripts/summarize_results.py
```

## Run everything except the agent

```bash
rm -rf tests/outputs tests/analysis

.venv/bin/python -m pytest tests/unit_tests tests/application_tests tests/direct_tests

.venv/bin/python tests/scripts/summarize_results.py
```

The agent sections in the report will show that no agent run is available.

## Manual testing

Open [manual_test/MANUAL_TEST.md](manual_test/MANUAL_TEST.md).

It includes the setup files, UI checks, direct shell checks, agent prompts, and
cleanup steps.
