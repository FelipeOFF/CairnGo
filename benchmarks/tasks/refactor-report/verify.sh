#!/usr/bin/env bash
# verify.sh <workdir> -- exit 0 = task solved, non-zero = not solved.
# Runs the behavior tests AND an anti-cheat structural check: the duplicated
# `total += r["amount"]` accumulation line must be deduplicated to at most
# one occurrence (it appears 3 times in the unrefactored fixture — one per
# function). Passing the behavior tests alone is never enough: the raw
# fixture already passes them (the duplication is functionally correct), so
# this second check is what actually proves extraction happened.
set -euo pipefail
WORKDIR="$1"
cd "$WORKDIR"
python3 -m unittest tests.test_report -v

DUP_COUNT=$(grep -v '^\s*#' report.py | grep -cF 'total += r["amount"]' || true)
if [ "$DUP_COUNT" -gt 1 ]; then
  echo "anti-cheat: 'total += r[\"amount\"]' still appears $DUP_COUNT times in report.py (expected <=1 after extracting a shared helper)" >&2
  exit 1
fi
echo "anti-cheat: duplication check passed ($DUP_COUNT occurrence(s))"
