#!/usr/bin/env bash
# Thin wrapper around the gbsync dispatcher. See gbsync.py for the contract.
# Usage: gbsync.sh <create|update|close> <bd_id> | pull [--since <iso>]
#        [--dir <dir>] [--dry-run]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/gbsync.py" "$@"
