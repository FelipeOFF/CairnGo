---
description: Health-check the GSD↔beads wiring — run cairn-doctor, explain the report, route each finding to its fix
argument-hint: "[--fix-labels] [--close-completed] [--json]"
---

Audit the repo's cairn wiring and walk the user through fixing what it finds.

## 1. Run the doctor

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" $ARGUMENTS
```

Any flags the user typed (`--fix-labels`, `--close-completed`, `--json`) are
in $ARGUMENTS and go straight onto the call; `--json` gives machine output. Exit codes: `0` all ok — warnings included, they
never change the exit code — or not-applicable (`.planning/` or `.beads/`
absent); `5` bd unavailable; `7` at least one check **failed** — including a
`--close-completed` that bd refused (step 4).

Not-applicable: relay the printed note — when exactly one side exists it
suggests `/cairn:migrate`; when neither exists, route to `/cairn:init`.

## 2. Explain the report

Header shows root, milestone, and active phase; then one ✓/⚠/✗ line per check
with itemized findings. Failures (✗) block; warnings (⚠) are advisories. Give
the user the short version: what is inconsistent and what fixes it.

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

- **req-issue** (✗) — a ROADMAP requirement has no stamped, phase-labeled
  issue: run `/cairn:migrate` (mode C wires or creates), or for a one-off
  create it yourself **with the stamp**:
  `bd create "CAT-NN: <title>" -l m-<m>,phase-<N> --metadata '{"gsd": {"req": "CAT-NN", "phase": N, "milestone": "vX.Y"}}'`.
- **frontmatter-ids** (✗) — a PLAN.md `beads:` id is dangling or unlabeled:
  edit the PLAN's `beads:` list, or add the missing `phase-<N>` label to the
  issue.
- **maps-fresh** (⚠) — regenerate each stale phase:
  `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>`.
- **superseded-released** (⚠) — a superseded PLAN still holds open ids: close
  them or move them to the plan that superseded it.
- **phase-complete-open** (⚠, ✗ when a close was refused) — non-closed issues
  whose phase labels all point at ROADMAP-complete phases (a cross-phase issue
  with one live phase is not flagged): step 4 above (`--close-completed`), or
  re-open the phase if it is not actually done — the note item flags when the
  on-disk artifacts disagree with the checkbox. A ✗ here means bd refused a
  close the run attempted; its reason is on the item.
- **orphans** (⚠) — issues labeled for a non-ROADMAP phase, or non-closed with
  no `phase-*` label: attach the right phase label + stamp, label `backlog`,
  or close.
- **label-pairs** (⚠) — step 3 above.
- **claims-stale** (⚠) — in_progress + assigned issues outside the active
  phase: finish and close them, release the claim, or correct
  `active_phase:` in STATE.md.
- **bd-doctor** (✗) — follow bd's own advice: run `bd doctor` directly.

Re-run the doctor after the fixes to confirm a clean `ok` footer.
