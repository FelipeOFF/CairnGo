---
phase: 09-adopt-gsd-core-commands
plan: "01"
status: complete
requirements: [GSD-05]
beads: [CairnGo-k21]
---

# Phase 9 Plan 01 — Summary

Every gsd-core command cairn does not wrap now carries a written decision.

## What shipped

`cairn/docs/gsd-core-commands.md` — a decision table covering all **54**
unreferenced commands in three sections:

- **Wrapped as `/cairn:*` — 13.** Commands that change work beads has to know
  about: `phase`, `discuss-phase`, `spec-phase`, `mvp-phase`, `ui-phase`,
  `ai-integration-phase`, `ultraplan-phase`, `plan-review-convergence`,
  `validate-phase`, `secure-phase`, `cleanup`, `review-backlog`,
  `audit-milestone`. Each row says *why* — the strongest being `phase`, whose
  CRUD renumbers or removes phases and orphans every issue carrying the
  matching `phase-<N>` label.
- **Use the GSD command directly — 39.** Nothing here changes tracked work, so
  a wrapper would be an alias and one more thing to keep in sync. Rows point at
  cairn's equivalent where one exists (`next` → `/cairn:status`, `health` →
  `/cairn:doctor`, `thread`/`mempalace-*` → `/cairn:remember`/`recall`).
- **Deliberately out of scope — 2.** `pr-branch` builds a PR branch by
  filtering out `.planning/` commits, and in cairn `.planning/` *is* the record.
  `graphify` builds a second knowledge graph competing with context-mode, which
  cairn already scopes by issue and phase.

The doc states the wrap criterion **before** applying it, so the operator's
"wrap the phase/planning-adjacent ones" bias lands consistently instead of
per-command by feel.

## What the work turned up

**The research note undercounted by more than half.** It reported 24
unreferenced commands. Derived against the installed `open-gsd/gsd-core@v1.8.0`:
71 commands total, 18 referenced by cairn, **54 unreferenced**, of which 41 are
not mentioned anywhere in cairn in any form. The doc ships the three-line
recipe that re-derives this after a gsd-core bump, so the table can be audited
rather than believed.

**Coverage was verified, not asserted.** A script extracts the command names
from the doc's tables and diffs them against the derived list: 54 expected, 54
documented, nothing missing, nothing extra.

## Deferred, and tracked

The thirteen wrap decisions are recorded; the wrappers are not built. That is
real work, so it is on the books as **CairnGo-9xy** (`discovered-from`
CairnGo-k21) with the full list and the reasoning, rather than left as prose in
a doc. Until they exist, running the GSD command followed by `/cairn:doctor`
catches the drift a wrapper would have prevented — orphans, stale maps, missing
`beads:` frontmatter.

This matches the requirement, whose done-condition is the recorded decision:
*"each has an explicit decision recorded … No wholesale wrapping."*

## Verification

- 54/54 commands documented, verified by script.
- Linked from the root README's documentation table and `cairn/docs/commands.md`.
