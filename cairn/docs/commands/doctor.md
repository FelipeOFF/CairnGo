# /cairn:doctor

> Health-check the GSD↔beads wiring — run cairn-doctor, explain the report, route each finding to its fix

## Usage

```
/cairn:doctor
```

Under the hood:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" [--json] [--fix-labels]
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
4. Routes each finding to its remediation:
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
   - **orphans** (⚠) — issues labeled for a non-ROADMAP phase, or non-closed
     with no `phase-*` label → attach the right phase label + stamp, label
     `backlog`, or close.
   - **label-pairs** (⚠) — step 3 above (`--fix-labels`).
   - **claims-stale** (⚠) — in_progress + assigned issues outside the active
     phase → finish and close, release the claim, or correct `active_phase:`
     in STATE.md.
   - **bd-doctor** (✗) — beads' own diagnostics failed → run `bd doctor`
     directly and follow its advice.

   (A ninth check probes the minimum supported `bd` version; it needs no
   routing beyond upgrading bd.)
5. Re-runs the doctor after fixes to confirm a clean `ok` footer.

## Flags & arguments

| Flag | Effect |
| --- | --- |
| `--json` | Machine-readable report |
| `--fix-labels` | Repair label pairs via `cairn-relabel pair` (active milestone) before checking |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | All ok (warnings included) — or not-applicable: `.planning/` or `.beads/` absent (one side present → suggests `/cairn:migrate`; neither → `/cairn:init`) |
| `2` | Usage — notably `--fix-labels` refuses when candidates exist but the milestone is unresolvable: set `milestone:` in STATE.md frontmatter, or mark the in-progress ROADMAP milestone with 🚧, then retry |
| `5` | `bd` unavailable |
| `7` | At least one check **failed** (✗) |

## Examples

Routine health check:

```
/cairn:doctor
```

```
cairn doctor — root: ~/Projects/app · milestone: v1.0 · active phase: 3
✓ req-issue          ✓ frontmatter-ids     ⚠ maps-fresh (phase 2 stale)
✓ superseded-released ✓ orphans            ✓ label-pairs
✓ claims-stale       ✓ bd-doctor
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
  `cairn-relabel pair` (`bd update`)

## Related

- [/cairn:migrate](migrate.md) — the fix for req-issue findings and unwired repos
- [/cairn:init](init.md) — when neither `.planning/` nor `.beads/` exists
- [/cairn:milestone](milestone.md) — carried-over issues show as transient orphan warns
- [/cairn:ship](ship.md) — the ship gate is the enforcement twin of these checks
