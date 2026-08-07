#!/usr/bin/env bats
# capability.bats — exercises the GSD capability bundle (cairn/capability/):
# manifest envelope shape, fragment/script path integrity, the blocking
# deterministic ship gate, the optional gsd-core validateCapability pass, and
# the bundled scripts' no-op / block / report contracts.
#
# Assertion style note (same as cairn-map.bats): a failing `[[ ]]` or `! cmd`
# mid-test does NOT fail a bats test on this bash, so substring checks use
# grep -qF over "$output" written through printf.

load 'helpers'

CAP_DIR="$CAIRN_REPO_ROOT/cairn/capability"
CAP_JSON="$CAIRN_REPO_ROOT/cairn/capability/capability.json"
GATE_SH="$CAIRN_REPO_ROOT/cairn/capability/scripts/cairn-loop-gate.sh"
MAP_SHIM="$CAIRN_REPO_ROOT/cairn/capability/scripts/cairn-map.sh"
LEASE_SHIM="$CAIRN_REPO_ROOT/cairn/capability/scripts/cairn-lease.sh"
LEASE_DIRECT="$CAIRN_REPO_ROOT/cairn/scripts/cairn-lease.sh"

# The closed 12-point vocabulary from docs/reference/capability-manifest.md.
VALID_POINTS="discuss:pre discuss:post plan:pre plan:post execute:pre execute:wave:pre execute:wave:post execute:post verify:pre verify:post ship:pre ship:post"

# Assert NEEDLE appears in "$output".
assert_output_contains() {
  if ! printf '%s\n' "$output" | grep -qF -- "$1"; then
    echo "expected output to contain '$1', got:" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}

# Locate gsd-core's runnable capability validator, or return 1.
# Probe order: $GSD_CORE_DIR (repo checkout or package layout), then the
# lib/ directory next to an installed gsd_run launcher.
find_gsd_validator() {
  local cand dirs=()
  [ -n "${GSD_CORE_DIR:-}" ] && dirs+=(
    "$GSD_CORE_DIR/gsd-core/bin/lib/capability-validator.cjs"
    "$GSD_CORE_DIR/bin/lib/capability-validator.cjs"
  )
  if command -v gsd_run >/dev/null 2>&1; then
    dirs+=("$(dirname "$(command -v gsd_run)")/lib/capability-validator.cjs")
  fi
  for cand in "${dirs[@]:-}"; do
    if [ -n "$cand" ] && [ -f "$cand" ]; then
      printf '%s\n' "$cand"
      return 0
    fi
  done
  return 1
}

# ─── Manifest envelope ────────────────────────────────────────────────────────

@test "capability.json is valid JSON with the required feature envelope" {
  [ -f "$CAP_JSON" ]
  jq empty "$CAP_JSON"

  [ "$(jq -r '.id' "$CAP_JSON")" = "cairn" ]
  [ "$(jq -r '.role' "$CAP_JSON")" = "feature" ]

  # id must not use a reserved first-party prefix (gsd-, gsd-core-, anthropic-)
  run jq -r '.id' "$CAP_JSON"
  if printf '%s\n' "$output" | grep -qE '^(gsd-|gsd-core-|anthropic-)'; then
    echo "id uses a reserved first-party prefix: $output" >&2
    return 1
  fi

  # semver version
  run jq -r '.version' "$CAP_JSON"
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'

  # non-empty title/description, valid tier, requires array
  [ -n "$(jq -r '.title' "$CAP_JSON")" ]
  [ "$(jq -r '.title == ""' "$CAP_JSON")" = "false" ]
  [ "$(jq -r '.description == ""' "$CAP_JSON")" = "false" ]
  jq -e '.tier == "core" or .tier == "standard" or .tier == "full"' "$CAP_JSON"
  jq -e '.requires | type == "array"' "$CAP_JSON"

  # engines.gsd present (hard install/load gate)
  jq -e '.engines.gsd | type == "string" and length > 0' "$CAP_JSON"

  # runtimeCompat required for role:feature — supported non-empty
  jq -e '.runtimeCompat.supported | type == "array" and length > 0' "$CAP_JSON"
  jq -e '.runtimeCompat.unsupported | type == "array"' "$CAP_JSON"

  # feature body arrays all present
  jq -e '.skills | type == "array"' "$CAP_JSON"
  jq -e '.agents | type == "array"' "$CAP_JSON"
  jq -e '.hooks | type == "array"' "$CAP_JSON"
  jq -e '.steps | type == "array"' "$CAP_JSON"
  jq -e '.contributions | type == "array"' "$CAP_JSON"
  jq -e '.gates | type == "array"' "$CAP_JSON"
}

@test "config slice declares cairn.enabled, and NOT a key nothing reads" {
  jq -e '.config["cairn.enabled"].type == "boolean"' "$CAP_JSON"
  jq -e '.config["cairn.enabled"].default == true' "$CAP_JSON"

  # CairnGo-gbu / criterion 7. `cairn.sync_push` was declared here, documented
  # in three prompt fragments, and asserted by this very test — and read by NO
  # executable code: the push after a bd lifecycle write is decided solely by
  # the existence of .cairn/sync.json with an enabled backend
  # (cairn/hooks/post-bd-write.sh:126-152).
  #
  # DECIDED by Felipe on 2026-08-06 (D-04): delete the declaration, do not
  # implement the read. Implementing it would change behaviour for everyone
  # who already has a sync.json, and no default rescues that — `true` makes
  # the key mean nothing, `false` breaks pushes in silence. After the removal
  # the behaviour is byte for byte today's, and one button that wrote a value
  # the hook ignores is gone.
  #
  # This assertion is the inverse of the one it replaces, on purpose: a
  # declaration is a promise, and the way this one came back would be somebody
  # re-adding it here.
  jq -e '.config | has("cairn.sync_push") | not' "$CAP_JSON"

  # And the general rule behind it: every declared config key must be one a
  # reader can be named for. The set is small enough to assert whole.
  [ "$(jq -r '.config | keys | join(",")' "$CAP_JSON")" = "cairn.enabled" ]

  # activationKey, when present, must be a declared config key
  if [ "$(jq -r 'has("activationKey")' "$CAP_JSON")" = "true" ]; then
    key="$(jq -r '.activationKey' "$CAP_JSON")"
    jq -e --arg k "$key" '.config | has($k)' "$CAP_JSON"
  fi
}

@test "no prompt fragment gates the mirror push on a key nothing reads" {
  # The other half of CairnGo-gbu: three fragments told the agent to push
  # "if .cairn/sync.json has an enabled backend and config cairn.sync_push is
  # not false". The second clause was never readable by anything, so the
  # instruction described a condition that could not be evaluated.
  local f
  for f in "$CAP_DIR"/fragments/*.md; do
    if grep -qF "sync_push" "$f"; then
      echo "fragment still names the removed key: $f" >&2
      grep -nF "sync_push" "$f" >&2
      return 1
    fi
  done

  # The condition that DOES decide the push is still stated, so removing the
  # dead clause did not remove the rule.
  grep -qF ".cairn/sync.json" "$CAP_DIR/fragments/execute-wave-post.md"
}

@test "every hook point is in the closed 12-point vocabulary and every when-key is declared" {
  while IFS= read -r point; do
    if ! printf '%s\n' $VALID_POINTS | grep -qxF -- "$point"; then
      echo "invalid loop point: '$point'" >&2
      return 1
    fi
  done < <(jq -r '(.steps[].point, .contributions[].point, .gates[].point)' "$CAP_JSON")

  while IFS= read -r when; do
    jq -e --arg k "$when" '.config | has($k)' "$CAP_JSON" >/dev/null || {
      echo "when-key '$when' is not a declared config key" >&2
      return 1
    }
  done < <(jq -r '(.steps[], .contributions[], .gates[]) | select(has("when")) | .when' "$CAP_JSON")

  # onError must be skip|halt everywhere it is required
  while IFS= read -r oe; do
    [ "$oe" = "skip" ] || [ "$oe" = "halt" ] || {
      echo "invalid onError: '$oe'" >&2
      return 1
    }
  done < <(jq -r '(.steps[].onError, .gates[].onError, (.contributions[] | select(has("onError")) | .onError))' "$CAP_JSON")
}

@test "every referenced fragment and step path exists inside the bundle" {
  while IFS= read -r frag; do
    [ -f "$CAP_DIR/$frag" ] || {
      echo "fragment path '$frag' does not exist under cairn/capability/" >&2
      return 1
    }
    case "$frag" in
      /*|*..*) echo "fragment path '$frag' must be relative with no '..'" >&2; return 1 ;;
    esac
  done < <(jq -r '(.contributions[], .steps[]) | select(.fragment.path?) | .fragment.path' "$CAP_JSON")

  # every step ref must target something this capability declares
  while IFS= read -r stem; do
    jq -e --arg s "$stem" '.skills | index($s)' "$CAP_JSON" >/dev/null || {
      echo "step ref.skill '$stem' is not in the skills array" >&2
      return 1
    }
  done < <(jq -r '.steps[].ref.skill? // empty' "$CAP_JSON")
  while IFS= read -r stem; do
    jq -e --arg s "$stem" '.agents | index($s)' "$CAP_JSON" >/dev/null || {
      echo "step ref.agent '$stem' is not in the agents array" >&2
      return 1
    }
  done < <(jq -r '.steps[].ref.agent? // empty' "$CAP_JSON")
}

@test "ship gate is blocking, deterministic, and its script ships in the bundle" {
  [ "$(jq -r '.gates | length' "$CAP_JSON")" -eq 1 ]
  jq -e '.gates[0].point == "ship:pre"' "$CAP_JSON"
  jq -e '.gates[0].blocking == true' "$CAP_JSON"

  # exactly one check form, and it must be deterministic (agentVerdict is
  # forced advisory by the registry, so a blocking gate can never use it).
  # A named `query` check only routes first-party ids through
  # check-command-router, so the third-party deterministic form is a
  # command-exit-zero predicate running the bundled script.
  [ "$(jq -r '.gates[0].check | keys | length' "$CAP_JSON")" -eq 1 ]
  jq -e '.gates[0].check | has("agentVerdict") | not' "$CAP_JSON"
  jq -e '.gates[0].check.predicate.kind == "command-exit-zero"' "$CAP_JSON"
  run jq -r '.gates[0].check.predicate.command' "$CAP_JSON"
  assert_output_contains ".gsd/capabilities/cairn/scripts/cairn-loop-gate.sh"
  assert_output_contains "ship-gate"

  # the script the gate command targets exists and is executable
  [ -x "$GATE_SH" ]
  [ -x "$CAP_DIR/scripts/cairn-loop-gate.py" ]
  [ -x "$MAP_SHIM" ]
}

# The skip below is for local runs without a gsd-core checkout. CI must never
# take it: a validator that quietly skips is how a manifest breaks unnoticed.
# CI sets CAIRN_REQUIRE_GSD_VALIDATOR=1, which turns every skip into a failure.
require_or_skip() {
  if [ -n "${CAIRN_REQUIRE_GSD_VALIDATOR:-}" ]; then
    echo "CAIRN_REQUIRE_GSD_VALIDATOR is set but $1" >&2
    return 1
  fi
  skip "$1"
}

@test "gsd-core validateCapability accepts the manifest (required in CI, skipped locally without a checkout)" {
  command -v node >/dev/null 2>&1 || require_or_skip "node is not on PATH"
  VALIDATOR="$(find_gsd_validator)" || \
    require_or_skip "gsd-core validator not found — set GSD_CORE_DIR to a gsd checkout to enable"
  run node -e '
    const v = require(process.argv[1]);
    const cap = require(process.argv[2]);
    let errs = v.validateCapability(cap, "cairn");
    if (typeof v.validateAgainstContract === "function") {
      errs = errs.concat(v.validateAgainstContract(cap, "cairn"));
    }
    if (errs.length) { console.error(errs.join("\n")); process.exit(1); }
    console.log("VALID");
  ' "$VALIDATOR" "$CAP_JSON"
  [ "$status" -eq 0 ]
  assert_output_contains "VALID"
}

# ─── Bundled script contracts ────────────────────────────────────────────────

@test "ship-gate no-ops silently without .beads/" {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  run bash "$GATE_SH" ship-gate
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "ship-gate and map shim no-op silently when cairn.enabled=false" {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  mkdir .beads   # fake beads presence — the enabled gate fires before bd runs
  echo '{"cairn": {"enabled": false}}' > .planning/config.json

  run bash "$GATE_SH" ship-gate
  [ "$status" -eq 0 ]
  [ -z "$output" ]

  run bash "$GATE_SH" verify-cross 1
  [ "$status" -eq 0 ]
  [ -z "$output" ]

  run bash "$MAP_SHIM" 1
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "ship-gate blocks on a non-closed issue in a completed phase, passes after close" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # ROADMAP: phase 1 is [x], phase 2 is [ ]
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  GATE_ISSUE="$(bd create "AUTH-01: signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"

  run bash "$GATE_SH" ship-gate
  [ "$status" -eq 1 ]
  assert_output_contains "BLOCKED"
  assert_output_contains "$GATE_ISSUE"

  bd close "$GATE_ISSUE" --reason "done in tests" >/dev/null
  run bash "$GATE_SH" ship-gate
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "ship-gate --phase includes the shipped phase even when unchecked in ROADMAP" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  PH2_ISSUE="$(bd create "API-01: rate limiting" -t task -l phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-01","phase":2,"milestone":"v1.0"}}' --silent)"

  # phase 2 is [ ] in ROADMAP, so without --phase the gate passes...
  run bash "$GATE_SH" ship-gate
  [ "$status" -eq 0 ]

  # ...but shipping phase 2 explicitly must block on its open issue
  run bash "$GATE_SH" ship-gate --phase 2
  [ "$status" -eq 1 ]
  assert_output_contains "$PH2_ISSUE"
}

#-----------------------------------------------------------------------------
# roadmap-complete-but-nothing-built (CORR-05 / D-10) — additive, independent
# of what bd says. Twin of the cairn-gate.py coverage in cairn-gate.bats.
#-----------------------------------------------------------------------------

@test "ship-gate blocks a completed phase with no directory on disk at all, even with zero bd issues" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # ROADMAP: phase 1 is [x]
  bd init -q --prefix noart --non-interactive >/dev/null 2>&1   # zero issues
  rm -rf .planning/phases/01-auth

  run bash "$GATE_SH" ship-gate
  [ "$status" -eq 1 ]
  assert_output_contains "phase 1"
  assert_output_contains "no artifacts on disk"
}

@test "ship-gate blocks a completed phase whose disk holds only a bare PLAN.md (planned, never executed)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 ships SUMMARY + VERIFICATION by default
  bd init -q --prefix noart --non-interactive >/dev/null 2>&1   # zero issues
  rm -f .planning/phases/01-auth/01-01-SUMMARY.md \
        .planning/phases/01-auth/01-VERIFICATION.md

  run bash "$GATE_SH" ship-gate
  [ "$status" -eq 1 ]
  assert_output_contains "no artifacts on disk"
}

@test "ship-gate passes a completed phase with VERIFICATION.md on disk and zero bd issues (unchanged by this check)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 already ships a VERIFICATION.md
  bd init -q --prefix noart --non-interactive >/dev/null 2>&1   # zero issues

  run bash "$GATE_SH" ship-gate
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "cross-script lockstep (D-10): cairn-gate.sh and cairn-loop-gate.sh ship-gate both block on the same no-artifacts repo state" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # ROADMAP: phase 1 is [x]
  bd init -q --prefix lock --non-interactive >/dev/null 2>&1   # zero issues
  rm -rf .planning/phases/01-auth

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  local gate_status="$status"

  run bash "$GATE_SH" ship-gate
  local loop_gate_status="$status"

  # D-10's concrete lockstep proof: a phase the ROADMAP marks complete with
  # nothing built on disk blocks BOTH ship-gate entry points on the identical
  # repo state — never one twin passing while the other blocks.
  [ "$gate_status" -ne 0 ]
  [ "$loop_gate_status" -ne 0 ]
}

@test "verify-cross reports MISMATCH for open issues against a passed VERIFICATION, OK after close" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 ships a VERIFICATION with status: passed
  bd init -q --prefix vfy --non-interactive >/dev/null 2>&1
  VFY_ISSUE="$(bd create "AUTH-02: login flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-02","phase":1,"milestone":"v1.0"}}' --silent)"

  run bash "$GATE_SH" verify-cross 1
  [ "$status" -eq 0 ]
  assert_output_contains "MISMATCH"
  assert_output_contains "$VFY_ISSUE"

  bd close "$VFY_ISSUE" --reason "done in tests" >/dev/null
  run bash "$GATE_SH" verify-cross 1
  [ "$status" -eq 0 ]
  assert_output_contains "OK"
}

@test "bundle map shim resolves the dev-checkout generator and writes the phase map" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix shim --non-interactive >/dev/null 2>&1
  bd create "AUTH-01: signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent >/dev/null

  run bash "$MAP_SHIM" 1
  [ "$status" -eq 0 ]
  [ -f ".planning/phases/01-auth/01-BEADS-MAP.md" ]
  grep -qF "AUTH-01" ".planning/phases/01-auth/01-BEADS-MAP.md"
}

@test "bundle map shim honors the .cairn/plugin-root pointer from an installed layout" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix ptr --non-interactive >/dev/null 2>&1
  bd create "AUTH-01: signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent >/dev/null

  # Simulate `gsd capability install --scope project`: copy the bundle to
  # .gsd/capabilities/cairn/ (no plugin sources nearby) + pointer file.
  mkdir -p .gsd/capabilities
  cp -R "$CAP_DIR" .gsd/capabilities/cairn
  mkdir -p .cairn
  printf '%s\n' "$CAIRN_REPO_ROOT/cairn" > .cairn/plugin-root

  # Neutralize env fallbacks so only the pointer file can resolve the root
  # (the dev-relative fallback lands on the tmp repo root, which has no
  # scripts/cairn-map.py).
  run env CAIRN_PLUGIN_ROOT= CLAUDE_PLUGIN_ROOT= \
    bash ".gsd/capabilities/cairn/scripts/cairn-map.sh" 1
  [ "$status" -eq 0 ]
  [ -f ".planning/phases/01-auth/01-BEADS-MAP.md" ]
}

# ─── Lease bundle shim (15-02) ────────────────────────────────────────────────
# Mirrors the MAP_SHIM tests above, adapted to exercise acquire/status
# instead of a map refresh — the exact "outside a /cairn:*-initiated session"
# scenario (CLAUDE_PLUGIN_ROOT pointing at gsd-core, not cairn, during a bare
# /gsd:* run) this bundle shim exists to survive.

@test "bundle lease shim resolves the dev-checkout generator and delegates identically to the direct script" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lseshim --non-interactive >/dev/null 2>&1

  run bash "$LEASE_SHIM" acquire 15 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local shim_holder
  shim_holder="$(jq -r '.holder' <<<"$output")"
  [ -n "$shim_holder" ]
  [ "$shim_holder" != "null" ]

  # Confirm via the direct (Plan 15-01) script that the shim's write really
  # landed, and that both report the identical holder.
  run bash "$LEASE_DIRECT" status 15 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'true'
  assert_json_eq "$output" '.holder' "$shim_holder"
}

@test "bundle lease shim honors the .cairn/plugin-root pointer from an installed layout, outside a /cairn:*-initiated session" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lseptr --non-interactive >/dev/null 2>&1

  # Simulate `gsd capability install --scope project`: copy the bundle to
  # .gsd/capabilities/cairn/ (no plugin sources nearby) + pointer file.
  mkdir -p .gsd/capabilities
  cp -R "$CAP_DIR" .gsd/capabilities/cairn
  mkdir -p .cairn
  printf '%s\n' "$CAIRN_REPO_ROOT/cairn" > .cairn/plugin-root

  # Neutralize env fallbacks so only the pointer file can resolve the root —
  # this IS the "outside a /cairn:*-initiated session" scenario: a bare
  # /gsd:* run leaves CLAUDE_PLUGIN_ROOT pointing at gsd-core's own plugin
  # root, not cairn's, so only .cairn/plugin-root can resolve correctly.
  run env CAIRN_PLUGIN_ROOT= CLAUDE_PLUGIN_ROOT= \
    bash ".gsd/capabilities/cairn/scripts/cairn-lease.sh" acquire 15 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'true'

  # Prove the underlying bd write actually landed — not merely "exit 0" —
  # via a follow-up status call through the same copied shim.
  run env CAIRN_PLUGIN_ROOT= CLAUDE_PLUGIN_ROOT= \
    bash ".gsd/capabilities/cairn/scripts/cairn-lease.sh" status 15 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'true'
}

@test "bundle lease shim warns and exits 0 when no resolution tier finds cairn-lease.py" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lsedeg --non-interactive >/dev/null 2>&1

  # Copy the bundle with no plugin sources nearby and no .cairn/plugin-root
  # pointer — the dev-checkout fallback (bundle/../..) also lands short of
  # any scripts/cairn-lease.py reachable from this copied location.
  mkdir -p .gsd/capabilities
  cp -R "$CAP_DIR" .gsd/capabilities/cairn

  run env CAIRN_PLUGIN_ROOT= CLAUDE_PLUGIN_ROOT= \
    bash ".gsd/capabilities/cairn/scripts/cairn-lease.sh" status 15 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_output_contains "could not locate"
  assert_output_contains "cairn-lease.py"
}
