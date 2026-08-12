#!/usr/bin/env bash
# Thin wrapper around the Jira ask/answer decision. See cairn-jira.py for the
# contract (and for why detection is NOT implemented here: cairn-migrate.py is
# the only Jira detector, and this script is a consumer of it).
# Usage: cairn-jira.sh detect [--project-dir DIR] [--json]
#        cairn-jira.sh apply --key PREFIX [--base-url URL]
#                            [--project-dir DIR] [--json]
#        cairn-jira.sh decline [--project-dir DIR] [--json]
# Exit:  0 ok, 2 usage error (or no derivable base_url), 3 that same answer is
#        already on record (nothing rewritten), 5 the detector or the config
#        owner is unavailable. `detect` never exits 3 — it is a report.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-jira.py" "$@"
