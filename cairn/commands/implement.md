---
description: Implement a phase as one pull request — the beads' frontier run in parallel, one worktree per bead, merged as they land, reviewed, and marked ready
argument-hint: <phase-number> [--max N] [--no-explore]
group: loop
---

Implement phase **$ARGUMENTS** as one pull request, under the `cairn`
conventions. `/cairn:work` and `/cairn:autonomous` are untouched: this is the
verb for a phase whose beads form a **task graph** with a moving frontier,
where the win is running that frontier concurrently and landing every result
on one PR branch.

**The spec is the carrier, the tickets are the beads.** `bd show <carrier>
--json` holds the phase's promise (`description`), its context, research and
spec (`design`), and its plan records (`bd list --parent <carrier> --json`);
`bd ready -l m-<milestone>,phase-<N>` is the frontier, recomputed every time a
bead closes. Communication with subagents is **context pointers** — bead ids,
the carrier id, a plan record id, a base SHA — never prose copied from a
record they can read themselves.

## 0. Pre-flight

1. `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh"` — a ✗ (exit 7)
   stops here. Read the phase: `cairn-map.sh <N>`, the carrier, the plan
   records. No `## CONTEXT` on the carrier → `/cairn:plan <N>` first; a phase
   is implemented from its records, not from a guess.
2. **Scope and base branch** (`cairn-config.sh get ship.pr_scope`):
   - `phase` (default): the frontier is the phase's beads; the **base is the
     branch you are standing on** — the milestone branch (`feat/vX.Y/…`).
     Refuse when that branch is a control branch (`git.control_branches`, or
     what `cairn-land.py` detects, e.g. `master`): a phase PR against the
     trunk is the milestone PR in disguise.
   - `milestone`: the frontier is every open bead of the cycle; the base is
     the control branch.
   - `none`: stop — this verb exists to open a PR.
3. **Acquire the phase lease**
   (`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-lease.sh" acquire "$N"`) and
   create the PR branch from the base: `git checkout -b phase/<N>-<slug>`
   (`cairn-parallel.sh batch --json` names it under `selected[].branch`).
4. **Announce** before anything is created: the frontier now (ids and
   titles), the ceiling (`--max N`, else `autonomous.max_parallel`, itself 3),
   the base branch, the PR target. This is the interruption point.

## 1. Explore (optional, `--no-explore` skips it)

One **exploration subagent**, read-only, for what the beads need and the
records do not yet say: the files each bead touches, the tests that guard
them, the external docs. It reports text, and the session records it —
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" research --phase "$N"`
(body on stdin) — so every implementer reads one record instead of exploring
five times.

## 2. Open the draft PR first

```bash
git push -u origin phase/<N>-<slug>
gh pr create --draft --base <base> --title "<phase title>" --body-file - <<'BODY'
## Summary
<the phase's promise, from the carrier>
## Changes
<one line per bead: id — title>
## Test plan
<the suites the beads' plan records name>
BODY
```

The body carries the bead ids and nothing about who wrote it: **no AI
mention, no session trailer** — the user's golden rule, and it overrides any
template that asks for one. The PR exists before the first implementer runs
so every push has somewhere to land and every gate has a run to watch.

## 3. The frontier, in parallel

Loop until no bead of the scope is open:

1. **Frontier:** `bd ready -l m-<milestone>,phase-<N> --json` (the cycle's
   label pair, unpadded number). Drop what is already claimed by a live
   implementer. Take up to the ceiling minus the implementers still running.
2. **Prepare one worktree per bead**, from the PR branch — never
   `Agent isolation: "worktree"` (D-01: the name comes from the script, and
   reconcile finds the work by that name):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-parallel.sh" prepare-bead <id> \
     --base phase/<N>-<slug> --json
   ```
   It prints `worktree`, `branch` (`bead/<short>-<slug>`), `base_commit`, the
   lease it took (`bead:<id>`) and `response_language`. Exit 3 (a live
   holder owns the bead) is reported and skipped, never a stop.
3. **Spawn the implementers together, in the background**, one per prepared
   bead. Each prompt carries, literally: the absolute worktree path and
   branch from `prepare-bead`; the pointers (bead id, carrier id, plan record
   id, base SHA, the research record's location); the work — `bd update
   <id> --claim`, implement what the bead says, measure before changing,
   write the test that fails without the change, run the relevant suite with
   `cairn-test.sh` (never raw `bats`), **commit on the bead branch, never
   merge, never push**; the prohibition on `.planning/STATE.md`,
   `ROADMAP.md`, `REQUIREMENTS.md`; what to report (commits, tests run, what
   failed); and the `response_language` copied from `prepare-bead`.
4. **When an implementer finishes, a merger subagent lands it** — in the
   main checkout, on the PR branch, one bead at a time:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-parallel.sh" reconcile --beads \
     --base phase/<N>-<slug> --json
   git merge --no-ff bead/<short>-<slug>
   ```
   `reconcile` names the conflicts and the convergent edits the merge would
   resolve in silence; the merger **resolves a conflict by reading both
   sides** and never with a strategy that picks a side (`-X ours` / `-X
   theirs` are forbidden, in any spelling). After the merge it runs the suite
   the bead's plan record names. **A failing suite is a stop rule**: report
   the bead, the branch and the output, leave the merge uncommitted or revert
   it, let the other implementers finish, and stop the loop. Green → `bd
   close <id> --reason="…"`, release the bead lease
   (`cairn-lease.sh release bead:<id>`), and push:
   ```bash
   git push
   bd gate create --type=gh:run --blocks <next frontier bead> --reason="CI of phase/<N>-<slug>"
   bd gate discover
   ```
   The gate keeps the next bead out of `bd ready` until that run is green
   (`bd gate check --type=gh:run` before the next frontier read); never
   `--await-id` by workflow name. A red run keeps the gate open — fix it on the
   PR branch before taking more work.
5. **Re-read the frontier.** A closed bead unblocks others; spawn more
   implementers up to the ceiling. Go to 1.

**One implementer failing does not stop the others.** Report it (bead, step,
output), release its lease, leave its worktree for `cleanup` to report, and
carry on.

## 4. Review, fix, ready

1. **Review the PR branch** — the harness `code-review` skill when it is
   listed (`Skill` tool), else the vendored `gsd-code-reviewer` agent — over
   the whole diff against the base.
2. **One implementer fixes every finding**, in the main checkout on the PR
   branch, running the suites the findings touch; commit, push, gate.
3. **Verify and close the phase** (D-02): record the verdict on the carrier
   (`cairn-record.sh verification --phase "$N"`, one line per requirement
   with its evidence and the suites' counts), check `bd list
   -l m-<milestone>,phase-<N> --all` shows nothing open but the carrier, then
   `bd close <carrier> --reason="…"` and
   `cairn-lease.sh release "$N"`.
4. `gh pr ready`. Then, and only with `ship.auto_merge` = `true`
   (`cairn-config.sh get ship.auto_merge`): wait for the last gate
   (`bd gate check --type=gh:run`) and `gh pr merge --squash`. With `false`
   (the default) stop here — the merge is a human decision (`/cairn:ship`).

## 5. Clean up

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-parallel.sh" cleanup --apply
```

Removes only worktrees that are clean **and** wholly merged, releases leases
whose holder is gone, and reports what it kept — a failed bead's tree stays,
with the command to inspect it. Refresh the map
(`cairn-map.sh <N>`) and report: the PR URL, the beads closed, the gates
opened, what stopped and why.

## Stop rules

The suite fails after a merge; `reconcile` reports a conflict the merger
cannot read its way out of; the doctor reports ✗; bd becomes unavailable
(exit 5 anywhere); the base branch is a control branch under `pr_scope =
phase`. Stop, say where (bead, step, output), release the claims that no
longer reflect live work, and leave the PR as a draft with what landed.
