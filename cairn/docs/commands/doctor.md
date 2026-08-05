# /cairn:doctor

> Health-check the GSD↔beads wiring — run cairn-doctor, explain the report, route each finding to its fix

## Usage

```
/cairn:doctor [--fix-labels] [--close-completed] [--link-refs] [--json]
```

Flags typed by the user are appended to the script call. Under the hood:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" [--json] [--fix-labels] [--close-completed] [--link-refs]
```

`--apply-reconciliation N` is a separate, standalone invocation, not part of
this routine health-check flow — see its own section below.

## What it does

1. Runs `cairn-doctor.sh` (wrapper over `cairn-doctor.py`). The report opens
   with a header (repo root, milestone, active phase), then one
   `✓`/`⊘`/`⚠`/`✗` line per check with itemized findings, then a footer
   carrying a verdict word and all four counts.
2. Explains the report to the user: failures (`✗`) block, warnings (`⚠`) are
   advisories, and warnings never change the exit code.

   `⊘` is **not-applicable**: the check had nothing to check. It says the
   comparison never happened — which is a different sentence from `✓`, "I
   compared and it agrees". What it does **not** say is that anything is
   wrong; it never changes the exit code either. Each one carries a `scope`
   telling you which kind of absence it is:

   - **`out-of-scope`** — the input will never exist in a repo like yours and
     nothing is wrong. Cairn's own release manifests in a repo that is not
     cairn are the ordinary case. Permanent, expected, no action.
   - **`no-input`** — the input *should* exist given what your repo already
     has, so this is a gap you can close (a `STATE.md` that is present but
     carries no `active_phase`). The check's detail line names what is
     missing and where to fix it.

   Only `no-input` changes the footer's verdict word to `INCOMPLETE` and the
   `--json` `ok` key to `false`. A report can be `INCOMPLETE` and still exit
   `0` — an absent input is friction, not a state inconsistency, and exit `7`
   spent on friction stops meaning anything.

   **The `--json` keys that carry the verdict**, because "something failed"
   and "something never ran" are different questions:

   | Key | The question it answers |
   | --- | --- |
   | `.failed` | Did any check **fail**? The exact mirror of exit `7`. |
   | `.ok` | Did every check both **run** and pass? False when anything failed **or** when a check inside the doctor's remit got no input. |
   | `.counts` | How many checks landed in each of the four states (`ok`, `not-applicable`, `warn`, `fail`). The four always sum to `.checks \| length`. |
   | `.checks[].scope` | Present **only** on a `not-applicable` check: `out-of-scope` or `no-input`. |

   A consumer that wants "should I stop?" reads `.failed` (or the exit code).
   One that wants "can I trust this green?" reads `.ok`.
3. When the **label-pairs** check warns, offers a re-run with `--fix-labels`,
   which runs `cairn-relabel pair` with the active milestone **before** the
   checks so the report shows the post-fix state.
4. When the **phase-complete-open** check warns, offers a re-run with
   `--close-completed`, which bulk-closes every non-closed issue whose
   `phase-<N>` labels **all** point at phases ROADMAP.md marks complete
   (`bd close <id> --reason "doctor: phase N complete in ROADMAP"`)
   **before** the checks, printing each id it closes. All, not any: a
   cross-phase issue with one phase still open stays open, the same
   predicate `/cairn:status` uses for `stale_complete`. Any
   checkbox-vs-artifacts divergence warning is printed before the closes,
   and a repo with `.cairn/sync.json` gets a `/cairn:sync-pull` reminder
   (these closes bypass the push hook). Idempotent — nothing left to close
   means nothing closed. Because bd refuses to close an epic with an open
   child (and an issue with an open blocker), the sweep is a **fixpoint**:
   it re-passes the target set until a pass closes nothing, so one
   invocation drains an `epic ← epic ← epic` chain without `--force`.
   A target bd still refuses is reported with bd's reason and **fails**
   the check (exit `7`) instead of a silent partial sweep.
5. When the **external-ref** check finds an unambiguous, unlinked git
   match, offers a re-run with `--link-refs`, which backfills bd's
   `external_ref` field (`bd update <id> --external-ref gh-<N>`) for every
   closed issue whose match is unambiguous, printing each id it links.
   Idempotent — an issue that already carries an `external_ref` is never
   reconsidered, so a second run links nothing further. On a shallow
   clone, skips entirely and says so (see the check's own entry below).
6. Routes each finding to its remediation:
   - **req-issue** (✗) — a ROADMAP requirement has no stamped, phase-labeled
     issue → `/cairn:migrate` (mode C wires or creates), or a one-off
     `bd create "CAT-NN: <title>" -l m-<m>,phase-<N> --metadata
     '{"gsd": {"req": "CAT-NN", "phase": N, "milestone": "vX.Y"}}'` — always
     **with the stamp**.
   - **frontmatter-ids** (✗) — a PLAN.md `beads:` id is dangling or unlabeled
     → edit the PLAN's `beads:` list, or add the missing `phase-<N>` label.
   - **maps-fresh** (⚠) — stale generated maps → regenerate each phase with
     `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>`.
   - **superseded-released** (⚠) — a superseded PLAN still holds open ids →
     close them or move them to the superseding plan.
   - **phase-complete-open** (⚠; ✗ when a close was refused) — non-closed
     issues whose phase labels ALL
     point at phases ROADMAP.md marks complete (checkbox `- [x]` or a
     progress-table `| Complete |` row, same lenient reading as the ship
     gate; a cross-phase issue with one live phase is not flagged) → step 4
     above (`--close-completed`), or re-open the phase if it is not actually
     done. A note item flags when the on-disk artifacts disagree with the
     checkbox and names the gap (no phase directory, no PLAN in it, or a
     PLAN without its SUMMARY) — confirm before closing. A ✗ means bd
     refused a close (typically an epic whose remaining open child sits in
     a phase that is NOT complete) → close or re-phase that child, or
     re-open the phase.
   - **orphans** (⚠) — issues labeled for a non-ROADMAP phase, or non-closed
     with no `phase-*` label → attach the right phase label + stamp, label
     `backlog`, or close.
   - **label-pairs** (⚠) — step 3 above (`--fix-labels`).
   - **claims-stale** (⚠; ⊘ when it has no input) — in_progress + assigned
     issues outside the active
     phase → finish and close, release the claim, or correct `active_phase:`
     in STATE.md.

     It reports `⊘ not-applicable` / `no-input` when it **cannot run at all**,
     which is its state in this
     repository today: STATE.md's frontmatter carries no `active_phase`, so
     there is nothing to compare the claims against. `no-input`, not
     `out-of-scope`: STATE.md **is** here, it just lacks a key someone can
     add — so this one does make the report read `INCOMPLETE`, without
     changing the exit code. That is reported, named
     and addressed rather than skipped in silence — measured 2026-08-04, it
     used to read `✓ claims-stale  skipped — no active_phase in STATE.md`, a
     check that had never run once in this project's life while wearing the
     success marker. Five cairn surfaces read that key (`cairn-status.py`,
     `cairn-doctor.py`, `cairn-lease.py`, `cairn-migrate.py`,
     `hooks/session-start.sh`) and **which key `STATE.md` should carry —
     `current_phase`, what GSD writes, or `active_phase`, what cairn reads —
     is open in `CairnGo-rq0`**: it changes what all five read and what every
     STATE.md already on disk means, so it is a grooming decision, not a
     rename. Never a failure either: a check with no input is friction, not a
     state inconsistency, and exit `7` spent on friction stops meaning
     anything.
   - **bd-doctor** (✗) — beads' own diagnostics failed → run `bd doctor`
     directly and follow its advice.
   - **gsd-capability** (✗) — the cairn capability is not registered with the
     installed GSD, so plain `/gsd:*` does **not** create, claim, close or gate
     bd issues. Three causes, all named in the detail line:
     - *the installed gsd-core will not load* — its own manifest declares the
       standard `hooks/hooks.json` path that Claude Code loads automatically, so
       the loader refuses the whole plugin and there are no `/gsd:*` commands at
       all. Reported before the others because it outranks them, and because the
       `gsd-tools` CLI keeps working, which hides it → run
       `scripts/cairn-capability.sh repair-manifest`, then `/reload-plugins`.
       A gsd-core update restores the original file, which is why this is
       re-checked rather than fixed once.
     - *two GSD lineages installed at once* — a 4.x `gsd` plugin sitting beside
       `gsd-core`, which is what happens on a machine that already had GSD when
       cairn was installed: the dependency lands beside the old plugin rather
       than replacing it. Both provide the same workflow surface and only one
       can host the capability, so `/gsd:*` may be answered by the one that
       cannot while every other check reports green → uninstall the 4.x plugin
       named in the detail line, then `/reload-plugins`.
     - *GSD 4.x lineage* (`jnuyens/gsd-plugin`) — that line has no `capability`
       subcommand at all and cannot host the fusion →
       `claude plugin install gsd-core@cairngo`, then `/reload-plugins`.
     - *gsd-core installed but the capability did not register, or its bundle
       is staged without the scripts its gates run* → re-run `/cairn:init`.
       The bundle check is not cosmetic: the ship-gate predicate no-ops when
       its script is missing, so a partly-staged bundle leaves a gate that
       passes without checking anything.

     This is a ✗ and not a ⚠ on purpose. The capability install used to fail
     silently, and a soft signal is exactly how that went unnoticed. A ⚠ is
     used only when no GSD binary can be found at all, since that is not
     evidence either way.

   - **phase-corroboration** (⚠/✗) — Plan 13-01's `phase_model()` verdict
     for a phase disagrees across disk, bd, the ROADMAP checkbox, or
     STATE.md's `active_phase` pointer. Each item is routed to the
     likely-correct fix first: a **disk-vs-bd** item (disk says the phase
     shipped, bd still has an open issue) → close the open issue(s) if the
     work is really done, or `/cairn:work N` if it is not; a
     **roadmap-vs-disk** item (the checkbox is ticked, disk disagrees) →
     confirm the phase is really done before leaving it ticked, or
     re-plan it; a **state_md-vs-disk** item (STATE.md still points at a
     phase disk already finished) → nothing to fix unless you are
     genuinely still working that phase. Disk-vs-bd and roadmap-vs-disk
     are `blocks` severity and **fail** the run (exit `7`); a
     state_md-vs-disk item, or bd being unreadable for a phase
     (`unknown`), is `informs` and only warns. Shells to `cairn-status.py
     --json`; a failure there degrades this check to a warn rather than
     crashing the doctor run.

     Each **conflict** item also names when each of its cited sources
     last moved (Plan 16-05, JOUR-02) — e.g. "disk last moved
     2026-07-31T10:00:00+00:00, bd last moved never observed" — pulled
     from `cairn-journal.py last-moved --phase N --json` (one call per
     phase, cached, never one per conflict item). This is the only place
     the transition journal's history surfaces (D-04): a "never observed"
     source means the journal never saw that side move, not that nothing
     happened. A missing, unreadable, or broken journal degrades the
     clause to nothing — the conflict itself, its severity, and this
     check's exit code are completely unaffected either way.
   - **phase-artifacts** (⚠) — names which artifact is missing for a phase
     whose board row would otherwise be a bare dash (CARD-02/D-04): a
     `PLAN.md` still lacking its own `SUMMARY.md` in a phase that has
     already reached `disk_state: verified` (an `NN-VERIFICATION.md`
     exists), or an `NN-VERIFICATION.md` with no readable `status:` field
     in its frontmatter → write the missing `SUMMARY.md`, or add the
     missing `status:` field to the verification report. The
     missing-`SUMMARY` half is deliberately narrower than it sounds: it
     only fires once a phase has reached `verified`, not on every
     unsummarized plan — an ordinary phase between waves always has some,
     and that is not the anomaly this check exists to name. One accepted
     consequence: a phase stuck at `executed` (a plan never summarized,
     and nobody ever runs `/cairn:verify` on it) never reaches `verified`
     and so is never flagged here either — check 5 (`phase-complete-open`)
     independently covers the ROADMAP-checkbox-complete flavor of the same
     gap. Shells to `cairn-status.py --json`, same pattern as
     phase-corroboration. Never fails the run — a missing `SUMMARY` or an
     unreadable verdict is record hygiene, not contradictory evidence
     about what happened.
   - **external-ref** (⚠) — a closed issue has no bd `external_ref` and an
     unambiguous `(#N)` PR reference was found in this repo's own git
     history (a commit within ±2 days of the issue's `closed_at`, touching
     that phase's `files_modified`) → step 5 above (`--link-refs`). Never
     warns merely because history predates the convention — that is this
     repo's entire history today (STACK.md) and is not, by itself,
     actionable. On a shallow clone, the check is skipped for the whole
     run and says so: a shallow clone's git match can be silently *wrong*
     at the boundary commit, not merely incomplete, so `--link-refs`
     never trusts one (run against a full clone, or `git fetch
     --unshallow`, then retry).
   - **lease-stale** (⚠) — a phase-level coordination lease
     (`cairn-lease.py`, Plan 15-01) is currently held and its heartbeat is
     older than the 4h TTL → reclaimable, not a bug: the next
     `/cairn:work N` reclaims it automatically, or run `cairn-lease.sh
     release N` directly to clear it now. Mirrors **claims-stale**'s own
     never-fails posture one level up (D-04/LEASE-05) — always a warning,
     never a doctor failure. Shells to `cairn-lease.py status --all
     --json`; a non-zero exit or unparsable JSON degrades this check to a
     warn rather than crashing the doctor run.
   - **release-versions** (✗; ⊘ `out-of-scope` outside cairn's own repo) —
     the plugin version's carriers disagree
     (`cairn/.claude-plugin/plugin.json` `version`,
     `.claude-plugin/marketplace.json` **nested** `metadata.version`, the
     first released CHANGELOG heading, the `v<version>` git tag) → run
     `cairn-release.sh check` and align the carrier named in the item.
     Applies only inside cairn's own repo. **In your repo this reads `⊘`
     with scope `out-of-scope`, and that is the normal, permanent state** —
     those manifests are cairn's own and will never be there, so nothing is
     missing and the report is not incomplete. No action.
   - **test-parallel** (⚠; ⊘ either family) — this machine cannot run the
     bats suite in
     parallel (GNU `parallel`, or `flock`/`shlock`, missing) → install what
     the item names. Never fails the run: a slow suite is friction, not a
     state inconsistency. Applies only inside cairn's own repo. Two `⊘`
     shapes, and they mean opposite things:
     - **outside cairn's repo** → `out-of-scope`. Normal and permanent, same
       as **release-versions**. No action.
     - **inside cairn's repo, with no `bats` on PATH** → `no-input`, and this
       one *is* a gap worth closing: nothing about parallelism could be
       concluded because the suite cannot run here at all (a different
       sentence from "it will run slowly"). It makes the footer read
       `INCOMPLETE`; install `bats-core` and it clears.
   - **req-ledger** (✗; ⚠ outside its own links; ⊘ `out-of-scope` with no
     ledger) — the requirement ledger's
     chain disagrees with itself: an **active** requirement with no row in
     the coverage table, a coverage **footer** claiming a different number
     than the table holds, a phase whose `**Requirements**:` line does not
     yield the ids the ledger assigns it, or a plan whose `SUMMARY.md` is
     on disk while its ROADMAP checkbox still reads `- [ ]` → run
     `cairn-bookkeep.sh reconcile --apply` (reading is the default; the
     writing sits behind that flag). Requirements under `## Deferred` or
     `## Out of Scope` are outside the table **by rule** and are never
     counted as gaps — the detail line says how many were excluded that
     way, because an unexplained absence is the same defect facing the
     other direction.

     **Where it stops, and where `req-issue` stops.** `req-issue` (check 1)
     goes requirement → **bd issue**, and it can only count the ids it
     manages to *read* off a phase's `**Requirements**:` line. `req-ledger`
     goes active requirement → **row in the coverage table** → **the number
     the footer claims**, plus the **legibility of that same line** and the
     **plan checkboxes** of the phase.

     That boundary is not theoretical. Measured 2026-08-04 in this
     repository: **35** active requirements, **33** coverage rows (`AUTO-05`
     and `AUTO-06` had none), a footer still reading `29 requisitos, 29
     mapeados.`, and `req-issue` reporting `ok :: 29 requirement(s) mapped
     to issues` — because `ROADMAP.md:400` read `**Requirements**: AUTO-01 …
     AUTO-08` and an ellipsis is prose, not a separator, so six ids never
     entered its count. Three numbers for one quantity, two of them wrong
     from unrelated causes that met at 29 by coincidence, both wearing a
     green check, for days. `req-ledger` is what would have said so.

     The ledger is read **once**, by shelling out to `cairn-bookkeep.py
     reconcile --json` — the doctor never re-parses it, because a second
     reader is a fifth number for the same quantity. A disagreement
     `reconcile` names *outside* these links (STATE.md's counters, its
     free-text narrative) is surfaced as a **warning** and never spends
     exit `7` on a check called `req-ledger`. A `.planning/` with no
     `REQUIREMENTS.md`, or a roadmap with no coverage view at all, reads
     `⊘` with scope `out-of-scope` — the doctor runs in users' repos, most
     carry no coverage table, and **keeping none is a method choice, not a
     gap**: calling it `no-input` would leave every such repo permanently
     `INCOMPLETE` over a table it deliberately does not keep. But the
     ledger being **unreadable**
     (the script missing, an unexpected exit, unparsable JSON) is a
     **failure**, never a warning: a warning does not change the exit code,
     so degrading there would leave the doctor exiting `0` over a ledger
     nobody managed to read.

   (Check 0, `bd-version`, runs first but needs no routing beyond
   upgrading bd — eighteen checks in total.)
7. Re-runs the doctor after fixes to confirm a clean `ok` footer.

## Flags & arguments

| Flag | Effect |
| --- | --- |
| `--json` | Machine-readable report |
| `--fix-labels` | Repair label pairs via `cairn-relabel pair` (active milestone) before checking |
| `--close-completed` | Bulk-close non-closed issues in ROADMAP-complete phases via `bd close --reason` before checking (idempotent, prints each closed id; sweeps as a fixpoint so parent/blocker chains drain in one run, and exits `7` if bd refuses one) |
| `--link-refs` | Backfill closed issues lacking `external_ref` from an unambiguous git match via `bd update --external-ref` (idempotent, prints each linked id; skipped entirely on a shallow clone) |
| `--apply-reconciliation N` | ESC-03, a **separate, standalone** invocation, not paired with the ordinary checks — see [Applying a reconciliation proposal](#applying-a-reconciliation-proposal-esc-03) below |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | All ok (warnings included) — or not-applicable: `.planning/` or `.beads/` absent (one side present → suggests `/cairn:migrate`; neither → `/cairn:init`). Also any number of `⊘` checks, of either family, **including a footer reading `INCOMPLETE`**: an absent input is friction, not a state inconsistency, and exit `7` spent on friction stops meaning anything. Read `.ok` (or the footer word) for "can I trust this green", not the exit code. Also `--apply-reconciliation`'s own "no longer in conflict" refusal — nothing left to apply is not a failure |
| `2` | Usage — notably `--fix-labels` refuses when candidates exist but the milestone is unresolvable: set `milestone:` in STATE.md frontmatter, or mark the in-progress ROADMAP milestone with 🚧, then retry. Also `--apply-reconciliation` finding no proposal for phase N (`.cairn/conflicts.json` missing, or its own `phase` field doesn't match N) |
| `5` | `bd` unavailable |
| `7` | At least one check **failed** (✗) — including `--close-completed` leaving a target unclosed because bd refused it (reported on the phase-complete-open check with bd's reason), and a `blocks`-severity phase-corroboration conflict. Also `--apply-reconciliation` refusing a stale proposal, a bad citation, an unrecognized `recommended_action.type`, an issue-provenance mismatch, or bd itself refusing a close/reopen it was asked to apply |

## Examples

Routine health check:

```
/cairn:doctor
```

```
[cairn-doctor] ~/Projects/app — milestone: v1.0, active phase: 3
 ✓ req-issue            12 requirement(s) mapped to issues
 ⚠ maps-fresh           1 of 3 phase map(s) need attention
     - phase 2: stale map 02-BEADS-MAP.md — run cairn-map.sh 2
 ✓ orphans              48 issue(s), no orphans
 …
 ⊘ release-versions     no cairn/.claude-plugin/plugin.json under this root
                        (the version carriers are cairn's own, not a wired
                        repo's)
 ⊘ test-parallel        no cairn/.claude-plugin/plugin.json under this root
                        (cairn's bats suite is cairn's own, not a wired
                        repo's)
[cairn-doctor] ok — 15 ok, 2 not-applicable, 1 warning(s), 0 failure(s)
```

Those two `⊘` are the ordinary state of every repo that is not cairn itself:
`out-of-scope`, permanent, no action, and the footer still says `ok`.

A check that never ran says so, and the footer says the report is incomplete
without claiming anything failed — note the exit code is still `0`:

```
 ⊘ claims-stale         cannot check — STATE.md's frontmatter carries no
                        'active_phase', so there is nothing to compare
                        in_progress claims against …
[cairn-doctor] INCOMPLETE — 16 ok, 1 not-applicable, 1 warning(s), 0 failure(s)
```

A repo whose GSD cannot host the fusion reports it plainly:

```
✗ gsd-capability     GSD 4.x lineage — it has no 'capability' subcommand, so
                     plain /gsd:* does NOT touch bd issues. Install the
                     official core: claude plugin install gsd-core@cairngo
FAIL — 12 ok, 0 warning(s), 1 failure(s)
```

Repair label pairs, then re-check:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" --fix-labels
```

## Applying a reconciliation proposal (ESC-03)

`--apply-reconciliation N` is the human-invoked, separate command that
applies a semantic-escalation reconciliation proposal `/cairn:reconcile N`
wrote to `.cairn/conflicts.json` (Phase 17). It is not one of the 18 checks
above and does not run alongside them — it always exits on its own instead
of falling through to the ordinary report.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" --apply-reconciliation N
```

Before touching anything it re-verifies the proposal is STILL trustworthy —
never trusting what the proposal claims about itself, since time may have
passed since `/cairn:reconcile` wrote it — and refuses the WHOLE apply,
fail-closed, on any of:

1. no `.cairn/conflicts.json` for phase N, or its own `phase` field doesn't
   match N (exit `2`).
2. phase N's corroboration verdict is no longer `"conflict"`, re-read via a
   REAL `cairn-reconcile.py collect N --json` run at apply-time (exit `0` —
   nothing to apply, not a failure).
3. the freshly re-collected `evidence_hash` no longer matches the
   proposal's own stored one — the tree moved between proposal and apply
   (exit `7`).
4. any citation fails a real `cairn-reconcile.py verify N` re-check (D-03 —
   one bad citation invalidates the whole proposal) (exit `7`).
5. any `recommended_action.type` falls outside the closed
   `{bd_close, bd_reopen, manual_review}` vocabulary — checked over every
   claim before anything is even enumerated (exit `7`).
6. any `bd_close`/`bd_reopen` claim's `recommended_action.issue` names a bd
   id carrying no `phase-N` label — the issue-provenance check: correct
   citations elsewhere in the same proposal never excuse a claim that
   targets an unrelated issue (exit `7`).

Only once every one of those passes does anything print: EVERY claim is
enumerated — statement, recommended action, what will happen, with
`manual_review` claims listed as "skipped (manual review, no automated
action)" — **before** the first `bd` subprocess call ever runs, so the
operator sees the full plan while it can still be stopped. `bd_close`/
`bd_reopen` claims are then applied one at a time (`bd close --reason` /
`bd update --status open --assignee ""`); `manual_review` claims never touch
bd. A close/reopen bd itself refuses is reported by id and reason and fails
the run (exit `7`) — never silent, the same "asked for it and did not get
it" discipline `--close-completed`'s own `close_failures` reporting already
applies one level up.

## Files touched

- **Reads:** `.planning/ROADMAP.md`, `.planning/STATE.md`, phase dirs
  (PLAN.md frontmatter, `NN-BEADS-MAP.md` freshness, `files_modified:`),
  beads state via `bd`, `cairn-status.py --json` (phase corroboration),
  `cairn-lease.py status --all --json` (lease staleness), git history
  (`git rev-parse --is-shallow-repository`, `git log` — the external-ref
  check reads this for its report even without `--link-refs`);
  `--apply-reconciliation` additionally reads `.cairn/conflicts.json` and
  shells to `cairn-reconcile.py collect`/`verify`
- **Writes:** nothing by default; with `--fix-labels`, issue labels via
  `cairn-relabel pair` (`bd update`); with `--close-completed`, issue status
  via `bd close --reason`; with `--link-refs`, `external_ref` via
  `bd update --external-ref`; with `--apply-reconciliation N`, issue status
  via `bd close --reason` / `bd update --status open --assignee ""` for
  each `bd_close`/`bd_reopen` claim only — never any git write

## Related

- [/cairn:migrate](migrate.md) — the fix for req-issue findings and unwired repos
- [/cairn:init](init.md) — when neither `.planning/` nor `.beads/` exists
- [/cairn:milestone](milestone.md) — carried-over issues show as transient orphan warns
- [/cairn:ship](ship.md) — the ship gate is the enforcement twin of these checks
