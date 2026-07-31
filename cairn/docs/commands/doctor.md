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

## What it does

1. Runs `cairn-doctor.sh` (wrapper over `cairn-doctor.py`). The report opens
   with a header (repo root, milestone, active phase), then one `✓`/`⚠`/`✗`
   line per check with itemized findings, then an `ok`/failure footer.
2. Explains the report to the user: failures (`✗`) block, warnings (`⚠`) are
   advisories, and warnings never change the exit code.
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
   - **claims-stale** (⚠) — in_progress + assigned issues outside the active
     phase → finish and close, release the claim, or correct `active_phase:`
     in STATE.md.
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

   (Check 0, `bd-version`, runs first but needs no routing beyond
   upgrading bd — fifteen checks in total.)
7. Re-runs the doctor after fixes to confirm a clean `ok` footer.

## Flags & arguments

| Flag | Effect |
| --- | --- |
| `--json` | Machine-readable report |
| `--fix-labels` | Repair label pairs via `cairn-relabel pair` (active milestone) before checking |
| `--close-completed` | Bulk-close non-closed issues in ROADMAP-complete phases via `bd close --reason` before checking (idempotent, prints each closed id; sweeps as a fixpoint so parent/blocker chains drain in one run, and exits `7` if bd refuses one) |
| `--link-refs` | Backfill closed issues lacking `external_ref` from an unambiguous git match via `bd update --external-ref` (idempotent, prints each linked id; skipped entirely on a shallow clone) |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | All ok (warnings included) — or not-applicable: `.planning/` or `.beads/` absent (one side present → suggests `/cairn:migrate`; neither → `/cairn:init`) |
| `2` | Usage — notably `--fix-labels` refuses when candidates exist but the milestone is unresolvable: set `milestone:` in STATE.md frontmatter, or mark the in-progress ROADMAP milestone with 🚧, then retry |
| `5` | `bd` unavailable |
| `7` | At least one check **failed** (✗) — including `--close-completed` leaving a target unclosed because bd refused it (reported on the phase-complete-open check with bd's reason), and a `blocks`-severity phase-corroboration conflict |

## Examples

Routine health check:

```
/cairn:doctor
```

```
cairn doctor — root: ~/Projects/app · milestone: v1.0 · active phase: 3
✓ req-issue          ✓ frontmatter-ids     ⚠ maps-fresh (phase 2 stale)
✓ superseded-released ✓ phase-complete-open ✓ orphans
✓ label-pairs        ✓ claims-stale        ✓ bd-doctor
✓ gsd-capability      ✓ phase-corroboration ✓ phase-artifacts
✓ external-ref        ✓ lease-stale
ok (1 warning)
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

## Files touched

- **Reads:** `.planning/ROADMAP.md`, `.planning/STATE.md`, phase dirs
  (PLAN.md frontmatter, `NN-BEADS-MAP.md` freshness, `files_modified:`),
  beads state via `bd`, `cairn-status.py --json` (phase corroboration),
  `cairn-lease.py status --all --json` (lease staleness), git history
  (`git rev-parse --is-shallow-repository`, `git log` — the external-ref
  check reads this for its report even without `--link-refs`)
- **Writes:** nothing by default; with `--fix-labels`, issue labels via
  `cairn-relabel pair` (`bd update`); with `--close-completed`, issue status
  via `bd close --reason`; with `--link-refs`, `external_ref` via
  `bd update --external-ref` — never any git write

## Related

- [/cairn:migrate](migrate.md) — the fix for req-issue findings and unwired repos
- [/cairn:init](init.md) — when neither `.planning/` nor `.beads/` exists
- [/cairn:milestone](milestone.md) — carried-over issues show as transient orphan warns
- [/cairn:ship](ship.md) — the ship gate is the enforcement twin of these checks
