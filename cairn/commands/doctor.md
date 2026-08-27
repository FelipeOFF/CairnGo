---
description: Health-check the GSD↔beads wiring — run cairn-doctor, explain the report, route each finding to its fix
argument-hint: "[--fix-labels] [--close-completed] [--json] [--apply-reconciliation N]"
group: health
---

Audit the repo's cairn wiring and walk the user through fixing what it finds.

## 1. Run the doctor

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" $ARGUMENTS
```

Any flags the user typed (`--fix-labels`, `--close-completed`, `--json`) are
in $ARGUMENTS and go straight onto the call; `--json` gives machine output. Exit codes: `0` all ok — warnings included, they
never change the exit code — or not-applicable (`.planning/` or `.beads/`
absent), **or a report whose verdict is `INCOMPLETE`**; `5` bd unavailable;
`7` at least one check **failed** — including a `--close-completed` that bd
refused (step 4).

`INCOMPLETE` exiting `0` is deliberate: an absent input is friction, not a
state inconsistency, and spending exit `7` on friction is how exit `7` stops
meaning anything. The verdict of an incomplete run therefore lives only where
it is **read** — the footer word, the `⊘` symbol, the top-level `ok` key — so
the exit code alone can never tell you the run was complete. Step 2 is where
you say it.

Not-applicable: relay the printed note — when exactly one side exists it
suggests `/cairn:migrate`; when neither exists, route to `/cairn:init`.

## 2. Explain the report

Header shows root, milestone, and active phase; then one line per check with
its itemized findings; then a footer carrying the verdict.

**Four statuses, and the symbol is the status.** Three of them is the old
vocabulary and it has nowhere to put a check that had nothing to check:

| Symbol | Status | What it says |
|---|---|---|
| `✓` | `ok` | the check ran, over real input, and found nothing wrong |
| `⊘` | `not-applicable` | the check had **no input** — it did not pass, it did not run |
| `⚠` | `warn` | an advisory; never changes the exit code |
| `✗` | `fail` | a state inconsistency; this is what exit `7` counts |

A `⊘` comes in one of two families, and they are not the same sentence:

- `out-of-scope` — the input will never exist for this **class** of repo
  (cairn's own release manifests, in a repo that is not cairn). Permanent,
  ordinary, no action, and it does **not** make the report incomplete.
- `no-input` — the input *should* exist given what the repo already has (a
  `STATE.md` with no `active_phase`, a `ROADMAP.md` with no phase). It is a
  gap someone can close, and it is what makes the report incomplete.

**Three verdicts, ranked.** A failure outranks an incomplete report, because
"something is inconsistent" is the louder sentence:

- any `✗` → **FAIL**
- no `✗`, but at least one `⊘ no-input` → **INCOMPLETE**
- neither → **ok**

Reading `--json`: there is no `verdict` key — derive it from two booleans.
`failed` true → FAIL. `failed` false with `ok` false → INCOMPLETE. Both
answered → clean. `counts` carries the per-status totals, and a `⊘` check
carries a `scope` field naming its family.

Give the user the short version: what is inconsistent, and what fixes it. Two
things you may never do — **never call a `⊘` a pass, and never report an
INCOMPLETE run as clean**. Name the checks that had no input, say which family
each absence belongs to, and for `no-input` say what would close the gap.

## 3. Offer `--fix-labels` when the label-pairs check warns

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" --fix-labels
```

Runs `cairn-relabel pair` with the active milestone **before** the checks, so
the report shows the post-fix state. It refuses (exit `2`) when candidates
exist but the milestone is unresolvable — set `milestone:` in STATE.md
frontmatter (or mark the in-progress ROADMAP milestone with 🚧) first.

## 4. Offer `--close-completed` when the phase-complete-open check warns

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" --close-completed
```

Bulk-closes every non-closed issue whose `phase-<N>` labels **all** point at
phases ROADMAP.md marks complete (`bd close <id> --reason "doctor: phase N
complete in ROADMAP"`), printing each id it closes, **before** the checks run
— so the report shows the post-fix state. All, not any: a cross-phase issue
with one phase still open is left alone, exactly as `/cairn:status` keeps it
out of `stale_complete` and may offer it as the next action. Idempotent: a
re-run with nothing left to close closes nothing.

bd refuses to close an epic that still has an open child, and an issue whose
blocker is still open, so the sweep runs as a **fixpoint**: it re-passes the
target set until a whole pass closes nothing. One invocation therefore drains
a whole `epic ← epic ← epic` chain (children first, then each epic as its
blocker clears) with no `--force`. Whatever bd still refuses is listed under
the check with bd's own reason and makes the check **fail (exit 7)** — never a
silent partial sweep. Usual cause: the epic's remaining open child sits in a
phase that is NOT complete, so it was rightly out of scope; close or re-phase
that child, or re-open the phase.

Caution: when the ROADMAP
checkbox and the on-disk artifacts disagree (no phase directory, no PLAN in
it, or a PLAN without its SUMMARY — the note names which), the
divergence warning is printed **before** the closes — confirm with the user
that the phase is really done; the alternative fix is re-opening the phase
(uncheck it in ROADMAP.md). These closes go straight through `bd close`, so no
push hook fires: when `.cairn/sync.json` exists the run reminds you to run
`/cairn:sync-pull` so external mirrors stop showing the issues open.

## 5. Route the remediation per check

Two findings this command fixes itself, and they are steps 3 and 4 above:
`label-pairs` → `--fix-labels`, `phase-complete-open` → `--close-completed`.
A third has a one-line answer: `maps-fresh` → regenerate each stale phase with
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>`.

For every other id, the routing lives in one place:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/doctor.md
```

That page carries an entry per check — the id, the symbols it can report, the
`⊘` family when it has one, and the action that closes it. Read the entries
for the ids **this run actually reported**, and give the user those actions in
your own words, in the order the report printed them: failures first,
`no-input` next (they are why the verdict reads INCOMPLETE), advisories last.

Do **not** copy that table into this page, and do **not** write here how many
checks there are. Both are exactly how a page like this starts lying, and this
repository has already shipped every version of it: a page claiming fifteen
while sixteen were registered, a docstring claiming eighteen in total while
nineteen were, and two hand-written totals disagreeing inside a single file.
The doctor grows almost every phase; an address survives that, a copy does
not.

An id the report prints and the table does not carry is a gap in the **table**
— say so plainly and route the user to the check's own name, rather than
inventing a remedy for a check you cannot read.

Two `jira-links` items need a session, and this is the session. An item
saying **existence … not checked** means the script had no token and no
`CAIRN_JIRA_FETCH` to ask with: load the Atlassian MCP per `/cairn:jira`
and fetch each linked key yourself (`getJiraIssue`), then report which exist
— the script said `skipped`, and only a session can close that gap. A
**duplicate** item names two beads sharing one card: put the pair to the user
(`AskUserQuestion`) with each bead's title, ask which one the card is really
about, and offer to create another card for the other through
`/cairn:jira link` — never unlink one of them on your own.

Re-run the doctor after the fixes. A clean re-run is an `ok` footer with no
`⊘ no-input` line — not merely exit `0`, which an INCOMPLETE run also
returns.

## 6. Apply a verified reconciliation proposal (`--apply-reconciliation N`)

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" --apply-reconciliation "$N"
```

This is a separate, human-invoked command (ESC-03) — not something this
routine health check offers reactively like steps 3-4 above. It is the next
step `/cairn:reconcile N` itself names once it has written a citation-checked
proposal to `.cairn/conflicts.json`; run it only when the user has reviewed
that proposal and actually wants it applied.

Before touching anything it re-verifies the proposal is still trustworthy —
never trusting what the proposal says about itself: a fresh `collect N`
compares today's `evidence_hash` against the one stamped in the proposal
(mismatch -> refused, stale, tell the user to re-run `/cairn:reconcile N`); a
fresh `verify N` re-checks every citation (one bad citation refuses the whole
proposal, D-03); and every `bd_close`/`bd_reopen` claim's target bd id must
actually carry a `phase-N` label (correct citations elsewhere never excuse a
claim naming an unrelated issue). Any one of these refusals is fail-closed
and all-or-nothing — nothing is written. If the phase's conflict has already
resolved some other way since the proposal was written, it says so and exits
clean (exit `0`) — nothing left to apply is not a failure.

Only once all of that passes does it print anything: EVERY claim —
statement, recommended action, what will happen, `manual_review` claims
listed as "skipped" — BEFORE touching bd at all, so the user sees the full
plan while it can still be stopped. It then applies only the closed
vocabulary: `bd_close`/`bd_reopen` claims change bd state one at a time
(`bd close --reason` / `bd update --status open --assignee ""`);
`manual_review` claims never touch bd. A close/reopen bd itself refuses is
reported by id and reason and fails the run (exit `7`) — never silent.
