#!/usr/bin/env bash

########################
# Script by John Reed  #
# cairn install beacon #
########################

#***************************************************************************
# cairn opt-in install beacon — GitHub-native, no server.
#
# Fires ONE anonymous GET at a GitHub release-asset "beacon". GitHub bumps that
# asset's download_count on the fetch; the author reads back only that aggregate
# integer. Nothing else leaves your machine — no IP logged by the author, no
# repo name, no identifiers, no per-event record. Off unless you opt in via
# /cairn:init (which writes .cairn/telemetry.json with "enabled": true).
#***************************************************************************

set -euo pipefail

# Constants
BEACON_URL="https://github.com/eventually-consistent-code/claude-plugins/releases/download/install-beacon/beacon"
PROJECT_DIR="${1:-$PWD}"
CFG="$PROJECT_DIR/.cairn/telemetry.json"
MARKER="$PROJECT_DIR/.cairn/.beacon-sent"

# Opt-in gate — silently do nothing unless telemetry.json says enabled:true.
[ -f "$CFG" ] || exit 0
grep -q '"enabled"[[:space:]]*:[[:space:]]*true' "$CFG" || exit 0

# Once-per-install guard — don't re-count on every /cairn:init re-run.
[ -f "$MARKER" ] && exit 0

# Fire and forget — a short timeout and `|| true` so this NEVER blocks or fails
# setup. A miss just means one uncounted install; that's the coarse-by-design
# tradeoff of the server-free approach.
echo "sending anonymous install ping..."
curl -fsSL --max-time 5 -o /dev/null "$BEACON_URL" >/dev/null 2>&1 || true
touch "$MARKER"
echo "ping sent. thanks — turn it off anytime by setting \"enabled\": false in .cairn/telemetry.json"

exit 0
