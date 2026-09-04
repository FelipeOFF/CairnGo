---
name: cairn
description: Spec-driven development on beads. Use when the repo has `.beads/`, or the user runs /cairn-init, /cairn-implement, /cairn-status, /cairn-doctor, or asks to grill/spec/ticket/implement work with bd (and optional Jira or other spokes). Conducts grill → spec → tickets → implement. The bead is the source; CONTEXT.md in this loop is an error.
---

# cairn

bd is the hub. Specs and tickets live on beads. Optional spokes (Jira, GitHub, GitLab, Asana, Azure Boards) mirror that graph; they are never the source.

## Gate

`.beads/` must exist (`bd ready` or `ls .beads/`). If it does not, run `/cairn-init`. Never run `bd` in a repo without `.beads/`.

Use `bd` for all task tracking. No markdown TODO lists, no `.planning/` as destination, no `CONTEXT.md` / `docs/adr/` as the plan.

## Model

| kind | what it is |
|---|---|
| **spec** | parent bead. Title = name. Description = spec body. `design` holds `## GLOSSARY` and `## ADR`. Metadata `{"cairn":{"kind":"spec","milestone":"vX.Y"?}}` |
| **ticket** | child of a spec (`bd create --parent`). Tracer-bullet slice. Metadata `kind=ticket`. Blockers are `bd dep` |

Optional label `m-vX.Y` groups a cycle. Do not stamp GSD phase labels on new work.

Triage labels (exactly one state + optional category): `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`, plus `bug` or `enhancement`.

**Frontier** = `bd ready` ∩ `ready-for-agent`.

## Pipeline

`/cairn-implement [ref]` is the door. Resolve `ref` in order: bd id, spoke key (`PROJ-123`), label `m-*`, title search.

| state | do |
|---|---|
| nothing / raw idea | grill → create spec on bd → tickets → implement the frontier |
| hollow spec | grill / to-spec; write the body and `design` on that bead |
| spec full, no tickets | to-tickets → child beads + deps, label `ready-for-agent` |
| frontier tickets | implement-spec (worktrees, one PR, merge frontier as it opens) |
| one ticket | that ticket, if blockers are closed |
| epic / `m-vX.Y` | frontier of child specs |

Orchestrate the Matt skills (`grill-with-docs`, `to-spec`, `to-tickets`, `implement-spec`). **Publish through bd.** Follow `references/matt-on-beads.md`. Creating or editing `CONTEXT.md` or `docs/adr/` in this loop is an **error** — stop, write the prose on the spec bead instead.

After every `bd create` / `--claim` / `bd close`, if `.cairn/sync.json` has an enabled backend, PUSH: `gbsync.sh create|update|close <id>`.

## Commands

- `/cairn-init` — git + bd, tracker templates, plugin-root
- `/cairn-implement [ref]` — the door
- `/cairn-status` — READY / DOING / BLOCKED
- `/cairn-doctor` — health of the v5 graph
- `/cairn-sync-config` / `/cairn-sync-pull` — optional spoke

Slash names are hyphenated (`/cairn-init`). Grok registers the filename, so that is what you type there. Claude Code registers plugin commands as `plugin:filename`, so the fully-qualified form is `/cairn:cairn-init`. Official Claude docs say the plugin prefix is optional when the short name does not collide; `/cairn-init` does not collide with a builtin. If the slash menu does not resolve the hyphenated name, use the qualified form.

## Spoke map (Jira is the reference)

spec → Epic · ticket → Story/Task · `bd dep` → blocks · `m-vX.Y` → Fix Version

Same shape on the other bundled adapters. Linear is not in this version.

## Session

Claim with `bd update <id> --claim`. Close with `bd close <id> --reason="..."`. Same-day pause: comment and keep the claim. Longer pause: `--assignee "" --status open`.
