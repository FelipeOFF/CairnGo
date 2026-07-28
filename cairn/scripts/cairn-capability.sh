#!/usr/bin/env bash
# Thin wrapper around the cairn capability installer/verifier. See
# cairn-capability.py for the contract.
# Usage: cairn-capability.sh detect|install [--project-dir <dir>]
#        [--gsd-bin <path>] [--capability-dir <dir>] [--json]
# Exit:  0 registered and completely staged, 2 usage, 5 GSD unavailable,
#        7 failure (legacy lineage, install failed, or did not register).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-capability.py" "$@"
