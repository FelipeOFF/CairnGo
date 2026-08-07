# /cairn:review-backlog

> Promote backlog items into the active milestone — GSD review-backlog, and
> every promoted item arrives as a stamped bd issue

## Usage

```text
/cairn:review-backlog [milestone]
```

Without an argument the active milestone is resolved from ROADMAP.md's current
milestone header, or STATE.md.

## Why this wrapper exists

Promoting an item **creates tracked work**. An item that moves into the
milestone as a line of markdown and nothing else is exactly the off-the-books
work cairn exists to prevent: it will not appear in
[`/cairn:status`](./status.md), will not gate a ship, and will not show up in
any phase's map.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight review-backlog`. Exit `6` or `5`
   stops the command and prints the script's message verbatim.
2. **Resolves the active milestone.**
3. **Records what is already tracked**
   (`bd list -l m-<milestone> --all --limit 0 --json`), so promotion does not
   duplicate it. An item whose issue exists is **claimed**, not re-created.
4. **Runs `/gsd:review-backlog`.**
5. **Every promoted item becomes an issue** — the step this wrapper exists for
   — labelled `m-<milestone>,phase-<N>` with the **unpadded** number
   (`phase-3`, never `phase-03`) and the `{"gsd": {...}}` stamp. An item
   promoted into the milestone but not yet into a phase carries the milestone
   label and **no** `phase-*` label, the same rule
   [`/cairn:quick`](./quick.md) follows for unphased work — never a guessed
   phase number.
6. **An item the review declined stays declined, on the record** — left in the
   backlog, no issue created, nothing deleted.
7. **Closes the review's own bookkeeping issue.** The promoted items stay
   **open**: they are the work, not the review of it.
8. **Refreshes and checks the map** of every phase that gained an item.

Next: [/cairn:plan N](./plan.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- the backlog and `.planning/ROADMAP.md` — via `/gsd:review-backlog`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated for phases that gained work
- bd issues — created for every promoted item, claimed where they existed

## See also

- [`/cairn:quick`](./quick.md) — the unphased-work label rule this follows
- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
