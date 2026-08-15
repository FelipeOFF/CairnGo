---
name: cairn
description: Use when working in a repo that has `.beads/` — cairn plans and executes phases with the bd issue tracker as the single owner of state, so planning, execution and verification create, claim and close tracked work. Defines the label convention, the metadata stamp, the record kinds, lifecycle hooks and precedence rules. A `.planning/` directory, when present, is a GSD project waiting to be imported — never a source cairn writes to.
---

# cairn — the tracker owns the state

Plan and execute phases with `bd` (beads) as the single owner of the project's
state: the roadmap, the phases, the requirements, the plans, the summaries and
the verdicts all live as tracked work, and nothing has to be kept in agreement
with a document on disk.

## Activation gate

Apply this skill when the repo contains **`.beads/`** (confirm with `bd ready`
or `ls .beads/`). That is the whole gate. Never run `bd` in a repo without
`.beads/` — `/cairn:init` creates it.

**`.planning/` is not part of the gate, and this is the point.** A repo that
carries one is a GSD project whose content has not been imported yet: read it
once, with `/cairn:migrate`, and never again. cairn does not write markdown —
not a roadmap, not a plan, not a summary, not a map. If you find yourself
about to create `.planning/` to satisfy something here, the something is wrong.

**Prefer `bd` for ALL task tracking** — never TodoWrite/TaskCreate or markdown
TODO lists for project work. Run `bd prime` once per session for the command
reference and the session-close protocol.

## The model

There is one owner. `bd` holds the work items AND the planning record; a
phase, a requirement and a plan are all beads, distinguished by what they
carry.

- **Labels (the pair):** every issue that belongs to a CYCLE carries BOTH
  `m-<milestone>` (e.g. `m-v1.0`) AND `phase-<N>` (unpadded — `phase-3`,
  never `phase-03`). Phase numbers collide across milestones (v1.0 and v1.1
  each have a phase 1), so the milestone label disambiguates. List a phase's
  work with `bd list -l m-<milestone>,phase-<N>` — a comma list to `-l` is
  AND. *Legacy repos* whose issues carry only `phase-N`: pair them once with
  `${CLAUDE_PLUGIN_ROOT}/scripts/cairn-relabel.sh pair --milestone <m>`.

  Two failure modes around this label, and both have bitten:

  - **A bare version label is not a milestone label.** `v1.6` without the
    `m-` prefix matches nothing: not `bd list -l m-v1.6`, not any cycle
    listing, not the board. The epic `CairnGo-dhl` carried one and survived
    the entire close of v1.6 — 72 issues closed, release shipped — before
    anyone found it by hand. `/cairn:doctor` now names this as its own
    finding, separate from a broken pair, because the fix is different:
    rename the label, don't pair it.
  - **Backlog work carries NEITHER label, and that is the convention, not an
    oversight.** An issue outside every cycle is marked as such by the
    ABSENCE of `m-*` and `phase-N` — that is what keeps it out of a cycle's
    listings and out of "what is left to do" on the board. Do not stamp a
    backlog item with the current milestone to make it visible; visibility
    is what the `backlog` label and the READY lane are for. The doctor
    leaves these alone by construction.
- **Metadata stamp:** every cairn-managed issue carries
  `{"gsd": {"req": "CAT-NN", "phase": N, "milestone": "vX.Y"}}`, set via
  `bd create`/`bd update` `--metadata`. Updates are **read-modify-write**:
  `--metadata` replaces the whole `gsd` object, so read it from
  `bd show <id> --json`, change the one field, write the full object back.
  The pair `(gsd.req, gsd.milestone)` is the **dedup key** — never create a
  second issue for the same requirement in the same milestone.
- **Who is who inside a phase.** Four kinds of bead wear the same `phase-N`
  label, and telling them apart is the convention, not a heuristic:

  | | carries | is |
  |---|---|---|
  | requirement | `gsd.req` | the requirement itself |
  | plan record | label `plan-NN` | one wave of the phase |
  | child | an id with the parent's suffix (`proj-9c0h.3`) | subordinate work |
  | **phase carrier** | none of the above | the phase itself — its name is the title, its goal the description |

  The `bd` JSON carries no `parent` key (measured, bd 1.1.0), which is why
  hierarchy is read off the id and never off a field.

## The records — what used to be documents

Planning prose is recorded on beads through one boundary,
`${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh`, which writes the structured
fact to bd and writes **no file at all**:

```bash
cairn-record.sh <kind> --phase <N> [--plan <P>] [--issue <ID>] <<'BODY'
…the prose…
BODY
```

| kind | lands on | as |
|---|---|---|
| `plan` | a `phase-N` + `plan-NN` bead | `description` — opens the record |
| `summary` | that same bead | `notes`, and **closes** it |
| `context`, `research`, `patterns`, `spec`, `ui-spec`, `ai-spec` | the phase carrier | `design` |
| `verification` | the phase carrier | `acceptance_criteria` |
| `review`, `log` | the phase carrier | `notes`, appended |

Two things about this table are load-bearing:

- **A summary is not a new artifact.** It is the close of the record the plan
  opened, which is why `summary` takes the same `--phase`/`--plan` pair and
  why the bead count does not rise when one is recorded.
- **`append` and `set` are not interchangeable.** `log` and `review` append
  because UAT sessions and audit trails accumulate; a `set` would erase the
  previous entry on every write.

The script writes the fact; the **prompt layer** indexes the prose with
`ctx_index(content: …, source: "gb/<bd_id>/<phase>")`. The split is deliberate
— context-mode has no CLI, so a script cannot index.

### Asking about a phase

A question about a phase is a question to bd, and the answer is already there:

```bash
bd list -l "phase-<N>" --all --limit 0 --json | jq -r '.[].description'  # the plans
bd list -l "phase-<N>" --all --limit 0 --json | jq -r '.[].notes'        # the summaries
bd show <phase-carrier> --json | jq -r '.design, .acceptance_criteria'   # context, research, verdict
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>                    # the phase, as a table
```

`cairn-map` **prints** the requirement↔issue table; it does not write it.
There is no `NN-BEADS-MAP.md`, no generated markers, and nothing that can go
stale — the view is regenerated by the act of asking for it.

## Lifecycle

- **`/cairn:new` / `/cairn:milestone new`** — create one bd issue per
  requirement following the convention above (label pair + metadata stamp,
  dedup on `(gsd.req, gsd.milestone)`), plus a **phase carrier** per phase, and
  capture ordering with bd dependencies.
- **`/cairn:plan N`** — record the phase's context and research on the carrier,
  then one `plan` record per wave. Where a bead conflicts with the phase's
  recorded context, the context wins — update the bead with a dated
  reconciliation note.
- **`/cairn:work N` / execute** — on start, `bd update <id> --claim` for the
  plan's beads (`--claim` assigns and sets `in_progress` atomically). On
  success, close the plan's record with its summary
  (`cairn-record.sh summary --phase N --plan P`, body on stdin) and
  `bd close <id> --reason="<1-2 sentence summary>"` the requirements it
  delivered.
- **`/cairn:ship` / session close** — before pushing, confirm every bead of a
  finished phase is closed: `bd list -l m-<milestone>,phase-<N> --all` must
  show nothing non-closed (open, in_progress or blocked all block the ship).

Work discovered mid-phase that belongs to no plan → `/cairn:quick`: a
`quick`-labeled, unphased issue with a `discovered-from` dep on the active one.

### Pause / resume

- **Session end** — for each in_progress issue assigned to you: resuming
  same-day → add a dated note
  (`bd comment <id> "paused YYYY-MM-DD: <where it stands, what's next>"`) and
  **keep the claim**; pausing indefinitely → release it
  (`bd update <id> --assignee "" --status open`) so it returns to the ready
  pool instead of looking owned. The session-stop hook warns about leftover
  claims either way — don't ignore it silently.
- **Resuming** — `bd update <id> --claim` (idempotent when already yours).

## Precedence

**The bead is the source.** Its description, design, notes and acceptance
criteria are what the phase says it is, and nothing on disk overrides them.

The one exception is the import: while a `.planning/` directory is still
waiting to be migrated, its documents are the INPUT and they win — that is
what `/cairn:migrate` reads them for. Once imported, they are history; a
"reconciliation" that copies a stale document back over a bead is the failure
mode this rule exists to prevent.

## Bootstrap and adoption

- **New project** — `/cairn:init` (git + `bd init`), then `/cairn:new`.
  Nothing creates `.planning/`.
- **Existing GSD project** — `/cairn:migrate` (detect → plan → apply) imports
  the roadmap, the requirements and the phase tree into bd. Route every
  "unmigrated GSD" nudge there, and never run a project-creation command over
  a `.planning/` that has not been imported.
- **Health** — `/cairn:doctor` audits requirement↔issue coverage, label pairs,
  claims and recoverability. Never hand-create an issue for an existing
  requirement without the metadata stamp: an unstamped issue is invisible to
  the dedup key, so a later migrate or plan run duplicates it.

## Mirror to external tools (optional)

If the repo also has `.cairn/sync.json` with an enabled backend, bd issues are
mirrored two-way (hub-and-spoke) to GitHub Issues / GitLab / Jira / Asana /
Azure Boards — see the **`cairn-sync`** skill. PUSH the matching mirror right
after each bd lifecycle write (`create` / `--claim` / `close`); reconcile
external edits back with `/cairn:sync-pull`. Configure via
`/cairn:sync-config`.

## Project-specific extensions

A project's own `CLAUDE.md` may extend this with project-specific steps (e.g.
mirroring issue status to a GitHub Project, custom completion-note templates,
conventional-commit `Closes <id>` trailers). Project `CLAUDE.md` **overrides**
this skill on any conflict.
