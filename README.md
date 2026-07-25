# CairnGo

![CairnGo — plan · work · ship](assets/cairngo-hero.png)

<p align="center">
  <a href="https://github.com/FelipeOFF/CairnGo/actions/workflows/ci.yml"><img src="https://github.com/FelipeOFF/CairnGo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version 1.0.0"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-d97757" alt="Claude Code plugin marketplace">
</p>

**One lifecycle for planning, tracking and shipping — inside Claude Code.**
CairnGo fuses [GSD](https://github.com/open-gsd/get-shit-done-redux) (structured
planning), [beads](https://github.com/gastownhall/beads) (a git-native issue
tracker built for AI agents) and
[context-mode](https://github.com/mksglu/context-mode) (compressed memory) into
a single workflow: you plan and execute with plain `/gsd:*` commands, and every
work item is created, claimed, closed and gated in `bd` — invisibly.

---

## Why

Planning tools and issue trackers drift apart the moment an agent is doing the
work. GSD knows *what* to build; beads knows *what's in flight*; nothing keeps
them honest with each other. Cairn closes that gap with **enforcement, not
prose**:

| Layer | What it guarantees |
|---|---|
| **GSD capability** | `/gsd:plan-phase` links issues, `/gsd:execute-phase` claims & closes them, `/gsd:ship` is *blocked* while tracked work is open |
| **Claude Code hooks** | every `bd` write auto-mirrors to external trackers and refreshes the phase map; unwired repos get a migration nudge at session start |
| **git `pre-push` shim** | the ship gate holds even outside the agent |
| **Generated artifacts** | the requirement↔issue map is derived from `bd` state — never hand-maintained, never stale |

## Quickstart

```text
/plugin marketplace add FelipeOFF/CairnGo
/plugin marketplace add mksglu/context-mode   # cross-marketplace dependency
/plugin install cairn@cairngo                 # GSD installs automatically
```

Then, in the project you want to wire:

```text
/cairn:init      # detects the repo state, installs the capability,
                 # wires git + bd, and routes to the right setup
```

From there the normal loop just works — `/gsd:plan-phase 1`,
`/gsd:execute-phase 1`, `/gsd:verify-work`, `/gsd:ship` — with tracked work
handled for you. `/cairn:help` prints the full unified command map.

## Already using GSD or beads?

`/cairn:init` detects existing history and routes to **`/cairn:migrate`**,
which adopts your repo instead of restarting it:

| Your repo has | Migration does |
|---|---|
| `.planning/` only (GSD) | backfills the whole beads graph — epics per phase, issues per requirement, finished phases preserved as closed history |
| `.beads/` only (beads) | bootstraps `.planning/` from your issue graph — epics become phases, you confirm the grouping |
| both, unwired | links requirements to issues (exact matches auto, fuzzy ones confirmed by you) |

Always dry-run first, idempotent on re-runs, resumable if interrupted — and it
**never** runs `/gsd:new-project` over an existing `.planning/`. Details in the
[migration guide](cairn/docs/migration.md).

## Plugins in this marketplace

| Plugin | Description |
|---|---|
| [**cairn**](./cairn) | The fusion layer itself — capability, hooks, migration, doctor, sync adapters (GitHub/GitLab/Jira/Asana/Azure Boards) and intent-scoped memory. See the [full plugin README](./cairn#readme). |
| **gsd** | Get Shit Done — planning/execution/verification (`/gsd:*`). Published here as a cairn dependency, sourced from upstream; compatibility pinned by the capability's `engines.gsd`. Standalone: `/plugin install gsd@cairngo`. |

## Documentation

| Doc | What's inside |
|---|---|
| [Plugin README](cairn/README.md) | the full feature tour, data model and command map |
| [Command reference](cairn/docs/commands.md) | all 22 `/cairn:` commands — grouped index, one doc per verb |
| [Architecture](cairn/docs/architecture.md) | ownership model, linking contract, enforcement layers |
| [Migration guide](cairn/docs/migration.md) | adopting existing repos, safety model, troubleshooting |
| [Sync guide](cairn/docs/sync.md) | mirroring bd to external trackers |
| [Memory guide](cairn/docs/context.md) | intent-scoped context-mode integration |
| [CHANGELOG](CHANGELOG.md) | release history |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (hooks and the
  capability are Claude Code–specific; other GSD runtimes get the conventions
  without the enforcement)
- `bd` ≥ 1.1.0 (`brew install beads` — `/cairn:init` offers to install it)
- GSD ≥ 1.8.0 (pinned by `engines.gsd`; installs as a dependency)

## Contributing

Tests are bats against real `bd` fixtures — `bats tests/` — and every
deterministic behavior ships as a script with its own suite. Ground rules,
layout and style live in [CONTRIBUTING.md](CONTRIBUTING.md).

## License & credits

[MIT](LICENSE). CairnGo began as a fork of
[eventually-consistent-code/claude-plugins](https://github.com/eventually-consistent-code/claude-plugins)
— credit to the original cairn concept. The stones are stacked higher here:
capability fusion, automatic migration, deterministic gates and a test harness.
