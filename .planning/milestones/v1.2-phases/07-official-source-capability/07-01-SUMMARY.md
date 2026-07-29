---
phase: 07-official-source-capability
plan: "01"
status: complete
requirements: [GSD-01, GSD-02]
beads: [CairnGo-jge, CairnGo-zb4]
---

# Phase 7 Plan 01 — Summary

cairn now depends on the official `open-gsd/gsd-core`, and the capability install
that had been failing silently since the plugin shipped now verifies itself and
reports the truth.

## What shipped

**GSD-01 — the official source.** The marketplace entry is renamed `gsd` →
`gsd-core` and sourced from `open-gsd/gsd-core` pinned at `ref: v1.8.0`;
`cairn/.claude-plugin/plugin.json` depends on `gsd-core`. The pin is deliberate:
gsd-core's default branch is `next`, a development branch, so an unpinned entry
would have shipped unreleased code to every install. The marketplace schema
supports pinning — the official Anthropic marketplace does the same by
`ref`/`commit`/`sha`.

Live references updated in `README.md`, `cairn/README.md`,
`cairn/docs/commands/init.md`, `cairn/commands/init.md`, `cairn/scripts/cairn-init.sh`
and the two codebase-map files. `CHANGELOG.md` and
`benchmarks/baselines/gsd-only.json` keep their old references on purpose: one is
history, the other is a pin that benchmark reproducibility depends on.

**GSD-02 — proven, not attempted.** New script pair
`cairn/scripts/cairn-capability.{py,sh}` with two commands:

- `detect` — read-only report of lineage, registration and staging.
- `install` — install (with `capability update` as the re-run fallback), then
  verify; the verification, not the installer's exit code, decides the result.

Registration is proven by two independent checks, both required: GSD's own
`capability list` must report cairn `active`, **and** the staged bundle must carry
`scripts/cairn-loop-gate.sh`. The second is not redundant — the ship-gate predicate
reads `test -f <gate script> || exit 0`, so a bundle staged without its scripts
leaves a gate that passes without checking anything.

`/cairn:init` step 2 now calls the script and branches on its exit code
(0 active · 5 no GSD · 7 not installed), stating plainly that plain `/gsd:*` will
not touch bd issues when it is 7.

## What the work turned up

1. **The failure was worse than "swallowed".** `gsd_run` and `gsd` are not on PATH
   in a normal Claude Code session (verified on this machine), so the old block did
   not even reach its install attempt — it took the `else` branch and printed
   "skipping". Discovery now searches the plugin cache, which is what makes the
   install possible at all.
2. **The 4.x line cannot host the capability.** gsd 4.3.1/4.4.0 answers
   `Error: Unknown command: capability` and exits 1. gsd-core 1.8.0 offers
   `install, update, remove, list, outdated, trust, disable, enable, state, set`.
3. **The fusion does work against the official core.** Installing this repo's bundle
   into a scratch project registered `cairn v1.0.0`, `scope: project`,
   `status: active`, with the gate scripts staged intact — verified through the exact
   git-tag path a marketplace install takes, including gsd-core's self-healing
   runtime build (~3s on first call, after Claude Code's `npm install
   --ignore-scripts`).
4. **A discovery bug, found and fixed during self-review.** Ordering candidates by
   version alone let a legacy `gsd 4.4.0` outrank `gsd-core 1.8.0` — cairn would have
   reported "legacy" on a machine that has the official core. Lineage now outranks the
   version number. The regression test was proved to fail against the old ordering
   before being kept.

## Verification

- `bats tests/` green with `CAIRN_REQUIRE_GSD_VALIDATOR=1` and a pinned gsd-core
  checkout; 16 new tests in `tests/cairn-capability.bats`.
- CI pins `GSD_CORE_REF: v1.8.0`, shallow-clones the tag and sets
  `CAIRN_REQUIRE_GSD_VALIDATOR=1`, so the official `validateCapability` pass now runs
  on every PR instead of skipping. All three modes were checked by hand: required +
  present → pass, required + absent → fail, local + absent → skip.
- A shallow clone is all CI needs: gsd-core git-tracks the generated
  `capability-validator.cjs` and its single dependency, so no npm install and no tsc
  build are involved.
- `cairn-capability.sh detect` on this machine reports the legacy lineage and exits 7
  — the honest answer, and the one the old code never gave.

## Known consequence, carried to phase 8

Existing installs do not follow a plugin rename, so everyone currently on `gsd` keeps
a lineage that cannot host the capability until they act. GSD-04 owns that path.
Related: implementing GSD-03 as written (doctor **fails** when the capability is
absent) will make `cairn-doctor` fail on this repo until gsd-core is installed here.
