#!/usr/bin/env bash
# cairn PostToolUse hook (Bash / Grok terminal tools).
#
# Reads the active runtime hook payload on stdin ({tool_name, tool_input:
# {command}, ...}) and reacts to bd lifecycle writes — commands matching
# ^bd (create|update|close|reopen). Three fire-and-forget background jobs:
#
#   a) MIRROR PUSH — when <project>/.cairn/sync.json exists with at least one
#      enabled backend, fire gbsync for the affected issue:
#        - update/close with an extractable id  -> gbsync <verb> <id>
#          (reopen mirrors as update — gbsync speaks create|update|close)
#        - create (id not knowable) or no id    -> "full push": every bd
#          issue missing from .cairn/id-map.json is pushed as a create
#          (self re-invocation with --bg-full-push).
#      The id heuristic is the first id-shaped non-flag token after the
#      subcommand (flag values like --reason "…" are quoted tokens that fail
#      the id shape; --parent/--epic values are skipped explicitly), so
#      'bd close --reason "x" <id>' and 'bd close <id> --reason "x"' both work.
#   b) MAP REFRESH — when <project>/.planning/ exists and the command string
#      mentions phase-<N>, regenerate that phase's NN-BEADS-MAP.md via
#      cairn-map.sh <N>.
#   c) EXTERNAL-REF BACKFILL (bd close only — CORR-08 / D-12) — best-effort:
#      when gh is on PATH and `gh pr view` finds a PR for the current branch,
#      fire `bd update <id> --external-ref gh-<N>` so the closing issue links
#      to it going forward (cairn-doctor's `--link-refs` covers the backfill
#      for history that already happened). gh absent or no PR yet are both
#      silent no-ops — the common cases, not failures. The one deliberate
#      exception to "background jobs redirect to /dev/null" in this file:
#      this job's stdout+stderr APPEND to .cairn/hook.log instead, so a
#      write failure is observable instead of vanishing exactly like the bug
#      shape this milestone exists to remove.
#
# All jobs run nohup'd in the background so the hook returns immediately.
# Contract: at most ONE non-blocking JSON systemMessage; ALWAYS exit 0 (never fail the
# tool call). Test seams: CAIRN_GBSYNC / CAIRN_MAP / CAIRN_GH / CAIRN_BD
# override the respective tools (gh/bd invoked directly, gbsync/map via
# bash, so plain shell stubs work either way).
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAIRN_ROOT="$(dirname "$HOOK_DIR")"
GBSYNC="${CAIRN_GBSYNC:-$CAIRN_ROOT/scripts/gbsync.sh}"
CAIRN_MAP="${CAIRN_MAP:-$CAIRN_ROOT/scripts/cairn-map.sh}"

# --- background re-invocation: full push of unmapped issues -----------------
if [ "${1:-}" = "--bg-full-push" ]; then
  PROJECT_DIR="${2:-$PWD}"
  cd "$PROJECT_DIR" 2>/dev/null || exit 0
  command -v bd >/dev/null 2>&1 || exit 0
  ids="$(bd list --all --limit 0 --json 2>/dev/null | python3 -c '
import json, sys
from pathlib import Path
try:
    issues = json.load(sys.stdin) or []
except Exception:
    raise SystemExit
if not isinstance(issues, list):
    issues = [issues]
try:
    idmap = json.loads(Path(".cairn/id-map.json").read_text())
except Exception:
    idmap = {}
for iss in issues:
    iid = iss.get("id")
    if iid and iid not in idmap:
        print(iid)
' 2>/dev/null || true)"
  for id in $ids; do
    bash "$GBSYNC" create "$id" --dir "$PROJECT_DIR" >/dev/null 2>&1
  done
  exit 0
fi

# --- parse the hook payload --------------------------------------------------
# Only assignments serialized with shlex.quote enter eval.
CONTEXT="$(python3 "$CAIRN_ROOT/scripts/cairn-hook-context.py" 2>/dev/null)" || exit 0
eval "$CONTEXT"
case "$TOOL_NAME" in Bash|run_terminal_command|run_terminal_cmd) ;; *) exit 0 ;; esac
cd "$PROJECT_DIR" 2>/dev/null || exit 0
PARSED="$(python3 -c '
import re, shlex, sys
cmd = sys.argv[1]
m = re.match(r"^\s*bd\s+(create|update|close|reopen)\b", cmd)
if not m:
    raise SystemExit
verb = m.group(1)
try:
    toks = shlex.split(cmd[m.end():])
except ValueError:
    toks = cmd[m.end():].split()
issue = ""
skip_next = False
# Known value-taking flags: their (separate-token) values can be id-shaped
# (-l phase-3, --assignee agent-1, --reason follow-up, --parent <id>) and
# must never be mistaken for the positional issue id. Boolean flags
# (--claim, --force, --json, ...) are deliberately NOT listed.
VALUE_FLAGS = {
    "--parent", "--epic", "--reason", "-l", "--labels", "--label",
    "--add-label", "--remove-label", "--set-labels",
    "--assignee", "-a", "--status", "-s", "--type", "-t", "--priority",
    "-p", "--description", "-d", "--title", "--metadata", "--estimate",
    "--defer", "--due", "--dep", "--deps", "--file", "-f",
}
for tok in toks:
    if skip_next:
        skip_next = False
        continue
    if tok.startswith("-"):
        skip_next = tok in VALUE_FLAGS
        continue
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*-[A-Za-z0-9]+", tok):
        issue = tok
        break  # first id-shaped non-flag token wins, wherever it sits
pm = re.search(r"\bphase-(\d+)\b", cmd)
phase = pm.group(1) if pm else ""
print(f"{verb}|{issue}|{phase}")
' "$TOOL_COMMAND" 2>/dev/null || true)"

[ -n "$PARSED" ] || exit 0
VERB="${PARSED%%|*}"
REST="${PARSED#*|}"
ISSUE="${REST%%|*}"
PHASE="${REST#*|}"

QUEUED=""

# --- (a) mirror push ---------------------------------------------------------
SYNC_JSON="$PROJECT_DIR/.cairn/sync.json"
if [ -f "$SYNC_JSON" ]; then
  ENABLED="$(python3 -c '
import json, sys
try:
    cfg = json.loads(open(sys.argv[1]).read())
except Exception:
    print("no"); raise SystemExit
on = [b for b in cfg.get("backends", []) if b.get("enabled")]
print("yes" if on else "no")
' "$SYNC_JSON" 2>/dev/null || echo no)"
  if [ "$ENABLED" = "yes" ]; then
    if [ "$VERB" != "create" ] && [ -n "$ISSUE" ]; then
      # gbsync's push vocabulary is create|update|close — a reopen is a
      # status change on an existing mirror, so it rides as update.
      SYNC_VERB="$VERB"
      if [ "$SYNC_VERB" = "reopen" ]; then SYNC_VERB="update"; fi
      nohup bash "$GBSYNC" "$SYNC_VERB" "$ISSUE" --dir "$PROJECT_DIR" >/dev/null 2>&1 &
    else
      nohup bash "$HOOK_DIR/post-bd-write.sh" --bg-full-push "$PROJECT_DIR" >/dev/null 2>&1 &
    fi
    QUEUED="mirror push"
  fi
fi

# --- (b) phase map refresh ---------------------------------------------------
if [ -n "$PHASE" ] && [ -d "$PROJECT_DIR/.planning" ]; then
  nohup bash "$CAIRN_MAP" "$PHASE" >/dev/null 2>&1 &
  QUEUED="${QUEUED:+$QUEUED + }map refresh (phase $PHASE)"
fi

# --- (c) external-ref backfill on bd close -----------------------------------
# D-12 (CORR-08): gh absent, or gh present with no PR yet for this branch, are
# both silent no-ops — neither is a failure, so no log line either way.
if [ "$VERB" = "close" ] && [ -n "$ISSUE" ] && command -v "${CAIRN_GH:-gh}" >/dev/null 2>&1; then
  PR_NUM="$(cd "$PROJECT_DIR" 2>/dev/null && "${CAIRN_GH:-gh}" pr view --json number -q .number 2>/dev/null || true)"
  if [ -n "$PR_NUM" ]; then
    mkdir -p "$PROJECT_DIR/.cairn" 2>/dev/null || true
    # The one deliberate exception in this file: append to a persistent log
    # instead of /dev/null, so a write failure here is observable rather
    # than vanishing like the bug shape this hook must not repeat.
    nohup "${CAIRN_BD:-bd}" -C "$PROJECT_DIR" update "$ISSUE" \
      --external-ref "gh-$PR_NUM" >> "$PROJECT_DIR/.cairn/hook.log" 2>&1 &
    QUEUED="${QUEUED:+$QUEUED + }external-ref gh-$PR_NUM"
  fi
fi

if [ -n "$QUEUED" ]; then
  python3 -c 'import json, sys; print(json.dumps({"systemMessage": sys.argv[1]}))' \
    "[cairn] bd $VERB${ISSUE:+ $ISSUE} → $QUEUED queued" 2>/dev/null || true
fi
exit 0
