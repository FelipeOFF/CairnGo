---
description: Tracked side-quest — stamped quick issue with discovered-from provenance, then GSD quick
argument-hint: <task description> [--full] [--discuss] [--research] [--validate] | list | status <slug> | resume <slug>
group: loop
---

Side work stays tracked — never do a "quick thing" off the books.

First, split $ARGUMENTS: strip `--full`, `--discuss`, `--research`,
`--validate` — the clean description titles the bd issue; the flags are
forwarded to the vendored quick workflow (`--discuss --research --validate` ≡ `--full`).
When $ARGUMENTS is a quick subcommand (`list`, `status <slug>`,
`resume <slug>`), route it straight to the vendored quick workflow — create and claim
nothing.

1. Find the active issue: `bd list --status in_progress --assignee <actor>`
   (actor resolves the way bd does: `$BEADS_ACTOR`, then git `user.name`, then
   `$USER`). Several hits → the one in the current plan's `beads:`
   frontmatter. None is fine — skip the dep below.
2. Create the quick task — labeled `quick` + `m-<active milestone>` (milestone
   from ROADMAP.md's current header, or STATE.md), **no `phase-*` label**:
   quick work is unphased. `bd q` can't stamp metadata, so use `bd create`:
   ```bash
   bd create "<clean description>" -t task -l m-<milestone>,quick \
     --metadata '{"gsd": {"milestone": "vX.Y"}}' \
     --deps discovered-from:<active-id>   # only when step 1 found one
   ```
   (`--deps discovered-from:` records provenance without blocking; after the
   fact the same edge is `bd dep add <quick-id> <active-id> -t discovered-from`.)
3. Claim it (`bd update <quick-id> --claim`), then execute the vendored
   quick workflow (`${CLAUDE_PLUGIN_ROOT}/gsd/commands/gsd/quick.md`) with the
   description plus any stripped flags.
4. On completion: `bd close <quick-id> --reason="<1–2 sentence summary>"`.
   Abandoned or deferred → release it (`bd update <quick-id> --assignee ""
   --status open`) and leave it open: it stays visible in `/cairn:status`'s
   ready list instead of evaporating.
