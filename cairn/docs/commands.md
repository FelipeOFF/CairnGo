# Command reference

Six slash commands. Files live at `cairn/commands/cairn-*.md`.

## Invocation

| Harness | What you type | Why |
|---|---|---|
| Grok | `/cairn-init` | slash name is the filename |
| Claude Code | `/cairn:cairn-init` | plugin commands register as `plugin:filename` |
| Claude Code, no collision | `/cairn-init` | official docs: prefix is optional unless another command shares the name |

Documented names are hyphenated (`/cairn-implement`), not `/cairn:plan`. The qualified Claude form is `/cairn:cairn-init`, never `/cairn:init` — that file does not exist.

## Commands

| Slash | Role |
|---|---|
| `/cairn-init` | git + bd, `docs/agents/*`, `.cairn/plugin-root` |
| `/cairn-implement [ref]` | grill → spec → tickets → implement. `ref` is a bd id, spoke key, `m-vX.Y`, or title |
| `/cairn-status` | READY / DOING / BLOCKED from bd |
| `/cairn-doctor` | v5 spec/ticket graph health |
| `/cairn-sync-config` | enable a spoke (writes `.cairn/sync.json`) |
| `/cairn-sync-pull` | pull spoke edits into bd (last-writer-wins) |

`bd` is the hub. Specs and tickets live on beads. Optional spokes (Jira, GitHub, GitLab, Asana, Azure Boards) mirror that graph.

## Historical names

Pre-5.0 cairn wrapped GSD as `/cairn:init`, `/cairn:plan`, `/cairn:migrate`, `/cairn:doctor`, and dozens more. Those commands were removed in 5.0.0. CHANGELOG 5.0.0 is the record; this page does not keep them as current.
