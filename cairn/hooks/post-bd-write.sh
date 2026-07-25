#!/usr/bin/env bash
# cairn PostToolUse hook (matcher: Bash).
#
# Reads the Claude Code hook payload on stdin ({tool_name, tool_input:
# {command}, ...}) and reacts to bd lifecycle writes — commands matching
# ^bd (create|update|close). Two fire-and-forget background jobs:
#
#   a) MIRROR PUSH — when <project>/.cairn/sync.json exists with at least one
#      enabled backend, fire gbsync for the affected issue:
#        - update/close with an extractable id  -> gbsync <verb> <id>
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
#
# Both jobs run nohup'd in the background so the hook returns immediately.
# Contract: at most ONE short stdout line; ALWAYS exit 0 (never fail the
# tool call). Test seams: CAIRN_GBSYNC / CAIRN_MAP override the scripts
# (invoked via bash, so plain shell stubs work).
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$HOOK_DIR")"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
GBSYNC="${CAIRN_GBSYNC:-$PLUGIN_ROOT/scripts/gbsync.sh}"
CAIRN_MAP="${CAIRN_MAP:-$PLUGIN_ROOT/scripts/cairn-map.sh}"

# --- background re-invocation: full push of unmapped issues -----------------
if [ "${1:-}" = "--bg-full-push" ]; then
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
    bash "$GBSYNC" create "$id" >/dev/null 2>&1
  done
  exit 0
fi

# --- parse the hook payload --------------------------------------------------
PARSED="$(python3 -c '
import json, re, shlex, sys
try:
    data = json.load(sys.stdin)
except Exception:
    raise SystemExit
if data.get("tool_name", "Bash") != "Bash":
    raise SystemExit
cmd = (data.get("tool_input") or {}).get("command") or ""
m = re.match(r"^\s*bd\s+(create|update|close)\b", cmd)
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
    "--assignee", "-a", "--status", "-s", "--type", "-t", "--priority",
    "-p", "--description", "-d", "--title", "--metadata", "--estimate",
    "--defer-until", "--dep", "--deps", "--file", "-f",
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
' 2>/dev/null || true)"

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
      nohup bash "$GBSYNC" "$VERB" "$ISSUE" >/dev/null 2>&1 &
    else
      nohup bash "${BASH_SOURCE[0]}" --bg-full-push >/dev/null 2>&1 &
    fi
    QUEUED="mirror push"
  fi
fi

# --- (b) phase map refresh ---------------------------------------------------
if [ -n "$PHASE" ] && [ -d "$PROJECT_DIR/.planning" ]; then
  nohup bash "$CAIRN_MAP" "$PHASE" >/dev/null 2>&1 &
  QUEUED="${QUEUED:+$QUEUED + }map refresh (phase $PHASE)"
fi

[ -n "$QUEUED" ] && echo "[cairn] bd $VERB${ISSUE:+ $ISSUE} → $QUEUED queued"
exit 0
