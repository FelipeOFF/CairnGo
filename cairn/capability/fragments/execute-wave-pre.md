<!-- cairn capability — execute:wave:pre fragment, injected into the executor.
     NOT an alternate wave dispatch: the host workflow's normal dispatch loop
     proceeds unchanged; this only adds a start-of-plan claim protocol.
     Registered at execute:wave:pre (not execute:pre) because the execute
     workflow only renders wave-level pre hooks today. -->

## Claim this plan's beads issues before starting (cairn)

Applies only when the project root contains `.beads/`. If it is missing, or
the plan has no `beads:` frontmatter key, skip silently.

Before executing the first task of this wave, re-acquire this phase's
coordination lease (it exits 0 and prints a report; it no-ops silently
outside beads repos):

```bash
CAP=".gsd/capabilities/cairn"; [ -d "$CAP" ] || CAP="${GSD_HOME:-$HOME}/.gsd/capabilities/cairn"
bash "$CAP/scripts/cairn-lease.sh" acquire <N>
```

This repeats the acquire call `/cairn:work` already made once at session
start rather than relying on that single call for the whole run: it is what
keeps the lease's heartbeat fresh for the DURATION of a long, multi-wave
execution — session-start only renews the lease once, so without this
per-wave call a phase that runs for hours across several waves with no
session restart would have its lease read as stale partway through, even
though the same worktree is still actively working it. If it reports the
lease held by another live worktree (exit 3), surface the printed report
verbatim — same posture as `/cairn:work`'s own acquire step: report and
continue, never block the wave.

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
