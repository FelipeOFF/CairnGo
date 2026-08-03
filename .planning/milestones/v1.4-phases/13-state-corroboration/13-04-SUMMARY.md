---
phase: 13-state-corroboration
plan: "04"
status: complete
requirements: [CORR-05]
beads: [CairnGo-51p]
---

# Phase 13 Plan 04 — Summary

Both gates learned the same rule, in the same commit, and one test proves it.

## What shipped

**`cairn-gate.py` and `cairn/capability/scripts/cairn-loop-gate.py`** now both
block a completed phase whose disk never reached `executed` — no `-SUMMARY.md`,
no `-VERIFICATION.md`, nothing built behind a ticked checkbox. The offending
entry reports `status: "no-artifacts"` and leads with the phase number rather
than an issue id, because there is no issue: the defect is that the work was
never done, not that a ticket stayed open.

The two scripts are deliberately duplicated rather than sharing an import. The
capability bundle has to be loadable by GSD on its own, and that self-containment
is a constraint, not an oversight to be tidied away.

**`disk_reached_executed()` requires SUMMARY or VERIFICATION**, never a bare
`PLAN.md`. An earlier draft of this plan would have accepted a lone plan file as
evidence of work — which is precisely the "planned but never built" state the rule
exists to catch. The planner found and corrected that before execution.

## The thing worth knowing

**One test runs both scripts against one repo state and asserts both block:**
`"cross-script lockstep (D-10): cairn-gate.sh and cairn-loop-gate.sh ship-gate
both block on the same no-artifacts repo state"` in `tests/capability.bats`.

Two separate tests, each exercising its own script in isolation, would both keep
passing on the day someone edits one twin and forgets the other — and the project
would ship a gate that passes while its twin blocks, which is worse than having no
check at all, because both signals look authoritative. This repo has already
shipped a gate whose predicate silently no-opped because the script it referenced
was missing. That is the failure this test exists to make impossible to repeat
quietly.
