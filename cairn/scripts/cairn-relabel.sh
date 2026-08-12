#!/usr/bin/env bash
# Thin wrapper around the cairn-relabel tool. See cairn-relabel.py for the
# contract. Usage:
#   cairn-relabel.sh pair --milestone <m> [--phase <N>] [--dry-run]
#   cairn-relabel.sh renumber --from <N> --to <M> [--milestone <m>] [--force]
#                             [--dry-run]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-relabel.py" "$@"
