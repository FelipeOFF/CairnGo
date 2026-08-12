#!/usr/bin/env bash
# Thin wrapper around the trivial-family GSD dispatcher. See cairn-gsd.py for
# the contract (and for the declared resolution chain of the config defaults
# manifest).
# Usage: cairn-gsd.sh <spelling do verbo> [argv do verbo]
#        e.g. cairn-gsd.sh query config-get <key.path> [--default <v>] [--raw]
# Exit:  0/1 per the verb's own contract (cairn/gsd/contracts/). 2 dispatcher
#        usage error — unknown dispatcher flag, or a token outside the
#        contract universe. 4 the verb belongs to a family this script does
#        not serve yet; stderr names the family and the delivering phase.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-gsd.py" "$@"
