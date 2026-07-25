#!/usr/bin/env bash
# cairn Stop hook — end-of-session tracker hygiene.
# When the repo has .beads/ and bd is available, list in_progress issues
# still assigned to the current actor (resolved the way bd itself does:
# $BEADS_ACTOR, then git user.name, then $USER) and print ONE warning line
# if any remain. Silent when clean, silent on any failure, ALWAYS exit 0 —
# this hook never blocks the stop.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
[ -d "$PROJECT_DIR/.beads" ] || exit 0
command -v bd >/dev/null 2>&1 || exit 0

ACTOR="${BEADS_ACTOR:-$(git -C "$PROJECT_DIR" config user.name 2>/dev/null || true)}"
[ -n "$ACTOR" ] || ACTOR="${USER:-}"
[ -n "$ACTOR" ] || exit 0

LINE="$(bd -C "$PROJECT_DIR" list --status in_progress --assignee "$ACTOR" \
          --limit 0 --json 2>/dev/null | python3 -c '
import json, sys
try:
    issues = json.load(sys.stdin) or []
except Exception:
    raise SystemExit
if not isinstance(issues, list):
    issues = [issues]
ids = [i.get("id", "?") for i in issues]
if ids:
    print("[cairn] session ending with %d in_progress issue(s) still "
          "assigned to you: %s — bd close <id> --reason=..., pause per the "
          "cairn pause/resume rule, or hand off before stopping."
          % (len(ids), ", ".join(ids)))
' 2>/dev/null || true)"

[ -n "$LINE" ] && echo "$LINE"
exit 0
