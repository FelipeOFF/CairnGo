# Phase 15: Phase lease — Deferred Items

Discoveries made during execution that are real but out of scope for the
plan that found them. Logged here per the executor's scope-boundary rule
rather than fixed silently or ignored.

## From Plan 15-04 (session hooks)

### session-stop.sh's pre-existing in_progress-issue check will also catch the lease bookkeeping issue itself

**Discovered during:** Task 1, while designing the "releases every lease
and prints one line naming the phase" test.

**What was measured (live, not assumed):** `cairn-lease.py acquire` calls
`bd update <id> --claim`, and bd's own `--claim` sets the issue's real
`status` to `in_progress` and `assignee` to the actor bd resolves via the
same `$BEADS_ACTOR` / `git config user.name` / `$USER` chain the rest of
the codebase uses. Verified with a real `bd 1.1.0` binary:

```
$ bash cairn-lease.sh acquire 15 --project-dir <dir>
$ bd list --status in_progress --assignee "<actor>" --json
[{"id": "prb-ajn", "title": "phase-15 lease", "status": "in_progress",
  "assignee": "<actor>", "labels": ["lease"], ...}]
```

**The interaction:** `session-stop.sh`'s pre-existing in_progress-issue
check (`bd list --status in_progress --assignee "$ACTOR"`) resolves the
SAME actor chain, with no `BEADS_ACTOR` override, in real (non-test)
usage. So in the ordinary case — a session that holds a phase lease and
then stops, exactly the workflow D-03 is built for — the lease
bookkeeping issue itself will ALSO be caught by that check, and the user
will see:

```
[cairn] session ending with 1 in_progress issue(s) still assigned to you:
prb-ajn — bd close <id> --reason=..., pause per the cairn pause/resume
rule, or hand off before stopping.
```

immediately followed by this plan's own, correct line:

```
[cairn] session ending — released 1 phase lease(s) you were holding: 15
```

The first line's advice ("bd close <id> --reason=...") is actively wrong
for a lease issue — a human should never manually close it; `release
--mine` already handles it, one line later, in the same hook run.

**Why not fixed here:** 15-04-PLAN.md's Task 1 action text explicitly
instructs: "After the existing in_progress-issues check (leave it
completely untouched)". Excluding `lease`-labeled issues from that
check's query/output would mean editing that pre-existing block, which is
outside this plan's authorized scope (`files_modified` also lists only
`session-start.sh`, `session-stop.sh`, `tests/hooks.bats` — not a second,
broader change to the untouched block). This plan's own tests avoid the
collision by acquiring the test lease under a distinct `BEADS_ACTOR`
override so the two checks stay observably independent (see
`tests/hooks.bats`, "session-stop: releases every lease...").

**Precedent that this is a known class of problem, not a one-off:**
15-05-PLAN.md (sibling wave-2 plan, `cairn-status.py`'s status panel)
already designs an `is_lease_issue()` filter for exactly this reason —
excluding the `lease`-labeled, claimed-in_progress bookkeeping issue from
the "doing" lane so it isn't mistaken for real work. The same exemption
pattern (filter on the `lease` label, matching `NO_PHASE_EXEMPT` in
`cairn-doctor.py` and the orphans-check exemption from Plan 15-03) should
be applied to `session-stop.sh`'s in_progress-issue query too.

**Suggested fix for a follow-up plan:** filter `session-stop.sh`'s
`bd list --status in_progress --assignee "$ACTOR"` result to drop any
issue carrying the `lease` label before computing `ids`/`LINE` — same
`python3 -c` inline-parsing block, one more `if "lease" in (i.get("labels")
or [])` condition.
