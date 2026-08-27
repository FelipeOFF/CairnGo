#!/usr/bin/env bash
# Thin wrapper around cairn-board.py. See its docstring for the contract.
#   cairn-board.sh start [--port N] [--open] | stop | open | status | serve --port N
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-board.py" "$@"
