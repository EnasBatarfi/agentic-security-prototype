# Complexity Results

## Compared versions

- Baseline: `impl/baseline` at `1332294d8830591d0b3e76368ddf5f7942564613`
- Enforcement: `impl/application-policy-enforcement` at `ceb3b5b3a10608f59d5e7b2a72fa1ee6b283480e`

## Cyclomatic complexity

| Metric | Baseline | Enforcement | Difference |
|---|---:|---:|---:|
| Analyzed blocks | 60 | 95 | +35 |
| Average complexity | 1.77 | 2.72 | +0.95 |
| Maximum complexity | 9 | 14 | +5 |
| Rank A blocks | 58 | 85 | +27 |
| Rank B blocks | 2 | 6 | +4 |
| Rank C blocks | 0 | 4 | +4 |
| Rank D blocks | 0 | 0 | +0 |
| Rank E blocks | 0 | 0 | +0 |
| Rank F blocks | 0 | 0 | +0 |

## Enforcement Blocks Ranked B or Higher

| Rank | Score | Function or class |
|---|---:|---|
| C | 14 | `normalize_user_file_path` |
| C | 12 | `confirm_pending_side_effect` |
| C | 12 | `run_agent` |
| C | 12 | `validate_policies` |
| B | 9 | `_extract_text` |
| B | 9 | `authorize` |
| B | 9 | `resolve_user_file_path` |
| B | 6 | `Policy` |
| B | 6 | `request_confirmation_if_needed` |
| B | 6 | `search_files_impl` |

Most blocks remain Rank A. Radon measures control flow inside individual
functions and classes; it does not measure all cross-layer complexity.
