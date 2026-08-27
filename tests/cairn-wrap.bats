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

# A fake cairn commands dir. Each arg is "name:wraps:family[:implementation]"
# (wraps and family empty => a cairn-own command, no `wraps:` key). The
# implementation field defaults to `inline`, the shape twelve of the thirteen
# have carried since phase 37.
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
  local tail="${rest#*:}"
  local family="${tail%%:*}"
  local impl="inline"
  case "$tail" in *:*) impl="${tail#*:}" ;; esac
  {
    echo '---'
    echo "description: does $name"
    if [ -n "$wraps" ]; then
      echo "wraps: $wraps"
      echo "wrap-family: $family"
      echo "implementation: $impl"
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
  echo "$output" | grep -qF "'phase' is not implemented by this plugin"
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
  echo "$output" | grep -qF "'ship' is implemented here"
}

@test "preflight: an empty surface is 6 (looked), not 5 (could not look)" {
  # The two codes are two different facts. Collapsing them into one makes
  # exactly one of these two tests fail.
  WRAP_SURFACE="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/gsd-empty.XXXXXX")"

  CAIRN_GSD_COMMANDS_DIR="$WRAP_SURFACE" run bash "$WRAP" preflight phase
  [ "$status" -eq 6 ]
  echo "$output" | grep -qF '0 command(s) found there'
}

@test "preflight: a plugin with no vendored runtime exits 5 and lists every path tried" {
  # Phase 37 changed what exit 5 MEANS. It used to say "no GSD is installed on
  # this machine"; it now says "this plugin is incomplete", because the
  # runtime is vendored and its absence is a defect of the install, not of the
  # environment. CLAUDE_PLUGIN_ROOT is pointed at an empty tree to produce
  # exactly that, with no dependence on what the runner has installed.
  local fake_plugin
  fake_plugin="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/fake-plugin.XXXXXX")"

  run env -u CAIRN_GSD_COMMANDS_DIR CLAUDE_PLUGIN_ROOT="$fake_plugin" \
    bash "$WRAP" preflight phase
  [ "$status" -eq 5 ]
  echo "$output" | grep -qF 'no vendored GSD surface'
  echo "$output" | grep -qF 'CAIRN_GSD_COMMANDS_DIR (unset)'
  echo "$output" | grep -qF "$fake_plugin/gsd/commands/gsd (absent or empty)"
  echo "$output" | grep -qF "$fake_plugin/gsd/gsd-core/workflows (absent or empty)"
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

  local i name wraps file impl
  for ((i = 0; i < count; i++)); do
    name="$(jq -r ".wrappers[$i].command" <<<"$output")"
    wraps="$(jq -r ".wrappers[$i].wraps" <<<"$output")"
    file="$CAIRN_REPO_ROOT/cairn/commands/$name.md"

    # As agulhas sao CONSTRUIDAS a partir do JSON, nunca digitadas. Desde a
    # fase 37 a primeira metade e' condicional: um comando `vendored` delega
    # ao arquivo que o plugin carrega, e por isso preflighta; um `inline` E' a
    # implementacao, e preflightar seria afirmar uma delegacao inexistente —
    # alem de instalar um gate que nao pode falhar.
    impl="$(jq -r ".wrappers[$i].implementation" <<<"$output")"
    if [ "$impl" = "vendored" ]; then
      grep -qF "cairn-wrap.sh\" preflight $wraps" "$file" \
        || { echo "$name.md is vendored and does not preflight $wraps" >&2; return 1; }
      grep -qF "gsd/commands/gsd/$wraps.md" "$file" \
        || { echo "$name.md is vendored and never names its implementation file" >&2; return 1; }
    else
      grep -qF "cairn-wrap.sh\" preflight" "$file" \
        && { echo "$name.md is inline and still preflights" >&2; return 1; }
    fi
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

@test "the installed wrappers are exactly the thirteen GSD-05 decided" {
  # An exact count and an exact SET, never `>=`: a lost wrapper is the defect
  # this phase is about, and an inequality would hide it. The thirteen names
  # are written HERE and nowhere else — this test is what asserts agreement
  # with decision GSD-05 (see cairn/docs/gsd-core-commands.md). The script
  # itself still derives; a wrapper removed, or one wrapping a command outside
  # the decision, fails here naming which.
  run bash "$WRAP" list --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.wrappers | length' '13'
  assert_json_eq "$output" '[.wrappers[].wraps] | sort | join(",")' \
    'ai-integration-phase,audit-milestone,cleanup,discuss-phase,mvp-phase,phase,plan-review-convergence,review-backlog,secure-phase,spec-phase,ui-phase,ultraplan-phase,validate-phase'
}

@test "every vendored command resolves against the runtime this plugin carries" {
  # A INVERSAO da fase 37. Antes: "todo wrapper delega a um comando que o
  # gsd-core instalado tem". Agora: "todo comando `vendored` resolve DENTRO do
  # plugin", e a maquina de quem roda deixou de entrar na conta.
  run bash "$WRAP" list --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" --json
  [ "$status" -eq 0 ]

  local count i wraps impl checked=0
  count="$(jq -r '.wrappers | length' <<<"$output")"
  local listing="$output"
  for ((i = 0; i < count; i++)); do
    impl="$(jq -r ".wrappers[$i].implementation" <<<"$listing")"
    [ "$impl" = "vendored" ] || continue
    wraps="$(jq -r ".wrappers[$i].wraps" <<<"$listing")"
    run bash "$WRAP" preflight "$wraps"
    [ "$status" -eq 0 ] || {
      echo "preflight $wraps exited $status" >&2
      return 1
    }
    checked=$((checked + 1))
  done
  # Desde a phase 46 NENHUM wrapper le o runtime vendorizado (os comandos de
  # planejamento sao autossuficientes e gravam pelo cairn-record), entao
  # zero checados e' o estado esperado — desde que zero seja tambem o numero
  # de comandos que DECLARAM vendored. Um declarado e nao checado e' o que o
  # teste nao pode deixar passar.
  local declared
  declared="$(jq -r '[.wrappers[] | select(.implementation == "vendored")] | length' <<<"$listing")"
  [ "$checked" -eq "$declared" ] || {
    echo "declarados vendored: $declared, checados: $checked — o teste nao mediu o que devia" >&2
    return 1
  }
}

@test "the guard still bites: a verb this plugin does not carry exits 6" {
  # O par negativo, e ele e' o que impede a inversao de virar um gate vazio.
  # `spec-phase` foi um dos treze e HOJE e' implementacao inline: o plugin nao
  # carrega arquivo nenhum para ele, e preflight tem de dizer isso.
  run bash "$WRAP" preflight spec-phase
  [ "$status" -eq 6 ]
  echo "$output" | grep -qF "'spec-phase' is not implemented by this plugin"
  echo "$output" | grep -qF 'command(s) found there'
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

# ---------------------------------------------------------------------------
# docs — WRAP-03. The list is derived; the page is a VIEW of the disk.
# ---------------------------------------------------------------------------

# A doc fixture with hand-written prose on both sides of where the block goes.
make_doc_fixture() {
  WRAP_DOC="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/cairn-doc.XXXXXX")/commands.md"
  mkdir -p "$(dirname "$WRAP_DOC")/commands"
  cat > "$WRAP_DOC" <<'DOC'
# Command reference

Hand-written intro that must survive regeneration.

| Command | Description |
|---|---|
| [`/cairn:solo`](./commands/solo.md) | a cairn command of its own |

## See also

Hand-written outro that must survive too.
DOC
  WRAP_DOC_PAGES="$(dirname "$WRAP_DOC")/commands"
}

@test "docs: adding a wrapper makes the page list it, with no prose edited" {
  # THE test for WRAP-03. Swapping the derivation for a literal list makes the
  # third wrapper never appear, and this fails.
  make_cairn_commands "alpha:plan-phase:phase" "beta:cleanup:milestone"
  make_doc_fixture

  run bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES"
  [ "$status" -eq 0 ]
  grep -qF '/cairn:alpha' "$WRAP_DOC"
  grep -qF '/cairn:beta' "$WRAP_DOC"

  # Freeze everything outside the markers, byte for byte.
  local before_outside="$BATS_TEST_TMPDIR/outside.before"
  sed '/cairn:generated:start/,/cairn:generated:end/d' "$WRAP_DOC" \
    > "$before_outside"

  # A wrapper arrives. Nobody edits prose.
  add_cairn_command "gamma:ui-phase:phase"
  run bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES"
  [ "$status" -eq 0 ]
  grep -qF '/cairn:gamma' "$WRAP_DOC"
  grep -qF '`/gsd:ui-phase`' "$WRAP_DOC"

  local after_outside="$BATS_TEST_TMPDIR/outside.after"
  sed '/cairn:generated:start/,/cairn:generated:end/d' "$WRAP_DOC" \
    > "$after_outside"
  diff "$before_outside" "$after_outside"
}

@test "docs --check: a wrapper the page has not seen is stale (3), with a diff" {
  make_cairn_commands "alpha:plan-phase:phase"
  make_doc_fixture
  bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" >/dev/null

  add_cairn_command "gamma:ui-phase:phase"
  run bash "$WRAP" docs --check --commands-dir "$WRAP_COMMANDS" \
    --doc "$WRAP_DOC" --doc-pages-dir "$WRAP_DOC_PAGES"
  [ "$status" -eq 3 ]
  echo "$output" | grep -qF 'gamma'
  echo "$output" | grep -qF '+++'
}

@test "docs --check: current is 0" {
  # Without this pair, the test above would pass against a --check that always
  # exits 3.
  make_cairn_commands "alpha:plan-phase:phase"
  make_doc_fixture
  bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" >/dev/null

  run bash "$WRAP" docs --check --commands-dir "$WRAP_COMMANDS" \
    --doc "$WRAP_DOC" --doc-pages-dir "$WRAP_DOC_PAGES"
  [ "$status" -eq 0 ]
}

@test "docs: everything outside the markers survives, and the block is placed once" {
  make_cairn_commands "alpha:plan-phase:phase"
  make_doc_fixture
  bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" >/dev/null

  grep -qF 'Hand-written intro that must survive regeneration.' "$WRAP_DOC"
  grep -qF 'Hand-written outro that must survive too.' "$WRAP_DOC"
  grep -qF '/cairn:solo' "$WRAP_DOC"
  [ "$(grep -c 'cairn:generated:start' "$WRAP_DOC")" -eq 1 ]
  [ "$(grep -c 'cairn:generated:end' "$WRAP_DOC")" -eq 1 ]

  # A second run must not append a second block.
  bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" >/dev/null
  [ "$(grep -c 'cairn:generated:start' "$WRAP_DOC")" -eq 1 ]
}

@test "docs: a no-op run writes nothing — measured by sha256 AND mtime" {
  # A byte-identical rewrite is still a write. cairn-bookkeep.py set this bar.
  make_cairn_commands "alpha:plan-phase:phase"
  make_doc_fixture
  bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" >/dev/null

  local sha1 mtime1 sha2 mtime2 changed
  sha1="$(shasum -a 256 "$WRAP_DOC" | cut -d' ' -f1)"
  mtime1="$(file_mtime_ns "$WRAP_DOC")"
  sleep 1
  run bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" --json
  [ "$status" -eq 0 ]
  sha2="$(shasum -a 256 "$WRAP_DOC" | cut -d' ' -f1)"
  mtime2="$(file_mtime_ns "$WRAP_DOC")"

  # Three assertions, and they fail in different ways on purpose.
  #
  # `changed` is the decision the generator made, read from its own output
  # rather than inferred: it is the only one of the three that says WHY, and a
  # generator that starts rewriting identical bytes trips it first.
  changed="$(jq -r '.changed' <<<"$output")"
  [ "$changed" = "false" ]
  # sha catches a rewrite that changed the bytes.
  [ "$sha1" = "$sha2" ]
  # mtime catches the byte-identical rewrite, which the sha cannot see. Read
  # through file_mtime_ns, not `stat`: the platform-shim spelling this line
  # used to carry passed on macOS and failed on the CI runner on 2026-08-07,
  # and a portability shim must never be what decides a verdict.
  [ "$mtime1" = "$mtime2" ]
}

@test "docs: a command with no row anywhere is NAMED, and the warning clears" {
  # This is how /cairn:config and /cairn:reconcile stayed invisible for weeks.
  # A generator that quietly omitted them would have preserved that.
  make_cairn_commands "alpha:plan-phase:phase" "ghost::"
  make_doc_fixture

  run bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" --json
  [ "$status" -eq 0 ]
  # `solo` is a link with no command file — that is the ORPHAN direction, not
  # this one. `ghost` is a command file with no link, which is what
  # /cairn:config and /cairn:reconcile were.
  assert_json_eq "$output" '[.undocumented[]] | join(",")' 'ghost'
  grep -qF 'Not documented: `/cairn:ghost`' "$WRAP_DOC"

  # Give both a row in the hand-written table; the warning goes on its own.
  python3 - "$WRAP_DOC" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
row = "| [`/cairn:ghost`](./commands/ghost.md) | a real row |\n"
s = s.replace("| [`/cairn:solo`](./commands/solo.md) | a cairn command of its own |\n",
              "| [`/cairn:solo`](./commands/solo.md) | a cairn command of its own |\n" + row)
open(p, "w").write(s)
PY
  run bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.undocumented | length' '0'
  refute_in_file 'Not documented' "$WRAP_DOC"
}

@test "docs: a doc page for no installed command is NAMED as an orphan" {
  make_cairn_commands "alpha:plan-phase:phase"
  make_doc_fixture
  touch "$WRAP_DOC_PAGES/ancient.md"

  run bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.orphan_pages[]] | join(",")' 'ancient'
  grep -qF 'Orphan page: `commands/ancient.md`' "$WRAP_DOC"
}

@test "docs: a row linking a page that does not exist is NAMED as missing" {
  # The generator writes a row per wrapper whether or not anyone wrote the
  # page, so a table of broken links is a lie this tool can author itself.
  # Reporting it is not optional.
  make_cairn_commands "alpha:plan-phase:phase"
  make_doc_fixture

  run bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.missing_pages[]] | join(",")' 'alpha'
  grep -qF 'Missing page: `commands/alpha.md`' "$WRAP_DOC"

  # Write the page; the warning goes on its own.
  touch "$WRAP_DOC_PAGES/alpha.md"
  run bash "$WRAP" docs --commands-dir "$WRAP_COMMANDS" --doc "$WRAP_DOC" \
    --doc-pages-dir "$WRAP_DOC_PAGES" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.missing_pages | length' '0'
  refute_in_file 'Missing page' "$WRAP_DOC"
}

# ---------------------------------------------------------------------------
# The real page. These are the guards that keep it from ageing again.
# ---------------------------------------------------------------------------

@test "the real command reference is current, and documents every command" {
  run bash "$WRAP" docs --check --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" \
    --doc "$CAIRN_REPO_ROOT/cairn/docs/commands.md" \
    --doc-pages-dir "$CAIRN_REPO_ROOT/cairn/docs/commands"
  [ "$status" -eq 0 ]

  run bash "$WRAP" docs --check --json \
    --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" \
    --doc "$CAIRN_REPO_ROOT/cairn/docs/commands.md" \
    --doc-pages-dir "$CAIRN_REPO_ROOT/cairn/docs/commands"
  assert_json_eq "$output" '.undocumented | length' '0'
  # Every row on the page links a page that exists — no broken links.
  assert_json_eq "$output" '.missing_pages | length' '0'
}

@test "/cairn:help derives its wrapper list instead of transcribing one" {
  # The help map is the page users read most, and it is hand-written ASCII —
  # exactly the shape that ages. It must DELEGATE the wrapper list rather than
  # carry a copy of it.
  local file="$CAIRN_REPO_ROOT/cairn/commands/help.md"
  grep -qF 'cairn-wrap.sh" list' "$file"

  # And it must not have transcribed the list: no wrapper name may appear in
  # the hand-written map block. Deleting the delegation and pasting thirteen
  # lines in fails here.
  local mapblock="$BATS_TEST_TMPDIR/help.map"
  awk '/^```text/{f=1;next} /^```/{f=0} f' "$file" > "$mapblock"

  run bash "$WRAP" list --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" --json
  [ "$status" -eq 0 ]
  local count i name
  count="$(jq -r '.wrappers | length' <<<"$output")"
  local listing="$output"
  for ((i = 0; i < count; i++)); do
    name="$(jq -r ".wrappers[$i].command" <<<"$listing")"
    refute_in_file "/cairn:$name" "$mapblock"
  done
}

@test "the real command reference states no hand-written total" {
  # The direct guard against the measured defect: this page said "22 in total"
  # with 25 commands on disk, and doctor.md said "fifteen checks" with sixteen
  # registered. A digit followed by "in total" outside the generated block is
  # a number nobody validates.
  local outside="$BATS_TEST_TMPDIR/commands.outside"
  sed '/cairn:generated:start/,/cairn:generated:end/d' \
    "$CAIRN_REPO_ROOT/cairn/docs/commands.md" > "$outside"
  refute_in_file ' in total' "$outside"
}
