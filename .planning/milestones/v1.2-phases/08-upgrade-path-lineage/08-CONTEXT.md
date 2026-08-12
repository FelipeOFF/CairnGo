# Phase 8: Upgrade path and lineage reporting - Context

**Gathered:** 2026-07-28
**Status:** Ready for planning
**Source:** Interactive autonomous run. The deprecation window was chosen by the operator (see below), not defaulted.

<domain>
## Phase Boundary

Phase 7 fixed the source and the install. This phase makes the *state* visible on
every health check, and gives people already installed a path that does not require
deleting their setup. Requirements: GSD-03, GSD-04. bd issues: CairnGo-xcc,
CairnGo-wlc — see `08-BEADS-MAP.md`.

</domain>

<decisions>
## Operator decision

**Deprecation window: one minor release — the old `gsd` entry is removed in v1.4.**
Claude recommended a date-based window on the grounds that a version-based one is
invisible to users who do not track releases. The operator chose the release-based
window; v1.4 is what ships in the docs and the marketplace description.

## Implementation decisions (locked)

- **`gsd-capability` is a FAIL, not a warn.** The requirement says so, and the
  reason is the whole milestone: the capability install failed silently for months
  precisely because nothing hard ever said no. A warn would repeat the mistake.
- **"No GSD binary found" is a WARN.** That is genuinely "cannot tell", not
  "the capability is missing" — a different claim deserving a different signal.
- **The check delegates to `cairn-capability.py detect --json`** rather than
  re-implementing the lineage rules, so the two registration checks live in one
  place and cannot drift.
- **`CAIRN_GSD_BIN` is a real seam, not a test hack.** This check reads GLOBAL
  state (which GSD is installed on the machine) while every other doctor check
  reads the repo. Without an override the doctor's verdict would depend on the
  developer's plugin cache: the same repo would report differently on two machines,
  the test suite would pass or fail by accident, and CI would disagree with local
  runs for reasons no one could see.
- **Both entries stay in the marketplace for the window.** The old one carries its
  deprecation, its consequence ("the fusion cannot run on it") and its removal
  version in the description itself, because that string is what a user sees in the
  plugin list.

</decisions>

<risks>
- **This check turns `cairn-doctor` red on any repo whose GSD is the 4.x line —
  including this one.** That is the honest state (the fusion really is off here),
  but doctor failure is a stop rule for `/cairn:autonomous`, so the run cannot
  continue past this phase's checkpoint until either gsd-core is installed locally
  or the operator decides otherwise. Raised with the operator rather than worked
  around.
- The local install cannot switch to gsd-core until this branch merges and the
  marketplace is refreshed, so the red doctor is expected in the interim.
</risks>
