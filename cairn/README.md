# Cairn

> *A cairn is a stack of stones that marks a trail — and remembers the path you
> took. This plugin does the same for a project: it stacks **plan → work →
> memory** into one marker so a solo build stays on-trail.*

**Cairn** is a Claude Code plugin that wires the [GSD](https://github.com/jnuyens/gsd-plugin)
planning workflow (`/gsd:*`, `.planning/`) to the [beads](https://github.com/gastownhall/beads)
issue tracker (`bd`, `.beads/`) so phase planning and execution **create,
claim, and close** tracked work automatically — and makes the
[context-mode](https://github.com/mksglu/context-mode) knowledge base
**intent-aware**, scoping compressed memory to the active issue and phase.

**Batteries included.** Installing cairn auto-installs GSD **and** context-mode
(declared plugin dependencies) and, on your first session, offers to install the
beads `bd` binary. Then a single [`/cairn:init`](#install) wires a project end to
end — git, beads, GSD, and the first roadmap.

It stays **thin glue** — it does not fork, vendor, or modify GSD, beads, or
context-mode. GSD is re-published in this marketplace as a pointer to its
upstream (`jnuyens/gsd-plugin`) so it can be a clean same-marketplace dependency;
context-mode is pulled **cross-marketplace** from its own `context-mode`
marketplace (`mksglu/context-mode`); beads stays an independent upstream binary.
Cairn ships only the conventions that connect them.

## What it does

When a repo contains **both** `.planning/` (GSD) and `.beads/` (beads):

- **Phase ↔ issues** — each GSD phase `NN` maps requirement IDs → bd issue IDs
  in `.planning/phases/NN-<slug>/NN-BEADS-MAP.md`.
- **Labels** — every bd issue for phase `N` carries `phase-N` (`bd list -l phase-N`).
- **Plan frontmatter** — each `PLAN.md` carries `beads: [ids]` it advances.
- **Lifecycle** — `new-project` creates issues, `plan-phase` reads the map and
  sets frontmatter, `execute-phase` claims → in_progress → closes, `ship`
  verifies all closed before push.
- **Precedence** — GSD phase docs win over conflicting bd issue text.

It activates **only** when both directories are present, so it's silent in
non-GSD or non-beads repos.

## Requirements

Cairn handles its own dependencies:

- **GSD** — installed automatically as a plugin dependency (provides `/gsd:*`).
- **context-mode** — a plugin dependency pulled cross-marketplace from the
  `context-mode` marketplace (provides the `ctx_*` tools + intent-aware memory).
  Add that marketplace if you don't have it
  (`/plugin marketplace add mksglu/context-mode`), else the dependency stays
  unresolved and cairn is disabled until you do.
- **beads** (`bd`) — a binary, not a plugin, so cairn offers to install it on
  your first session (or run `/cairn:init`). Manual install:
  `brew install beads` · `npm install -g @beads/bd`.

## Install

```text
/plugin marketplace add BigJiggity/claude-plugins
/plugin install cairn@bigjiggity     # GSD comes with it
```

Then, in the repo you want to set up:

```text
/cairn:init        # soup to nuts: ensures GSD + bd, runs git + bd init,
                   # then launches /gsd:new-project for the roadmap interview
```

`/cairn:init` is the one command you need to start — it ensures both tools are
present, wires git + beads, and hands off to the interactive GSD project setup.
After both `.planning/` and `.beads/` exist, every `/gsd:*` command follows the
integration convention (see the bundled `cairn` skill).

## One interface — `/cairn:`

You don't have to remember whether a thing is a `bd` command or a `/gsd:*`
command. `/cairn:` is a single namespace over both; each workflow verb runs the
combined GSD+beads lifecycle per the integration conventions. `/cairn:help`
prints this map.

```text
SETUP
  /cairn:init             ensure GSD + beads, wire git + bd init, then hand off
  /cairn:new              new project: /gsd:new-project + create bd issues + maps

LOOP
  /cairn:plan  <N>        plan phase N  (GSD plan-phase + reconcile beads map)
  /cairn:work  <N>        execute phase N  (claim → execute → close per plan)
  /cairn:verify <N>       verify phase N  (GSD verify-work × beads cross-check)
  /cairn:ship             gate on all phase issues closed, then GSD ship / push

VIEW
  /cairn:status           combined: bd ready/blocked + active phase + progress
  /cairn:progress         roadmap-level progress (GSD)
  /cairn:issues [N]       list beads issues, optionally scoped to phase N

MEMORY (context-mode — on by default)
  /cairn:remember [what]  index reference material under the active gb/<id>/<phase>
  /cairn:recall  <query>  search memory scoped to the active issue + phase
  /cairn:context-config   (optional) tune the scope template / capacity threshold

SYNC (optional)
  /cairn:sync-config      mirror bd ↔ GitHub/GitLab/Jira/Asana/Azure Boards
  /cairn:sync-pull        reconcile external edits back into bd

ESCAPE HATCHES (raw passthrough — reach anything the verbs don't wrap)
  /cairn:bd  <args…>      run any beads command       (e.g. /cairn:bd dep add a b)
  /cairn:gsd <cmd> [args] run any GSD command          (e.g. /cairn:gsd debug)
  /cairn:ctx <op> [args]  run any context-mode op      (e.g. /cairn:ctx stats)
```

The verbs are a curated facade over all three tools, not a full mirror — the
three passthroughs (`/cairn:bd`, `/cairn:gsd`, `/cairn:ctx`) reach anything a
verb doesn't wrap, so the whole of beads, GSD, and context-mode stays one
keystroke away without cairn drifting as they change. All three are
dependencies, so the memory verbs work out of the box; `/cairn:context-config`
only tunes the scope template and capacity threshold.

## Two-way sync to external tools (optional)

Mirror bd issues to **GitHub Issues, GitLab, Jira, Asana, and/or Azure Boards** —
**hub-and-spoke, pull-on-demand**. bd is the hub and source of truth; every tool
syncs to bd, never tool-to-tool.

- **PUSH** (bd → tools): fires on bd lifecycle events (create / claim / close).
- **PULL** (tools → bd): `/cairn:sync-pull` reconciles external edits back
  into bd with **last-writer-wins by timestamp**; genuine both-sides-changed
  cases are logged to `.cairn/conflicts.json`.

Setup:

```text
/cairn:sync-config     # pick backends, write .cairn/sync.json
# export the API tokens it tells you to (tokens are referenced by ENV VAR NAME,
# never stored in the repo)
/cairn:sync-pull       # reconcile external edits into bd, on demand
```

Each tool is a small **adapter** in `adapters/` implementing a simple
stdin/stdout contract (`adapters/_contract.md`). Add another tool (Linear,
Trello, …) by dropping in one adapter and a `sync.json` block — no dispatcher
changes. Adapters read API tokens from environment variables named in
`sync.json`; **no secrets are ever written to disk**.

> GitHub is live-tested (via the `gh` CLI's auth). GitLab / Jira / Asana /
> Azure Boards adapters are implemented to each tool's REST spec; supply the
> relevant API token env var to use them.

**📖 Full guide:** [`docs/sync.md`](./docs/sync.md) — architecture, data model,
the reconciliation algorithm, per-backend setup, the adapter contract, security,
and troubleshooting.

## Intent-aware memory (context-mode integration)

[context-mode](https://github.com/mksglu/context-mode) ships with cairn as a
dependency, so this is on by default. Cairn gives its knowledge base
**architectural awareness**: context-mode compresses runtime data well but is
blind to *what the work is*; Cairn ties its memory to the **active bd issue**
and **GSD phase** (drive it with `/cairn:remember` and `/cairn:recall`):

- **Scope by intent** — index during execution under a `source` label
  `gb/<bd_id>/<phase>`, then recall scoped to the active task
  (`ctx_search(source: "<bd_id>")`) instead of the whole session's noise.
- **Phase-driven scope switch** — on `Execute → Verify`, checkpoint `ctx_stats`
  and switch the active scope to the new phase's label; the prior phase's noise
  is simply no longer searched.
- **Capacity guard** — when `ctx_stats` token usage crosses a configurable
  threshold, the agent is told to split the active bd issue into sub-tasks
  (`bd create` + `bd dep add`) — a natural context reset before the window degrades.

**Scope-by-label only** — this layer never deletes the knowledge base.
context-mode can only purge by whole session or whole project, so any real wipe
(`ctx_purge`) stays a manual, user-confirmed action.

Tuning (optional):

```text
/cairn:context-config   # write .cairn/context.json to tune the scope template / threshold
```

The `cairn-context` skill is active by default whenever the `ctx_*` tools are
present (they ship with cairn). `.cairn/context.json` is optional — defaults
apply without it; this command only overrides them.

**📖 Full guide:** [`docs/context.md`](./docs/context.md) — the layered model,
the source-label convention, the three behaviors, configuration, capability
boundaries, and troubleshooting.

## Components

| Path | Purpose |
|---|---|
| `skills/cairn/SKILL.md` | the GSD↔bd integration convention |
| `skills/cairn-sync/SKILL.md` | the bd↔external-tools sync convention |
| `skills/cairn-context/SKILL.md` | the context-mode intent-aware memory convention |
| `commands/init.md` | `/cairn:init` — soup-to-nuts setup (ensure GSD + bd, git + bd init, hand off to `/gsd:new-project`) |
| `commands/help.md` | `/cairn:help` — print the unified `/cairn:` interface |
| `commands/new.md` · `plan.md` · `work.md` · `verify.md` · `ship.md` | workflow verbs — the combined GSD+beads lifecycle |
| `commands/status.md` · `progress.md` · `issues.md` | views over beads + GSD state |
| `commands/remember.md` · `recall.md` | intent-scoped context-mode index / search (active issue + phase) |
| `commands/bd.md` · `gsd.md` · `ctx.md` | raw passthroughs to `bd` / `/gsd:*` / `ctx_*` |
| `commands/sync-config.md` | `/cairn:sync-config` — configure backends |
| `commands/sync-pull.md` | `/cairn:sync-pull` — reconcile tools → bd |
| `commands/context-config.md` | `/cairn:context-config` — tune the context-mode integration (optional) |
| `scripts/gbsync.py` · `gbsync.sh` | the push/pull sync dispatcher |
| `adapters/*.py` | github · gitlab · jira · asana · azure-boards adapters |
| `adapters/_contract.md` | the adapter interface spec |
| `hooks/session-start.sh` | "integration active" reminder when both dirs present |
| `scripts/cairn-init.sh` | the bootstrap script (git + bd init) |
| `templates/sync.json.example` | starter sync config |
| `templates/context.json.example` | starter context-mode config |

## Privacy

Cairn runs entirely on your machine, collects no telemetry, and sends data
only to the external trackers you explicitly enable (using your own
credentials). See [`PRIVACY.md`](./PRIVACY.md).

## License

MIT
