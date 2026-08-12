# bookkeep-drift — the frozen disagreement

**Captured:** 2026-08-03  
**From:** `.planning/` of this repository at `ce372f4ef6aa2e5c875d1625631856dd6de14eb8`  
**Writer:** `capture.sh` in this directory. Nothing else writes these files, and no test ever calls it.

**NOTHING BELOW IS TO BE FIXED IN THE FIXTURE.** Every line of this inventory is test input: `cairn-bookkeep.py reconcile` has to NAME each one. Tidying a file here deletes the only realistic input this command has, and a command that only meets consistent files proves it can write, never that it can resolve drift.

The counts below were measured by `capture.sh` itself, with its own deliberately dumb counters — never by `cairn-bookkeep.py`. Two independent counts of the same bytes is the point: if this manifest and `reconcile` disagree, that is a finding about one of them.

## Frozen files

| File | Bytes | sha256 |
|------|-------|--------|
| `ROADMAP.md` | 30638 | `27e7d06f1f7843e2657cf67d01d33ec4e064887a1de650c7c7bfc4a45d3d3125` |
| `REQUIREMENTS.md` | 6982 | `d9a37563721469dc7b01b1f0b5bd7e4bce3ce9abe86faa83b8b3dedb291e4701` |
| `STATE.md` | 13436 | `a26f34b1e4c421563e89b916abbeea67b9c8fbc44d5dcf957f3c3b70ec396f67` |

`phases.tsv` is not hashed: it is a derived index of .planning/phases/, rewritten by this script alongside the copies.

## The disagreement inventory

1. **35 active requirements** in REQUIREMENTS.md's milestone section, of which 0 carry a checked box.
2. **33 rows** in the ROADMAP coverage table — 2 active requirement(s) have no row at all: `AUTO-05`, `AUTO-06`.
3. The coverage footer asserts `29 requisitos, 29 mapeados.` — a claim of 29 against 33 actual rows and 35 actual active requirements. Neither number is right, and they are wrong for different reasons.
4. **Deferred, and NOT a disagreement:** `CORR-09` lives under a deferred heading and is out of the table by rule. An explained absence is not drift — but silencing it would repeat the same defect in the other direction, so `reconcile` reports it under `requirements.deferred`.
5. **`BOARD-01`** is `- [ ]` in REQUIREMENTS.md and `Complete` in the coverage table, while the phase that carries it is already checked off in the phase list.
6. **The sharpest one: phase 29's requirements line is an ellipsis.** It reads `**Requirements**: AUTO-01 … AUTO-08`, and an id scan over it yields 2 ids — `AUTO-01`, `AUTO-08` — not the eight the prose means. There is no readable source of phase 29's requirements inside the ROADMAP today. Two tools already answer `ok` over that silence: `cairn-doctor req-issue` reports `29 requirement(s) mapped` (the sum of every phase's parsed ids), and `29-BEADS-MAP.md` says `None — every phase requirement is mapped`. Note the coincidence, because it is how this survives: that total happens to equal the wrong footer's number, from an unrelated cause.
7. **STATE.md frontmatter vs the disk.** `progress.total_plans: 3` and `progress.completed_plans: 3` against 10 `*-PLAN.md` and 3 `*-SUMMARY.md` actually on disk. The phase pair (`1`/`10`, percent `10`) still agrees with the 10 phase lines — that half of the arithmetic is the part D-01 keeps.
8. **`last_activity_desc`** reads `Milestone v1.5 Legible State aberto (9 fases, 24 requisitos)` against 10 phases and 35 active requirements. Free-text frontmatter nobody recalculates; `reconcile` reports it and does not propose to rewrite it.
9. **The prose body of STATE.md contradicts its own frontmatter** — the body names an older phase and an archived milestone while the frontmatter says `current_phase: 29`. That prose is the measured source of the `current_phase: 29 -> 18` corruption `state record-session` produced (29-CONTEXT.md, D-01). `reconcile` never reads the body, and a test asserts the older number appears nowhere in its computed output.
10. **10 plan checkbox line(s)** still read `- [ ]` in the phase detail blocks; some of them have a `*-SUMMARY.md` sitting next to them on disk.

## Phase tree (`phases.tsv`)

| Phase dir | `*-PLAN.md` | `*-SUMMARY.md` | verification |
|-----------|-------------|----------------|--------------|
| `20-group-model` | 3 | 3 | yes |
| `29-nothing-mechanical-stays-manual` | 7 | 0 | no |

`make_drift_fixture` (tests/helpers.bash) rebuilds this tree with EMPTY files of the right names and commits the result, so the diff a write test measures has a denominator.
