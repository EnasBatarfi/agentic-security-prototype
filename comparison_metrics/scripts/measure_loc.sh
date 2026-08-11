#!/usr/bin/env bash

# Compare production code size and keep test work separate

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
BASE_REF="impl/baseline"
SECURE_REF="impl/application-policy-enforcement"
ANALYSIS_OUT="$ROOT/comparison_metrics/analysis"
RAW_OUT="$ROOT/comparison_metrics/outputs"

cd "$ROOT"

command -v cloc >/dev/null 2>&1 || {
    echo "cloc is not installed. Install it with: brew install cloc"
    exit 1
}

BASE_HASH="$(git rev-parse "$BASE_REF")"
SECURE_HASH="$(git rev-parse "$SECURE_REF")"

# Use clean committed snapshots so working-tree files are not counted.
SNAPSHOT_DIR="$(mktemp -d)"
trap 'rm -rf "$SNAPSHOT_DIR"' EXIT

mkdir -p "$SNAPSHOT_DIR/baseline" "$SNAPSHOT_DIR/enforcement"
git archive "$BASE_HASH" | tar -x -C "$SNAPSHOT_DIR/baseline"
git archive "$SECURE_HASH" | tar -x -C "$SNAPSHOT_DIR/enforcement"

# Count changed production Python files and physical lines.
git diff --numstat "$BASE_HASH..$SECURE_HASH" \
    -- apps mcp_client mcp_server config \
    | while IFS=$'\t' read -r added deleted file_path; do
        [[ "$added" =~ ^[0-9]+$ ]] || continue
        [[ "$deleted" =~ ^[0-9]+$ ]] || continue
        [[ "$file_path" == *.py ]] || continue
        [[ "$file_path" == */migrations/* ]] && continue
        [[ "$file_path" == */tests/* ]] && continue
        [[ "$(basename "$file_path")" == "tests.py" ]] && continue

        # Manual review confirmed that this is only a final-newline change.
        [[ "$file_path" == "apps/conversations/models.py" ]] && continue

        printf '%s\t%s\t%s\n' "$added" "$deleted" "$file_path"
    done > "$RAW_OUT/production_files.tsv"

# Test changes are useful supporting effort but are not production LoC.
git diff --numstat "$BASE_HASH..$SECURE_HASH" -- tests \
    | while IFS=$'\t' read -r added deleted file_path; do
        [[ "$added" =~ ^[0-9]+$ ]] || continue
        [[ "$deleted" =~ ^[0-9]+$ ]] || continue
        [[ "$file_path" == *.py ]] || continue
        printf '%s\t%s\t%s\n' "$added" "$deleted" "$file_path"
    done > "$RAW_OUT/verification_files.tsv"

# Build the same production file list for cloc in both snapshots.
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
        | LC_ALL=C sort > "$output"
}

make_file_list "$SNAPSHOT_DIR/baseline" "$SNAPSHOT_DIR/baseline-files.txt"
make_file_list "$SNAPSHOT_DIR/enforcement" "$SNAPSHOT_DIR/enforcement-files.txt"

cloc \
    --list-file="$SNAPSHOT_DIR/baseline-files.txt" \
    --include-lang=Python \
    --out="$RAW_OUT/baseline_cloc.txt"

cloc \
    --list-file="$SNAPSHOT_DIR/enforcement-files.txt" \
    --include-lang=Python \
    --out="$RAW_OUT/enforcement_cloc.txt"

read -r PROD_FILES PROD_ADDED PROD_DELETED < <(
    awk -F '\t' '
        { files += 1; added += $1; deleted += $2 }
        END { print files, added, deleted }
    ' "$RAW_OUT/production_files.tsv"
)

read -r TEST_FILES TEST_ADDED TEST_DELETED < <(
    awk -F '\t' '
        { files += 1; added += $1; deleted += $2 }
        END { print files, added, deleted }
    ' "$RAW_OUT/verification_files.tsv"
)

read -r BASE_FILES BASE_BLANK BASE_COMMENT BASE_CODE < <(
    awk '$1 == "SUM:" { print $2, $3, $4, $5 }' "$RAW_OUT/baseline_cloc.txt"
)

read -r SECURE_FILES SECURE_BLANK SECURE_COMMENT SECURE_CODE < <(
    awk '$1 == "SUM:" { print $2, $3, $4, $5 }' "$RAW_OUT/enforcement_cloc.txt"
)

CODE_PERCENT="$(awk -v base="$BASE_CODE" -v secure="$SECURE_CODE" \
    'BEGIN { printf "%.1f", ((secure - base) / base) * 100 }')"

cat > "$ANALYSIS_OUT/loc_results.md" <<EOF
# Lines of Code Results

## Compared versions

- Baseline: \`$BASE_REF\` at \`$BASE_HASH\`
- Enforcement: \`$SECURE_REF\` at \`$SECURE_HASH\`

## Final production size

| Metric | Baseline | Enforcement | Difference |
|---|---:|---:|---:|
| Python files | $BASE_FILES | $SECURE_FILES | +$((SECURE_FILES - BASE_FILES)) |
| Code lines | $BASE_CODE | $SECURE_CODE | +$((SECURE_CODE - BASE_CODE)) (+$CODE_PERCENT%) |
| Comment lines | $BASE_COMMENT | $SECURE_COMMENT | +$((SECURE_COMMENT - BASE_COMMENT)) |
| Blank lines | $BASE_BLANK | $SECURE_BLANK | +$((SECURE_BLANK - BASE_BLANK)) |

## Physical production changes

| Metric | Result |
|---|---:|
| Production files changed | $PROD_FILES |
| Lines inserted | $PROD_ADDED |
| Lines deleted | $PROD_DELETED |
| Net change | $((PROD_ADDED - PROD_DELETED)) |

## Supporting test changes

| Metric | Result |
|---|---:|
| Python test files changed | $TEST_FILES |
| Lines inserted | $TEST_ADDED |
| Lines deleted | $TEST_DELETED |
| Net change | $((TEST_ADDED - TEST_DELETED)) |

Git counts physical lines, including comments and blanks. \`cloc\` measures
final code size. Tests are shown separately and are not included in the
production totals.
EOF

echo "LoC comparison completed."
echo "Read: comparison_metrics/analysis/loc_results.md"
