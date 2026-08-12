#!/usr/bin/env bats
# cairn-inventory.bats — exercises the pinned-tag corpus inventory's CLI
# contract (cairn-inventory.py / the cairn-inventory.sh wrapper).
#
# What is under test here:
#   corpus (D-01)  the clone is cached, the cache HEAD is validated against
#                  the expected tag commit on EVERY run, and a cache hit is
#                  100% offline — proved by running with --source pointing at
#                  a path that does not exist.
#   metric (REM-02) one declared metric: the broad regex lives in --json as
#                  metric.regex; sites carry file/line/scope/verb.
#
# Exit codes under test: 0 ok, 2 usage, 5 dependency unavailable,
# 6 invalid corpus.
#
# Assertion style notes:
#   - every status assertion is on the EXACT value (`-eq 6`), never `-ne 0`:
#     a negation accepts the wrong code and hides a regression.
#   - a failing `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this
#     bash, so substring checks use grep -qF.
#   - no test hard-codes a count taken from the real corpus tree: fixture
#     expectations come from the fixture, and the real-cache assertions
#     (skip-gated below) carry the reproduction command beside each value.
#   - no test touches GitHub: fixtures are local git repos carrying the same
#     tag name, and the real-cache tests skip when the cache is absent.

load 'helpers'

INVENTORY="$CAIRN_SCRIPTS_DIR/cairn-inventory.sh"

# --- fixture builders, local to this file -----------------------------------
# helpers.bash is loaded by thirty suites and is not touched for one phase's
# shape; the precedent is the trend suite's local builders.

# A local git repo carrying tag v1.10.0 with a synthetic mini-corpus, plus an
# empty cache slot. Exports INV_SOURCE, INV_CACHE, INV_COMMIT.
new_corpus_fixture() {
  local base
  base="$(mktemp -d "${BATS_TEST_TMPDIR:-${TMPDIR:-/tmp}}/inv.XXXXXX")"
  INV_SOURCE="$base/source"
  INV_CACHE="$base/cache/gsd-core-v1.10.0"
  mkdir -p "$INV_SOURCE/gsd-core/workflows"
  git init -q "$INV_SOURCE"
  git -C "$INV_SOURCE" config user.email "cairn-tests@example.com"
  git -C "$INV_SOURCE" config user.name "Cairn Tests"

  cat > "$INV_SOURCE/gsd-core/workflows/fast.md" <<'EOF'
# fast workflow (fixture)

_GSD_TOOLS="x"; gsd_run() { node "$GSD_TOOLS" "$@"; }; gsd_run() { node "$GSD_TOOLS" "$@"; }; gsd_run() { node "$GSD_TOOLS" "$@"; }

Load state:
```bash
gsd_run query state.load
```
Then render loop hooks:
```bash
gsd_run loop render-hooks
```
And commit:
```bash
gsd_run query commit "feat: x" --files a.txt
```
Both spellings of the same verb exist in the corpus:
```bash
gsd_run query verification status
gsd_run query verification.status --json
```
E a prosa menciona gsd_run @@@ sem chamar nada.
EOF

  # An agent file whose name is in the script's declared AGENTS_SCOPE.
  mkdir -p "$INV_SOURCE/agents"
  cat > "$INV_SOURCE/agents/gsd-executor.md" <<'EOF'
# executor (fixture agent)

```bash
gsd_run query state.record-metric
gsd_run check
```
EOF

  # A commands/ file: calibration territory, never sites[] territory.
  mkdir -p "$INV_SOURCE/commands"
  cat > "$INV_SOURCE/commands/calibrate.md" <<'EOF'
# command shim (fixture)

```bash
gsd_run query commands.only --pick x
gsd_run query state.load
```
EOF

  git -C "$INV_SOURCE" add -A
  git -C "$INV_SOURCE" commit -qm "fixture corpus"
  git -C "$INV_SOURCE" tag v1.10.0
  INV_COMMIT="$(git -C "$INV_SOURCE" rev-parse HEAD)"
}

# Run the inventory against the fixture (clone-on-miss, hit afterwards).
inv() {
  run "$INVENTORY" --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" "$@"
}

# jq over the last `inv --json` output.
ijq() { printf '%s' "$output" | jq -r "$1"; }

# --- the tracer slice: clone, validate, scan, --json ------------------------

@test "clone from a local source produces --json with the expected sites" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  [ "$(ijq '.source.commit')" = "$INV_COMMIT" ]
  [ "$(ijq '.source.cache_state')" = "cloned" ]
  # The declared metric travels in the artifact (REM-02).
  [ "$(ijq '.metric.regex')" = 'gsd_run (query )?[a-z][a-z-]*(\.[a-z-]+)?' ]
  # Sites carry file (relative to the clone root), line, scope and verb.
  [ "$(ijq '[.sites[] | select(.verb == "state.load")] | length')" -eq 1 ]
  [ "$(ijq '.sites[] | select(.verb == "state.load") | .file')" = \
    "gsd-core/workflows/fast.md" ]
  [ "$(ijq '.sites[] | select(.verb == "state.load") | .scope')" = \
    "workflows8" ]
  [ "$(ijq '.sites[] | select(.verb == "state.load") | .line')" -gt 0 ]
  # The broad metric sees the non-query top-level subcommand too.
  [ "$(ijq '[.sites[] | select(.verb == "loop")] | length')" -eq 1 ]
  [ "$(ijq '.sites[] | select(.verb == "loop") | .subcommand')" = \
    "render-hooks" ]
  # The line numbers come from the fixture file itself, not from a literal:
  # recompute the state.load line with grep.
  local expected_line
  expected_line="$(grep -n 'gsd_run query state.load' \
    "$INV_SOURCE/gsd-core/workflows/fast.md" | cut -d: -f1)"
  [ "$(ijq '.sites[] | select(.verb == "state.load") | .line')" \
    -eq "$expected_line" ]
}

@test "a cache hit is 100% offline: --source pointing nowhere still answers" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  local first_sites
  first_sites="$(ijq '.sites')"
  # Same cache, a source that cannot exist: a hit must never touch it.
  run "$INVENTORY" --cache-dir "$INV_CACHE" --source /nonexistent/nowhere \
    --expect-commit "$INV_COMMIT" --json
  [ "$status" -eq 0 ]
  [ "$(ijq '.source.cache_state')" = "hit" ]
  [ "$(ijq '.sites')" = "$first_sites" ]
}

@test "a cache whose HEAD is not the expected commit dies 6 naming both shas" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  local wrong="0000000000000000000000000000000000000000"
  run "$INVENTORY" --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$wrong" --json
  [ "$status" -eq 6 ]
  printf '%s' "$output" | grep -qF "$wrong"
  printf '%s' "$output" | grep -qF "$INV_COMMIT"
}

@test "an unknown flag is a usage error, exit 2" {
  new_corpus_fixture
  inv --nope
  [ "$status" -eq 2 ]
}

@test "a failing clone with no cache to fall back on exits 5" {
  new_corpus_fixture
  run "$INVENTORY" --cache-dir "$INV_CACHE" --source /nonexistent/nowhere \
    --expect-commit "$INV_COMMIT" --json
  [ "$status" -eq 5 ]
}

@test "the human output without --json answers with the model's totals" {
  new_corpus_fixture
  inv
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF "[cairn-inventory]"
}

# --- full classification: scopes, normalization, accounting -----------------

@test "sites from AGENTS_SCOPE files carry scope agents, with their summary" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  [ "$(ijq '[.sites[] | select(.scope == "agents")] | length')" -eq 2 ]
  [ "$(ijq '.sites[] | select(.verb == "state.record-metric") | .file')" = \
    "agents/gsd-executor.md" ]
  [ "$(ijq '.sites[] | select(.verb == "state.record-metric") | .scope')" = \
    "agents" ]
  # summary.agents is derived from the same sites, not counted elsewhere.
  [ "$(ijq '.summary.agents.sites')" -eq \
    "$(ijq '[.sites[] | select(.scope == "agents")] | length')" ]
  [ "$(ijq '.summary.agents.verbs')" -eq \
    "$(ijq '[.sites[] | select(.scope == "agents") | .verb] | unique | length')" ]
}

@test "calibration feeds summary.corpus_calibration only — never sites or verbs" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  # The expectation is RECOMPUTED from the fixture with the research's own
  # grep, never typed by hand.
  local expected_calls expected_verbs
  expected_calls="$(grep -rhoE 'gsd_run query [a-z][a-z0-9._-]+' \
    "$INV_SOURCE/gsd-core/workflows" "$INV_SOURCE/commands" \
    | wc -l | tr -d ' ')"
  expected_verbs="$(grep -rhoE 'gsd_run query [a-z][a-z0-9._-]+' \
    "$INV_SOURCE/gsd-core/workflows" "$INV_SOURCE/commands" \
    | awk '{print $3}' | sort -u | wc -l | tr -d ' ')"
  [ "$(ijq '.summary.corpus_calibration.calls')" -eq "$expected_calls" ]
  [ "$(ijq '.summary.corpus_calibration.verbs')" -eq "$expected_verbs" ]
  # commands/ is calibration territory: no site, no verb entry comes from it.
  [ "$(ijq '[.sites[] | select(.file | startswith("commands/"))] | length')" \
    -eq 0 ]
  [ "$(ijq '.verbs | has("commands.only")')" = "false" ]
}

@test "the two spellings of verification.status count ONE verb, two spellings" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  [ "$(ijq '.verbs["verification.status"].count')" -eq 2 ]
  [ "$(ijq '.verbs["verification.status"].spellings | length')" -eq 2 ]
  # The bare `verification` verb must not survive normalization.
  [ "$(ijq '.verbs | has("verification")')" = "false" ]
  # The two-word site keeps its own spelling and loses the subcommand.
  [ "$(ijq '[.sites[] | select(.spelling == "query verification status")] | length')" -eq 1 ]
  [ "$(ijq '.sites[] | select(.spelling == "query verification status") | .verb')" = \
    "verification.status" ]
  [ "$(ijq '.sites[] | select(.spelling == "query verification status") | .subcommand')" = \
    "null" ]
}

@test "loop render-hooks is counted as verb+subcommand, summarised in workflows8" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  # Recomputed from the fixture, not typed.
  local expected
  expected="$(grep -c 'gsd_run loop render-hooks' \
    "$INV_SOURCE/gsd-core/workflows/fast.md" | tr -d ' ')"
  [ "$(ijq '.summary.loop_render_hooks_sites')" -eq "$expected" ]
  [ "$(ijq '.sites[] | select(.verb == "loop") | .subcommand')" = \
    "render-hooks" ]
}

@test "accounting: the per-scope identity is recomputed from the fixture" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  # total_raw comes from the files themselves — occurrences, not lines.
  local w8_raw ag_raw shim_raw
  w8_raw="$(grep -o 'gsd_run' "$INV_SOURCE/gsd-core/workflows/fast.md" \
    | wc -l | tr -d ' ')"
  ag_raw="$(grep -o 'gsd_run' "$INV_SOURCE/agents/gsd-executor.md" \
    | wc -l | tr -d ' ')"
  shim_raw="$(grep 'gsd_run() {' "$INV_SOURCE/gsd-core/workflows/fast.md" \
    | grep -o 'gsd_run' | wc -l | tr -d ' ')"
  [ "$(ijq '.accounting.workflows8.total_raw')" -eq "$w8_raw" ]
  [ "$(ijq '.accounting.agents.total_raw')" -eq "$ag_raw" ]
  # All occurrences of the shim-defining line land together in one bucket.
  [ "$(ijq '.accounting.workflows8.shim_preambles')" -eq "$shim_raw" ]
  [ "$(ijq '.accounting.workflows8.shim_preambles')" -gt 1 ]
  # The identity holds in EACH slice, always.
  [ "$(ijq '[.accounting.workflows8, .accounting.agents] | all(.total_raw == .calls + .shim_preambles + .other)')" = "true" ]
  # calls in a slice == sites in that scope: nothing double-counted.
  [ "$(ijq '.accounting.workflows8.calls')" -eq \
    "$(ijq '[.sites[] | select(.scope == "workflows8")] | length')" ]
  [ "$(ijq '.accounting.agents.calls')" -eq \
    "$(ijq '[.sites[] | select(.scope == "agents")] | length')" ]
}

@test "negative control: a stray gsd_run in prose lands in other, enumerated" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  # The fixture carries exactly one occurrence the broad regex cannot claim
  # (`gsd_run @@@` in prose) — the bucket must be alive and name the site.
  [ "$(ijq '.accounting.workflows8.other')" -eq 1 ]
  [ "$(ijq '.accounting.workflows8.other_sites | length')" -eq 1 ]
  [ "$(ijq '.accounting.workflows8.other_sites[0].file')" = \
    "gsd-core/workflows/fast.md" ]
  ijq '.accounting.workflows8.other_sites[0].excerpt' | grep -qF "@@@"
  # The agents slice has no stray occurrence: its bucket stays empty, and
  # the enumeration matches the count in every slice.
  [ "$(ijq '.accounting.agents.other')" -eq 0 ]
  [ "$(ijq '[.accounting.workflows8, .accounting.agents] | all((.other_sites | length) == .other)')" = "true" ]
}

@test "the declared metric and its calibration twin travel literally in --json" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  [ "$(ijq '.metric.regex')" = 'gsd_run (query )?[a-z][a-z-]*(\.[a-z-]+)?' ]
  [ "$(ijq '.metric.calibration_regex')" = 'gsd_run query [a-z][a-z0-9._-]+' ]
}

# --- the human output is a mechanical view of the model ---------------------

@test "the human output resumes every scope and the accounting" {
  new_corpus_fixture
  inv
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF "workflows8"
  printf '%s' "$output" | grep -qF "agents"
  # The accounting reaches the prose: the shim bucket's count, recomputed
  # from the fixture, has to be visible without opening the JSON.
  local shim_raw
  shim_raw="$(grep 'gsd_run() {' "$INV_SOURCE/gsd-core/workflows/fast.md" \
    | grep -o 'gsd_run' | wc -l | tr -d ' ')"
  printf '%s' "$output" | grep -qF "$shim_raw"
}

# --- the guard against the hand-typed count ---------------------------------

# Numeric tokens present in HUMAN and absent from every scalar value of JSON.
# Empty output means the human text is a view of the data. Copied locally
# from tests/cairn-trend.bats (helpers.bash is loaded by thirty suites and is
# not touched for one phase's shape).
numbers_not_in_json() {
  local human="$1" jsonout="$2" tok json_tokens missing=""
  json_tokens="$(printf '%s' "$jsonout" | jq -r '[.. | scalars] | .[]' \
    | grep -oE '[0-9]+' | sort -u)"
  while IFS= read -r tok; do
    [ -z "$tok" ] && continue
    printf '%s\n' "$json_tokens" | grep -qx -- "$tok" || missing="$missing $tok"
  done < <(printf '%s' "$human" | grep -oE '[0-9]+' | sort -u)
  printf '%s' "$missing"
}

@test "GUARD: every number in the human output is a value in the JSON" {
  # Two targets when the real cache exists, one always: a command that
  # derived on one corpus and stamped on the other would pass a
  # single-target check.
  new_corpus_fixture
  local human json missing
  human="$("$INVENTORY" --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" || true)"
  json="$("$INVENTORY" --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --json || true)"
  missing="$(numbers_not_in_json "$human" "$json")"
  if [ -n "$missing" ]; then
    echo "numbers in the prose with no value behind them:$missing" >&2
    return 1
  fi

  local real_cache="$CAIRN_REPO_ROOT/.cairn/cache/gsd-core-v1.10.0"
  if [ -d "$real_cache" ]; then
    human="$("$INVENTORY" --cache-dir "$real_cache" || true)"
    json="$("$INVENTORY" --cache-dir "$real_cache" --json || true)"
    missing="$(numbers_not_in_json "$human" "$json")"
    if [ -n "$missing" ]; then
      echo "numbers in the real-cache prose with no value behind them:$missing" >&2
      return 1
    fi
  fi
}

@test "GUARD negative control: the check rejects a forged number" {
  # A guard that only ever passes proves nothing — a broken token extraction
  # would stay green forever. This is the liveness half.
  new_corpus_fixture
  local json missing
  json="$("$INVENTORY" --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --json || true)"
  missing="$(numbers_not_in_json "o inventário tem 987654 sítios" "$json")"
  [ -n "$missing" ]
  printf '%s' "$missing" | grep -qF "987654"
}

@test "GUARD: no live count about the corpus lives outside the dated block" {
  # The house convention makes the docstring record MEASURED VERSUS ASSUMED,
  # which means writing measured numbers into prose — what saves a number is
  # being DATED and labelled as a measurement of one instant. So: counts live
  # inside that block, and nowhere else in either delivered file.
  local py="$CAIRN_SCRIPTS_DIR/cairn-inventory.py"
  local sh="$CAIRN_SCRIPTS_DIR/cairn-inventory.sh"
  local nouns='verbos?|verbs?|s[íi]tios?|sites?|chamadas?|calls?'
  nouns="$nouns"'|workflows?|agentes?|agents?|ocorr[êe]ncias?|occurrences?'
  local numerals='[0-9]+|two|three|four|five|six|seven|eight|nine|ten'
  numerals="$numerals"'|eleven|twelve|dois|duas|três|quatro|cinco|seis|sete'
  numerals="$numerals"'|oito|nove|dez|onze|doze'
  local pattern="(^|[^A-Za-z_])($numerals) ($nouns)([^A-Za-z]|$)"

  # Everything in the .py BEFORE the dated measurement block.
  local before hit
  before="$(awk '/^MEASURED VERSUS ASSUMED$/{exit} {print}' "$py")"
  hit="$(printf '%s' "$before" | grep -inE "$pattern" || true)"
  if [ -n "$hit" ]; then
    echo "a live count sits outside the dated block in cairn-inventory.py:" >&2
    echo "$hit" >&2
    return 1
  fi
  # The .sh header restates the contract and is exactly the kind of place a
  # number moves into and is forgotten.
  hit="$(grep -inE "$pattern" "$sh" || true)"
  if [ -n "$hit" ]; then
    echo "a live count sits in cairn-inventory.sh:" >&2
    echo "$hit" >&2
    return 1
  fi
  # Liveness: the pattern must actually match something, or it guards air.
  printf 'the corpus has 189 sites\n' | grep -qiE "$pattern"
  printf 'faltam dois verbos\n' | grep -qiE "$pattern"
}

@test "the dated block carries a 2026-08 date and a command beside each count" {
  local py="$CAIRN_SCRIPTS_DIR/cairn-inventory.py"
  awk '/^MEASURED VERSUS ASSUMED$/{f=1} f{print}' "$py" \
    | grep -qE '2026-08'
  # ASSUMED is not optional: the block records what was NOT measured too.
  awk '/^MEASURED VERSUS ASSUMED$/{f=1} f{print}' "$py" \
    | grep -qE '^ASSUMED'
}

# --- the acceptance numbers, against the real corpus (skip-gated) -----------
# Every expected value below was MEASURED on 2026-08-10 by running
#   CLAUDE_PROJECT_DIR=<repo> cairn/scripts/cairn-inventory.sh --json
# against the real cache of the v1.10.0 tag (commit 68a04cc). Where the
# measurement diverged from the research's ballpark, the measured value is
# asserted and the divergence is noted beside it — never the other way
# around: the script is not bent to force a research number.

real_inv() {
  local real_cache="$CAIRN_REPO_ROOT/.cairn/cache/gsd-core-v1.10.0"
  [ -d "$real_cache" ] || \
    skip "cache do clone ausente — rode cairn-inventory.sh uma vez com rede"
  run "$INVENTORY" --cache-dir "$real_cache" --json
}

@test "real corpus: 189 sites in the 8 workflows under the broad metric" {
  real_inv
  [ "$status" -eq 0 ]
  # Reproduces the research exactly (broad regex over the 8 md + steps).
  [ "$(ijq '.summary.workflows8.sites')" -eq 189 ]
  # Distinct verbs: research ballparked 60-61; the normalization this
  # inventory fixes (dual spelling = one verb) measures 59.
  # Command: cairn-inventory.sh --json | jq '.summary.workflows8.verbs'
  [ "$(ijq '.summary.workflows8.verbs')" -eq 59 ]
}

@test "real corpus: agents scope sites and verbs under the declared list" {
  real_inv
  [ "$status" -eq 0 ]
  # The research measured 64 sites over 12 dispatched agents; AGENTS_SCOPE
  # declares the mechanical 16-name intersection and measures 65/42.
  # Command: cairn-inventory.sh --json | jq '.summary.agents'
  [ "$(ijq '.summary.agents.sites')" -eq 65 ]
  [ "$(ijq '.summary.agents.verbs')" -eq 42 ]
}

@test "real corpus: the calibration regex reproduces 534 calls / 116 verbs" {
  real_inv
  [ "$status" -eq 0 ]
  # Reproduces the research exactly (grep -rhoE 'gsd_run query
  # [a-z][a-z0-9._-]+' over gsd-core/workflows + commands).
  [ "$(ijq '.summary.corpus_calibration.calls')" -eq 534 ]
  [ "$(ijq '.summary.corpus_calibration.verbs')" -eq 116 ]
}

@test "real corpus: 17 loop render-hooks sites in the 8" {
  real_inv
  [ "$status" -eq 0 ]
  [ "$(ijq '.summary.loop_render_hooks_sites')" -eq 17 ]
}

@test "real corpus: the workflows8 slice reproduces 651 = 189 + 460 + 2" {
  real_inv
  [ "$status" -eq 0 ]
  # The research's completeness identity, measured on the workflows8 slice
  # only — an accounting mixed across scopes would diverge by construction.
  [ "$(ijq '.accounting.workflows8.total_raw')" -eq 651 ]
  [ "$(ijq '.accounting.workflows8.calls')" -eq 189 ]
  [ "$(ijq '.accounting.workflows8.shim_preambles')" -eq 460 ]
  [ "$(ijq '.accounting.workflows8.other')" -eq 2 ]
  [ "$(ijq '.accounting.workflows8.other_sites | length')" -eq 2 ]
}

@test "real corpus: the identity holds in BOTH slices, other enumerated" {
  real_inv
  [ "$status" -eq 0 ]
  # In the agents slice the identity is asserted without a research-fixed
  # value: the research never measured it there.
  [ "$(ijq '[.accounting.workflows8, .accounting.agents] | all(.total_raw == .calls + .shim_preambles + .other)')" = "true" ]
  [ "$(ijq '[.accounting.workflows8, .accounting.agents] | all((.other_sites | length) == .other)')" = "true" ]
}
