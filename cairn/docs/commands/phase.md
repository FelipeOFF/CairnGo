# /cairn:phase

> CRUD for phases in ROADMAP.md — GSD phase, plus the relabel that keeps its
> issues from being orphaned

## Usage

```text
/cairn:phase [--insert | --remove | --edit] <phase-name-or-number>
```

Arguments pass straight through to `/gsd:phase`. The mode flag decides which
workflow runs there: none adds a phase at the end of the current milestone,
`--insert` inserts a decimal phase between two existing ones, `--remove`
removes a future phase and renumbers what follows, `--edit` edits a phase in
place.

## Why this wrapper exists

This is the strongest case on the wrap list, and the reason is mechanical.
`--remove` and `--insert` **renumber phases**, and every bd issue carrying the
old `phase-<N>` label is orphaned the moment the ROADMAP moves under it.
`/gsd:phase` knows nothing about those labels — it edits a markdown file.
Nothing else in cairn would notice: the maps regenerate from labels, the board
groups by labels, the ship gate counts by labels.

## What it does

1. **Preflight.** Refuses to start when the delegate is not installed:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight phase
   ```
   Exit `6` (looked, not there) or `5` (no GSD command surface found at all)
   stops the command and the script's message is printed verbatim — it names
   what is missing, every path searched, and the fix. Running anyway would be
   the silent exit 0 this wrapper exists to prevent.
2. **Records the before-state.** For the target phase and, on
   `--remove`/`--insert`, every phase numbered after it:
   `bd list -l phase-<N> --all --limit 0 --json`. This has to happen *before*
   delegating: afterwards the ROADMAP no longer says which issues belonged to
   which number.
3. **Claims the work.** `bd update <id> --claim` — atomic, assigns and sets
   `in_progress` in one call, idempotent when the issue is already yours.
4. **Runs `/gsd:phase $ARGUMENTS`.**
5. **Moves the labels** — the step that only exists here:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-relabel.sh" renumber \
     --from <old> --to <new> --milestone <active> --dry-run
   ```
   Dry run first, then for real. `cairn-relabel` deep-merges
   `metadata.gsd.phase` instead of clobbering it, which a plain
   `bd update --metadata` would not (bd replaces each provided key's value
   wholesale). Labels use the **unpadded** number — `phase-3`, never
   `phase-03`.
6. **Creates issues for a phase that was added**, with the label pair
   `m-<milestone>,phase-<N>` and the `{"gsd": {...}}` metadata stamp. A phase
   that was **removed** leaves its issues behind: they are closed with a
   reason, or released and left open when the work is merely deferred. No
   issue is ever deleted to tidy up a renumber.
7. **Refreshes the generated map** of every phase whose number moved
   (`cairn-map.sh <N>`).
8. **Proves it.** `bd list -l phase-<old>` is empty for every number that
   moved, and the new number holds exactly the ids recorded in step 2.
   Anything that did not arrive is reported.

Next: [/cairn:status](./status.md), then [/cairn:plan N](./plan.md).

## Exit codes

The command is prose; the deterministic steps carry the codes.

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` | `/gsd:phase` is installed |
| | `5` | no GSD command surface found — cannot tell |
| | `6` | looked, and `/gsd:phase` is not there |
| `cairn-relabel renumber` | `0` | labels moved |
| | `1` | partial failure applying changes |
| | `2` | usage, or a **refusal** — a target already carries the destination label |
| | `5` | `bd` unavailable |
| `cairn-map` | `5` | `bd` unavailable — degrade, do not block |

A `cairn-relabel` exit `2` refusal is not a crash: resolve the ambiguous
double-label by hand. Never reach for `--force` to get past a refusal you have
not read.

## Files it touches

- `.planning/ROADMAP.md` — via `/gsd:phase`
- bd issues — labels and `metadata.gsd.phase`, via `cairn-relabel`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated for every moved phase

## See also

- [Command reference](../commands.md) — every `/cairn:` command
- [gsd-core commands](../gsd-core-commands.md) — why this command earns a
  wrapper and 39 others do not
