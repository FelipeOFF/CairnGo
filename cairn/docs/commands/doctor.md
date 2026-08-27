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

   **A repo with nothing written down yet.** Run the doctor on a project whose
   `ROADMAP.md` lists no phase and you get several `⊘` and an `INCOMPLETE`
   footer — and exit `0`. That is the report working: `req-issue` never
   compared a requirement to an issue, `orphans` never compared a phase label
   to a roadmap. Before, all of them said `✓`. Nothing is broken; write the
   roadmap and each one starts comparing.

   **How to tell in advance which of your checks will read `⊘`.** A count of
   zero means two different things, and the doctor now distinguishes them:

   - **`⊘` `no-input`** when the zero means *a guarantee this project wants
     was never verified*, and there is something you can do about it: no
     `**Requirements**:` line to read, no phase directory to find a map in,
     no `PLAN.md` carrying the `beads:` stamp.
   - **`✓`** when the zero makes the answer genuinely true and there is
     nothing to do: no stale lease *because nothing is leased*, no unpaired
     label *because every label is paired*, no issue open in a completed
     phase *because no phase is complete yet*.

   The second group is not an oversight — phase 23 evaluated each one and
   left it alone, with the reason written beside the code that returns it.
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
   - **orphans** (⚠; ⊘ when it has no input) — issues labeled for a
     non-ROADMAP phase, or non-closed with no `phase-*` label → attach the
     right phase label + stamp, label `backlog`, or close. Two independent
     axes: the phase-label one needs a ROADMAP that lists phases and reads
     `⊘` with scope `no-input` when it has none, while the unlabeled-issue
     axis keeps running either way — so a `⚠` over an empty roadmap is a real
     finding and the detail still says the other axis could not run.
     **Exempt: an issue that is closed AND carries at least one `m-*` label
     AND has every one of them archived under `.planning/milestones/`.** That
     is what makes the count fall back to zero at the end of a cycle instead
     of growing at every milestone until the check is noise — measured in
     cairn's own repo, all 61 findings were closed issues of the four
     archived milestones. All three conditions, and **all** the milestone
     labels rather than any one of them, so three things keep warning: an
     issue still **open** on a cycle that already closed (live work, worth
     reporting), a closed issue with **no `m-*` label** (no evidence of
     archiving — exempting there would be approving without comparing), and
     an issue **carried into the active milestone**, which
     [milestone.md](milestone.md) documents as a transient orphan until the
     new roadmap places it. Nothing is exempted in silence: the detail always
     says how many were suppressed, because a count that quietly reaches zero
     is indistinguishable from an axis somebody switched off.
   - **label-pairs** (⚠) — step 3 above (`--fix-labels`).
   - **milestone-carrier** (✗) — every OPEN cycle (an `m-*` label with at
     least one non-closed bead) has exactly one milestone carrier: the bead
     with the marker label `milestone` + `m-vX.Y` and no `phase-N`, created
     by `/cairn:milestone new`. **None** → run the `bd create` the item
     prints (a failure since 4.1; 4.0 only warned, so a cycle opened under
     3.x had one release to catch up). **Two or more** → one cycle, one
     bead: close or relabel the extra, then re-run. Closed cycles are history
     and are never asked.
   - **planning-writes** (⊘ out-of-scope; ⚠) — a `.md` file git sees as new
     or modified under `.planning/phases/` in a repo that has `.beads/`: a
     document written where the bead is the source. Record it with the
     `cairn-record.sh <kind>` the item names (spec, context, plan, summary,
     verification, review…) and `git rm` the file. `⊘` when there is no
     `.planning/phases/` at all.
   - **jira-links** (⊘ out-of-scope; ⚠; ✗) — `⊘` until `.cairn/sync.json`
     enables a `jira` backend (`/cairn:sync-config`); that is not a clean
     bill, it is "nothing to compare". With a backend: **gap** (⚠) — an open
     cycle's milestone carrier or an open phase's carrier with no
     `external_ref` → `/cairn:jira link --milestone vX.Y` / `--phase N`;
     **duplicate** (✗) — two beads share one `jira-<KEY>` → `/cairn:jira`
     asks which bead the card is about and offers another card for the
     other; **absent** (✗) — a linked key the tracker does not know, asked
     through `CAIRN_JIRA_FETCH` or REST with the backend's token env vars →
     fix the key (`unlink`, then `link` the right card); **epic drift** (⚠) —
     the story's live parent is not the cached epic → re-link to refresh the
     cache. An **existence … not checked** item means neither road was open;
     in a session `/cairn:jira audit` asks the MCP instead. The check never
     writes.
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
   - **gsd-capability** (⚠/✗) — the vendored GSD runtime is broken, or an
     external GSD plugin is still installed beside it. **This check inverted
     in v1.6** (phase 37): it used to ask whether the cairn capability had
     registered against an installed `gsd-core`, and it told you to *install*
     that plugin. cairn now ships the GSD runtime inside itself, so an
     installed `gsd-core` is something to *uninstall*. Three outcomes, in the
     order the check decides them — and the order is deliberate, because a
     machine migrating from v1.5 hits more than one of them at once:
     - *the vendored GSD runtime is incomplete* (✗, first) — `cairn/gsd/` is
       missing its `MANIFEST.json` or the files that manifest lists. This is a
       defect of the **cairn install**, not of your environment, and no
       external plugin can supply it → `claude plugin install cairn@cairngo`,
       then `/reload-plugins`. Checked first because no statement about the
       environment is worth anything while the plugin itself is broken.
     - *an external GSD plugin is still installed* (✗, second) — `gsd-core`,
       the 4.x `gsd`, or both, named individually in the detail line. Two
       lineages must not answer at once: the installed plugin serves `/gsd:*`
       with the pre-bd workflows while `/cairn:*` serves bd, and that window is
       the defect class the whole v1.5 cycle chased →
       `claude plugin uninstall <name>`, then `/reload-plugins`.
     - *leftover capability state* (⚠, last) — `.gsd/capabilities/cairn/` or
       `.gsd-capabilities.json` from a `/cairn:init` that ran before v1.6. The
       capability was archived (see `cairn/capability/ARCHIVED.md`): nothing
       reads these files → `rm -rf` the paths named in the detail line.

     The residue is a ⚠ and never a ✗, for the reason checks 8 and 14 already
     record: leftover files are friction, not a state inconsistency, and an
     exit `7` spent on friction stops meaning anything. It is evaluated **last**
     for a related reason — a machine that migrated has both the install and
     the residue, and checking residue first would report the finding that
     needs action as a warning. The doctor names the cleanup; it never deletes.

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

   - **response-language** (⚠) — the language chosen at install and the
     language GSD hands to its subagents have stopped agreeing.
     `/cairn:init` records the answer in
     `.cairn/config.json:agents.response_language` — it has to, because when
     it asks, `.planning/` does not exist yet and cairn is forbidden from
     creating it — and `cairn-config.sh set` propagates that answer into
     `.planning/config.json:response_language`, the key GSD's own workflows
     read, the moment that file exists. Two states are worth a line: the
     answer was recorded and **never propagated** (the post-hand-off re-run
     was skipped), or the two files carry **different** values. Both report
     the exact `set` command that closes it, and the second one also names
     which value governs — GSD's, because it is read by GSD's workflows as
     well as by cairn.

     Never a failure. A divergence breaks nothing mechanically; it makes
     half the subagents of a run answer in one language and half in another,
     which is exactly what went unnoticed for a whole milestone and exactly
     why it belongs in a health report rather than in an exit code. The
     doctor reports it and writes neither file.

   - **phase-landed** (⚠; ✗ for an archived cycle; ⊘ `out-of-scope` with no
     control branch) — a phase the roadmap calls **complete** whose commits
     are not on the branch everything has to reach. Showing the information
     and never asking for it trains everybody not to look, so this is the
     asking half. MEASURED 2026-08-06 on cairn's own repository: nine
     roadmap-complete phases were not on `origin/main` (145 commits ahead) and
     the doctor said nothing about any of them.

     The whole question is read **once** from `cairn-land.sh report --json`
     through the `CAIRN_LAND` seam — the doctor reads no git of its own, the
     same way check 3 defers to `cairn-map.py` and check 17 to
     `cairn-bookkeep.py`. Two readers of one fact is the defect this milestone
     has already paid for twice.

     The severity split is the point. A complete phase of the **open** cycle
     that has not been pushed yet is `⚠`: unpushed work is the ordinary state
     of anybody mid-cycle, it is friction and not inconsistency, and exit `7`
     spent on friction stops meaning anything. A complete phase of an
     **archived** milestone that never arrived is `✗`: a cycle was closed over
     work the control branch does not have, and that is a claim the repository
     cannot support. Both route to [/cairn:ship](ship.md); the check writes
     nothing.

     A complete phase the local history cannot place — no commit touched its
     directory and none named it in a conventional-commit scope — is listed by
     name, prefixed `unknown ::` and carrying its reason, and it raises
     **nothing**. Measured: phases 7-12 of this repository predate the scope
     convention and are attributable by neither source, and charging that
     would hand every long-lived repo a permanent finding about history nobody
     is going to rewrite. Named without being charged is the honest middle.

   - **plan-counters** (✗; ⊘ `no-input` when `STATE.md` carries no
     `progress:` block with both keys) — a `STATE.md` claiming more plans
     completed than it has. MEASURED 2026-08-06 on cairn's own repository,
     right after the close of phase 22: `total_plans: 39` against
     `completed_plans: 47`, and `47 = 39` plan summaries `+ 8` **phase**
     summaries. The glob that produced the second number matched
     `NN-MM-SUMMARY.md` and `NN-SUMMARY.md` alike, while its `*-PLAN.md` pair
     matched only plans, because a phase has no `NN-PLAN.md`. The two look
     symmetric and the naming is not.

     This check **compares and never recomputes**, and that is the whole
     design. The writer (`cairn-bookkeep close`) and the verifier
     (`cairn-bookkeep reconcile`) derive `completed_plans` with the *same*
     rule, so they agreed — `reconcile` returned `disagreements: []` while
     printing both contradictory numbers inside one JSON object. A check that
     recounted the tree with that rule would agree too, in the act of trying to
     catch it. So it reads the two numbers exactly as written and asks the one
     question neither glob can answer about itself: can more plans be finished
     than exist? `completed > total` is impossible by arithmetic, not by
     convention.

     A missing key is `⊘ no-input`, never a failure — the `progress:` block is
     GSD's, and a repository that never grew one has nothing inconsistent about
     it. (A repository with no `.planning/` at all never reaches this check —
     the doctor registers zero checks there.) The finding routes to
     `cairn-bookkeep.sh reconcile`, which owns the recount; the check writes
     nothing.

   - **state-dialect** (✗; ⊘ `out-of-scope` when `STATE.md` carries fewer
     than two readable phase keys) — a `STATE.md` whose two phase keys name
     two different phases. MEASURED 2026-08-05 on cairn's own repository:
     `grep -rn current_phase cairn/` returned **zero readers**, while five
     surfaces read `active_phase` (`cairn-status.py`, `cairn-doctor.py`,
     `cairn-lease.py`, `cairn-migrate.py`, `hooks/session-start.sh`). cairn
     was writing the key it does not read, and GSD writes the key cairn does
     not read either.

     The decision (2026-08-06) is **additive**: `cairn-bookkeep close` now
     writes `active_phase` beside `current_phase`, reading stays on
     `active_phase`, no reader changes and no repository is migrated. This
     check is the **stated counterpart** of the duplicated key, not an extra:
     two keys that must agree and that nobody compares is the defect this
     cycle measured four separate times — the coverage footer against its
     table, `req-issue` against `req-ledger`, `completed_plans` against
     `total_plans`, and two hand-kept numbers inside one document. Writing the
     pair without comparing it would have created the fifth case in the act of
     fixing the fourth.

     It **compares and never derives**. A phase recomputed from the roadmap
     would agree with whichever key the same rule wrote, so the two values are
     read exactly as written and asked the one question neither can answer
     about itself: do they name the same phase?

     Fewer than two readable keys is `⊘ out-of-scope`, never `no-input`, and
     the distinction is load-bearing: a file with one key **has no dialect
     disagreement to have** — speaking one dialect is the state AUTO-10 is
     named after — the missing `active_phase` is already reported as
     `no-input` by `claims-stale`, and a second `no-input` would drop `.ok` in
     every GSD repository that has never run `cairn-bookkeep`, a permanent
     false red. The finding routes to `cairn-bookkeep.sh close <N> --apply`,
     which writes both keys; the check writes nothing.

   - **issues-recoverable** (✗; ⚠ when the tracked export is behind the
     store; ⊘ `no-input` when bd is unavailable or the store is empty; ⊘
     `out-of-scope` when there is no `.beads/`) — whether the issue store
     survives this machine. Measured on this repository on 2026-08-07:
     `.beads/embeddeddolt` 27 MB inside `.gitignore`, `.beads/issues.jsonl`
     absent, `.beads/backup/` 13 MB and also ignored, and zero `refs/dolt`
     among the 42 refs on the remote. **A clean clone recovered none of the
     176 issues** — while `CLAUDE.md:25` had been stating in writing, for
     weeks, that the sync used `refs/dolt/data` and that the JSONL was a
     passive export. Neither existed. Nobody lied: bd ships `export.auto`
     disabled and commented out, so the file that sentence promises is never
     born until somebody enables it.

     It reads **what git tracks**, never the configuration: `export.auto:
     true` proves an intent, and a tracked path proves a file, so the check
     compares the exported ids against the live store instead of believing
     either. Absence is `✗` and lag is `⚠`, because a stale export still
     recovers most of the history while a missing one recovers nothing, and
     spending exit 7 on lag is how exit 7 stops meaning anything.

     The finding routes to enabling `export.auto` plus `git-add` in
     `.beads/config.yaml`, then `bd export -o .beads/issues.jsonl` and
     committing the file. **Green here means the issue records have a way
     back, never the database**: the JSONL carries no Dolt branch, no commit
     history and no working set, so full recovery still needs a Dolt remote.

   - **export-identity** (✗ for a session id anywhere and for a hostname or
     an absolute home path a HUMAN typed; ⚠ for the same value written by a
     TOOL; ⊘ `no-input` when no export is tracked, where `issues-recoverable`
     already owns the gap) — what the tracked export PUBLISHES. The sibling
     of `issues-recoverable`: that check proves the export exists and can be
     recovered from, this one proves it is safe to hand to every clone, fork
     and mirror of a public repository.

     Measured on this repository on 2026-08-11: two lease records carrying
     `socket.gethostname()` and an absolute worktree path, both written by
     `cairn-lease.py`, plus 161 journal records carrying the same hostname.
     The v1.5 security sweep had already walked this tree and missed all of
     them, because it looked for session ids and stopped there.

     The split by AUTHOR is the whole design. Prose is `✗`: a human wrote
     it, a human clears it with `bd update`. A tool-written value is `⚠`,
     because scrubbing it by hand is undone by the next run that writes it
     — the fix belongs at the source, in the surface that records the
     value, and a check that spends exit 7 on a value the user cannot
     durably clear teaches people to ignore exit 7. A session id is `✗`
     wherever it sits and whoever wrote it; that one is never routine.

     The finding routes to `cairn_identity.py` for a tool-written value
     (`machine_id()` for a hostname, `collapse_home()` for a home path) and
     to `bd update` for prose. The placeholders this project argues WITH —
     `/Users/x`, `/home/user`, `USERNAME` — are deliberately not findings,
     or this page would fail its own check.

   (Check 0, `bd-version`, runs first but needs no routing beyond
   upgrading bd. This page deliberately states no total: the count changes
   almost every cycle, and a hand-kept total here has already aged twice.)
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

A machine that still carries the pre-v1.6 plugin reports it plainly:

```
✗ gsd-capability     an external GSD plugin is still installed —
                     gsd-core@cairngo. cairn no longer requires one, and two
                     lineages must not answer at once
                     Fix: claude plugin uninstall gsd-core@cairngo
                     then /reload-plugins
[cairn-doctor] FAIL — 15 ok, 2 not-applicable, 0 warning(s), 1 failure(s)
```

Repair label pairs, then re-check:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" --fix-labels
```

## Applying a reconciliation proposal (ESC-03)

`--apply-reconciliation N` is the human-invoked, separate command that
applies a semantic-escalation reconciliation proposal `/cairn:reconcile N`
wrote to `.cairn/conflicts.json` (Phase 17). It is not one of the 22 checks
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
