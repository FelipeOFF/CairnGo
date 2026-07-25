#!/usr/bin/env bash
# Thin wrapper around the cairn migration engine. See cairn-migrate.py for
# the full contract (detect / plan / apply, exit codes, plan-file shape).
# Usage: cairn-migrate.sh detect [--project-dir D] [--json]
#        cairn-migrate.sh plan   [--mode A|B|C] [--milestone M] [--force]
#                                [--project-dir D]
#        cairn-migrate.sh apply  [--plan FILE] [--yes] [--project-dir D]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-migrate.py" "$@"
