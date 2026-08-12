#!/usr/bin/env bash

########################
# cairn-init           #
########################

# cairn-init — the deterministic half of /cairn:init.
# Wires git + beads so the cairn integration can activate. GSD arrives as a
# declared plugin dependency, and installing the bd binary (if missing) is the
# interactive job of the /cairn:init command — this script assumes bd is already
# on PATH and stops with guidance if it isn't.
# The .planning/ tree is created interactively by /cairn:new inside Claude.
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

# 5. git pre-push ship gate — a tiny shim that runs cairn-gate.sh and blocks
#    the push ONLY on exit 6 (open bd issues in completed phases). Exit 5
#    (bd unavailable) warns but never blocks. Idempotent: re-runs refresh the
#    shim in place. Chainable beads-style: a pre-existing foreign pre-push
#    hook is moved to pre-push.old and the shim runs it first.
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$(git rev-parse --git-path hooks 2>/dev/null || echo .git/hooks)"
mkdir -p "$HOOKS_DIR"
SHIM="$HOOKS_DIR/pre-push"
SHIM_MARKER="cairn pre-push gate"
if [ -f "$SHIM" ] && ! grep -qF "$SHIM_MARKER" "$SHIM"; then
  # Never clobber a pre-push.old that chains an EARLIER foreign hook: cairn
  # chained hook X aside, another tool later wrote a fresh pre-push, and a
  # re-run would silently delete X. Refuse and let the user consolidate.
  if [ -f "$SHIM.old" ] && ! grep -qF "$SHIM_MARKER" "$SHIM.old"; then
    echo "  ✗ both $SHIM and $SHIM.old exist and neither is the cairn shim —" >&2
    echo "    refusing to overwrite pre-push.old (it chains an earlier hook)." >&2
    echo "    Merge the two hooks manually, then re-run cairn-init.sh." >&2
    exit 1
  fi
  mv "$SHIM" "$SHIM.old"
  echo "  ✓ existing pre-push hook moved to pre-push.old (chained — runs first)"
fi
cat > "$SHIM" <<SHIM_EOF
#!/usr/bin/env bash
# ${SHIM_MARKER} — installed by cairn-init.sh; re-run cairn-init.sh to refresh.
# Blocks a push ONLY when cairn-gate exits 6 (completed GSD phases with open
# bd issues). Exit 5 = bd unavailable -> warn but NEVER block (availability
# failure is not a gate failure); any other gate error never blocks either.
# Bypass once with: git push --no-verify

# Chain: a pre-existing pre-push hook was moved aside at install; run it first.
OLD="\$(dirname "\$0")/pre-push.old"
if [ -x "\$OLD" ]; then
  "\$OLD" "\$@" || exit \$?
fi

GATE="\${CAIRN_GATE:-$SCRIPTS_DIR/cairn-gate.sh}"
if ! command -v "\$GATE" >/dev/null 2>&1 && [ ! -e "\$GATE" ]; then
  echo "[cairn] pre-push: cairn-gate not found (\$GATE) — ship gate skipped" >&2
  exit 0
fi
# Pin the gate to THIS repo: cairn-gate prefers \$CLAUDE_PROJECT_DIR over the
# cwd, so a 'git -C /other/repo push' from a Claude session would otherwise
# gate the session's project instead of the repo being pushed.
REPO_ROOT="\$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
rc=0
if command -v "\$GATE" >/dev/null 2>&1; then
  "\$GATE" --planning-dir "\$REPO_ROOT/.planning" || rc=\$?
else
  bash "\$GATE" --planning-dir "\$REPO_ROOT/.planning" || rc=\$?
fi
if [ "\$rc" -eq 6 ]; then
  echo "[cairn] PUSH BLOCKED — completed phases still have open bd issues (listed above)." >&2
  echo "        Close them (bd close <id> --reason=...) or bypass once: git push --no-verify" >&2
  exit 6
fi
if [ "\$rc" -eq 5 ]; then
  echo "[cairn] warning: bd unavailable — ship gate skipped, push allowed." >&2
fi
exit 0
SHIM_EOF
chmod +x "$SHIM"
echo "  ✓ pre-push ship gate installed (cairn-gate; blocks only on exit 6)"

# 6. Vendored GSD runtime — the plugin carries its own since v1.6, so this
#    checks THIS INSTALL rather than recommending someone else's plugin. An
#    external gsd-core is no longer a dependency; it is something
#    /cairn:doctor asks you to uninstall, because two lineages answering
#    /gsd:* and /cairn:* at once is the defect the vendoring closed.
RUNTIME="$(cd "$(dirname "$0")/.." && pwd)/gsd"
if [ -f "$RUNTIME/MANIFEST.json" ] && [ -d "$RUNTIME/commands" ]; then
  echo "  ✓ vendored GSD runtime present (no external plugin needed)"
else
  echo "  ! vendored GSD runtime missing under $RUNTIME — this cairn install"
  echo "    is incomplete. Reinstall: claude plugin install cairn@cairngo"
fi

cat <<'NEXT'

▸ next step (inside Claude Code):
    /cairn:new              # interactive — creates .planning/ + ROADMAP,
                            # then the bd issues and the phase↔beads maps

  From there the loop runs in one namespace:
    /cairn:plan 1           # plans the phase and sets each PLAN's beads:
    /cairn:work 1           # claim -> in_progress -> close per plan
    /cairn:verify 1         # UAT against what the phase promised
    /cairn:status           # READY / DOING / BLOCKED, and the next action

  A repo that already has .planning/ or .beads/ history: /cairn:migrate.
  Health of the wiring, any time: /cairn:doctor.
NEXT
