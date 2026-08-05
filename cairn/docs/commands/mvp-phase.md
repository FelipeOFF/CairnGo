# /cairn:mvp-phase

> Plan a phase as a vertical MVP slice — GSD mvp-phase, with the PLAN's beads
> frontmatter filled and the map reconciled

## Usage

```text
/cairn:mvp-phase <phase-number>
```

The bare phase number drives labels and the map.

## Why this wrapper exists

It writes a `PLAN.md`, and in cairn a PLAN without `beads:` frontmatter is a
plan nothing can trace. The SPIDR split also produces slices that do not map
one-to-one onto the phase's existing issues — that divergence is named here
rather than found at execution time.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight mvp-phase`. Exit `6` or `5` stops.
2. **Regenerates and reads the map first**, so slicing starts from tracked work.
3. **Claims** every id on the map.
4. **Runs `/gsd:mvp-phase`.**
5. **Fills each generated `PLAN.md`'s `beads:` frontmatter** with the ids that
   plan advances — the link that lets [`/cairn:work`](./work.md) claim and close
   by plan.
6. **A slice with no issue gets one**, labelled `m-<milestone>,phase-<N>`
   (unpadded) with the `metadata.gsd` stamp.
7. **Work the MVP defers is released, not closed** — a deferred slice stays in
   [`/cairn:status`](./status.md)'s ready lane.
8. **Refreshes and checks the map.**

Next: [/cairn:work N](./work.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- `.planning/phases/*/NN-MM-PLAN.md` — written, then given `beads:`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated
- bd issues — claimed, created, closed or released

## See also

- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
