#!/usr/bin/env bash
# verify.sh <workdir> -- exit 0 = task solved, non-zero = not solved.
set -euo pipefail
WORKDIR="$1"
cd "$WORKDIR"
exec python3 -m unittest tests.test_pipeline -v
