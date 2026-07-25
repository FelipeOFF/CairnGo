#!/usr/bin/env bash
# Thin wrapper around the cairn ship gate. See cairn-gate.py for the contract.
# Usage: cairn-gate.sh [--planning-dir <dir>] [--json]
# Exit:  0 clear / not applicable, 2 usage, 5 bd unavailable (never blocks
#        a push), 6 gate failed (the only code the pre-push shim blocks on).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-gate.py" "$@"
