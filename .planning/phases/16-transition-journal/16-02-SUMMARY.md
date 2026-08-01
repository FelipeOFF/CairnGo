---
phase: 16-transition-journal
plan: 02
subsystem: infra
tags: [python, jsonl, append-only, journal, compaction, flock, os.rename, concurrency]

requires:
  - phase: 16-transition-journal (plan 01)
    provides: "cairn-journal.py's observe/lease/history/last-moved
      subcommands, the O_APPEND+os.write() atomic-append primitive, and
      _read_records()'s quarantine-on-parse-failure primitive"
provides:
  - "compact subcommand (D-03): folds every phase's full journal history
    into one snapshot record per phase, written to a brand-new sibling
    file and swapped into place via os.rename — never a rewrite of the
    live journal.jsonl in place"
  - "the pre-rename size re-validation that closes Pitfall 14: a record
    appended by a lock-free observe/lease call during compaction's own
    read-to-rename window aborts the rename (deletes the sibling, exits
    0, deferred to the next invocation) instead of being silently
    discarded by a stale-read rename"
  - "_last_known()'s new `snapshot` event branch — required for JOUR-05;
    without it, last-moved/observe's own dedup lookup would see a
    freshly-compacted journal as \"nothing was ever observed\" for every
    phase"
  - "the auto-trigger: observe/lease both check the journal's current
    byte size in-process, before their own append, and call compact()
    first once JOURNAL_COMPACT_THRESHOLD_BYTES is exceeded"
affects: [16-03-lease-wiring, 16-04-status-wiring, 16-05-gitignore]

tech-stack:
  added: []
  patterns:
    - "sibling-write-then-os.rename swap for a file that must survive a
       crash without ever being rewritten in place — a crash between the
       two steps leaves the original fully intact and only an orphaned
       tmp file behind"
    - "non-blocking fcntl.flock (LOCK_EX | LOCK_NB) scoped to a single
       critical section within one short-lived process invocation, held
       via a dedicated *.lock file next to the resource it guards, never
       as the resource's own longer-lived coordination primitive"
    - "pre-mutation staleness re-validation: compare a size (or other
       cheap fingerprint) captured at the START of a read-fold-write
       sequence against a fresh read of the same fact taken immediately
       before the sequence's one irreversible step, abort on mismatch
       rather than merge or overwrite"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-journal.py
    - cairn/scripts/cairn-journal.sh
    - tests/cairn-journal.bats

key-decisions:
  - "_last_known() had to learn to fold `snapshot` records, which the
     plan's Task 1 action didn't explicitly spell out as a production
     change but which JOUR-05 cannot be satisfied without. Without this,
     last-moved/observe's dedup lookup would treat a freshly-compacted
     journal as if nothing had ever been observed for any phase — the
     opposite of D-03's whole point. Documented below as a deviation
     (Rule 1/2: correctness is not optional, not a scope addition)."
  - "The replay-equivalence test (Task 2) compares last-moved --json
     output via `jq -S .` (recursive key-sort) rather than raw string
     equality. compact() writes the snapshot record with
     json.dumps(..., sort_keys=True), so a folded {\"value\":...,
     \"ts\":...} sub-object round-trips post-compaction with its keys
     reordered alphabetically — same values, different key order, which
     a byte-for-byte string diff would wrongly flag as a real mismatch.
     jq -S . is one of the two structural-equality options the plan's
     own acceptance criteria names explicitly."
  - "JOURNAL_COMPACT_THRESHOLD_BYTES set to 200 KiB: small enough this
     plan's own bats tests don't need to pad a multi-megabyte fixture to
     exercise auto-compaction conceptually (though the tests exercise
     `compact` directly via the manual subcommand, not by growing a
     fixture past the threshold, per the plan's own acceptance criteria),
     large enough that routine day-to-day phase work (a handful of
     observe/lease calls per session) will not compact every few
     appends."

requirements-completed: [JOUR-05]

coverage:
  - id: D1
    description: "compact folds every phase's full history into exactly
      one snapshot record per phase, written to a brand-new sibling file
      and swapped into place via os.rename; never a rewrite of the live
      journal.jsonl in place; a no-op on a nonexistent journal creates
      nothing"
    requirement: JOUR-05
    verification:
      - kind: integration
        ref: "tests/cairn-journal.bats#compact: on a nonexistent journal
          is a no-op, exits 0, creates nothing"
        status: pass
      - kind: integration
        ref: "tests/cairn-journal.bats#compact: folds multi-phase history
          into exactly one snapshot record per touched phase"
        status: pass
      - kind: integration
        ref: "tests/cairn-journal.bats#compact: a crash between the
          sibling write and the rename leaves the original journal
          byte-for-byte unchanged"
        status: pass
    human_judgment: false
  - id: D2
    description: "two compactions racing each other are serialized by a
      non-blocking flock: the contended caller's own compaction attempt
      is skipped (exit 0, journal untouched, no hang), while its own
      append (if it was an auto-trigger check) still proceeds against
      the still-live, uncompacted journal"
    verification:
      - kind: integration
        ref: "tests/cairn-journal.bats#compact: a contended compaction
          lock is skipped without hanging; a concurrent observe still
          succeeds uncompacted"
        status: pass
    human_judgment: false
  - id: D3
    description: "a record appended by a separate, lock-free observe/
      lease process during a real compaction's own read-to-rename window
      is never silently discarded by that compaction's rename — proven
      by injecting a real concurrent append via the
      CAIRN_JOURNAL_COMPACT_TEST_DELAY seam, not by inspecting the lock"
    requirement: JOUR-05
    verification:
      - kind: integration
        ref: "tests/cairn-journal.bats#compact: THE LOAD-BEARING TEST --
          a record appended by a separate process during compaction's
          read-to-rename window survives (Pitfall 14)"
        status: pass
    human_judgment: false
  - id: D4
    description: "compacting the journal changes zero phases' last-moved
      answer -- proven by a before/after structural-equality diff of
      last-moved for every phase touched by ~39 synthetic records across
      3 phases and all 3 real event kinds, plus a secondary check that
      history after compaction is strictly smaller and every remaining
      record is a snapshot"
    requirement: JOUR-05
    verification:
      - kind: integration
        ref: "tests/cairn-journal.bats#replay equivalence: last-moved is
          provably identical before and after compaction, for every
          touched phase (JOUR-05)"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-31
status: complete
---

# Phase 16 Plan 02: Transition Journal Compaction Summary

**compact subcommand (D-03): folds every phase's journal history into one snapshot record via sibling-write + os.rename, closing the exact race (Pitfall 14) where a lock-free append landing mid-compaction would otherwise be silently discarded — proven by racing a real concurrent append against a real compaction, and by first watching that same test fail without the fix.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-31
- **Tasks:** 2/2
- **Files modified:** 3 (cairn-journal.py, cairn-journal.sh, tests/cairn-journal.bats)

## Accomplishments

- `compact` subcommand: reads the journal once, folds each phase's full history via the existing `_last_known()`, writes exactly one `snapshot` record per phase to a `tempfile.mkstemp` sibling, and swaps it into place with `os.rename` — never an in-place rewrite of `journal.jsonl`
- A non-blocking `fcntl.flock(LOCK_EX | LOCK_NB)` on a dedicated `journal.jsonl.compact.lock` serializes two concurrent compactions against each other (a contended caller is skipped, exit 0, never blocked/hung)
- The pre-rename staleness re-validation that actually closes Pitfall 14: `size_at_read` is captured from the exact bytes `_parse_records()` folds (no second `stat()` reopening the same TOCTOU gap), and a fresh `journal_path.stat().st_size` immediately before `os.rename()` — still inside the same flock hold — aborts the rename on any mismatch, deleting the sibling and leaving the live journal exactly as the concurrently-appending process left it
- `_last_known()` extended to fold `snapshot` records, without which `last-moved`/`observe`'s own dedup lookup would treat a freshly-compacted journal as "nothing was ever observed" — this is what makes JOUR-05's replay-equivalence claim actually true, not just asserted
- Auto-trigger wiring: `observe`/`lease` both check the journal's byte size in-process, before their own append, and call `compact()` first once `JOURNAL_COMPACT_THRESHOLD_BYTES` (200 KiB) is exceeded
- The load-bearing concurrent-append test, run **twice**: once against the code with the pre-rename re-validation removed (confirmed it fails — the concurrently-appended record was silently discarded, `history --phase 67` returned 0 records instead of 1), and once against the restored code (confirmed it passes)

## Task Commits

Each task was committed atomically:

1. **RED — failing tests for compact + replay equivalence (both tasks)** — `1aa25c6` (test)
2. **Task 1: compact subcommand — sibling write, flock-guarded rename, pre-rename staleness re-validation** — `8a35c27` (feat)
3. **Task 2: replay-equivalence assertion fix (jq -S structural comparison)** — `e284be5` (test)

**Plan metadata:** committed alongside this SUMMARY (see final commit below).

## Files Created/Modified

- `cairn/scripts/cairn-journal.py` — `compact`/`_compact_locked`/`_build_snapshot_record`/`_maybe_auto_compact`/`_compact_lock_path` (compaction), `_parse_records` (split out of `_read_records` so `size_at_read` derives from the same bytes that get folded), `_last_known`'s new `snapshot` branch, `cmd_compact`, `JOURNAL_COMPACT_THRESHOLD_BYTES`, module docstring's new "Compaction" section
- `cairn/scripts/cairn-journal.sh` — usage/exit-code header comment updated to include `compact`
- `tests/cairn-journal.bats` — 6 new tests: `compact` no-op on missing journal, multi-phase snapshot folding, crash-between-write-and-rename byte-for-byte preservation, contended-lock skip-without-hanging, the load-bearing concurrent-append survival test (Pitfall 14), and the replay-equivalence proof (JOUR-05)

## Decisions Made

1. **`_last_known()` needed a `snapshot`-folding branch the plan's Task 1 action didn't explicitly call out.** The plan's action section describes building the snapshot record via `_last_known()` but doesn't mention that `_last_known()` itself must be taught to read a `snapshot` record back. Without this, every read path (`last-moved`, `observe`'s own dedup lookup) would see a freshly-compacted journal as if no phase had ever been observed — the exact opposite of what JOUR-05 requires ("compacting the journal changes zero phases' last-moved answer"). Implemented as a fourth branch in `_last_known()`'s per-record loop, folding a snapshot's `state`/`verdict`/`lease` sub-objects into `known` the same way a real event would. Documented as a deviation below (Rule 1/2 — correctness, not scope creep).

2. **Replay-equivalence comparison uses `jq -S .`, not raw string equality.** `compact()` writes the snapshot record via `json.dumps(record, sort_keys=True)` (matching this codebase's existing JSON-write convention). That means a folded `{"value": ..., "ts": ...}` sub-object — built with `value` first by `_last_known()`'s real-event branches — round-trips through a snapshot write/read as `{"ts": ..., "value": ...}`, alphabetically reordered. Same values, different key order. A raw string diff of `last-moved --json` before/after compaction flagged this as a mismatch on first run; switched to `jq -S .` (recursive key-sort) normalization on both sides before comparing, one of the two structural-equality options the plan's own acceptance criteria names explicitly ("a real diff... or a jq structural equality check").

3. **`JOURNAL_COMPACT_THRESHOLD_BYTES = 200 * 1024`.** Per the plan's discretion note ("pick something in the low hundreds of KB"). The bats tests exercise `compact` directly via the manual subcommand (as the plan's own acceptance criteria specifies — "without needing to grow a fixture to the real threshold"), so the exact value only needed to satisfy "large enough that routine day-to-day phase work does not compact every few appends," which 200 KiB comfortably does relative to this journal's per-record size (~200-400 bytes).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1/2 - missing critical functionality] `_last_known()` did not fold `snapshot` records**

- **Found during:** Task 1, while implementing `compact()` and reasoning through what `last-moved` would return immediately after a compaction
- **Issue:** The plan's Task 1 action describes `compact()` building each phase's snapshot via `_last_known()` (already built), but doesn't call out that `_last_known()` itself needs a new branch to READ a `snapshot` record back. Without it, `_last_known()`'s per-record loop only recognizes `state_changed`/`verdict_changed`/`lease_changed` — a `snapshot` event would silently fall through every `elif`, contributing nothing to `known`. The first read of `last-moved` against a freshly-compacted journal would report every axis as `null`/never-observed, directly contradicting JOUR-05's own must-have truth ("compacting the journal changes zero phases' last-moved answer").
- **Fix:** Added a `elif event == "snapshot":` branch to `_last_known()` that folds a snapshot's `state`/`verdict`/`lease` sub-objects into `known` exactly like a real event would overwrite it. Because a compacted file always has its snapshot record(s) earliest in file order (written once at compaction time; every subsequent real event is necessarily appended after, since observe/lease only ever append), folding the snapshot first and any later real events over it reconstructs the same answer a full, uncompacted replay would.
- **Files modified:** `cairn/scripts/cairn-journal.py` (`_last_known()`)
- **Verification:** `tests/cairn-journal.bats#replay equivalence: last-moved is provably identical before and after compaction, for every touched phase (JOUR-05)` — this test fails immediately without the fix (every before/after last-moved answer would go from real values to all-null)
- **Committed in:** `8a35c27`

**Total deviations:** 1 auto-fixed (Rule 1/2 — necessary for JOUR-05's actual correctness claim, not an optional addition). No scope creep — no subcommand, flag, or record field beyond what the plan specified.

## Issues Encountered

None beyond the deviation above — no blockers, no auth gates, no package installs.

## The Concurrent-Append Test: Run Both Ways

Per this plan's stated purpose, the pre-rename re-validation was verified two ways, not asserted:

1. **Without the guard.** Temporarily replaced `if size_now != size_at_read:` with `if False and size_now != size_at_read:` (the abort path made permanently unreachable, nothing else changed) and ran `bats tests/cairn-journal.bats -f "THE LOAD-BEARING TEST"` in isolation. Result: **FAILED** — `assert_json_eq "$output" '.records | length' '1'` returned `0`, i.e. `history --phase 67` after the race showed zero records where the concurrently-appended one should have been. This is the exact silent-discard Pitfall 14 describes: the compaction's stale-read sibling swapped in over the live file, and phase 67's real, successfully-`os.write()`-appended record vanished with no error anywhere.
2. **With the guard restored.** Reverted the file to be byte-for-byte identical to the pre-experiment version (`diff`-confirmed), re-ran the full suite: **16/16 pass**, including the load-bearing test.

## User Setup Required

None — stdlib only (`fcntl`, `tempfile`, `time` added to the existing stdlib-only import set), no external service configuration.

## Next Phase Readiness

- `cairn-journal.py`'s `compact` subcommand, its auto-trigger wiring, and `_last_known()`'s snapshot-folding are ready for Plan 16-03 (lease wiring) and Plan 16-04 (status/verdict wiring) to build on without any further compaction-awareness work on their part — they call `observe`/`lease` exactly as Plan 16-01 already specified, and compaction happens transparently underneath.
- `.cairn/journal.jsonl.compact.lock` is a new file this plan introduces, sitting next to the journal — Plan 16-05 (`.gitignore` entry) should confirm its glob covers this sibling file too, not just `journal.jsonl` itself.
- No blockers for the next wave.

---
*Phase: 16-transition-journal*
*Completed: 2026-07-31*

## Self-Check: PASSED

- FOUND: cairn/scripts/cairn-journal.py
- FOUND: cairn/scripts/cairn-journal.sh
- FOUND: tests/cairn-journal.bats
- FOUND commit: 1aa25c6
- FOUND commit: 8a35c27
- FOUND commit: e284be5
- Full suite re-run at self-check time: `bats tests/cairn-journal.bats` — 16/16 passing (3 consecutive runs, no flakiness observed in the timing-sensitive lock-contention and concurrent-append tests)
