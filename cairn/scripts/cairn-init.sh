#!/usr/bin/env bash

########################
# Script by John Reed  #
# cairn-init           #
########################

# cairn-init — the deterministic half of /cairn:init.
# Wires git + beads so the cairn integration can activate. GSD arrives as a
# declared plugin dependency, and installing the bd binary (if missing) is the
# interactive job of the /cairn:init command — this script assumes bd is already
# on PATH and stops with guidance if it isn't.
# GSD's own .planning/ is created interactively by /gsd:new-project inside Claude.
#
# Usage:  cairn-init.sh [target-dir]   (defaults to current dir)
set -euo pipefail

DIR="${1:-$PWD}"
cd "$DIR"
echo "▸ bootstrapping GSD<->beads in: $DIR"

# 1. git repo
if [ -d .git ]; then
  echo "  ✓ git repo already present"
else
  git init -q
  echo "  ✓ git init"
fi

# 2. beads binary must be present (install is handled by /cairn:init first)
if ! command -v bd >/dev/null 2>&1; then
  echo "  ✗ 'bd' not on PATH — install beads, then re-run:" >&2
  echo "      brew install beads        # macOS / Linux (recommended)" >&2
  echo "      npm install -g @beads/bd  # Node.js users" >&2
  echo "      curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash" >&2
  exit 1
fi

# 3. beads project
if [ -d .beads ]; then
  echo "  ✓ .beads/ already present"
else
  bd init
  echo "  ✓ bd init"
fi

# 4. GSD presence — soft check; it ships as a cairn plugin dependency
if command -v claude >/dev/null 2>&1 && claude plugin list 2>/dev/null | grep -qiw gsd; then
  echo "  ✓ GSD plugin installed"
else
  echo "  ! GSD not detected — it should auto-install as a cairn dependency."
  echo "    If /gsd:* is unavailable, run: claude plugin install gsd@bigjiggity"
fi

cat <<'NEXT'

▸ next step (inside Claude Code):
    /gsd:new-project        # interactive — creates .planning/ + ROADMAP

  After the roadmap exists, the cairn skill takes over: one bd issue per
  requirement, label each phase-N, write each NN-BEADS-MAP.md. Then:
    /gsd:plan-phase 1       # reads NN-BEADS-MAP.md, sets beads: frontmatter
    /gsd:execute-phase 1    # claim -> in_progress -> close per plan

  The cairn integration conventions activate once both .planning/ and .beads/ exist.
NEXT
