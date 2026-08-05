# /cairn:cleanup

> Archive phase directories from completed milestones — GSD cleanup, refusing
> to archive over open issues or a missing beads map

## Usage

```text
/cairn:cleanup [milestone]
```

Without an argument the completed milestone is resolved from ROADMAP.md's
headers, or STATE.md. Everything is scoped by `m-<milestone>`.

## Why this wrapper exists

This is the only one of the thirteen whose carelessness **destroys record**.
The `NN-BEADS-MAP.md` files live inside the directories being archived — they
are the phase↔issue record. Archiving a phase whose issues are still open, or
whose map is missing, buries the only written link between the work and the
tracker.

So the checks happen **before** delegating, and what they find is named rather
than archived over.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight cleanup`. Exit `6` or `5` stops the
   command and prints the script's message verbatim.
2. **Resolves the milestone.**
3. **Enumerates what would be archived and checks each phase, before running
   anything:**
   - `bd list -l m-<milestone>,phase-<N> --status open --json`. **Any open issue
     stops the command**, named with id and title. The fix is
     [`/cairn:milestone complete`](./milestone.md), whose gate exists for
     exactly this, or closing the work.
   - **A phase directory with no `NN-BEADS-MAP.md` gets one regenerated first**
     (`cairn-map.sh <N>`), so what is archived carries its record.
4. **Claims** the milestone's remaining bookkeeping, if any is assignable.
5. **Runs `/gsd:cleanup`.**
6. **Verifies the archive kept the record** — every archived directory still
   contains its map. Anything that does not is reported with its path, not as a
   count.
7. **Closes the cleanup's own bookkeeping issue.** Issues belonging to archived
   phases are not touched here: they were already closed in step 3, or the
   command stopped.

Next: [/cairn:status](./status.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `5` | `bd` unavailable |

**This is the one place in cairn where `cairn-map` exit `5` blocks.** Everywhere
else an unavailable `bd` degrades with a warning. Here it means the map cannot
be rebuilt, and archiving a phase whose record could not be written is a
permanent loss — so the command stops instead.

## Files it touches

- `.planning/phases/*/` — archived, via `/gsd:cleanup`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated when missing, before
  archiving
- bd issues — read (the gate), and the cleanup's own issue closed

## See also

- [`/cairn:milestone`](./milestone.md) — `complete`, the gate this command
  points at rather than re-implementing
- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
