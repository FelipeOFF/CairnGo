#!/usr/bin/env bash
# cairn SessionStart hook.
# 1. Offer to install bd when it is missing.
# 2. Write .cairn/plugin-root so commands resolve the plugin without
#    CLAUDE_PLUGIN_ROOT in the agent shell.
# 3. Remind v5 conventions when .beads/ is present.
# stdout is injected into the session as additional context.
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$HOOK_DIR")"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
DATA_DIR="${CLAUDE_PLUGIN_DATA:-}"
SKIP_MARKER="${DATA_DIR:+$DATA_DIR/bd-install.skip}"

#***************************************************************************
# 1. beads bootstrap — only nudges when bd is missing and not skipped
#***************************************************************************
if ! command -v bd >/dev/null 2>&1; then
  if [ -z "$SKIP_MARKER" ] || [ ! -f "$SKIP_MARKER" ]; then
    cat <<'MSG'
[cairn] Setup needed: the beads issue tracker (`bd`) is not installed, and cairn
uses it for all task tracking. Offer to install it now, and on the user's OK run
the first installer that fits their machine:
  • macOS / Linux (recommended):  brew install beads
  • Node.js users:                npm install -g @beads/bd
  • portable fallback:            curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash
Then verify with `bd version`. If the user declines, create an empty file at
$CLAUDE_PLUGIN_DATA/bd-install.skip so this stops nagging. Or just run /cairn:init,
which walks the whole setup (git + beads + GSD + first project) end to end.
MSG
  fi
fi

#***************************************************************************
# 2. migration discovery — GSD planning exists but beads isn't wired yet.
#    One line each; branch 2a is skipped while bd is missing (block 1 already
#    nudges the whole setup, so we don't double up).
#***************************************************************************
# 2a. .planning/ present, .beads/ absent — the repo predates cairn.
if [ -d "$PROJECT_DIR/.planning" ] && [ ! -d "$PROJECT_DIR/.beads" ] \
   && command -v bd >/dev/null 2>&1; then
  echo "[cairn] GSD planning found but beads is not initialized — run /cairn:migrate to wire existing phases to bd issue tracking."
fi

#***************************************************************************
# 3. cairn-active reminder — the repo is tracked by beads
#
#    v1.7: o gatilho era `.planning/` E `.beads/`, e o nudge do meio pedia um
#    `NN-BEADS-MAP.md` para declarar a fiacao completa. Os dois pressupunham
#    que cairn e' uma PONTE entre um GSD em disco e o bd. Cairn e' o sistema:
#    `.beads/` basta, e `.planning/` e' material a importar — nunca destino.
#***************************************************************************
# 5. A stop request (phase 50) belongs to the run it was made for: one found at
#    session start predates this session and would stop the first loop for
#    nothing. Say it was cleared, so the operator knows it did not survive.
if [ -f "$PROJECT_DIR/.cairn/stop" ]; then
  rm -f "$PROJECT_DIR/.cairn/stop"
  echo "[cairn] a stop request from a previous session was cleared (.cairn/stop) — request again from the board if it still applies."
fi
mkdir -p "$PROJECT_DIR/.cairn"
printf '%s\n' "$PLUGIN_ROOT" > "$PROJECT_DIR/.cairn/plugin-root"

if [ -d "$PROJECT_DIR/.beads" ]; then
  cat <<'MSG'
[cairn] beads hub is active (v5). Specs and tickets live on bd.
  • /cairn-grill [ref] — interview, write the spec bead
  • /cairn-implement [ref] — tickets + code for a spec that exists
  • /cairn-status — READY / DOING / BLOCKED
  • CONTEXT.md in this loop is an error; glossary/ADRs go on the spec bead
  • optional spoke: /cairn-sync-config (Jira Epic=spec, Story=ticket)
MSG

  # beads installs its OWN Claude integration on `bd init` (a `bd prime`
  # SessionStart hook + a BEADS INTEGRATION block in CLAUDE.md) that already
  # injects bd basics, the "use bd for all tracking" rule, and the session-close
  # protocol. Only restate those when that integration ISN'T present — otherwise
  # we'd double up at every SessionStart.
  if grep -q "BEGIN BEADS INTEGRATION" "$PROJECT_DIR/CLAUDE.md" 2>/dev/null \
     || grep -q "bd prime" "$PROJECT_DIR/.claude/settings.json" 2>/dev/null; then
    echo "  (bd basics, the all-tracking rule, and session-close come from beads' own \`bd prime\` hook — not repeated here.)"
  else
    cat <<'MSG'
  • use `bd` for ALL task tracking (not TodoWrite / markdown TODOs)
Run `bd prime` for the full bd command reference and session-close protocol.
MSG
  fi

fi

exit 0
