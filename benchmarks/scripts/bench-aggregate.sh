#!/usr/bin/env bash
# Thin wrapper around the bench-aggregate statistics layer. See
# bench-aggregate.py for the contract.
# Usage: bench-aggregate.sh --in <jsonl> [--in <jsonl> ...] --out <aggregated.json>
# Exit codes: 0 aggregation completed, 2 usage error
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/bench-aggregate.py" "$@"
