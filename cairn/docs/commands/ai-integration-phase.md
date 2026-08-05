# /cairn:ai-integration-phase

> Generate the AI design contract (AI-SPEC.md) for a phase that builds an AI
> system — GSD ai-integration-phase, with its requirements tracked

## Usage

```text
/cairn:ai-integration-phase [phase number]
```

The bare phase number drives labels and the map.

## Why this wrapper exists

An AI-SPEC carries **evaluation criteria**, not just features — and an eval
nobody tracked is an eval nobody runs. Every requirement the contract names
arrives as a stamped issue in the same run.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight ai-integration-phase`. Exit `6` or
   `5` stops.
2. **Claims** the phase's ids.
3. **Runs `/gsd:ai-integration-phase`.**
4. **Every requirement becomes an issue** — including the evaluation criteria,
   which are the ones most easily lost — labelled `m-<milestone>,phase-<N>`
   (unpadded) with the `metadata.gsd` stamp.
5. **Closes what the contract settled**; releases and leaves open what it
   deferred.
6. **Refreshes and checks the map.**

Next: [/cairn:plan N](./plan.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- `.planning/phases/*/NN-AI-SPEC.md` — via `/gsd:ai-integration-phase`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated
- bd issues — claimed, created, closed or released

## See also

- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
