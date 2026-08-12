---
description: Run every remaining phase hands-off — the full cairn loop per phase (map → plan → claim → execute → close → verify), doctor between phases, ship gate at the end
argument-hint: "[start-phase] [--sequential] [--max N] [--interactive]"
group: loop
---

Run the milestone to completion under the `cairn` conventions, without
checkpointing back to the user between steps. This is the beads-aware
counterpart of the vendored autonomous workflow: every phase passes through the full bd
bookkeeping (claim → in_progress → close → map refresh), whether or not the
cairn GSD capability is installed — its hooks are idempotent with these steps.

**Parallel execution is the default.** Phases the status model already reports
as independent are executed at the same time, one git worktree each, and the
announcement in step 0.4 says how many will run and why **before** anything is
created. A command that detects parallelism, announces parallelism and then
runs in single file is saying one thing and doing another; closing that gap is
the whole point of this mode. `--sequential` is the named way out: one phase at
a time, in the main checkout, exactly the loop this command used to run.

## 0. Pre-flight (stop here if it fails)

1. `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh"` — a ✗ failure
   (exit 7) **stops** the run before it starts: report and route each finding
   per `/cairn:doctor`. Warnings are noted and do not block. A
   **not-applicable** note (exit 0 with one side missing — e.g. `.planning/`
   without `.beads/`) also **stops**: route to `/cairn:migrate` to wire the
   missing side, or offer the bare vendored autonomous workflow instead.

   That top-level note is **not** the same thing as the `⊘` a single check
   can now carry, and the difference decides whether this run continues. A
   report whose footer reads `INCOMPLETE` — one or more checks that had no
   input to compare — **does not stop the run**, because the exit code did
   not change: it is still `0`, and phase 23 kept it that way on purpose,
   since an absent input is friction and not an inconsistency. Note which
   checks read `⊘`, say so in the run report, and carry on. It matters
   because those checks are the ones whose green you cannot bank on later:
   if verification at the end leans on one of them, it is leaning on a
   comparison that never happened, and that gap has to be closed by hand
   (write the roadmap phase, set `active_phase:` in STATE.md) rather than
   inferred from a passing run.
2. bd must be available (doctor exit 5 means it isn't) — without bd there is
   no "autonomous through beads": **stop** and offer the bare vendored workflow
   instead.
3. Resolve the pending phases, the order, and the batch that runs at once —
   **from the status model rather than by reading ROADMAP.md yourself**:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-status.sh" --json
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-parallel.sh" batch --json
   ```
   `phases[]` gives each pending phase its title, state on disk and
   `blocked_by`; `next_commands[]` gives the order and the reason for it;
   `parallelism` gives what could run at the same time. Start at
   `$ARGUMENTS` when given, else at the first entry of `next_commands`.
   Resolve the active milestone from `milestone`.

   `batch --json` turns that reading into the lot that actually runs:
   `selected[]` (one entry per phase, each with its `title`, `next_command`,
   `reason`, the `branch` and `worktree` it will get, and `lease_stale`),
   `deferred[]` (what stays out, each with the reason — a lease held by a live
   holder, or the ceiling), `max` (the ceiling in effect), `runnable` /
   `blocked` / `declared` / `note` passed through verbatim from
   `parallelism`, and `announcement` (the text for step 0.4).

   **Do not decide independence here.** It is computed in exactly one place in
   this codebase — `parallelism()` in `cairn-status.py` — and `batch` consumes
   that answer rather than recomputing it. A second opinion about what can run
   at once is a second truth about the same fact, which is precisely the defect
   this milestone exists to remove. Pass `--max N` through to `batch` when the
   run was invoked with it.

   Under `--sequential`, still run `batch` and still announce what it found —
   then execute the phases one at a time. Announcing parallelism and queueing
   anyway is honest here and only here, because the operator asked for it by
   name.
4. **Announce the run before anything is created.** Print the batch's
   `announcement` verbatim: it already carries how many phases run at once and
   which, each one's `next_command` and the reason it sits where it does, the
   worktree and branch each will receive, what stays out and why (a lease
   already held names its holder and since when), and the honesty line when
   `parallelism.declared` is false. Then add the two things that text does not
   carry:

   - Name the ceiling in force — the `max` the batch reports — and say that
     `--max N` raises or lowers it. The ceiling is discretionary: it limits how
     much concurrent work one person can actually review before reviewing
     becomes rubber-stamping, not anything git or bd cares about. Without the
     number the operator cannot tell "only two phases are free" from "five are
     free and the ceiling cut three", and in a mode whose entire point is that
     the operator can interrupt informed, the ceiling in force is interruption
     information.
   - Say that this is the interruption point: the next step creates worktrees
     and spawns agents that write code, and nothing before that is expensive to
     undo. An order chosen silently is an order nobody can disagree with before
     it costs an hour.

   When `parallelism.declared` is false, say so: no dependencies are recorded
   anywhere in the roadmap, so the split reflects what is recorded, not a
   verified ordering.

   Then go. No further questions: gray areas during planning resolve to
   sensible defaults recorded as Claude's Discretion in each phase's
   CONTEXT.md.

   **`--interactive` inverts that last sentence**, and only that one. The
   pre-flight, the order, the stop rules and every bd step are unchanged; what
   changes is that a genuine design decision is put to the user instead of
   being recorded as Claude's Discretion. The discussion step inside moment 1
   is the mechanism.

## The loop

Four moments, in this order. The reason for each is part of the rule, because
the order is what keeps the parallel half from writing where it must not.

### 1. Plan — in the main checkout, one phase at a time

`/cairn:plan N` for every phase of the batch, sequentially, in the main
checkout, **before any worktree exists**. Without `--interactive`, run it
non-interactively (skip discussion questions; record assumptions instead). Each
run regenerates the beads map, runs the vendored plan-phase workflow for N, reconciles divergence
(CONTEXT wins) and sets each PLAN.md's `beads:` frontmatter.

Planning is deliberately not parallelized, and the reason is mechanical rather
than cautious: the plan-phase workflow writes to `ROADMAP.md` — it fills in the
phase Goal and the list of plans. A phase planned inside its own worktree would
therefore break the planning-file prohibition on its very first step. Planning
centrally, one phase after another, *is* the central application that rule
asks for, and it is cheap next to execution, so little is lost. It also means
every worktree is branched from a HEAD that already carries its own PLAN.md
files.

**Discuss (only under `--interactive`)** — if the phase has no
`NN-CONTEXT.md`, run the vendored discuss-phase workflow for N **before** planning it. Invoke it
here, in the autonomous loop, rather than telling the user to run it
themselves.

This is allowed, and the reason matters. GSD's `plan-phase` workflow forbids
invoking discuss-phase as a nested Skill/Task call, because `AskUserQuestion`
misbehaves in a subcontext (gsd-core #1009) — that prohibition is about
**plan-phase** nesting it one level down. The autonomous loop runs in the
top-level session, so a `Skill` call from here is the same context the user's
own discussion would run in, and the questions work. Do not hand the
command back to the user as if you could not run it.

**Discuss at the phase's turn, never in a batch up front.** It is tempting,
with five pending phases, to discuss all five before planning any — do not. A
CONTEXT.md is a set of locked decisions, and decisions locked for phase N+2 are
taken against a codebase that phase N is about to change: the discussion is
held over a guess, and the guess is then recorded as settled. That is the same
failure this whole plugin is built to catch — a record that claims more
certainty than anything corroborates. This applies with more force in a
parallel run, not less: the phases in one batch are independent by dependency,
which says nothing about which files they will touch.

One narrow exception, and it must be checked rather than assumed: a phase may
be discussed ahead of its turn when `blocked_by` is empty **and** its roadmap
entry says it needs no research during planning. Anything else waits for its
turn in the loop.

Without `--interactive`, skip the discussion entirely — gray areas resolve to
Claude's Discretion, as above.

### 2. Prepare — one named worktree and one lease per phase

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-parallel.sh" prepare "$N" --json
```

once per phase in `selected[]`. It creates the worktree `batch` already named
(`<repo>-phase-<N>`, on branch `phase/<N>-<slug>`), takes that phase's lease
pointing **at** that worktree, and prints `worktree`, `branch`, `base_commit`,
the resulting `lease.holder`, `planning_files_forbidden` and
`response_language`.

Exit 3 means a live holder already owns the phase: report the holder and the
time from the output, drop that one phase from the batch, and **carry on with
the others** — an owned phase is something to report, never a reason to stop
the run. Exit 4 (git refused: the path is occupied, or the branch exists
without its worktree) is handled the same way, with the script's own message.

Read the worktree path out of `prepare`'s output and hand it to the agent. The
agent is never asked where it worked: a self-declared location is not evidence
of anything, and reconciliation finds the work by the name `prepare` gave it,
not by any name an agent reports afterwards.

### 3. Execute — one subagent per prepared phase, at the same time

Spawn the subagents together, one per prepared phase, so they actually run
concurrently. This is the step the announcement exists to precede.

<!-- SUBAGENT-PROMPT-BEGIN -->
Each subagent's prompt carries all six of these, literally:

- **Where it works.** The absolute worktree path and the branch name, copied
  from that phase's `prepare` output. Every command runs with that worktree as
  the working directory. Never a path the agent picked, and never one it
  reported back.
- **What it runs.** `/cairn:work N`, then `/cairn:verify N`, inside that
  worktree. `/cairn:work` acquires the phase lease itself and resolves its own
  identity from the working directory, so it finds the lease `prepare` already
  took, recognises it as its own and simply heartbeats it.
- **What it must not write.** `.planning/STATE.md`, `.planning/ROADMAP.md` and
  `.planning/REQUIREMENTS.md` are forbidden inside the worktree: do not create,
  edit or delete them, and do not let a delegated command do it either. Every
  phase writes all three, which makes them the one collision surface that is
  guaranteed rather than merely possible. The completion marks for every phase
  in the batch are applied together, in the main checkout, in moment 4.
- **Commit, never merge, never push.** Commit the phase's work on the branch it
  was handed. Do not merge it into any other branch, do not rebase it onto one,
  and do not push. Joining the work is moment 4, and it happens in the main
  checkout under a human eye.
- **What to report back.** The branch, the commits made, the plans executed and
  the bd ids closed — plus any step that failed and why. The report is
  narrative; nothing in moment 4 depends on it for a path, a branch name or a
  file list, all of which are discovered from git.
- **What language it answers in.** The `response_language` from that phase's
  `prepare` output, copied literally — read from the output, never remembered
  and never inferred from the repository. Every user-facing line the subagent
  writes goes in that language: its report back, the SUMMARY it produces, any
  question it asks. Code, identifiers, file paths, commands and bd ids stay
  exactly as they are. A `null` value means `prepare` could not read the
  config: say so in the announcement instead of guessing a language.
<!-- SUBAGENT-PROMPT-END -->

**The failure of one parallel phase does not stop the others.** Report it with
the phase number and the failing step, let the remaining phases finish, and
leave its lease to be released in moment 4 — killing three live agents because
a fourth failed loses work that was already done and correct.

### 4. Reconcile, merge, mark, clean up

Nothing in this moment happens inside a worktree.

1. **Reconcile first, and put the whole report in front of the operator.**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-parallel.sh" reconcile --json
   ```
   It reads committed refs only and writes nothing. `branches[]` says what each
   phase produced; each entry of `pairs[]` carries the merge `conflicts` git
   will raise **and** the `convergent_edits` git would resolve in silence — the
   same line changed to the same value on both sides, for two different
   reasons, which is the class that passes unnoticed because it interrupts
   nothing.

   **Exit 6 is a stop rule.** The report goes to the operator — file and line
   of every conflict and every convergent edit — before any merge is attempted.
   A null `conflicts` list with a `conflicts_note` means git is too old to
   pre-compute them, and that also exits 6: "unknown" is not "clean".

   **`planning_writes` is presented to the operator even when the exit is 0.**
   A branch that wrote to one of the three planning files is reported there and
   deliberately does not move the exit code — reporting is not failing, and
   failing the reconciliation over it is a variant that was recorded and not
   adopted. So a run with no conflict and no convergent edit exits 0 while
   still carrying a violation in that list, and reacting only to exit 6 would
   let it through. Detecting something nobody reads is the same as not
   detecting it.
2. **Merge one branch at a time**, `git merge --no-ff <branch>`, plain. A git
   conflict is a stop rule: hand it to the operator with the branch and the
   paths, and do not attempt to resolve it.

   **No merge strategy that resolves a conflict by automatically preferring one
   side is permitted anywhere** — not in a run, not in an example, not in this
   file and not in its documentation page. That covers both the whole-strategy
   selection and the recursive strategy option, in either direction (`ours`,
   `theirs`). A conflict is two agents disagreeing about the same lines; a flag
   that picks a winner in silence destroys one side of that disagreement and
   reports success, which is the failure mode this entire phase exists to make
   impossible.
3. **Apply the completion marks centrally** — one command per merged phase,
   here in the main checkout, and never by editing the three planning files
   by hand:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-bookkeep.sh" close <N> --apply
   ```
   That single call marks the phase, marks every requirement whose phases are
   all closed, moves the coverage table and its footer, ticks the plan
   checkboxes whose `-SUMMARY.md` is on disk, moves the STATE counters and
   releases the lease. It is idempotent, so
   re-running it after a partial batch is safe.

   Exit 5 means `bd` was not reachable and **nothing** was written — fix that
   and re-run; do not fall back to editing by hand. It is **not** a gate:
   what it will not write it names under `unresolved`, and barring a phase
   stays with `cairn-gate.sh`. Fold its report into the per-phase block this
   step already emits. This is the other half of the prohibition the
   subagents carried.

   Then run the phase checkpoint for each merged phase, also here:
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh"` (failure stops the
   run), and `bd list -l m-<milestone>,phase-N --all` must show **no issue with
   a status other than `closed`** — the same semantics the ship gate enforces
   later (`--status open` alone would miss `in_progress`/`blocked` stragglers
   and defer the failure to the very end of the run). Emit a one-block report
   per phase (plans executed, issues closed, doctor verdict).
4. **Clean up.**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-parallel.sh" cleanup --apply
   ```
   It prunes worktree registrations whose directory is gone, releases leases
   whose holder is not a worktree of this repo, and removes only the worktrees
   that are clean **and** wholly merged. Anything with uncommitted work or
   unmerged commits is retained and reported with the command to inspect it —
   including the tree of a phase that failed in moment 3.

Then take the next batch: back to step 0.3, until no phase is pending.

### `--sequential`

One phase at a time, in the main checkout, no worktree and no subagent: plan,
`/cairn:work N`, `/cairn:verify N`, phase checkpoint, next phase. Moments 2 and
3 do not run, and moment 4 collapses to the checkpoint — there is nothing to
reconcile and nothing to merge. The lease is still taken by `/cairn:work`
itself. Use it when the batch is not worth the worktrees, or when the operator
wants to watch one phase at a time.

## Stop rules (autonomous ≠ blind)

Stop immediately, report where you are (phase, step, offending ids/output),
and leave the repo consistent — release claims that no longer reflect active
work (`bd update <id> --assignee "" --status open`) or close what is truly
done — when:

- doctor reports a ✗ failure (exit 7) at any checkpoint;
- reconciliation exits 6 — findings, or conflicts it could not rule out; the
  report reaches the operator before any branch is merged;
- a merge raises a git conflict;
- a plan's execution fails and cannot be recovered within the phase, in a
  sequential run;
- verification finds a gap that reconciliation cannot close;
- bd becomes unavailable mid-run (exit 5 from any script) — claims and closes
  can no longer be trusted;
- the ship gate blocks (exit 6).

Two things that are explicitly **not** stop rules, because in a parallel run
they are ordinary events: `prepare` refusing a phase whose lease a live holder
already owns (exit 3), and one parallel phase failing while the others are
still running. Both are reported and the run continues.

**Stop rules override the delegated commands' degradation paths.** During an
autonomous run, the exit-5 fallbacks the individual commands document (e.g.
`/cairn:plan`'s "fall back to reading the existing map file") do **not**
apply: any exit 5 from `cairn-map`/`cairn-doctor`/`cairn-gate`, or any bd
failure, halts the run instead of degrading it — silent degradation is
exactly what autonomous mode must not do.

The resume path after a stop is the ordinary loop: fix the reported problem,
then re-run `/cairn:autonomous` — phases already marked complete in
ROADMAP.md are detected and skipped, and `cleanup` reports what the stopped run
left behind. When resuming a phase that was interrupted mid-way, **skip the
claim for ids already `closed`** by the earlier partial pass: `bd update <id>
--claim` on a closed issue errors ("not claimable: status closed") — during a
resume that error is expected and benign, not an execution-failure stop rule.

## After the last phase

1. `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-gate.sh"` — exit 6 **stops**
   with the offending ids (a phase marked done still has non-closed issues).
   Green: report the milestone summary — phases run, plans executed, issues
   closed, and any unphased `quick` issues still open.
2. Do **not** push. Hand off with `/cairn:ship` as the suggested next step —
   the push stays a human decision, and the pre-push shim enforces the same
   gate outside the agent anyway.

Notes:

- The vendored runtime already claims and
  closes issues via hooks — every bd step above is idempotent (re-claiming
  your own issue and re-closing a closed one are no-ops), so the run is safe
  either way.
- `quick`-labeled issues are unphased and never block a phase; they stay
  visible in `/cairn:status`'s ready list.
- A phase worktree keeps its own `.cairn/journal.jsonl`, which disappears with
  the worktree: what a parallel phase journalled locally does not survive
  `cleanup`. A durable cross-worktree journal is a v2 item, and it is recorded
  here rather than discovered later.
