#!/usr/bin/env bash
# Thin wrapper around the cairn transition journal. See cairn-journal.py for
# the contract.
# Usage: cairn-journal.sh {observe|lease N {acquired|released}|history|
#                          last-moved|compact} [--project-dir DIR] [--json]
# Exit:  0 ok (includes every compact outcome: no journal, compacted,
#        lock-contended skip, aborted-stale-read defer), 2 usage,
#        4 short/failed write during append.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-journal.py" "$@"
