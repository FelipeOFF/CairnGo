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
| [**context-mode**](https://github.com/mksglu/context-mode) | MCP plugin that saves ~98% of your context window — sandboxed code execution + an FTS5/BM25 knowledge base with intent-driven search. Re-published here as a cairn dependency; installable on its own. Upstream: `mksglu/context-mode`. |

Install a plugin:

```text
/plugin install cairn@bigjiggity     # GSD installs automatically as a dependency
```
