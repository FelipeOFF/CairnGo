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

@test "list names EXACTLY the seven keys of the schema — and sync_push is not one of them" {
  make_config_fixture

  run bash "$CONFIG" list --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  # An assertion on the SET, not on prose: an eighth key with no reader turns
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
  #
  # Documented override (plan 24-01): six -> seven, for
  # `agents.response_language`. Same rule, same shape: the reader is named
  # (`cairn-parallel.py prepare`), it is executable, and it lands in the same
  # cycle — the payload of `prepare --json` carries the value and
  # tests/cairn-parallel.bats reads it out of that payload. The reason it is a
  # cairn key at all, when GSD already has `response_language`, is measured
  # and written in cairn-config.py's docstring (M-1/M-2/M-3): at the moment
  # /cairn:init asks, `.planning/` does not exist and cairn is forbidden from
  # creating it.
  #
  # Documented override (plan 30-01): seven -> eight, for
  # `git.control_branches`. Same rule, same shape: the readers are named and
  # all three ship in this cycle — cairn-land.py writes the answer through
  # `set` and reads it through `get`, cairn-status.py renders from its report
  # and cairn-doctor.py's phase-landed check cross-checks against it. It is a
  # comma-separated LIST because gitflow really does keep two control branches
  # at once, and empty means the question was never answered rather than "no
  # branch".
  #
  # Documented override (plan 30-03): eight -> nine, for `git.review_state`.
  # It is the switch on the ONLY cairn script that talks to a forge, its
  # default is `off`, and its reader is cairn-review.py — a separate file
  # precisely so the structural inventories over cairn-land.py and
  # cairn-status.py keep proving those two make no network call.
  assert_json_eq "$output" '[.keys[].key] | sort | join(",")' \
    'agents.response_language,autonomous.max_cycles,autonomous.max_parallel,bookkeep.auto_commit,git.control_branches,git.review_state,jira.link,ship.pr_scope,test.jobs'
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
  assert_json_eq "$output" \
    '[.keys[] | select(.key == "agents.response_language") | .reader][0]' \
    'cairn-parallel.py prepare'
}

#-----------------------------------------------------------------------------
# Plan 24-01 — `agents.response_language`: the type, and the precedence.
#
# What these tests do NOT claim: that a subagent received the value. That
# proof lives at the delivery point, in tests/cairn-parallel.bats, reading the
# payload of `prepare --json` — because the defect this phase exists to close
# happened WITH the key correctly set (.planning/config.json:69 already said
# pt-BR), so an assertion about config bytes would have been green on the day
# it broke.
#-----------------------------------------------------------------------------

@test "the language key defaults to English, and says so explicitly rather than by omission" {
  make_config_fixture

  run bash "$CONFIG" get agents.response_language --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  [ "$output" = "English" ]

  run bash "$CONFIG" get agents.response_language --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' 'English'
  # Explicit, not implicit: `source` names where English came from. A key that
  # was merely absent would answer the same value with no way to tell the two
  # apart, which is the "silent default wins until somebody notices" the
  # roadmap card names.
  assert_json_eq "$output" '.source' 'default'
  assert_json_eq "$output" '.planning_key' 'response_language'
}

@test "with only .cairn/config.json — the state a fresh install is actually in — the cairn key governs" {
  make_config_fixture
  # No .planning/ at all. This is not a contrived state: /cairn:init asks
  # BEFORE the /gsd:new-project hand-off, so this is the repo at the moment
  # the answer is given. If the key did not govern here it would govern
  # nowhere, which is the "declared and read by nothing" defect.
  [ ! -e "$ROOT/.planning" ]

  bash "$CONFIG" set agents.response_language Portuguese --project-dir "$ROOT"

  run bash "$CONFIG" get agents.response_language --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' 'Portuguese'
  assert_json_eq "$output" '.source' 'file'
}

@test "GSD's .planning/config.json outranks the cairn key, and source names the winner" {
  make_config_fixture
  bash "$CONFIG" set agents.response_language Portuguese --project-dir "$ROOT"
  mkdir -p "$ROOT/.planning"
  printf '{\n  "response_language": "Japanese"\n}\n' \
    > "$ROOT/.planning/config.json"

  run bash "$CONFIG" get agents.response_language --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  # Breaks if the precedence is inverted — the case where cairn's subagents
  # answer in one language and GSD's ~30 workflows answer in another IN THE
  # SAME RUN, which is the divergence, not the fix.
  assert_json_eq "$output" '.value' 'Japanese'
  assert_json_eq "$output" '.source' 'planning'

  run bash "$CONFIG" list --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  grep -qF "which outranks this file" <<<"$output"
}

@test "a corrupt .planning/config.json degrades to the cairn key instead of taking the read down" {
  make_config_fixture
  bash "$CONFIG" set agents.response_language Portuguese --project-dir "$ROOT"
  mkdir -p "$ROOT/.planning"
  printf 'this is not json at all\n' > "$ROOT/.planning/config.json"

  run bash "$CONFIG" get agents.response_language --project-dir "$ROOT" --json
  # Exit zero is the assertion. GSD's file is not ours to validate, and a die
  # here would take down cairn-parallel.py batch and prepare, both of which
  # shell out to this script on every run.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' 'Portuguese'
  assert_json_eq "$output" '.source' 'file'
}

@test "a .planning value of the wrong type falls through instead of winning" {
  make_config_fixture
  bash "$CONFIG" set agents.response_language Portuguese --project-dir "$ROOT"
  mkdir -p "$ROOT/.planning"
  # null is GSD's own "unset" for this key (config-loader.cjs:755 emits null),
  # and an empty string is a key that looks answered while saying nothing.
  printf '{\n  "response_language": null\n}\n' > "$ROOT/.planning/config.json"
  run bash "$CONFIG" get agents.response_language --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' 'Portuguese'
  assert_json_eq "$output" '.source' 'file'

  printf '{\n  "response_language": ""\n}\n' > "$ROOT/.planning/config.json"
  run bash "$CONFIG" get agents.response_language --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' 'Portuguese'
  assert_json_eq "$output" '.source' 'file'
}

@test "an empty, multi-line or over-long language exits 3 and leaves the file exactly as it was" {
  make_config_fixture
  bash "$CONFIG" set agents.response_language Portuguese --project-dir "$ROOT"
  cp "$ROOT/.cairn/config.json" "$BATS_TEST_TMPDIR/before.json"

  local bad
  for bad in "" "   " "$(printf 'pt\nBR')" "$(python3 -c 'print("x"*41)')"; do
    run bash "$CONFIG" set agents.response_language "$bad" --project-dir "$ROOT"
    [ "$status" -eq 3 ]
  done

  # Validation happens BEFORE the write, so a rejected value is not a write
  # that got undone — it is a write that never happened.
  run diff "$BATS_TEST_TMPDIR/before.json" "$ROOT/.cairn/config.json"
  [ "$status" -eq 0 ]

  run bash "$CONFIG" get agents.response_language --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  [ "$output" = "Portuguese" ]
}

#-----------------------------------------------------------------------------
# Plan 24-02 — the propagation into GSD's own config.
#
# Mechanism rather than prose: the defect this phase closes was "the prose
# said to hand the value over and nobody did", so the hand-over from cairn's
# key to GSD's is done by `set` itself. Its ONE condition — the GSD file must
# already exist — is three measurements, not caution:
#
#   M-1  `gsd-tools query config-set response_language X` CREATES `.planning/`
#        when absent (measured: exit 0, directory appears with only
#        config.json in it).
#   M-2  a `.planning/` holding only config.json makes cairn-migrate.py
#        classify() answer state A instead of D — and init.md:20-22 makes
#        state A STOP the init and divert to /cairn:migrate.
#   M-3  init.md:153 forbids it in writing.
#-----------------------------------------------------------------------------

# A .planning/config.json with several keys, in GSD's own 2-space shape and
# WITHOUT response_language — the state a project is in right after
# /gsd:new-project has run.
write_planning_config() {
  mkdir -p "$ROOT/.planning"
  cat > "$ROOT/.planning/config.json" <<'JSONEOF'
{
  "model_profile": "balanced",
  "commit_docs": true,
  "git": {
    "branching_strategy": "none"
  },
  "zzz_last_key": "stays last"
}
JSONEOF
}

@test "set of the language never creates .planning/ when it is absent, and says it did not propagate" {
  make_config_fixture
  [ ! -e "$ROOT/.planning" ]

  run bash "$CONFIG" set agents.response_language Portuguese \
    --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.propagated' 'false'
  assert_json_eq "$output" '.propagation_reason' 'planning-config-absent'

  # The assertion this test exists for. Creating the directory here would
  # flip cairn-migrate's state letter from D to A on the very repo cairn just
  # touched, and the next /cairn:init would refuse to continue (M-1/M-2/M-3).
  [ ! -e "$ROOT/.planning" ]
  # And the answer itself was still recorded — the propagation failing is not
  # the write failing.
  run bash "$CONFIG" get agents.response_language --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  [ "$output" = "Portuguese" ]
}

@test "set of the language writes GSD's key when its file exists, touching only the new key's boundary and reordering nothing" {
  make_config_fixture
  write_planning_config
  cp "$ROOT/.planning/config.json" "$BATS_TEST_TMPDIR/planning-before.json"

  run bash "$CONFIG" set agents.response_language Portuguese \
    --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.propagated' 'true'

  run jq -r '.response_language' "$ROOT/.planning/config.json"
  [ "$status" -eq 0 ]
  [ "$output" = "Portuguese" ]

  # The exact cost of the propagation, measured rather than claimed. Plan
  # 24-02 said "a diff of exactly one line"; the measurement corrected it and
  # the correction is written here instead of the sentence quietly changing:
  # appending a key to a JSON object necessarily puts a comma on the line that
  # used to be last, so the honest shape is ONE line removed and TWO added,
  # and both of them concern the boundary of the new key. Nothing else moves.
  run bash -c "diff '$BATS_TEST_TMPDIR/planning-before.json' '$ROOT/.planning/config.json' | grep -c '^>'"
  [ "$status" -eq 0 ]
  [ "$output" -eq 2 ]
  run bash -c "diff '$BATS_TEST_TMPDIR/planning-before.json' '$ROOT/.planning/config.json' | grep -c '^<'"
  [ "$output" -eq 1 ]
  run bash -c "diff '$BATS_TEST_TMPDIR/planning-before.json' '$ROOT/.planning/config.json' | grep -F 'zzz_last_key' | grep -c ."
  [ "$output" -eq 2 ]

  # And the strong half: strip the key we added and the file is the ORIGINAL
  # again, key for key, value for value, IN ORDER. Breaks on re-serialization
  # that reorders or reindents a file whose diffs other people read — which is
  # why sort_keys is deliberately absent from the propagating write even
  # though our own file uses it.
  run python3 -c '
import json, sys
before = json.load(open(sys.argv[1]))
after = json.load(open(sys.argv[2]))
assert "response_language" in after, "the key was not written"
del after["response_language"]
assert list(after.items()) == list(before.items()), "other keys moved or changed"
print("identical")
' "$BATS_TEST_TMPDIR/planning-before.json" "$ROOT/.planning/config.json"
  [ "$status" -eq 0 ]
  [ "$output" = "identical" ]

  # Key order preserved on disk, not just semantically.
  run jq -r 'keys_unsorted | .[0]' "$ROOT/.planning/config.json"
  [ "$output" = "model_profile" ]
  run jq -r 'keys_unsorted | .[3]' "$ROOT/.planning/config.json"
  [ "$output" = "zzz_last_key" ]
}

@test "a second set replaces GSD's value instead of duplicating the key" {
  make_config_fixture
  write_planning_config
  bash "$CONFIG" set agents.response_language Portuguese --project-dir "$ROOT"
  local before
  before="$(wc -l < "$ROOT/.planning/config.json")"

  run bash "$CONFIG" set agents.response_language Japanese \
    --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.propagated' 'true'

  run jq -r '.response_language' "$ROOT/.planning/config.json"
  [ "$output" = "Japanese" ]
  [ "$(wc -l < "$ROOT/.planning/config.json")" -eq "$before" ]
  run bash -c "grep -c 'response_language' '$ROOT/.planning/config.json'"
  [ "$output" -eq 1 ]
}

@test "an unreadable .planning/config.json is left exactly as it was, and set still exits 0" {
  make_config_fixture
  mkdir -p "$ROOT/.planning"
  printf 'half a file {{{ not json\n' > "$ROOT/.planning/config.json"
  cp "$ROOT/.planning/config.json" "$BATS_TEST_TMPDIR/corrupt-before"

  run bash "$CONFIG" set agents.response_language Portuguese \
    --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.propagated' 'false'
  assert_json_eq "$output" '.propagation_reason' 'planning-config-unreadable'

  # Rewriting a file we could not parse would destroy whatever was in it.
  run diff "$BATS_TEST_TMPDIR/corrupt-before" "$ROOT/.planning/config.json"
  [ "$status" -eq 0 ]
}

@test "a key with no counterpart in GSD's config never touches that file" {
  make_config_fixture
  write_planning_config
  cp "$ROOT/.planning/config.json" "$BATS_TEST_TMPDIR/untouched-before.json"

  run bash "$CONFIG" set ship.pr_scope milestone --project-dir "$ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.propagated' 'false'
  assert_json_eq "$output" '.propagation_reason' 'key-is-cairn-only'

  # Breaks if propagation ever became a property of `set` rather than of the
  # key: five of the seven keys are nobody's business but cairn's.
  run diff "$BATS_TEST_TMPDIR/untouched-before.json" \
    "$ROOT/.planning/config.json"
  [ "$status" -eq 0 ]
}

@test "the /cairn:config command offers the language and says which file wins when the two disagree" {
  local cmd="$CAIRN_REPO_ROOT/cairn/commands/config.md"
  [ -f "$cmd" ]

  grep -qF "agents.response_language" "$cmd"
  # The default has to be named as the default, not left as the first item of
  # a list — "inglês nunca é o silêncio de uma chave ausente".
  grep -qF "the default is English" "$cmd"
  # Breaks if the two doors start telling different stories about precedence,
  # which is the disagreement the subordination exists to prevent.
  grep -qF "that value governs" "$cmd"
  grep -qF "GSD's key outranks this one" "$cmd"
}

@test "the human render of a propagating set names the other file, and of a non-propagating one says why" {
  make_config_fixture
  write_planning_config

  run bash "$CONFIG" set agents.response_language Portuguese \
    --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  grep -qF ".planning/config.json:response_language" <<<"$output"

  rm -rf "$ROOT/.planning"
  run bash "$CONFIG" set agents.response_language Portuguese \
    --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  # A silent mechanism is indistinguishable from an absent one.
  grep -qF "not propagated" <<<"$output"
  grep -qF "planning-config-absent" <<<"$output"
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
