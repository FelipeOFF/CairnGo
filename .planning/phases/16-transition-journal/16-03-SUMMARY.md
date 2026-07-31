---
phase: 16-transition-journal
plan: "03"
subsystem: infra
tags: [python, bash, journal, lease, wiring, resilience]

requires:
  - phase: 16-transition-journal (plan 01)
    provides: "cairn-journal.py's `lease` subcommand contract — unconditional
      append of one lease_changed record, --holder/--actor required,
      --prev-holder optional"
provides:
  - "cairn-lease.py's cmd_acquire/release_one/cmd_release --mine now call
    cairn-journal.py's `lease` subcommand exactly once per GENUINE
    acquire/reclaim/release transition (D-01) — the concrete source of the
    'lease' axis Plan 16-01's last-moved subcommand already knows how to
    report"
  - "journal_lease_event() — a resilient, best-effort journal-call helper:
    any failure (nonzero exit, missing script, subprocess error) degrades
    to a stderr warning, never changes cairn-lease.py's own exit code or
    bd state (D-02)"
  - "CAIRN_JOURNAL env seam (default: the sibling cairn-journal.py),
    mirroring the existing CAIRN_GBSYNC/CAIRN_MAP/CAIRN_GATE convention"
affects: [16-04-status-wiring]

tech-stack:
  added: []
  patterns:
    - "resilient cross-script call: shell out via subprocess.run inside a
       try/except that never raises and never changes the caller's exit
       code — bookkeeping (the journal record) must never block the real
       work (the lease operation) it is recording"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-lease.py
    - tests/cairn-lease.bats

key-decisions:
  - "cairn-journal.py's `lease` subcommand has --actor as a REQUIRED
     argument (argparse required=True), but the plan's action text for
     release_one's call shape omitted --actor entirely. Omitting it would
     make every release call fail argparse validation (exit 2), which
     journal_lease_event() would then treat as a journal failure — meaning
     release would NEVER actually journal, contradicting the plan's own
     acceptance criteria ('release ... exactly one more record appended').
     Fixed by always passing --actor: resolve_actor(root) (the actor
     performing the release) for release_one and release --mine, matching
     how the acquire branch already resolves and passes actor. Documented
     as a Rule 3 deviation below."

requirements-completed: [JOUR-01, JOUR-02]

coverage:
  - id: D1
    description: "a fresh lease acquire or a reclaim-from-stale writes
      exactly one lease_changed record; a heartbeat-only renew
      (already_mine in acquire, or the renew subcommand) writes zero"
    requirement: JOUR-01
    verification:
      - kind: integration
        ref: "tests/cairn-lease.bats#journal: fresh acquire writes one
          lease_changed record; a same-worktree renewal via acquire, and
          renew, write zero"
        status: pass
      - kind: integration
        ref: "tests/cairn-lease.bats#journal: a reclaim from a stale
          lease writes one lease_changed record naming the previous
          holder"
        status: pass
      - kind: integration
        ref: "tests/cairn-lease.bats#journal: acquire held-by-another
          (EXIT_HELD) writes nothing to either worktree's journal"
        status: pass
    human_judgment: false
  - id: D2
    description: "an actual release (a lease that existed and was held)
      writes exactly one lease_changed record; releasing an already-vacant
      lease, or release --mine matching zero leases, writes zero"
    requirement: JOUR-01
    verification:
      - kind: integration
        ref: "tests/cairn-lease.bats#journal: release writes one
          lease_changed record; a second release on the now-vacant lease
          writes zero"
        status: pass
      - kind: integration
        ref: "tests/cairn-lease.bats#journal: release on a phase whose
          lease issue was never created writes zero records"
        status: pass
      - kind: integration
        ref: "tests/cairn-lease.bats#journal: release --mine writes one
          lease_changed record per phase actually released, zero for a
          phase held by a different worktree"
        status: pass
    human_judgment: false
  - id: D3
    description: "cairn-lease.py's own documented exit-code contract is
      completely unchanged by this plan — a broken or missing
      cairn-journal.py never blocks, changes, or fails an
      acquire/release/renew call, it only forgoes the journal entry and
      prints a warning"
    requirement: JOUR-02
    verification:
      - kind: integration
        ref: "tests/cairn-lease.bats#journal failure:
          acquire/release/renew succeed identically to normal, with a
          stderr warning, when CAIRN_JOURNAL points at a nonexistent
          path"
        status: pass
      - kind: integration
        ref: "tests/cairn-lease.bats#journal failure:
          acquire/release/renew succeed identically to normal, with a
          stderr warning, when CAIRN_JOURNAL is a stub that always exits
          1"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-31
status: complete
---

# Phase 16 Plan 03: Lease Journal Wiring Summary

**cairn-lease.py's acquire/reclaim/release paths now call cairn-journal.py's `lease` subcommand on every genuine transition, via a resilient CAIRN_JOURNAL seam that degrades a broken journal to a stderr warning, never a blocked lease.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-31
- **Tasks:** 2/2
- **Files modified:** 2 (cairn-lease.py, tests/cairn-lease.bats)

## Accomplishments

- `journal_lease_event()` helper in `cairn-lease.py`: shells out to `cairn-journal.py lease <phase> {acquired|released} --holder H --actor A [--prev-holder P] --project-dir root` via the new `CAIRN_JOURNAL` env seam (default: sibling `cairn-journal.py`), and swallows every failure mode (nonzero exit, missing script, subprocess error) into a single `[cairn-lease] warning: ...` stderr line — never raises, never calls `die()`, never changes the caller's exit code
- `cmd_acquire` calls it exactly once for a fresh acquire or a reclaim-from-stale (with `prev_holder` set only on reclaim), and zero times for `already_mine` (heartbeat renewal) or the EXIT_HELD branch
- `release_one` and `cmd_release --mine` call it exactly once per real release (the lease existed and was held), zero times for a no-op release (no lease issue, or already vacant)
- `cmd_renew` untouched — it never journals, in any branch, by contract
- 8 new bats tests: 6 prove the wiring writes the right count of records on each transition type (fresh acquire, reclaim, EXIT_HELD, release, no-op release, release --mine across two worktrees), 2 prove the resilience contract under both a nonexistent `CAIRN_JOURNAL` and a stub that always exits 1
- Every new wiring test was proven load-bearing, not vacuous, by disabling the corresponding production code and watching it fail (`0` records where `1`/`2` expected), then restoring and confirming green — see "Deviations" and the git history below for the exact commits
- Every new resilience test was proven the same way: temporarily replaced `journal_lease_event()`'s try/except with a raising `check=True` call, watched both new tests fail (status became `1`, not `0`), then restored and confirmed green

## Task Commits

Each task was committed atomically, following RED -> GREEN for Task 1 (a real failing-test commit, not a simulated one):

1. **Task 1 (RED): failing coverage for lease journal wiring** — `943c848` (test)
2. **Task 1 (GREEN): wire cairn-lease.py to cairn-journal.py on genuine transitions** — `b1eea54` (feat)
3. **Task 2: prove a broken CAIRN_JOURNAL never blocks acquire/release/renew** — `a5af4e6` (test; no production change needed, per the plan's own note — the Task 1 resilience guard already covers it)

**Plan metadata:** committed alongside this SUMMARY (see final commit below).

## Files Created/Modified

- `cairn/scripts/cairn-lease.py` — `CAIRN_JOURNAL` env seam constant, `journal_lease_event()` helper, wiring in `cmd_acquire`/`release_one`/`cmd_release`, module docstring's new "Journal wiring" section plus updated Behavior bullets for `acquire`/`release`/`release --mine`/`renew`
- `tests/cairn-lease.bats` — 8 new tests: 6 for wiring correctness (Task 1), 2 for journal-failure resilience (Task 2)

## Decisions Made

1. **`--actor` is required for every `lease` journal call, including release — a plan gap, not a design choice.** See `key-decisions` in the frontmatter above. `cairn-journal.py`'s `lease` subcommand's argparse has `--actor` as `required=True`, but the plan's action text described release's call shape without it. Passing no `--actor` would make cairn-journal.py itself exit 2 (usage error) on every release, which `journal_lease_event()`'s resilience contract would then correctly swallow as "journal failed" — meaning release would silently NEVER journal, contradicting the plan's own truths/acceptance criteria. Fixed by resolving `resolve_actor(root)` at the release call sites (both `release_one` and `cmd_release --mine`), matching the actor semantics `cmd_acquire` already uses (the actor performing the action, not the lease's prior holder).

2. **Test titles all contain the exact filter substrings the plan's `<verify>` commands use** (`"journal"` for Task 1, `"journal failure"` for Task 2) so both `bats tests/cairn-lease.bats -f "journal"` and `bats tests/cairn-lease.bats -f "journal failure"` select precisely the intended sets — verified directly (8 tests for `"journal"`, 2 for `"journal failure"`).

3. **Journal wiring tests read history back through the SAME `--project-dir` the write went through**, because the journal is documented as per-worktree local storage (`<project-dir>/.cairn/journal.jsonl`, never cross-worktree). The reclaim and `release --mine` tests explicitly assert this cross-worktree isolation too (a phase acquired in worktree B never shows up in worktree A's own journal), which is a faithful test of the real behavior rather than an assumption.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking] `--actor` omitted from the plan's release call shape, but required by cairn-journal.py**

- **Found during:** Task 1, reading `cairn-journal.py`'s `lease` subcommand argparse definition per the plan's own `<read_first>` instruction ("do not guess it")
- **Issue:** The plan's Task 1 behavior/action text describes `release_one`'s journal call as `cairn-journal.py lease <phase> released --holder <holder> --project-dir <root>` — no `--actor`. But `cairn-journal.py`'s `lease` subparser has `lease.add_argument("--actor", required=True, ...)`. Omitting it would make every release's journal call fail argparse's own validation, which `journal_lease_event()`'s resilience contract (also required by this same plan) would swallow into a silent "journal failed" warning — meaning release would NEVER actually write a `lease_changed` record, directly contradicting the plan's own truth ("an actual release... writes exactly one lease_changed record") and acceptance criteria.
- **Fix:** Both `release_one` and `cmd_release --mine` now resolve and pass `--actor` (`resolve_actor(root)`) on every journal call, exactly like the acquire branch already does.
- **Files modified:** `cairn/scripts/cairn-lease.py` (`release_one`, `cmd_release`)
- **Verification:** `tests/cairn-lease.bats#journal: release writes one lease_changed record...` and the `release --mine` equivalent — both assert `.records[1].action == "released"` is actually present, which would be impossible if `--actor` were missing (the journal call would fail silently and the record would never exist)
- **Committed in:** `b1eea54`

---

**Total deviations:** 1 auto-fixed (Rule 3 — necessary for the plan's own acceptance criteria to be achievable; not a scope addition, since `--actor` was already being resolved and passed on the acquire side).
**Impact on plan:** No scope creep — no new subcommand, flag, or record field beyond what the plan specified. This is the exact "do not guess it" contract the plan's `<read_first>` instruction anticipated by requiring the implementer to read `cairn-journal.py`'s actual argparse definition rather than trust the plan's own prose paraphrase of it.

## Issues Encountered

None beyond the deviation above — no blockers, no auth gates, no package installs.

## User Setup Required

None — stdlib only, no external service configuration.

## Next Phase Readiness

- `cairn-lease.py`'s journal wiring is complete and independently verified (both the wiring itself and its resilience contract were proven load-bearing by disabling and re-enabling the relevant code, not just asserted).
- Plan 16-04 (status/verdict wiring) can follow the same `journal_lease_event()`-style pattern for `cairn-status.py`'s `corroborate()` verdict-change calls into `cairn-journal.py observe`.
- No blockers for the next wave.

---
*Phase: 16-transition-journal*
*Completed: 2026-07-31*

## Self-Check: PASSED

- FOUND: cairn/scripts/cairn-lease.py (journal_lease_event, CAIRN_JOURNAL, wiring in cmd_acquire/release_one/cmd_release)
- FOUND: tests/cairn-lease.bats (8 new tests, 24 total)
- FOUND: .planning/phases/16-transition-journal/16-03-SUMMARY.md
- FOUND commit: 943c848
- FOUND commit: b1eea54
- FOUND commit: a5af4e6
- Full suite re-run at self-check time: `bats tests/cairn-lease.bats` — 24/24 passing; `bats tests/cairn-journal.bats` — 16/16 passing (unaffected regression)
