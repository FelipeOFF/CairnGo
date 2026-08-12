#!/usr/bin/env bash
# Thin wrapper around the golden recorder for the GSD differential harness.
# See cairn-gsd-record.py for the contract (gate order, atomic golden writes,
# and why an unverified cache HEAD is refused rather than recorded from).
# Usage: cairn-gsd-record.sh [--cache-dir <dir>] [--source <url|path>]
#                            [--expect-commit <sha>] [--only <scenario-id>]
#                            [--scenarios <file>] [--goldens-dir <dir>]
# Exit:  0 ok — goldens recorded from the real binary. 2 usage error.
#        5 a dependency is unavailable — node is missing, or the runtime
#        build of the clone failed. 6 invalid corpus/manifest — the cache
#        HEAD does not match the pinned tag commit, a scenario is missing,
#        or a mask does not match; nothing is recorded in any of these.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-gsd-record.py" "$@"
