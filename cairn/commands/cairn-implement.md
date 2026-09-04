---
description: Ticket and implement a spec that already exists
argument-hint: "[ref]"
---

Run the SDD **implement** half on beads. Read `${PLUGIN_ROOT}/skills/cairn/SKILL.md` and `${PLUGIN_ROOT}/references/matt-on-beads.md` first.

This command does **not** interview a raw idea. If there is nothing to implement yet, point at `/cairn-grill` and stop. Do not write code in that case.

`PLUGIN_ROOT` = `$CAIRN_PLUGIN_ROOT` or `$GROK_PLUGIN_ROOT` or `$CLAUDE_PLUGIN_ROOT` or `head -1 .cairn/plugin-root`.

`$ARGUMENTS` is `ref` (optional).

## Resolve ref

Empty → look at `bd ready` ∩ `ready-for-agent`. Else try, in order:

1. `bd show <ref>` succeeds → that bead
2. spoke key: `.cairn/id-map.json` or `bd list` / `external_ref` matching `<ref>`
3. label `m-<ref>` or ref already looks like `m-vX.Y` → `bd list -l <label>`
4. title search: `bd search <ref>`

## Route

| what you resolved | action |
|---|---|
| nothing / idea only / unresolved ref | **stop.** Tell the user to run `/cairn-grill` with the idea. Do not create a spec. Do not write code. |
| spec (`cairn.kind=spec` or type epic, no `kind=ticket`) with empty description | **stop.** `/cairn-grill <spec-id>` — the spec is hollow. |
| spec with body, no children | to-tickets → `bd create --parent <spec>` + `bd dep`; label `ready-for-agent` |
| spec or milestone with open children | implement-spec on **frontier**: `ready-for-agent` and `bd ready` |
| ticket | implement that ticket if unblocked; else name the blockers |
| `m-vX.Y` / epic spoke | frontier of specs that carry that label (or children of that epic) |

Creating `CONTEXT.md` or `docs/adr/` is an **error**. Write glossary/ADRs on the spec `design`.

After each `bd create` / `--claim` / `bd close`, PUSH if sync is enabled:

```bash
bash "${PLUGIN_ROOT}/scripts/gbsync.sh" create|update|close <id>
```

Implement-spec: one PR for the spec, worktrees per ticket, merge into the PR branch as the frontier opens, then `/cairn-status`.
