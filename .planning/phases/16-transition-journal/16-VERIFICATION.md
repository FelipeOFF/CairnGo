---
phase: 16-transition-journal
verified: 2026-07-31T19:34:34Z
status: passed
score: 14/14 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 16: Transition journal Verification Report

**Phase Goal:** o histórico do que realmente aconteceu sobrevive a uma queda e
consegue explicar um conflito, sem nunca virar autoridade sobre o estado
corrente.

**Verified:** 2026-07-31T19:34:34Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Method

Every truth below was checked at three levels: the code that is supposed to
implement it, the test that is supposed to prove it, and — for every load-
bearing claim — an actual live run of that test in this session (not a
re-statement of the SUMMARY's own reported numbers). Full suites were run
where feasible; `cairn-status.bats` and `cairn-doctor.bats` were run in full
in the background (8–16 min each) in addition to their targeted `-f` filters.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | (JOUR-01/04) `observe`/`lease` append `state_changed`/`verdict_changed`/`lease_changed` records carrying `actor`/`ts`/`nonce`/`phase`/`event`, and only on a genuine change — dedup, not a log of every render | ✓ VERIFIED | `cairn-journal.py:_envelope()`, `_state_changed_record()`, `cmd_observe()`'s diff-against-`_last_known()` loop; `tests/cairn-journal.bats` "tracer", "observe dedup" ×3 — ran live, 16/16 pass |
| 2 | (JOUR-04) A crash mid-write leaves an isolated, byte-offset-reported line; everything before it is still read via `history`/`last-moved`, never a crash or silent drop | ✓ VERIFIED | `cairn-journal.py:_parse_records()` (byte-offset quarantine, not line-number); fixture truncates **inside a JSON string value** and self-verifies `json.JSONDecodeError` before trusting the test — `tests/cairn-journal.bats` "torn tail" ×3 — ran live, pass |
| 3 | (JOUR-04, a real bug found and fixed) A new append landing on a torn (non-newline-terminated) tail does not concatenate onto the garbage and corrupt/lose the new record too | ✓ VERIFIED | `_append_record()`'s read-only pre-check + separator fold into the same `os.write()` payload (16-01-SUMMARY's documented deviation #1); `tests/cairn-journal.bats` "a corrupted trailing fragment is never fixed by a later write, only ever reported" — ran live, pass |
| 4 | (JOUR-02) The doctor's conflict report names, per conflict, when each cited source last moved — the exact seeded timestamp, or the literal phrase "never observed", never a blank or fabricated value | ✓ VERIFIED | `cairn-doctor.py:journal_last_moved()`/`_last_moved_clause()`, wired into `check_phase_corroboration()`'s per-conflict loop; `tests/cairn-doctor.bats -f "last-moved"` — ran live, 3/3 pass |
| 5 | (JOUR-02, D-04) The journal's history surfaces **only** inside the conflict report and the `history`/`last-moved` CLI — nothing was added to the board (terminal, `--json`, or HTML) | ✓ VERIFIED | `grep` of `render_html_inner` and the terminal-render path in `cairn-status.py` shows zero journal references; `journal_last_moved()`/`_last_moved_clause()` exist only inside `cairn-doctor.py`'s `check_phase_corroboration()` |
| 6 | (JOUR-02) `journal_last_moved()` is called at most once per phase, never once per conflict item, even for a phase with two simultaneous conflicts | ✓ VERIFIED | `last_moved_cache` dict in `check_phase_corroboration()`; `tests/cairn-doctor.bats` "journal_last_moved() is called at most once per phase" via a call-counting stub — ran live, pass |
| 7 | (JOUR-03) `corroborate()` is provably independent of the journal — it reads only its five scalar arguments (`n, disk_state, roadmap_complete, bd_val, bd_ok, state_md_active_phase`) and never opens/queries `.cairn/journal.jsonl` anywhere in its call graph | ✓ VERIFIED | Read `cairn-status.py:530-590` fresh: no journal reference in `corroborate()`'s body; `grep "cairn-journal\|CAIRN_JOURNAL"` on the whole file shows the only subprocess call is `observe`, at the very end of `phase_model()`, never `history`/`last-moved` |
| 8 | (JOUR-03) Deleting `.cairn/journal.jsonl` (with real accumulated history) changes **zero bytes** of the next `--json` corroboration render | ✓ VERIFIED | `tests/cairn-status.bats` "JOUR-03" — a 3-render structural (`jq -S .`) diff (no-journal read → populated-journal read → post-deletion read), pinned fixture with no `.cairn/sync.json` and no lease held (asserted directly) — ran live, pass |
| 9 | (JOUR-03) A hand-edit made entirely outside any `cairn-*` command is still caught by `corroborate()` on the **very first read**, proving detection never depended on the journal having observed an intermediate state | ✓ VERIFIED | Same test, Part 1: a plain `sed` on `ROADMAP.md` (never through a cairn script) against a fixture where `.cairn/journal.jsonl` does not exist yet at all — the resulting `roadmap`-vs-`disk` conflict is detected on the first `cairn-status.sh --json` call |
| 10 | (JOUR-05) `compact()` folds each phase's full history into exactly one `snapshot` record, written to a brand-new sibling file and swapped in via `os.rename` — never a rewrite of the live `journal.jsonl` in place | ✓ VERIFIED | `cairn-journal.py:compact()`/`_compact_locked()`; `tests/cairn-journal.bats` "compact: folds multi-phase history…" and "a crash between the sibling write and the rename leaves the original journal byte-for-byte unchanged" — ran live, pass |
| 11 | (JOUR-05) `last-moved`'s answer is structurally identical before and after compaction, for **every** phase touched, across all three real event kinds (state, verdict, lease) — never a spot-check of one field | ✓ VERIFIED | `tests/cairn-journal.bats` "replay equivalence" — 3 phases, ~39 synthetic records, `jq -S .` structural diff on `last-moved` for every phase, plus a secondary check that `history` shrinks to exactly one `snapshot` record per phase — ran live, pass |
| 12 | (JOUR-05, the hard race) A record appended by a genuinely separate process during compaction's own read-to-rename window survives — never silently discarded by a stale-read rename (Pitfall 14) | ✓ VERIFIED | `compact()`'s pre-rename `size_now != size_at_read` re-check, where `size_at_read` is derived from the **exact bytes** `_parse_records()` folds, never a second independent `stat()`; "THE LOAD-BEARING TEST" — a real backgrounded `compact` (`CAIRN_JOURNAL_COMPACT_TEST_DELAY=1`) racing a real second `observe` process — ran live, pass. 16-02-SUMMARY also documents the test was run once with the guard disabled and confirmed to fail exactly as predicted |
| 13 | (D-02) `cairn-journal.py` is the single writer — no second implementation of the `O_APPEND`+`os.write()` recipe exists; `cairn-lease.py`, `cairn-status.py`, `cairn-doctor.py` all shell out to it via `subprocess` | ✓ VERIFIED | `grep -rn "O_APPEND\|os\.write(" cairn/scripts/*.py` — every hit is inside `cairn-journal.py`; the three callers each define a `CAIRN_JOURNAL` env seam and call `subprocess.run([sys.executable, CAIRN_JOURNAL, ...])` |
| 14 | (resilience) A broken or missing `cairn-journal.py` never blocks lease acquisition, a corroboration render, or the doctor run — it only forgoes the journal entry and prints a warning; the `--actor`-omission bug that would have made every `release` silently never journal was found and fixed | ✓ VERIFIED | `cairn-lease.py:journal_lease_event()`, `cairn-status.py:journal_observe_phases()`, `cairn-doctor.py:journal_last_moved()` all try/except around `subprocess.run`, never `die()`/raise; `release_one`/`cmd_release --mine` both resolve and pass `--actor` (read directly, confirms 16-03-SUMMARY's documented fix); `tests/cairn-lease.bats -f "journal failure"` (2/2) and `tests/cairn-status.bats "journal observe: a broken CAIRN_JOURNAL…"` — ran live, pass |

**Score:** 14/14 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `cairn/scripts/cairn-journal.py` | Single append-only writer: `observe`/`lease`/`history`/`last-moved`/`compact` | ✓ VERIFIED | 949 lines, full module docstring as spec, no type hints (house convention); exists, substantive, wired (called by all 3 downstream scripts) |
| `cairn/scripts/cairn-journal.sh` | Thin exec wrapper | ✓ VERIFIED | Matches `cairn-gate.sh`'s shape exactly |
| `tests/cairn-journal.bats` | Full coverage incl. torn-line/compaction/race fixtures | ✓ VERIFIED | 16 tests, **16/16 pass** (ran live, full suite) |
| `cairn/scripts/cairn-lease.py` (modified) | `journal_lease_event()`, `CAIRN_JOURNAL` seam, wired in `cmd_acquire`/`release_one`/`cmd_release`, **not** `cmd_renew` | ✓ VERIFIED | Read the relevant sections directly; `cmd_renew` confirmed to have zero journal calls in any branch |
| `tests/cairn-lease.bats` (modified) | Wiring + resilience coverage | ✓ VERIFIED | 24 tests, **24/24 pass** (ran live, full suite) |
| `cairn/scripts/cairn-status.py` (modified) | `journal_observe_phases()`, wired once at the end of `phase_model()`; `corroborate()` untouched | ✓ VERIFIED | Read `corroborate()` and the `phase_model()` call site directly |
| `tests/cairn-status.bats` (modified) | Wiring + JOUR-03 proof | ✓ VERIFIED | 55 tests, **55/55 pass** (ran live, full suite in background) |
| `cairn/scripts/cairn-doctor.py` (modified) | `journal_last_moved()`/`_last_moved_clause()`, cached once per phase | ✓ VERIFIED | Read the relevant sections directly |
| `tests/cairn-doctor.bats` (modified) | Last-moved + gitignore coverage | ✓ VERIFIED, count claim corrected | 51 tests, **51/51 pass** (ran live, full suite in background). 16-05-SUMMARY.md claims "55/55" — this is **wrong**; `bats --count` and a live full run both confirm 51. See Anti-Patterns below — non-blocking, the 4 new tests genuinely exist and pass. |
| `.gitignore` | `.cairn/journal.jsonl*` glob | ✓ VERIFIED | Present at line 7; `git status --porcelain` on the live repo shows no journal file staged or untracked-visible |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `cairn-lease.py` (`cmd_acquire` fresh/reclaim, `release_one`, `cmd_release --mine`) | `cairn-journal.py lease` | `CAIRN_JOURNAL` subprocess, genuine-transition-only | ✓ WIRED | `already_mine` (heartbeat via acquire) and `cmd_renew` correctly write zero; verified against live test output showing exact 1-record-per-transition counts |
| `cairn-status.py` (`phase_model()`, once at the very end) | `cairn-journal.py observe` | `CAIRN_JOURNAL` subprocess, one batched call | ✓ WIRED | Call-counting stub test confirms exactly one subprocess spawn per `--json` render, not one per phase |
| `cairn-doctor.py` (`check_phase_corroboration()`) | `cairn-journal.py last-moved` | `CAIRN_JOURNAL` subprocess, cached per phase | ✓ WIRED | Call-counting stub confirms at most one call per phase even with 2 simultaneous conflicts |
| `cairn-status.py corroborate()` | `cairn-journal.py` (any subcommand) | — | ✓ CONFIRMED NOT WIRED (by design, JOUR-03) | `grep` shows zero journal references inside `corroborate()`'s call graph; only `observe` is ever called, and only after `corroborate()` has already produced every phase's answer |

### Behavioral Spot-Checks / Test Execution

| Suite | Command | Result | Status |
|-------|---------|--------|--------|
| `tests/cairn-journal.bats` | `bats tests/cairn-journal.bats` (full, live) | 16/16 pass | ✓ PASS |
| `tests/cairn-lease.bats` | `bats tests/cairn-lease.bats` (full, live) | 24/24 pass | ✓ PASS |
| `tests/cairn-status.bats` | `bats tests/cairn-status.bats -f "journal observe\|JOUR-03"` then full suite (live, background) | 4/4 then 55/55 | ✓ PASS |
| `tests/cairn-doctor.bats` | `bats tests/cairn-doctor.bats -f "last-moved\|gitignore"` then full suite (live, background) | 4/4 then 51/51 | ✓ PASS (count claim in 16-05-SUMMARY.md corrected — see below) |

No probes (`scripts/*/tests/probe-*.sh`) apply to this phase — bats is the project's test runner for these scripts.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| JOUR-01 | 16-01, 16-03, 16-04 | Toda transição de estado de fase é registrada com actor, instante, fase e evento | ✓ SATISFIED | Truths #1, #13, #14 above |
| JOUR-02 | 16-01, 16-05 | O journal explica um conflito mostrando quando cada lado se moveu | ✓ SATISFIED | Truths #4, #5, #6 above |
| JOUR-03 | 16-04 | O journal nunca é autoridade única sobre o estado corrente | ✓ SATISFIED | Truths #7, #8, #9 above |
| JOUR-04 | 16-01 | Um registro truncado por queda de processo é isolado e reportado com sua posição, nunca descartado em silêncio | ✓ SATISFIED | Truths #2, #3 above |
| JOUR-05 | 16-02 | O journal tem compactação projetada desde o início, com replay provado idêntico ao original | ✓ SATISFIED | Truths #10, #11, #12 above |

No orphaned requirements — all 5 JOUR-* requirements map to a plan in this phase, matching `.planning/REQUIREMENTS.md`'s traceability table and `16-BEADS-MAP.md`'s 1:1 issue mapping.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/phases/16-transition-journal/16-05-SUMMARY.md` | "Verification" section | Claims `bats tests/cairn-doctor.bats` full suite is "55/55 passing" | ℹ️ Info | **Factually wrong, but non-blocking.** `bats --count tests/cairn-doctor.bats` and a live full run both return **51**, not 55. Traced the actual history: `git show <pre-16-05-commit>:tests/cairn-doctor.bats \| grep -c "^@test"` = 47; 16-05 added exactly 4 tests (3 in `5e0866b`, 1 in `bda93f0`) = 51. The SUMMARY's own prose says "51/51 pre-existing + 4 new" then states the total as 55 — an internal arithmetic slip (the "51 pre-existing" figure was itself wrong; it should have read 47). The 4 new tests genuinely exist, are genuinely load-bearing (16-05-SUMMARY documents 5 break/restore experiments per test), and all pass — this is a self-reported-number error, not a functional gap, and does not affect any JOUR-01..05 truth or ROADMAP success criterion. |

No debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) found in any file this phase modified. No stub returns, no hardcoded-empty data flowing to a report, no dead controls.

### Human Verification Required

None. Every truth in this phase is either a deterministic file/parse property (append atomicity, torn-line quarantine, gitignore) or a race/concurrency property that was proven with a **real second process** (the compaction race, the concurrent-append survival test) rather than by inspecting a lock. All were exercised live in this session, not merely read from SUMMARY.md.

### Gaps Summary

None. All 4 ROADMAP success criteria and all 5 JOUR requirements are backed by code that does what it claims and by tests that were run live in this session and genuinely fail without the guard they exist to prove (documented per-plan in the "Deviations"/"Load-Bearing Verification" sections of 16-01 through 16-05's SUMMARYs, and spot-confirmed here for JOUR-03 and the compaction race by reading the actual production code, not just the test).

The one finding — 16-05-SUMMARY.md's inflated "55/55" claim for `cairn-doctor.bats` (actual: 51/51) — is recorded above as a non-blocking informational anti-pattern. It does not gate this phase: it is a reporting inaccuracy in a SUMMARY, not a gap in the shipped behavior.

---

_Verified: 2026-07-31T19:34:34Z_
_Verifier: Claude (gsd-verifier)_
