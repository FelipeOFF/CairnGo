# /cairn:plan-review-convergence

> Replan until cross-AI review concerns are resolved — GSD
> plan-review-convergence, with the beads linkage re-resolved after every
> rewrite

## Usage

```text
/cairn:plan-review-convergence <phase> [--codex] [--gemini] [--claude] [--opencode] [--ollama] [--lm-studio] [--llama-cpp] [--agy] [--text] [--ws <name>] [--all] [--max-cycles N]
```

The bare phase number drives labels and the map; every reviewer flag goes only
to `/gsd:plan-review-convergence`.

## Why this wrapper exists

It **rewrites PLAN.md**, possibly several times. Every rewrite can split a
plan, merge two, or renumber them — and the `beads:` frontmatter written before
the first cycle is stale after it. The linkage is **re-resolved after
convergence**, never assumed to have survived.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight plan-review-convergence`. Exit `6`
   or `5` stops.
2. **Records the linkage before the first cycle** — the only record of the
   pre-convergence mapping.
3. **Claims** every id in that record.
4. **Runs `/gsd:plan-review-convergence`.**
5. **Re-resolves `beads:` on every plan that now exists** — a fresh resolution,
   not a diff. A split plan inherits the ids matching its remaining scope; a
   merged one carries both. An id that lands nowhere is **reported**, never
   quietly dropped: converging a review does not finish work.
6. **A concern no issue covers becomes one**, labelled `m-<milestone>,phase-<N>`
   (unpadded) with the `metadata.gsd` stamp.
7. **Closes only what convergence settled**; releases the rest.
8. **Refreshes and checks the map.**

Next: [/cairn:work N](./work.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- `.planning/phases/*/NN-MM-PLAN.md` — rewritten, then re-linked
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated
- bd issues — claimed, created, closed or released

## See also

- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
