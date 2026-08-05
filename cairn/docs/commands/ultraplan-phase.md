# /cairn:ultraplan-phase

> Offload planning to the ultraplan cloud and import it back — GSD
> ultraplan-phase, and the imported PLAN gets the beads frontmatter it arrives
> without

## Usage

```text
/cairn:ultraplan-phase [phase-number]
```

The bare phase number drives labels and the map.

## Why this wrapper exists

The sharpest gap on the whole wrap list: **the PLAN.md comes back from the
cloud without `beads:` frontmatter.** It was written somewhere that has never
heard of this repository's issue tracker. Nothing downstream notices —
[`/cairn:work`](./work.md) simply finds no ids to claim and executes the phase
untracked.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight ultraplan-phase`. Exit `6` or `5`
   stops.
2. **Records the phase's ids before the round trip** — the imported plan will
   not mention them, so the mapping has to exist on this side.
3. **Claims** each of them.
4. **Runs `/gsd:ultraplan-phase`** and lets it import.
5. **Fills `beads:` on every imported `PLAN.md`** — the step this wrapper exists
   for. A plan that cannot be matched is reported, not left with an empty key.
6. **A plan the cloud invented with no issue behind it gets one**, labelled
   `m-<milestone>,phase-<N>` (unpadded) with the `metadata.gsd` stamp.
7. **Anything the imported plan dropped is released and left open** — never
   closed because a remote planner stopped mentioning it.
8. **Refreshes and checks the map.**

Next: [/cairn:work N](./work.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- `.planning/phases/*/NN-MM-PLAN.md` — imported, then given `beads:`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated
- bd issues — claimed, created, closed or released

## See also

- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
