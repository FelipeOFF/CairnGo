# Migrating an existing project to cairn

> **v5:** `/cairn:migrate` was removed. Bootstrap with `/cairn-init`. Claude
> Code also registers `/cairn:cairn-init`. See [commands.md](./commands.md).
> The rest of this page describes the pre-5.0 GSD migration flow.

> You already use GSD, or beads, or both — and you want cairn's unified
> lifecycle without redoing anything. This is the guide. One command does it:
>
> ```text
> /cairn:migrate
> ```
>
> `/cairn:init` also detects your situation automatically (its step 0) and
> routes here, so either entry point works.

## What migration will never do

- It never runs `/gsd:new-project` over an existing `.planning/`.
- It never writes anything before showing you a complete dry-run plan.
- It never duplicates work on a re-run (issues are stamped and recognized).
- It never closes a pre-existing issue without asking, one by one.
- It never pushes to your sync mirrors mid-run (one `/cairn:sync-pull`
  reconcile at the end — the run reminds you when sync is configured).

## Which mode are you?

`/cairn:migrate` detects this — the table is here so you know what to expect.

| You have | Mode | What happens |
|---|---|---|
| `.planning/` (GSD), no `.beads/` | **A — backfill** | Your roadmap becomes a beads graph |
| `.beads/` (beads), no `.planning/` | **B — bootstrap** | Your issue graph becomes a GSD planning setup |
| Both, but not wired together | **C — reconcile** | The two histories get matched and linked |
| Both, already wired | **W — nothing to migrate** | You're done; `/cairn:doctor` if things feel off |
| Neither | **D — greenfield** | Regular `/cairn:init` flow, nothing to migrate |

### Mode A — you use GSD, beads arrives

Reads `ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md` and every phase directory,
then creates — one `bd create` at a time, deliberately (see the safety
model):

- one **epic per phase**, with epic-level dependencies from the roadmap's
  `**Depends on**` lines;
- one **issue per requirement** (`CAT-NN`), child of its phase epic, carrying
  the acceptance text, the label pair (`m-<milestone>` + `phase-<N>`) and the
  `metadata.gsd` stamp;
- **completed phases become closed issues** (close reason: `migrated:
  completed in phase NN (see SUMMARIES)`) — your history is preserved, not
  discarded;
- the active phase's issues stay open and unclaimed — claiming is asked,
  never assumed;
- every phase gets its generated `NN-BEADS-MAP.md`;
- non-superseded plans get `beads:` frontmatter resolved from their
  `requirements:` list;
- stray `.planning/todos/pending/*` become tracked `migrated-todo` issues.

### Mode B — you use beads, GSD arrives

Reads your issue graph (`bd list --json`, dependencies, epics).

- Epics become candidate **phases**, in dependency order. No epics? cairn
  proposes phases from the topological "Stage N" layers of your blocking
  graph; open non-epic strays land in a trailing "Unscoped work" phase;
- you **confirm the phase grouping** before anything is written — it lives in
  `.cairn/migrate-plan.json` and gets edited and re-presented until you're
  happy;
- you're asked for the milestone name first (no answer defaults to `v1.0`
  with a warning), then `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md` and
  `MILESTONES.md` are generated from the graph;
- closed issues are recorded under `## Completed pre-cairn` in
  `MILESTONES.md`;
- an in-progress issue sets the active phase;
- `PROJECT.md` comes from a short seeded interview (your backlog already
  answers most of it) — the engine itself never writes it. Repos with real
  docs should consider `/gsd:onboard` or `/gsd:ingest-docs` first — migration
  will point you there when it fits;
- plans are *not* fabricated: `/cairn:plan N` creates them later, as always.

### Mode C — both installed, never wired

- Requirements whose ID appears literally in an issue title link
  automatically; already-stamped issues count as wired;
- near-matches (title similarity) are shown to you in one batch for
  confirmation — nothing fuzzy is linked silently;
- unmatched requirements are created as in mode A, parented to an existing
  phase epic when there is one (mode C never creates epics);
- orphan issues (no requirement, no phase label) are yours to route: attach
  to a phase (it then appears in that phase's map and ship gate), label it
  `backlog` (parked deliberately — `/cairn:doctor` stops flagging it), or
  leave it as-is (`/cairn:doctor`'s orphans check keeps it visible);
- a divergence report closes the run: open matched issues in completed
  phases offer a close, each one confirmed with you individually; closed
  issues in phases that never passed verification are flagged as warnings.

## Safety model

1. **Dry run first, always.** `plan` is read-only: it writes only
   `.cairn/migrate-plan.json` and prints every create, close, label and file
   write it would do, grouped by kind. Abort costs nothing.
2. **Confirmation lives in the plan file.** Sensitive steps — closing a
   pre-existing issue, accepting a fuzzy link — are marked
   `pending_confirmation` and are skipped by `apply` until confirmed; the
   prose command flips them only after asking you.
3. **Resume, don't repeat.** Progress is journaled in
   `.cairn/migrate-state.json` (JSONL, one line per completed step); an
   interrupted or partially failed run (`apply` exit 8) picks up where it
   stopped on the next `apply --yes`.
4. **Idempotent by stamp.** Issues carry `metadata.gsd.req` +
   `metadata.gsd.milestone`; re-runs update them instead of cloning them —
   and every write handler double-checks live bd state, so even a truncated
   journal never produces duplicates.
5. **Sequential creates on purpose.** `bd create --graph` stores nested
   metadata as a string (verified against bd 1.1.0), which would break the
   queryable `metadata.gsd` contract — so the engine creates issues one at a
   time. Correctness beats one-transaction elegance.
6. **No mid-run mirror pushes.** The engine's bd writes never trigger the
   mirror-push hook; you reconcile once at the end with `/cairn:sync-pull`,
   and `apply` prints the reminder when `.cairn/sync.json` exists.

## After migrating

- `/cairn:doctor` — audit the wiring end to end (requirement ↔ issue ↔ map ↔
  frontmatter, label pairs, map freshness). Run it whenever things feel off;
  `--fix-labels` repairs missing milestone labels.
- `/cairn:status` — your fused view, driven by `bd ready`: actionable,
  in-flight, blocked, and one suggested next action.
- Carry on with the plain loop — `/gsd:plan-phase`, `/gsd:execute-phase`,
  `/gsd:verify-work`, `/gsd:ship` — the installed capability makes them
  claim, close and gate bd issues by themselves (the `/cairn:plan`, `work`,
  `verify`, `ship` verbs run the same lifecycle, narrated).
- Side work goes through `/cairn:quick`: a tracked, unphased issue with
  `discovered-from` provenance — never a "quick thing" off the books.
- When the milestone wraps, `/cairn:milestone complete` gates, reconciles and
  archives it, and `/cairn:milestone new` starts the next cycle.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `bd: command not found` (exit 5) | beads binary missing | `/cairn:init` offers installers (brew / npm / curl); then re-run |
| Migration proposes re-creating existing issues | issues lack the `metadata.gsd` stamp (created outside cairn) | run mode C reconcile; confirm the matches once — stamps persist |
| Ship gate lists issues from an old milestone | legacy issues carry `phase-N` without the `m-*` pair | `/cairn:doctor --fix-labels` (or `cairn-relabel.sh pair --milestone <m>`) |
| `apply` exited 8 | one step failed mid-run | fix the cause (stderr names the step), re-run `apply --yes` — it resumes from the journal |
| External mirror out of date after migration | mirror pushes are suppressed during the run by design | run `/cairn:sync-pull` once; the end-of-run summary reminds you |
| detect says **W** but tracking feels wrong | wired, but drifted | `/cairn:doctor` — its nine checks pinpoint the drift |
