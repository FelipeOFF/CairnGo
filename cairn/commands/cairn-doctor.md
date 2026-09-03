---
description: Health-check the v5 spec/ticket graph, labels, claims, spoke
argument-hint: "[--json] [--fix]"
---

```bash
PLUGIN_ROOT="${CAIRN_PLUGIN_ROOT:-${GROK_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}}"
if [ -z "$PLUGIN_ROOT" ] && [ -f .cairn/plugin-root ]; then PLUGIN_ROOT="$(head -1 .cairn/plugin-root)"; fi
bash "${PLUGIN_ROOT}/scripts/cairn-doctor.sh" $ARGUMENTS
```

Print the report verbatim. Route each fail to a fix (missing `.beads/` → `/cairn-init`; spec without tickets → `/cairn-implement <spec>`; spoke drift → `/cairn-sync-pull`). Do not treat missing `phase-N` on v5 work as a failure.
