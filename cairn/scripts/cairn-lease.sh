#!/usr/bin/env bash
# Thin wrapper around the cairn phase lease. See cairn-lease.py for the
# contract.
# Usage: cairn-lease.sh {acquire N|release N|renew [N]|status N|status --all
#                        |release --mine} [--project-dir DIR] [--json]
# Exit:  0 ok (including not-held/no-op outcomes), 2 usage, 3 acquire-only
#        "held by another live holder" (nothing written), 5 bd unavailable.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-lease.py" "$@"
