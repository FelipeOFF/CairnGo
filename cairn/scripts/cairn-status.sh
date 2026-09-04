#!/usr/bin/env bash
# Thin wrapper around the cairn-status board renderer. See cairn-status.py for the contract.
# Usage: cairn-status.sh [--json] [--plain] [--brief] [--width N] [--max-rows N]
#        [--ascii] [--color=always|never]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-status.py" "$@"
