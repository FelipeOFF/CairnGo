#!/usr/bin/env bash
# Thin wrapper around the cairn landing report. See cairn-land.py for the
# contract: did this phase's work enter the control branch, and which PR took
# it there. Local git only — no network on any path this script reaches.
# Usage: cairn-land.sh {detect | apply --branches a,b | report}
#                      [--project-dir DIR] [--planning-dir DIR] [--json]
# Exit:  0 ok, 2 usage / unresolvable branch, 3 nothing to write,
#        5 cairn-config.py unavailable.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-land.py" "$@"
