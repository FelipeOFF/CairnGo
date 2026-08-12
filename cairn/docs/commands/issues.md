# /cairn:issues

> List beads issues, optionally scoped to a phase

## Usage

```
/cairn:issues [phase-number]
```

## What it does

1. **With a phase number** — lists issues carrying that phase's label pair:
   ```bash
   bd list -l m-<milestone>,phase-<N>
   ```
   The milestone comes from ROADMAP.md's current milestone header.
2. **Legacy fallback** — repos whose issues carry no `m-*` labels fall back
   to the plain phase label:
   ```bash
   bd list -l phase-<N>
   ```
3. **Without arguments** — lists the whole project: `bd list`.
4. Groups the output by status (`open` / `in_progress` / `closed`) and notes
   any issues blocked by dependencies.

Read-only: no issue is created, claimed, or modified.

## Flags & arguments

| Argument | Effect |
| --- | --- |
| `[phase-number]` | Optional positional — scope the listing to one phase |

## Examples

All issues in phase 3 of the active milestone:

```
/cairn:issues 3
```

```
open (2):        app-12  Add auth to sync endpoint
                 app-13  Fix flaky gate test
in_progress (1): app-9   Status board renderer  [◆ felipe]
closed (4):      app-5, app-6, app-7, app-8
blocked:         app-14  (waiting on app-12)
```

Whole project:

```
/cairn:issues
```

## Files touched

- **Reads:** beads state via `bd list`, `.planning/ROADMAP.md` (milestone
  header)
- **Writes:** nothing — read-only

## Gotchas

- **The label pair is an AND filter.** `bd list -l a,b` matches issues
  carrying *both* labels. On legacy repos without `m-*` labels, the
  `phase-<N>` fallback alone can mix same-numbered phases from *different*
  milestones — phase numbering is continuous across milestones precisely to
  limit this, but old repos may predate that convention.
- Phase labels are unpadded: `phase-3`, never `phase-03`.

## Related

- [/cairn:status](status.md) — the curated board (ready/doing/blocked) instead
  of a flat list
- [/cairn:work](work.md) — execute the phase these issues belong to
- [/cairn:verify](verify.md) — cross-check issue state against GSD verification
