#!/usr/bin/env bash
# Thin wrapper around the vendored-preamble rewriter. See cairn-preamble.py
# for the contract — including the loud declaration that this is the one
# script in the house that WRITES under cairn/gsd/, and only on the preamble
# line of paths registered in cairn/gsd-adaptations.json.
# Usage: cairn-preamble.sh --print-form
#        cairn-preamble.sh list  [--root <dir>] [--registry <path>] [--json]
#        cairn-preamble.sh check [<path>...] [--root <dir>] [--registry <path>]
#        cairn-preamble.sh apply [<path>...] [--root <dir>] [--registry <path>]
# Exit:  0 ok. 2 usage, or a named refusal (path outside cairn/gsd/, a
#        protected path, a path absent from the registry). 3 stale — some
#        registered path still carries the old form, the same meaning
#        cairn-map.py --check and cairn-wrap.py --check give the 3.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-preamble.py" "$@"
