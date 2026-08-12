# /cairn:plan

> Plan a phase — GSD plan-phase plus beads map reconciliation

## Usage

```text
/cairn:plan <phase-number> [--auto] [--research] [--skip-research] [--tdd]
```

The phase number is required; anything after it is passed through to
`/gsd:plan-phase` (see Flags). Only the bare phase number reaches `cairn-map`
and the labels. `cairn-map` resolves the phase directory itself:
`3` matches `3-auth`, `03-auth`, and a project-code-prefixed
`myproj-03-auth`.

## What it does

1. **Regenerate the phase's beads map, then read it.** The map is generated
   from bd state — never hand-edit between the `<!-- cairn:generated:* -->`
   markers (manual notes *outside* the markers survive regeneration):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>
   ```
   The script prints the map's path; the whole `*-BEADS-MAP.md` file is read,
   including any manual notes outside the markers. Exit 5 means bd is
   unavailable — fallback: read the existing file as-is (resolve the phase
   directory by its numeric prefix under `.planning/phases/`).
2. **Run `/gsd:plan-phase <N>` plus any passthrough flags** — the normal GSD
   planning flow. (With the
   capability installed, its `plan:post` hook also writes `beads:`
   frontmatter and refreshes the map when plain `/gsd:plan-phase` is used.)
3. **Reconcile divergence.** Where a bd issue conflicts with the phase
   `CONTEXT.md`, **CONTEXT wins** — the conflict is flagged ⚠ (outside the
   markers) and the issue is updated via `bd update` with a dated note
   pointing at the GSD doc; the issue text is never silently followed.
   Issues are created for any unmapped requirement (label pair
   `m-<milestone>,phase-<N>` + `gsd` metadata stamp), then the map is
   regenerated. `cairn-map.sh <N> --check` verifies it is current (exit 3 +
   diff when stale).
4. **Link plans to issues:** each generated `PLAN.md` gets its `beads:`
   frontmatter set to the bd ids it advances.

Next: [/cairn:work N](./work.md).

### Side effects

- `NN-BEADS-MAP.md` regenerated (twice, when reconciliation creates issues).
- `bd update` on diverging issues (dated reconciliation note),
  `bd create` for unmapped requirements — both fire the plugin's PostToolUse
  hook (mirror push + map refresh) as with any bd write.
- `beads:` frontmatter written into each generated `PLAN.md`.
- No commits are made by the command itself.

## Flags & arguments

| Argument / flag | Meaning |
|---|---|
| `<phase-number>` | required positional — the phase to plan; the only part `cairn-map.sh` and the labels see |
| `--auto` | passed through to `/gsd:plan-phase` |
| `--research` / `--skip-research` | passed through to `/gsd:plan-phase` |
| `--gaps` | passed through to `/gsd:plan-phase` |
| `--skip-verify` | passed through to `/gsd:plan-phase` |
| `--prd <file>` | passed through to `/gsd:plan-phase` |
| `--reviews` | passed through to `/gsd:plan-phase` |
| `--text` | passed through to `/gsd:plan-phase` |
| `--tdd` | passed through to `/gsd:plan-phase` |
| `--check` (of `cairn-map.sh`) | verify map freshness instead of regenerating; exit 3 + diff when stale |

## Exit codes

These belong to `cairn-map.sh`, which the command drives:

| Code | Meaning |
|---|---|
| `0` | map generated / up to date |
| `3` | (`--check` only) map is stale — a diff is printed |
| `5` | bd unavailable — fall back to reading the existing map file as-is |

## Examples

```text
/cairn:plan 3
→ cairn-map.sh 3 → .planning/phases/03-auth/03-BEADS-MAP.md (regenerated)
→ /gsd:plan-phase 3 … 2 plans created
→ reconcile: app-12 diverged from CONTEXT.md → ⚠ flagged, bd update with
  dated note · 1 unmapped requirement → bd create (stamped, labeled)
→ 03-01-PLAN.md beads: [app-12] · 03-02-PLAN.md beads: [app-14, app-15]
→ next: /cairn:work 3
```

```text
/cairn:plan 3        # bd not installed on this machine
→ cairn-map.sh exited 5 (bd unavailable) — reading the existing
  03-BEADS-MAP.md as-is; reconciliation against live bd state is skipped
```

## Files touched

- **Reads:** `.planning/phases/<dir>/*-BEADS-MAP.md`, phase `CONTEXT.md`,
  bd state via `bd … --json`.
- **Writes:** `*-BEADS-MAP.md` (generated region), `PLAN.md` `beads:`
  frontmatter, `.beads/` via `bd update` / `bd create`.

## Related

- [/cairn:work](./work.md) — execute the phase just planned
- [/cairn:verify](./verify.md) — cross-check after execution
- [/cairn:new](./new.md) — where the issues and maps come from initially
- [/cairn:milestone](./milestone.md) — roadmap-level lifecycle around phases
