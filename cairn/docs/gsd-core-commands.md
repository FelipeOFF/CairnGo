# What gsd-core brings, and what cairn does with it

gsd-core ships **71** commands under `/gsd:`. cairn's own wrappers reference 18
of them. This page records an explicit decision for each of the remaining **54**
— wrapped, use directly, or out of scope — so the answer to "why isn't there a
`/cairn:` version of this?" is written down rather than re-argued.

Counted against `open-gsd/gsd-core@v1.8.0`. The earlier research note said 24;
that was a partial read. The real figure is 54, of which 41 are not mentioned
anywhere in cairn today.

## The rule

A command earns a `/cairn:*` wrapper when running it **changes work that beads
has to know about** — a phase appears or disappears, a `PLAN.md` is written that
needs `beads:` frontmatter, a completed phase is re-opened for audit, or issues
would be orphaned. Everything else is a perfectly good GSD command and cairn
adds nothing by aliasing it.

cairn's value is the fusion, not a second name for someone else's command.

## Wrapped as `/cairn:*` — 13

These touch phase or milestone state, so bd must follow.

| Command | What it does | Why it needs a wrapper |
|---|---|---|
| `phase` | CRUD for phases in ROADMAP.md | Removing or renumbering a phase orphans every issue carrying its `phase-<N>` label. The strongest case on this list. |
| `discuss-phase` | Gathers phase context before planning | Produces the CONTEXT.md that `/cairn:plan` treats as authoritative on divergence; the two must agree about which phase they mean. |
| `spec-phase` | Produces SPEC.md with ambiguity scoring | A phase gains a requirements surface; issues get stamped from it. |
| `mvp-phase` | Plans a phase as a vertical MVP slice | Writes PLAN.md, which must carry `beads:` frontmatter. |
| `ui-phase` | Produces UI-SPEC.md for a frontend phase | Phase artifact; its requirements need issues like any other. |
| `ai-integration-phase` | Produces AI-SPEC.md for an AI phase | Same. |
| `ultraplan-phase` | Offloads planning to the cloud, imports back | The imported PLAN.md arrives without `beads:` frontmatter — precisely the gap the plan wrapper closes. |
| `plan-review-convergence` | Replans until review concerns resolve | Rewrites PLAN.md, so the id linkage has to be re-resolved. |
| `validate-phase` | Fills validation gaps on a completed phase | Re-opens finished work; issues closed by the ship gate may need reopening. |
| `secure-phase` | Retroactive threat-mitigation verification | Same shape as validate-phase. |
| `cleanup` | Archives phase dirs from completed milestones | `NN-BEADS-MAP.md` lives in those dirs; archiving them without the maps breaks the record. |
| `review-backlog` | Promotes backlog items into the active milestone | Creates tracked work, which must arrive as bd issues with the label pair. |
| `audit-milestone` | Audits a milestone before archiving | Belongs to the `/cairn:milestone complete` gate, which already refuses to archive over non-closed issues. |

**Status: decided, not yet built.** This phase records the decision; the
wrappers are follow-up work. Until they exist, run these as `/gsd:*` and then
`/cairn:doctor` — it catches the drift they would have prevented (orphans,
stale maps, missing `beads:` frontmatter).

## Use the GSD command directly — 39

Nothing here changes what beads tracks, so a wrapper would be an alias and one
more thing to keep in sync.

| Command | What it does | Note |
|---|---|---|
| `next` | Routes to the next GSD action | `/cairn:status` is cairn's answer, and it reconciles bd against STATE.md. |
| `health` | Diagnoses planning-directory health | `/cairn:doctor` is the cairn-aware equivalent; run both. |
| `add-tests` | Generates tests from UAT criteria | Produces code, not tracked work. |
| `code-review` | Reviews a phase's changed source | Read-only over the diff. |
| `audit-fix` | Find → classify → fix → test → commit | Operates on code; issues it should file are `/cairn:quick`'s job. |
| `audit-uat` | Cross-phase audit of outstanding UAT | Reporting. |
| `eval-review` | Audits an AI phase's evaluation coverage | Reporting. |
| `ui-review` | Retroactive visual audit | Reporting. |
| `review` | Cross-AI peer review of plans | Read-only over plans. |
| `docs-update` | Generates docs verified against the codebase | Documentation output. |
| `map-codebase` | Parallel mappers → `.planning/codebase/` | Descriptive output; no work items. |
| `extract-learnings` | Pulls decisions and lessons from artifacts | Reporting. |
| `milestone-summary` | Project summary for onboarding | Read-only. |
| `forensics` | Post-mortem for failed workflows | Diagnostic. |
| `explore` | Socratic ideation | Pre-commitment thinking; `/cairn:quick` covers anything that becomes work. |
| `sketch` | Throwaway HTML mockups | Same. |
| `spike` | Experiential exploration of an idea | Same. |
| `capture` | Captures ideas, tasks, notes, seeds | Overlaps `/cairn:quick`, which already tracks side work. |
| `import` | Ingests external plans with conflict detection | `/cairn:migrate` owns adoption of existing repos. |
| `inbox` | Triages GitHub issues and PRs | `/cairn:sync-*` owns the external-tracker direction. |
| `thread` | Persistent cross-session context threads | `/cairn:remember` / `/cairn:recall` are cairn's memory surface. |
| `mempalace-capture` | Files an artifact into MemPalace | Same. |
| `mempalace-recall` | Recalls decisions from MemPalace | Same. |
| `profile-user` | Developer behavioural profile | Personal, not project state. |
| `workspace` | Manage isolated workspace environments | Environment management. |
| `workstreams` | Parallel workstream management | Environment management; cairn tracks parallelism through bd dependencies. |
| `manager` | Interactive multi-phase command centre | A UI over commands cairn already wraps. |
| `undo` | Safe git revert using the phase manifest | Git-level; reverting code does not reopen issues on its own — check `/cairn:doctor` after. |
| `config` · `settings` · `surface` | GSD configuration and skill surfacing | GSD's own configuration. |
| `update` | Updates GSD | Tool maintenance. |
| `fast` | Trivial inline task, no planning | Deliberately overhead-free; adding tracking would defeat it. |
| `ns-context` · `ns-ideate` · `ns-manage` · `ns-project` · `ns-review` · `ns-workflow` | Namespace menus grouping the above | Menus, not operations. Wrapping a menu of commands cairn has already triaged would be circular. |

## Deliberately out of scope — 2

| Command | Why not |
|---|---|
| `pr-branch` | It builds a PR branch by **filtering out `.planning/` commits**. In cairn, `.planning/` is the record — the roadmap, the phase artifacts and the beads maps are the point of the change, not noise to strip. Adopting it would fight the model. |
| `graphify` | Builds a second knowledge graph in `.planning/graphs/`. cairn already ships context-mode as its memory layer and scopes it by issue and phase; two graphs would compete for the same job with no reconciliation between them. |

## Keeping this honest

The counts above are derived, not remembered. To re-derive after a gsd-core
bump:

```bash
GC=~/.claude/plugins/cache/gsd-core/gsd-core/<version>
ls "$GC/commands/gsd/" | sed 's/\.md$//' | sort > /tmp/all.txt
grep -rhoE "/gsd:[a-z0-9-]+" cairn/ | sed 's|/gsd:||' | sort -u > /tmp/ref.txt
comm -23 /tmp/all.txt /tmp/ref.txt
```

A command that appears in that output and not in a table above has no decision
recorded yet.
