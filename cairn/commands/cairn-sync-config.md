---
description: Configure two-way bd ↔ spoke sync (writes .cairn/sync.json)
---

bd is the hub. Spokes (Jira, GitHub, GitLab, Asana, Azure Boards) mirror specs as Epics (or the tool's parent type) and tickets as Stories/Tasks, with `bd dep` as blocks.

1. Require `.beads/` (`/cairn-init` if missing).
2. If `.cairn/sync.json` is missing:

```bash
PLUGIN_ROOT="${CAIRN_PLUGIN_ROOT:-${GROK_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}}"
if [ -z "$PLUGIN_ROOT" ] && [ -f .cairn/plugin-root ]; then PLUGIN_ROOT="$(head -1 .cairn/plugin-root)"; fi
mkdir -p .cairn
cp "${PLUGIN_ROOT}/templates/sync.json.example" .cairn/sync.json
```

3. Edit backends with the user (enable, project keys, token **env var names** never secrets).
4. Jira graph: spec = Epic, ticket = Story/Task, deps = blocks, `m-vX.Y` = Fix Version. Linear is not shipped.
5. Confirm a dry-run push of one open spec if they want.
