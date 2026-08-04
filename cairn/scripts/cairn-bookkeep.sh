#!/usr/bin/env bash
# Thin wrapper around cairn's planning bookkeeper. See cairn-bookkeep.py for
# the contract.
# Usage: cairn-bookkeep.sh close <phase-number> [--apply] [--json]
#                               [--planning-dir <dir>]
# Exit:  0 ok / nothing to change, 2 usage or ambiguous phase number,
#        3 read mode found something to change, 4 no such phase,
#        5 RESERVED for bd unavailable (never returned yet — the tracker
#        path is plan 29-02).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-bookkeep.py" "$@"
