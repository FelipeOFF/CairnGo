# /cairn:spec-phase

> Clarify WHAT a phase delivers, with ambiguity scoring — GSD spec-phase,
> and every requirement the SPEC names gets a stamped issue

## Usage

```text
/cairn:spec-phase <phase> [--auto] [--text]
```

The bare phase number drives labels and the map; `--auto` and `--text` go only
to `/gsd:spec-phase`.

## Why this wrapper exists

A SPEC gives the phase a **requirements surface**, and in cairn a requirement
without an issue is untracked work. The SPEC's requirements arrive as bd issues
carrying the label pair and the stamp, in the same run that produced them.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight spec-phase`. Exit `6` or `5` stops
   the command and prints the script's message verbatim.
2. **Claims** the phase's existing ids before rewriting the shape of them.
3. **Runs `/gsd:spec-phase`.**
4. **Turns every new requirement into an issue**, labelled
   `m-<milestone>,phase-<N>` (unpadded — `phase-3`, never `phase-03`) with
   `metadata.gsd.req` set. That stamp is what `cairn-map` keys the requirement
   table on; without it the issue lands in the map's gap list instead of a row.
5. **A requirement the SPEC drops** is closed with a reason, or released and
   left open when merely deferred. Never deleted.
6. **Refreshes and checks the map** — its requirement-gap list is the proof
   that step 4 was complete, rather than an assumption.

Next: [/cairn:discuss-phase N](./discuss-phase.md), then [/cairn:plan N](./plan.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- `.planning/phases/*/NN-SPEC.md` — via `/gsd:spec-phase`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated
- bd issues — claimed, created, closed or released

## See also

- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
