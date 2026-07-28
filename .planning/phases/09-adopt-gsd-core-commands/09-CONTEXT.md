# Phase 9: Adopt what gsd-core brings - Context

**Gathered:** 2026-07-28
**Status:** Ready for planning
**Source:** Interactive autonomous run. The triage bias was chosen by the operator.

<domain>
## Phase Boundary

Every gsd-core command cairn does not wrap gets an explicit, written decision.
Requirement: GSD-05. bd issue: CairnGo-k21 — see `09-BEADS-MAP.md`.

The requirement's done-condition is the **record**, not the implementation:
"each has an explicit decision recorded: wrapped as `/cairn:*`, documented as
'use the GSD command directly', or deliberately out of scope. No wholesale
wrapping."

</domain>

<decisions>
## Operator decision

**Triage bias: wrap the phase/planning-adjacent commands, document the rest.**
Claude recommended documenting by default to keep cairn's command surface small,
on the grounds that cairn's value is the fusion rather than aliasing someone
else's command. The operator chose the wider wrapping, and that is the bias
applied.

## Implementation decisions (locked)

- **The counts are derived, not remembered.** The research note said 24
  unreferenced commands. Recomputed against the installed
  `open-gsd/gsd-core@v1.8.0`: **71 commands, 18 referenced by cairn, 54
  unreferenced**, of which 41 are not mentioned anywhere in cairn today. The doc
  ships the command that re-derives this after a gsd-core bump, so the table can
  be audited rather than trusted.
- **The wrap test is concrete**, so the bias is applied consistently rather than
  by feel: a command earns a wrapper when running it changes work beads must know
  about — a phase appears or disappears, a `PLAN.md` is written that needs
  `beads:` frontmatter, a completed phase is reopened, or issues would be
  orphaned.
- **Decision recorded, wrappers deferred and tracked.** Thirteen commands were
  decided as "wrap". Building them is real work and is filed as `CairnGo-9xy`
  (`discovered-from` CairnGo-k21) rather than left implicit — side work stays on
  the books.
- **Two commands are out of scope on principle, not by omission.** `pr-branch`
  strips `.planning/` commits, and in cairn `.planning/` *is* the record.
  `graphify` builds a second knowledge graph competing with context-mode, which
  cairn already scopes by issue and phase.

</decisions>

<risks>
- The table is a point-in-time read of v1.8.0. A gsd-core bump can add commands
  with no decision recorded. Mitigated by shipping the re-derivation command in
  the doc itself rather than a number in prose.
</risks>
