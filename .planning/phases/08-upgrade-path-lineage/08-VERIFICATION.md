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
| The old entry still resolves | `.claude-plugin/marketplace.json` carries `gsd` alongside `gsd-core`; JSON validated, three plugins listed |
| Its consequence is stated where users see it | The entry's own `description` says the beads fusion cannot run on it and names the removal version |
| The deprecation has a stated end | v1.4 — in the marketplace description, `cairn/docs/gsd-core-migration.md`, the README plugin table and the CHANGELOG's Deprecated section |
| The path does not require starting over | The guide's four commands are install, reload, `/cairn:init`, `/cairn:doctor`; `.planning/` and `.beads/` are untouched, and `/cairn:init` is idempotent |
| A user can tell whether they need to act | `/cairn:doctor` → `✗ gsd-capability` names which of the two causes applies |

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
