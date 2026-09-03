#!/usr/bin/env bash

########################
# cairn-init           #
########################

# cairn-init — the deterministic half of /cairn-init.
# Wires git + beads. Installing the bd binary (if missing) is the interactive
# job of the /cairn-init command — this script assumes bd is already on PATH.
#
# Usage:  cairn-init.sh [target-dir]   (defaults to current dir)
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="${1:-$PWD}"
cd "$DIR"
echo "▸ bootstrapping cairn (beads hub) in: $DIR"

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

# cairn relies on bd >= 1.1.0 (--claim semantics, --all, nested --metadata).
BD_MIN_VERSION="1.1.0"
BD_VER="$(bd version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
if [ -n "$BD_VER" ] && [ "$(printf '%s\n' "$BD_MIN_VERSION" "$BD_VER" | sort -V | head -1)" != "$BD_MIN_VERSION" ]; then
  echo "  ⚠ bd $BD_VER < $BD_MIN_VERSION — some cairn conventions may misbehave; upgrade beads" >&2
fi

# 3. beads project
if [ -d .beads ]; then
  echo "  ✓ .beads/ already present"
else
  bd init
  echo "  ✓ bd init"
fi

# 4. keep generated local state out of git — everything cairn writes under
#    .cairn/ that is machine-local (docs/sync.md §4). This is a LIST, never
#    a blanket '.cairn/' or '.cairn/*.json': sync.json and context.json are
#    meant to be committed so the whole team shares one config, and a
#    directory-wide ignore would silently hide them.
#    Idempotent: each entry is appended at most once.
GI=".gitignore"
CAIRN_IGNORES=(
  '.cairn/id-map.json'
  '.cairn/state.json'
  '.cairn/conflicts.json'
  # v1.4 generated files — added late, hence the "re-run /cairn:init" note
  # in the release. journal.jsonl needs the wildcard, not the exact name:
  # cairn-journal.py writes journal.jsonl.tmp-* siblings and a
  # journal.jsonl.compact.lock next to it, and an exact name misses both.
  '.cairn/journal.jsonl*'
  # Phase 28: .cairn/journal/ is the one VERSIONED thing under .cairn/ — one
  # partition per checkout. Only its .jsonl segments are versioned; the
  # compaction lock and any scratch sibling in there are per-machine. A
  # whitelist, so nothing new leaks in by default.
  '.cairn/journal/*'
  '!.cairn/journal/*.jsonl'
  '.cairn/reconcile-evidence.json'
  '.cairn/hook.log'
  # cairn-migrate's resumable plan + state: same class, same reason.
  '.cairn/migrate-plan.json'
  '.cairn/migrate-state.json'
  # /cairn:init writes ${CLAUDE_PLUGIN_ROOT} here — an absolute, per-machine
  # path that is wrong on every other checkout.
  '.cairn/plugin-root'
)
ADDED=0
for entry in "${CAIRN_IGNORES[@]}"; do
  if grep -qxF "$entry" "$GI" 2>/dev/null; then
    continue
  fi
  if [ "$ADDED" -eq 0 ]; then
    printf '\n# cairn: generated local state (never commit)\n' >> "$GI"
  fi
  printf '%s\n' "$entry" >> "$GI"
  ADDED=$((ADDED + 1))
done
if [ "$ADDED" -gt 0 ]; then
  # Report the count, not the names: a message that enumerates starts lying
  # the moment the set grows — which is exactly how we got here.
  echo "  ✓ gitignored $ADDED generated .cairn state file(s)"
else
  echo "  ✓ .cairn state files already gitignored"
fi

# 4b. merge=union on the journal partitions (phase 28, DJOUR-02). Without this
#     line a project adopted by /cairn:init would version its partitions with
#     the DEFAULT merge, and the same partition on two branches would conflict
#     with markers — silently, on whichever machine skipped the setup. It has
#     to be `union` and not a custom driver: a custom `merge.<name>.driver`
#     lives in .git/config, which git never clones (28-RESEARCH.md, E17).
#     Idempotent: the line is appended at most once.
GA=".gitattributes"
GA_LINE='.cairn/journal/*.jsonl merge=union'
if grep -qxF "$GA_LINE" "$GA" 2>/dev/null; then
  echo "  ✓ journal partitions already set to merge=union"
else
  printf '\n# cairn: journal partitions merge by concatenation (one file per\n# checkout, never reordered). union is built-in — a custom driver would\n# need .git/config, which git never clones.\n%s\n' "$GA_LINE" >> "$GA"
  echo "  ✓ journal partitions set to merge=union"
fi

mkdir -p .cairn
printf '%s\n' "$PLUGIN_ROOT" > .cairn/plugin-root
echo "  ✓ .cairn/plugin-root"

# Tracker templates for Matt skills (do not clobber user edits).
mkdir -p docs/agents
if [ ! -f docs/agents/issue-tracker.md ]; then
  cp "$PLUGIN_ROOT/templates/issue-tracker-beads.md" docs/agents/issue-tracker.md
  echo "  ✓ docs/agents/issue-tracker.md"
else
  echo "  ✓ docs/agents/issue-tracker.md already present"
fi
if [ ! -f docs/agents/triage-labels.md ]; then
  cp "$PLUGIN_ROOT/templates/triage-labels.md" docs/agents/triage-labels.md
  echo "  ✓ docs/agents/triage-labels.md"
else
  echo "  ✓ docs/agents/triage-labels.md already present"
fi
cat <<'NEXT'

▸ next:
    /cairn-implement        # grill → spec → tickets → implement (bd is the hub)
    /cairn-status           # READY / DOING / BLOCKED
    /cairn-doctor           # graph health
    /cairn-sync-config      # optional Jira / GitHub / … spoke
NEXT
exit 0
