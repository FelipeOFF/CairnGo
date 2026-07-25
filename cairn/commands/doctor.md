---
description: Health-check the GSD↔beads wiring — run cairn-doctor, explain the report, route each finding to its fix
---

Audit the repo's cairn wiring and walk the user through fixing what it finds.

## 1. Run the doctor

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh"
```

(`--json` for machine output.) Exit codes: `0` all ok — warnings included, they
never change the exit code — or not-applicable (`.planning/` or `.beads/`
absent); `5` bd unavailable; `7` at least one check **failed**.

Not-applicable: relay the printed note — when exactly one side exists it
suggests `/cairn:migrate`; when neither exists, route to `/cairn:init`.

## 2. Explain the report

Header shows root, milestone, and active phase; then one ✓/⚠/✗ line per check
with itemized findings. Failures (✗) block; warnings (⚠) are advisories. Give
the user the short version: what is inconsistent and what fixes it.

## 3. Offer `--fix-labels` when check 6 (label-pairs) warns

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" --fix-labels
```

Runs `cairn-relabel pair` with the active milestone **before** the checks, so
the report shows the post-fix state. It refuses (exit `2`) when candidates
exist but the milestone is unresolvable — set `milestone:` in STATE.md
frontmatter (or mark the in-progress ROADMAP milestone with 🚧) first.

## 4. Route the remediation per check

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
- **orphans** (⚠) — issues labeled for a non-ROADMAP phase, or non-closed with
  no `phase-*` label: attach the right phase label + stamp, label `backlog`,
  or close.
- **label-pairs** (⚠) — step 3 above.
- **claims-stale** (⚠) — in_progress + assigned issues outside the active
  phase: finish and close them, release the claim, or correct
  `active_phase:` in STATE.md.
- **bd-doctor** (✗) — follow bd's own advice: run `bd doctor` directly.

Re-run the doctor after the fixes to confirm a clean `ok` footer.
