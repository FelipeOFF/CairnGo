# Phase 9 — Verification

**Verified:** 2026-07-28
**Requirement:** GSD-05
**Verdict:** met. 0 blocking gaps.

## GSD-05 — decide, one by one, what gsd-core brings

> **Done when** each has an explicit decision recorded: wrapped as `/cairn:*`,
> documented as "use the GSD command directly", or deliberately out of scope.
> No wholesale wrapping.

| Claim | Evidence |
|---|---|
| The list is derived, not inherited | `ls commands/gsd/` against the installed `gsd-core@v1.8.0` → 71 commands; `grep -rhoE "/gsd:[a-z0-9-]+" cairn/` → 18 referenced; 54 unreferenced |
| The research note's figure was wrong | It said 24. The real count is 54, of which 41 are not mentioned anywhere in cairn in any form. Corrected in the doc with the derivation shown |
| Every command has exactly one decision | Script diff of the doc's table rows against the derived list: 54 expected, 54 documented, 0 missing, 0 extra |
| The three outcomes are all used | 13 wrapped · 39 use-directly · 2 out of scope |
| No wholesale wrapping | 13 of 54 (24%), each with a stated reason tied to a written criterion |
| The criterion is explicit | "A command earns a wrapper when running it changes work beads has to know about" — stated before the tables, so the bias is applied consistently |
| Out-of-scope calls are reasoned, not omissions | `pr-branch` filters `.planning/` commits, which are the record in cairn; `graphify` duplicates context-mode's job with no reconciliation |
| The table survives a gsd-core bump | The doc ships the three-line re-derivation recipe; a command absent from every table has no decision recorded |
| The deferred work is tracked | `CairnGo-9xy`, `discovered-from` CairnGo-k21, carrying all thirteen commands and the reasoning |

## Scope note

The requirement's done-condition is the recorded decision, not the
implementation. The thirteen wrappers are decided and filed, not built — stated
plainly in the doc and the summary rather than implied by omission.
