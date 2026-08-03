---
phase: 14-phase-card
plan: "03"
subsystem: cli
tags: [python, cairn-doctor, cairn-status, bats]

requires:
  - phase: 14-phase-card plan 01
    provides: "phase_model()'s disk_state / verify_status keys in cairn-status.py --json"
provides:
  - "check_phase_artifacts() (doctor check 12, id \"phase-artifacts\") — names a PLAN.md missing its SUMMARY.md when the phase has reached disk_state \"verified\", and an NN-VERIFICATION.md with no readable status: field"
  - "the doctor half of D-04's narrowing of the phase card's missing-artifact story: the board renders a bare dash for 'nothing yet'; doctor names the unexpected gap"
affects: ["/cairn:doctor CLI output and JSON contract", "cairn/docs/commands/doctor.md"]

tech-stack:
  added: []
  patterns:
    - "Reuse main()'s already-computed disk_incomplete_reasons() dict instead of a second frontmatter parser — the same 'compute once, cross-reference against a second subprocess read' shape check_phase_corroboration() established for check 11"
    - "A check gated on a DERIVED state (disk_state == \"verified\"), not on the raw fact that motivated it (a plan lacking its SUMMARY) — narrowing the trigger to avoid firing on ordinary in-progress work, with the resulting false-negative documented in the docstring rather than left as a silent trap"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-doctor.py
    - tests/cairn-doctor.bats
    - cairn/docs/commands/doctor.md

key-decisions:
  - "The missing-SUMMARY half is gated on disk_state == \"verified\", not on every disk_incomplete_reasons() entry — an earlier, ungated version (the plan's own read_first note) fired on any phase between waves with an unsummarized plan, which a plan-checker caught as noise. A phase someone ran /cairn:verify on despite an unsummarized plan is the genuine anomaly; a phase still being worked is not."
  - "Documented, not hidden: a phase stuck at disk_state \"executed\" (SUMMARY-less plan, VERIFICATION.md never written, nobody runs /cairn:verify) never reaches \"verified\" and so never fires this check either. Written into check_phase_artifacts()'s docstring and the module docstring's check-12 entry as an accepted trade — the false negative the narrowed gate exchanges for removing the mid-flight false positive."
  - "Inserted as check 12 (between phase-corroboration and external-ref) rather than appended last, so the module docstring, the checks=[] wiring order, and the physical file layout all agree; external-ref was renumbered 12 -> 13 everywhere it appears (module docstring, doctor.md, the bats section banner) since it was the only check whose number moved."
  - "Status is warn/ok only, never fail — a missing SUMMARY or unreadable verdict is record hygiene, not contradictory evidence about what happened, matching D-01's 'cairn never stops the flow' applied to hygiene rather than correctness findings."
  - "[Deviation, Rule 2] Synced cairn/docs/commands/doctor.md (new routing entry, check count 13 -> 14, external-ref renumbered) even though the plan's files_modified list only named the two .py/.bats files — CONVENTIONS.md's Documentation-as-Contract section states this doc is load-bearing, and every prior check addition kept it in sync."

requirements-completed: [CARD-02]

coverage:
  - id: D1
    description: "A phase whose disk_state has reached \"verified\" while one of its PLAN.md files still lacks its own SUMMARY.md is named, by filename, by the phase-artifacts check"
    requirement: "CARD-02"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#phase-artifacts: verified phase with an unsummarized plan warns, names the file, never fails the run"
        status: pass
    human_judgment: false
  - id: D2
    description: "A phase whose NN-VERIFICATION.md carries no readable status: field is named by the phase-artifacts check"
    requirement: "CARD-02"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#phase-artifacts: verified phase with an unreadable VERIFICATION status warns, never fails the run"
        status: pass
    human_judgment: false
  - id: D3
    description: "An ordinary mid-flight phase (two plans, one summary, no VERIFICATION.md yet — disk_state short of \"verified\") produces ZERO items — the false-positive regression the narrowed gate exists to prevent"
    requirement: "CARD-02"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#phase-artifacts: same two-plan/one-summary phase with NO VERIFICATION.md produces zero items (mid-flight regression)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The check's status is always \"ok\" or \"warn\", never \"fail\" — a lone phase-artifacts warn never turns an otherwise-clean doctor run into exit 7"
    requirement: "CARD-02"
    verification:
      - kind: unit
        ref: "tests/cairn-doctor.bats#phase-artifacts: a lone phase-artifacts warn never turns an otherwise-clean run into a failure"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-07-31
status: complete
---

# Phase 14 Plan 3: phase-artifacts doctor check Summary

**`/cairn:doctor` gains check 12 ("phase-artifacts"), naming a PLAN.md missing its SUMMARY on a verified phase and an unreadable VERIFICATION.md status, gated on `disk_state == "verified"` to avoid firing on ordinary mid-flight work.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-07-31T01:13:00-03:00 (immediately after 14-02's completion commit)
- **Completed:** 2026-07-31T01:58:00-03:00
- **Tasks:** 2 (both `tdd="true"`)
- **Files modified:** 3 (`cairn/scripts/cairn-doctor.py`, `tests/cairn-doctor.bats`, `cairn/docs/commands/doctor.md`)

## Accomplishments

- `check_phase_artifacts()` added to `cairn-doctor.py` as check 12, id `"phase-artifacts"`: shells to `cairn-status.py --json` (the same subprocess pattern `check_phase_corroboration()` already uses) and cross-references `main()`'s already-computed `disk_reasons` against each phase's `disk_state`, so no second frontmatter parser was added to the file.
- The missing-SUMMARY half fires **only** for a phase that has reached `disk_state == "verified"` (has an `NN-VERIFICATION.md`) — the narrowed gate the plan's `read_first` note called out as the fix for an earlier, ungated draft that fired on every mid-flight phase.
- The unreadable-verdict half fires for any `"verified"` phase whose `NN-VERIFICATION.md` has no readable `status:` field.
- Both halves are `warn`-only; the check's own status is never `"fail"`.
- Five new bats tests cover: the clean/`ok` case, both warn shapes (each isolated so exactly one item fires), the sibling mid-flight regression proving the narrowed gate holds (same two-plan/one-summary fixture, minus the `VERIFICATION.md`, produces zero items), and a dedicated "lone warn never fails the run" assertion.
- `cairn/docs/commands/doctor.md` synced: a new routing entry for `phase-artifacts` between `phase-corroboration` and `external-ref`, the check-count bump (13 → 14), and `external-ref`'s renumbering (12 → 13) reflected in its own module-docstring entry and the illustrative sample report.

## Task Commits

1. **Task 1: check_phase_artifacts — missing SUMMARY and unreadable verify_status (D-04)** - `d4efdd7` (feat)
2. **Task 2: bats coverage — warn cases, mid-flight false-positive regression, never-fail, degrade path** - `f031079` (test, also carries the doctor.md doc sync)

_No plan-metadata commit was made — see "Deviations from Plan" below for why STATE.md/ROADMAP.md/REQUIREMENTS.md were left untouched in this worktree._

## Files Created/Modified

- `cairn/scripts/cairn-doctor.py` — `check_phase_artifacts()` (check 12), module docstring updated (check count, new entry, external-ref renumbered), wired into `main()`'s `checks = [...]` list
- `tests/cairn-doctor.bats` — new `phase-artifacts` test block (5 tests), healthy-fixture check-count assertion bumped 13 → 14, external-ref section banner renumbered
- `cairn/docs/commands/doctor.md` — new routing entry, check count, sample report line, renumbered external-ref entry

## Decisions Made

See `key-decisions` in the frontmatter above. The two load-bearing ones: (1) the missing-SUMMARY half is gated on `disk_state == "verified"`, not on every `disk_incomplete_reasons()` gap, to avoid warning on ordinary in-progress phases; (2) the resulting false-negative (a phase stuck at `"executed"` that never gets verified never fires this check) is written into the docstring as an accepted, deliberate trade rather than left as an undocumented gap.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Synced `cairn/docs/commands/doctor.md`**
- **Found during:** Task 1/2 (adding the check)
- **Issue:** The plan's `files_modified:` frontmatter lists only `cairn-doctor.py` and `cairn-doctor.bats`, but `CONVENTIONS.md`'s Documentation-as-Contract section calls `cairn/docs/commands/doctor.md` load-bearing, and my own task briefing explicitly flagged it: "a new check needs its routing entry, and every prior check addition kept this file in sync."
- **Fix:** Added a `phase-artifacts` routing entry (between `phase-corroboration` and `external-ref`), bumped "thirteen checks" → "fourteen checks", renumbered `external-ref`'s own check number (12 → 13), and added a `phase-artifacts` line to the illustrative sample report.
- **Files modified:** `cairn/docs/commands/doctor.md`
- **Verification:** Manual read-through against the pattern every prior check entry follows; no automated test covers doctor.md prose.
- **Committed in:** `f031079` (part of Task 2's commit)

**2. [Rule 2 - Missing Critical] Neutralized incidental phase-corroboration confounds in the new bats fixtures**
- **Found during:** Task 2 (writing the bats tests)
- **Issue:** Three of the five new tests push phase 2 to `disk_state` `"executed"` or `"verified"` while its bd issue (`$DOC_P2`) stays open and `STATE.md`'s `active_phase` still points at 2 — both trip `phase-corroboration`'s own R1 (`blocks`, disk-vs-bd) and R3 (`informs`, state_md-vs-disk) conflicts, an unrelated check's findings bleeding into assertions meant to isolate `phase-artifacts`' own behavior. One test (`... NO VERIFICATION.md produces zero items`) initially failed the overall exit-code assertion for exactly this reason.
- **Fix:** Added a `neutralize_phase2_corroboration()` bats helper (closes `$DOC_P2`, regenerates phase 2's map, points `active_phase` at a nonexistent phase number) and called it in every test that pushes phase 2 past `"planned"`.
- **Files modified:** `tests/cairn-doctor.bats`
- **Verification:** `bats tests/cairn-doctor.bats -f phase-artifacts` — 5/5 passing; full suite `bats tests/cairn-doctor.bats` — 43/43 passing.
- **Committed in:** `f031079` (part of Task 2's commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2 — missing critical functionality: doc sync and test-fixture isolation)
**Impact on plan:** Both were necessary for the check to be genuinely load-bearing (documented) and for the tests to actually isolate what they claim to test. No scope creep — no behavior outside `check_phase_artifacts()` itself was added.

## Issues Encountered

Non-blocking, resolved during Task 2: the mid-flight regression test's fixture (adding a `SUMMARY.md` to phase 2's existing plan, with no `VERIFICATION.md`) moved phase 2's `disk_state` from `"planned"` to `"executed"` — still short of `"verified"` (so `phase-artifacts` itself behaved correctly), but `"executed"` is also enough to trip `phase-corroboration`'s disk-vs-bd axis against the still-open bd issue. Fixed by the `neutralize_phase2_corroboration()` helper documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

`/cairn:doctor` now names both missing-artifact shapes D-04 assigns it (verified-phase-missing-SUMMARY, and unreadable VERIFICATION status), completing the doctor half of D-04's narrowing. The board half (rendering a bare dash for a phase with nothing yet) was already delivered by 14-01/14-02. `requirements: [CARD-02]` was NOT marked complete in `.planning/REQUIREMENTS.md` in this worktree — see the note below.

**Not done in this worktree, by explicit instruction:** `STATE.md`, `ROADMAP.md`, and `REQUIREMENTS.md` were left untouched. My task briefing states these are shared across the three parallel wave worktrees (`CairnGo-phase-14`, `CairnGo-phase-15`, and the orchestrator's own `CairnGo`) and are "reconciled by the orchestrator at merge" — so the generic execute-plan workflow's `state_updates` and `final_commit` steps (which would run `gsd-tools query state.*`, `roadmap update-plan-progress`, and `requirements mark-complete CARD-02`) were skipped intentionally. The orchestrator needs to run `requirements mark-complete CARD-02` (and the STATE.md/ROADMAP.md progress updates) once this worktree's branch is merged.

---
*Phase: 14-phase-card*
*Completed: 2026-07-31*
