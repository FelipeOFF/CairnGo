# Command reference

One page per `/cairn:` command, grouped the same way `/cairn:help` prints the
map. Each description below is the command's own one-liner; follow the link for
usage, flags, exit codes, examples, and the files each command touches.

**How many there are is derived, not typed** — see the count under
[Wrapped GSD commands](#wrapped-gsd-commands), which `cairn-wrap.sh docs`
regenerates from what is installed. A hand-written count ages into a lie: this
page once claimed 22 commands while linking 23 pages with 25 on disk, and
`commands/doctor.md` claimed fifteen checks with sixteen registered. Both were
corrected by hand, which is exactly what guarantees the next drift.

## Setup

| Command | Description |
|---|---|
| [`/cairn:init`](./commands/init.md) | One-command, soup-to-nuts project setup — ensure GSD + beads, wire git + bd init, then hand off to the interactive GSD project setup |
| [`/cairn:new`](./commands/new.md) | Start a new cairn project — GSD new-project, then create the bd issues and generate the phase↔beads maps |

## Loop

| Command | Description |
|---|---|
| [`/cairn:plan`](./commands/plan.md) | Plan a phase — context, research and one plan record per wave, all on beads |
| [`/cairn:work`](./commands/work.md) | Execute a phase — claim each plan record's beads, do the work, close the record with its summary and the beads with their reason |
| [`/cairn:quick`](./commands/quick.md) | Tracked side-quest — stamped quick issue with discovered-from provenance, then GSD quick |
| [`/cairn:verify`](./commands/verify.md) | Verify a phase's work — every plan record's summary checked against the code and the beads, the verdict recorded on the carrier |
| [`/cairn:ship`](./commands/ship.md) | Ship — verify every completed phase's beads are closed, then GSD ship / push |
| [`/cairn:milestone`](./commands/milestone.md) | Milestone lifecycle — new (roadmap + stamped issues + maps) or complete (gate → reconcile → archive → compact) |
| [`/cairn:autonomous`](./commands/autonomous.md) | Run every remaining phase hands-off — the full cairn loop per phase (map → plan → claim → execute → close → verify), doctor between phases, ship gate at the end |

## View

| Command | Description |
|---|---|
| [`/cairn:status`](./commands/status.md) | Render the status board — READY / DOING / BLOCKED lanes from bd, GSD position, one next action |
| [`/cairn:progress`](./commands/progress.md) | Roadmap-level project progress (GSD) |
| [`/cairn:issues`](./commands/issues.md) | List beads issues, optionally scoped to a phase |
| [`/cairn:land`](./commands/land.md) | Did this work reach the control branch — per phase, offline, and which pull request took it |
| [`/cairn:review`](./commands/review.md) | Pull-request state for this project's phases — the one cairn surface that talks to the forge, behind a switch that is off by default |
| [`/cairn:help`](./commands/help.md) | Show the cairn unified command interface (one namespace for GSD + beads) |

## Migrate & health

| Command | Description |
|---|---|
| [`/cairn:migrate`](./commands/migrate.md) | Adopt an existing repo into cairn — detect GSD/beads state, dry-run a plan, confirm with the user, apply with resume journaling |
| [`/cairn:doctor`](./commands/doctor.md) | Health-check the GSD↔beads wiring — run cairn-doctor, explain the report, route each finding to its fix |
| [`/cairn:reconcile`](./commands/reconcile.md) | Investigate a detected phase conflict and propose a cited reconciliation — proposes only, never applies |

## Configuration

| Command | Description |
|---|---|
| [`/cairn:config`](./commands/config.md) | Configure cairn — auto-commit, PR scope, the ceilings on an autonomous run, and test jobs (writes .cairn/config.json, the file you can also edit by hand) |

## Memory (context-mode — on by default)

| Command | Description |
|---|---|
| [`/cairn:remember`](./commands/remember.md) | Index current work into context-mode under the active bd issue + phase label |
| [`/cairn:recall`](./commands/recall.md) | Recall context-mode memory scoped to the active bd issue + phase (intent-aware search) |
| [`/cairn:context-config`](./commands/context-config.md) | Tune the context-mode integration (intent-aware memory) — writes .cairn/context.json to override the defaults |

## Sync (optional)

| Command | Description |
|---|---|
| [`/cairn:sync-config`](./commands/sync-config.md) | Configure two-way bd↔external sync (GitHub/GitLab/Jira/Asana/Azure Boards) — writes .cairn/sync.json |
| [`/cairn:sync-pull`](./commands/sync-pull.md) | Reconcile external work-management tools back into bd (pull-on-demand, last-writer-wins) |
| [`/cairn:jira`](./commands/jira.md) | Link this cycle to Jira — Story ↔ milestone, Sub-task ↔ phase, 1:1, written to the bead's external_ref; the only door that talks to the Atlassian MCP |

## Escape hatches (raw passthrough)

| Command | Description |
|---|---|
| [`/cairn:bd`](./commands/bd.md) | Run any beads (bd) command directly — raw passthrough |
| [`/cairn:gsd`](./commands/gsd.md) | Run a command from an external GSD install — raw passthrough, and cairn does not require one |
| [`/cairn:ctx`](./commands/ctx.md) | Run a context-mode operation directly — raw passthrough to the ctx_* tools |

## Wrapped GSD commands

<!-- cairn:generated:start -->
Generated by cairn-wrap — do not edit between markers

cairn ships **41** commands: **13** wrap a `/gsd:*` command (listed below, derived from each command file's `wraps:` frontmatter) and **28** are cairn's own (grouped above).

**Phase-scoped — claim the phase's issues, delegate, refresh the map**

| Command | Wraps | Description |
|---|---|---|
| [`/cairn:ai-integration-phase`](./commands/ai-integration-phase.md) | `/gsd:ai-integration-phase` | Record the AI design contract for a phase that builds an AI system — the AI-SPEC on the phase carrier, with its requirements and evals tracked |
| [`/cairn:discuss-phase`](./commands/discuss-phase.md) | `/gsd:discuss-phase` | Gather phase context before planning — the decisions recorded on the phase carrier, and the phase's beads reconciled against them |
| [`/cairn:mvp-phase`](./commands/mvp-phase.md) | `/gsd:mvp-phase` | Plan a phase as a vertical MVP slice — the plan recorded on beads, the tracer wave first, and the map reconciled |
| [`/cairn:plan-review-convergence`](./commands/plan-review-convergence.md) | `/gsd:plan-review-convergence` | Replan until cross-AI review concerns are resolved — the plan records rewritten, the convergence log on the carrier, the requirement linkage re-resolved after every rewrite |
| [`/cairn:secure-phase`](./commands/secure-phase.md) | `/gsd:secure-phase` | Retroactively verify a completed phase's threat mitigations — the security review recorded on the carrier, and an unmitigated threat a tracked issue rather than a note |
| [`/cairn:spec-phase`](./commands/spec-phase.md) | `/gsd:spec-phase` | Clarify WHAT a phase delivers, with ambiguity scoring — the SPEC recorded on the phase carrier, and every requirement it names a stamped issue |
| [`/cairn:ui-phase`](./commands/ui-phase.md) | `/gsd:ui-phase` | Record the UI design contract for a frontend phase — the UI-SPEC on the phase carrier, with its requirements tracked as stamped issues |
| [`/cairn:ultraplan-phase`](./commands/ultraplan-phase.md) | `/gsd:ultraplan-phase` | Offload planning to the ultraplan cloud and import it back — the imported plan lands as plan records that name the requirements they advance |
| [`/cairn:validate-phase`](./commands/validate-phase.md) | `/gsd:validate-phase` | Retroactively fill validation gaps on a completed phase — the verification recorded on the carrier, and any issue the audit re-opens re-opened in bd too |

**Structural — changes the phase list itself, so labels move**

| Command | Wraps | Description |
|---|---|---|
| [`/cairn:phase`](./commands/phase.md) | `/gsd:phase` | CRUD for phases in ROADMAP.md — GSD phase, plus the relabel that keeps its issues from being orphaned |

**Milestone-scoped — the label pair is `m-<milestone>`**

| Command | Wraps | Description |
|---|---|---|
| [`/cairn:audit-milestone`](./commands/audit-milestone.md) | `/gsd:audit-milestone` | Audit a milestone against its original intent before archiving — GSD audit-milestone, reported against the same gate /cairn:milestone complete enforces |
| [`/cairn:cleanup`](./commands/cleanup.md) | `/gsd:cleanup` | Archive phase directories from completed milestones — GSD cleanup, refusing to archive over open issues or a missing beads map |
| [`/cairn:review-backlog`](./commands/review-backlog.md) | `/gsd:review-backlog` | Promote backlog items into the active milestone — GSD review-backlog, and every promoted item arrives as a stamped bd issue |

⚠ Orphan page: `commands/bookkeep.md` documents no installed command.

<!-- cairn:generated:end -->

## See also

- [Architecture](./architecture.md) — how the pieces fit together
- [Migration guide](./migration.md) — adopting existing repos
- [GSD Core migration](./gsd-core-migration.md) — moving an existing install to
  the official GSD, and what changed in v1.4
- [gsd-core commands](./gsd-core-commands.md) — a recorded decision for every
  GSD command cairn's own loop does not already drive: which earn a wrapper,
  which to run directly, and which are out of scope
- [Sync guide](./sync.md) — mirroring bd to external trackers
- [Memory guide](./context.md) — the context-mode integration
