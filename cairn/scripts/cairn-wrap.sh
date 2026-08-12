#!/usr/bin/env bash
# Thin wrapper around the cairn wrapper tooling. See cairn-wrap.py for the
# contract.
# Usage: cairn-wrap.sh preflight <gsd-command> [--json]
#        cairn-wrap.sh list [--commands-dir <dir>] [--json]
#        cairn-wrap.sh docs [--check] [--commands-dir <dir>] [--doc <file>]
#                           [--doc-pages-dir <dir>] [--json]
# Exit:  0 ok, 2 usage, 3 docs stale (--check), 5 GSD unavailable (could not
#        look), 6 the named GSD command is missing (looked, not there).
#        5 and 6 are BOTH failures for a wrapper — see the .py docstring for
#        why 5 here does not inherit the "callers must not block on 5" rule.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-wrap.py" "$@"
