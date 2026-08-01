#!/usr/bin/env bash
# Thin wrapper around the cairn version-carrier check and the release-notes
# derivation. See cairn-release.py for the contract, including why
# capability.json is exempt from the equality set but not from semver validity
# (Phase 19, D-02), and why `notes` cuts the CHANGELOG instead of writing prose
# a second time (REL-03).
# Usage: cairn-release.sh check [--project-dir DIR] [--json] [--require-tag]
#        cairn-release.sh notes VERSION [--project-dir DIR]
# Exit:  0 check: every lockstep carrier agrees and every carrier is valid
#          semver (an uncreated git tag is 'pending', not a failure);
#          notes: the section was found and printed with its migration answer,
#        2 usage (unknown subcommand, bad flag, `notes` with no version),
#        6 findings — a mismatch, an invalid semver, a missing or unparsable
#          carrier, an absent tag under --require-tag, or (notes) a CHANGELOG
#          section that does not exist or carries no migration answer.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-release.py" "$@"
