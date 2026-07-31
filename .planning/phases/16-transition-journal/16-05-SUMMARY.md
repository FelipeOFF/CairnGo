---
phase: 16-transition-journal
plan: "05"
subsystem: infra
tags: [python, bats, journal, corroboration, doctor, gitignore]

requires:
  - phase: 16-transition-journal (plan 01)
    provides: "cairn-journal.py's `last-moved --phase N --json` contract —
      per-axis {value, ts} dict, null when never observed, including for
      a phase with no journal file at all"
  - phase: 16-transition-journal (plan 04)
    provides: "cairn-status.py's own CAIRN_JOURNAL env-seam convention for
      shelling into cairn-journal.py — mirrored here for doctor.py's own
      call into the same script"
provides:
  - "check_phase_corroboration()'s per-conflict-item text now cites each
    cited source's last-moved timestamp (JOUR-02, D-04's 'dentro do
    relatório de conflito' — the ONLY place the journal's history
    surfaces by design)"
  - "journal_last_moved(root, phase) / _last_moved_clause() — the
    shell-out-and-degrade-to-nothing helper pair, gated by a new
    CAIRN_JOURNAL env seam on cairn-doctor.py matching cairn-lease.py's
    and cairn-status.py's existing convention for this same script"
  - ".cairn/journal.jsonl* in .gitignore — the entry the journal has
    needed since Plan 16-01 first wrote to it, as a glob that also covers
    compact()'s tmp-write and lock-file siblings"
affects: []

tech-stack:
  added: []
  patterns:
    - "purely additive report enrichment: journal_last_moved()'s result
       only ever appends text to an item whose status/severity was
       already fully decided by corroborate()'s own 'severity' field —
       a broken/missing journal degrades the trailing clause to nothing,
       never the item's severity or the check's own exit code (T-16-09)"
    - "call-once-per-phase caching (last_moved_cache, a local dict keyed
       by phase number) for a subprocess call that would otherwise scale
       with conflict-item count, not phase count"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-doctor.py
    - cairn/docs/commands/doctor.md
    - tests/cairn-doctor.bats
    - .gitignore

key-decisions:
  - "journal_last_moved() reads a CAIRN_JOURNAL env seam (default: the
     sibling cairn-journal.py) rather than hardcoding SCRIPTS_DIR like
     check_lease_stale() does for cairn-lease.py. This is necessary, not
     cosmetic: it is the only way a test can make doctor's OWN last-moved
     read fail independently of cairn-status.py's internal observe call
     (both inherit the same env var from one `env CAIRN_JOURNAL=...`
     invocation), which the plan's own acceptance criteria requires
     ('CAIRN_JOURNAL=/nonexistent/path ... only the last-moved clause is
     missing'). Verified this is load-bearing by temporarily removing the
     returncode check and watching the degrade test fail for exactly the
     predicted reason (see Deviations)."
  - "the 'bd never observed' acceptance scenario (Task 1's first
     criterion) requires cairn-status.py's OWN internal journal_observe_
     phases() call — which runs synchronously, inside the very same
     cairn-doctor.py invocation, moments before doctor's own last-moved
     read — to be blocked, or bd's real value would get journaled a few
     milliseconds before doctor reads it back, and 'never observed' would
     never be literally true. The test achieves this with a CAIRN_JOURNAL
     stub that fails ONLY on the `observe` subcommand (blocking
     cairn-status.py's write) and execs into the real cairn-journal.py
     for every other subcommand (letting doctor's own `last-moved` read
     succeed against the real, pre-seeded journal) — the same
     exec-through-after-intercepting technique tests/cairn-status.bats
     already uses for its call-counting stub, extended to be selective by
     subcommand."

requirements-completed: [JOUR-02]

coverage:
  - id: D1
    description: "a real disk-vs-bd conflict item names disk's exact
      seeded last-moved timestamp and the literal phrase 'never observed'
      for bd, which the journal genuinely never recorded"
    requirement: JOUR-02
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#last-moved: a real conflict item
          names each cited source's last-moved timestamp, or 'never
          observed'"
        status: pass
    human_judgment: false
  - id: D2
    description: "a broken CAIRN_JOURNAL leaves phase-corroboration's
      status and item count byte-identical to a working journal — only
      the trailing last-moved clause is missing, never a change to
      fail/warn/ok or the conflict count"
    requirement: JOUR-02
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#last-moved: a broken CAIRN_JOURNAL
          leaves status/detail identical to a working journal, only the
          clause is missing"
        status: pass
    human_judgment: false
  - id: D3
    description: "journal_last_moved() is called at most once per phase,
      never once per conflict item, even when a single phase carries two
      simultaneous conflicts (disk-vs-bd and roadmap-vs-disk)"
    requirement: JOUR-02
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#last-moved: journal_last_moved() is
          called at most once per phase, not once per conflict item"
        status: pass
    human_judgment: false
  - id: D4
    description: ".cairn/journal.jsonl and its compaction temp/lock
      siblings are never staged by git add -A against the repo's own
      real .gitignore"
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#gitignore: journal.jsonl and its
          compaction temp siblings are never staged by git add -A"
        status: pass
    human_judgment: false

duration: ~55min
completed: 2026-07-31
status: complete
---

# Phase 16 Plan 05: Doctor's Last-Moved Enrichment + Journal .gitignore Summary

**check_phase_corroboration()'s conflict items now cite each cited source's last-moved timestamp from cairn-journal.py, cached once per phase and degrading cleanly to no clause when the journal is broken or absent — plus the .cairn/journal.jsonl* .gitignore entry the journal has needed since Plan 16-01.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-07-31
- **Tasks:** 2/2
- **Files modified:** 4 (cairn-doctor.py, doctor.md, tests/cairn-doctor.bats, .gitignore)

## Accomplishments

- `journal_last_moved(root, phase)`: shells to `cairn-journal.py last-moved --phase N --json` through a new `CAIRN_JOURNAL` env seam (default: the sibling script — matches cairn-lease.py's/cairn-status.py's existing convention for this identical script), returning `None` on any failure (missing script, nonzero exit, unparsable JSON) — mirrors `check_lease_stale()`'s shell-out-and-degrade shape.
- `_last_moved_clause(last_moved, sources)`: `"<source> last moved <ts>"` per cited source, or the literal `"never observed"` when the journal has no record for that axis — never a blank, never a fabricated timestamp.
- `check_phase_corroboration()` calls `journal_last_moved()` **at most once per phase** (`last_moved_cache`, a local dict populated lazily), never once per conflict item — proven, not just asserted, via a call-counting `CAIRN_JOURNAL` stub against a phase carrying two simultaneous conflicts.
- The enrichment is purely additive: it appends a trailing clause to an item whose `status`/`severity` was already fully decided by `corroborate()`'s own `severity` field — a broken/missing journal degrades the clause to nothing, never the check's own status or exit code (T-16-09).
- `.cairn/journal.jsonl*` added to `.gitignore` as a **glob**, not a bare filename — confirmed load-bearing: narrowing it to the bare filename left `journal.jsonl.tmp-*` and `journal.jsonl.compact.lock` staged by `git add -A` in the regression test.
- `cairn/docs/commands/doctor.md` kept in sync with the new report text (the check's docstring format changed).

## Task Commits

Each task was committed atomically, RED → GREEN for Task 1 (a genuinely failing test commit, then the implementation that turns it green):

1. **Task 1 (RED): failing tests for last-moved enrichment** — `5e0866b` (test)
2. **Task 1 (GREEN): check_phase_corroboration() cites each conflict source's last-moved timestamp** — `9fc837f` (feat)
3. **Task 2: ignore the journal and its compaction temp siblings** — `bda93f0` (feat)

**Plan metadata:** committed alongside this SUMMARY (see final commit below).

## Files Created/Modified

- `cairn/scripts/cairn-doctor.py` — `CAIRN_JOURNAL` env seam constant, `journal_last_moved()`, `_last_moved_clause()`, `check_phase_corroboration()`'s per-phase loop (cache + clause composition), both docstrings updated
- `cairn/docs/commands/doctor.md` — phase-corroboration's doc entry updated to describe the new trailing last-moved clause
- `tests/cairn-doctor.bats` — 3 new `last-moved:`-titled tests (seeded-timestamp + never-observed, broken-CAIRN_JOURNAL degrade, call-count), 1 new `gitignore:`-titled test
- `.gitignore` — `.cairn/journal.jsonl*` entry

## Decisions Made

1. **`journal_last_moved()` reads a `CAIRN_JOURNAL` env seam rather than hardcoding `SCRIPTS_DIR`.** See `key-decisions` in the frontmatter above for the full reasoning — this is what makes the plan's own "`CAIRN_JOURNAL=/nonexistent/path` degrades to no clause" acceptance criterion achievable, and I verified it is load-bearing (see Deviations/Load-Bearing Verification below).
2. **The "bd never observed" test uses a subcommand-selective stub.** cairn-status.py's own internal `journal_observe_phases()` call (Plan 16-04) runs synchronously inside the same doctor invocation, moments before doctor's own last-moved read — so bd's real value would otherwise get journaled before the read, and "never observed" could never be literally true for a real conflict. The stub blocks only the `observe` subcommand and execs into the real script for everything else, letting disk's earlier-seeded value read back untouched while bd genuinely never gets recorded.
3. **The 3 `last-moved:`-titled tests and 1 `gitignore:`-titled test satisfy the plan's own `-f "last-moved"` / `-f "gitignore"` filter commands exactly** — verified directly (3 and 1 respectively, no over- or under-selection).

## Deviations from Plan

None requiring a Rule 1-4 classification — the plan's literal `<action>` text for `journal_last_moved()` showed a hardcoded `SCRIPTS_DIR`-based subprocess call with no env seam, but its own acceptance criteria (the `CAIRN_JOURNAL=/nonexistent/path` degrade test) is only achievable if the call reads that env var — the two pieces of the same task specification only cohere with the env-seam reading, which is also literally what the plan's own `key_links` line points at ("the same shell-out-and-parse-defensively pattern check_lease_stale() ... already use[s]" — describing the *degrade shape*, not the *hardcoded-path* detail, since check_lease_stale() itself has no env seam at all). Implemented with the env seam; documented here as the resolution of that internal tension rather than a Rule-4 architectural change, since it adds zero new surface beyond the `CAIRN_JOURNAL` name already established by two sibling scripts for this identical target script.

## Issues Encountered

None — no auth gates, no package installs, no blockers.

## Load-Bearing Verification (not just asserted)

Per this plan's own standard ("what_would_make_this_wrong"), every new assertion was proven by breaking the corresponding production code and watching the test go red, then restoring:

1. **Call-once-per-phase caching.** Removed the `last_moved_cache` guard (called `journal_last_moved()` unconditionally per conflict item instead of once per phase). Re-ran the call-count test: **failed** — `n_last_moved` was `2`, not `1`, for phase 2's two simultaneous conflicts. Restored; passed again.
2. **The enrichment clause itself.** Disabled the `if clause: line = ...` append (`if False and clause:`). Re-ran the last-moved filter: **both** the seeded-timestamp test and the degrade-comparison test failed (the latter because "last moved" never appears in the *working* run either, so the two runs are trivially identical — proving that test also depends on the enrichment actually firing). Restored; both passed again.
3. **The `CAIRN_JOURNAL`-respecting degrade path specifically.** Removed only the `if proc.returncode != 0: return None` check (leaving the try/except and JSON-parse guard intact), so a broken path (`/nonexistent/path`) would still `json.loads("{}")` successfully into an all-null dict instead of returning `None`. Re-ran: the degrade test **failed** at exactly the predicted assertion (`refute_in_output "last moved"` — a clause DID appear, built entirely from "never observed" entries, because the `{}` fallback masked the failure). Restored; passed again. This isolates that the *returncode check specifically* — not merely "some" error handling — is what the degrade test proves.
4. **The `.gitignore` entry.** Removed `.cairn/journal.jsonl*` from `.gitignore` entirely. Re-ran the gitignore test: **failed** (`journal.jsonl` unexpectedly staged). Restored; passed again.
5. **The glob, specifically (not just the bare filename).** Narrowed the entry to the bare `.cairn/journal.jsonl` (no trailing `*`). Re-ran: **failed** — the compaction tmp/lock siblings were still staged, proving the glob (not the bare filename) is what the acceptance criteria required. Restored the glob; passed again.

Every one of these five experiments left the file in a diff-clean, byte-identical-to-final state after restoration (confirmed via `git status --short` showing no stray `TEMP` markers before the final commits).

## User Setup Required

None — stdlib only, no external service configuration.

## Verification

- `bats tests/cairn-doctor.bats -f "last-moved"` — 3/3 passing (run repeatedly throughout, including after each load-bearing break/restore cycle)
- `bats tests/cairn-doctor.bats -f "gitignore"` — 1/1 passing (same)
- `bats tests/cairn-doctor.bats -f "phase-corroboration"` — 4/4 passing (pre-existing tests, unaffected — confirms the enrichment is purely additive)
- `bats tests/cairn-doctor.bats` (full suite, all 55 tests) — **55/55 passing, exit 0** (run once before the RED/GREEN restructuring at 51/51 pre-existing + 4 new, then re-run after final commits — see the session's own record; both runs green)
- `bats tests/cairn-status.bats` (regression) — 55/55 passing, unaffected
- `bats tests/cairn-journal.bats` (regression, per this plan's own execution notes) — 16/16 passing, unaffected
- `git status --porcelain` on this repo after this plan's changes — clean, no stray `.cairn/journal.jsonl` or `TEMP` markers left behind

## Next Phase Readiness

- This is the last plan of Phase 16 (wave 3). JOUR-01 through JOUR-05 are now all closed: the journal writer/reader (16-01), compaction (16-02), lease wiring (16-03), corroboration wiring + the JOUR-03 independence proof (16-04), and now the doctor enrichment + `.gitignore` entry (16-05, JOUR-02's own report-surfacing half).
- No blockers, no deferred work, no known stubs.

---
*Phase: 16-transition-journal*
*Completed: 2026-07-31*

## Self-Check: PASSED

- FOUND: cairn/scripts/cairn-doctor.py
- FOUND: cairn/docs/commands/doctor.md
- FOUND: tests/cairn-doctor.bats
- FOUND: .gitignore
- FOUND: .planning/phases/16-transition-journal/16-05-SUMMARY.md
- FOUND commit: 5e0866b
- FOUND commit: 9fc837f
- FOUND commit: bda93f0
- Full suite re-run at self-check time: `bats tests/cairn-doctor.bats` — 55/55 passing (14m09s, confirmed via background run after final commits)
- Regression re-run: `bats tests/cairn-status.bats` — 55/55 passing; `bats tests/cairn-journal.bats` — 16/16 passing
