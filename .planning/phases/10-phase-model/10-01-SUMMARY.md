---
phase: 10-phase-model
plan: "01"
status: complete
requirements: [PANEL-01]
beads: [CairnGo-b33]
---

# Phase 10 Plan 01 — Summary

The status surface now reads what a phase *is*, and all three renderings come
from that one read.

## What shipped

`phase_model()` in `cairn-status.py` — one list, built once in `main()`, handed
to the terminal board, `--json` and the HTML page. Each phase carries:

| field | source |
|---|---|
| `title`, `requirements`, `completed_on` | roadmap checkbox line |
| `milestone`, `plans_done` / `plans_total` | progress table, falling back to the roadmap line, then to `PLAN`/`SUMMARY` pairs on disk |
| `disk_state` | artifacts present: none → planned → executed → verified |
| `depends_on`, `blocked_by` | bd issue edges ∪ `PLAN.md` `depends_on:` frontmatter |
| `next_command` | computed from `disk_state` |

`roadmap_phases()` survives only as a derivation of the model, so the counts in
the footer and the described list cannot drift apart.

Rendered today: the terminal footer reads `phase 10/12 Phase model — read what a
phase actually is · v1.3 · done: 26`, the HTML header carries the same title
under the position line, and `--json` exposes the whole model under `phases`.

## What the work turned up

**bd reports dependency edges in two different shapes, silently.** `bd list` and
`bd ready` return a `dependencies` array of `{issue_id, depends_on_id}`;
`bd blocked` returns a flat `blocked_by` list of ids and no `dependencies` at
all. Reading only the first shape loses every edge whose target is *still open*
— which is exactly the set the parallelism answer is about. Both are read now.
This was caught by a test failing, not by inspection.

**A test passed for a reason worth checking.** The "dependency on a completed
phase" case went green while its sibling failed, which looked like luck. It was
not: `bd ready` does carry `dependencies` when the issue has them, and an
earlier probe had simply landed on an issue with none. Verified before trusting
it.

**Two roadmap dialects, one parser.** `- [x] Phase 1: Title (2/2 plans) —
completed <date>` and `- [x] **Phase 1: Title** - description` both occur.
Titles carry their own em dashes, so the completion suffix is stripped by shape
and never by splitting on the dash — the case that would silently truncate
"Phase model — read what a phase actually is" to "Phase model".

**Archived phases would have been told to re-plan.** Completing a milestone
moves its phase dirs out of `.planning/phases/`, leaving `disk_state: none` for
work that is finished. Reading disk state alone suggested `/cairn:plan 1`. A
roadmap-complete phase now returns no command at all; when the checkbox and the
artifacts genuinely disagree, that is `/cairn:doctor`'s report to make.

## Verification

- `bats tests/cairn-phase-model.bats` — 14 tests green, including the
  cross-surface proof: the title is read from `--json`, then asserted present in
  the rendered terminal board and in the written HTML file. A surface that
  re-derives its own answer fails there.
- `bats tests/cairn-status.bats` — 43 green, unchanged apart from the footer now
  carrying the phase title.
- On this repo the model resolves the real graph: phase 11 blocked by 10, phase
  12 blocked by 10 and 11, phase 10 free — which is the input phase 12 needs.
