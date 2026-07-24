---
name: cairn
description: Use when working in a repo that has BOTH GSD (.planning/) and beads (.beads/) — wires phase planning and execution to the bd issue tracker so /gsd:* commands create, claim, and close tracked work. Defines the per-phase map, plan frontmatter, label convention, lifecycle hooks, and precedence rules.
---

# GSD ↔ beads integration

Wire the GSD planning workflow (`/gsd:*`, `.planning/`) to the beads issue
tracker (`bd`, `.beads/`) so phase planning and execution close tracked work.

## Activation gate

Apply this skill **only when the repo contains BOTH**:
- `.planning/` (GSD is in use), AND
- `.beads/` (beads is initialized — confirm with `bd ready` or `ls .beads/`).

If either is absent, this skill does not apply. Never run `bd` in a repo
without `.beads/`, and never create `.planning/` just to satisfy this skill.

When both are present, **prefer `bd` for ALL task tracking** — do NOT use
TodoWrite/TaskCreate or markdown TODO lists for project work. Run `bd prime`
once per session for command reference and the session-close protocol.

## The model

GSD owns the *plan* (roadmap → phases → PLAN.md). beads owns the *work items*.
They are linked by a per-phase map file and per-plan frontmatter.

- **Phase ↔ issues:** each GSD phase `NN` maps its requirement IDs to bd issue
  IDs in a `{NN}-BEADS-MAP.md` inside the phase directory
  (`.planning/phases/NN-<slug>/NN-BEADS-MAP.md`).
- **Label:** every bd issue belonging to phase `N` carries the label
  `phase-N`. List a phase's work with `bd list -l phase-N`.
- **Plan frontmatter:** every `PLAN.md` carries a `beads:` list of the bd IDs
  it advances:
  ```yaml
  beads: [proj-7hp, proj-4qv]   # REQ-01/02 — provisioner; REQ-04 — registry
  ```

### `NN-BEADS-MAP.md` format

```markdown
# Phase NN — <name> ↔ beads map

> Precedence: where a bd issue conflicts with this phase's CONTEXT.md,
> CONTEXT.md wins. Divergent issues are flagged ⚠ and updated, not followed.

| REQ | Requirement | bd issue(s) | bd status | Notes / divergence |
|-----|-------------|-------------|-----------|--------------------|
| ... | ...         | `proj-xxx`  | OPEN      | ...                |

## Gaps
Requirements with no bd issue yet → create them (see lifecycle below).
```

## Lifecycle (hook into GSD commands)

- **`/gsd:new-project` / `/gsd:new-milestone`** — after the roadmap is written,
  create one bd issue per requirement (`bd create`), label each `phase-N`, and
  write each phase's `NN-BEADS-MAP.md`. Capture dependencies with bd's
  dependency support where the roadmap implies ordering.
- **`/gsd:plan-phase N`** — READ the phase's `NN-BEADS-MAP.md` first (resolve
  the phase directory by its numeric prefix — `3` and `03` are the same phase,
  and the directory name may carry a project-code prefix). Reconcile any
  divergence between existing bd issues and the phase `CONTEXT.md` (CONTEXT
  wins — flag ⚠ and update the issue). Create issues for unmapped requirements.
  Set the `beads:` frontmatter on each generated `PLAN.md`.
- **`/gsd:execute-phase N` / `/gsd:execute-plan`** — for each plan, on start:
  `bd update <id> --claim` for every id in that plan's `beads:` frontmatter
  (`--claim` atomically assigns the issue and sets its status to
  `in_progress` — no separate `--status` call needed). On successful
  completion + verification:
  `bd close <id> --reason="<1-2 sentence summary>"`.
- **`/gsd:ship` / session close** — before pushing, confirm every bd issue for
  completed plans is closed (`bd list -l phase-N --status open` should be empty
  for finished phases). Then push.

## Precedence

When a bd issue description conflicts with GSD phase docs
(`CONTEXT.md`, `PLAN.md`, `ROADMAP.md`), **the GSD doc wins** — it is the newer,
human-locked source of truth. Update the bd issue to match (with a dated
reconciliation note pointing at the GSD doc); do not silently follow the stale
issue.

## Bootstrap a new project

Run the `/cairn:init` command (or `cairn-init.sh`) to ensure `git` +
`bd init` are done so this skill activates, then run `/gsd:new-project` to
create `.planning/`.

## Mirror to external tools (optional)

If the repo also has `.cairn/sync.json` with an enabled backend, bd issues
are mirrored two-way (hub-and-spoke) to GitHub Issues / GitLab / Jira / Asana /
Azure Boards — see the **`cairn-sync`** skill. PUSH the matching mirror right
after each bd lifecycle write (`create` / `--claim` / `close`); reconcile
external edits back with `/cairn:sync-pull`. Configure via
`/cairn:sync-config`.

## Project-specific extensions

A project's own `CLAUDE.md` may extend this with project-specific steps
(e.g. mirroring issue status to a GitHub Project, custom completion-note
templates, conventional-commit `Closes <id>` trailers). Project `CLAUDE.md`
**overrides** this skill on any conflict.
