#!/usr/bin/env bash
# Thin wrapper around the cairn consistency doctor. See cairn-doctor.py for
# the contract.
# Usage: cairn-doctor.sh [--project-dir <dir>] [--json] [--fix-labels]
# Exit:  0 all ok / warnings only / not applicable, 2 usage or refused
#        --fix-labels, 5 bd unavailable, 7 at least one check failed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-doctor.py" "$@"
