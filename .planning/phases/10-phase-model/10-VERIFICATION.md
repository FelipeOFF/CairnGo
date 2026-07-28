# Phase 10 — Verification

**Verified:** 2026-07-28
**Requirement:** PANEL-01
**Verdict:** met. 0 blocking gaps.

## PANEL-01 — the phase model carries what a phase is

> **Done when** a phase is described by title and plan progress everywhere it
> appears, and the three surfaces are proven to render from the same model.

| Claim | Evidence |
|---|---|
| A phase carries its title | `--json` → `phases[].title`; terminal footer `phase 10/12 Phase model — read what a phase actually is`; HTML `<p class="pos-title">` |
| …and its plan progress | `plans_done`/`plans_total` from the roadmap line, the progress table, or `PLAN`/`SUMMARY` pairs on disk; one shared spelling via `phase_progress_text` |
| …and dependencies and on-disk state | `depends_on`, `blocked_by`, `disk_state`, `next_command` all present in the model |
| The three surfaces render from ONE model | Test "the terminal board, --json and the HTML page report the same title": reads the title from `--json`, then asserts it appears in the rendered board and in the written HTML. A surface re-deriving its own answer fails here |
| The counts cannot drift from the list | Test asserts `phase.total == len(phases)`, `phase.completed == len([complete])`, and `phase.title` equals the active phase's title in the model. `roadmap_phases()` is now a derivation of `phase_model()`, not a second parse |
| An em dash inside a title survives | Test with `Phase 3: Phase model — read what a phase actually is (PANEL-01)`; the completion suffix is stripped by shape, never by splitting on the dash |
| Both roadmap dialects parse | Tests cover `Phase N: Title (2/2 plans) — completed <date>` and `**Phase N: Title** - description` |
| Requirement ids are not mistaken for plan progress | Test asserts `["PANEL-04", "PANEL-05"]` off a trailing parenthetical |
| `next_command` is computed, not authored | Test walks the ladder: no artifacts → `/cairn:plan 3`, PLAN → `/cairn:work 3`, SUMMARY → `/cairn:verify 3` |
| A completed, archived phase is never told to re-plan | Test asserts phase 1 has `disk_state: none` and an empty `next_command` |
| Dependencies come from bd, before planning | Test registers a bd edge with `bd dep add` and asserts `depends_on: [3]`, `blocked_by: [3]` |
| A dependency already complete does not block | Test closes the target and asserts `depends_on: [1]`, `blocked_by: []` |
| PLAN.md frontmatter is honoured too | Test with `depends_on: ["03-phase-model"]` resolves to `[3]` |

## Defect found and fixed during this phase

bd reports dependency edges in **two different shapes** depending on the
subcommand: `bd list`/`bd ready` return a `dependencies` array, `bd blocked`
returns a flat `blocked_by` list and no `dependencies` at all. The first
implementation read only the array, which silently dropped every edge whose
target was still open — precisely the edges the parallelism section exists to
report. Caught by a failing test rather than by inspection; both shapes are read
now (`dep_target_ids`).

A sibling test that passed while that one failed was re-checked rather than
assumed correct: `bd ready` does carry `dependencies` when the issue has them,
so it passed for the right reason.

## Test evidence

- `tests/cairn-phase-model.bats` — 14/14.
- `tests/cairn-status.bats` — 43/43, no regression.

## Consumed by

Phase 11 renders the described pending list (PANEL-02) and the next-command
section (PANEL-03) from this model; phase 12 renders the parallelism note
(PANEL-04) from `blocked_by` and fills the board (PANEL-05).
