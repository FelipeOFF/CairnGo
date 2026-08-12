# Deferred Items — Phase 1

Out-of-scope discoveries logged during execution. Not fixed here.

## From 01-02 (2026-07-25)

- **Pre-existing bats suites exceed 45s locally under sandboxed execution:**
  `tests/cairn-doctor.bats`, `tests/cairn-gate.bats`, `tests/cairn-migrate.bats`,
  `tests/cairn-status.bats` each hit a 45s timeout when run in the sandboxed
  local session (likely slow/network-blocked `bd`/dolt operations; a full
  `bats tests/` run exceeded 2 minutes). All four suites predate this plan and
  none touch 01-02's files — `bench-run.bats`, `bench-verify.bats`,
  `cairn-map.bats`, `cairn-init.bats`, `cairn-relabel.bats`, `capability.bats`,
  `gbsync.bats`, `hooks.bats`, `smoke.bats` all pass locally. Worth timing
  these four in CI (ubuntu, unsandboxed) to see whether it is an environment
  artifact or genuine suite slowness.
