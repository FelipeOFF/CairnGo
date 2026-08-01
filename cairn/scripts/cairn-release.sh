#!/usr/bin/env bash
# Thin wrapper around the cairn version-carrier check. See cairn-release.py
# for the contract, including why capability.json is exempt from the equality
# set but not from semver validity (Phase 19, D-02).
# Usage: cairn-release.sh check [--project-dir DIR] [--json] [--require-tag]
# Exit:  0 every lockstep carrier agrees and every carrier is valid semver
#          (an uncreated git tag is 'pending', not a failure),
#        2 usage, 6 findings — a mismatch, an invalid semver, a missing or
#          unparsable carrier, or an absent tag under --require-tag.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-release.py" "$@"
