# /cairn:autonomous

> Run every remaining phase hands-off — the full cairn loop per phase (map → plan → claim → execute → close → verify), doctor between phases, ship gate at the end

## Usage

```
/cairn:autonomous [start-phase] [--sequential] [--max N]
```

Without arguments, starts at the first phase not marked complete in
`ROADMAP.md`. With a phase number, starts there (earlier pending phases are
left untouched — useful after a manual fix mid-milestone).

**Parallel execution is the default.** Phases the status model reports as
independent run at the same time, one git worktree each, announced before
anything is created. `--sequential` is the named way out.

## What it does

The beads-aware counterpart of `/gsd:autonomous`. Where GSD's autonomous mode
walks discuss → plan → execute per phase, this command walks the **cairn**
loop, so every phase also passes through the full bd bookkeeping — claim →
`in_progress` → close → map refresh — with consistency checks between phases.

1. **Pre-flight.** Runs `cairn-doctor.sh`; a ✗ failure (exit 7) stops the run
   before it starts, and so does a not-applicable note (one side missing —
   routed to `/cairn:migrate`). Confirms bd is available (doctor exit 5 stops
   — without bd this degenerates to plain `/gsd:autonomous`, which it offers
   instead). Resolves pending phases and the active milestone from
   `cairn-status.sh --json`, and the lot that runs at once from
   `cairn-parallel.sh batch --json` — which consumes the status model's
   independence calculation rather than repeating it.
2. **Announces the batch before creating anything:** how many phases run
   concurrently and why each one, the branch and worktree each will get, what
   stays out and why, the `--max` ceiling in force and how to change it, and
   the honesty line when the roadmap declares no dependencies at all. This is
   the interruption point — the next step creates worktrees and spawns agents
   that write code.
3. **The loop, four moments.** *Plan* every phase of the batch sequentially in
   the main checkout (`/cairn:plan N` — GSD's plan-phase writes `ROADMAP.md`,
   which a phase worktree may not do). *Prepare* one named worktree and one
   lease per phase (`cairn-parallel.sh prepare N`; a phase already owned by a
   live holder leaves the batch and the run continues). *Execute* one subagent
   per phase concurrently — each handed its worktree path and branch from
   `prepare`'s own output, told to run `/cairn:work N` and `/cairn:verify N`
   there, forbidden to touch the three planning files, told to commit on
   its branch without merging or pushing, and told which
   `response_language` to write its user-facing output in — also copied from
   `prepare`'s output rather than remembered. *Reconcile, merge, mark, clean up*
   in the main checkout: `cairn-parallel.sh reconcile --json` first (exit 6
   stops; `planning_writes` is shown even at exit 0), then one plain
   `git merge --no-ff` per branch, then one `cairn-bookkeep.sh close <N>
   --apply` per merged phase, then `cairn-parallel.sh cleanup --apply`.
4. **Per phase, once merged:** the checkpoint runs in the main checkout —
   `cairn-doctor.sh` plus `bd list -l m-<milestone>,phase-N --all` showing no
   issue with a status other than `closed`, the same semantics the ship gate
   enforces.
5. **After the last phase:** runs `cairn-gate.sh`; exit 6 stops with the
   offending ids. Green ends with a milestone summary and hands off to
   `/cairn:ship` — it never pushes on its own.

Under `--sequential`, moments 2 and 3 do not run: one phase at a time in the
main checkout, plan → work → verify → checkpoint, and nothing to reconcile.

## Stop rules

Autonomous is not blind. The run stops immediately — reporting phase, step
and offending ids, and leaving claims/closes consistent with reality — on any
of: doctor ✗ failure at a checkpoint; reconciliation exiting 6 (findings, or
conflicts it could not rule out) before any branch is merged; a git conflict
during a merge; an unrecoverable plan execution failure in a sequential run; a
verification gap reconciliation cannot close; bd unavailable mid-run (exit 5);
ship gate blocked (exit 6). After fixing the reported problem, re-running
`/cairn:autonomous` resumes: phases already complete in ROADMAP.md are skipped
and `cleanup` reports what the stopped run left behind.

Explicitly **not** stop rules, because in a parallel run they are ordinary:
`prepare` refusing a phase whose lease a live holder already owns (exit 3), and
one parallel phase failing while the others keep running. Both are reported and
the run goes on.

No merge strategy that resolves a conflict by automatically preferring one side
is permitted anywhere in this command, including in examples — a flag that
picks a winner in silence destroys one side of a real disagreement and reports
success.

## Flags & arguments

| Argument | Meaning |
|---|---|
| `start-phase` (optional) | Phase number to start from; defaults to the first pending phase |
| `--sequential` | Turn off the parallel default: one phase at a time in the main checkout, no worktrees, no subagents |
| `--max N` | Ceiling on how many phases run concurrently (default 3); passed through to `cairn-parallel.sh batch` |
| `--interactive` | Put genuine design decisions to the user instead of recording them as Claude's Discretion (adds `/gsd:discuss-phase` at each phase's turn) |

## Examples

```
/cairn:autonomous              # run all remaining phases, parallel by default
/cairn:autonomous 3            # resume from phase 3 after a manual fix
/cairn:autonomous --sequential # one phase at a time, in the main checkout
/cairn:autonomous --max 2      # parallel, but never more than two at once
```

## Files touched

- `.planning/phases/<N>-*/` — plans, CONTEXT, SUMMARY, `NN-BEADS-MAP.md`
  (regenerated per phase), via the delegated commands
- `.beads/` — claims, status transitions and closes for every phase issue,
  plus the per-phase lease taken by `cairn-parallel.sh prepare`
- `ROADMAP.md` / `STATE.md` / `REQUIREMENTS.md` — phase completion state, via
  `cairn-bookkeep.sh close <N> --apply` (see `docs/commands/bookkeep.md`), one
  call per merged phase; in a parallel run these are written **only** in the
  main checkout, after the merges
- `../<repo>-phase-<N>/` — one sibling worktree per parallel phase, on branch
  `phase/<N>-<slug>`; created by `prepare` and removed by `cleanup --apply`
  once clean and wholly merged

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
