#!/usr/bin/env bash
# cairn SessionStart hook.
# Three jobs:
#   1. First-run bootstrap nudge — if beads (bd) isn't installed yet, inject a
#      one-time offer so Claude can prompt the user and install it. GSD ships as
#      a declared plugin dependency, so it is already auto-installed; only the
#      bd *binary* needs this hook (a binary can't be a plugin dependency).
#   2. Migration discovery — .planning/ without .beads/ (or both present but no
#      generated NN-BEADS-MAP.md) gets a one-line /cairn:migrate nudge.
#   3. Integration-active reminder — when the repo has BOTH .planning/ (GSD) and
#      .beads/ (beads), inject the cairn convention reminder.
# Anything printed to stdout is injected into the session as additional context.
set -euo pipefail

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
# 3. integration-active reminder — both GSD and beads present in this repo
#***************************************************************************
if [ -d "$PROJECT_DIR/.planning" ] && [ -d "$PROJECT_DIR/.beads" ]; then
  # 2b. both present but no generated phase maps yet — wiring incomplete.
  if ! find "$PROJECT_DIR/.planning/phases" -name '*-BEADS-MAP.md' -print -quit \
       2>/dev/null | grep -q .; then
    echo "[cairn] .planning/ and .beads/ are both present but no NN-BEADS-MAP.md exists under .planning/phases/ — run /cairn:migrate to wire phases to bd issues."
  fi
  # Always emit the cairn-specific glue — the part neither tool knows on its own.
  cat <<'MSG'
[cairn] This repo uses BOTH GSD (.planning/) and beads (.beads/).
The cairn integration is active — use the `cairn` skill conventions:
  • each phase NN maps requirements -> bd ids in .planning/phases/NN-*/NN-BEADS-MAP.md
    (a GENERATED file — regenerate via cairn-map, never hand-edit between the markers)
  • every bd issue carries the label PAIR m-<milestone> + phase-<N> (unpadded);
    list a phase's work with: bd list -l m-<milestone>,phase-<N>
  • every issue carries the metadata stamp {"gsd": {"req", "phase", "milestone"}};
    (gsd.req, gsd.milestone) is the dedup key — never create a second issue for
    the same requirement in the same milestone
  • every PLAN.md carries a `beads:` frontmatter list of the bd ids it advances
  • execute-phase: claim -> in_progress -> close each plan's bd ids
  • on conflict, GSD phase docs (CONTEXT/PLAN/ROADMAP) win over bd issue text
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

  # context-mode is a cairn dependency, so the integration is on by default.
  # .cairn/context.json is optional tuning, not a gate.
  cat <<'MSG'
[cairn] context-mode intent-aware memory is active (context-mode is a dependency;
.cairn/context.json tunes it, defaults apply without it). Use the `cairn-context`
skill conventions when the ctx_* tools are present:
  • index during execution under source label gb/<bd_id>/<phase>
  • recall scoped to the active task: ctx_search(source: "<bd_id>")  (/cairn:recall)
  • stream logs/test output via ctx_execute_file (don't persist them)
  • on phase transition: ctx_stats checkpoint, switch scope to the new phase label
  • capacity guard: if ctx_stats tokens exceed the threshold (default 150k), advise
    splitting the active bd issue into sub-tasks (bd create + bd dep add)
  • scope-by-label only — this layer NEVER calls ctx_purge (manual/user-only)
MSG
fi

exit 0
