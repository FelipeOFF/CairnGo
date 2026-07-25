<!-- cairn capability — execute:wave:pre fragment, injected into the executor.
     NOT an alternate wave dispatch: the host workflow's normal dispatch loop
     proceeds unchanged; this only adds a start-of-plan claim protocol.
     Registered at execute:wave:pre (not execute:pre) because the execute
     workflow only renders wave-level pre hooks today. -->

## Claim this plan's beads issues before starting (cairn)

Applies only when the project root contains `.beads/`. If it is missing, or
the plan has no `beads:` frontmatter key, skip silently.

Before executing the first task of your assigned plan, claim every id listed
in the plan's `beads:` frontmatter:

```bash
bd update <id> --claim
```

- `--claim` atomically assigns the issue to you AND sets it `in_progress` —
  no separate `--status` call. It is idempotent when the issue is already
  claimed by you; that case is fine, continue.
- If an id is claimed by **someone else**, do not steal it: surface the
  conflict in your output and continue with the plan (the orchestrator
  resolves ownership).
- Track further to-dos of this plan in bd, not in TodoWrite or markdown
  lists.

If `.cairn/sync.json` has an enabled backend and config `cairn.sync_push` is
not false, push the mirror for each claimed id right after claiming (see the
cairn-sync skill).
