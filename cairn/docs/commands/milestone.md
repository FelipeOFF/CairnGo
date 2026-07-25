# /cairn:milestone

> Milestone lifecycle — new (roadmap + stamped issues + maps) or complete (gate → reconcile → archive → compact)

## Usage

```
/cairn:milestone <new|complete>
```

With neither `new` nor `complete`, the command asks which mode to run.

## What it does

### `new` — start the next milestone

1. Runs `/gsd:new-milestone` — GSD updates PROJECT.md, REQUIREMENTS.md, and
   ROADMAP.md. Phase numbering is **continuous across milestones** (v1.0
   ended at phase 5 → v1.1 starts at phase 6); it never restarts at 1.
2. Creates one stamped issue per new requirement, **dedup check first**: an
   issue with the same `(gsd.req, gsd.milestone)` already exists (e.g.
   carried over during `complete`) → it is updated, never duplicated.
   Otherwise:
   ```bash
   bd create "CAT-NN: <requirement title>" \
     -l m-<new-milestone>,phase-<N> \
     --metadata '{"gsd": {"req": "CAT-NN", "phase": N, "milestone": "vX.Y"}}'
   ```
   Roadmap-implied ordering is captured with `bd dep add`.
3. Generates each new phase's beads map:
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>` (once per phase).
4. Suggests `/cairn:doctor` to confirm the wiring, then `/cairn:plan <N>`.

### `complete` — close out the current milestone

1. **Deterministic gate first:**
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-gate.sh"` — every completed
   phase must be clean. Any non-closed issue blocks (exit `6` lists the ids);
   exit `5` means bd is unavailable — check by hand as `/cairn:ship`
   describes. The command **stops** until the gate passes.
2. Reconciles stragglers **with the user** — per non-closed issue:
   - close: `bd close <id> --reason="<why it's done or dropped>"`, or
   - carry over: swap the label pair
     (`bd update <id> --remove-label m-<old>,phase-<N> --add-label m-<new>`)
     and update the stamp by the **read-modify-write rule** (see Gotchas).
3. Runs `/gsd:complete-milestone` — archives ROADMAP/REQUIREMENTS and the
   phase dirs to `.planning/milestones/v<X.Y>-phases/`. Generated
   `NN-BEADS-MAP.md` files are archived **with** their phase dirs — correct
   history; they are not cleaned or regenerated.
4. Offers semantic compaction of aged closed issues:
   `bd admin compact --analyze --json` lists candidates (~30 days closed).
   Only on explicit per-issue confirmation:
   `bd admin compact --apply --id <id> --summary -`.
5. Suggests `/cairn:milestone new` to start the next cycle.

## Flags & arguments

| Argument | Effect |
| --- | --- |
| `<new\|complete>` | Positional mode selector; omitted → the command asks |

## Exit codes

The gate script (`cairn-gate.sh`, used by `complete`):

| Code | Meaning |
| --- | --- |
| `0` | Clean — all issues in completed phases closed |
| `2` | Usage error |
| `5` | `bd` unavailable — verify manually |
| `6` | Gate failed — non-closed issues listed; **stop** until resolved |

## Examples

```
/cairn:milestone new        # after complete: seed v1.1 roadmap + issues + maps
/cairn:milestone complete   # gate, reconcile, archive, optionally compact
```

## Files touched

- **Reads:** `.planning/ROADMAP.md`, `.planning/STATE.md`, beads state
- **Writes:** `.planning/` (PROJECT/REQUIREMENTS/ROADMAP via GSD; archive
  under `.planning/milestones/`), phase `NN-BEADS-MAP.md` files (generated),
  beads issues (`bd create/update/close/dep add`, `bd admin compact`)

## Gotchas

- **Read-modify-write on the stamp.** `bd update --metadata` replaces the
  whole `gsd` object. Read it from `bd show <id> --json`, change only
  `milestone`, and write the complete object back — never write a partial
  stamp.
- **Transient orphan warns.** A carried-over issue has no `phase-*` label
  until `new` places it in the next roadmap, so `/cairn:doctor` reports it as
  an orphan warn in between. Expected; it clears on the next roadmap.
- **Compaction is permanent.** There is no undo for
  `bd admin compact --apply`.
- **Two different "compact"s.** Top-level `bd compact` is Dolt commit
  squashing — a different tool from `bd admin compact` (semantic issue
  compaction). Don't confuse them.

## Related

- [/cairn:ship](ship.md) — the same gate guards every push
- [/cairn:doctor](doctor.md) — confirm wiring after `new`; explains orphan warns
- [/cairn:plan](plan.md) — the next step after `new`
- [/cairn:new](new.md) — first-ever milestone of a fresh project
