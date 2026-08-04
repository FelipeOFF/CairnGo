#!/usr/bin/env bash
# Thin wrapper around cairn's own settings. See cairn-config.py for the
# contract (and for why the file lives in .cairn/ rather than in
# .planning/config.json).
# Usage: cairn-config.sh {get <key>|set <key> <value>}
#                        [--project-dir DIR] [--json]
# Exit:  0 ok, 2 usage error or unknown key, 3 invalid value for the key's
#        type (nothing written) or unreadable config JSON.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-config.py" "$@"
