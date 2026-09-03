# Issue tracker: beads (bd)

Issues and specs for this repo live in **beads** (`bd`). bd is the hub.
Optional spokes (Jira, GitHub, GitLab, Asana, Azure Boards) configured in
`.cairn/sync.json` are mirrors. Never treat a spoke as the source.

## Conventions

- **Create a spec**: `bd create --title "..." --type=epic --labels=enhancement,ready-for-agent --metadata '{"cairn":{"kind":"spec"}}'` with the spec body as description and glossary/ADRs as design.
- **Create a ticket**: `bd create --title "..." --type=task --parent=<spec-id> --labels=ready-for-agent --metadata '{"cairn":{"kind":"ticket"}}'`.
- **Read**: `bd show <id>`
- **List open**: `bd list --status=open`
- **Frontier**: `bd ready` then keep `ready-for-agent`
- **Comment**: `bd comment <id> "..."`
- **Labels**: `bd update <id> --add-label "..."` / `--remove-label "..."`
- **Close**: `bd close <id> --reason="..."`
- **Block**: `bd dep add <issue> <depends-on>`

## Pull requests as a triage surface

**PRs as a request surface: no.**

## When a skill says "publish to the issue tracker"

Create a beads issue (`bd create`). Then, if sync is enabled, `gbsync.sh create <id>`.

## When a skill says "fetch the relevant ticket"

`bd show <id>`. Spoke keys (`PROJ-123`) resolve via `.cairn/id-map.json` or `external_ref`.

## Wayfinding / maps

The **map** is a spec epic. Child tickets are `bd create --parent=<spec-id>`.
Blocking is native `bd dep`. A ticket is unblocked when every blocker is closed
(`bd ready`). Claim with `bd update <id> --claim`.
