---
description: Run every remaining phase hands-off — the full cairn loop per phase (map → plan → claim → execute → close → verify), doctor between phases, ship gate at the end
argument-hint: "[start-phase] [--interactive]"
---

Run the milestone to completion under the `cairn` conventions, phase by phase,
without checkpointing back to the user between steps. This is the beads-aware
counterpart of `/gsd:autonomous`: every phase passes through the full bd
bookkeeping (claim → in_progress → close → map refresh), whether or not the
cairn GSD capability is installed — its hooks are idempotent with these steps.

## 0. Pre-flight (stop here if it fails)

1. `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh"` — a ✗ failure
   (exit 7) **stops** the run before it starts: report and route each finding
   per `/cairn:doctor`. Warnings are noted and do not block. A
   **not-applicable** note (exit 0 with one side missing — e.g. `.planning/`
   without `.beads/`) also **stops**: route to `/cairn:migrate` to wire the
   missing side, or offer plain `/gsd:autonomous` instead.
2. bd must be available (doctor exit 5 means it isn't) — without bd there is
   no "autonomous through beads": **stop** and offer plain `/gsd:autonomous`
   instead.
3. Resolve the pending phases and the order, **from the status model rather
   than by reading ROADMAP.md yourself**:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-status.sh" --json
   ```
   `phases[]` gives each pending phase its title, state on disk and
   `blocked_by`; `next_commands[]` gives the order and the reason for it;
   `parallelism` gives what could run at the same time. Start at
   `$ARGUMENTS` when given, else at the first entry of `next_commands`.
   Resolve the active milestone from `milestone`.
4. **Announce the run, including the order you chose and why.** Not just the
   phase list: state the order, the reason each phase sits where it does
   (straight from `next_commands[].reason`), and what `parallelism.note` says
   could run concurrently — plus the fact that this run executes them in
   sequence anyway, so the operator can stop you and split the work across
   agents or worktrees if that is worth doing. An order chosen silently is an
   order nobody can disagree with before it costs an hour.

   When `parallelism.declared` is false, say so: no dependencies are recorded
   anywhere in the roadmap, so the order is phase number and nothing more.

   Then go. No further questions: gray areas during planning resolve to
   sensible defaults recorded as Claude's Discretion in each phase's
   CONTEXT.md.

   **`--interactive` inverts that last sentence**, and only that one. The
   pre-flight, the order, the stop rules and every bd step are unchanged; what
   changes is that a genuine design decision is put to the user instead of
   being recorded as Claude's Discretion. Step 0 of each phase below is the
   mechanism.

## Per phase N (in order)

0. **Discuss (only under `--interactive`)** — if the phase has no
   `NN-CONTEXT.md`, run `/gsd:discuss-phase N` **before** planning it.
   Invoke it here, in the autonomous loop, rather than telling the user to run
   it themselves.

   This is allowed, and the reason matters. GSD's `plan-phase` workflow forbids
   invoking discuss-phase as a nested Skill/Task call, because
   `AskUserQuestion` misbehaves in a subcontext (gsd-core #1009) — that
   prohibition is about **plan-phase** nesting it one level down. The
   autonomous loop runs in the top-level session, so a `Skill` call from here
   is the same context the user's own `/gsd:discuss-phase` would run in, and
   the questions work. Do not hand the command back to the user as if you
   could not run it.

   **Discuss at the phase's turn, never in a batch up front.** It is tempting,
   with five pending phases, to discuss all five before planning any — do not.
   A CONTEXT.md is a set of locked decisions, and decisions locked for phase
   N+2 are taken against a codebase that phase N is about to change: the
   discussion is held over a guess, and the guess is then recorded as settled.
   That is the same failure this whole plugin is built to catch — a record
   that claims more certainty than anything corroborates.

   One narrow exception, and it must be checked rather than assumed: a phase
   may be discussed ahead of its turn when `blocked_by` is empty **and** its
   roadmap entry says it needs no research during planning. Anything else
   waits for its turn in the loop.

   Without `--interactive`, skip this step entirely — gray areas resolve to
   Claude's Discretion, as above.

1. **Plan** — `/cairn:plan N`. Without `--interactive`, run it
   non-interactively (skip discussion questions; record assumptions instead);
   under `--interactive`, step 0 has already produced the CONTEXT.md that
   plan-phase would otherwise have prompted about. This regenerates the beads
   map, runs `/gsd:plan-phase N`, reconciles divergence (CONTEXT wins) and sets
   each PLAN.md's `beads:` frontmatter.
2. **Work** — `/cairn:work N`: for each plan, claim its `beads:` ids
   (`bd update <id> --claim`) **before starting it**, run
   `/gsd:execute-phase N`, close ids on verified completion
   (`bd close <id> --reason="…"`), done-check with the pair label
   `m-<milestone>,phase-N` (unpadded — `phase-3`, never `phase-03`), refresh
   the map.
3. **Verify** — `/cairn:verify N`: `/gsd:verify-work N` cross-checked against
   bd; reconcile mismatches (close the issue, or reopen the work). A gap that
   reconciliation cannot close is a stop rule.
4. **Phase checkpoint** —
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh"` (failure stops the
   run), then `bd list -l m-<milestone>,phase-N --all` must show **no issue
   with a status other than `closed`** — the same semantics the ship gate
   enforces later (`--status open` alone would miss `in_progress`/`blocked`
   stragglers and defer the failure to the very end of the run). Emit a
   one-block phase report (plans executed, issues closed, doctor verdict)
   and continue to the next phase.

## Stop rules (autonomous ≠ blind)

Stop immediately, report where you are (phase, step, offending ids/output),
and leave the repo consistent — release claims that no longer reflect active
work (`bd update <id> --assignee "" --status open`) or close what is truly
done — when:

- doctor reports a ✗ failure (exit 7) at any checkpoint;
- a plan's execution fails and cannot be recovered within the phase;
- verification finds a gap that reconciliation cannot close;
- bd becomes unavailable mid-run (exit 5 from any script) — claims and closes
  can no longer be trusted;
- the ship gate blocks (exit 6).

**Stop rules override the delegated commands' degradation paths.** During an
autonomous run, the exit-5 fallbacks the individual commands document (e.g.
`/cairn:plan`'s "fall back to reading the existing map file") do **not**
apply: any exit 5 from `cairn-map`/`cairn-doctor`/`cairn-gate`, or any bd
failure, halts the run instead of degrading it — silent degradation is
exactly what autonomous mode must not do.

The resume path after a stop is the ordinary loop: fix the reported problem,
then re-run `/cairn:autonomous` — phases already marked complete in
ROADMAP.md are detected and skipped. When resuming a phase that was
interrupted mid-way, **skip the claim for ids already `closed`** by the
earlier partial pass: `bd update <id> --claim` on a closed issue errors
("not claimable: status closed") — during a resume that error is expected
and benign, not an execution-failure stop rule.

## After the last phase

1. `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-gate.sh"` — exit 6 **stops**
   with the offending ids (a phase marked done still has non-closed issues).
   Green: report the milestone summary — phases run, plans executed, issues
   closed, and any unphased `quick` issues still open.
2. Do **not** push. Hand off with `/cairn:ship` as the suggested next step —
   the push stays a human decision, and the pre-push shim enforces the same
   gate outside the agent anyway.

Notes:

- With the cairn GSD capability installed, plain `/gsd:*` already claims and
  closes issues via hooks — every bd step above is idempotent (re-claiming
  your own issue and re-closing a closed one are no-ops), so the run is safe
  either way.
- `quick`-labeled issues are unphased and never block a phase; they stay
  visible in `/cairn:status`'s ready list.
