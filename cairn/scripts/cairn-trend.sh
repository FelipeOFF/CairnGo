#!/usr/bin/env bash
# Thin wrapper around the cross-cycle trend reader. See cairn-trend.py for
# the contract (and for why a cycle with no comparable verdict is
# `not-applicable` with a named scope rather than a zero).
# Usage: cairn-trend.sh [--planning-dir <dir>] [--json]
# Exit:  0 ok — the cycles were read, including a repo with no .planning/,
#        2 usage error, 4 insufficient — fewer comparable cycles than a
#        series needs, so no direction is declared. 4 is a verdict and not a
#        failure: it is the roadmap's own "say so instead of drawing a line".
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-trend.py" "$@"
