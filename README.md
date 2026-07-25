# CairnGo

Claude Code plugin marketplace by [FelipeOFF](https://github.com/FelipeOFF).

## Install the marketplace

```text
/plugin marketplace add FelipeOFF/CairnGo
```

## Plugins

| Plugin | Description |
|---|---|
| [**Cairn**](./cairn) | Marks the trail and remembers the path. Batteries-included GSD↔beads glue: installs GSD with it, bootstraps the beads tracker (`bd`), and wires a project end to end with one `/cairn:init`. The bundled GSD capability fuses the loops so plain `/gsd:*` commands create, claim, close, and gate bd issues; `/cairn:migrate` wires repos that already have planning or beads history. Optionally mirrors issues to GitHub/GitLab/Jira/Asana/Azure Boards and makes the context-mode knowledge base intent-aware (memory scoped to the active issue + phase). |
| **GSD** | Get Shit Done — structured planning/execution/verification workflow (`/gsd:*`). Published here as a cairn dependency, sourced from its upstream repo (see `.claude-plugin/marketplace.json`); compatibility is pinned by the cairn capability's `engines.gsd`. Installable on its own: `/plugin install gsd@cairngo`. |

cairn also depends on [**context-mode**](https://github.com/mksglu/context-mode)
(`mksglu/context-mode`), pulled cross-marketplace from its own `context-mode`
marketplace — add that marketplace if you don't already have it:

```text
/plugin marketplace add mksglu/context-mode
```

Install a plugin:

```text
/plugin install cairn@cairngo     # GSD installs automatically as a dependency
```
