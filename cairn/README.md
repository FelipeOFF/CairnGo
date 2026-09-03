# cairn

Spec-driven development on beads. The plugin is the conductor: it orients
`/cairn-implement` at grill → spec → tickets → implement, stores the work on
`bd`, and optionally mirrors it.

## Commands

| Slash | Role |
|---|---|
| `/cairn-init` | git + bd, `docs/agents/*`, `.cairn/plugin-root` |
| `/cairn-implement [ref]` | the door |
| `/cairn-status` | READY / DOING / BLOCKED |
| `/cairn-doctor` | v5 graph health |
| `/cairn-sync-config` | enable a spoke |
| `/cairn-sync-pull` | pull the spoke into bd |

`ref` is a bd id, a spoke key (`PROJ-123`), a `m-vX.Y` label, or a title.

## Model

- **spec** — parent bead (`cairn.kind=spec`). Body in description, glossary/ADRs in `design`.
- **ticket** — child (`--parent`). `bd dep` for blockers.
- **frontier** — `bd ready` ∩ `ready-for-agent`.
- Writing `CONTEXT.md` in this loop is an error.

## Spoke (Jira is the reference)

spec → Epic · ticket → Story/Task · dep → blocks · `m-vX.Y` → Fix Version.

GitHub / GitLab / Asana / Azure Boards use the same shape. Linear is not shipped.
