#!/usr/bin/env bash
# Thin wrapper around the cairn pull-request review fetch. See cairn-review.py
# for the contract. THIS IS THE ONLY CAIRN SCRIPT THAT TALKS TO THE NETWORK,
# and only when `git.review_state` says which tool to use — the default is
# `off`. The board never invokes it.
# Usage: cairn-review.sh {fetch [--pr N] | show} [--project-dir DIR] [--json]
# Exit:  0 ok, 2 usage, 3 nothing to do (the switch is off, or no PR to ask
#        about), 5 a helper or the gh/glab it names is unavailable.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-review.py" "$@"
