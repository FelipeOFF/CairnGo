#!/usr/bin/env bash
# Thin wrapper around cairn-stop.py: request [--phase N] [--reason T] | check [--phase N] | clear
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-stop.py" "$@"
