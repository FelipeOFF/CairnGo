# Deferred Items — Phase 06

Out-of-scope discoveries logged during execution. Not fixed here (scope boundary).

## Intermittent bd hang in tests/cairn-status.bats (pre-existing, environmental)

- **Found during:** 06-03 execution (2026-07-26), full-suite regression run
- **Symptom:** a single `bats tests/` invocation hung indefinitely inside a
  bd-dependent `cairn-status.bats` test (first at global test 147,
  `no phase-labeled ready work falls back to STATE.md's workflow step`; on an
  isolated re-run of the same file it instead hung after test 21 — the hang
  point moves between runs). The hang sits inside `bd init`/`bd create`
  fixture setup (embedded dolt), not in any assertion.
- **Pre-existence evidence:** `tests/cairn-status.bats` last modified in
  `b6bdc30` (2026-07-25), before this phase's wave 2; the same file passed
  193/193 full-suite runs earlier on 2026-07-26 (06-01/06-02 executions) and
  passed 22/22 with exit 0 on the very next per-file run during 06-03.
  Nothing in 06-03 touches cairn-status or bd.
- **Workaround used for evidence:** ran the suite per-file with per-file
  timeouts — all 21 files exit 0, 199/199 ok, 0 not ok.
- **Suggested follow-up:** investigate bd/embedded-dolt startup flakiness
  under repeated rapid `bd init` in tmpdirs (possibly a dolt lock/fsync
  stall); consider a bats-level timeout guard around `make_bd_fixture`.
