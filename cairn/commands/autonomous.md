---
description: Run every remaining phase hands-off — the full cairn loop per phase (map → plan → claim → execute → close → verify), doctor between phases, ship gate at the end
argument-hint: "[start-phase]"
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
3. Resolve the pending phases from ROADMAP.md (phases not marked complete),
   starting at `$ARGUMENTS` when given, else the first pending one. Resolve
   the active milestone (STATE.md frontmatter `milestone:`, else ROADMAP.md's
   🚧 header).
4. Announce the run — the ordered phase list and the stop rules below — then
   go. No further questions: gray areas during planning resolve to sensible
   defaults recorded as Claude's Discretion in each phase's CONTEXT.md.

## Per phase N (in order)

1. **Plan** — `/cairn:plan N`, non-interactively (skip discussion questions;
   record assumptions instead). This regenerates the beads map, runs
   `/gsd:plan-phase N`, reconciles divergence (CONTEXT wins) and sets each
   PLAN.md's `beads:` frontmatter.
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
