#!/usr/bin/env bats
# cairn-vendoring.bats — the executable proof of the phase-32 vendoring:
# the manifest is DERIVED (closure re-run and compared, D-02), the vendored
# tree matches the pinned clone on the inclusion list in BOTH directions
# (D-01, VEND-01/VEND-03), and the cut holds — gsd-write-guard.js and the
# excluded blocks are absent by test (VEND-04). Every guard ships with its
# paired negative control: a guard that only ever passes proves nothing.
#
# PHASE 36 CHANGED WHAT "MATCHES" MEANS, and the change is the point of the
# suite rather than a concession to it. Phase 36 adapts the vendored prompt
# layer, so blanket byte-identity became false the day it landed. It was NOT
# replaced by a new baseline (that would kill the only thing this suite is
# for — proving nothing beyond the adapted paths moved). It was replaced by
# a two-sense invariant against ONE versioned registry,
# cairn/gsd-adaptations.json: every path OUTSIDE the registry is
# byte-identical to the cache, and every path INSIDE it MUST differ. A
# registered path that is byte-identical again is a FAILURE — the adaptation
# was lost to a re-vendor, a merge or a revert, and the tree is silently back
# on the dead runtime.
#
# That same two-sense set comparison is also the phase's replacement for the
# `git status --porcelain cairn/gsd/` empty gate of phases 33-35 (armadilha
# PORCELAIN): the porcelain gate is now false by design, and unlike it this
# one survives the commit.
#
# Exit codes under test: 0 ok, 2 usage / manifest missing, 5 dependency
# unavailable, 6 invalid corpus / manifest-commit mismatch / requires guard.
#
# Assertion style notes:
#   - every status assertion is on the EXACT value (`-eq 6`), never `-ne 0`:
#     a negation accepts the wrong code and hides a regression.
#   - a failing `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this
#     bash, so substring checks use grep -qF.
#   - no test hard-codes a count taken from the real corpus tree without the
#     reproduction command beside it: fixture expectations come from the
#     fixture, and the real-corpus assertions (acceptance numbers below,
#     fidelity skip-gated by the cache) each carry their command.
#   - no test touches GitHub: fixtures are local git repos carrying the same
#     tag name, and the real-cache tests skip when the cache is absent.

load 'helpers'

INVENTORY="$CAIRN_SCRIPTS_DIR/cairn-inventory.sh"

# --- fixture builders, local to this file -----------------------------------
# helpers.bash is loaded by thirty suites and is not touched for one phase's
# shape; the precedent is the inventory suite's local builders. The corpus
# builder is COPIED from cairn-inventory.bats and extended with a reference
# chain that proves the fixed point in miniature: fast.md mentions r1.md,
# r1.md mentions t1.md, t1.md mentions nothing — and orfao.md is mentioned
# by nobody.

# A local git repo carrying tag v1.10.0 with a synthetic mini-corpus, plus an
# empty cache slot. Exports INV_SOURCE, INV_CACHE, INV_COMMIT.
new_corpus_fixture() {
  local base
  base="$(mktemp -d "${BATS_TEST_TMPDIR:-${TMPDIR:-/tmp}}/vnd.XXXXXX")"
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

Read @~/.claude/gsd-core/references/r1.md before doing anything.
EOF

  # The reference chain: r1 pulls t1 (two hops from the workflow), and the
  # orphan is referenced by NOBODY — the fixed point must include the chain
  # and exclude the orphan.
  mkdir -p "$INV_SOURCE/gsd-core/references" "$INV_SOURCE/gsd-core/templates"
  cat > "$INV_SOURCE/gsd-core/references/r1.md" <<'EOF'
# r1 (fixture reference)
Depois de ler isto, aplique gsd-core/templates/t1.md ao resultado.
EOF
  cat > "$INV_SOURCE/gsd-core/templates/t1.md" <<'EOF'
# t1 (fixture template)
Nada aqui referencia mais nada.
EOF
  cat > "$INV_SOURCE/gsd-core/references/orfao.md" <<'EOF'
# orfao (fixture reference que ninguém menciona)
EOF

  # The upstream license enters through the SAME list as everything else.
  cat > "$INV_SOURCE/LICENSE" <<'EOF'
MIT License (fixture)

Copyright (c) 2026 Fixture Upstream
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

  # A commands/ file: calibration territory, never sites[] territory — and
  # NOT a shim of the 8, so the closure must leave it out.
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

# Re-tag the fixture after adding files to it (the cache slot is fresh per
# fixture, so the next run clones the amended commit).
retag_fixture() {
  git -C "$INV_SOURCE" add -A
  git -C "$INV_SOURCE" commit -qm "fixture amendment"
  git -C "$INV_SOURCE" tag -f v1.10.0
  INV_COMMIT="$(git -C "$INV_SOURCE" rev-parse HEAD)"
}

# Run the flat inventory / the subcommands against the fixture.
inv() {
  run "$INVENTORY" --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" "$@"
}
clo() {
  run "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" "$@"
}
ven() {
  run "$INVENTORY" vendor --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" "$@"
}

# jq over the last `run` output.
cjq() { printf '%s' "$output" | jq -r "$1"; }

# --- shared assertion oracles ------------------------------------------------
# Explicit roots as arguments so the negative controls can point the SAME
# loop at forged trees — the liveness half of every guard.

# Set exactness, both directions: under the tree there is NOTHING beyond
# files[] + MANIFEST.json + contracts/**, and no files[] entry is missing.
assert_tree_set_exact() {
  local manifest="$1" dest="$2"
  local tree_list manifest_list only_tree only_manifest
  tree_list="$(cd "$dest" && find . -type f | sed 's|^\./||' \
    | grep -v '^MANIFEST\.json$' | grep -v '^contracts/' | LC_ALL=C sort)"
  manifest_list="$(jq -r '.files[]' "$manifest" | LC_ALL=C sort)"
  only_tree="$(LC_ALL=C comm -23 <(printf '%s\n' "$tree_list") \
    <(printf '%s\n' "$manifest_list"))"
  only_manifest="$(LC_ALL=C comm -13 <(printf '%s\n' "$tree_list") \
    <(printf '%s\n' "$manifest_list"))"
  if [ -n "$only_tree" ] || [ -n "$only_manifest" ]; then
    printf 'tree-only files:\n%s\nmanifest-only files:\n%s\n' \
      "$only_tree" "$only_manifest" >&2
    return 1
  fi
}

# Byte fidelity, in BOTH senses — the shape assert_tree_set_exact already has
# for sets, now for bytes (phase 36, VEND-BYTES).
#
# Until phase 36 this oracle said one thing: every files[] entry is
# byte-identical to the corpus. Phase 36 is the first to WRITE under
# cairn/gsd/, so the invariant grows a fourth argument — the registry of
# declared adaptations — and splits:
#
#   OUTSIDE the registry: `cmp` must be EQUAL. Nothing drifts unannounced.
#   INSIDE  the registry: `cmp` must DIFFER. A registered path that is
#                         byte-identical again means the adaptation was LOST
#                         (a re-vendor, a merge, a revert) and the tree is
#                         quietly back on the upstream runtime.
#
# The fourth argument is optional so the fixture rounds keep their old
# meaning: no registry = empty allowlist = exactly the oracle of before.
assert_tree_bytes_match() {
  local manifest="$1" dest="$2" corpus="$3" adaptations="${4:-}" fails=0 p
  local allow=""
  if [ -n "$adaptations" ] && [ -f "$adaptations" ]; then
    allow="$(jq -r '.adaptations[].path' "$adaptations" | LC_ALL=C sort)"
  fi
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if [ ! -f "$dest/$p" ]; then
      echo "manifest entry missing under the tree: $p" >&2
      fails=$((fails + 1))
      continue
    fi
    if [ -n "$allow" ] && printf '%s\n' "$allow" | grep -qxF -- "$p"; then
      if cmp -s "$dest/$p" "$corpus/$p"; then
        echo "a adaptação registrada sumiu — o arquivo voltou ao byte do upstream: $p" >&2
        fails=$((fails + 1))
      fi
      continue
    fi
    if ! cmp -s "$dest/$p" "$corpus/$p"; then
      echo "vendored bytes diverge from the corpus: $p" >&2
      fails=$((fails + 1))
    fi
  done < <(jq -r '.files[]' "$manifest")
  [ "$fails" -eq 0 ]
}

# --- the fixed point, in miniature -------------------------------------------

@test "closure on the fixture converges to the fixed point and excludes the orphan" {
  new_corpus_fixture
  clo --json
  [ "$status" -eq 0 ]
  # Two hops from the workflow: r1 via fast.md, t1 via r1.md. Expectations
  # come from the fixture itself, never from the real tree.
  [ "$(cjq '.files | index("gsd-core/workflows/fast.md") != null')" = "true" ]
  [ "$(cjq '.files | index("gsd-core/references/r1.md") != null')" = "true" ]
  [ "$(cjq '.files | index("gsd-core/templates/t1.md") != null')" = "true" ]
  [ "$(cjq '.files | index("agents/gsd-executor.md") != null')" = "true" ]
  [ "$(cjq '.files | index("LICENSE") != null')" = "true" ]
  # The orphan is referenced by nobody and the calibrate command is not a
  # shim of the 8: both stay out.
  [ "$(cjq '.files | index("gsd-core/references/orfao.md")')" = "null" ]
  [ "$(cjq '.files | index("commands/calibrate.md")')" = "null" ]
  # files[] is sorted and totals restate the list.
  [ "$(cjq '.files == (.files | sort)')" = "true" ]
  [ "$(cjq '(.files | length) == .totals.files')" = "true" ]
  [ "$(cjq '.source.commit')" = "$INV_COMMIT" ]
}

@test "closure is deterministic: two runs emit identical bytes" {
  new_corpus_fixture
  local a="$BATS_TEST_TMPDIR/run-a.json" b="$BATS_TEST_TMPDIR/run-b.json"
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --json > "$a"
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --json > "$b"
  run diff "$a" "$b"
  [ "$status" -eq 0 ]
}

@test "closure --write emits exactly the bytes of --json, with a trailing newline" {
  new_corpus_fixture
  local m="$BATS_TEST_TMPDIR/manifest.json" live="$BATS_TEST_TMPDIR/live.json"
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --write "$m" >/dev/null
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --json > "$live"
  run diff "$m" "$live"
  [ "$status" -eq 0 ]
  [ "$(tail -c1 "$m" | od -An -c | tr -d ' ')" = '\n' ]
}

@test "written manifest vs live output: the file SETS are identical in both directions (empty diff)" {
  new_corpus_fixture
  local m="$BATS_TEST_TMPDIR/manifest.json" live="$BATS_TEST_TMPDIR/live.json"
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --write "$m" >/dev/null
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --json > "$live"
  local written_files live_files only_written only_live
  written_files="$(jq -r '.files[]' "$m" | LC_ALL=C sort)"
  live_files="$(jq -r '.files[]' "$live" | LC_ALL=C sort)"
  only_written="$(LC_ALL=C comm -23 <(printf '%s\n' "$written_files") \
    <(printf '%s\n' "$live_files"))"
  only_live="$(LC_ALL=C comm -13 <(printf '%s\n' "$written_files") \
    <(printf '%s\n' "$live_files"))"
  if [ -n "$only_written" ] || [ -n "$only_live" ]; then
    printf 'written-only files:\n%s\nlive-only files:\n%s\n' \
      "$only_written" "$only_live" >&2
    return 1
  fi
}

# --- vendor fidelity, in miniature -------------------------------------------

@test "vendor on the fixture copies exactly the list, byte-identical, nothing beyond it" {
  new_corpus_fixture
  local m="$BATS_TEST_TMPDIR/manifest.json" d="$BATS_TEST_TMPDIR/dest"
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --write "$m" >/dev/null
  ven --manifest "$m" --dest "$d"
  [ "$status" -eq 0 ]
  run assert_tree_bytes_match "$m" "$d" "$INV_CACHE" ""
  [ "$status" -eq 0 ]
  run assert_tree_set_exact "$m" "$d"
  [ "$status" -eq 0 ]
}

@test "negative control: a corrupted byte in the vendored copy is caught and named" {
  # A guard that only ever passes proves nothing — this is the liveness half
  # of the byte-fidelity oracle.
  new_corpus_fixture
  local m="$BATS_TEST_TMPDIR/manifest.json" d="$BATS_TEST_TMPDIR/dest"
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --write "$m" >/dev/null
  "$INVENTORY" vendor --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --manifest "$m" --dest "$d" >/dev/null
  printf 'X' >> "$d/gsd-core/templates/t1.md"
  run assert_tree_bytes_match "$m" "$d" "$INV_CACHE" ""
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "gsd-core/templates/t1.md"
}

@test "negative control: a file beyond the manifest under the tree is caught and named" {
  new_corpus_fixture
  local m="$BATS_TEST_TMPDIR/manifest.json" d="$BATS_TEST_TMPDIR/dest"
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --write "$m" >/dev/null
  "$INVENTORY" vendor --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --manifest "$m" --dest "$d" >/dev/null
  mkdir -p "$d/gsd-core/references"
  printf 'forjado\n' > "$d/gsd-core/references/intruso.md"
  run assert_tree_set_exact "$m" "$d"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "gsd-core/references/intruso.md"
}

# --- the requires guard bites -------------------------------------------------

@test "closure dies naming the SKILL.md when it promises a shim outside the list" {
  # The guard derived from rejecting the research's requires-expansion: a
  # vendored SKILL.md may not declare `requires:` pointing at a command the
  # cut does not deliver. In the real clone requires: lives in the commands'
  # frontmatter and no vendored SKILL.md declares it — this fixture proves
  # the guard BITES the day one does.
  new_corpus_fixture
  mkdir -p "$INV_SOURCE/skills/gsd-fast"
  cat > "$INV_SOURCE/skills/gsd-fast/SKILL.md" <<'EOF'
---
name: gsd-fast
requires: [config]
---
# shim (fixture) prometendo um command que o corte não entrega
EOF
  retag_fixture
  clo --json
  [ "$status" -eq 6 ]
  printf '%s' "$output" | grep -qF "skills/gsd-fast/SKILL.md"
  printf '%s' "$output" | grep -qF "commands/gsd/config.md"
}

# --- the flat contract and the vendor error paths -----------------------------

@test "the flat invocation is untouched by the subcommands (fixture, --json, exit 0)" {
  new_corpus_fixture
  inv --json
  [ "$status" -eq 0 ]
  [ "$(cjq '.source.commit')" = "$INV_COMMIT" ]
  [ "$(cjq '.sites | length > 0')" = "true" ]
}

@test "vendor with a missing manifest exits exactly 2 naming the path" {
  new_corpus_fixture
  ven --manifest "$BATS_TEST_TMPDIR/nao-existe.json"
  [ "$status" -eq 2 ]
  printf '%s' "$output" | grep -qF "nao-existe.json"
}

@test "vendor with a diverging manifest commit exits exactly 6 naming both shas" {
  new_corpus_fixture
  local m="$BATS_TEST_TMPDIR/manifest.json" forged="$BATS_TEST_TMPDIR/forged.json"
  "$INVENTORY" closure --cache-dir "$INV_CACHE" --source "$INV_SOURCE" \
    --expect-commit "$INV_COMMIT" --write "$m" >/dev/null
  jq '.source.commit = "0000000000000000000000000000000000000000"' "$m" > "$forged"
  ven --manifest "$forged" --dest "$BATS_TEST_TMPDIR/dest"
  [ "$status" -eq 6 ]
  printf '%s' "$output" | grep -qF "0000000000000000000000000000000000000000"
  printf '%s' "$output" | grep -qF "$INV_COMMIT"
}

# --- the real artifacts (VEND-01 reverse / VEND-03 / VEND-04) ----------------

VEND_MANIFEST="$CAIRN_REPO_ROOT/cairn/gsd/MANIFEST.json"
VEND_ROOT="$CAIRN_REPO_ROOT/cairn/gsd"
CONTRACTS_AGG="$CAIRN_REPO_ROOT/cairn/gsd/contracts/contracts.json"
# O registro de adaptações vive FORA de cairn/gsd/: um arquivo a mais lá
# dentro reprovaria assert_tree_set_exact, que exige a árvore == files[].
VEND_ADAPTATIONS="$CAIRN_REPO_ROOT/cairn/gsd-adaptations.json"

@test "real manifest: exists, parses, ends in a newline, files[] sorted and non-empty" {
  [ -f "$VEND_MANIFEST" ]
  jq empty "$VEND_MANIFEST"
  [ "$(tail -c1 "$VEND_MANIFEST" | od -An -c | tr -d ' ')" = '\n' ]
  jq -e '.schema_version == 1' "$VEND_MANIFEST"
  jq -e '.files | length > 0 and . == sort' "$VEND_MANIFEST"
  jq -e '.derived_from.command == "cairn/scripts/cairn-inventory.sh closure --json"' "$VEND_MANIFEST"
}

@test "real manifest: source identity agrees with contracts.json and the commit is the pinned sha" {
  # The pinned sha is typed ONCE in this test; the sibling identity is read
  # from contracts.json and compared, never typed a second time (the model
  # is the aggregate↔family identity check of the contracts suite).
  [ -f "$CONTRACTS_AGG" ]
  jq -e '.source.commit == "68a04ccf8ef74803bdb651e12c3b85b218bbccdf"' "$VEND_MANIFEST"
  local repo tag commit
  repo=$(jq -r '.source.repo' "$CONTRACTS_AGG")
  tag=$(jq -r '.source.tag' "$CONTRACTS_AGG")
  commit=$(jq -r '.source.commit' "$CONTRACTS_AGG")
  jq -e --arg r "$repo" --arg t "$tag" --arg c "$commit" \
    '.source.repo == $r and .source.tag == $t and .source.commit == $c' \
    "$VEND_MANIFEST"
}

@test "real tree: every files[] entry exists under cairn/gsd/ (presence needs no cache)" {
  local p fails=0
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if [ ! -f "$VEND_ROOT/$p" ]; then
      echo "manifest entry missing under cairn/gsd/: $p" >&2
      fails=$((fails + 1))
    fi
  done < <(jq -r '.files[]' "$VEND_MANIFEST")
  [ "$fails" -eq 0 ]
}

@test "real tree: nothing beyond files[] + MANIFEST.json + contracts/** in either direction" {
  # The reverse sense of VEND-01 ("exactly the files on the list"): find of
  # the tree vs files[] of the manifest, comm in BOTH directions, residues
  # named on stderr by the shared oracle.
  run assert_tree_set_exact "$VEND_MANIFEST" "$VEND_ROOT"
  [ "$status" -eq 0 ]
}

# --- the cut holds (VEND-04) --------------------------------------------------

# The excluded blocks of the research §3 table, as paths relative to the
# vendored root: upstream tests, docs, TypeScript source, dev/release
# scripts, the installer (bin/install.js — the whole bin/ block), the
# runtime bin seed (gsd-core/bin), eslint-rules, the multi-host
# capabilities/, .github, examples, .changeset, and the hooks/ block where
# gsd-write-guard.js lives.
CUT_BLOCKS="tests docs src scripts bin gsd-core/bin eslint-rules capabilities .github examples .changeset hooks"

# The single absence oracle for the cut. Takes the tree root as its argument
# so the negative control can point the SAME loop at a forged tree.
assert_cut_holds() {
  local root="$1" fails=0 block hits
  # gsd-write-guard by name, anywhere: the canonical exclusion.
  hits="$(find "$root" -name 'gsd-write-guard*' -print 2>/dev/null)"
  if [ -n "$hits" ]; then
    echo "gsd-write-guard survived the cut:" >&2
    echo "$hits" >&2
    fails=$((fails + 1))
  fi
  for block in $CUT_BLOCKS; do
    if [ -e "$root/$block" ]; then
      echo "excluded block present under the vendored tree: $block" >&2
      fails=$((fails + 1))
    fi
  done
  # Multi-host source by name, constrained to compiled-source extensions so
  # a legitimate reference like runtime-aware-dispatch.md never
  # false-positives.
  hits="$(find "$root" \( -name 'host-integration-sdk*' \
    -o -name 'adapter-*.cts' -o -name 'runtime-*.cts' \) -print 2>/dev/null)"
  if [ -n "$hits" ]; then
    echo "multi-host block present under the vendored tree:" >&2
    echo "$hits" >&2
    fails=$((fails + 1))
  fi
  [ "$fails" -eq 0 ]
}

@test "the cut holds: gsd-write-guard.js is NOT vendored (collides with bd as state owner)" {
  # The upstream PreToolUse hook blocks any Write that shrinks
  # ROADMAP.md/STATE.md below a line floor. In cairn the bd database owns
  # that state and the milestone retires the planning files as owners —
  # vendoring the guard would make the upstream hook fight the new owner,
  # so its absence is asserted BY NAME.
  [ ! -e "$VEND_ROOT/hooks/gsd-write-guard.js" ]
  [ -z "$(find "$VEND_ROOT" -name 'gsd-write-guard*' -print 2>/dev/null)" ]
}

@test "the cut holds: every excluded block of the research §3 table is absent (tabular)" {
  run assert_cut_holds "$VEND_ROOT"
  [ "$status" -eq 0 ]
}

@test "negative control: a forged forbidden file is caught and named by the absence loop" {
  # The liveness half of the cut oracle: inject a forbidden file into a
  # simulated tree and prove the SAME loop bites it.
  local forged="$BATS_TEST_TMPDIR/forged-tree"
  mkdir -p "$forged/hooks"
  printf 'module.exports = {};\n' > "$forged/hooks/gsd-write-guard.js"
  run assert_cut_holds "$forged"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "gsd-write-guard.js"
}

# --- the acceptance numbers, against the real corpus -------------------------
# Every expected value below was MEASURED on 2026-08-10 by running
#   CLAUDE_PROJECT_DIR=<repo> cairn/scripts/cairn-inventory.sh closure --json | jq '.totals'
# against the real cache of the v1.10.0 tag (commit 68a04cc). The research
# §2.1 ballpark was 160 files / 28,071 lines; the measured closure is larger
# and the divergence is explained beside the value in the dated block of
# cairn-inventory.py (16 agents where the research summed 13, 16 shims where
# it counted only the 8 SKILL.md, LICENSE entering through the list itself,
# and contexts/ referenced by no file) — the measured value is asserted and
# the script is never bent to force a research number.

@test "real manifest: totals restate files[] and carry the measured closure size" {
  jq -e '(.files | length) == .totals.files' "$VEND_MANIFEST"
  # closure --json | jq '.totals.files'  → 171 (2026-08-10)
  jq -e '.totals.files == 171' "$VEND_MANIFEST"
  # closure --json | jq '.totals.lines'  → 29957 (2026-08-10)
  jq -e '.totals.lines == 29957' "$VEND_MANIFEST"
}

# --- fidelity against the real cache (skip-gated) ----------------------------

real_cache_or_skip() {
  REAL_CACHE="$CAIRN_REPO_ROOT/.cairn/cache/gsd-core-v1.10.0"
  [ -d "$REAL_CACHE" ] || \
    skip "cache do clone ausente — rode cairn-inventory.sh uma vez com rede"
}

@test "real tree: every files[] entry matches the pinned cache on both senses of the registry" {
  real_cache_or_skip
  run assert_tree_bytes_match "$VEND_MANIFEST" "$VEND_ROOT" "$REAL_CACHE" \
    "$VEND_ADAPTATIONS"
  [ "$status" -eq 0 ]
}

@test "negative control: the two senses of the byte oracle both bite, and say WHICH" {
  # The liveness half of VEND-BYTES, forged so it runs with or without the
  # cache. Two failures, two distinct sentences — an unannounced drift and a
  # LOST adaptation are different defects and a shared message would hide the
  # second, which is the one a re-vendor or a bad merge produces.
  local base="$BATS_TEST_TMPDIR/two-senses"
  local corpus="$base/corpus" tree="$base/tree"
  mkdir -p "$corpus/w" "$tree/w"
  printf 'adaptado\n' > "$corpus/w/a.md"
  printf 'intocado\n' > "$corpus/w/b.md"
  cp "$corpus/w/a.md" "$tree/w/a.md"
  cp "$corpus/w/b.md" "$tree/w/b.md"
  printf '{"files":["w/a.md","w/b.md"]}\n' > "$base/manifest.json"
  printf '%s\n' '{"schema_version":1,"adaptations":[{"path":"w/a.md","phase":"36","waves":[1],"reason":"forjado"}]}' \
    > "$base/adaptations.json"

  # Sentido A: o registrado voltou ao byte do upstream.
  run assert_tree_bytes_match "$base/manifest.json" "$tree" "$corpus" \
    "$base/adaptations.json"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "a adaptação registrada sumiu"
  printf '%s' "$output" | grep -qF "w/a.md"

  # Adaptado de verdade: o mesmo laço passa a ficar verde.
  printf 'adaptado pela fase\n' > "$tree/w/a.md"
  run assert_tree_bytes_match "$base/manifest.json" "$tree" "$corpus" \
    "$base/adaptations.json"
  [ "$status" -eq 0 ]

  # Sentido B: um NÃO registrado divergiu.
  printf 'deriva nao anunciada\n' > "$tree/w/b.md"
  run assert_tree_bytes_match "$base/manifest.json" "$tree" "$corpus" \
    "$base/adaptations.json"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "vendored bytes diverge from the corpus"
  printf '%s' "$output" | grep -qF "w/b.md"
}

@test "PORCELAIN invertido: o conjunto divergente do cache é EXATAMENTE o registro" {
  # A forma nova do gate herdado das fases 33-35. Aquele era
  # `git status --porcelain cairn/gsd/` vazio, convenção copiada em onze
  # planos, e a fase 36 o reprova por desenho. Este vale antes E depois do
  # commit, que é por que os planos seguintes citam ele.
  real_cache_or_skip
  local p diverged registered only_tree only_registry
  diverged=""
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    [ -f "$VEND_ROOT/$p" ] || continue
    cmp -s "$VEND_ROOT/$p" "$REAL_CACHE/$p" || diverged="${diverged}${p}"$'\n'
  done < <(jq -r '.files[]' "$VEND_MANIFEST")
  diverged="$(printf '%s' "$diverged" | LC_ALL=C sort)"
  registered="$(jq -r '.adaptations[].path' "$VEND_ADAPTATIONS" \
    | LC_ALL=C sort)"
  only_tree="$(LC_ALL=C comm -23 <(printf '%s\n' "$diverged") \
    <(printf '%s\n' "$registered"))"
  only_registry="$(LC_ALL=C comm -13 <(printf '%s\n' "$diverged") \
    <(printf '%s\n' "$registered"))"
  if [ -n "$only_tree" ] || [ -n "$only_registry" ]; then
    printf 'divergem do cache sem registro:\n%s\nregistrados que não divergem:\n%s\n' \
      "$only_tree" "$only_registry" >&2
    return 1
  fi
}

@test "real manifest == closure re-run on the cache: file sets identical in both directions" {
  real_cache_or_skip
  local live="$BATS_TEST_TMPDIR/live.json"
  "$INVENTORY" closure --cache-dir "$REAL_CACHE" --json > "$live"
  local manifest_files live_files only_manifest only_live
  manifest_files="$(jq -r '.files[]' "$VEND_MANIFEST" | LC_ALL=C sort)"
  live_files="$(jq -r '.files[]' "$live" | LC_ALL=C sort)"
  only_manifest="$(LC_ALL=C comm -23 <(printf '%s\n' "$manifest_files") \
    <(printf '%s\n' "$live_files"))"
  only_live="$(LC_ALL=C comm -13 <(printf '%s\n' "$manifest_files") \
    <(printf '%s\n' "$live_files"))"
  if [ -n "$only_manifest" ] || [ -n "$only_live" ]; then
    printf 'manifest-only files:\n%s\nlive-only files:\n%s\n' \
      "$only_manifest" "$only_live" >&2
    return 1
  fi
}

@test "real LICENSE: byte-identical to the clone's — never stacked with extra copyrights" {
  real_cache_or_skip
  run cmp "$VEND_ROOT/LICENSE" "$REAL_CACHE/LICENSE"
  [ "$status" -eq 0 ]
}

# --- the vendoring numbers guard ---------------------------------------------
# The inventory suite's docstring GUARD watches sites/verbs/calls nouns; the
# closure introduced NEW nouns (arquivos/files, linhas/lines) that a count
# could hide behind. Same discipline, extended HERE (existing suites are not
# edited): a numeric closure count may live only inside the dated
# MEASURED VERSUS ASSUMED block of cairn-inventory.py, and never in the .sh.

vendoring_count_pattern() {
  local nouns='arquivos?|files?|linhas?|lines?'
  local numerals='[0-9]+([.,][0-9]+)*'
  numerals="$numerals"'|dois|duas|tr[êe]s|quatro|cinco|seis|sete|oito|nove|dez'
  printf '(^|[^A-Za-z_])(%s) (%s)([^A-Za-z]|$)' "$numerals" "$nouns"
}

@test "GUARD: no live closure count (files/lines nouns) outside the dated block" {
  local py="$CAIRN_SCRIPTS_DIR/cairn-inventory.py"
  local sh="$CAIRN_SCRIPTS_DIR/cairn-inventory.sh"
  local pattern before hit
  pattern="$(vendoring_count_pattern)"
  before="$(awk '/^MEASURED VERSUS ASSUMED$/{exit} {print}' "$py")"
  hit="$(printf '%s' "$before" | grep -inE "$pattern" || true)"
  if [ -n "$hit" ]; then
    echo "a closure count sits outside the dated block in cairn-inventory.py:" >&2
    echo "$hit" >&2
    return 1
  fi
  hit="$(grep -inE "$pattern" "$sh" || true)"
  if [ -n "$hit" ]; then
    echo "a closure count sits in cairn-inventory.sh:" >&2
    echo "$hit" >&2
    return 1
  fi
  # Liveness: the pattern must actually match something, or it guards air.
  printf 'the closure has 171 files\n' | grep -qiE "$pattern"
  printf 'faltam duas linhas\n' | grep -qiE "$pattern"
}

@test "GUARD negative control: a forged count outside the block is caught" {
  # Same extraction, pointed at a forged file carrying a count BEFORE the
  # dated block — the guard must bite and name the number.
  local forged="$BATS_TEST_TMPDIR/forged-inventory.py"
  { printf 'prose: a arvore vendorizada tem 999 arquivos hoje\n'
    printf 'MEASURED VERSUS ASSUMED\n'
    printf 'depois do bloco: 123 linhas podem morar aqui\n'; } > "$forged"
  local pattern before hit
  pattern="$(vendoring_count_pattern)"
  before="$(awk '/^MEASURED VERSUS ASSUMED$/{exit} {print}' "$forged")"
  hit="$(printf '%s' "$before" | grep -inE "$pattern" || true)"
  [ -n "$hit" ]
  printf '%s' "$hit" | grep -qF "999"
  # And the after-block text is exactly what the extraction excludes.
  printf '%s' "$before" | grep -qF "123" && return 1
  return 0
}
