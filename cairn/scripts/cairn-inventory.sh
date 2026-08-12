#!/usr/bin/env bash
# Thin wrapper around the pinned-tag corpus inventory. See cairn-inventory.py
# for the contract (and for why a cache whose HEAD is not the pinned tag
# commit is refused with both shas named rather than measured).
# Usage: cairn-inventory.sh [--json] [--cache-dir <dir>] [--source <url|path>]
#                           [--expect-commit <sha>] [--refresh]
#        cairn-inventory.sh closure [--json] [--write <path>] [corpus flags]
#        cairn-inventory.sh vendor [--manifest <path>] [--dest <dir>]
#                           [corpus flags]
# Exit:  0 ok — the corpus was measured. 2 usage error. 5 a dependency is
#        unavailable — git is missing, or the clone failed and there is no
#        cache to fall back on. 6 invalid corpus — the cache HEAD does not
#        match the pinned tag commit; the inventory never measures an
#        unverified corpus.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-inventory.py" "$@"
