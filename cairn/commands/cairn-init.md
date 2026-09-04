---
description: Wire git + beads, write tracker templates and plugin-root
argument-hint: "[target-dir]"
---

Bootstrap this repo for cairn v5.

## 1. bd on PATH

If `bd` is missing, offer to install (`brew install beads`, or `npm install -g @beads/bd`, or the beads install script). Then continue.

## 2. Deterministic wire

```bash
PLUGIN_ROOT="${CAIRN_PLUGIN_ROOT:-${GROK_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}}"
if [ -z "$PLUGIN_ROOT" ] && [ -f .cairn/plugin-root ]; then PLUGIN_ROOT="$(head -1 .cairn/plugin-root)"; fi
bash "${PLUGIN_ROOT}/scripts/cairn-init.sh" ${ARGUMENTS:-.}
```

If `PLUGIN_ROOT` is still empty, the init script lives next to this command at `../scripts/cairn-init.sh` relative to the plugin checkout.

## 3. Tracker files for Matt skills

Copy (do not overwrite if the user already edited them):

- `${PLUGIN_ROOT}/templates/issue-tracker-beads.md` → `docs/agents/issue-tracker.md`
- `${PLUGIN_ROOT}/templates/triage-labels.md` → `docs/agents/triage-labels.md`

## 4. Next

Offer `/cairn-grill` with the first piece of work. Do not create `.planning/` or `CONTEXT.md`.
