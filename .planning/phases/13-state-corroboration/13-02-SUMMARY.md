---
phase: 13-state-corroboration
plan: "02"
status: complete
requirements: [CORR-02, CORR-07]
beads: [CairnGo-jc5, CairnGo-u7s]
---

# Phase 13 Plan 02 — Summary

The conflict is visible where the operator already looks, and it costs one line.

## What shipped

**One phase, one line, always.** A conflicting phase replaces its state text with
a marker and the reason inline — `✗ conflict — disco executed, bd 2 abertas` —
and a summary line closes the panel with the counts and where to get the detail.
The itemised per-source breakdown belongs to `/cairn:doctor` and `--json`, never
to the board.

This was chosen by the user from four variants rendered in the terminal side by
side, not described in prose. The two-line-per-conflict variant was rejected
precisely because a board that grows with the number of conflicts stops being
scannable exactly when it matters most.

**Terminal and HTML render from one helper**, `conflict_summary_text()`, and the
test renders both and compares. It does not assert each surface against its own
hardcoded string — that would let the two drift together toward the same wrong
answer and still pass.

**The harmless-diff corpus.** Regenerated maps, bumped mtimes and reordered JSON
keys produce zero conflicts, each corpus entry carrying a written justification
above its test. A detector that cries wolf gets ignored, and an ignored detector
is worse than none, because it manufactures confidence it has not earned.

## The thing worth knowing

The accent colour was deliberately **not** applied to the metadata text. The
`--oxide` token's own comment documents it as large-text-or-marks only at 3.38:1,
below AA for that size, and every existing use in the codebase respects that. The
colour signal arrives as a left border accent instead, matching the established
`.panel-par.is-split` pattern, so the conflict reads at a glance without the line
becoming harder to read than the ones around it.

Two plan instructions could not be followed literally and were corrected rather
than worked around: the acceptance criteria pinned `--width 100` for assertions on
the full detail string, but the panel's own budget formula yields 65 columns there
while the real detail strings run 68–77 — the assertion would have been testing
truncation, not content. The wider width is used only for those assertions, with
the reason written at each site. And `touch -d '+1 hour'` is GNU-only; the fixture
uses `sleep 1; touch` so it runs on this machine at all.
