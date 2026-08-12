#!/usr/bin/env bats
# cairn-release.bats — exercises the CLI contract of cairn-release.py (through
# the cairn-release.sh wrapper): the version-carrier `check` and the release-
# notes derivation `notes`.
#   0 check: every lockstep carrier agrees and every carrier is valid semver;
#     notes: the section was found and printed with its migration answer,
#   2 usage, 6 findings.
#
# `notes` is pinned by a GOLDEN test that compares the whole derived output
# byte for byte. That is deliberate: the point of deriving the notes from the
# CHANGELOG is that no sentence about this release is written twice, and any
# normalisation or rewrite slipped onto that path turns the golden red.
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
  # `status` is a fact about this carrier ALONE — it was read and it is valid
  # semver. Whether it matches anything is a different question with its own
  # field (see the FIX-03 test below).
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="marketplace") | .status' 'ok'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="marketplace") | .agrees_with_reference' 'false'
}

# FIX-03 / CairnGo-tuh. MEASURED live with the CHANGELOG already at 1.5.0 and
# both manifests still at 1.4.2:
#
#     marketplace  1.4.2 (the OLD version)   -> status: ok
#     changelog    1.5.0 (the only correct)  -> status: mismatch
#
# The top verdict, the finding text and exit 6 were all correct — the gate
# never lied. What lied was the per-carrier field: comparisons run against
# present[0], so `status` meant "agrees with the first readable carrier" while
# reading as "is correct". A consumer filtering status=="mismatch" to find what
# to fix would be sent to the file that was already right.
#
# Deriving `status` from the MAJORITY was rejected by this same measurement:
# with two carriers at 1.4.2 and one at 1.5.0, the majority also accuses the
# changelog. Nothing offline can know which version was intended, so the field
# says what it measures instead of pretending to know.
@test "the reference carrier is named, and agreement is not called correctness" {
  make_release_fixture 1.5.0
  # Reproduce the measured shape exactly: the two manifests carry the OLD
  # version, the CHANGELOG carries the new one.
  printf '{"name": "cairn", "version": "1.4.2"}\n' \
    > cairn/.claude-plugin/plugin.json
  printf '{"name": "cairngo", "metadata": {"version": "1.4.2"}, "plugins": []}\n' \
    > .claude-plugin/marketplace.json

  run bash "$RELEASE" check --project-dir "$PWD" --json
  [ "$status" -eq 6 ]

  # The yardstick is NAMED, so nobody has to infer it from ordering.
  assert_json_eq "$output" '.reference' 'plugin'

  # Nothing in the payload claims the old value is correct.
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="marketplace") | .value' '1.4.2'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="marketplace") | .agrees_with_reference' 'true'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="changelog") | .value' '1.5.0'
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="changelog") | .agrees_with_reference' 'false'

  # And `mismatch` is gone from the per-carrier status vocabulary: "does not
  # match" is a statement about a PAIR, never about one file.
  assert_json_eq "$output" \
    '[.carriers[] | select(.status=="mismatch")] | length' '0'

  # The own-axis carrier is never compared, so it answers null rather than a
  # boolean that would read as a verdict (D-02).
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="capability") | .agrees_with_reference' 'null'

  # The finding still names both sides, both keys and both values — the gate
  # was never the broken part.
  assert_json_eq "$output" '.findings | length' '1'
  grep -qF "1.4.2" <<<"$output"
  grep -qF "1.5.0" <<<"$output"
}

@test "an unreadable carrier answers null about agreement, never false" {
  make_release_fixture 1.5.0
  rm .claude-plugin/marketplace.json

  run bash "$RELEASE" check --project-dir "$PWD" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="marketplace") | .status' 'missing'
  # The key must EXIST and hold null — an absent key answers `null` to jq too,
  # which would make this assertion pass against a payload that never learned
  # the field.
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="marketplace") | has("agrees_with_reference")' \
    'true'
  # `false` would say "it disagrees", which is a comparison that never
  # happened. The three-nothings trap, one field over.
  assert_json_eq "$output" \
    '.carriers[] | select(.name=="marketplace") | .agrees_with_reference' 'null'
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

#-----------------------------------------------------------------------------
# Task 3: notes — derived from the CHANGELOG, never written a second time
#-----------------------------------------------------------------------------

# A CHANGELOG with THREE version sections around the one under test, so both
# neighbours can be proven not to leak. Every section carries a marker string
# that exists nowhere else in the file, which is what makes "did not leak" an
# assertion instead of a hope. The middle section is shaped like the real
# [1.5.0]: a preamble, two change subsections, and the migration subsection
# last — Keep a Changelog's order, which is NOT the published order.
#
# Entries WRAP onto indented continuation lines on purpose. A first draft of
# this fixture was one flat line per entry, and under the reflow break — the
# very break the golden test exists to catch — it stayed GREEN, because
# collapsing whitespace on a line that has none changes no bytes. The
# indentation is what gives the golden something to lose.
make_notes_fixture() {
  make_tmp_repo
  cat > CHANGELOG.md <<'EOF'
# Changelog

All notable changes to this project are documented in this file.

## [1.6.0] - 2026-09-01

### Added

- **an entry that says NEWERONLY** and wraps onto a second
  line, indented.

## [1.5.0] - 2026-08-01

a section preamble that says PREAMBLEONLY and wraps onto a
second line

### Added

- **an entry that says ADDEDONLY** and wraps onto a second
  line, indented, the way the real entries do.

### Fixed

- **an entry that says FIXEDONLY** and wraps onto a second
  line, indented too.

### Upgrading

a migration answer that says MIGRATIONONLY, wrapping onto a
second line as well

```
   run this to find out
```

## [1.4.2] - 2026-07-28

### Added

- **an entry that says OLDERONLY** and wraps onto a second
  line, indented.
EOF
}

# 1-based line number of the first line of $output containing $1.
line_of() {
  grep -nF -- "$1" <<<"$output" | head -1 | cut -d: -f1
}

# Break: ANY normalisation, reflow, re-wrap or rewrite on the derivation path.
# This is the test that turns "derived, never written a second time" from an
# intention into something a machine checks: the whole output, byte for byte,
# against the CHANGELOG's own bytes relabelled and reordered.
@test "notes: the derived output matches the golden text byte for byte" {
  make_notes_fixture

  run bash "$RELEASE" notes 1.5.0 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  expected="$(cat <<'EOF'
## Am I affected?

a migration answer that says MIGRATIONONLY, wrapping onto a
second line as well

```
   run this to find out
```

## What changed

a section preamble that says PREAMBLEONLY and wraps onto a
second line

### Added

- **an entry that says ADDEDONLY** and wraps onto a second
  line, indented, the way the real entries do.

### Fixed

- **an entry that says FIXEDONLY** and wraps onto a second
  line, indented too.
EOF
)"
  [ "$output" = "$expected" ]
}

# Break: cut to end of file instead of to the next version heading. Every
# older release would then be republished as part of this one's notes.
@test "notes: neither neighbouring version section leaks into the output" {
  make_notes_fixture

  run bash "$RELEASE" notes 1.5.0 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  refute_in_output "OLDERONLY"
  refute_in_output "NEWERONLY"
  refute_in_output "## [1.4.2]"
  refute_in_output "## [1.6.0]"
}

# Break: invert the mapping, or stop the cut at the first subsection heading.
# The published order is the users' question first — that is what the three
# 1.4.x releases established, and it is the opposite of the file's order.
@test "notes: the migration answer sits under the user's question, the rest under the changes" {
  make_notes_fixture

  run bash "$RELEASE" notes 1.5.0 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  local question changes migration added fixed
  question="$(line_of '## Am I affected?')"
  changes="$(line_of '## What changed')"
  migration="$(line_of 'MIGRATIONONLY')"
  added="$(line_of 'ADDEDONLY')"
  fixed="$(line_of 'FIXEDONLY')"

  [ "$question" -lt "$migration" ]
  [ "$migration" -lt "$changes" ]
  [ "$changes" -lt "$added" ]
  [ "$added" -lt "$fixed" ]
  # The migration subsection's own heading is replaced by the question, not
  # printed twice.
  refute_in_output "### Upgrading"
}

# Break: derive the notes anyway. The published release then goes out unable
# to answer "what do I have to do?" — which is literally why three consecutive
# 1.4.x releases existed.
@test "notes: a section with no migration subsection exits 6, never publishable output" {
  make_notes_fixture

  run bash "$RELEASE" notes 1.4.2 --project-dir "$PWD"
  [ "$status" -eq 6 ]
  grep -qF "1.4.2" <<<"$output"
  grep -qF "Upgrading" <<<"$output"
  refute_in_output "## What changed"
  refute_in_output "OLDERONLY"
}

# The same failure from the other side: a heading with nothing under it must
# not pass as an answer.
@test "notes: an empty migration subsection exits 6 too" {
  make_notes_fixture
  cat > CHANGELOG.md <<'EOF'
# Changelog

## [1.5.0] - 2026-08-01

### Added

- an entry that says ADDEDONLY

### Upgrading

EOF

  run bash "$RELEASE" notes 1.5.0 --project-dir "$PWD"
  [ "$status" -eq 6 ]
  grep -qF "Upgrading" <<<"$output"
  refute_in_output "## Am I affected?"
}

# Break: print nothing and exit 0. A silent empty release note is the same
# green-without-proof this milestone is named after.
#
# The message is asserted, not just the code: a first draft only grepped the
# version string, and a break that cut an EMPTY section still exited 6 —
# through the no-migration path, whose message also names the version. Two
# different failures reported identically is the class of thing this phase is
# about, so the finding must say which one happened.
@test "notes: a version absent from the CHANGELOG exits 6 naming the version" {
  make_notes_fixture

  run bash "$RELEASE" notes 9.9.9 --project-dir "$PWD"
  [ "$status" -eq 6 ]
  grep -qF "## [9.9.9]" <<<"$output"
  grep -qF "CHANGELOG.md" <<<"$output"
  refute_in_output "Upgrading"
  refute_in_output "## Am I affected?"
  refute_in_output "Traceback"
}

# Break: default the version to the CHANGELOG head, which would silently
# derive a release nobody asked for.
@test "notes without a version exits 2, and its --help answers" {
  make_notes_fixture

  run bash "$RELEASE" notes --project-dir "$PWD"
  [ "$status" -eq 2 ]

  run bash "$RELEASE" notes --help
  [ "$status" -eq 0 ]
  grep -qF -- "--project-dir" <<<"$output"

  run bash "$RELEASE" --help
  [ "$status" -eq 0 ]
  grep -qF "notes" <<<"$output"
}
