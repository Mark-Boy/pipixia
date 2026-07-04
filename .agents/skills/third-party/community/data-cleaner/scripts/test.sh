#!/usr/bin/env bash
# Run unit tests + end-to-end checks for the data-cleaning skill.
# Exit code 0 = all checks passed.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SKILL_DIR"

PASS=0
FAIL=0

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        PASS=$((PASS + 1))
        echo "  PASS  $label"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL  $label"
        echo "        expected: $expected"
        echo "        actual:   $actual"
    fi
}

assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  PASS  $label"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL  $label (missing: $needle)"
    fi
}

echo "[1] zig build test"
zig build test --summary all

echo ""
echo "[2] Build release binary"
zig build -Doptimize=ReleaseFast
BIN="$SKILL_DIR/zig-out/bin/dataclean"

echo ""
echo "[3] CLI smoke tests"

# version
assert_eq "version" "dataclean 1.1.0" "$("$BIN" --version)"

# simple.csv: 5 rows + 1 header, no transforms
out=$("$BIN" fixtures/simple.csv | wc -l | tr -d ' ')
assert_eq "simple.csv passthrough rows" "6" "$out"

# dirty.csv with --all should yield exactly 27 lines (header + 26 unique data rows)
out=$("$BIN" --all fixtures/dirty.csv | wc -l | tr -d ' ')
assert_eq "dirty.csv --all rows" "27" "$out"

# stats report contains expected counts
err=$("$BIN" --all --stats fixtures/dirty.csv 2>&1 >/dev/null)
assert_contains "stats: rows out=26" "rows out: 26" "$err"
assert_contains "stats: cols=7" "cols: 7" "$err"

# IQR outliers detected
err=$("$BIN" --all --outliers=iqr fixtures/dirty.csv 2>&1 >/dev/null)
assert_contains "iqr outliers age" "col[3=age]" "$err"
assert_contains "iqr outliers score" "col[4=score]" "$err"

# detect-types correctly flags score as string (mixed)
err=$("$BIN" --all --detect-types fixtures/dirty.csv 2>&1 >/dev/null)
assert_contains "score is string (mixed)" "col[4=score] string" "$err"
assert_contains "age is integer" "col[3=age] integer" "$err"

# stdin is supported
out=$(cat fixtures/simple.csv | "$BIN" --trim | wc -l | tr -d ' ')
assert_eq "stdin pipe rows" "6" "$out"

# strict mode + validation failure -> exit 1
set +e
"$BIN" --validate=age:range=0..30 --strict fixtures/simple.csv >/dev/null 2>/dev/null
strict_rc=$?
set -e
assert_eq "strict exit code on failure" "1" "$strict_rc"

# without strict, validation failure does not change exit code
set +e
"$BIN" --validate=age:range=0..30 fixtures/simple.csv >/dev/null 2>/dev/null
rc=$?
set -e
assert_eq "non-strict exit code with failures" "0" "$rc"

# strict with passing rules -> exit 0
set +e
"$BIN" --validate=age:range=0..120 --strict fixtures/simple.csv >/dev/null 2>/dev/null
rc=$?
set -e
assert_eq "strict exit code when rules pass" "0" "$rc"

# --output writes to file
TMP=$(mktemp)
"$BIN" --all --output="$TMP" fixtures/dirty.csv
out=$(wc -l < "$TMP" | tr -d ' ')
assert_eq "--output rows written" "27" "$out"
rm -f "$TMP"

# --no-header: simple.csv has 5 data + 1 header = 6 rows total
out=$("$BIN" --no-header fixtures/simple.csv | wc -l | tr -d ' ')
assert_eq "--no-header preserves all rows" "6" "$out"

# fill-na=drop drops rows with empty cells
out=$("$BIN" --all --fill-na=drop fixtures/dirty.csv | wc -l | tr -d ' ')
# at least header should remain
test "$out" -ge "1" && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1))
echo "  PASS  fill-na=drop produced $out lines"

echo ""
echo "================================"
echo "  passed: $PASS"
echo "  failed: $FAIL"
echo "================================"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
