# /cairn:quick

> Tracked side-quest — stamped quick issue with discovered-from provenance, then GSD quick

## Usage

```
/cairn:quick <task description> [--full] [--discuss] [--research] [--validate]
```

The description becomes both the bd issue title and the `/gsd:quick` task.
Flags are stripped from the description first — the clean title goes to
`bd create`, the flags are forwarded to `/gsd:quick`
(`--discuss --research --validate` ≡ `--full`). The `/gsd:quick` subcommands
`list`, `status <slug>`, and `resume <slug>` route straight through — no
issue is created or claimed for them.

## What it does

Side work stays tracked — never a "quick thing" off the books.

1. **Finds the active issue:**
   `bd list --status in_progress --assignee <actor>`, where the actor
   resolves the way bd does: `$BEADS_ACTOR`, then git `user.name`, then
   `$USER`. Several hits → the one in the current plan's `beads:`
   frontmatter. None → fine; the provenance dep below is skipped.
2. **Creates the quick issue** — labeled `quick` + `m-<active milestone>`
   (milestone from ROADMAP.md's current header, or STATE.md), with **no
   `phase-*` label**: quick work is unphased.
   ```bash
   bd create "<clean description>" -t task -l m-<milestone>,quick \
     --metadata '{"gsd": {"milestone": "vX.Y"}}' \
     --deps discovered-from:<active-id>   # only when step 1 found one
   ```
   `--deps discovered-from:` records provenance **without blocking**. After
   the fact, the same edge is
   `bd dep add <quick-id> <active-id> -t discovered-from`.
3. **Claims it** (`bd update <quick-id> --claim`), then runs `/gsd:quick`
   with the description plus any stripped flags — GSD guarantees (atomic
   commits, state tracking) with optional agents skipped.
4. **On completion:** `bd close <quick-id> --reason="<1–2 sentence summary>"`.
   Abandoned or deferred → **release** it
   (`bd update <quick-id> --assignee "" --status open`) and leave it open: it
   stays visible in `/cairn:status`'s READY lane instead of evaporating.

## Flags & arguments

| Argument / flag | Effect |
| --- | --- |
| `<task description>` | Positional, required — issue title (flags stripped) and GSD quick description |
| `--full` | Forwarded to `/gsd:quick` — equivalent to `--discuss --research --validate` |
| `--discuss` | Forwarded to `/gsd:quick` (composable) |
| `--research` | Forwarded to `/gsd:quick` (composable) |
| `--validate` | Forwarded to `/gsd:quick` (composable) |
| `list` / `status <slug>` / `resume <slug>` | `/gsd:quick` subcommands — routed straight through, no bd issue created or claimed |

## Examples

```
/cairn:quick fix the flaky gate test on macOS
```

Resulting bookkeeping:

```
created app-17 "fix the flaky gate test on macOS"  [m-v1.0, quick]
  discovered-from: app-9 (Status board renderer)
claimed app-17 → running /gsd:quick …
closed app-17 --reason="Pinned bats to 1.11; gate test green on macOS."
```

## Files touched

- **Reads:** `.planning/ROADMAP.md` / `.planning/STATE.md` (milestone), the
  current plan's `beads:` frontmatter (disambiguation)
- **Writes:** one beads issue (`bd create/update/close`); whatever the quick
  task itself touches via `/gsd:quick` (its own atomic commits and
  `.planning/quick/` state)

## Gotchas

- **`bd q` can't stamp metadata** — always `bd create` here, or the issue
  lacks the `gsd` stamp and shows up in doctor findings.
- **Quick is unphased.** Never add a `phase-*` label to a quick issue; it
  belongs to the milestone, not to a phase.
- **`discovered-from` never blocks.** It is provenance, not ordering — the
  active issue does not wait on the quick one.
- **Never let the issue evaporate.** Every quick issue ends either closed
  with a reason or released back to open.

## Related

- [/cairn:work](work.md) — the phase loop this side-quest interrupts
- [/cairn:status](status.md) — released quick issues resurface in READY
- [/cairn:issues](issues.md) — quick issues appear unphased in the full list
