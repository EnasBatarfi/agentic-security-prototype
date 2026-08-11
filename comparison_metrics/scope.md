# Comparison Scope

## Question

How much manual engineering work was needed to move from the insecure baseline
to the version with application-level security enforcement?

## Versions compared

- Baseline: `impl/baseline`
- Enforcement: `impl/application-policy-enforcement`

The scripts record the exact commit hashes used for each measurement.

## Included as production work

The production comparison includes Python code under `apps`, `mcp_client`,
`mcp_server`, and `config`. This covers the authorization logic, agent and
Django integration, filesystem protection, confirmation flow, and audit
logging.

## Kept separate or excluded

- Automated tests are measured separately from production code.
- Migrations, notebooks, manual-testing material, documentation, and generated
  results are excluded from the production total.
- The top-level `manage.py` entry point is excluded.
- `models.py` is excluded from the Git change total because the only difference
  is a final newline and there is no behavior change.

## How the numbers should be read

- Git counts inserted and deleted physical lines, including comments and blank
  lines.
- `cloc` counts final code, comment, and blank lines in each version.
- Radon measures control-flow complexity inside functions and classes.
- An LLM was used for the first grouping of components, easy-to-miss details,
  and reusable parts. The groups were then checked against the changed code,
  imports, models, and existing tests before writing the final analysis.

These measurements show code size and structure. They do not measure developer
time or prove that the implementation is secure.
