#!/usr/bin/env bash
# cairn Stop hook — end-of-session tracker hygiene.
# Two jobs, both silent when clean, silent on any failure, ALWAYS exit 0 —
# this hook never blocks the stop:
#   1. in_progress-issue reminder — list in_progress issues still assigned
#      to the current actor (resolved the way bd itself does: $BEADS_ACTOR,
#      then git user.name, then $USER) and print ONE warning line if any
#      remain. Excludes any issue carrying the `lease` label (Plan 15-01):
#      acquiring a lease claims its bookkeeping issue in_progress under
#      this same actor, and "bd close <id> --reason=..." is wrong advice
#      for it — job 2 below already releases it, one line later, in the
#      same hook run. Mirrors cairn-status.py's is_lease_issue() exemption
#      (Plan 15-05) and NO_PHASE_EXEMPT in cairn-doctor.py.
#   2. lease release (D-03) — release every phase lease THIS worktree holds
#      via `cairn-lease.sh release --mine` (worktree-scoped identity — never
#      the unconditional `release <N>` verify-post.md calls once per phase
#      regardless of holder) and print one line naming what was released.
#      A lease held by a DIFFERENT worktree is never touched.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$HOOK_DIR")"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
CAIRN_LEASE="${CAIRN_LEASE:-$PLUGIN_ROOT/scripts/cairn-lease.sh}"
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
ids = [i.get("id", "?") for i in issues
       if "lease" not in (i.get("labels") or [])]
if ids:
    print("[cairn] session ending with %d in_progress issue(s) still "
          "assigned to you: %s — bd close <id> --reason=..., pause per the "
          "cairn pause/resume rule, or hand off before stopping."
          % (len(ids), ", ".join(ids)))
' 2>/dev/null || true)"

[ -n "$LINE" ] && echo "$LINE"

# --- lease release (D-03) -----------------------------------------------
# release --mine is worktree-scoped by holder identity, so it can never
# clear a DIFFERENT worktree's active lease — verify-post.md's own
# unconditional `release <N>` is a deliberately different verb.
LEASE_LINE="$(bash "$CAIRN_LEASE" release --mine --project-dir "$PROJECT_DIR" \
                --json 2>/dev/null | python3 -c '
import json, sys
try:
    result = json.load(sys.stdin) or {}
except Exception:
    raise SystemExit
phases = result.get("phases") or []
if phases:
    print("[cairn] session ending — released %d phase lease(s) you were "
          "holding: %s" % (len(phases), ", ".join(str(p) for p in phases)))
' 2>/dev/null || true)"

[ -n "$LEASE_LINE" ] && echo "$LEASE_LINE"
exit 0
