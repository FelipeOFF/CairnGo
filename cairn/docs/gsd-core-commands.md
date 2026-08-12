# What gsd-core brings, and what cairn does with it

> **Phase 37 (v1.6) changed the premise of this page.** cairn no longer
> installs gsd-core: the GSD runtime is vendored inside the plugin, and the
> vendoring closure carries **8 verbs**, not 71. So "use directly" now means
> "use an external gsd-core you installed for your own reasons" — cairn
> neither requires nor recommends one, and `/cairn:doctor` reports an
> installed gsd-core as something to uninstall. The tables below are kept
> because the DECISIONS in them are still the decisions; the counts describe
> the 1.8.0 surface they were taken against.

gsd-core ships **71** commands under `/gsd:`. This page records an explicit
decision for the **54** cairn's own loop does not already drive — wrapped, use
directly, or out of scope — so the answer to "why isn't there a `/cairn:`
version of this?" is written down rather than re-argued.

Counted against `open-gsd/gsd-core@v1.8.0`. The earlier research note said 24;
that was a partial read.

**Re-derived 2026-08-05, with the recipe at the foot of this page:** 71
commands, **31** referenced somewhere in `cairn/`, **40** referenced nowhere,
and every one of those 40 carries a decision in a table below. The referenced
figure moved from 18 to 31 when phase 26 built the thirteen wrappers.

Two arithmetic notes, because a page about counting should not be caught
miscounting. First, `18 + 54 = 72`, one more than the 71 that exist: `config`
sat in the *use directly* table while `cairn/commands/config.md` already
mentioned `/gsd:config`, so it was on both sides of the split. Second, the
thirteen wrapped commands are now referenced too — so "unreferenced" and
"has a decision here" have stopped being the same set, and only the second is
what this page promises.

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

**Status: decided, built, and then re-implemented.** Phase 26 shipped all
thirteen as wrappers around an external gsd-core. Phase 37 removed that
dependency, and the thirteen split by whether the vendored runtime carries
their verb — measured 2026-08-12, `ls cairn/gsd/commands/gsd/` → 8 files:

| implementation | count | what the command does |
|---|---|---|
| `vendored` | 1 (`discuss-phase`) | preflights, then reads and follows `${CLAUDE_PLUGIN_ROOT}/gsd/commands/gsd/discuss-phase.md` |
| `inline` | 12 (all the rest) | the command file **is** the implementation: it states the deliverable, its sections, and the decision to record |

The `implementation:` key carries that, with a closed vocabulary checked the
same way `wrap-family:` is — a typo is a named usage error, never a silent
"this is not a wrapper".

Only a `vendored` command preflights. An `inline` one does not, and that is
deliberate: `cairn-wrap.sh preflight` now resolves against the plugin's own
`gsd/` tree, so an inline command calling it would assert a delegation that
does not exist — and would install a check that cannot fail, the vacuous gate
`cairn-capability.py`'s docstring warns about. The refusal itself is intact and
still measured: `preflight spec-phase` exits 6 here, because the plugin does
not carry that verb.

**Known ceiling, written rather than hidden.** The twelve inline contracts are
thinner than the upstream workflows they replace. That is the price of closing
the window in which an old `/gsd:*` (markdown, cached 1.8.0) and a new
`/cairn:*` (bd) answer at the same time — the defect class the whole v1.5 cycle
chased. Deepening them is measured by the parity gate in phase 38, not assumed
away here.

The list of them in [the command reference](./commands.md#wrapped-gsd-commands)
is **derived from what is installed**, not typed: `cairn-wrap.sh docs`
regenerates it from each command file's `wraps:` frontmatter, and
`cairn-wrap.sh docs --check` exits `3` when the page and the disk disagree. The
table below states the *decision*; that one states the *installation*, and
they are checked against each other by the suite.

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

The marketplace segment differs per install — on a cairn-installed machine the
path is `~/.claude/plugins/cache/cairngo/gsd-core/<version>`. `installPath` in
`~/.claude/plugins/installed_plugins.json` is the one that is always right, and
it is what `cairn-wrap.sh preflight` reads.

A command that appears in that output and not in a table above has no decision
recorded yet.
