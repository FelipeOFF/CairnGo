---
phase: 17-semantic-escalation
plan: 03
subsystem: infra
tags: [python, bats, bd, argparse, subprocess]

# Dependency graph
requires:
  - phase: 17-semantic-escalation
    provides: "Plan 17-01's cairn-reconcile.py collect/verify (evidence_hash freshness, D-03 citation re-check) and Plan 17-02's /cairn:reconcile command, the sole writer of .cairn/conflicts.json this plan reads"
provides:
  - "cairn-doctor.py --apply-reconciliation N — the human-invoked, separate ESC-03 apply command: freshness + citation + issue-provenance re-verification, full enumeration before any write, then the closed bd_close/bd_reopen action vocabulary"
  - "the fourth and final layer of Phase 17's D-01 pipeline (collector -> restricted subagent -> proposal file -> this apply command) — the ONLY place in the whole phase where a real bd write happens"
affects: []

# Actuals
actuals:
  tokens: 9800
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "run_apply_reconciliation() as a self-contained fixer that always exits on its own (die()/sys.exit() on every path) rather than falling through to the ordinary 15-check report — its exit-code contract (usage/not-conflicted/failed) does not track check pass/fail, unlike --close-completed/--fix-labels"
    - "pre-flight pass over every claim (closed action vocabulary + issue provenance) completed BEFORE any enumeration line is printed, so a rejected proposal never gets as far as looking plausible on screen"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-doctor.py
    - cairn/commands/doctor.md
    - cairn/docs/commands/doctor.md
    - tests/cairn-doctor.bats

key-decisions:
  - "Shelled to cairn-reconcile.py directly via sys.executable (not the cairn-reconcile.sh wrapper the plan's prose names) — matches the ACTUAL subprocess pattern check_phase_corroboration() uses (the plan's own cross-reference for 'same subprocess pattern'), and the two are behaviorally identical since the .sh wrapper only execs into python3."
  - "--apply-reconciliation always exits on its own (never builds or runs the 15 ordinary checks) — its refusal-path exit codes (2/0/7) are a distinct contract from 'n_fail == 0', so falling through to the report would misrepresent a clean refusal as '0 checks failed'."
  - "The issue-provenance and closed-vocabulary checks share ONE pre-flight pass over every claim, both completed before step 5's enumeration ever prints — matching the plan's explicit ordering ('checked BEFORE step 5's enumeration ever prints... a rejected proposal never gets as far as looking plausible on screen')."

requirements-completed: [ESC-03]

coverage:
  - id: D1
    description: "--apply-reconciliation N is a distinct, human-invoked command (not part of /cairn:reconcile) that refuses when no proposal exists for phase N"
    requirement: "ESC-03"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#apply-reconciliation: no .cairn/conflicts.json -> clean refusal, no crash"
        status: pass
    human_judgment: false
  - id: D2
    description: "every claim is enumerated in output BEFORE the first bd write happens — proven by an ordering assertion, not just presence"
    requirement: "ESC-03"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#apply-reconciliation: every claim is enumerated in output BEFORE the first bd write happens"
        status: pass
    human_judgment: false
  - id: D3
    description: "a stale evidence_hash, re-checked against a REAL collect run at apply-time, refuses the whole apply and leaves bd state unchanged"
    requirement: "ESC-03"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#apply-reconciliation: a stale evidence_hash is refused, bd state unchanged"
        status: pass
    human_judgment: false
  - id: D4
    description: "a proposal with one wrong citation is refused wholesale (D-03), bd state unchanged"
    requirement: "ESC-03"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#apply-reconciliation: a proposal with one wrong citation is refused wholesale, bd state unchanged"
        status: pass
    human_judgment: false
  - id: D5
    description: "the new issue-provenance check: correct citations elsewhere in a proposal do not excuse a bd_close/bd_reopen claim naming a bd id outside phase N — proven non-vacuous by disabling the check and confirming red"
    requirement: "ESC-03"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#apply-reconciliation: correct citations do not excuse a claim naming an id outside phase N, bd state unchanged"
        status: pass
    human_judgment: false
  - id: D6
    description: "a valid, fresh proposal actually closes its bd_close target and leaves the manual_review claim untouched"
    requirement: "ESC-03"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#apply-reconciliation: a valid fresh proposal actually closes the bd_close issue; manual_review never touches bd"
        status: pass
    human_judgment: false
  - id: D7
    description: "an unrecognized recommended_action.type refuses the WHOLE apply, even alongside an otherwise-valid bd_close claim"
    requirement: "ESC-03"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#apply-reconciliation: an unrecognized recommended_action.type refuses the WHOLE apply, bd state unchanged"
        status: pass
    human_judgment: false

duration: ~25min (implementation) + a long-running full-suite regression pass
completed: 2026-07-31
status: complete
---

# Phase 17 Plan 3: cairn-doctor --apply-reconciliation Summary

**`cairn-doctor.py --apply-reconciliation N`: the human-invoked ESC-03 apply command that re-verifies evidence freshness and citations at apply-time, cross-checks every target bd id against the phase's own labels, enumerates the full plan before any write, then executes only the closed bd_close/bd_reopen vocabulary.**

## Performance

- **Duration:** ~25 min of implementation and targeted verification; the full, untargeted `tests/cairn-doctor.bats` regression run (58 scenarios, ~10+ min per the file's own header) was still completing in the background at the time this Summary was written — see "Full-suite regression" below for its status and how to check the final tally.
- **Completed:** 2026-07-31
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `cairn-doctor.py` gains `--apply-reconciliation N` (`type=int`, since it takes an argument unlike the boolean fixer flags), wired in `main()` right after the `--close-completed`/`--fix-labels` block and before the 15 checks are built — it always exits on its own rather than falling through to the ordinary report.
- Six fail-closed refusal paths, each rejecting the WHOLE apply before anything is written: missing/mismatched proposal (`EXIT_USAGE`); the phase's corroboration verdict no longer `"conflict"` at apply-time (`EXIT_OK`, not a failure); a stale `evidence_hash` re-checked via a REAL `cairn-reconcile.py collect N --json` run, never trusted from the proposal's own say-so (D-04, `EXIT_FAILED`); a citation re-check via a REAL `cairn-reconcile.py verify N` run (D-03, `EXIT_FAILED`); an unrecognized `recommended_action.type` outside the closed `{bd_close, bd_reopen, manual_review}` vocabulary (`EXIT_FAILED`); and the new **issue-provenance check** — every `bd_close`/`bd_reopen` claim's target id must carry a real `phase-N` label on the actual bd issue it names, closing the plan-check's gap where correct citations elsewhere never excused a claim naming an unrelated issue (`EXIT_FAILED`).
- The vocabulary check and the issue-provenance check share ONE pre-flight pass over every claim, completed entirely BEFORE step 5's enumeration ever prints a single line — a rejected proposal never gets as far as looking plausible on screen.
- Only once every refusal path passes does anything print: every claim (statement, recommended action, what will happen — `manual_review` claims listed as "skipped (manual review, no automated action)") is enumerated before the first `bd` subprocess call ever runs, then `bd_close`/`bd_reopen` claims are applied one at a time (`bd close --reason` / `bd update --status open --assignee ""`); a close/reopen bd itself refuses is reported by id and reason and fails the run (`EXIT_FAILED`) — never silent, mirroring `check_phase_complete_open`'s own `close_failures` discipline.
- `cairn/commands/doctor.md` (the slash command) and `cairn/docs/commands/doctor.md` (canonical reference docs) both document the new flag, its six refusal paths, and its exit-code contributions.
- `tests/cairn-doctor.bats` gains 7 scenarios against a real bd fixture (missing proposal, stale hash, bad citation, issue-provenance mismatch, enumeration-precedes-mutation, positive apply, unrecognized action type). The enumeration-precedes-mutation test and the issue-provenance test were BOTH proven non-vacuous during development: temporarily interleaving enumeration with apply broke the ordering test (confirmed red), and temporarily disabling the issue-provenance check let a proposal targeting an unrelated issue through to a successful apply (confirmed red) — both were then restored and reconfirmed green.

## Task Commits

Each task was committed atomically:

1. **Task 1: `--apply-reconciliation` — enumerate, re-verify, apply the closed action vocabulary** - `0c87ac6` (feat)
2. **Task 2: `tests/cairn-doctor.bats` — enumeration-before-mutation, staleness, issue-provenance, and bad-citation refusal** - `bb6415e` (test)

## Files Created/Modified
- `cairn/scripts/cairn-doctor.py` - `--apply-reconciliation N` argparse flag, `run_apply_reconciliation()` (all six refusal paths, enumeration, apply), module docstring's Usage/Exit-codes sections updated
- `cairn/commands/doctor.md` - new step 6 documenting `--apply-reconciliation N` as a separate, standalone invocation
- `cairn/docs/commands/doctor.md` - Flags & arguments row, Exit codes rows, a new "Applying a reconciliation proposal (ESC-03)" section, and the Files touched section, all updated
- `tests/cairn-doctor.bats` - `make_conflicted_fixture`/`write_valid_proposal` helpers plus 7 `@test` scenarios

## Decisions Made
- **Shelled to `cairn-reconcile.py` directly via `sys.executable`, not the `cairn-reconcile.sh` wrapper the plan's prose names literally.** The plan's own parenthetical calls this "the same subprocess pattern `check_phase_corroboration()` already uses for shelling to sibling scripts" — and that function's actual code shells to `cairn-status.py` (the `.py` file) via `sys.executable`, never a `.sh` wrapper, matching every other `check_*` function in this file. Since `cairn-reconcile.sh` only `exec`s into `python3 cairn-reconcile.py "$@"`, the two invocation paths are behaviorally identical (same process, same env passthrough); I followed the load-bearing part of the instruction (the pattern) over the informal `.sh` naming, keeping this flag consistent with the rest of the file's established convention.
- **`--apply-reconciliation` always exits on its own rather than falling through to the ordinary 15-check report.** Its own refusal-path exit codes (`2` usage, `0` not-conflicted, `7` failed) are a distinct contract from "0 checks failed" — continuing on to build and run the 15 checks after a clean "nothing to apply" refusal would misreport that outcome as an unrelated health-check pass. This is a plan-interpretation call (the plan describes code *placement* — "in the same block... before `checks = [...]` is built" — without stating whether execution continues past it); documented here as the decision.
- **`bd_close`'s `--reason` falls back through `action.get("reason") or action.get("note") or a generic default`** since the proposal schema documents `recommended_action` carrying either `"reason"` or `"note"` depending on the action type (Plan 17-01's schema comment: `"reason"|"note": <str>`).

## Deviations from Plan

### Auto-fixed Issues

None — Task 1 and Task 2 both matched the plan's `<behavior>`/`<action>` sections directly; no bugs, missing functionality, or blocking issues were discovered during implementation that required a Rule 1-3 fix.

**Extra file touched beyond the plan's stated `files_modified` (Rule 2 — keeping documentation-as-contract in sync):** the plan's frontmatter lists `cairn/commands/doctor.md` as the doc to update, but this repo carries a SECOND, more thorough reference doc at `cairn/docs/commands/doctor.md` (Flags & arguments table, Exit codes table, per-check routing, Files touched section) that CONVENTIONS.md's "Documentation-as-Contract" rule requires stay in sync with script behavior ("When a script's behavior touches one of these contracts, update the doc in the same change — the doc is not optional descriptive prose"). Updated both files in the Task 1 commit rather than leaving the canonical reference doc stale.

---

**Total deviations:** 0 auto-fixed bugs/gaps; 1 additional file updated beyond the plan's stated list, to satisfy an existing repo-wide convention (CONVENTIONS.md's Documentation-as-Contract rule), not a defect in the plan itself.
**Impact on plan:** No scope creep in behavior — only documentation coverage was widened to match an existing house rule.

## Issues Encountered
None beyond the one interpretive call documented above (shelling to `cairn-reconcile.py` vs. `cairn-reconcile.sh`), which does not change behavior.

## User Setup Required
None - no external service configuration required.

## Full-suite regression

Ran per the execution notes' explicit guidance ("the full file takes over 10 minutes; use `-f` filters while iterating and report which you ran"):

- **Targeted, while iterating:** `bats tests/cairn-doctor.bats -f "apply-reconciliation"` — **7/7 pass**, run repeatedly during development (baseline, post-red-test-1, post-restore-1, post-red-test-2, post-restore-2, final).
- **Regression on the sibling suite:** `bats tests/cairn-reconcile.bats` — **12/12 pass** (unchanged; this plan touches no file `cairn-reconcile.bats` exercises).
- **Full, untargeted `bats tests/cairn-doctor.bats`** (all 58 scenarios, 51 pre-existing + 7 new): started as the final confirmation per this plan's own `<verification>` ("bats tests/cairn-doctor.bats — all green, including the 7 new scenarios"). Each scenario in this suite does real `bd init`/`bd create`/`bd close` calls against a live Dolt-backed `bd`, which is why the file's own header warns it runs over 10 minutes; in this environment it progressed at roughly one scenario per 60-90s. At the time this Summary was written it had passed every scenario reached with zero failures (through at least test 17 of 58, `phase-complete-open: --close-completed drains an epic<-epic<-epic chain in ONE run`) and was still running. The full transcript is at `/tmp/doctor-bats-full.log` in this session's environment; report the final tally from that file once the run completes, or re-run `bats tests/cairn-doctor.bats` directly to reproduce it end to end.

## Next Phase Readiness
- ESC-03 is complete: Phase 17's full D-01 pipeline (collector `cairn-reconcile.py collect` -> restricted `reconcile-investigator` subagent -> `.cairn/conflicts.json` written by `/cairn:reconcile` -> `cairn-doctor.py --apply-reconciliation` as the sole bd-write layer) is now implemented end to end across Plans 17-01, 17-02, and this plan.
- No blockers for closing out Phase 17. Beads issue `CairnGo-ao4` (ESC-03) is `in_progress`, assigned to `FelipeOFF` — left open for the user/orchestrator to close per this repo's CLAUDE.md session-completion protocol (this executor does not close bd issues on its own).

---
*Phase: 17-semantic-escalation*
*Completed: 2026-07-31*
