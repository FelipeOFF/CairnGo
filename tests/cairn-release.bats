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

# A throwaway carrier tree: a real git repo (so the tag carrier has a real,
# empty tag namespace to answer from) holding all four version carriers at
# their REAL paths and REAL key paths — plugin.json's top-level `version`,
# marketplace.json's NESTED `metadata.version`, the CHANGELOG's first released
# heading, capability.json's top-level `version`. Never mutates the real repo.
# $1 = the lockstep version (default 1.5.0), $2 = capability's own axis
# (default 1.0.0 — deliberately different, that is D-02).
make_release_fixture() {
  local version="${1:-1.5.0}" cap="${2:-1.0.0}"
  make_tmp_repo
  mkdir -p cairn/.claude-plugin .claude-plugin cairn/capability
  printf '{"name": "cairn", "version": "%s"}\n' "$version" \
    > cairn/.claude-plugin/plugin.json
  printf '{"name": "cairngo", "metadata": {"version": "%s"}, "plugins": []}\n' \
    "$version" > .claude-plugin/marketplace.json
  printf '{"id": "cairn", "version": "%s"}\n' "$cap" \
    > cairn/capability/capability.json
  cat > CHANGELOG.md <<EOF
# Changelog

## [$version] - 2026-08-01

### Added

- fixture entry
EOF
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

#-----------------------------------------------------------------------------
# Task 2: the failures — each test with the break that turns it red
#-----------------------------------------------------------------------------

# Break: drop marketplace.json from the compared set. Literally the hole that
# shipped three times.
@test "plugin.json and marketplace.json disagree: exit 6 naming both paths and both values" {
  make_release_fixture 1.5.0
  printf '{"name": "cairngo", "metadata": {"version": "1.4.2"}, "plugins": []}\n' \
    > .claude-plugin/marketplace.json

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 6 ]
  grep -qF "mismatch" <<<"$output"
  grep -qF "cairn/.claude-plugin/plugin.json" <<<"$output"
  grep -qF ".claude-plugin/marketplace.json" <<<"$output"
  grep -qF "1.5.0" <<<"$output"
  grep -qF "1.4.2" <<<"$output"
  # The finding names the KEY too, and the two keys differ.
  grep -qF "metadata.version" <<<"$output"

  run bash "$RELEASE" check --project-dir "$PWD" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.version' 'null'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="marketplace") | .status' 'mismatch'
}

# Break: stop reading the CHANGELOG heading at all.
@test "the CHANGELOG head disagrees with the manifests: exit 6 naming both versions" {
  make_release_fixture 1.5.0
  cat > CHANGELOG.md <<'EOF'
# Changelog

## [1.4.2] - 2026-07-28

### Added

- an older entry left at the top by mistake
EOF

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 6 ]
  grep -qF "mismatch" <<<"$output"
  grep -qF "CHANGELOG.md" <<<"$output"
  grep -qF "1.5.0" <<<"$output"
  grep -qF "1.4.2" <<<"$output"
}

# Break: add capability.json to the equality set. This test is what pins D-02
# against a future well-meaning tightening.
@test "capability.json on its own axis (1.0.0) while the rest read 1.5.0: exit 0" {
  make_release_fixture 1.5.0 1.0.0

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "[cairn-release] ok" <<<"$output"
  refute_in_output "mismatch"

  run bash "$RELEASE" check --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.version' '1.5.0'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="capability") | .value' '1.0.0'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="capability") | .status' 'ok'
}

# Break: remove the semver validation (the finding disappears), or swap the
# rule for equality (the token becomes the wrong one). The grep on the token
# catches both.
@test "capability.json at '1.0': exit 6 saying invalid semver, never mismatch" {
  make_release_fixture 1.5.0 1.0

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 6 ]
  grep -qF "invalid semver" <<<"$output"
  grep -qF "cairn/capability/capability.json" <<<"$output"
  grep -qF "1.0" <<<"$output"
  refute_in_output "mismatch"

  run bash "$RELEASE" check --project-dir "$PWD" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="capability") | .status' 'invalid semver'
  # The three lockstep carriers still agree — the finding is validity, not
  # equality.
  assert_json_eq "$output" \
    '[.findings[] | select(test("mismatch"))] | length' '0'
}

# Break: swallow the absence in a mute try/except, which would exit 0 — the
# green lie again.
@test "a carrier file is absent: exit 6 with 'missing' naming the path" {
  make_release_fixture 1.5.0
  rm .claude-plugin/marketplace.json

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 6 ]
  grep -qF "missing" <<<"$output"
  grep -qF ".claude-plugin/marketplace.json" <<<"$output"
  refute_in_output "Traceback"
}

# Break: read the version with an empty default. Three missing keys would then
# compare equal as three empty strings and the command would exit 0 claiming
# agreement between three nothings.
@test "a carrier is present but has no version key: exit 6 naming the file AND the key" {
  make_release_fixture 1.5.0
  printf '{"name": "cairngo", "metadata": {"description": "no version here"}}\n' \
    > .claude-plugin/marketplace.json

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 6 ]
  grep -qF "missing" <<<"$output"
  grep -qF ".claude-plugin/marketplace.json" <<<"$output"
  grep -qF "metadata.version" <<<"$output"
  refute_in_output "Traceback"
}

# The same trap from the other side: EVERY carrier missing its key must not
# read as three agreeing empty strings.
@test "every carrier missing its version key: exit 6, never a claimed agreement" {
  make_release_fixture 1.5.0
  printf '{"name": "cairn"}\n' > cairn/.claude-plugin/plugin.json
  printf '{"name": "cairngo", "metadata": {}}\n' \
    > .claude-plugin/marketplace.json
  printf '# Changelog\n\nnothing released yet\n' > CHANGELOG.md

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 6 ]
  refute_in_output "[cairn-release] ok"

  run bash "$RELEASE" check --project-dir "$PWD" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.version' 'null'
  # All THREE findings must be `missing`, each naming its own carrier. An
  # earlier draft only asserted `.findings | length == 3` and stayed GREEN
  # under the empty-default break — the empty strings were caught downstream
  # as `invalid semver` instead, so the test passed for the wrong reason and
  # proved nothing about the read. The token is what pins it.
  assert_json_eq "$output" \
    '[.findings[] | select(startswith("missing"))] | length' '3'
  refute_in_output "invalid semver"
}

# Break: let json.JSONDecodeError propagate.
@test "malformed JSON in a carrier: exit 6 with a message, never a traceback" {
  make_release_fixture 1.5.0
  printf '{"name": "cairn", "version": "1.5.0",\n' \
    > cairn/.claude-plugin/plugin.json

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 6 ]
  grep -qF "cairn/.claude-plugin/plugin.json" <<<"$output"
  grep -qF "not valid JSON" <<<"$output"
  refute_in_output "Traceback"
}

# Break: take the first '## [' blindly, which reads "Unreleased" as the
# version and mismatches against every manifest.
@test "'## [Unreleased]' above the first version is skipped: exit 0" {
  make_release_fixture 1.5.0
  cat > CHANGELOG.md <<'EOF'
# Changelog

## [Unreleased]

### Added

- work in flight

## [1.5.0] - 2026-08-01

### Added

- fixture entry
EOF

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "[cairn-release] ok" <<<"$output"
  refute_in_output "Unreleased"

  run bash "$RELEASE" check --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="changelog") | .value' '1.5.0'
}

@test "an uncreated git tag is reported pending, not a failure: exit 0" {
  make_release_fixture 1.5.0

  run bash "$RELEASE" check --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "pending" <<<"$output"

  run bash "$RELEASE" check --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.carriers[] | select(.name=="tag") | .key' 'v1.5.0'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="tag") | .status' 'pending'
}

# Break: ignore --require-tag, which would exit 0. This flag is how the plan
# that creates the tag proves D-02's fourth equality.
@test "an uncreated git tag under --require-tag: exit 6" {
  make_release_fixture 1.5.0

  run bash "$RELEASE" check --project-dir "$PWD" --require-tag
  [ "$status" -eq 6 ]
  grep -qF "missing" <<<"$output"
  grep -qF "v1.5.0" <<<"$output"
}

@test "the git tag exists and matches: exit 0 with the tag as an ok carrier" {
  make_release_fixture 1.5.0
  git commit -q --allow-empty -m "fixture"
  git tag v1.5.0

  run bash "$RELEASE" check --project-dir "$PWD" --require-tag --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.carriers[] | select(.name=="tag") | .status' 'ok'
  assert_json_eq "$output" '.carriers[] | select(.name=="tag") | .value' 'v1.5.0'
}

# Break: fall through to `check` by default, which would exit 0 on garbage.
@test "an unknown subcommand exits 2, and --help answers" {
  make_release_fixture 1.5.0

  run bash "$RELEASE" bump --project-dir "$PWD"
  [ "$status" -eq 2 ]

  run bash "$RELEASE" --help
  [ "$status" -eq 0 ]
  grep -qF "check" <<<"$output"

  run bash "$RELEASE" check --help
  [ "$status" -eq 0 ]
  grep -qF -- "--require-tag" <<<"$output"
}
