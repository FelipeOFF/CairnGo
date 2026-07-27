# /cairn:doctor

> Health-check the GSD↔beads wiring — run cairn-doctor, explain the report, route each finding to its fix

## Usage

```
/cairn:doctor [--fix-labels] [--close-completed] [--json]
```

Flags typed by the user are appended to the script call. Under the hood:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" [--json] [--fix-labels] [--close-completed]
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
5. Routes each finding to its remediation:
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

   (A tenth check probes the minimum supported `bd` version; it needs no
   routing beyond upgrading bd.)
6. Re-runs the doctor after fixes to confirm a clean `ok` footer.

## Flags & arguments

| Flag | Effect |
| --- | --- |
| `--json` | Machine-readable report |
| `--fix-labels` | Repair label pairs via `cairn-relabel pair` (active milestone) before checking |
| `--close-completed` | Bulk-close non-closed issues in ROADMAP-complete phases via `bd close --reason` before checking (idempotent, prints each closed id; sweeps as a fixpoint so parent/blocker chains drain in one run, and exits `7` if bd refuses one) |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | All ok (warnings included) — or not-applicable: `.planning/` or `.beads/` absent (one side present → suggests `/cairn:migrate`; neither → `/cairn:init`) |
| `2` | Usage — notably `--fix-labels` refuses when candidates exist but the milestone is unresolvable: set `milestone:` in STATE.md frontmatter, or mark the in-progress ROADMAP milestone with 🚧, then retry |
| `5` | `bd` unavailable |
| `7` | At least one check **failed** (✗) — including `--close-completed` leaving a target unclosed because bd refused it (reported on the phase-complete-open check with bd's reason) |

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
ok (1 warning)
```

Repair label pairs, then re-check:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" --fix-labels
```

## Files touched

- **Reads:** `.planning/ROADMAP.md`, `.planning/STATE.md`, phase dirs
  (PLAN.md frontmatter, `NN-BEADS-MAP.md` freshness), beads state via `bd`
- **Writes:** nothing by default; with `--fix-labels`, issue labels via
  `cairn-relabel pair` (`bd update`); with `--close-completed`, issue status
  via `bd close --reason`

## Related

- [/cairn:migrate](migrate.md) — the fix for req-issue findings and unwired repos
- [/cairn:init](init.md) — when neither `.planning/` nor `.beads/` exists
- [/cairn:milestone](milestone.md) — carried-over issues show as transient orphan warns
- [/cairn:ship](ship.md) — the ship gate is the enforcement twin of these checks
