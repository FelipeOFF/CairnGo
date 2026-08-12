#!/usr/bin/env bash
# Thin wrapper around the cairn-gate checks. See cairn-loop-gate.py for the contract.
# Usage: cairn-loop-gate.sh ship-gate [--phase N] [--milestone M] [--project-dir DIR]
#        cairn-loop-gate.sh verify-cross <phase> [--milestone M] [--project-dir DIR]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-loop-gate.py" "$@"
