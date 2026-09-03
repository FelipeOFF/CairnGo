---
description: Render READY / DOING / BLOCKED from bd
argument-hint: "[--brief] [--json] [--plain]"
---

Show the board. READY is `bd ready` ∩ `ready-for-agent` when that label is in use; otherwise `bd ready`. Do not paraphrase the script output.

```bash
PLUGIN_ROOT="${CAIRN_PLUGIN_ROOT:-${GROK_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}}"
if [ -z "$PLUGIN_ROOT" ] && [ -f .cairn/plugin-root ]; then PLUGIN_ROOT="$(head -1 .cairn/plugin-root)"; fi
bash "${PLUGIN_ROOT}/scripts/cairn-status.sh" --width 100 $ARGUMENTS
```

Present the output in a fenced code block. Exit 5 (bd missing) → say so and point at `/cairn-init`.
