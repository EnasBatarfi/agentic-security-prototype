# Lines of Code Results

## Compared versions

- Baseline: `impl/baseline` at `1332294d8830591d0b3e76368ddf5f7942564613`
- Enforcement: `impl/application-policy-enforcement` at `ceb3b5b3a10608f59d5e7b2a72fa1ee6b283480e`

## Final production size

| Metric | Baseline | Enforcement | Difference |
|---|---:|---:|---:|
| Python files | 32 | 41 | +9 |
| Code lines | 647 | 1309 | +662 (+102.3%) |
| Comment lines | 330 | 781 | +451 |
| Blank lines | 336 | 651 | +315 |

## Physical production changes

| Metric | Result |
|---|---:|
| Production files changed | 18 |
| Lines inserted | 1545 |
| Lines deleted | 117 |
| Net change | 1428 |

## Supporting test changes

| Metric | Result |
|---|---:|
| Python test files changed | 26 |
| Lines inserted | 1666 |
| Lines deleted | 302 |
| Net change | 1364 |

Git counts physical lines, including comments and blanks. `cloc` measures
final code size. Tests are shown separately and are not included in the
production totals.
