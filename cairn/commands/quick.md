---
description: Tracked side-quest — stamped quick issue with discovered-from provenance, then GSD quick
argument-hint: <task description>
---

Side work stays tracked — never do a "quick thing" off the books.

1. Find the active issue: `bd list --status in_progress --assignee <actor>`
   (actor resolves the way bd does: `$BEADS_ACTOR`, then git `user.name`, then
   `$USER`). Several hits → the one in the current plan's `beads:`
   frontmatter. None is fine — skip the dep below.
2. Create the quick task — labeled `quick` + `m-<active milestone>` (milestone
   from ROADMAP.md's current header, or STATE.md), **no `phase-*` label**:
   quick work is unphased. `bd q` can't stamp metadata, so use `bd create`:
   ```bash
   bd create "$ARGUMENTS" -t task -l m-<milestone>,quick \
     --metadata '{"gsd": {"milestone": "vX.Y"}}' \
     --deps discovered-from:<active-id>   # only when step 1 found one
   ```
   (`--deps discovered-from:` records provenance without blocking; after the
   fact the same edge is `bd dep add <quick-id> <active-id> -t discovered-from`.)
3. Claim it (`bd update <quick-id> --claim`), then run `/gsd:quick` with the
   description.
4. On completion: `bd close <quick-id> --reason="<1–2 sentence summary>"`.
   Abandoned or deferred → release it (`bd update <quick-id> --assignee ""
   --status open`) and leave it open: it stays visible in `/cairn:status`'s
   ready list instead of evaporating.
