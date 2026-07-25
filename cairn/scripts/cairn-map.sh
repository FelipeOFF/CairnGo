#!/usr/bin/env bash
# Thin wrapper around the cairn-map generator. See cairn-map.py for the contract.
# Usage: cairn-map.sh <phase-number> [--milestone <m>] [--planning-dir <dir>]
#        [--check] [--json]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-map.py" "$@"
