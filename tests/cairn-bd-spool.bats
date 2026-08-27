#!/usr/bin/env bats
# cairn-bd-spool.bats — the suite never feeds bd's metrics spool (phase 53,
# SPOOL-01, CairnGo-r7mw).
#
# Measured 2026-08-27: ~/.beads/eventsData held 259,653 `.evtq` files (1.0 GB),
# one anonymous `cli_command` event per bd invocation — and this suite runs
# thousands of them. cairn-test.sh pins HOME to a directory with bd's metrics
# off and exports CAIRN_TEST_HOME; this file proves the pin holds where it
# matters: a bd that inits, creates and lists leaves no event behind.
#
# Skipped when CAIRN_TEST_HOME is unset: raw `bats` is not the door, and a
# failure there would teach the suite that the door is optional.

load 'helpers'

@test "through cairn-test.sh, bd runs with metrics off and writes no .evtq" {
  require_bd
  [ -n "${CAIRN_TEST_HOME:-}" ] || skip "not running through cairn-test.sh (CAIRN_TEST_HOME unset)"
  [ "$HOME" = "$CAIRN_TEST_HOME" ]

  run bd metrics
  [ "$status" -eq 0 ]
  grep -qF "metrics: OFF" <<<"$output"

  make_tmp_repo
  bd init -q --prefix spl --non-interactive >/dev/null 2>&1
  bd create "one event" -t task --silent >/dev/null
  bd list --json >/dev/null

  local n
  n="$(find "$HOME/.beads/eventsData" -name '*.evtq' 2>/dev/null | wc -l | tr -d ' ')"
  [ "$n" -eq 0 ]
}
