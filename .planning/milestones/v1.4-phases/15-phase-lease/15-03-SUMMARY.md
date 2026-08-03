---
phase: 15-phase-lease
plan: "03"
subsystem: infra
tags: [bd, beads, cairn-doctor, bats]

# Dependency graph
requires:
  - phase: 15-phase-lease (Plan 15-01)
    provides: "cairn-lease.py status --all --json — the single TTL/staleness authority this check shells out to"
provides:
  - "cairn-doctor.py check 13 (lease-stale): a WARN-only report of every phase whose lease is currently held and stale, mirroring check 8 (claims-stale)'s discipline one level up"
  - "NO_PHASE_EXEMPT extended with 'lease' — the lease bookkeeping issue is never flagged by check 6 (orphans)"
affects: [15-04, 15-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "shell-out-to-a-sibling-script pattern (already used by check_maps_fresh() for cairn-map.py --check and check_phase_corroboration() for cairn-status.py --json) applied to a fourth sibling script, cairn-lease.py"
    - "never-fail WARN-only check discipline (check 8 claims-stale's own posture) applied one level up to a stale phase lease — a reclaimable condition is never a doctor failure"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-doctor.py
    - tests/cairn-doctor.bats
    - cairn/docs/commands/doctor.md

key-decisions:
  - "check_lease_stale() degrades to WARN (never crashes the doctor run) on a non-zero cairn-lease.py exit OR unparsable JSON, matching check_phase_corroboration()'s own degrade shape exactly — verified with a targeted bd wrapper that fails only the lease-label lookup, not bd entirely, so the rest of the doctor run stays observably green while lease-stale alone degrades"
  - "NO_PHASE_EXEMPT's comment was expanded to explain WHY the lease issue is exempt (it would otherwise look like real phase work to phase-complete-open, phase-corroboration, and work.md's own done-check), not just that it is"
  - "cairn/docs/commands/doctor.md — not in the plan's files_modified frontmatter — was updated in lockstep anyway (routing entry, reads list, worked example, thirteen->fourteen count) since the plan's own files_to_read flagged it as load-bearing and every prior check addition (11, 12) kept it in sync; tracked below as a deviation"

requirements-completed: [LEASE-04, LEASE-05]

coverage:
  - id: D1
    description: "a stale phase lease (heartbeat older than 4h) WARNs, itemized by phase/holder/actor/since-when with the reclaim path, and the doctor run still exits 0 — never 7"
    requirement: "LEASE-05"
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#lease-stale: a lease with a heartbeat older than 4h warns, itemized by phase and holder, exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "a freshly-acquired lease (no stale heartbeat) reads ok, empty items"
    requirement: "LEASE-05"
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#lease-stale: a freshly-acquired lease (no stale heartbeat) reads ok, empty items"
        status: pass
    human_judgment: false
  - id: D3
    description: "the healthy fixture (no lease ever touched) reports the new check ok, and .checks | length is 14"
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#healthy wired fixture: exit 0, every check ✓"
        status: pass
    human_judgment: false
  - id: D4
    description: "a created-then-released (vacant) lease issue is never flagged by check 6 (orphans) — exempted by its lease label, not merely absent from the roadmap-phase set"
    requirement: "LEASE-04"
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#lease-stale: the lease bookkeeping issue is exempt from check 6 (orphans) even vacant"
        status: pass
    human_judgment: false
  - id: D5
    description: "cairn-lease.py itself failing (bd unreachable for its own lease-label lookup) degrades lease-stale to warn with an explanatory detail, never a traceback, and never crashes the surrounding doctor run"
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#lease-stale: cairn-lease.py itself failing degrades to warn, never crashes the doctor run"
        status: pass
    human_judgment: false

# Metrics
duration: 40min
completed: 2026-07-31
status: complete
---

# Phase 15 Plan 03: Phase lease Summary

**`cairn-doctor.py` check 13 (`lease-stale`): a stale phase lease reported by phase/holder/since-when, WARN-only, mirroring check 8 (`claims-stale`)'s discipline one level up — a stale lease is reclaimable, never a doctor failure.**

## Performance

- **Duration:** ~40 min (includes a 10m35s full `bats tests/cairn-doctor.bats` run)
- **Completed:** 2026-07-31T00:48:15-03:00
- **Tasks:** 1 (Task 1: tracer/TDD)
- **Files modified:** 3 (all modified, none created)

## Accomplishments
- `check_lease_stale(root)`: shells to `cairn-lease.py status --all --json`, itemizes every phase whose lease is `held` AND `stale`, naming phase, holder, actor, `acquired_at`, `heartbeat_at`, and the reclaim path ("reclaimable — the next `/cairn:work N` takes it automatically, or run `cairn-lease.sh release N` to clear it now"). Status is `warn` when any items exist, `ok` otherwise — never `fail`.
- `NO_PHASE_EXEMPT` extended with `"lease"`, closing the exact gap the plan's `<what_matters_most>` flagged: without it, every held lease (which by design carries only the `lease` label, never `phase-<N>`) would trip check 6 (orphans) permanently.
- A non-zero `cairn-lease.py` exit or unparsable JSON degrades `lease-stale` to `warn` with an explanatory detail — proven with a bd wrapper that fails only the `-l lease` lookup while every other check in the same doctor run stays green, not merely inferred from the code.
- Module docstring (check 0's own "N checks in total" line, plus the full check-13 entry) and `cairn/docs/commands/doctor.md` (routing entry, reads list, worked example, count) updated in lockstep.
- `tests/cairn-doctor.bats`: the healthy-fixture `.checks | length` assertion bumped 13 -> 14, plus 4 new cases covering the plan's full `acceptance_criteria` list.

## Task Commits

Each task was committed atomically:

1. **Task 1: check 13 — lease-stale, itemized and WARN-only** - `6ded264` (feat) — `check_lease_stale()`, `NO_PHASE_EXEMPT` extension, docstring/doc sync, 4 new bats cases; all 42 `tests/cairn-doctor.bats` cases pass, plus 16/16 `tests/cairn-lease.bats` (regression check).

## Files Created/Modified
- `cairn/scripts/cairn-doctor.py` (modified) - `check_lease_stale()` (check 13), `NO_PHASE_EXEMPT` extended with `"lease"`, module docstring (check-0 total line + new check-13 entry), wired into `main()`'s `checks = [...]` list
- `tests/cairn-doctor.bats` (modified) - healthy-fixture count assertion 13 -> 14; new "lease-stale (check 13, LEASE-05) — 15-03" section with 4 cases
- `cairn/docs/commands/doctor.md` (modified) - new `lease-stale` routing bullet, `(...) — fourteen checks in total`, worked example gains a `✓ lease-stale` line, Reads list mentions `cairn-lease.py status --all --json`

## Decisions Made
- Placed `check_lease_stale()` and its section comment immediately before the "output + main" section (after `check_external_ref()`), matching its position as the last item in `main()`'s `checks = [...]` list — consistent with how checks 11/12 were appended when they were added.
- For the "`cairn-lease.py` itself would fail" acceptance criterion, built a bd wrapper that intercepts only invocations carrying the literal token `"lease"` (i.e. `cairn-lease.py`'s own `bd list -l lease --all ...` call) and passes every other invocation through to the real `bd` binary — rather than reusing the existing "bd missing from PATH" fixture verbatim (which strips `bd` from PATH entirely and makes `cairn-doctor.py`'s OWN top-level `shutil.which("bd")` preflight die before any check ever runs, so `lease-stale`'s own degrade branch would never be observable in that scenario). This narrower wrapper is the only construction that lets `lease-stale: warn` actually appear in the JSON output while every other check in the same run stays `ok`, which is what the acceptance criterion asks to observe.
- Reused the literal formatting cadence of check 12's docstring entry (the closest sibling in age/shape) for the new check-13 entry, rather than inventing new prose conventions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - missing critical functionality] Updated `cairn/docs/commands/doctor.md` in lockstep, though not in the plan's `files_modified`**
- **Found during:** Task 1 (`<files_to_read>` in the orchestrator's prompt explicitly named this doc "load-bearing" and said "a new check needs its routing entry")
- **Issue:** The plan's frontmatter `files_modified:` lists only `cairn/scripts/cairn-doctor.py` and `tests/cairn-doctor.bats`. But `doctor.md` documents every check's routing, the full check count ("thirteen checks in total"), a worked example listing every check icon, and the files-touched/reads list — all of which checks 11 and 12 kept in sync when they were added. Leaving it stale after adding check 13 would be exactly the kind of doc drift this repo's own doctor discipline exists to prevent.
- **Fix:** Added a `lease-stale` routing bullet (mirroring the `claims-stale`/`phase-corroboration` bullets' shape), bumped "thirteen checks in total" to "fourteen", added `✓ lease-stale` to the worked example's icon grid, and added `cairn-lease.py status --all --json (lease staleness)` to the Reads list.
- **Files modified:** `cairn/docs/commands/doctor.md`
- **Commit:** `6ded264`

No other deviations — the plan's `<behavior>`/`<action>` spec was otherwise followed exactly as written.

## Issues Encountered

None beyond the documented deviation above. Both `bd` and the existing `cairn-lease.py` surface (Plan 15-01) behaved exactly as their own module docstrings describe throughout.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`/cairn:doctor` now surfaces a stale phase lease by phase/holder/since-when, WARN-only, with the lease bookkeeping issue fully exempted from check 6. Plan 15-04 and 15-05 (status-panel footer line, per D-05) can build on `cairn-lease.py status --all --json` unaffected by this plan's changes — Plan 15-01's contract is untouched here. No blockers.

---
*Phase: 15-phase-lease*
*Completed: 2026-07-31*

## Self-Check: PASSED

All 3 modified files found on disk with the expected changes; task commit (`6ded264`) found in git history.
