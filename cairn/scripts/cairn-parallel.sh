#!/usr/bin/env bash
# Thin wrapper around the cairn parallel-phase driver. See cairn-parallel.py
# for the contract.
# Usage: cairn-parallel.sh {batch [--max N]|prepare N|reconcile [--phases
#                          7,9]} [--project-dir DIR] [--json]
# Exit:  0 ok, 2 usage, 3 phase lease held by another live holder (nothing
#        created / everything this run created was rolled back), 4 git
#        refused (path occupied, branch already exists, worktree add failed),
#        5 bd or a companion cairn script unavailable, 6 reconcile has
#        findings: a convergent edit, a merge conflict, or a git too old to
#        pre-compute conflicts at all — a report the caller cannot mistake
#        for success, never a resolution.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-parallel.py" "$@"
