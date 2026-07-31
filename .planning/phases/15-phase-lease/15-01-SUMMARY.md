---
phase: 15-phase-lease
plan: "01"
subsystem: infra
tags: [bd, beads, git-worktree, cli, bats]

# Dependency graph
requires: []
provides:
  - "cairn-lease.py/.sh: acquire/release/renew/status subcommands, the single TTL/staleness authority every other cairn surface shells out to"
  - "the `lease`-labelled (never phase-<N>) bd issue convention for phase-level coordination"
affects: [15-02, 15-03, 15-04, 15-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "phase-level coordination lease as a dedicated bd issue, one level above bd's own per-issue --claim"
    - "worktree-path identity (git rev-parse --show-toplevel) instead of bd's actor resolution, for telling two agents apart"
    - "bd --metadata full-object-replacement discipline: every write sends the complete {\"cairn\": {\"lease\": {...}}} object, never a partial patch"

key-files:
  created:
    - cairn/scripts/cairn-lease.py
    - cairn/scripts/cairn-lease.sh
    - tests/cairn-lease.bats
  modified: []

key-decisions:
  - "Argparse with subparsers (not hand-rolled parsing) — matches cairn-relabel.py's precedent for a multi-subcommand script and lets argparse's own exit-2 usage-error behavior double as EXIT_USAGE for free"
  - "A corrupt or missing heartbeat_at degrades to STALE (reclaimable), not to perpetually live — the inverse of the doctor's usual 'malformed metadata degrades to vacant/absent' rule, chosen specifically because a lease must never become a permanent block (D-04/T-15-02)"
  - "release <N> and release --mine are deliberately different primitives: release <N> is unconditional regardless of holder (verify-post.md's per-phase call), release --mine is scoped to this worktree's own holder identity only"

requirements-completed: [LEASE-02, LEASE-03, LEASE-04]

coverage:
  - id: D1
    description: "acquire/release/status work for a single phase; a real second git worktree proves the lease is visible cross-worktree (LEASE-03)"
    requirement: "LEASE-03"
    verification:
      - kind: integration
        ref: "tests/cairn-lease.bats#the tracer: lease acquired in worktree A is visible from a real second worktree B"
        status: pass
      - kind: integration
        ref: "tests/cairn-lease.bats#acquire on a live-held phase writes nothing, exits 3, names the holder and since-when"
        status: pass
    human_judgment: false
  - id: D2
    description: "the lease issue never carries a phase-<N> label, only `lease`"
    requirement: "LEASE-02"
    verification:
      - kind: integration
        ref: "tests/cairn-lease.bats#the lease issue carries only the lease label, never phase-<N>"
        status: pass
    human_judgment: false
  - id: D3
    description: "a stale lease (heartbeat older than 4h) is reclaimed by the next acquire with no manual unlock step, and acquire on a live-held phase never silently overwrites"
    requirement: "LEASE-04"
    verification:
      - kind: integration
        ref: "tests/cairn-lease.bats#a stale lease (heartbeat older than 4h) is reclaimed by the next acquire, with a fresh acquired_at"
        status: pass
    human_judgment: false
  - id: D4
    description: "renew, status --all, release --mine, and the usage/bd-unavailable defensive paths"
    verification:
      - kind: integration
        ref: "tests/cairn-lease.bats (tests 9-16)"
        status: pass
    human_judgment: false

# Metrics
duration: 35min
completed: 2026-07-30
status: complete
---

# Phase 15 Plan 01: Phase lease Summary

**cairn-lease.py/.sh: a phase-level coordination lease backed by a dedicated `lease`-labelled bd issue, identified by the acquiring worktree's `git rev-parse --show-toplevel`, with a real cross-worktree test proving LEASE-03.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-30T23:51:49-03:00
- **Tasks:** 2 (Task 1: tracer, Task 2: TDD)
- **Files modified:** 3 (2 created scripts, 1 created test file)

## Accomplishments
- `cairn-lease.py`/`.sh`: `acquire`/`release`/`renew`/`status` subcommands for a phase-level lease, one level above bd's own per-issue `--claim`
- The lease is a bd issue carrying only the `lease` label (never `phase-<N>`), so it cannot be mistaken for real phase work by `cairn-status.py`, `cairn-doctor.py`, or `work.md`'s own done-check
- A real second `git worktree` (via `git worktree add`) mechanically proves cross-worktree lease visibility — LEASE-03 verified end-to-end, not narrated
- A stale lease (heartbeat older than 4h) is reclaimed by the next `acquire` automatically; a live conflict writes nothing, reports who holds it and since when, and exits a distinct code (3) the caller can choose to ignore (D-04)
- `renew`, `status --all`, and `release --mine` round out the surface `cairn-doctor.py` (Plan 15-03) and `cairn-status.py` (Plan 15-05) will shell out to

## Task Commits

Each task was committed atomically:

1. **Task 1: acquire/release/status for one phase — the cross-worktree proof** - `732a479` (feat)
2. **Task 2: renew, status --all, release --mine, and the staleness edge cases** - TDD, two commits:
   - `fac77fa` (test — RED, verified failing against the task-1-only implementation)
   - `a240d99` (feat — GREEN, all 16 `tests/cairn-lease.bats` cases pass)

**Plan metadata:** committed separately after this SUMMARY (docs: complete plan).

## Files Created/Modified
- `cairn/scripts/cairn-lease.py` - acquire/release/renew/status subcommands, metadata schema, staleness/TTL logic, identity resolution
- `cairn/scripts/cairn-lease.sh` - thin exec wrapper, same pairing convention as every other `cairn-*.py` script
- `tests/cairn-lease.bats` - 16 cases: the cross-worktree tracer, held-by-another, label discipline, release idempotency, staleness reclaim, renew semantics, `status --all`, `release --mine`, usage errors, bd-unavailable

## Decisions Made
- Used `argparse` with subparsers rather than hand-rolled parsing, matching `cairn-relabel.py`'s precedent for a multi-subcommand script with several flags per subcommand (CONVENTIONS.md: "argparse beyond [2 flags]"). This also makes argparse's own usage-error exit code (2) line up with `EXIT_USAGE` for free — non-numeric/missing required positionals need no custom handling.
- `is_stale()` treats a missing or unparsable `heartbeat_at` as STALE (reclaimable) rather than "vacant" or "perpetually live" — the opposite default from the doctor's usual "malformed metadata degrades to absent" pattern, chosen deliberately because a lease must never become a permanent block (D-04, threat T-15-02).
- `release <N>` (unconditional, any holder) and `release --mine` (scoped to this worktree's own holder identity) are kept as clearly distinct verbs per the plan's explicit instruction, since `verify-post.md` will call the former once per phase regardless of outcome.

## Deviations from Plan

None - plan executed exactly as written. Task 1's `acquire` implementation already included the staleness-reclaim branch (vacant / already-mine / stale-heartbeat all fall through to "acquire"), which the plan's Task 1 action text specified as part of `acquire`'s core behavior; Task 2 built `renew`/`status --all`/`release --mine` on top of that, per the plan's task split.

## Issues Encountered
- macOS resolves `TMPDIR` through a `/var` → `/private/var` symlink, so bats' raw `$PWD`/`$BATS_TEST_TMPDIR` strings differ from the physical path `git rev-parse --show-toplevel` returns (what the script uses for holder identity). Fixed by canonicalizing test fixture worktree paths through `git rev-parse --show-toplevel` before asserting equality, rather than comparing against bash's logical `$PWD`. This is a test-fixture-only concern; the script's own identity resolution was correct throughout.
- Verified live (before writing any code) that `bd list`/`bd create`/`bd update` all share one database across a real `git worktree add` — both read and write paths, cross-worktree, from an actual `bd 1.1.0` binary — confirming D-01's measurement rather than assuming it still held.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`cairn-lease.py status --all --json` is ready for Plan 15-03 (`cairn-doctor.py`) and Plan 15-05 (`cairn-status.py`) to shell out to directly, per the plan's `key_links`. The `lease` label (with no `phase-<N>` pairing) is the contract those plans' `NO_PHASE_EXEMPT` set / lane filter must honor. No blockers.

---
*Phase: 15-phase-lease*
*Completed: 2026-07-30*

## Self-Check: PASSED

All 4 created files found on disk; all 3 task commits (`732a479`, `fac77fa`, `a240d99`) found in git history.
