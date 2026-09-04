# Command reference

Files live at `cairn/commands/`. Each verb has a hyphenated file (`cairn-implement.md`) and a short sibling (`implement.md`).

## Invocation

| Harness | Hyphenated file | Short file |
|---|---|---|
| Grok | `/cairn-init` | `/init` (qualified `/cairn:init` if the short name collides) |
| Claude Code | `/cairn:cairn-init` | `/cairn:init` |

Type `/cairn-implement` on Grok. Type `/cairn:implement` on Claude Code. The doubled `/cairn:cairn-implement` still works after update, from the hyphenated file.

Existing installs keep the old command list until the plugin copy is replaced:

```text
grok plugin update cairn
# or, path install:
grok plugin install /path/to/CairnGo/cairn --trust
```

Claude Code: update `cairn` from the marketplace, or reinstall the path. Restart the session (or reload plugins). `.cairn/plugin-root` should point at the new copy.

## Commands

| Slash | Claude Code | Role |
|---|---|---|
| `/cairn-grill [ref]` | `/cairn:grill` | interview, write the spec bead, stop |
| `/cairn-implement [ref]` | `/cairn:implement` | tickets + code for a spec that exists |
| `/cairn-init` | `/cairn:init` | git + bd, `docs/agents/*`, `.cairn/plugin-root` |
| `/cairn-status` | `/cairn:status` | READY / DOING / BLOCKED from bd |
| `/cairn-doctor` | `/cairn:doctor` | v5 spec/ticket graph health |
| `/cairn-sync-config` | `/cairn:sync-config` | enable a spoke (writes `.cairn/sync.json`) |
| `/cairn-sync-pull` | `/cairn:sync-pull` | pull spoke edits into bd (last-writer-wins) |

`/cairn-implement` on a raw idea stops and names `/cairn-grill`. It does not interview.

`bd` is the hub. Specs and tickets live on beads. Optional spokes (Jira, GitHub, GitLab, Asana, Azure Boards) mirror that graph.

## Historical names

Pre-5.0 cairn wrapped GSD as `/cairn:plan`, `/cairn:migrate`, and dozens more. Those commands were removed in 5.0.0. `/cairn:init` is current again: it is the short sibling of `cairn-init.md`, not the old GSD init. CHANGELOG 5.0.0 is the record of what was deleted.
