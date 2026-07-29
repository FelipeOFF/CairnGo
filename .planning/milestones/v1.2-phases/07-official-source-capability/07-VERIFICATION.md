# Phase 7 — Verification

**Verified:** 2026-07-28
**Requirements:** GSD-01, GSD-02
**Verdict:** both met. 0 blocking gaps.

## GSD-01 — cairn depends on the official GSD

> **Done when** a clean install of the marketplace pulls gsd-core, and no file
> still points at the old source.

| Claim | Evidence |
|---|---|
| The marketplace publishes gsd-core from the official repo | `.claude-plugin/marketplace.json` → `{"source":"github","repo":"open-gsd/gsd-core","ref":"v1.8.0"}` |
| The plugin name is real, not guessed | `open-gsd/gsd-core@v1.8.0`'s own `.claude-plugin/plugin.json` reports `"name": "gsd-core"`, `"version": "1.8.0"`, plugin at repo root |
| The `/gsd:` namespace survives the switch | gsd-core declares `"commands": "./commands/gsd/"`, so every `/cairn:*` wrapper that delegates stays valid |
| cairn depends on it | `cairn/.claude-plugin/plugin.json` → `"dependencies": ["gsd-core", …]` |
| Pinning is supported and necessary | Default branch is `next` (a dev branch). The official Anthropic marketplace pins its own entries by `ref`/`commit`/`sha` — verified in the installed marketplace cache |
| No live file points at the old source | Swept; remaining mentions are `cairn-capability.py` and `init.md` *describing* the legacy lineage, plus `CHANGELOG.md` (history) and `benchmarks/baselines/gsd-only.json` (a pin reproducibility depends on) |

**Risk checked and cleared:** a bare git clone of gsd-core has a non-functional CLI
("runtime library is not built"), which would have made this migration ship a broken
dependency. It does not: Claude Code runs `npm install --ignore-scripts` on plugin
install, and gsd-core's `ensure-runtime-build.cjs` compiles the runtime on first call.
Verified end to end — clone the tag, `npm install --ignore-scripts`, then
`capability list` succeeded after a one-time ~3s build.

## GSD-02 — the capability install is proven, not attempted

> **Done when** a failed capability install is reported as a failure with what to do
> about it, and the official validator runs in CI rather than skipping.

| Claim | Evidence |
|---|---|
| The old code returned 0 on failure | 4.3.1 `capability install` exits 1; the `\|\| echo "capability install skipped"` tail turned that into 0. Measured, not inferred |
| It was worse than swallowed | `gsd_run`/`gsd` are not on PATH in this session, so the block took its `else` branch and never attempted the install |
| Failure is now reported with a remedy | `cairn-capability.sh detect` on this machine: exit 7, names the legacy lineage and prints `claude plugin install gsd-core@cairngo` |
| The installer's exit code is not the verdict | Test: a stub whose `install` exits 0 while the registry omits cairn → exit 7 ("did not register") |
| A vacuous ship gate is caught | Test: bundle staged without `scripts/cairn-loop-gate.sh` → exit 7, explaining the gate would pass without checking |
| A disabled capability is not "active" | Test: registry reports cairn `status: disabled` → exit 7 |
| The fusion genuinely works | Real install against gsd-core 1.8.0 registered `cairn v1.0.0`, `scope: project`, `status: active`, gate scripts staged |
| The validator runs in CI | `.github/workflows/ci.yml` pins `GSD_CORE_REF: v1.8.0`, shallow-clones it, exports `GSD_CORE_DIR` + `CAIRN_REQUIRE_GSD_VALIDATOR=1` |
| A CI skip is a failure | Checked all three modes by hand: required+present → `ok`; required+absent → `not ok` with the reason; local+absent → `skip` (local dev unaffected) |

## Defect found and fixed during this phase

Discovery ordered candidate GSD binaries by version alone, so a legacy `gsd 4.4.0`
outranked `gsd-core 1.8.0` — cairn would have reported "legacy" on a machine that has
the official core installed. Fixed so lineage outranks the version number. The
regression test was proved meaningful by injecting the old ordering and watching it
fail, then restoring from a file copy.

## Test evidence

- `tests/cairn-capability.bats` — 16 tests, all green.
- Full suite green under `CAIRN_REQUIRE_GSD_VALIDATOR=1` with a pinned checkout.
- One local-only red herring: `bench-all.bats`'s repo-hygiene test asserts
  `git status --porcelain -- README.md` is empty, so it fails while README.md is
  being edited and passes once committed. It is a clean-tree assertion, not a defect
  in this work; CI runs on a clean checkout.

## Carried forward

- **GSD-03 has a consequence worth deciding.** Implemented as written ("fails, not
  warns, when the capability is absent while `.planning/` exists"), `cairn-doctor`
  will FAIL on this repo, because the GSD installed here is the 4.x line. Doctor
  failure is a stop rule for `/cairn:autonomous`. Operator decision needed in phase 8.
- **GSD-04** owns the upgrade path for existing installs; the window is decided
  (drops in v1.4).
