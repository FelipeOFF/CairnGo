#!/usr/bin/env bash
# Thin wrapper around the semantic escalation collector/citation checker.
# See cairn-reconcile.py for the contract.
# Usage: cairn-reconcile.sh collect <N> [--json] [--out PATH] [--project-dir DIR]
#        cairn-reconcile.sh verify <N>  [--file PATH] [--json] [--project-dir DIR]
# Exit:  0 ok, 2 usage, 3 not conflicted (collect's ESC-04 gate),
#        4 invalid proposal (verify — one bad citation rejects the whole
#        proposal).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-reconcile.py" "$@"
