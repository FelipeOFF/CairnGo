#!/usr/bin/env bash
# Thin wrapper around the bench-run harness. See bench-run.py for the contract.
# Usage: bench-run.sh --task <dir> --baseline <manifest.json> --out <path>
#        [--seed <int> --run-order-index <int>]
# Exit codes: 0 run completed, 2 usage error
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/bench-run.py" "$@"
