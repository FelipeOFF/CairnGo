# /cairn:progress

> Roadmap-level project progress (GSD)

## Usage

```
/cairn:progress
```

No arguments.

## What it does

1. Runs `/gsd:progress` — the GSD situational command that reads
   `.planning/ROADMAP.md` and `.planning/STATE.md`.
2. Summarizes roadmap completion: which phases are done, which is active,
   and how far the current milestone has advanced.
3. Points at `/cairn:status` for the operational view — the one that also
   folds in beads ready/blocked/in-progress work.

This is a pure GSD delegation with no cairn orchestration on top: no beads
queries, no labels, no scripts.

## Flags & arguments

None.

## Examples

```
/cairn:progress
```

Typical summary:

```
Milestone v1.0 — phase 3 of 5 active
✓ Phase 1: Scaffold        ✓ Phase 2: Core engine
▸ Phase 3: Status board (in progress)
  Phase 4: Sync            Phase 5: Docs
Next GSD step: execute phase 3
```

## Files touched

- **Reads:** `.planning/ROADMAP.md`, `.planning/STATE.md` (via `/gsd:progress`)
- **Writes:** nothing — read-only

## Gotchas

- **GSD only.** This view never consults beads — an issue can be `in_progress`
  in bd and invisible here. For the combined picture (bd ready/blocked lanes
  plus roadmap position plus one next action), use `/cairn:status`.

## Related

- [/cairn:status](status.md) — combined bd + GSD board with one next action
- [/cairn:issues](issues.md) — the beads side of the picture, per phase
