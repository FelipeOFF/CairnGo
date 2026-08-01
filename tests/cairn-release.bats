#!/usr/bin/env bats
# cairn-release.bats — exercises the version-carrier check's CLI contract
# (cairn-release.py / the cairn-release.sh wrapper):
#   0 every lockstep carrier agrees and every carrier is valid semver,
#   2 usage, 6 findings.
#
# The two rules under test are NOT the same rule (Phase 19, D-02):
#   plugin.json == marketplace.json == CHANGELOG head == git tag
#   capability.json -> its own axis, must only be VALID SEMVER
# Two tests pin that from both sides: capability at 1.0.0 while the rest read
# 1.5.0 must exit 0, and capability at `1.0` must exit 6 saying `invalid
# semver`, never `mismatch`.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so substring checks use grep -qF and negative checks
# use refute_in_output.

load 'helpers'

RELEASE="$CAIRN_SCRIPTS_DIR/cairn-release.sh"

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

#-----------------------------------------------------------------------------
# Task 1: the tracer — the real repo, read end to end, one verdict
#-----------------------------------------------------------------------------

@test "the tracer: check against THIS repo agrees and prints the current version" {
  # Deliberately the real repository, not a fixture: the carriers this command
  # exists to compare are this repo's own, and the third one
  # (.claude-plugin/marketplace.json, at the nested metadata.version) is the
  # one three releases of eyeballing missed.
  run bash "$RELEASE" check --project-dir "$CAIRN_REPO_ROOT"
  [ "$status" -eq 0 ]
  grep -qF "[cairn-release] ok" <<<"$output"

  local plugin_version
  plugin_version="$(jq -r '.version' \
    "$CAIRN_REPO_ROOT/cairn/.claude-plugin/plugin.json")"
  grep -qF "$plugin_version" <<<"$output"

  run bash "$RELEASE" check --project-dir "$CAIRN_REPO_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.version' "$plugin_version"
  # Every carrier reports its own path, its own key and its own value — the
  # three JSON key paths differ, which is half the reason this command exists.
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="plugin") | .key' 'version'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="marketplace") | .key' 'metadata.version'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="capability") | .rule' 'own-axis'
  assert_json_eq "$output" '.carriers | length' '5'
}
