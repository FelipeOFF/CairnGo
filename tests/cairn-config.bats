#!/usr/bin/env bats
# cairn-config.bats — exercises cairn's own settings file
# (cairn-config.py / the cairn-config.sh wrapper): the effective-value rule
# (file when present and well typed, schema default otherwise), the closed
# schema (an unknown key is a usage error, never a write), and type
# validation that happens BEFORE the write rather than after it.
#
# What this file deliberately does NOT test: whether a KEY IS READ. A written
# key is not a read key — that is the whole defect this phase exists to close
# (`cairn.sync_push` is declared, documented, asserted, and read by nothing).
# The proof that a setting reaches its consumer lives next to the consumer:
# tests/cairn-parallel.bats asserts the ceiling `batch` actually APPLIES.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so every check is a plain `[ ]` against a
# `run`-captured $status/$output, substring checks use grep -qF, and negative
# checks use refute_in_output.
#
# No bd, no network: these tests need only python3 and jq.

load 'helpers'

bats_require_minimum_version 1.5.0

CONFIG="$CAIRN_SCRIPTS_DIR/cairn-config.sh"

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# A throwaway repo with NO .cairn/ directory at all: the state every existing
# repo is in before this script ever runs. Exports ROOT.
make_config_fixture() {
  make_tmp_repo
  ROOT="$PWD"
  [ ! -e "$ROOT/.cairn/config.json" ]
}

#-----------------------------------------------------------------------------
# Task 1: get / set over one key, and the closed schema.
#-----------------------------------------------------------------------------

@test "with no config file at all, get returns the schema default and says so" {
  make_config_fixture

  run bash "$CONFIG" get autonomous.max_parallel --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  [ "$output" = "3" ]

  run bash "$CONFIG" get autonomous.max_parallel --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' '3'
  assert_json_eq "$output" '.source' 'default'
  assert_json_eq "$output" '.default' '3'
  # The entry rule made visible: every key names the executable that reads it.
  assert_json_eq "$output" '.reader' 'cairn-parallel.py batch'

  # Reading created nothing. A read is a read.
  [ ! -e "$ROOT/.cairn/config.json" ]
}

@test "set writes the key, get reads it back, and the file on disk is sorted with a trailing newline" {
  make_config_fixture

  run bash "$CONFIG" set autonomous.max_parallel 5 --project-dir "$ROOT"
  [ "$status" -eq 0 ]

  run bash "$CONFIG" get autonomous.max_parallel --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' '5'
  assert_json_eq "$output" '.source' 'file'

  # The nested shape a hand editor sees, not a flat "autonomous.max_parallel"
  # string key.
  run jq -r '.autonomous.max_parallel' "$ROOT/.cairn/config.json"
  [ "$status" -eq 0 ]
  [ "$output" = "5" ]

  # gbsync.py:write_json's shape, for git's sake: sorted keys, indent 2, and a
  # trailing newline. `tail -c 1` of a newline-terminated file is empty.
  run bash -c "tail -c 1 '$ROOT/.cairn/config.json' | wc -l | tr -d ' '"
  [ "$output" = "1" ]
}

@test "an unknown key is a usage error that names the valid keys, and writes nothing" {
  make_config_fixture

  run bash "$CONFIG" set naosei.chave 1 --project-dir "$ROOT"
  [ "$status" -eq 2 ]
  grep -qF "unknown key: naosei.chave" <<<"$output"
  grep -qF "autonomous.max_parallel" <<<"$output"
  refute_in_output "Traceback"
  [ ! -e "$ROOT/.cairn/config.json" ]

  run bash "$CONFIG" get naosei.chave --project-dir "$ROOT"
  [ "$status" -eq 2 ]
  grep -qF "known keys:" <<<"$output"
}

@test "a value of the wrong type exits 3 and leaves the file exactly as it was" {
  make_config_fixture

  # Nothing on disk yet: a rejected value must not create the file either.
  run bash "$CONFIG" set autonomous.max_parallel banana --project-dir "$ROOT"
  [ "$status" -eq 3 ]
  grep -qF "takes an integer" <<<"$output"
  refute_in_output "Traceback"
  [ ! -e "$ROOT/.cairn/config.json" ]

  # Now with a good value already stored: the rejection must not clobber it.
  run bash "$CONFIG" set autonomous.max_parallel 4 --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  local before
  before="$(cat "$ROOT/.cairn/config.json")"

  run bash "$CONFIG" set autonomous.max_parallel 0 --project-dir "$ROOT"
  [ "$status" -eq 3 ]
  grep -qF "must be at least 1" <<<"$output"
  [ "$(cat "$ROOT/.cairn/config.json")" = "$before" ]
}

@test "a hand-edited file value of the wrong type degrades to the default instead of failing the read" {
  make_config_fixture
  mkdir -p "$ROOT/.cairn"
  printf '{\n  "autonomous": {\n    "max_parallel": "lots"\n  }\n}\n' \
    > "$ROOT/.cairn/config.json"

  # `batch` shells out to this on every run, so a bad value cannot be fatal:
  # it degrades, and `source` reports where the answer really came from.
  run bash "$CONFIG" get autonomous.max_parallel --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' '3'
  assert_json_eq "$output" '.source' 'default'
}

@test "an unreadable config file is a named error, never a traceback" {
  make_config_fixture
  mkdir -p "$ROOT/.cairn"
  printf '{ this is not json' > "$ROOT/.cairn/config.json"

  run bash "$CONFIG" get autonomous.max_parallel --project-dir "$ROOT"
  [ "$status" -eq 3 ]
  grep -qF "is not valid JSON" <<<"$output"
  grep -qF ".cairn/config.json" <<<"$output"
  refute_in_output "Traceback"
}

@test "cairn-config.sh with no subcommand exits 2; --help lists get and set" {
  run bash "$CONFIG"
  [ "$status" -eq 2 ]

  run bash "$CONFIG" --help
  [ "$status" -eq 0 ]
  grep -qF "get" <<<"$output"
  grep -qF "set" <<<"$output"
}
