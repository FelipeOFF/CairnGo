---
phase: 15-phase-lease
plan: "04"
subsystem: infra
tags: [bash, hooks, bd, beads, cairn-lease, bats]

# Dependency graph
requires:
  - phase: 15-phase-lease (Plan 15-01)
    provides: "cairn-lease.py/.sh renew and release --mine subcommands, and the status --json shape both hooks and tests read"
provides:
  - "session-start.sh: best-effort, backgrounded lease heartbeat renewal (D-03) of any lease this worktree already holds"
  - "session-stop.sh: synchronous, worktree-scoped lease release (release --mine) with a printed confirmation line"
  - "tests/hooks.bats coverage proving D-03's named risk closed: a lease whose heartbeat was never renewed is independently visible as stale via both cairn-lease.sh status and cairn-doctor.sh, without either hook ever running"
affects: [15-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "hook-level CAIRN_LEASE env seam (mirrors the existing CAIRN_GBSYNC/CAIRN_MAP seams in post-bd-write.sh) for recorder-stub and broken-path testing"
    - "session-start fires a best-effort, backgrounded (nohup + &) renew; session-stop performs a synchronous, worktree-scoped release — mirrors the sync-vs-async split post-bd-write.sh already established for background work vs. a hook's own time-budgeted synchronous checks"

key-files:
  created: []
  modified:
    - cairn/hooks/session-start.sh
    - cairn/hooks/session-stop.sh
    - tests/hooks.bats

key-decisions:
  - "release --mine's JSON shape ({released, holder, phases}) carries no per-lease timestamp (the lease is already vacated before the JSON is printed), so session-stop.sh's confirmation line names which phase(s) were released without a 'since when' duration. The plan's action text described 'naming the phase and how long it had been held', but neither the must_haves truths nor the acceptance_criteria require the duration — only 'prints one line naming what it released' / 'prints exactly one line naming the phase' — so this is a data-shape adaptation, not a shortfall against what the plan actually gates on."
  - "Task 1's acceptance tests isolate the lease-release assertion from a real, measured interaction: acquiring a lease claims the underlying bd issue in_progress, assigned to the acquiring actor — the SAME actor chain (BEADS_ACTOR/git config/USER) session-stop.sh's pre-existing in_progress-issue check resolves. Tests acquire the lease under a distinct BEADS_ACTOR so the two checks stay observably independent; the real-world interaction itself is out of this plan's authorized scope (the plan explicitly says leave that check untouched) and is logged in 15-phase-lease/deferred-items.md instead of fixed here."
  - "Task 2's hook-never-ran test reuses helpers.bash's existing make_gsd_fixture (already shared infrastructure) rather than duplicating cairn-doctor.bats's richer make_doctor_fixture/wire_capability_ok apparatus — verified live that cairn-doctor.sh completes cleanly and reports the lease-stale check correctly even with a minimal bd init and no GSD-capability/label-pair wiring; other unrelated checks legitimately warn/fail on that minimal fixture, which is irrelevant to what this test asserts (the lease-stale check's own content)."

requirements-completed: [LEASE-04]

coverage:
  - id: D1
    description: "session-start.sh best-effort renews the heartbeat of a lease this worktree already holds (resolved via renew's own STATE.md active_phase lookup), and is a silent no-op for every other case — never acquiring or creating a lease as a side effect of starting a session"
    requirement: "LEASE-04"
    verification:
      - kind: integration
        ref: "tests/hooks.bats#session-start: fires lease renew in the background when both .planning/ and .beads/ are present"
        status: pass
      - kind: integration
        ref: "tests/hooks.bats#session-start: missing .planning/ or .beads/ never invokes the lease seam"
        status: pass
      - kind: integration
        ref: "tests/hooks.bats#session-start: .beads/ present but .planning/ absent never invokes the lease seam"
        status: pass
    human_judgment: false
  - id: D2
    description: "session-stop.sh releases every lease this worktree holds via release --mine, prints one line naming what was released, and never touches a lease held by a different worktree"
    requirement: "LEASE-04"
    verification:
      - kind: integration
        ref: "tests/hooks.bats#session-stop: releases every lease this worktree holds, confirmed via a follow-up status call, and prints exactly one line naming the phase"
        status: pass
      - kind: integration
        ref: "tests/hooks.bats#session-stop: a lease held by a DIFFERENT worktree is left completely untouched and silent"
        status: pass
    human_judgment: false
  - id: D3
    description: "the hook-never-ran risk (D-03's named risk): when heartbeat renewal never runs at all, the resulting staleness is observable via cairn-lease status's own content AND cairn-doctor's lease-stale check, never merely inferred from an exit code"
    requirement: "LEASE-04"
    verification:
      - kind: integration
        ref: "tests/hooks.bats#the hook-never-ran risk: a lease whose heartbeat was never renewed is independently reported stale by both cairn-lease status and cairn-doctor, without either hook ever running"
        status: pass
    human_judgment: false
  - id: D4
    description: "both hooks exit 0 unconditionally regardless of bd's availability, a missing .planning/.beads/, or a broken CAIRN_LEASE path — never a traceback, never a non-zero exit"
    requirement: "LEASE-04"
    verification:
      - kind: integration
        ref: "tests/hooks.bats (bd-missing and broken-CAIRN_LEASE-path tests for both hooks)"
        status: pass
    human_judgment: false

# Metrics
duration: ~55min
completed: 2026-07-31
status: complete
---

# Phase 15 Plan 04: Session hooks Summary

**session-start.sh best-effort renews, session-stop.sh releases (worktree-scoped), and a hook-never-ran test proves the resulting staleness is visible on two independent surfaces without either hook running.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-07-31T01:55:47-03:00
- **Tasks:** 2 (Task 1: tracer, Task 2: auto/test)
- **Files modified:** 3 (2 hooks, 1 test file)

## Accomplishments
- `session-start.sh` fires a best-effort, backgrounded `cairn-lease.sh renew --project-dir <dir>` (no phase argument — `renew`'s own `STATE.md` `active_phase` resolution decides what, if anything, gets renewed) inside the existing `.planning/` + `.beads/` guard, never outside it
- `session-stop.sh` synchronously calls `cairn-lease.sh release --mine --project-dir <dir> --json`, parses the result, and prints one `[cairn] session ending — released N phase lease(s) you were holding: <phases>` line — silent when nothing was released, exactly like the existing in_progress-issue check's own silence-when-clean behavior
- `release --mine`'s worktree-scoped identity is proven, not assumed: a real second `git worktree` holding a lease is left completely untouched by `session-stop.sh` run from a different worktree
- The phase's riskiest, explicitly-named assumption (D-03: "if the hooks don't run, the lease expires underneath a live session") is closed with a real test: a lease acquired and then simply left alone (heartbeat hand-advanced past the 4h TTL via `bd update` directly — never a real sleep, and neither hook is invoked anywhere in the test) is independently reported stale by both `cairn-lease.sh status --json` (`stale: true`) and `cairn-doctor.sh --json` (`lease-stale` check, `status: "warn"`, itemized by phase and holder)
- Both hooks keep their "never fail the caller" contract intact: exit 0 unconditionally when `bd` is missing from PATH, when `.planning/`/`.beads/` are absent, and when `CAIRN_LEASE` points at a nonexistent/unexecutable path — no traceback in any case

## Task Commits

Each task was committed atomically:

1. **Task 1: session-start renews, session-stop releases** - `e2f2db0` (feat)
2. **Task 2: the hook-never-ran risk — staleness must be visible, not silent** - `bcd4831` (test)

**Plan metadata:** committed separately after this SUMMARY (docs: complete plan) — deferred per this worktree's explicit instruction not to touch shared `.planning/STATE.md`/`ROADMAP.md`/`REQUIREMENTS.md`; the orchestrator reconciles those.

## Files Created/Modified
- `cairn/hooks/session-start.sh` - added the `HOOK_DIR`/`PLUGIN_ROOT`/`CAIRN_LEASE` seam (mirroring `post-bd-write.sh`) and a fourth, backgrounded job inside the existing `.planning/` + `.beads/` guard
- `cairn/hooks/session-stop.sh` - added the same `CAIRN_LEASE` seam and a synchronous `release --mine` call + one-line confirmation, after the existing (untouched) in_progress-issue check
- `tests/hooks.bats` - 14 new cases: session-start renew-fires / guard-absent (both directions) / bd-missing / broken-path; session-stop releases-and-confirms / different-worktree-untouched / nothing-held-silent / bd-missing / broken-path; plus the load-bearing hook-never-ran staleness-visibility test. Also generalized `path_without_gh()` into a reusable `path_without_bin(name)` deny-list helper (DRY — the new bd-missing tests needed the identical technique) and extended `make_recorders()` with a `LEASE_STUB`/`LEASE_LOG` recorder pair alongside the existing `GBSYNC`/`MAP`/`GH`/`BD` recorders.

## Decisions Made
See `key-decisions` in frontmatter for the two adaptations (release --mine's JSON shape has no duration field; the hook-never-ran test reuses `make_gsd_fixture` rather than duplicating `make_doctor_fixture`) and the test-isolation decision (distinct `BEADS_ACTOR` at acquire time to keep the lease bookkeeping issue's own bd assignee separate from session-stop's in_progress-issue check during testing).

## Deviations from Plan

### Auto-fixed / adapted issues

**1. [Rule 3 - Blocking] `release --mine --json`'s actual shape is an object, not the array the plan's action text described**
- **Found during:** Task 1 (session-stop.sh implementation)
- **Issue:** The plan's action text says to "Parse its JSON result (an array — reuse the same python3 -c inline-parsing idiom already used for the in_progress-issues check just above it)". `cairn-lease.py`'s actual `release --mine --json` output (shipped in Plan 15-01, unmodified here) is `{"released": N, "holder": "...", "phases": [...]}` — an object with a `phases` array field, not a bare array of per-lease entries.
- **Fix:** Parsed the actual object shape (`json.load(...).get("phases")`) instead of assuming a top-level array. The python3-inline-parsing idiom itself (same try/except/SystemExit shape as the pre-existing in_progress check) is preserved exactly as instructed.
- **Files modified:** cairn/hooks/session-stop.sh
- **Verification:** `tests/hooks.bats#session-stop: releases every lease...` asserts the printed line and a follow-up `cairn-lease.sh status --json` showing `held: false`
- **Committed in:** e2f2db0 (Task 1 commit)

**2. [Rule 2 - discovered, deferred, not fixed here] session-stop.sh's pre-existing in_progress-issue check also catches the lease bookkeeping issue itself in real (non-test) usage**
- **Found during:** Task 1, while designing the release-and-confirm test
- **Issue:** Measured live: `cairn-lease.py acquire` calls `bd update <id> --claim`, which sets the underlying bd issue's real `status` to `in_progress` and `assignee` to the actor bd resolves via the same chain (`BEADS_ACTOR`/`git config user.name`/`$USER`) session-stop.sh's own in_progress check uses. In ordinary use (no artificial actor override), a session that holds a lease and then stops would see BOTH the old "in_progress issue(s) still assigned to you: bd close <id> --reason=..." warning (wrong advice for a lease issue — it should never be manually `bd close`d) AND this plan's own correct "released" line.
- **Why not fixed:** 15-04-PLAN.md's Task 1 action text explicitly says "leave [the in_progress-issues check] completely untouched", and this plan's `files_modified` does not authorize a broader change to that block. 15-05-PLAN.md (sibling wave-2 plan) already designs an `is_lease_issue()` exemption for the identical reason in `cairn-status.py`'s status panel — confirming this is a known class of problem the phase design anticipates elsewhere, not a one-off.
- **Where it's tracked:** `.planning/phases/15-phase-lease/deferred-items.md` (new file), with the measured evidence and a suggested one-line fix (filter the `lease` label out of the in_progress query) for a follow-up plan.
- **Test isolation:** `tests/hooks.bats`'s own tests acquire the test lease under a distinct `BEADS_ACTOR` override so the two checks stay observably independent, keeping the test suite's assertions accurate to what THIS plan changed rather than papering over the interaction.

---

**Total deviations:** 2 (1 auto-fixed data-shape adaptation, 1 discovered-and-deferred real interaction, logged not fixed)
**Impact on plan:** The data-shape fix was necessary for Task 1 to work at all against the actual 15-01 contract. The deferred item does not block this plan's must_haves or acceptance_criteria (neither requires session-stop.sh's in_progress check to be lease-aware) and is out of this plan's authorized file scope; it is visible for a follow-up plan instead of silently absorbed.

## Issues Encountered
- Attempted to log the deferred item to `.planning/WINDOWS.md` via `gsd-tools windows append` per the broken-windows ledger convention; the installed `gsd-tools.cjs` in this environment does not recognize a `windows` subcommand (`Error: Unknown command: windows`). Per the ledger's own documented contract, this is optional/best-effort and does not block execution — the deferred item is fully recorded in `.planning/phases/15-phase-lease/deferred-items.md` instead.
- No other issues. All tasks executed, verified with `bats tests/hooks.bats` (32/32 pass) and `bats tests/cairn-lease.bats` (16/16 pass, no regression), and self-check confirmed against a temporary revert to the unmodified hooks (tests 19 and 27 — the two hook-behavior-dependent assertions — correctly failed against the pre-change hooks, proving they are load-bearing rather than exit-code-only checks; the modified hooks were then restored from a scratch backup and the full suite re-verified green).

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Both session-lifecycle hooks are wired to the phase lease (D-03 fully closed, including its named risk). Plan 15-05 (status-panel footer, per D-05) can build on `cairn-lease.py status --all --json` unaffected by this plan — no changes to Plan 15-01's contract were made here. One deferred item is on record in `deferred-items.md` for a future plan to close: excluding `lease`-labeled issues from `session-stop.sh`'s in_progress-issue query, mirroring the `is_lease_issue()` exemption 15-05 is already building for `cairn-status.py`. No blockers.

---
*Phase: 15-phase-lease*
*Completed: 2026-07-31*

## Self-Check: PASSED

All 3 modified files (`cairn/hooks/session-start.sh`, `cairn/hooks/session-stop.sh`, `tests/hooks.bats`) found on disk with the expected changes; both task commits (`e2f2db0`, `bcd4831`) found in `git log`. `bats tests/hooks.bats` (32/32) and `bats tests/cairn-lease.bats` (16/16) both pass with the committed hooks in place; a temporary revert to the unmodified hooks reproduced failures in the two hook-behavior-dependent tests, confirming they are genuinely load-bearing.
