# /cairn:discuss-phase

> Gather phase context before planning — GSD discuss-phase, with the phase's
> beads claimed and the CONTEXT reconciled against them

## Usage

```text
/cairn:discuss-phase <phase> [--all] [--auto] [--chain] [--batch] [--analyze] [--text] [--power] [--assumptions]
```

The bare phase number drives labels and the map. Every flag goes only to
`/gsd:discuss-phase`.

## Why this wrapper exists

The CONTEXT.md this produces is what [`/cairn:plan`](./plan.md) treats as
**authoritative on divergence**. If the CONTEXT and the phase's bd issues
disagree about what the phase is, that disagreement has to surface here, while
someone is still thinking about it — not at planning time, as a surprise.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight discuss-phase`. Exit `6` or `5`
   stops the command and prints the script's message verbatim.
2. **Reads the phase's beads first** (`cairn-map.sh <N>`), so the discussion
   starts from tracked work rather than a blank page. Exit `5` degrades to
   reading the existing map as-is.
3. **Claims** every id on the map — `bd update <id> --claim`.
4. **Runs `/gsd:discuss-phase`** with the full arguments.
5. **Reconciles, naming every divergence.** CONTEXT wins; the issue is updated
   with a dated note, flagged ⚠ outside the map's generated markers. A
   requirement the CONTEXT introduces with no issue becomes one, with the label
   pair `m-<milestone>,phase-<N>` (unpadded — `phase-3`, never `phase-03`) and
   the `{"gsd": {...}}` stamp.
6. **Closes what was settled**; releases and leaves open what was deferred
   (`bd update <id> --assignee "" --status open`) so it stays visible in
   [`/cairn:status`](./status.md).
7. **Refreshes and checks the map** (`--check` exits `3` + diff when stale).

Next: [/cairn:plan N](./plan.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- `.planning/phases/*/NN-CONTEXT.md` — via `/gsd:discuss-phase`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated
- bd issues — claimed, updated, created, closed or released

## See also

- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
