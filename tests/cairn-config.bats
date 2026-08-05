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

@test "cairn-config.sh with no subcommand exits 2; --help lists list, get and set" {
  run bash "$CONFIG"
  [ "$status" -eq 2 ]

  run bash "$CONFIG" --help
  [ "$status" -eq 0 ]
  grep -qF "list" <<<"$output"
  grep -qF "get" <<<"$output"
  grep -qF "set" <<<"$output"
}

#-----------------------------------------------------------------------------
# Task 2: the whole schema, the inventory of what already lives elsewhere, and
# the remaining types.
#-----------------------------------------------------------------------------

@test "list names EXACTLY the six keys of the schema — and sync_push is not one of them" {
  make_config_fixture

  run bash "$CONFIG" list --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  # An assertion on the SET, not on prose: a seventh key with no reader turns
  # this red, and so does the sync_push button, whose absence is a grooming
  # decision rather than an oversight (post-bd-write.sh:126-152 decides the
  # push by the existence of sync.json, and the flag is read by nothing).
  #
  # Documented override (plan 29-04): this literal said "five keys" and named
  # five until `jira.link` landed, and the test's title said five too. The
  # sixth key arrives WITH its reader in the same cycle — cairn-jira.py, which
  # writes the answer through `set` and reads it through `get` — which is the
  # entry rule being satisfied, not bent. The literal moved; the intention (a
  # key cannot slip in unnoticed) did not.
  assert_json_eq "$output" '[.keys[].key] | sort | join(",")' \
    'autonomous.max_cycles,autonomous.max_parallel,bookkeep.auto_commit,jira.link,ship.pr_scope,test.jobs'
  assert_json_eq "$output" '[.keys[] | select(.key | test("sync_push"))] | length' '0'

  # Every key names the executable that reads it. An empty reader is the
  # defect this phase exists to close.
  assert_json_eq "$output" '[.keys[] | select(.reader == null or .reader == "")] | length' '0'
  assert_json_eq "$output" '[.keys[] | select(.key == "autonomous.max_parallel") | .reader][0]' \
    'cairn-parallel.py batch'
  assert_json_eq "$output" '[.keys[] | select(.key == "ship.pr_scope") | .reader][0]' \
    'cairn-bookkeep.py'
  assert_json_eq "$output" '[.keys[] | select(.key == "test.jobs") | .reader][0]' \
    'cairn-test.py'
}

@test "list also inventories the config cairn keeps elsewhere, by file and by owner" {
  make_config_fixture

  run bash "$CONFIG" list --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  # The other half of "nothing lists the set": a list that only showed what
  # this script itself writes would still leave a reader hunting.
  assert_json_eq "$output" '[.elsewhere[].path] | sort | join(",")' \
    '.cairn/context.json,.cairn/sync.json,.planning/config.json'
  assert_json_eq "$output" '[.elsewhere[] | select(.path == ".cairn/sync.json") | .written_by][0]' \
    '/cairn:sync-config'
  assert_json_eq "$output" '[.elsewhere[] | select(.path == ".cairn/context.json") | .written_by][0]' \
    '/cairn:context-config'
  # cairn.enabled stays where the thing that activates the capability reads it.
  assert_json_eq "$output" '[.elsewhere[] | select(.path == ".planning/config.json") | .key][0]' \
    'cairn.enabled'
  assert_json_eq "$output" '[.elsewhere[] | select(.path == ".planning/config.json") | .read_by][0]' \
    'cairn-loop-gate.py'

  # Naming them is not reading them: no .cairn/ file was created by a list.
  [ ! -e "$ROOT/.cairn/config.json" ]
  [ ! -e "$ROOT/.cairn/sync.json" ]
  [ ! -e "$ROOT/.cairn/context.json" ]
}

@test "list reports where each value came from, and the human render says the file is hand-editable" {
  make_config_fixture
  bash "$CONFIG" set ship.pr_scope milestone --project-dir "$ROOT"

  run bash "$CONFIG" list --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.keys[] | select(.key == "ship.pr_scope") | .source][0]' 'file'
  assert_json_eq "$output" '[.keys[] | select(.key == "ship.pr_scope") | .value][0]' 'milestone'
  assert_json_eq "$output" '[.keys[] | select(.key == "ship.pr_scope") | .default][0]' 'phase'
  # Untouched keys still answer, from the schema.
  assert_json_eq "$output" '[.keys[] | select(.key == "bookkeep.auto_commit") | .source][0]' 'default'

  run bash "$CONFIG" list --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  grep -qF ".cairn/config.json" <<<"$output"
  grep -qF "edit it by hand" <<<"$output"
  grep -qF "read by cairn-bookkeep.py" <<<"$output"
}

@test "the enum key: default phase, settable to milestone or none, and anything else exits 3" {
  make_config_fixture

  run bash "$CONFIG" get ship.pr_scope --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  # Bare, not JSON-quoted: `$(cairn-config.sh get ship.pr_scope)` is a shell
  # idiom and `"phase"` would be the wrong answer to it.
  [ "$output" = "phase" ]

  run bash "$CONFIG" set ship.pr_scope milestone --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  run bash "$CONFIG" get ship.pr_scope --project-dir "$ROOT"
  [ "$output" = "milestone" ]

  run bash "$CONFIG" set ship.pr_scope talvez --project-dir "$ROOT"
  [ "$status" -eq 3 ]
  grep -qF "phase, milestone, none" <<<"$output"
  # The rejection did not overwrite the good value.
  run bash "$CONFIG" get ship.pr_scope --project-dir "$ROOT"
  [ "$output" = "milestone" ]
}

@test "the bool key: default false, real JSON booleans on disk, junk exits 3" {
  make_config_fixture

  run bash "$CONFIG" get bookkeep.auto_commit --project-dir "$ROOT"
  [ "$output" = "false" ]

  run bash "$CONFIG" set bookkeep.auto_commit true --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  # A JSON boolean, not the string "true" — a reader doing `if value:` on
  # "false" would be wrong for the rest of its life.
  run jq -r '.bookkeep.auto_commit | type' "$ROOT/.cairn/config.json"
  [ "$output" = "boolean" ]

  run bash "$CONFIG" set bookkeep.auto_commit talvez --project-dir "$ROOT"
  [ "$status" -eq 3 ]
  grep -qF "takes a boolean" <<<"$output"
}

#-----------------------------------------------------------------------------
# Task 3: the two doors.
#
# The asking layer is prose — AskUserQuestion does not run under bats, and no
# test here pretends otherwise. What IS proven is the seam underneath it: the
# command writes through `set` and reads through `list --json`, so if the two
# doors reach the same bytes, the questions cannot land anywhere else. The
# prose assertions below check that the command DELEGATES to that seam rather
# than reimplementing it, which is the one thing a bats file can honestly say
# about a markdown prompt.
#-----------------------------------------------------------------------------

@test "the two doors reach the same bytes: hand-write and read via get, set and read the file raw, and both orders produce identical files" {
  make_config_fixture

  # Door 1 — the one /cairn:config uses.
  bash "$CONFIG" set autonomous.max_parallel 5 --project-dir "$ROOT"
  bash "$CONFIG" set ship.pr_scope milestone --project-dir "$ROOT"
  local by_set="$BATS_TEST_TMPDIR/by-set.json"
  cp "$ROOT/.cairn/config.json" "$by_set"

  # `set` wrote something a hand editor can read back with jq alone.
  run jq -r '.autonomous.max_parallel' "$by_set"
  [ "$output" = "5" ]
  run jq -r '.ship.pr_scope' "$by_set"
  [ "$output" = "milestone" ]

  # Door 2 — a human with an editor, in a fresh repo, typing the same thing.
  # This heredoc is written by hand on purpose: it is what the format claims
  # to be, not what the writer happens to emit.
  local other="$BATS_TEST_TMPDIR/by-hand-repo"
  mkdir -p "$other/.cairn"
  cat > "$other/.cairn/config.json" <<'JSONEOF'
{
  "autonomous": {
    "max_parallel": 5
  },
  "ship": {
    "pr_scope": "milestone"
  }
}
JSONEOF

  # The hand-written file is read as authoritative, key for key.
  run bash "$CONFIG" get autonomous.max_parallel --project-dir "$other" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' '5'
  assert_json_eq "$output" '.source' 'file'
  run bash "$CONFIG" get ship.pr_scope --project-dir "$other"
  [ "$output" = "milestone" ]

  # And the two doors leave the same bytes on disk. Anything that normalized,
  # reordered, or stored somewhere else than the hand edit sees would make
  # "two doors, one place" a story rather than a fact.
  run cmp "$by_set" "$other/.cairn/config.json"
  [ "$status" -eq 0 ]
}

@test "a set never clobbers a key its own question did not ask about" {
  make_config_fixture
  mkdir -p "$ROOT/.cairn"
  # A hand edit carrying a key this run will not touch, plus a comment-free
  # unknown key someone left behind.
  cat > "$ROOT/.cairn/config.json" <<'JSONEOF'
{
  "autonomous": {
    "max_cycles": 7
  },
  "keep_me": "not a schema key, and not this script's to delete"
}
JSONEOF

  bash "$CONFIG" set ship.pr_scope none --project-dir "$ROOT"

  run jq -r '.autonomous.max_cycles' "$ROOT/.cairn/config.json"
  [ "$output" = "7" ]
  run jq -r '.keep_me' "$ROOT/.cairn/config.json"
  [ "$output" = "not a schema key, and not this script's to delete" ]
  run jq -r '.ship.pr_scope' "$ROOT/.cairn/config.json"
  [ "$output" = "none" ]
}

@test "the /cairn:config command delegates to the script and declares what it leaves out" {
  local cmd="$CAIRN_REPO_ROOT/cairn/commands/config.md"
  [ -f "$cmd" ]

  # A thin wrapper: the current values come from `list --json` and the write
  # goes through `set` — no prose reimplementation of either.
  grep -qF 'scripts/cairn-config.sh" list --json' "$cmd"
  grep -qF 'scripts/cairn-config.sh" set <key> <value>' "$cmd"

  # One batch with the current value pre-selected, in named sections — the
  # /gsd:config shape, mirrored rather than reinvented.
  grep -qF "AskUserQuestion" "$cmd"
  grep -qF "pre-selected" "$cmd"
  grep -qF "Bookkeeping" "$cmd"
  grep -qF "Autonomous run" "$cmd"
  grep -qF "Tests" "$cmd"

  # Both doors said out loud: half of AUTO-05 is exactly this sentence being
  # true and being told to the user.
  grep -qF "editing it by hand reaches exactly the same place" "$cmd"

  # What is NOT offered, why, and where the decision lives.
  grep -qF "cairn.sync_push" "$cmd"
  grep -qF "post-bd-write.sh:126-152" "$cmd"
  grep -qF "CairnGo-gbu" "$cmd"

  # And the three config commands are told apart in one place.
  local help="$CAIRN_REPO_ROOT/cairn/commands/help.md"
  grep -qF "/cairn:config" "$help"
  grep -qF "/cairn:sync-config" "$help"
  grep -qF "/cairn:context-config" "$help"
}

@test "the nullable int: null means available CPUs, a number means that number, zero is refused" {
  make_config_fixture

  run bash "$CONFIG" get test.jobs --project-dir "$ROOT"
  [ "$output" = "null" ]

  run bash "$CONFIG" set test.jobs 6 --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  run bash "$CONFIG" get test.jobs --project-dir "$ROOT"
  [ "$output" = "6" ]

  run bash "$CONFIG" set test.jobs null --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  run jq -r '.test.jobs | type' "$ROOT/.cairn/config.json"
  [ "$output" = "null" ]

  run bash "$CONFIG" set test.jobs 0 --project-dir "$ROOT"
  [ "$status" -eq 3 ]
  grep -qF "must be at least 1" <<<"$output"
}
