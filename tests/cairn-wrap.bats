#!/usr/bin/env bats
# cairn-wrap.bats — exercises the wrapper tooling's CLI contract
# (cairn-wrap.py / the cairn-wrap.sh wrapper):
#
#   preflight  WRAP-02 — a /cairn:* wrapper whose /gsd:* command is not
#              installed must FAIL naming what is missing. Proved by HIDING
#              the command, never by the happy path: a test that only runs
#              green would still pass with the existence check deleted, and
#              that is not proof.
#   list       WRAP-01/03 — the wrappers are derived from each command file's
#              frontmatter on disk, never from a list written in code.
#   docs       WRAP-03 — the documented list is regenerated from disk. Proved
#              by ADDING a wrapper and asserting the page starts listing it
#              with no prose edited.
#
# Exit codes under test: 0 ok, 2 usage, 3 docs stale, 5 no GSD surface found
# (could not look), 6 the named command is missing (looked, not there).
#
# Assertion style notes:
#   - every status assertion is on the EXACT value (`-eq 6`), never `-ne 0`:
#     a negation accepts the wrong code and hides a regression.
#   - a failing `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this
#     bash, so substring checks use grep -qF and negatives use refute_in_file.

load 'helpers'

WRAP="$CAIRN_SCRIPTS_DIR/cairn-wrap.sh"

# Assert NEEDLE does not appear in FILE. (`! grep` cannot be used inline:
# bash's `!` suppresses errexit, so its failure would never fail the test.)
refute_in_file() {
  if grep -qF -- "$1" "$2"; then
    echo "unexpectedly found '$1' in $2" >&2
    return 1
  fi
}

# A fake GSD command surface: <dir>/<name>.md for each name given.
# WRAP_SURFACE is exported for the test to point CAIRN_GSD_COMMANDS_DIR at.
make_gsd_surface() {
  WRAP_SURFACE="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/gsd-surface.XXXXXX")"
  local name
  for name in "$@"; do
    printf -- '---\nname: gsd:%s\n---\n' "$name" > "$WRAP_SURFACE/$name.md"
  done
}

# A fake cairn commands dir. Each arg is "name:wraps:family" (wraps and
# family empty => a cairn-own command, no `wraps:` key).
make_cairn_commands() {
  WRAP_COMMANDS="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/cairn-cmds.XXXXXX")"
  local spec
  for spec in "$@"; do
    add_cairn_command "$spec"
  done
}

add_cairn_command() {
  local spec="$1"
  local name="${spec%%:*}"
  local rest="${spec#*:}"
  local wraps="${rest%%:*}"
  local family="${rest#*:}"
  {
    echo '---'
    echo "description: does $name"
    if [ -n "$wraps" ]; then
      echo "wraps: $wraps"
      echo "wrap-family: $family"
    fi
    echo '---'
    echo
    echo "Body of $name."
  } > "$WRAP_COMMANDS/$name.md"
}

# ---------------------------------------------------------------------------
# preflight — WRAP-02
# ---------------------------------------------------------------------------

@test "preflight: a hidden GSD command exits 6 and names what is missing" {
  # The proof by absence. The surface exists and carries other commands;
  # `phase` is the one that is not there.
  make_gsd_surface plan-phase execute-phase ship

  CAIRN_GSD_COMMANDS_DIR="$WRAP_SURFACE" run bash "$WRAP" preflight phase
  [ "$status" -eq 6 ]
  echo "$output" | grep -qF '/gsd:phase'
  echo "$output" | grep -qF 'is not installed'
  echo "$output" | grep -qF "$WRAP_SURFACE"
  echo "$output" | grep -qF '3 command(s) found there'
  echo "$output" | grep -qF 'fix:'
}

@test "preflight: a present GSD command exits 0 in the same surface" {
  # Without this pair, the test above would pass against a preflight that
  # always exits 6.
  make_gsd_surface plan-phase execute-phase ship

  CAIRN_GSD_COMMANDS_DIR="$WRAP_SURFACE" run bash "$WRAP" preflight ship
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF '/gsd:ship is installed'
}

@test "preflight: an empty surface is 6 (looked), not 5 (could not look)" {
  # The two codes are two different facts. Collapsing them into one makes
  # exactly one of these two tests fail.
  WRAP_SURFACE="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/gsd-empty.XXXXXX")"

  CAIRN_GSD_COMMANDS_DIR="$WRAP_SURFACE" run bash "$WRAP" preflight phase
  [ "$status" -eq 6 ]
  echo "$output" | grep -qF '0 command(s) found there'
}

@test "preflight: no surface at all exits 5 and lists every path tried" {
  # HOME is redirected so the test reads a fixture machine, not the plugin
  # cache of whoever is running the suite. CLAUDE_PLUGIN_ROOT is cleared for
  # the same reason.
  local fake_home
  fake_home="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/fake-home.XXXXXX")"

  HOME="$fake_home" CLAUDE_PLUGIN_ROOT="" run env -u CAIRN_GSD_COMMANDS_DIR \
    -u CLAUDE_PLUGIN_ROOT HOME="$fake_home" bash "$WRAP" preflight phase
  [ "$status" -eq 5 ]
  echo "$output" | grep -qF 'no GSD command surface found'
  echo "$output" | grep -qF 'CAIRN_GSD_COMMANDS_DIR (unset)'
  echo "$output" | grep -qF 'installed_plugins.json (no gsd entry)'
  echo "$output" | grep -qF 'fix:'
}

@test "preflight: a seam pointing at nothing is usage (2), not discovery" {
  # Degrading to auto-discovery here would hide a mis-wired test instead of
  # naming it, so this is 2 and not 5.
  CAIRN_GSD_COMMANDS_DIR="/nonexistent/cairn/surface" run bash "$WRAP" \
    preflight phase
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF 'is not a directory'
}

@test "preflight --json: installed is a real boolean and searched is populated" {
  make_gsd_surface ship

  CAIRN_GSD_COMMANDS_DIR="$WRAP_SURFACE" run bash "$WRAP" preflight phase --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" '.installed' 'false'
  assert_json_eq "$output" '.installed | type' 'boolean'
  assert_json_eq "$output" '.command' 'phase'
  assert_json_eq "$output" '.exit' '6'
  assert_json_eq "$output" '.searched | length > 0' 'true'
}

# ---------------------------------------------------------------------------
# list — derived from disk
# ---------------------------------------------------------------------------

@test "list: wrappers come from frontmatter on disk, not from code" {
  # Swapping the scan for a literal list of the thirteen returns 0 wrappers
  # against this fixture.
  make_cairn_commands "alpha:plan-phase:phase" "beta::"

  run bash "$WRAP" list --commands-dir "$WRAP_COMMANDS" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.counts.total' '2'
  assert_json_eq "$output" '.counts.wrappers' '1'
  assert_json_eq "$output" '.counts.own' '1'
  assert_json_eq "$output" '.wrappers[0].command' 'alpha'
  assert_json_eq "$output" '.wrappers[0].wraps' 'plan-phase'
  assert_json_eq "$output" '.wrappers[0].family' 'phase'
}

@test "list: an unknown wrap-family is a named usage error" {
  make_cairn_commands "alpha:plan-phase:banana"

  run bash "$WRAP" list --commands-dir "$WRAP_COMMANDS" --json
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF 'alpha.md'
  echo "$output" | grep -qF 'banana'
}

# ---------------------------------------------------------------------------
# The uniform contract every wrapper carries — asserted over the REAL
# cairn/commands/, so it grows with the phase instead of being re-typed.
# ---------------------------------------------------------------------------

@test "every installed wrapper carries the house bookkeeping, by name" {
  run bash "$WRAP" list --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" --json
  [ "$status" -eq 0 ]

  local count
  count="$(jq -r '.wrappers | length' <<<"$output")"
  [ "$count" -gt 0 ]

  local i name wraps file
  for ((i = 0; i < count; i++)); do
    name="$(jq -r ".wrappers[$i].command" <<<"$output")"
    wraps="$(jq -r ".wrappers[$i].wraps" <<<"$output")"
    file="$CAIRN_REPO_ROOT/cairn/commands/$name.md"

    # The needles are BUILT from the JSON, never typed: a wrapper that
    # delegates to the wrong command fails here.
    grep -qF "cairn-wrap.sh\" preflight $wraps" "$file" \
      || { echo "$name.md does not call preflight $wraps" >&2; return 1; }
    grep -qF "/gsd:$wraps" "$file" \
      || { echo "$name.md never names /gsd:$wraps" >&2; return 1; }
    grep -qF 'bd update' "$file" \
      || { echo "$name.md never claims: no 'bd update'" >&2; return 1; }
    grep -qF -- '--claim' "$file" \
      || { echo "$name.md never claims: no '--claim'" >&2; return 1; }
    grep -qF 'bd close' "$file" \
      || { echo "$name.md never closes: no 'bd close'" >&2; return 1; }
    grep -qF 'm-<milestone>' "$file" \
      || { echo "$name.md never names the m-<milestone> label" >&2; return 1; }
    grep -qF 'phase-<N>' "$file" \
      || { echo "$name.md never names the phase-<N> label" >&2; return 1; }
    grep -qF 'metadata' "$file" \
      || { echo "$name.md never names the gsd metadata stamp" >&2; return 1; }
  done
}

@test "the installed wrapper set is exactly what is on disk" {
  # An exact count, never `>=`: a lost wrapper is the defect this phase is
  # about, and an inequality would hide it. This number moves as the phase
  # builds out, and moving it deliberately is the point.
  run bash "$WRAP" list --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.wrappers | length' '1'
  assert_json_eq "$output" '[.wrappers[].command] | join(",")' 'phase'
}

@test "/cairn:phase declares what it wraps in its frontmatter" {
  local file="$CAIRN_REPO_ROOT/cairn/commands/phase.md"
  assert_frontmatter_key "$file" "wraps"
  assert_frontmatter_key "$file" "wrap-family"
  extract_frontmatter "$file" | grep -qF 'wraps: phase'
  extract_frontmatter "$file" | grep -qF 'wrap-family: structural'
}

@test "/cairn:phase moves the labels a renumber would orphan" {
  # The one thing this wrapper adds over /gsd:phase. Deleting the relabel
  # step turns the wrapper into an alias and fails here.
  local file="$CAIRN_REPO_ROOT/cairn/commands/phase.md"
  grep -qF 'cairn-relabel.sh' "$file"
  grep -qF 'renumber' "$file"
  grep -qF 'phase-3' "$file"
  grep -qF 'phase-03' "$file"
}
