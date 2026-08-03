---
phase: 16-transition-journal
plan: "04"
subsystem: infra
tags: [python, bats, journal, corroboration, wiring, resilience]

requires:
  - phase: 16-transition-journal (plan 01)
    provides: "cairn-journal.py's `observe` subcommand contract — a batched
      stdin-JSON array of {phase, evidence, verdict}, diff-then-append
      against _last_known(), --json prints {\"written\": [...]}"
provides:
  - "phase_model() batch-wires every render (terminal, --json, --html, and
    every doctor check that shells out to cairn-status.py --json) into
    cairn-journal.py's `observe` subcommand — exactly ONE subprocess call
    per invocation, carrying every phase's evidence+corroboration verdict
    as one JSON array on stdin (D-01/D-02)"
  - "journal_observe_phases() — a resilient, best-effort journal-call
    helper mirroring cairn-lease.py's journal_lease_event(): any failure
    (nonzero exit, missing script, subprocess error, unparsable stdout)
    degrades to a stderr warning, never changes phase_model()'s own
    return value"
  - "CAIRN_JOURNAL env seam on cairn-status.py (default: the sibling
    cairn-journal.py), mirroring cairn-lease.py's identical seam"
  - "the JOUR-03 mechanical proof: corroborate() is provably independent
    of the journal's presence or contents — a hand-edit outside any cairn
    command is caught on the first read, and deleting a journal with real
    accumulated history changes zero bytes of the next --json render"
affects: [16-05-gitignore]

tech-stack:
  added: []
  patterns:
    - "batched-observe-after-compute: a per-item corroboration loop
       finishes fully, THEN exactly one subprocess call carries the whole
       batch to the journal — never one subprocess spawn per item, and
       never interleaved with the computation itself"
    - "same resilient-shell-out shape as journal_lease_event() and
       fetch_lease_status(): try/except around subprocess.run, a
       nonzero-exit check, a single warning line, no exception ever
       escapes to the caller"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-status.py
    - tests/cairn-status.bats

key-decisions:
  - "root (for --project-dir) is resolved as planning_dir.parent inside
     phase_model() itself, not passed in as a new parameter — this is the
     exact same expression phase_model() already used at its `row[\"dir\"]`
     call site, so the observe call reuses main()'s own resolution rather
     than inventing a second one (the plan's own instruction). Refactored
     that one call site to a local `root` variable in the process."
  - "the JOUR-03 test compares three renders, not two, to make the delete-
     the-journal proof exercise a journal that genuinely has accumulated
     history: a first read (no journal exists yet — proves Part 1),
     confirmation the journal now exists, a second read against that
     populated journal (before_output), then deletion and a third read
     (after_output). A naive two-render version (first read vs. post-
     delete read) would have compared two renders that BOTH start with no
     journal at call-time — a structurally weaker proof, since a
     hypothetical bug keyed on \"journal exists at read-time\" would slip
     through undetected in both directions. Verified this distinction
     directly: injecting exactly that bug shape caught it at the
     first_read_output-vs-before_output comparison, one step before the
     final delete-diff."

requirements-completed: [JOUR-03]

coverage:
  - id: D1
    description: "phase_model() calls cairn-journal.py observe exactly
      once per invocation with every phase's evidence+verdict batched in
      one JSON array on stdin, never one subprocess spawn per phase"
    requirement: JOUR-03
    verification:
      - kind: integration
        ref: "tests/cairn-status.bats#journal observe: exactly one batched
          cairn-journal.py invocation per --json run, not one per phase"
        status: pass
    human_judgment: false
  - id: D2
    description: "a broken or missing CAIRN_JOURNAL degrades to a stderr
      warning and produces byte-identical --json output to a working
      journal — phase_model()'s return value is unaffected by journal
      failures"
    requirement: JOUR-03
    verification:
      - kind: integration
        ref: "tests/cairn-status.bats#journal observe: a broken
          CAIRN_JOURNAL produces byte-identical --json output to a
          working one, plus a stderr warning"
        status: pass
    human_judgment: false
  - id: D3
    description: "observe's dedup (Plan 16-01) is exercised end-to-end
      through the real CLI: two --json runs with no state change between
      them append zero new records the second time"
    requirement: JOUR-03
    verification:
      - kind: integration
        ref: "tests/cairn-status.bats#journal observe: two --json runs
          with no state change between them append zero new records the
          second time"
        status: pass
    human_judgment: false
  - id: D4
    description: "a hand-edit made outside any cairn command is caught by
      corroborate() on the very first read, against a fixture where the
      journal did not exist yet at all; deleting a journal that has real
      accumulated history changes zero bytes of the next --json render's
      evidence/corroboration/conflicts keys, proven by a structural
      (jq -S .) diff over three successive renders, on a fixture pinned
      to have no other time-varying keys (no .cairn/sync.json, no lease
      held anywhere — asserted directly)"
    requirement: JOUR-03
    verification:
      - kind: integration
        ref: "tests/cairn-status.bats#JOUR-03: a hand-edit outside any
          cairn command is caught on the first read, and deleting the
          journal changes nothing"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-07-31
status: complete
---

# Phase 16 Plan 04: Corroboration Journal Wiring + JOUR-03 Proof Summary

**phase_model() batch-observes every render's corroboration verdict into cairn-journal.py exactly once per invocation, resiliently — and a mechanical, load-bearing-verified test proves corroborate() itself is provably independent of the journal's presence or contents (JOUR-03, Pitfall 11 closed for good).**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-31
- **Tasks:** 2/2
- **Files modified:** 2 (cairn-status.py, tests/cairn-status.bats)

## Accomplishments

- `journal_observe_phases()` in `cairn-status.py`: shells out to `cairn-journal.py observe --project-dir <root> --json` via the new `CAIRN_JOURNAL` env seam (default: sibling `cairn-journal.py`), carrying every phase's `{"phase", "evidence", "verdict"}` as ONE batched JSON array on stdin — never one subprocess spawn per phase — and swallows every failure mode (nonzero exit, missing script, subprocess error, unparsable stdout) into a single `[cairn-status] warning: ...` stderr line, never raising, never altering `phase_model()`'s return value
- `phase_model()` calls it exactly once, after its per-phase loop has fully computed every row's `evidence`/`corroboration`/`conflicts` — a pure side effect appended at the very end, right before `return out`
- `root` (for `--project-dir`) is resolved as `planning_dir.parent` — the exact expression `phase_model()` already used inline at its `row["dir"]` call site, now hoisted to a local variable and reused at both call sites, per the plan's "reuse the existing resolution, do not invent a second one" instruction
- 3 new bats tests prove the wiring: exactly-one-subprocess-call (via a counting stub that execs into the real `cairn-journal.py`, so the test also confirms the DONE criterion — history shows the expected 4 state_changed + 1 verdict_changed records per phase), byte-identical `--json` output under a broken `CAIRN_JOURNAL`, and dedup exercised end-to-end across two identical `--json` runs
- The JOUR-03 proof test: Part 1 catches a hand-edit made entirely outside any `cairn-*.sh` command (a plain `sed` on `ROADMAP.md`) on the very first read, against a fixture where `.cairn/journal.jsonl` did not exist yet at all. Part 2 diffs three successive `--json` renders structurally (`jq -S .`) — a first read (no journal), a second read (journal now has real accumulated history), and a third read after deleting the journal entirely — proving deletion changes zero bytes of the corroboration output, on a fixture pinned to carry no other time-varying keys (no `.cairn/sync.json`, no lease held anywhere, both asserted directly before trusting the diff)
- Both new deviation-guarding tests (journal-observe wiring and JOUR-03) were proven load-bearing by breaking the corresponding production code and watching them go red, then restoring and confirming green — see "Deviations" below

## Task Commits

Each task was committed atomically:

1. **Task 1: batch-wire phase_model() to cairn-journal.py observe, resiliently** — `be2a6ef` (feat)
2. **Task 2: JOUR-03's proof — deleting the journal changes no verdict, and an out-of-band edit is still caught** — `438a8fd` (test)

**Plan metadata:** committed alongside this SUMMARY (see final commit below).

## Files Created/Modified

- `cairn/scripts/cairn-status.py` — `CAIRN_JOURNAL` env seam, `journal_observe_phases()` helper, `phase_model()`'s call site (root resolved once, reused for `row["dir"]` too), module docstring's new step 4e, `phase_model()`'s own docstring updated
- `tests/cairn-status.bats` — `bats_require_minimum_version 1.5.0` (needed for `run --separate-stderr`), 3 journal-observe wiring tests, 1 JOUR-03 proof test

## Decisions Made

1. **`root` is `planning_dir.parent`, computed once and reused — not a new parameter.** `phase_model()` only receives `planning_dir`; `main()`'s own root resolution (`planning_dir.parent` in every branch) was already used inline at `row["dir"] = str(pdir.relative_to(planning_dir.parent))`. Hoisted that expression to a local `root` variable, used at both the `row["dir"]` site and the new observe call's `--project-dir` — satisfying the plan's explicit "reuse the existing resolution, do not invent a second one" instruction literally.

2. **The JOUR-03 test compares three renders, not two.** See `key-decisions` in the frontmatter above for the full rationale — a naive "first read vs. post-delete read" comparison would have compared two renders that both happen to start with no journal at call-time (since `corroborate()` always runs before that same invocation's own `observe` call writes anything), making a hypothetical "journal exists at read-time" bug undetectable by such a test. Inserted a middle render (against a journal that genuinely has accumulated history from the first read) to close that gap, and verified the closure by injecting exactly that bug shape.

## Deviations from Plan

None — plan executed exactly as written. No auto-fixes were needed; `corroborate()` was read fresh per the plan's `<read_first>` instruction and confirmed unchanged (it still reads only its five scalar arguments, no journal access anywhere in its call graph).

## Issues Encountered

None. No auth gates, no package installs, no blockers.

## Load-Bearing Verification (not just asserted)

Per this plan's own standard ("what_would_make_this_wrong"), both new test groups were proven load-bearing by breaking the corresponding production code and watching the tests fail, then restoring:

1. **Journal-observe wiring tests.** Commented out the `journal_observe_phases(root, out)` call site in `phase_model()`. Re-ran `bats tests/cairn-status.bats -f "journal observe"`: all 3 tests failed — the call-count test failed because the count file was never created at all (`No such file or directory`), the byte-identical test failed because no stderr warning was ever printed, and the dedup test failed because the first run's own record count was `0`. Restored the call site; all 3 passed again, and the restored file diffed byte-for-byte identical to the pre-experiment version.

2. **JOUR-03 test.** Injected the exact Pitfall-11 bug shape this test exists to rule out: a temporary hack in `phase_model()`'s per-phase loop that overwrote `evidence["disk"]` to a sentinel value whenever `.cairn/journal.jsonl` happened to exist at read-time (simulating "a future helper reads the journal for current state instead of live sources"). Re-ran the JOUR-03 test: it failed immediately, at the `first_read_output` vs. `before_output` structural diff (one step before the final delete-diff) — `jq -S .` reported the corrupted `"disk": "PITFALL11-BUG"` value diverging from the real `"disk": "none"`. Reverted the hack; the file diffed byte-for-byte identical to the clean, pre-experiment version, and the test passed again.

## User Setup Required

None — stdlib only, no external service configuration.

## Verification

- `bats tests/cairn-status.bats -f "journal observe"` — 3/3 passing
- `bats tests/cairn-status.bats -f "JOUR-03"` — 1/1 passing
- `bats tests/cairn-status.bats` (full suite, all 55 tests including the 4
  new ones) — 55/55 passing, exit 0
- `bats tests/cairn-journal.bats` (regression) — 16/16 passing, unaffected

## Next Phase Readiness

- `cairn-status.py`'s journal wiring is complete and independently verified (both the wiring itself and JOUR-03's independence guarantee were proven load-bearing by disabling/injecting and re-enabling the relevant code, not just asserted).
- Plan 16-05 (`.gitignore` entry) is the only remaining item this phase's own readiness notes point at — no new sibling files were introduced by this plan beyond what 16-01/16-02 already flagged.
- No blockers for the next wave.

---
*Phase: 16-transition-journal*
*Completed: 2026-07-31*

## Self-Check: PASSED

- FOUND: cairn/scripts/cairn-status.py
- FOUND: tests/cairn-status.bats
- FOUND: .planning/phases/16-transition-journal/16-04-SUMMARY.md
- FOUND commit: be2a6ef
- FOUND commit: 438a8fd
- Full suite re-run at self-check time: `bats tests/cairn-status.bats` — 55/55 passing; `bats tests/cairn-journal.bats` — 16/16 passing (unaffected regression)
