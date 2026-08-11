#!/usr/bin/env bash

# Compare cyclomatic complexity in the same production-code scope used for LoC

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
BASE_REF="impl/baseline"
SECURE_REF="impl/application-policy-enforcement"
ANALYSIS_OUT="$ROOT/comparison_metrics/analysis"
RAW_OUT="$ROOT/comparison_metrics/outputs"

cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
else
    PYTHON="$(command -v python3)"
fi

if [[ -x "$ROOT/.venv/bin/radon" ]]; then
    RADON="$ROOT/.venv/bin/radon"
else
    RADON="$(command -v radon || true)"
fi

if [[ -z "$RADON" ]]; then
    echo "Radon is not installed. Install it with: .venv/bin/python -m pip install radon"
    exit 1
fi

BASE_HASH="$(git rev-parse "$BASE_REF")"
SECURE_HASH="$(git rev-parse "$SECURE_REF")"

# Use clean snapshots and keep temporary JSON out of the analysis folder.
SNAPSHOT_DIR="$(mktemp -d)"
trap 'rm -rf "$SNAPSHOT_DIR"' EXIT

mkdir -p "$SNAPSHOT_DIR/baseline" "$SNAPSHOT_DIR/enforcement"
git archive "$BASE_HASH" | tar -x -C "$SNAPSHOT_DIR/baseline"
git archive "$SECURE_HASH" | tar -x -C "$SNAPSHOT_DIR/enforcement"

make_file_list() {
    local snapshot="$1"
    local output="$2"

    find \
        "$snapshot/apps" \
        "$snapshot/mcp_client" \
        "$snapshot/mcp_server" \
        "$snapshot/config" \
        -type f \
        -name '*.py' \
        ! -path '*/migrations/*' \
        ! -path '*/tests/*' \
        ! -name 'tests.py' \
        -print0 \
        | while IFS= read -r -d '' file_path; do
            printf '%s\0' "${file_path#"$snapshot/"}"
        done > "$output"
}

make_file_list "$SNAPSHOT_DIR/baseline" "$SNAPSHOT_DIR/baseline-files.nul"
make_file_list "$SNAPSHOT_DIR/enforcement" "$SNAPSHOT_DIR/enforcement-files.nul"

(
    cd "$SNAPSHOT_DIR/baseline"
    xargs -0 "$RADON" cc -s -a \
        < "$SNAPSHOT_DIR/baseline-files.nul" \
        > "$RAW_OUT/baseline_radon.txt"
    xargs -0 "$RADON" cc -j \
        < "$SNAPSHOT_DIR/baseline-files.nul" \
        > "$SNAPSHOT_DIR/baseline_radon.json"
)

(
    cd "$SNAPSHOT_DIR/enforcement"
    xargs -0 "$RADON" cc -s -a \
        < "$SNAPSHOT_DIR/enforcement-files.nul" \
        > "$RAW_OUT/enforcement_radon.txt"
    xargs -0 "$RADON" cc -j \
        < "$SNAPSHOT_DIR/enforcement-files.nul" \
        > "$SNAPSHOT_DIR/enforcement_radon.json"
)

"$PYTHON" - \
    "$SNAPSHOT_DIR/baseline_radon.json" \
    "$SNAPSHOT_DIR/enforcement_radon.json" \
    "$ANALYSIS_OUT/complexity_results.md" \
    "$BASE_REF" \
    "$BASE_HASH" \
    "$SECURE_REF" \
    "$SECURE_HASH" <<'PY'
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from radon.complexity import cc_rank


def summarize(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    blocks = [
        block
        for records in data.values()
        if isinstance(records, list)
        for block in records
        if "complexity" in block
    ]
    values = [int(block["complexity"]) for block in blocks]
    return {
        "count": len(values),
        "average": sum(values) / len(values) if values else 0,
        "maximum": max(values, default=0),
        "ranks": Counter(cc_rank(value) for value in values),
        "important": sorted(
            (
                (cc_rank(int(block["complexity"])), int(block["complexity"]), block["name"])
                for block in blocks
                if int(block["complexity"]) >= 6
            ),
            key=lambda item: (-item[1], item[2]),
        ),
    }


baseline_path, enforcement_path, output_path = map(Path, sys.argv[1:4])
base_ref, base_hash, secure_ref, secure_hash = sys.argv[4:8]
baseline = summarize(baseline_path)
enforcement = summarize(enforcement_path)

lines = [
    "# Complexity Results",
    "",
    "## Compared versions",
    "",
    f"- Baseline: `{base_ref}` at `{base_hash}`",
    f"- Enforcement: `{secure_ref}` at `{secure_hash}`",
    "",
    "## Cyclomatic complexity",
    "",
    "| Metric | Baseline | Enforcement | Difference |",
    "|---|---:|---:|---:|",
    (
        f"| Analyzed blocks | {baseline['count']} | {enforcement['count']} | "
        f"{enforcement['count'] - baseline['count']:+d} |"
    ),
    (
        f"| Average complexity | {baseline['average']:.2f} | "
        f"{enforcement['average']:.2f} | "
        f"{enforcement['average'] - baseline['average']:+.2f} |"
    ),
    (
        f"| Maximum complexity | {baseline['maximum']} | "
        f"{enforcement['maximum']} | "
        f"{enforcement['maximum'] - baseline['maximum']:+d} |"
    ),
]

for rank in "ABCDEF":
    base_count = baseline["ranks"].get(rank, 0)
    secure_count = enforcement["ranks"].get(rank, 0)
    lines.append(
        f"| Rank {rank} blocks | {base_count} | {secure_count} | "
        f"{secure_count - base_count:+d} |"
    )

lines.extend(
    [
        "",
        "## Enforcement Blocks Ranked B or Higher",
        "",
        "| Rank | Score | Function or class |",
        "|---|---:|---|",
    ]
)

for rank, score, name in enforcement["important"]:
    lines.append(f"| {rank} | {score} | `{name}` |")

lines.extend(
    [
        "",
        "Most blocks remain Rank A. Radon measures control flow inside individual",
        "functions and classes; it does not measure all cross-layer complexity.",
        "",
    ]
)

output_path.write_text("\n".join(lines), encoding="utf-8")
PY

echo "Complexity comparison completed."
echo "Read: comparison_metrics/analysis/complexity_results.md"
