---
phase: 13-state-corroboration
plan: "01"
status: complete
requirements: [CORR-01, CORR-02, CORR-03, CORR-04]
beads: [CairnGo-oms, CairnGo-jc5, CairnGo-puf, CairnGo-3ce]
---

# Phase 13 Plan 01 — Summary

A phase's state stopped being a guess made from four filenames.

## What shipped

**`bd_state()` and `corroborate()`, wired into `phase_model()`.** Every phase row
now carries `evidence` (what each source independently claims — disk, bd, roadmap
checkbox, `STATE.md`'s `active_phase`), `corroboration` (`ok` / `conflict` /
`unknown`) and `conflicts` (the itemised disagreements). All readable sources must
agree; there is no majority rule and no tiebreak, because a tiebreak is a source
winning in silence.

**`disk_state` was not touched.** Same four values, same type, same meaning, so
anything already parsing `--json` keeps working. This was not caution for its own
sake: `phase_next_command()` indexes a bare dict literal on it, and a fifth value
would have been a straight `KeyError` in production. The new guard sits before
that subscript and the dict itself is byte-identical.

**`needs_doctor` is computed once.** In `phase_model()`'s loop, read by
`phase_next_command()`'s guard and by `next_commands()`'s blocked fold, nowhere
else. An earlier revision of this plan computed the predicate in two places and
they drifted inside a single review round — the guard treated an `unknown` verdict
as routable while the sort did not, so an `unknown` phase could still surface as
the next thing to work on.

**An unreachable bd reports `unknown` everywhere and agreement nowhere.** All
three render paths now exit 5 carrying real output instead of a silent 0.

## The thing worth knowing

The test that proves the fail-open behaviour puts a `bd` on PATH that **exits
nonzero**. The repo already had a test that removes `bd` from PATH entirely, and
that proves a different thing: absence is not failure. A tool that is present and
broken is the case that produces a confident wrong answer, and it was the one
nothing covered.

One structural fact surfaced while building the fixtures: `corroborate()`'s
`roadmap_complete` argument is the same value `pending_phases()` filters on, so
the roadmap-versus-disk rule can only ever fire on a phase already excluded from
the pending panel. A blocking conflict on a *pending* phase therefore always comes
from disk-versus-bd. Knowing that is the difference between a fixture that tests
something and one that can never fire.
