---
description: Show the cairn unified command interface (one namespace for GSD + beads)
---

Print this map — `/cairn:` is the single interface for the whole GSD↔beads
workflow. Show it to the user, then offer the obvious next step for their repo
(no `.planning/` and no `.beads/` → `/cairn:new`; `.beads/` but no
`.planning/` — or the reverse — → `/cairn:migrate`; both present →
`/cairn:status`).

```text
SETUP
  /cairn:init             ensure GSD + beads, wire git + bd init, then hand off
  /cairn:new              new project: /gsd:new-project + stamped bd issues + generated maps

LOOP
  /cairn:plan  <N>        plan phase N  (GSD plan-phase + regenerate/reconcile beads map)
  /cairn:work  <N>        execute phase N  (claim → execute → close per plan)
  /cairn:quick <desc>     tracked side-quest: stamped quick issue (discovered-from) + GSD quick (--full/--discuss/--research/--validate pass through)
  /cairn:verify <N>       verify phase N  (GSD verify-work × beads cross-check)
  /cairn:ship             gate on all phase issues closed, then GSD ship / push
  /cairn:milestone <op>   new: roadmap + issues + maps · complete: gate → reconcile → archive
  /cairn:autonomous [N]   run every remaining phase hands-off (plan → claim → execute → close → verify per phase; stops at the ship gate)

  scripts/cairn-bookkeep.sh close <N> --apply
                          the end-of-phase bookkeeping, in one command: marks
                          the phase and its requirements, moves the coverage
                          table, the footer, the plan checkboxes and the STATE
                          counters, regenerates the map, releases the lease.
                          Invoked by the commands above; run it by hand when
                          you closed a phase outside them. Reading is the
                          default — drop --apply to see the edits first.
                          → docs/commands/bookkeep.md

VIEW
  /cairn:status           board render: READY / DOING / BLOCKED lanes + one next action (--brief)
  /cairn:progress         roadmap-level progress (GSD)
  /cairn:issues [N]       list beads issues, optionally scoped to phase N

MIGRATE & HEALTH
  /cairn:migrate          adopt an existing repo (GSD-only, beads-only, or both
                          unwired): detect → dry-run plan → confirm → apply
  /cairn:doctor           consistency checks (req↔issue, frontmatter ids, map
                          freshness, label pairs) + --fix-labels repair

MEMORY (context-mode — on by default)
  /cairn:remember [what]  index reference material under the active gb/<id>/<phase>
  /cairn:recall  <query>  search memory scoped to the active issue + phase

SYNC (optional)
  /cairn:sync-pull        reconcile external edits back into bd

CONFIG (three commands, three files — they do not overlap)
  /cairn:config           cairn's own knobs: auto-commit, PR scope, the
                          ceilings on an autonomous run, test jobs
                          → .cairn/config.json
  /cairn:sync-config      which backends bd mirrors to (GitHub/GitLab/Jira/
                          Asana/Azure Boards)        → .cairn/sync.json
                          Jira is detected first: it shows the key it found
                          and where, asks once, and writes the backend from
                          your yes — you never type a key or a credential.
                          No signal means no question, and a no is recorded
                          (jira.link in .cairn/config.json) so it stays no.
  /cairn:context-config   context-mode scope template + capacity threshold
                                                     → .cairn/context.json
  Each writes a file you can also edit by hand, and /cairn:config ends by
  naming all three plus GSD's own `cairn.enabled` — one place to look.

ESCAPE HATCHES (raw passthrough — reach anything the verbs don't wrap)
  /cairn:bd  <args…>      run any beads command   (e.g. /cairn:bd dep add a b)
  /cairn:gsd <cmd> [args] run any GSD command      (e.g. /cairn:gsd debug)
  /cairn:ctx <op> [args]  run any context-mode op  (e.g. /cairn:ctx stats)
```
