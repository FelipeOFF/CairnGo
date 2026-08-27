# /cairn:implement

> Implement a phase as one pull request — the beads' frontier run in parallel, one worktree per bead, merged as they land, reviewed, and marked ready

## Usage

```text
/cairn:implement <phase-number> [--max N] [--no-explore]
```

## The idea

A phase whose beads form a task graph has a **frontier** — the beads nothing
blocks — that moves every time one closes. This verb runs that frontier
concurrently: one implementer subagent per bead, each in its own worktree
branched from the PR branch, a merger that lands each result and runs its
suite, and more implementers as the frontier opens. `/cairn:work` and
`/cairn:autonomous` are untouched. The spec is the phase carrier, the tickets
are the beads, and subagents get **pointers** (ids, SHAs), not prose.

## What it does

1. Pre-flight: doctor, the records, the scope (`ship.pr_scope`) and the base
   branch — with `phase` the base is the branch you stand on (the milestone
   branch) and a control branch is refused; with `milestone` the base is the
   control branch. Phase lease; PR branch `phase/<N>-<slug>`.
2. Optional exploration subagent → `cairn-record.sh research`.
3. **Draft PR first** (`gh pr create --draft --base <base>`), Summary /
   Changes / Test plan with the bead ids — no AI mention, no session trailer.
4. The frontier loop: `bd ready -l m-<milestone>,phase-<N>` →
   `cairn-parallel.sh prepare-bead <id> --base <pr-branch>` → implementers in
   the background (claim, implement, test, commit; never merge or push) →
   a merger per result (`reconcile --beads --base`, `git merge --no-ff`,
   conflicts read, never `-X ours/theirs`, the bead's suite; **red = stop**)
   → `bd close`, lease release, push, `bd gate create --type=gh:run` on the
   next bead + `bd gate discover` → re-read the frontier.
5. Review (`code-review` skill, else `gsd-code-reviewer`), one implementer
   fixes, verification recorded, carrier closed, `gh pr ready`;
   `ship.auto_merge = true` merges when the last gate is green, `false`
   (default) stops there.
6. `cairn-parallel.sh cleanup --apply`; report.

## Scripts it leans on

| Script | Verb |
|---|---|
| `cairn-parallel.sh` | `prepare-bead <id> --base <ref>`, `reconcile --beads --base <ref>`, `cleanup --apply` |
| `cairn-lease.sh` | `acquire N`, `acquire bead:<id>` (through prepare-bead), `release` |
| `cairn-record.sh` | `research`, `verification` |
| `cairn-config.sh` | `ship.pr_scope`, `ship.auto_merge`, `autonomous.max_parallel` |
| `bd gate` | `create --type=gh:run --blocks <bead>`, `discover`, `check` |

## Related

- [`/cairn:plan`](plan.md) — the records this verb implements from
- [`/cairn:work`](work.md) — one wave at a time, in the main checkout
- [`/cairn:autonomous`](autonomous.md) — every phase, one worktree per phase
- [`/cairn:ship`](ship.md) — the merge, when it stays human
- [`/cairn:config`](config.md) — `ship.pr_scope`, `ship.auto_merge`
