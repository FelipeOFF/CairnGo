---
description: Adopt an existing repo into cairn — detect GSD/beads state, dry-run a plan, confirm with the user, apply with resume journaling
group: health
---

Migrate an existing repo onto the cairn conventions (label pair + metadata
stamp + `beads:` frontmatter + generated maps). All writes go through the
deterministic engine — never hand-create issues or `.planning/` files during a
migration.

Hard rule, every mode: **never run `/gsd:new-project` or `/gsd:new-milestone`
over an existing `.planning/`** — the engine backfills; a GSD interview would
re-interrogate at best and clobber at worst.

## 0. Detect

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-migrate.sh" detect
```

Line 1 is the state letter, line 2 the description (`--json` for details):

- **A** — `.planning/` only → GSD-only backfill (mode A below)
- **B** — `.beads/` only → beads-only bootstrap (mode B below)
- **C** — both present, unwired → wire-up / reconcile (mode C below)
- **W** — both present, already wired → tell the user, suggest `/cairn:doctor`, **stop**
- **D** — neither → nothing to migrate; route to `/cairn:init`, **stop**

Whatever the state letter: when the detect JSON (`detect --json`) carries
`external.jira` with `detected: true`, the repo already references Jira cards
(`prefixes` lists the issue-key prefixes found). Tell the user and suggest
`/cairn:sync-config` after the migration — it pre-fills the Jira backend from
this detection and can import the existing cards. Never configure sync or run
an import on your own; migration itself stays mirror-silent (see "Always").

Exit codes for `plan`/`apply` below: `0` ok, `2` usage / wrong mode / no plan /
abort, `5` bd unavailable (install via `/cairn:init` step "Ensure beads",
then retry), `8` partial apply failure.

## Mode A — GSD-only: backfill beads from `.planning/`

1. Dry-run:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-migrate.sh" plan
   ```
   Writes `.cairn/migrate-plan.json` and prints a summary grouped by step kind:
   epics per ROADMAP phase (+ deps from `**Depends on**`), one child issue per
   requirement (stamped + labeled), closes for completed phases, `beads:`
   frontmatter appends, `migrated-todo` issues from `.planning/todos/pending/`,
   and per-phase map regeneration.
2. Present the plan and ask the user to confirm before applying. On a huge
   plan, summarize: counts per step kind plus the first few examples of each —
   don't paste hundreds of steps.
3. On yes:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-migrate.sh" apply --yes
   ```
   Exit `8` = partial failure: failed steps are listed on stderr and the
   journal (`.cairn/migrate-state.json`) records what completed — fix the
   cause and re-run `apply --yes`; it resumes without duplicating (handlers
   also dedup against live bd state on `(gsd.req, gsd.milestone)`).
4. Finish with `/cairn:doctor` to confirm the wiring.

## Mode B — beads-only: bootstrap `.planning/` from the backlog

1. Dry-run: `plan --milestone vX.Y` — ask the user for the milestone first;
   with no `--milestone` mode B has no `.planning/` to infer from and defaults
   to `v1.0` with a warning. If
   generated docs already exist and the user wants them replaced, re-plan with
   `--force`.
2. Present the **proposed phase grouping** for editing before anything is
   written: epics become phases in dependency order (children = that phase's
   requirements), open non-epic strays land in a trailing "Unscoped work"
   phase, and with no epics the plan falls back to topological "Stage N"
   layers. The grouping lives in the plan file: each `create_issue` /
   `update_issue` / `link_issue` step carries `phase`, `labels`
   (`m-<milestone>`, `phase-<N>`) and `gsd` stamp, and the `write_file` steps
   hold the matching REQUIREMENTS.md / ROADMAP.md / STATE.md content. To move
   an issue between phases per the user's answers, edit those fields **and**
   the corresponding `write_file` content in `.cairn/migrate-plan.json`, then
   re-present until confirmed.
3. On yes: `apply --yes`. The engine never fabricates PLAN.md and never writes
   PROJECT.md — closed issues are recorded under `## Completed pre-cairn` in
   MILESTONES.md, and maps land in the created phase dirs.
4. **PROJECT.md — short seeded interview.** If the repo has rich existing docs
   (ADRs, PRDs, specs, a substantial README), point the user to
   `/gsd:ingest-docs` or `/gsd:onboard` first instead. Otherwise ask 3–4
   questions max — what is this project, why does it exist, where does it
   stand today — and write PROJECT.md yourself from the answers plus what the
   backlog already shows. Explicitly do **not** run `/gsd:new-project`.
5. Finish with `/cairn:doctor`. Plans come later: `/cairn:plan <N>` produces
   each PLAN.md and its `beads:` frontmatter.

## Mode C — both present, unwired: link and reconcile

1. Dry-run: `plan`. Issues whose title contains a literal `CAT-NN` token are
   auto-linked; already-stamped issues count as wired; unmatched requirements
   become mode-A-style creates (parented to an existing phase epic when one
   exists — mode C never creates epics).
2. **Fuzzy candidates** (title similarity ≥ 0.6) land as `link_candidate`
   steps with status `pending_confirmation` — apply skips them until
   confirmed. Present them to the user as one batch (issue title vs
   requirement title, with the score); for each one the user accepts, set
   `params.confirmed: true` on that step in `.cairn/migrate-plan.json`.
   Rejected candidates stay skipped and the requirement stays unwired — note
   it so the user can create it properly later.
3. **Orphans** — non-closed issues with no requirement match and no `phase-*`
   label are listed under `orphans` (default action `report`). Ask the user
   how to route each: attach to a phase (`"action": "attach-to-phase-<N>"`),
   `"label-backlog"`, or leave as `report`.
4. **Divergence report** — show it. Open matched issues in complete phases get
   `close_issue` steps gated behind `pending_confirmation`: confirm **each
   close of a pre-existing issue per-issue** with the user before flipping
   `confirmed` (it may be mirrored externally). Closed issues in phases
   lacking a passed VERIFICATION appear as warnings only — relay them.
5. After flipping the confirmed steps and orphan actions in the plan file:
   `apply --yes`. Re-runs resume from the journal, so confirming more steps
   later and re-applying is safe.
6. After the confirmations landed, run `plan` once more and apply if it
   surfaces new steps: an issue wired via a just-confirmed fuzzy candidate
   only receives its divergence `close_issue` offer on this second pass
   (close offers are computed at plan time from already-stamped issues).
7. Finish with `/cairn:doctor`.

## Always

- When `.cairn/sync.json` exists (sync configured), remind the user to run
  `/cairn:sync-pull` after the migration (`apply` prints this too) — migration
  writes must reconcile with the external mirror, not push into it mid-run.
- Suggest `/cairn:doctor` as the closing step of every mode.
