---
description: Tune the context-mode integration (intent-aware memory) — writes .cairn/context.json to override the defaults
group: memory
---

Tune the cairn ↔ context-mode integration, which scopes context-mode's
knowledge base by the active bd issue + GSD phase and watches token usage to
advise task-splitting. The integration is **on by default** — context-mode
ships as a cairn plugin dependency, so the defaults apply in every repo where
the cairn integration is active, with no config file needed. This command only
writes `.cairn/context.json` to override those defaults (source template,
capacity threshold). Do the following:

1. Confirm prerequisites:
   - `.beads/` exists (`ls .beads/`). If not, tell the user to run
     `/cairn:init` first and stop.
   - The `ctx_*` MCP tools (context-mode) are available this session. They
     ship with cairn (context-mode is a plugin dependency), so if they are
     missing the dependency is unresolved or the plugin was disabled — tell the
     user to add its marketplace (`/plugin marketplace add mksglu/context-mode`)
     or re-enable context-mode, and stop — without the tools there is nothing
     to tune.

2. If `.cairn/context.json` does not exist, create `.cairn/` and seed it
   from the template:
   ```bash
   mkdir -p .cairn
   cp "${CLAUDE_PLUGIN_ROOT}/templates/context.json.example" .cairn/context.json
   ```
   If it already exists, read it and edit in place (preserve existing values).

3. Ask the user (AskUserQuestion) to tune two things:
   - **Capacity guard** — keep it on? If yes, set `capacity_guard.token_threshold`
     to match their autonomous-loop length:
     short single-phase ≈ `80000`, medium multi-phase ≈ `150000` (default),
     long autonomous ≈ `300000`. If off, set `capacity_guard.enabled: false`.
   - **Source template** — keep the default `gb/{bd_id}/{phase}` unless they
     want a different label scheme. `{bd_id}` and `{phase}` are the only
     interpolated fields.

4. Leave `reset.mode` as `scope-by-label`. Explain that this integration never
   deletes the knowledge base — `ctx_purge` (session or whole project) stays a
   manual, user-confirmed action. Do not offer an auto-purge mode; context-mode
   has no per-phase or per-task delete.

5. Confirm what you wrote (path + the values set). Remind the user that the
   `cairn-context` skill was already active with the defaults — this file only
   overrides them — and that setting `enabled: false` here is the way to switch
   the conventions off in this repo.
