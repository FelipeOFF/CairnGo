# Phase 8 — Verification

**Verified:** 2026-07-28
**Requirements:** GSD-03, GSD-04
**Verdict:** both met. 1 consequence carried to the operator (not a gap).

## GSD-03 — doctor reports which GSD lineage is installed

> **Done when** doctor distinguishes gsd-core from the 4.x distribution and fails,
> not warns, when the capability is absent while `.planning/` exists.

| Claim | Evidence |
|---|---|
| Doctor names the lineage | `cairn-doctor` on this repo: `✗ gsd-capability  GSD 4.x lineage — it has no 'capability' subcommand, so plain /gsd:* does NOT touch bd issues` |
| It distinguishes the two lines | Test: stub answering `Unknown command: capability` → fail with the upgrade command; stub answering a gsd-core registry without cairn → fail routed to `/cairn:init` |
| It fails rather than warns | Both cases exit 7. `bats tests/cairn-doctor.bats -f gsd-capability` |
| It says whether the capability *registered*, not just whether it was installed | The check reuses `cairn-capability.py detect`, which requires `capability list` to report cairn `active` **and** the staged bundle to carry `scripts/cairn-loop-gate.sh` |
| A partly-staged bundle is caught | Test: delete the gate script from a staged bundle → exit 7. Without this the ship gate would pass without checking anything |
| "Cannot tell" is not "missing" | Test: no discoverable GSD → ⚠ warn, exit stays 0 |
| The verdict is reproducible across machines | `CAIRN_GSD_BIN` pins discovery; the doctor fixture wires a stub so the suite does not inherit the developer's plugin cache |

## GSD-04 — an upgrade path for people already installed

> **Done when** a user on the old plugin gets a working path to gsd-core that does
> not require deleting their setup, and the deprecation has a stated end.

| Claim | Evidence |
|---|---|
| ~~The old entry still resolves~~ | **Superseded at release — see the amendment below.** |
| The path does not require starting over | The guide's four commands are install, reload, `/cairn:init`, `/cairn:doctor`; `.planning/` and `.beads/` are untouched, and `/cairn:init` is idempotent |
| The deprecation has a stated end | It ends in v1.4, stated in the migration guide and the CHANGELOG's Removed section |
| A user can tell whether they need to act | `/cairn:doctor` → `✗ gsd-capability` names which of the two causes applies |

## Amendment at release (v1.4.0)

The phase shipped the compatibility entry as the requirement asked. **The
operator then decided to remove it in the same release that introduces the
migration**, rather than carry it for a cycle.

The cost was put to them explicitly before the decision: an install still on
`gsd@cairngo` gets no grace period, and the choice contradicts GSD-04's own
wording. They chose it anyway, so that is what shipped.

Where that leaves GSD-04:

| Part of the requirement | Status |
|---|---|
| "a working path to gsd-core that does not require deleting their setup" | **Met.** `cairn/docs/gsd-core-migration.md` documents it; `.planning/` and `.beads/` are untouched |
| "the deprecation has a stated end" | **Met.** It ends in v1.4, stated in the guide and the CHANGELOG |
| "keeps the old entry for one release cycle alongside the new one" | **Not met, by decision.** The entry is gone as of v1.4.0 |

Practical effect, since it is narrower than "existing installs break": Claude
Code caches installed plugins, so a machine that already has `gsd@cairngo`
keeps running it. What stops working is *re-resolving* that name — a reinstall,
a new machine, or a marketplace refresh that tries to re-fetch it.

## Test evidence

- `bats tests/cairn-doctor.bats` — 28/28 green.
- The healthy fixture asserts eleven checks, all `ok` — so the success path of the
  new check is under test, not only its failures.

## Carried to the operator (not a gap)

`cairn-doctor` is now red on this repo, because the GSD installed here is the 4.x
line. That is the honest state — the fusion genuinely is off — but doctor failure
is a stop rule for `/cairn:autonomous`, and the local install cannot move to
gsd-core until this branch merges and the marketplace is refreshed. The run stops
here for that decision rather than routing around its own stop rule.
