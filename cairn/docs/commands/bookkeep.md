# cairn-bookkeep

> Close a phase in one command — mark it, mark its requirements, move the
> table, the footer, the plan checkboxes and the STATE counters, regenerate
> the map and release the lease. And say what it would not write.

This page documents a **script**, not a slash command. `/cairn:autonomous`
and the end-of-phase path invoke it; you can also run it by hand. (Do not
confuse `cairn-bookkeep.sh reconcile` with `/cairn:reconcile` — the latter
investigates a phase *conflict* between bd and the planning files and only
ever writes a proposal. This one edits the planning files themselves.)

## Usage

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-bookkeep.sh" close <N> [--apply] [--no-tracker] [--json] [--planning-dir DIR]
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-bookkeep.sh" reconcile [--apply] [--json] [--planning-dir DIR]
```

**Reading is the default; writing needs `--apply`.** That is the house
pattern (`cairn-doctor.sh --apply-reconciliation`) and it is what keeps an
autonomous loop from writing by accident.

`CAIRN_NOW` overrides the clock (`2026-08-04`, or a full ISO stamp). Unset
means the real one. A value that does not start with `YYYY-MM-DD` is a usage
error rather than a garbage date written into three files.

## What `close <N> --apply` does

| # | Edit | Where |
|---|------|-------|
| 1 | the phase's checkbox `[ ]` → `[x]`, plus ` — completed <date>` | `ROADMAP.md` |
| 2 | the checkbox of every requirement whose phases are all complete | `REQUIREMENTS.md` |
| 3 | those requirements' status cell → `Complete`, and a row for an active requirement that has none | the coverage table |
| 4 | the coverage footer, recounted | the coverage table |
| 5 | each `NN-MM-PLAN.md` checkbox whose `NN-MM-SUMMARY.md` is on disk | `ROADMAP.md` |
| 6 | the STATE counters (list below) | `STATE.md` |
| 7 | the phase map and the phase lease | `cairn-map.py` / `cairn-lease.py` |

`reconcile --apply` does 2 to 6 and **marks no phase complete**: the way to
repair drift that already exists without pretending a phase just closed.

Running either twice writes nothing the second time. That is not a nicety —
in an autonomous loop the second run is the normal case.

## The derivation rule

One authority, five derived views. Fix the authority; the views follow.

- **authority** — the phase's checkbox line in `ROADMAP.md`.
- The phase's requirements come from its `**Requirements**:` line, the same
  dialect `cairn-map.py` reads. Never the parenthesis on the checkbox line.
- **derived 1** — a requirement is complete when **every** phase carrying it
  is complete.
- **derived 2** — its checkbox in `REQUIREMENTS.md` reflects derived 1.
- **derived 3** — its row in the coverage table reflects derived 1.
- **derived 4** — the footer's `N requisitos, N mapeados.` counts how many
  requirements are active and how many of them the table maps. Two different
  numbers: `35 requisitos, 33 mapeados.` says exactly where the gap is.
- **derived 5** — each plan checkbox reflects whether its `-SUMMARY.md` is on
  disk.

Without this written down, the next person repairs the wrong side and the
command starts fighting them.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | done, or nothing to change |
| 2 | usage error: bad flags, a phase number matching two checkbox lines, two footer lines inside the coverage section, a malformed `CAIRN_NOW` |
| 3 | read mode found something to change (mirrors `cairn-map.py`'s "stale") |
| 4 | no checkbox line for that phase number, in a roadmap that names phases. A roadmap naming none is out-of-scope (see below), not exit 4 |
| 5 | `bd` is not on PATH and `--no-tracker` was not passed. Returned **before** any write: the three files are byte-identical |

## `close N` in a tracker-owned repo

The file decides only while it names a phase. A `.planning/ROADMAP.md` that
carries no phase checkbox at all is the index the import archived — this
repository's own, after v1.7 — and `close N` treats it exactly like no
roadmap: `documents.status = not-applicable`, scope `out-of-scope`, exit 0,
nothing written. (Measured 2026-08-26: it used to die with exit 4 on every
phase of a migrated repo, and the autonomous checkpoint closed carriers by
hand.)

What still closes with the phase, under `--apply`, in this order: the lease
is retired, the worktree is cleaned, and the **phase carrier is closed**
(`bd close <id> --reason "phase N closed by cairn-bookkeep"`), reported as
`tracker :: carrier :: closed <id>` and under `tracker.carrier` in `--json`
(`state`: `closed`, `already-closed`, `open-work`, `none`, `failed`). A
non-closed bead of the phase besides the carrier leaves the carrier open and
is named with its id — the exit does not change, because this command is not
a gate; barring is `cairn-gate.sh`'s 6. A phase without a carrier is reported
as `none`, never given one: creating it is `cairn-record`'s job.

## The STATE keys it writes, exhaustively

`current_phase`, `current_phase_name` (both only on `close`),
`progress.total_phases`, `progress.completed_phases`, `progress.total_plans`,
`progress.completed_plans`, `progress.percent`, `last_updated`,
`last_activity`.

Each by replacing the value of its own line — indentation, quoting and key
order preserved. A key the file does not already have is **not created**; it
is named under `skipped`. The two timestamps ride along with a real change
and never alone, because a run that changed nothing did not produce activity.

`last_activity_desc` and `stopped_at` are free text a person wrote, and are
never rewritten — but `reconcile` **names** them (`state-narrative-stale`)
when the numbers inside them contradict the computed ones. A field nobody
recalculates and nobody reports is how the coverage footer reached 29.

`current_phase` versus `active_phase` is **open**, addressed in
`CairnGo-rq0`: the file has `current_phase` and no `cairn` script reads it,
while five read `active_phase`. This command writes the key the file already
has and invents none. Which dialect wins is grooming, not mechanics.

## Two config keys (`.cairn/config.json`, `/cairn:config`)

| Key | Effect here |
|-----|-------------|
| `bookkeep.auto_commit` | `true` → after a successful `--apply`, stage **exactly** the files this run planned (never `-A`) and make one `chore(cairn): bookkeeping fase N` commit. Default `false`: written, uncommitted, and the report prints the command |
| `ship.pr_scope` | becomes the report's `pr_due`: `true` for `phase`, `false` for `milestone` and `none` |

A git failure is reported, never fatal: the edits are already on disk and
correct, and the commit is a convenience on top of them.

## What it does not do

- **It is not a gate.** A missing artifact is a named entry under `skipped`
  or `unresolved`, never a refusal. Barring a phase belongs to
  `cairn-gate.sh`, which already exits 6. (Measured: gsd-tools'
  `phase complete 20` — the operation a hand actually performs — refused to
  run and wrote zero bytes because the phase's verification came back
  `human_needed`.)
- **It never un-marks anything.** Marking complete is corroborated by an
  artifact that exists; un-marking asserts an *absence*, and an absence has
  many causes. A view ahead of its authority is reported as `*-ahead` and
  left alone.
- **It never expands an ellipsis.** A `**Requirements**: AUTO-01 … AUTO-08`
  line is named as `requirements-line-unreadable` and nothing is derived from
  the ids it does not state — including the phase cell of a row it therefore
  will not insert.
- **It never reads or writes the prose body of `STATE.md`.** Measured cause:
  `state record-session` took `Phase: 18` out of that body and wrote it over
  `current_phase: 29`, naming a phase of an archived milestone.
- **It never reflows markdown.** Every write is a line replacement or a line
  insertion at a planned position. Measured contrast: `roadmap
  update-plan-progress 20` produces +31/−4 to flip three checkboxes, because
  `_normalizeMd` runs over every `.md` the gsd-tools writes.
- **It never decides a push.** `pr_due` is a report field; `/cairn:ship`
  decides.
