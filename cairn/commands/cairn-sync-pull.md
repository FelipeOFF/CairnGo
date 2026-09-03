---
description: Pull spoke edits back into bd (last-writer-wins)
argument-hint: "[--since <iso8601>]"
---

1. Require `.cairn/sync.json` with an enabled backend. Else `/cairn-sync-config`.

```bash
PLUGIN_ROOT="${CAIRN_PLUGIN_ROOT:-${GROK_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}}"
if [ -z "$PLUGIN_ROOT" ] && [ -f .cairn/plugin-root ]; then PLUGIN_ROOT="$(head -1 .cairn/plugin-root)"; fi
bash "${PLUGIN_ROOT}/scripts/gbsync.sh" pull $ARGUMENTS
```

2. Read `.cairn/conflicts.json`. Surface new conflicts. bd remains the source; a spoke cannot silently overwrite a newer bead without a conflict entry.
