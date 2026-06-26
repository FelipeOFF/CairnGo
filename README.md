# claude-plugins

Marketplace of Claude Code plugins by BigJiggity.

## Install the marketplace

```text
/plugin marketplace add BigJiggity/claude-plugins
```

## Plugins

| Plugin | Description |
|---|---|
| [**Cairn**](./cairn) | Marks the trail and remembers the path. Batteries-included GSD↔beads glue: installs GSD with it, bootstraps the beads tracker (`bd`), and wires a project end to end with one `/cairn:init`. Wires GSD planning (`/gsd:*`) to beads — create, claim, and close tracked work — optionally mirrors issues to GitHub/GitLab/Jira/Asana/Azure Boards, and optionally makes the context-mode knowledge base intent-aware (memory scoped to the active issue + phase). |
| [**GSD**](https://github.com/jnuyens/gsd-plugin) | Get Shit Done — structured planning/execution/verification workflow (`/gsd:*`). Re-published here as a cairn dependency; installable on its own. Upstream: `jnuyens/gsd-plugin`. |

cairn also depends on [**context-mode**](https://github.com/mksglu/context-mode)
(`mksglu/context-mode`), pulled cross-marketplace from its own `context-mode`
marketplace — add that marketplace if you don't already have it.

Install a plugin:

```text
/plugin install cairn@bigjiggity     # GSD installs automatically as a dependency
```
