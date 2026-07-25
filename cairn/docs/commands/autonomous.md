# /cairn:autonomous

> Run every remaining phase hands-off — the full cairn loop per phase (map → plan → claim → execute → close → verify), doctor between phases, ship gate at the end

## Usage

```
/cairn:autonomous [start-phase]
```

Without arguments, starts at the first phase not marked complete in
`ROADMAP.md`. With a phase number, starts there (earlier pending phases are
left untouched — useful after a manual fix mid-milestone).

## What it does

The beads-aware counterpart of `/gsd:autonomous`. Where GSD's autonomous mode
walks discuss → plan → execute per phase, this command walks the **cairn**
loop, so every phase also passes through the full bd bookkeeping — claim →
`in_progress` → close → map refresh — with consistency checks between phases.

1. **Pre-flight.** Runs `cairn-doctor.sh`; a ✗ failure (exit 7) stops the run
   before it starts, and so does a not-applicable note (one side missing —
   routed to `/cairn:migrate`). Confirms bd is available (doctor exit 5 stops
   — without bd this degenerates to plain `/gsd:autonomous`, which it offers
   instead).
   Resolves pending phases and the active milestone, announces the ordered
   plan of attack, then proceeds without further questions.
2. **Per phase, in order:** `/cairn:plan N` (non-interactive; assumptions
   recorded as Claude's Discretion) → `/cairn:work N` (claim before starting,
   close on verified completion, done-check via the `m-<milestone>,phase-N`
   pair label, map refresh) → `/cairn:verify N` (GSD verification
   cross-checked against bd, mismatches reconciled) → phase checkpoint
   (`cairn-doctor.sh` + `bd list -l m-<milestone>,phase-N --all` showing no
   issue with a status other than `closed`, the same semantics the ship gate
   enforces) → next phase.
3. **After the last phase:** runs `cairn-gate.sh`; exit 6 stops with the
   offending ids. Green ends with a milestone summary and hands off to
   `/cairn:ship` — it never pushes on its own.

## Stop rules

Autonomous is not blind. The run stops immediately — reporting phase, step
and offending ids, and leaving claims/closes consistent with reality — on any
of: doctor ✗ failure at a checkpoint; an unrecoverable plan execution
failure; a verification gap reconciliation cannot close; bd unavailable
mid-run (exit 5); ship gate blocked (exit 6). After fixing the reported
problem, re-running `/cairn:autonomous` resumes: phases already complete in
ROADMAP.md are skipped.

## Flags & arguments

| Argument | Meaning |
|---|---|
| `start-phase` (optional) | Phase number to start from; defaults to the first pending phase |

## Examples

```
/cairn:autonomous        # run all remaining phases of the active milestone
/cairn:autonomous 3      # resume from phase 3 after a manual fix
```

## Files touched

- `.planning/phases/<N>-*/` — plans, CONTEXT, SUMMARY, `NN-BEADS-MAP.md`
  (regenerated per phase), via the delegated commands
- `.beads/` — claims, status transitions and closes for every phase issue
- `ROADMAP.md` / `STATE.md` — phase completion state, via GSD

## Related

- [/cairn:plan](./plan.md) · [/cairn:work](./work.md) ·
  [/cairn:verify](./verify.md) — the loop it drives, phase by phase
- [/cairn:ship](./ship.md) — the suggested hand-off once the gate is green
- [/cairn:doctor](./doctor.md) — run between phases; its report routes fixes
  after a stop
- [/cairn:gsd](./gsd.md) — `/cairn:gsd autonomous` reaches GSD's own
  autonomous mode without the cairn orchestration (doctor checkpoints, phase
  gates, map refresh); claim/close still happen via the capability's hooks
  when installed
