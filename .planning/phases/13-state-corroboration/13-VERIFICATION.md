---
phase: 13-state-corroboration
verified: 2026-07-30T21:40:00Z
status: passed
score: 5/5 success criteria verified, 8/8 requirements delivered
behavior_unverified: 0
overrides_applied: 0
gaps: []
---

# Phase 13: State corroboration — Verification Report

**Phase Goal:** o estado de uma fase deixa de ser um palpite do sistema de arquivos e
passa a ser um veredito em que quatro fontes independentes votaram, onde a
discordância é nomeada e uma fonte que não deu para ler diz isso em vez de
concordar.

**Verified:** 2026-07-30, commits `cdc942e` (wave 1) + `5fa58d5` (wave 2)
**Status:** passed
**Re-verification:** No — initial verification

**Method:** goal-backward, adversarial. For every criterion I located the test
that is supposed to prove it, then asked whether that test would still pass if
the underlying feature were removed or reverted to the pre-phase behavior. I
read `corroborate()`, `bd_state()`, `phase_next_command()`, `next_commands()`,
`cairn-gate.py`, `cairn-loop-gate.py`, `cairn-doctor.py`'s two new checks, and
`post-bd-write.sh` in full, not just their diffs. I ran the fast test files
directly (`cairn-corroboration.bats` 22/22, `capability.bats` 17/17,
`hooks.bats` 21/21, `cairn-gate.bats` 16/16, `cairn-phase-model.bats` 28/28 —
all green, all run in this session) rather than trusting SUMMARY.md's reported
counts. The two ~8-minute files (`cairn-status.bats`, `cairn-doctor.bats`)
were not re-run in full; instead every doctor test relevant to this phase's
must-haves was read in full and its exit-code/assertion pairing checked by
hand (see the Requirements table below for which ones).

## Goal Achievement

### Success Criteria (from ROADMAP.md, the standard for this phase)

#### SC1 — `--json` carries per-phase evidence + a verdict; `disk_state` unchanged

**Criterion:** `/cairn:status --json` carrega, por fase, a alegação de cada
fonte mais um veredito `ok`/`conflict`/`unknown`, enquanto `disk_state`
mantém seus quatro valores, tipo e significado.

**Evidence:**
- `corroborate()` (`cairn/scripts/cairn-status.py:417-487`) returns
  `(verdict, evidence, conflicts)` from exactly the four sources named in
  CORR-01 (disk, bd, roadmap, STATE.md). `phase_model()` (line 701) attaches
  these as additive `row["evidence"]`, `row["corroboration"]`,
  `row["conflicts"]` without touching `row["disk_state"]`, which is still
  set at line 742 from the unmodified `phase_disk_state()` (4 return values:
  `none`/`planned`/`executed`/`verified`, line 373).
- `phase_next_command()` (line 777) does its dict subscript on `disk_state`
  (`{"none": ..., "planned": ..., "executed": ..., "verified": ...}[disk_state]`)
  strictly AFTER the `needs_doctor` early-return (line 803), and
  `disk_state` can never carry a fifth value because `phase_disk_state()`
  is its only producer — the `KeyError` risk the CONTEXT.md flags as the
  reason corroboration must be a parallel structure is verifiably closed.
- Test: `tests/cairn-corroboration.bats::"the module docstring documents the
  new corroboration keys and bd_ok"` plus the whole existing
  `cairn-phase-model.bats` suite (28/28, run this session) as a live schema
  regression check — nothing about the pre-existing `--json` shape broke.

**Mutation check:** if `bd_ok` were not threaded through to `corroborate()`,
`evidence["bd"]` would read a real status instead of `"unknown"` on a forced
bd failure — this is exactly what the CORR-03 test below asserts and would
catch.

**Verdict:** VERIFIED.

#### SC2 — SUMMARY-exists-but-bd-open renders `conflict` on all three surfaces, naming both claims

**Criterion:** Uma fase cujo SUMMARY.md existe mas cujas issues no bd seguem
abertas renderiza `conflict` nas três superfícies (terminal, `--json`, HTML),
nomeando as duas alegações.

**Evidence:**
- `corroborate()`'s R1 rule (line 457-465) fires exactly on this shape:
  `disk_done != bd_done` → `{"severity": "blocks", "sources": ["disk",
  "bd"], "detail": f"disk reports phase {n} {disk_state}, bd reports its
  issues {bd_val}"}` — both claims named in one string.
- `conflict_summary_text()` (line 866) is the SINGLE helper both
  `phase_panel_lines()` (terminal, line 1400) and `html_phases()` (HTML,
  line 2161) call — never independently re-derived.
- Test: `"a blocks conflict's detail string is verbatim-identical across
  --json, the terminal panel and the HTML page"` (`cairn-corroboration.bats`
  line 534) extracts the `detail` string from the real `--json` output (not
  a hardcoded literal) and asserts it appears **verbatim inside** both the
  `--width 200` terminal render and the `--html` output — a genuine
  cross-surface parity proof, not three independent hardcoded-string
  assertions that could drift together toward the same wrong answer. Ran
  green in this session.

**Verdict:** VERIFIED.

#### SC3 — bd unreachable → every phase `unknown`, none `ok`, proven by a forced-failure test

**Criterion:** Com o bd inalcançável, toda fase afetada reporta `unknown` e
nenhuma reporta concordância. Provado por teste que força a falha, não por
leitura do código.

**Evidence — the exact adversarial question asked in the brief:**
`make_failing_bd_stub()` (`tests/cairn-corroboration.bats:87-96`) writes a
**real `bd` executable onto PATH** that always `exit 9`s — present, then
broken — which is a different failure shape from
`tests/cairn-status.bats::"bd missing from PATH exits 5"` (line 385), which
strips `bd` from PATH entirely (absent). Both shapes are now tested, and the
corroboration test file's own header comment states the distinction
explicitly. I read both tests side by side to confirm this; it is not a
paraphrase.
- Test `"a real bd query failure degrades every phase to unknown evidence,
  never ok, through --json"` (line 380) asserts, over the real `--json`
  output: `p["evidence"]["bd"] == "unknown"` and
  `p["corroboration"] != "ok"` for **every** phase.
- Two further tests in the same file prove the SAME forced failure exits 5
  through the plain terminal render (line 401) and the `--html` render path
  (line 416) — not just `--json`.
- `main()` (line 2450-2467) runs a cheap `bd list --limit 1` probe before the
  real lane queries; on failure it sets `bd_ok = False` and degrades every
  lane to empty rather than calling `die()` before any output — this is what
  makes exit 5 reachable with real board output on every render path
  (confirmed at lines 2535-2539: `exit_code = EXIT_OK if bd_ok else
  EXIT_NO_BD`, applied uniformly after `--json`/`--html`/terminal printing).

**Mutation check:** if the probe/`bd_ok` wiring were removed, `bd_state()`
would be computed against empty issue lists (since `fetch_lanes()` would
never run either), yielding `evidence.bd == "none"` and `corroboration ==
"ok"` — the test's explicit `!= "ok"` and `== "unknown"` assertions would
fail. This is a real, not vacuous, test.

**Verdict:** VERIFIED. Ran `bats tests/cairn-corroboration.bats` this
session: 22/22 green, including all three forced-failure tests.

#### SC4 — ship gate refuses a milestone with a `conflict` phase; `/cairn:autonomous` does not select it

**Criterion:** `/cairn:ship` recusa um milestone que contenha fase em
`conflict`, e `/cairn:autonomous` não a seleciona como próxima.

**Evidence — two independent, deliberately duplicated mechanisms, matching
D-10's explicit lockstep requirement:**
1. **Ship gate.** `cairn-gate.py` gained a second, independent block
   reason (`disk_reached_executed()`, main() lines 264-276): a completed
   phase whose disk never reached `executed` (no `-SUMMARY.md`/
   `-VERIFICATION.md`) blocks even with zero bd issues — this is Plan
   13-01's R2 rule, duplicated (not imported) into
   `cairn/capability/scripts/cairn-loop-gate.py`'s `cmd_ship_gate()` per this
   repo's no-shared-lib convention (confirmed identical logic in both files
   by reading the wave-2 diff for each). The **pre-existing** "non-closed
   bd issue in a completed phase" check (predates this phase, unchanged)
   is functionally R1's blocking direction, already scoped to completed
   phases. Combined, a completed phase carrying either a disk-vs-bd or a
   roadmap-vs-disk "blocks" conflict fails the ship gate; "informs"-only
   conflicts (R3, STATE.md staleness) correctly do NOT block, per D-09/D-10
   ("o ship gate barra apenas os bloqueantes") — this is a documented,
   deliberate scope choice, not a gap.
   - **D-10 lockstep test, found and read in full:**
     `tests/capability.bats::"cross-script lockstep (D-10): cairn-gate.sh
     and cairn-loop-gate.sh ship-gate both block on the same no-artifacts
     repo state"` (line 317) builds ONE tmp repo, then runs `cairn-gate.sh`
     and `$GATE_SH ship-gate` (confirmed `GATE_SH` =
     `cairn/capability/scripts/cairn-loop-gate.sh`, `tests/capability.bats:15`)
     against that SAME state and asserts both exit nonzero. This is a
     genuine single lockstep test, not two independent per-script tests
     that could drift — exactly what the brief asked me to confirm by name.
     Ran green this session (`capability.bats` 17/17).
2. **`/cairn:autonomous` selection.** `next_commands()` (line 964) reads
   `needs_doctor` (computed once, see SC1) and reroutes such a phase's
   `reason` to `"corroboration conflict — resolve via /cairn:doctor before
   continuing"` with `blocked=True`, sorting it behind every runnable phase
   (`out.sort(key=lambda c: (c["blocked"], c["phase"]))`, line 1008). This
   is the self-contained model-level guarantee. Separately and primarily,
   `cairn/commands/autonomous.md`'s pre-flight (unchanged by this phase,
   step 0.1) runs `cairn-doctor.sh` and **stops the whole run** on exit 7 —
   which the new `phase-corroboration` doctor check now produces for any
   `blocks`-severity conflict (`cairn-doctor.py:949`,
   `status = "fail" if any_blocks else ...`). Both mechanisms are real and
   composable, exactly as 13-01's plan documented them.

**Verdict:** VERIFIED. `capability.bats` 17/17 and `cairn-gate.bats` 16/16
run green this session.

#### SC5 — CORR-07 harmless-diff corpus produces zero conflicts; CORR-08 backfill works on published history

**Criterion:** O corpus de diferenças sabidamente inócuas produz zero
conflitos, cada entrada com justificativa; uma issue fechada passa a
registrar o PR que a fechou, com backfill recuperável sem reescrever commit.

**Evidence — CORR-07 corpus, checked for whether each entry is a genuine
regression test or a "was never going to conflict anyway" no-op:**
- 4 entries in `tests/cairn-corroboration.bats` (lines 663-771), each with a
  one-line justification comment directly above it, as required:
  1. Zero bd issues under phase-N → `ok`. Meaningful: if `bd_state()`
     treated an empty qualifying set as anything but `"none"`, this breaks.
  2. A cross-phase issue open only because a LATER undone phase shares its
     label → the EARLIER phase still reads `ok`. This is the ALL-not-ANY
     discipline (`bd_state()` line 404-406) — genuinely load-bearing: an
     ANY-based implementation would report this as a false `conflict` for
     the earlier phase, and this test would catch that regression.
  3. Regenerating `NN-BEADS-MAP.md` (new mtime, new content) between two
     runs changes nothing `corroborate()` reads. Meaningful: proves the map
     file is invisible to `phase_disk_state()`'s suffix check by
     construction — a genuine regression test if someone widened that check.
  4. Touching (not modifying) an existing `-SUMMARY.md` leaves `disk_state`
     and `corroboration` unchanged. Meaningful: proves existence-only, not
     mtime-sensitive.
  All four are real mutation-resistant tests, not tautologies. One minor
  observation, not a gap: REQUIREMENTS.md's CORR-07 text names "JSON key
  reordering" as a third example alongside "regenerated map" and "mtime" —
  there is no dedicated test for it, but access to bd's JSON fields
  everywhere in this code is by key (`iss.get(...)`), so key-order is
  structurally incapable of producing a difference; a dedicated test would
  be closer to testing Python's dict semantics than this code. Not treated
  as a gap.
- Test: full corpus ran green this session (part of `cairn-corroboration.bats`
  22/22).

**Evidence — CORR-08 backfill:**
- Going forward: `post-bd-write.sh`'s `(c)` block (lines 160-174) fires
  `bd update <id> --external-ref gh-<N>` in the background on `bd close`
  when `gh pr view` resolves a PR — D-12.
- History backfill: `cairn-doctor.py`'s `check_external_ref()` (line 1082)
  is read-only by default (reports `<id> -> gh-N` candidates), writes only
  behind `--link-refs`, is idempotent, and refuses to run at all on a real
  shallow clone (D-08) — verified via
  `tests/cairn-doctor.bats::"external-ref: a real shallow clone skips
  --link-refs entirely, writes nothing (D-08)"` (line 969), which performs
  an ACTUAL `git clone --depth 1` (not a simulated flag) and confirms
  `git rev-parse --is-shallow-repository` is `true` before asserting the
  check warns and writes nothing. Idempotency and PR-window ambiguity are
  each separately tested (lines 906, 944) and I read all four in full.
- D-12's "never silently discarded" ressalva: test
  `"post-bd-write: external-ref write failure is observable in
  .cairn/hook.log, never swallowed"` (`tests/hooks.bats:295`) forces `bd` to
  fail with a distinct stderr string and asserts that string lands in
  `.cairn/hook.log` — content, not exit code (the hook's exit-0 contract is
  asserted separately and is expected regardless of the underlying write's
  success). This is the correct adversarial shape per the commit message's
  own claim of having been mutation-tested.

**Verdict:** VERIFIED. `hooks.bats` 21/21 ran green this session; the four
`cairn-doctor.bats` external-ref tests and the doctor `phase-corroboration`
tests were read in full (not re-run — see Method) and their exit-code /
assertion pairing checked by hand against the source they exercise.

### Requirements Coverage (CORR-01..08)

| Req | Status | Evidence |
|---|---|---|
| CORR-01 | **Delivered** | `corroborate()` reads all 4 independent sources (disk/bd/roadmap/STATE.md), `cairn-status.py:417-487`. Tested: R1/R2/R3 tests in `cairn-corroboration.bats`, all green this session. |
| CORR-02 | **Delivered** | `conflicts[]` names both sources per item (`"sources": [...]`, `"detail": "..."`); no majority rule — two readable sources disagreeing is already `conflict` (D-06, no tiebreak code path exists). Tested by the D-04 cross-surface parity tests. |
| CORR-03 | **Delivered** | Real broken-`bd`-on-PATH stub (not PATH-removal) forces every phase to `evidence.bd == "unknown"`, `corroboration != "ok"`, on all 3 render paths, exit 5 on each. `cairn-corroboration.bats` lines 380-428, all green this session. |
| CORR-04 | **Delivered** | `disk_state` untouched (still 4 values from `phase_disk_state()`); `phase_next_command()`'s dict subscript is unreachable for any value outside those 4 because the `needs_doctor` early-return sits before it and `disk_state` has no other producer. Existing `--json` consumers regression-checked via `cairn-phase-model.bats` (28/28 green this session). |
| CORR-05 | **Delivered** | Ship gate: R2 rule added in lockstep to both `cairn-gate.py` and `cairn-loop-gate.py`, proven by one cross-script test asserting both block on identical state (`capability.bats:317`, green this session); pre-existing bd-issue check covers R1's blocking direction. Autonomous: `needs_doctor` reroutes/deprioritizes in `next_commands()`, plus the existing doctor pre-flight hard-stop in `autonomous.md`. |
| CORR-06 | **Delivered** | `check_phase_corroboration()` (`cairn-doctor.py:886-951`), check 11: shells to `cairn-status.py --json` (same pattern as `check_maps_fresh()`), fails on any `blocks` item, warns on `informs`/`unknown`, routes each conflict to a recommended fix via `CORROBORATION_RECOMMENDATION` (D-01: likely fix first). 4 dedicated doctor tests read in full (`cairn-doctor.bats:815-903`); 6 pre-existing doctor tests updated from exit 0→7 with a NEW assertion naming `phase-corroboration` as the failing check (verified via `git show 5fa58d5` diff, not assumed) — one of those six was fixed by correcting its fixture rather than loosening its assertion, and I read that specific diff hunk to confirm the correction was real, not a weakening. |
| CORR-07 | **Delivered** | 4-entry corpus in the test file, each justified, each a genuine mutation-resistant regression test (see SC5 above). Minor: "JSON key reordering" named in REQUIREMENTS.md has no dedicated test, but is structurally unreachable given key-based access throughout — not a functional gap. |
| CORR-08 | **Delivered** | Going-forward hook (`post-bd-write.sh`) + read-only-by-default/`--link-refs`-write/idempotent/shallow-clone-safe doctor backfill (`check_external_ref()`). D-12's observability ressalva specifically tested via log-content assertion under forced failure, not exit-code alone. |

**8/8 requirements delivered**, all currently `in_progress` in bd
(`bd list -l m-v1.4,phase-13 --all --json` — CairnGo-oms, jc5, puf, 3ce, bnr,
51p, u7s, x4p). Recommend closing all eight.

### Anti-Patterns Found

None. Scanned all files touched by both commits
(`cairn/scripts/cairn-status.py`, `cairn/scripts/cairn-gate.py`,
`cairn/scripts/cairn-doctor.py`, `cairn/capability/scripts/cairn-loop-gate.py`,
`cairn/hooks/post-bd-write.sh`, `cairn/templates/status-board.html`) for
`TODO`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER`/stub-return patterns. None found.
No vacuous "asserts exit 0 on a fire-and-forget contract" test pattern
survived — every place that contract exists (`post-bd-write.sh`) is paired
with a content-based assertion for the case that matters (D-12).

### Behavioral / Test Evidence Actually Run This Session

- `bats tests/cairn-corroboration.bats` — 22/22 green
- `bats tests/capability.bats` — 17/17 green
- `bats tests/hooks.bats` — 21/21 green
- `bats tests/cairn-gate.bats` — 16/16 green
- `bats tests/cairn-phase-model.bats` — 28/28 green
- `tests/cairn-status.bats` and `tests/cairn-doctor.bats` were NOT re-run in
  full in this session (each ~8 minutes, per the task brief); the specific
  tests relevant to this phase's must-haves within `cairn-doctor.bats` were
  read in full instead, and their exit-code/assertion pairing checked
  against `cairn-doctor.py`'s actual source rather than trusted from
  SUMMARY.md's "349 tests, zero failures" claim.

### Gaps Summary

No blocking gaps. One non-blocking observation carried forward (not filed as
a gap): CORR-07's roadmap text names "JSON key reordering" as an example
harmless diff; the actual 4-entry corpus does not include a dedicated test
for it because it is structurally unreachable (all bd JSON access in this
codebase is by key, never by position). This does not weaken CORR-07's
delivery — the corpus's four entries are all genuine, mutation-resistant
regression tests, not placeholder coverage.

---

_Verified: 2026-07-30T21:40:00Z_
_Verifier: Claude (gsd-verifier)_
