#!/usr/bin/env bash
# verify.sh <workdir> -- exit 0 = task solved, non-zero = not solved.
# Never staged inside <workdir>; invoked with its path as an argument.
set -euo pipefail
WORKDIR="$1"
cd "$WORKDIR"
exec python3 -m unittest tests.test_convert -v
