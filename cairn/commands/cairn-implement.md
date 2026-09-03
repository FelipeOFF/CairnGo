---
description: Grill, spec, ticket and implement — one door, starts at the right step
argument-hint: "[ref]"
---

Run the SDD loop on beads. Read `${PLUGIN_ROOT}/skills/cairn/SKILL.md` and `${PLUGIN_ROOT}/references/matt-on-beads.md` first.

`PLUGIN_ROOT` = `$CAIRN_PLUGIN_ROOT` or `$GROK_PLUGIN_ROOT` or `$CLAUDE_PLUGIN_ROOT` or `head -1 .cairn/plugin-root`.

`$ARGUMENTS` is `ref` (optional).

## Resolve ref

Empty → new work. Else try, in order:

1. `bd show <ref>` succeeds → that bead
2. spoke key: `.cairn/id-map.json` or `bd list` / `external_ref` matching `<ref>`
3. label `m-<ref>` or ref already looks like `m-vX.Y` → `bd list -l <label>`
4. title search: `bd search <ref>`

## Route

| what you resolved | action |
|---|---|
| nothing / idea only | grill-with-docs + domain terms on a **new spec bead** (not CONTEXT.md). Then to-spec body on that bead. Then to-tickets as children. Then implement-spec on the frontier. |
| spec (`cairn.kind=spec` or type epic, no `kind=ticket`) with empty description | grill / to-spec; `bd update --description` / `--design` |
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
