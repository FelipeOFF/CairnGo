#!/usr/bin/env bash
# Thin wrapper around the bats suite runner. See cairn-test.py for the
# contract (and for the measurement that inverts the obvious requirement:
# `bats -j` without GNU parallel executes ZERO tests and exits 1, so the
# absence is detected BEFORE the command is composed, not after).
# Usage: cairn-test.sh [--jobs N] [--print-command] [--project-dir DIR]
#                      [paths...]
# Exit:  0 suite passed, 2 usage error (bad flag, job count below 1, or a
#        path that does not exist), 5 bats not on PATH. Codes 2 and 5 are
#        this runner's own and can only be emitted BEFORE bats is invoked;
#        every other code is bats' own, passed through untranslated — even
#        when bats itself exits 2 or 5, in which case a line on stderr names
#        the origin.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-test.py" "$@"
