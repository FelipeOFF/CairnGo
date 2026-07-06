#!/usr/bin/env bash

########################
# Script by John Reed  #
# cairn usage stats    #
########################

#***************************************************************************
# Pulls every usage signal cairn has into one view:
#   1. npm downloads (once published)     — api.npmjs.org (public)
#   2. GitHub release asset downloads      — real tarball grabs (public)
#   3. opt-in install beacon               — release-asset download_count
#   4. GitHub 14-day traffic (owner-only)  — clones/views (needs gh auth)
# Read-only. Needs: curl, and `gh` authed as the repo owner for section 4.
#***************************************************************************

set -uo pipefail

# Constants
REPO="BigJiggity/claude-plugins"
NPM_PKG="@eventually-consistent/cairn"
NPM_PKG_ENC="@eventually-consistent%2Fcairn"
BEACON_TAG="install-beacon"
BEACON_ASSET="beacon"

echo "***************************"
echo "*   cairn usage stats     *"
echo "***************************"
echo

# 1. npm downloads --------------------------------------------------------
echo "# npm downloads ($NPM_PKG)"
npm_json="$(curl -fsSL "https://api.npmjs.org/downloads/point/last-month/$NPM_PKG_ENC" 2>/dev/null || true)"
if echo "$npm_json" | grep -q '"downloads"'; then
  echo "  last 30 days: $(echo "$npm_json" | grep -o '"downloads":[0-9]*' | head -1 | cut -d: -f2)"
else
  echo "  not published yet (run: npm publish) — no data."
fi
echo

# 2. release asset downloads (real tarball grabs) -------------------------
echo "# GitHub release downloads (tarball)"
if command -v gh >/dev/null 2>&1; then
  gh api "repos/$REPO/releases" \
    --jq '.[] | select(.tag_name != "'"$BEACON_TAG"'") | .assets[] | "  \(.name): \(.download_count)"' \
    2>/dev/null || echo "  none yet."
else
  echo "  gh not found — skipping."
fi
echo

# 3. opt-in install beacon ------------------------------------------------
echo "# opt-in install beacon (approx installs)"
if command -v gh >/dev/null 2>&1; then
  count="$(gh api "repos/$REPO/releases/tags/$BEACON_TAG" \
    --jq '.assets[] | select(.name=="'"$BEACON_ASSET"'") | .download_count' 2>/dev/null || true)"
  if [ -n "${count:-}" ]; then
    echo "  beacon downloads: $count  (opt-in pings; coarse — see PRIVACY.md)"
  else
    echo "  beacon release not found — create it (see README > Telemetry & stats)."
  fi
else
  echo "  gh not found — skipping."
fi
echo

# 4. GitHub 14-day traffic (owner-only) -----------------------------------
echo "# GitHub traffic (rolling 14 days, owner-only)"
if command -v gh >/dev/null 2>&1; then
  clones="$(gh api "repos/$REPO/traffic/clones" --jq '"\(.count) total / \(.uniques) unique"' 2>/dev/null || echo "n/a (need owner auth)")"
  views="$(gh api "repos/$REPO/traffic/views"  --jq '"\(.count) total / \(.uniques) unique"' 2>/dev/null || echo "n/a")"
  echo "  clones: $clones"
  echo "  views:  $views"
  echo "  note: clones are inflated by your own dev machines + Claude Code re-installs."
else
  echo "  gh not found — skipping."
fi
echo
echo "stats done."
