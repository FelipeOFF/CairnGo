# /cairn:context-config

> Tune the context-mode integration (intent-aware memory) — writes .cairn/context.json to override the defaults

## Usage

```text
/cairn:context-config
```

No arguments. The command is interactive (AskUserQuestion).

## What it does

Tunes the cairn ↔ context-mode integration, which scopes context-mode's
knowledge base by the active bd issue + GSD phase and watches token usage to
advise task-splitting. The integration is **on by default** — context-mode
ships as a cairn plugin dependency, so the defaults apply in every repo where
the cairn integration is active, with **no config file needed**. This command
only writes `.cairn/context.json` to override those defaults:

1. **Confirms prerequisites:**
   - `.beads/` exists. If not → run [`/cairn:init`](init.md) first; the
     command stops.
   - The `ctx_*` MCP tools are available this session. If missing, the
     dependency is unresolved or the plugin was disabled — the command tells
     the user to `/plugin marketplace add mksglu/context-mode` (or re-enable
     context-mode) and stops.
2. **Seeds or edits the file:** if `.cairn/context.json` does not exist, it is
   seeded from `${CLAUDE_PLUGIN_ROOT}/templates/context.json.example`;
   otherwise it is edited in place, preserving existing values.
3. **Asks two tuning questions:**
   - **Capacity guard** — keep it on, and at what
     `capacity_guard.token_threshold`: short single-phase loops ≈ `80000`,
     medium multi-phase ≈ `150000` (default), long autonomous ≈ `300000`.
     Off → `capacity_guard.enabled: false`.
   - **Source template** — keep the default `gb/{bd_id}/{phase}` unless a
     different label scheme is wanted. `{bd_id}` and `{phase}` are the **only**
     interpolated fields.
4. **Leaves `reset.mode` as `scope-by-label`.** The integration never deletes
   the knowledge base — `ctx_purge` (session or whole project) stays a manual,
   user-confirmed action. There is no auto-purge mode, because context-mode
   has no per-phase or per-task delete.
5. **Confirms** the path and values written.

Setting `enabled: false` in the file is the way to switch the conventions off
in a repo; an absent file means everything runs on defaults.

## Flags & arguments

None. All choices are made interactively.

## Examples

```text
/cairn:context-config
```

→ prerequisites pass, `.cairn/context.json` seeded from the template, user
picks threshold `300000` for long `/gsd:autonomous` runs and keeps the default
source template. The command confirms:
`wrote .cairn/context.json — capacity_guard.token_threshold: 300000, source_template: gb/{bd_id}/{phase}`.

```text
/cairn:context-config       # in a repo without .beads/
```

→ stops immediately and routes to [`/cairn:init`](init.md).

## Files touched

- **Reads:** `.beads/` (existence check),
  `${CLAUDE_PLUGIN_ROOT}/templates/context.json.example` (seed),
  `.cairn/context.json` (when editing in place).
- **Writes:** `.cairn/context.json` (creates `.cairn/` if needed). The file
  holds no secrets and is meant to be committed so the team shares the same
  settings.

## Related

- [`/cairn:remember`](remember.md) / [`/cairn:recall`](recall.md) — the verbs this config tunes
- [`/cairn:ctx`](ctx.md) — raw passthrough, including the manual `purge`
- [`/cairn:init`](init.md) — prerequisite setup (`.beads/`)
- [Cairn context guide](../context.md) — full field table and threshold tuning
