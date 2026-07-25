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

@test "config slice declares cairn.enabled and cairn.sync_push (boolean, default true)" {
  jq -e '.config["cairn.enabled"].type == "boolean"' "$CAP_JSON"
  jq -e '.config["cairn.enabled"].default == true' "$CAP_JSON"
  jq -e '.config["cairn.sync_push"].type == "boolean"' "$CAP_JSON"
  jq -e '.config["cairn.sync_push"].default == true' "$CAP_JSON"
  # activationKey, when present, must be a declared config key
  if [ "$(jq -r 'has("activationKey")' "$CAP_JSON")" = "true" ]; then
    key="$(jq -r '.activationKey' "$CAP_JSON")"
    jq -e --arg k "$key" '.config | has($k)' "$CAP_JSON"
  fi
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

@test "gsd-core validateCapability accepts the manifest (skips when gsd-core is absent)" {
  command -v node >/dev/null 2>&1 || skip "node is not on PATH"
  VALIDATOR="$(find_gsd_validator)" || \
    skip "gsd-core validator not found — set GSD_CORE_DIR to a gsd checkout to enable"
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
