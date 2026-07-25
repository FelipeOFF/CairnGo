# /cairn:migrate

> Adopt an existing repo into cairn — detect GSD/beads state, dry-run a plan,
> confirm with the user, apply with resume journaling

## Usage

```text
/cairn:migrate
```

No arguments — the command detects which mode applies. All writes go through
the deterministic engine (`cairn-migrate.sh` → `cairn-migrate.py`); issues and
`.planning/` files are never hand-created during a migration. The full
user-facing guide, including the safety model and troubleshooting, lives in
[docs/migration.md](../migration.md).

**Hard rule, every mode:** never run `/gsd:new-project` or
`/gsd:new-milestone` over an existing `.planning/` — the engine backfills; a
GSD interview would re-interrogate at best and clobber at worst.

## What it does

**Step 0 — detect.**
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-migrate.sh" detect` prints the
state letter (line 1) and a description (line 2; `--json` for details):

| State | Meaning | Route |
|---|---|---|
| **A** | `.planning/` only | GSD-only backfill (mode A) |
| **B** | `.beads/` only | beads-only bootstrap (mode B) |
| **C** | both present, unwired | wire-up / reconcile (mode C) |
| **W** | both present, already wired | suggest [/cairn:doctor](./doctor.md), **stop** |
| **D** | neither | nothing to migrate; route to [/cairn:init](./init.md), **stop** |

Every mode follows the same shape: `detect → plan (dry-run) → confirm →
apply --yes`, and closes with [/cairn:doctor](./doctor.md).

### Mode A — GSD-only: backfill beads from `.planning/`

1. `plan` writes `.cairn/migrate-plan.json` and prints a summary grouped by
   step kind: epics per ROADMAP phase (+ deps from `**Depends on**`), one
   stamped + labeled child issue per requirement, closes for completed
   phases, `beads:` frontmatter appends, `migrated-todo` issues from
   `.planning/todos/pending/`, and per-phase map regeneration.
2. The plan is presented for confirmation before anything is applied. On a
   huge plan, counts per step kind plus a few examples are shown — never
   hundreds of pasted steps.
3. On yes: `apply --yes`. Exit `8` = partial failure — failed steps are
   listed on stderr and the journal (`.cairn/migrate-state.json`) records
   what completed; fix the cause and re-run `apply --yes`, which **resumes
   without duplicating** (handlers also dedup against live bd state on
   `(gsd.req, gsd.milestone)`).

### Mode B — beads-only: bootstrap `.planning/` from the backlog

1. `plan --milestone vX.Y` — the milestone name is asked first; with no
   `--milestone` there is no `.planning/` to infer from and it defaults to
   `v1.0` with a warning. If generated docs already exist and should be
   replaced, re-plan with `--force`.
2. The **proposed phase grouping** is presented for editing before anything
   is written: epics become phases in dependency order, open non-epic strays
   land in a trailing "Unscoped work" phase, and with no epics the plan falls
   back to topological "Stage N" layers. The grouping lives in
   `.cairn/migrate-plan.json` and is edited and re-presented until confirmed.
3. On yes: `apply --yes`. The engine never fabricates PLAN.md and never
   writes PROJECT.md — closed issues are recorded under
   `## Completed pre-cairn` in MILESTONES.md, and maps land in the created
   phase directories.
4. PROJECT.md comes from a short seeded interview (3–4 questions max) — or
   `/gsd:ingest-docs` / `/gsd:onboard` when the repo has rich existing docs.
   Explicitly **not** `/gsd:new-project`.
5. Plans come later: [/cairn:plan N](./plan.md) produces each PLAN.md and its
   `beads:` frontmatter.

### Mode C — both present, unwired: link and reconcile

1. Issues whose title contains a literal `CAT-NN` token are auto-linked;
   already-stamped issues count as wired; unmatched requirements become
   mode-A-style creates, parented to an existing phase epic when one exists —
   **mode C never creates epics**.
2. **Fuzzy candidates** (title similarity ≥ 0.6) land as `link_candidate`
   steps with status `pending_confirmation` — `apply` skips them until the
   user accepts each one (`params.confirmed: true` in the plan file).
3. **Orphans** (non-closed issues with no requirement match and no `phase-*`
   label) are routed per the user's answer: attach to a phase,
   `label-backlog`, or leave as `report`.
4. **Divergence report:** open matched issues in complete phases get
   `close_issue` steps gated behind `pending_confirmation` — each close of a
   pre-existing issue is confirmed **per-issue** (it may be mirrored
   externally). Closed issues in phases lacking a passed VERIFICATION are
   warnings only.
5. `apply --yes`; re-runs resume from the journal, so confirming more steps
   later and re-applying is safe.
6. Run `plan` once more afterwards: an issue wired via a just-confirmed fuzzy
   candidate only receives its divergence `close_issue` offer on this second
   pass.

### Always

- When `.cairn/sync.json` exists, run [/cairn:sync-pull](./sync-pull.md)
  after the migration (`apply` prints this reminder too) — mirror pushes
  never fire mid-run by design; migration writes reconcile at the end.
- Every mode closes with [/cairn:doctor](./doctor.md).

## Flags & arguments

Engine flags (passed to `cairn-migrate.sh`):

| Flag | Applies to | Meaning |
|---|---|---|
| `detect` \| `plan` \| `apply` | — | engine subcommands |
| `--json` | `detect` | machine-readable detection details |
| `--milestone vX.Y` | `plan` (mode B) | milestone name for the bootstrap |
| `--force` | `plan` (mode B) | re-plan, replacing previously generated docs |
| `--yes` | `apply` | apply without the script's own prompt |

## Exit codes

For `plan` / `apply`:

| Code | Meaning |
|---|---|
| `0` | ok |
| `2` | usage / wrong mode / no plan / abort |
| `5` | bd unavailable — install via [/cairn:init](./init.md) step "Ensure beads", then retry |
| `8` | partial apply failure — fix the cause, re-run `apply --yes` (resumes from the journal) |

## Examples

```text
/cairn:migrate       # repo with .planning/ only
→ detect: A — GSD-only backfill
→ plan: 4 epics, 12 create_issue, 5 close_issue (completed phases),
  12 frontmatter appends, 4 maps  → confirm? yes
→ apply --yes: 37/37 steps ok · run /cairn:doctor to confirm the wiring
```

```text
/cairn:migrate       # both present, unwired; apply hit a network error
→ apply exited 8 — 2 steps failed (listed on stderr)
→ fix, then re-run apply --yes: resumes from .cairn/migrate-state.json,
  0 duplicates (dedup on gsd.req + gsd.milestone)
```

## Files touched

- **Reads:** `.planning/` (ROADMAP, REQUIREMENTS, STATE, phase dirs),
  bd state via `bd … --json`, `.cairn/sync.json` (presence only).
- **Writes:** `.cairn/migrate-plan.json` (the dry-run plan — `plan` writes
  nothing else), `.cairn/migrate-state.json` (JSONL resume journal),
  `.beads/` via sequential `bd create` / `bd update` / `bd close`,
  `.planning/` generated docs (mode B: REQUIREMENTS / ROADMAP / STATE /
  MILESTONES), `NN-BEADS-MAP.md` per phase, `beads:` frontmatter appends
  (mode A).

## Related

- [/cairn:init](./init.md) — routes here from its step 0 (states A/B/C)
- [/cairn:doctor](./doctor.md) — the closing step of every mode
- [/cairn:sync-pull](./sync-pull.md) — reconcile mirrors after migrating
- [/cairn:new](./new.md) — greenfield alternative (state D)
- [/cairn:plan](./plan.md) — produces PLAN.md files after a mode B bootstrap
- [docs/migration.md](../migration.md) — full guide: safety model, troubleshooting
