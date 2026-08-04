#!/usr/bin/env bash
# Thin wrapper around cairn's planning bookkeeper. See cairn-bookkeep.py for
# the contract.
# Usage: cairn-bookkeep.sh close <phase-number> [--apply] [--no-tracker]
#                               [--json] [--planning-dir <dir>]
#        cairn-bookkeep.sh reconcile [--apply] [--json] [--planning-dir <dir>]
# Exit:  0 ok / nothing to change, 2 usage, ambiguous phase number or two
#        coverage footers, 3 read mode found something to change,
#        4 no such phase, 5 bd not on PATH and --no-tracker not passed
#        (refused BEFORE writing: the three files are byte-identical).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-bookkeep.py" "$@"
