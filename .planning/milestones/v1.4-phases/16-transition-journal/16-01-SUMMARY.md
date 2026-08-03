---
phase: 16-transition-journal
plan: 01
subsystem: infra
tags: [python, jsonl, append-only, journal, corroboration]

requires: []
provides:
  - "cairn-journal.py — the single append-only, local, gitignored writer
    for cairn's observed state history (D-02): observe/lease/history/
    last-moved subcommands"
  - "_append_record()'s O_APPEND + one os.write() atomic-append recipe,
    with the append-after-torn-tail separator fix — every later writer
    (compact in Plan 16-02) funnels through this one function"
  - "_read_records()'s quarantine-on-parse-failure primitive — every read
    path (history, last-moved, observe's own dedup lookup) shares it"
affects: [16-02-compaction, 16-03-lease-wiring, 16-04-status-wiring,
          16-05-gitignore]

tech-stack:
  added: []
  patterns:
    - "single-writer JSONL journal: every write funnels through one
       _append_record(), every read through one _read_records() — no
       subcommand opens the journal file itself"
    - "internal-only sentinel object (_NEVER_OBSERVED) to distinguish
       'no prior record' from 'prior value was JSON null', resolved to
       null only at record-build time"

key-files:
  created:
    - cairn/scripts/cairn-journal.py
    - cairn/scripts/cairn-journal.sh
    - tests/cairn-journal.bats
  modified: []

key-decisions:
  - "history/last-moved --json output is an object ({\"records\":[...],
     \"warnings\":[...]} / the last-known dict plus a \"warnings\" key),
     not a bare array — the plan's prose mentioned both a bare array and
     a warnings key for the same --json mode; an object satisfies both
     readings and is what the acceptance criteria's jq assertions
     actually need."
  - "found and fixed a real bug beyond the plan's literal os.open recipe:
     appending straight onto a torn (non-newline-terminated) tail would
     concatenate the new record onto the old garbage, corrupting both.
     Fixed with a read-only pre-check of the last byte (separate from the
     O_WRONLY write fd, which cannot itself be read) that folds a
     leading separator into the same single os.write() payload when
     needed — still one atomic syscall, not a second write."

requirements-completed: [JOUR-01, JOUR-02, JOUR-04]

coverage:
  - id: D1
    description: "observe appends a state_changed/verdict_changed record
      (actor/ts/nonce/phase/event populated) only when the incoming
      value differs from the last recorded value for that phase+axis;
      resubmitting identical evidence appends zero new lines"
    requirement: JOUR-01
    verification:
      - kind: integration
        ref: "tests/cairn-journal.bats#observe dedup: resubmitting
          identical evidence+verdict appends zero new lines"
        status: pass
      - kind: integration
        ref: "tests/cairn-journal.bats#observe dedup: state_md
          null-to-null is zero new records, null-to-value is one with
          from null"
        status: pass
      - kind: integration
        ref: "tests/cairn-journal.bats#observe dedup: verdict change
          appends exactly one verdict_changed record independent of
          evidence"
        status: pass
    human_judgment: false
  - id: D2
    description: "a journal truncated mid-record at a byte offset inside
      a JSON string value (never a record boundary) still returns every
      complete record before the cut via history/last-moved, plus a WARN
      naming the byte offset, and never crashes or exits non-zero"
    requirement: JOUR-04
    verification:
      - kind: integration
        ref: "tests/cairn-journal.bats#torn tail: a byte-offset cut
          inside a JSON string value quarantines with the correct
          offset, history reads all complete records"
        status: pass
      - kind: integration
        ref: "tests/cairn-journal.bats#torn tail: last-moved degrades the
          same way as history, no crash"
        status: pass
      - kind: integration
        ref: "tests/cairn-journal.bats#torn tail: a corrupted trailing
          fragment is never fixed by a later write, only ever reported"
        status: pass
    human_judgment: false
  - id: D3
    description: "last-moved --phase N --json reports each of
      disk/bd/roadmap/state_md/verdict/lease's last known value and
      timestamp, or null when never observed, including for a phase with
      no records or no journal file at all"
    requirement: JOUR-02
    verification:
      - kind: integration
        ref: "tests/cairn-journal.bats#last-moved: reports last value+ts
          per axis, or null when never observed"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-07-31
status: complete
---

# Phase 16 Plan 01: Transition Journal Summary

**cairn-journal.py: the single append-only writer for cairn's observed phase-state/lease/verdict history, backed by one O_APPEND+os.write() atomic-append primitive and a quarantine-on-parse-failure read primitive that survives a torn write.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-31
- **Tasks:** 3/3
- **Files created:** 3 (cairn-journal.py, cairn-journal.sh, tests/cairn-journal.bats)

## Accomplishments

- `cairn-journal.py` with four subcommands — `observe` (batched, diff-then-append against `_last_known()`), `lease` (unconditional append, no dedup), `history` (sorted read, `--phase` filter), `last-moved` (per-axis last value+timestamp) — all funneling through exactly one write primitive and one read primitive
- The `O_APPEND` + single `os.write()` atomicity recipe, verified against a real torn-write fixture, plus a fix for a bug the fixture surfaced (see Deviations)
- Byte-offset (not line-number) quarantine reporting on `_read_records()`, proven against a fixture truncated inside a JSON string value — never a record boundary — self-verified to produce `json.JSONDecodeError` before trusting any further assertion

## Task Commits

Each task was committed atomically:

1. **Task 1: tracer — append/read primitives, observe, history** — `ced631c` (feat)
2. **Task 2: dedup logic, verdict_changed, lease subcommand, last-moved** — `6540faf` (test, RED) → `ea22c4d` (feat, GREEN)
3. **Task 3: torn-line quarantine fixture (JOUR-04)** — `58b58b2` (test + fix) → `7037911` (test, T-16-01 lock-in + USAGE wiring)

**Plan metadata:** committed alongside this SUMMARY (see final commit below).

## Files Created/Modified

- `cairn/scripts/cairn-journal.py` — the single writer: record schema, `_append_record`/`_read_records` primitives, `_last_known`/`_resolve_last_value` dedup folding, `observe`/`lease`/`history`/`last-moved` subcommands
- `cairn/scripts/cairn-journal.sh` — thin exec wrapper, matches `cairn-gate.sh`'s shape
- `tests/cairn-journal.bats` — 10 tests: tracer, 3× observe dedup, lease subcommand, last-moved, 3× torn-tail, malformed-stdin (T-16-01)

## Decisions Made

1. **`history`/`last-moved` `--json` output shape.** The plan's prose said `--json` prints "a JSON array" for `history` but also said warnings appear "under a `warnings` key" in `--json` mode — these two statements are only simultaneously true if the top-level `--json` output is an object, not a bare array. Implemented `history --json` as `{"records": [...], "warnings": [...]}`, and `last-moved --json` as the per-axis dict with a `"warnings"` key merged in. Both satisfy every acceptance-criteria `jq` assertion given in the plan (`.records | length`, `.warnings`, `.disk`, `.lease.value`, etc.).

2. **The Task 1 tracer test's exact-4 assertion needed updating for Task 2.** Task 1 explicitly scoped `observe` to evidence axes only ("THIS task only needs `state_changed`"), so the tracer payload (which also carries `"verdict": "ok"`) produced exactly 4 `written` records at that point. Task 2 legitimately extends `observe` to also process `verdict` on the same CLI contract — the identical tracer payload now correctly produces 5 records (4 `state_changed` + 1 `verdict_changed`). Updated the tracer test's assertions accordingly rather than leaving a stale, now-incorrect count; the full suite (10/10) must pass as of the final commit, and it does.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Append-after-torn-tail corruption in `_append_record()`**

- **Found during:** Task 3, writing the "a corrupted trailing fragment is never fixed by a later write, only ever reported" fixture
- **Issue:** The plan's literal recipe (`os.open(O_WRONLY|O_CREAT|O_APPEND)` + one `os.write()` of the record line) is correct for the *normal* case, but has a latent bug for the *torn-write recovery* case: after a crash leaves the file NOT ending in `\n` (a torn tail), the next `observe`/`lease` call's `O_APPEND` write lands immediately after the garbage bytes with no separator, concatenating the new record onto the old fragment. `_read_records()`'s line-splitting then treats the whole merged blob as ONE unparseable line — quarantining not just the old torn record but the brand-new one too, which the fixture's own assertion (`history --phase 44` must show exactly 2 complete records: the original `planned` plus the new `executed`) caught directly (it returned 1, not 2).
- **Fix:** `_append_record()` now does a read-only pre-check (a separate, ordinary `open(path, "rb")` — the write fd is `O_WRONLY` and cannot itself be read from) of the current last byte. If it is not already `\n` (file-empty/new counts as "no separator needed"), a leading `\n` is folded into the SAME payload passed to the single `os.write()` call — so the whole thing (separator + record) still lands in exactly one atomic syscall, never a second write. This does not violate the "exactly one `os.write()` per append" contract; it just makes that one write's payload occasionally two bytes longer.
- **Files modified:** `cairn/scripts/cairn-journal.py` (`_append_record()`, plus the module docstring's atomicity section updated to document the guard)
- **Verification:** `tests/cairn-journal.bats` — "torn tail: a corrupted trailing fragment is never fixed by a later write, only ever reported" (now passes; failed before the fix, along with every other test, because of an unrelated bug this fix's first draft introduced — see below — since fixed)
- **Committed in:** `58b58b2`

**2. [Rule 3 - blocking bug in my own fix's first draft] `os.read()` on a write-only fd**

- **Found during:** Task 3, immediately after drafting fix #1 above
- **Issue:** My first attempt at the separator pre-check tried to `os.fstat()`/`os.lseek()`/`os.read()` the SAME fd that was opened `O_WRONLY` for the actual write — `os.read()` on a write-only descriptor raises `OSError: [Errno 9] Bad file descriptor`, breaking every subcommand that appends (all 9 previously-passing tests regressed to failing).
- **Fix:** Moved the pre-check to a separate, ordinary `open(journal_path, "rb")` context, entirely independent of the `O_WRONLY` write fd, before computing the payload and opening the write fd.
- **Files modified:** `cairn/scripts/cairn-journal.py` (`_append_record()`)
- **Verification:** Full suite re-run, 9/9 then 10/10 passing
- **Committed in:** `58b58b2` (folded into the same commit as fix #1 — this was caught and corrected before that commit, not a separate regression afterward)

**3. [Rule 2 - missing validation] `USAGE` constant was defined but unreferenced**

- **Found during:** final self-review pass (checking the file against `CONVENTIONS.md`'s die()+USAGE house pattern used by `cairn-gate.py`/`cairn-lease.py`)
- **Issue:** `_load_observe_payload()`'s `die()` calls didn't append the `USAGE` line, unlike `cairn-lease.py`'s equivalent manual-validation `die()` calls — a minor consistency gap, not a functional bug (argparse's own subcommand usage messages still fire for flag-level errors).
- **Fix:** Appended `\n{USAGE}` to `_load_observe_payload()`'s four `die()` calls.
- **Files modified:** `cairn/scripts/cairn-journal.py`
- **Verification:** `tests/cairn-journal.bats#observe: malformed stdin ... dies EXIT_USAGE, never a traceback` (new test, added to lock in T-16-01's threat-model claim)
- **Committed in:** `7037911`

---

**Total deviations:** 3 auto-fixed (2 Rule 1/3 bugs found via the plan's own required fixture, 1 Rule 2 consistency gap found on self-review)
**Impact on plan:** All three are necessary for correctness (the torn-tail fix is load-bearing for JOUR-04's actual guarantee) or consistency. No scope creep — no subcommand, flag, or record field beyond what the plan specified.

## Issues Encountered

None beyond the deviations above — no blockers, no auth gates, no package installs.

## User Setup Required

None — stdlib only, no external service configuration.

## Next Phase Readiness

- `cairn-journal.py`'s `observe`/`lease`/`history`/`last-moved` CLI contract is ready for Plan 16-02 (compaction, via `os.rename` per D-03) to build on, and for Plan 16-03 (lease wiring) and Plan 16-04 (status/verdict wiring) to call as the actual event source.
- `.cairn/journal.jsonl` is written by these tests but is NOT yet in `.gitignore` — Plan 16-05 owns that entry; this plan only confirmed the file gets written at the right path.
- No blockers for the next wave.

---
*Phase: 16-transition-journal*
*Completed: 2026-07-31*

## Self-Check: PASSED

- FOUND: cairn/scripts/cairn-journal.py
- FOUND: cairn/scripts/cairn-journal.sh
- FOUND: tests/cairn-journal.bats
- FOUND: .planning/phases/16-transition-journal/16-01-SUMMARY.md
- FOUND commit: ced631c
- FOUND commit: 6540faf
- FOUND commit: ea22c4d
- FOUND commit: 58b58b2
- FOUND commit: 7037911
- Full suite re-run at self-check time: `bats tests/cairn-journal.bats` — 10/10 passing
