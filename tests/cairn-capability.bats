#!/usr/bin/env bats
# cairn-capability.bats — the capability installer/verifier contract.
#
# The point of this script is that "attempted" is not "installed", so these
# tests care most about the paths where an install LOOKS fine and is not:
# a lineage that cannot host the capability at all, a registry that does not
# list it, and a bundle staged without the scripts its gates run. Each must
# exit 7, not 0.
#
# Assertion style note (same as capability.bats): a failing `[[ ]]` mid-test
# does NOT fail a bats test on this bash, so substring checks go through
# grep -qF over "$output".

load 'helpers'

CAP_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-capability.sh"
BUNDLE="$CAIRN_REPO_ROOT/cairn/capability"

assert_output_contains() {
  if ! printf '%s\n' "$output" | grep -qF -- "$1"; then
    echo "expected output to contain '$1', got:" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}

# A fake GSD entry point. $1 selects what `capability list` reports:
#   core-active    cairn present with status active   (the happy path)
#   core-inactive  cairn present, status disabled
#   core-absent    a valid registry without cairn in it
#   legacy         the 4.x line: no 'capability' subcommand, exit 1
#   garbage        answers, but not with JSON
# install/update always succeed, so the verification — not the installer's
# exit code — decides the verdict.
make_gsd_stub() {
  local mode="$1" bin="$BATS_TEST_TMPDIR/gsd_run"
  cat > "$bin" <<EOF
#!/usr/bin/env sh
mode="$mode"
EOF
  cat >> "$bin" <<'EOF'
if [ "$1" != "capability" ]; then echo "unexpected: $*" >&2; exit 1; fi
case "$mode" in
  legacy) echo "Error: Unknown command: capability" >&2; exit 1 ;;
esac
case "$2" in
  install|update) echo '{"status":"installed","id":"cairn"}'; exit 0 ;;
esac
case "$mode" in
  garbage) echo "not json at all"; exit 0 ;;
  core-absent)
    echo '[{"id":"ai-integration","status":"active"}]' ;;
  core-inactive)
    echo '[{"id":"cairn","status":"disabled","version":"1.0.0","scope":"project"}]' ;;
  *)
    echo '[{"id":"cairn","status":"active","version":"1.0.0","scope":"project","role":"feature"}]' ;;
esac
exit 0
EOF
  chmod +x "$bin"
  printf '%s\n' "$bin"
}

# Stage a bundle the way `capability install --scope project` does.
# $2 = "complete" (default) or "no-scripts" to reproduce a bundle staged
# without the gate script.
stage_bundle() {
  local proj="$1" how="${2:-complete}"
  local dest="$proj/.gsd/capabilities/cairn"
  mkdir -p "$dest/fragments" "$dest/scripts"
  cp "$BUNDLE/capability.json" "$dest/capability.json"
  cp "$BUNDLE"/fragments/*.md "$dest/fragments/" 2>/dev/null || true
  if [ "$how" = "complete" ]; then
    cp "$BUNDLE"/scripts/cairn-loop-gate.sh "$dest/scripts/"
    cp "$BUNDLE"/scripts/cairn-loop-gate.py "$dest/scripts/" 2>/dev/null || true
  fi
}

setup() {
  PROJ="$BATS_TEST_TMPDIR/proj"
  mkdir -p "$PROJ"
}

# ─── Usage ───────────────────────────────────────────────────────────────────

@test "no command is a usage error" {
  run bash "$CAP_SH"
  [ "$status" -eq 2 ]
  assert_output_contains "a command is required"
}

@test "unknown command is a usage error" {
  run bash "$CAP_SH" frobnicate
  [ "$status" -eq 2 ]
  assert_output_contains "unknown command"
}

@test "unknown flag is a usage error" {
  run bash "$CAP_SH" detect --wat
  [ "$status" -eq 2 ]
  assert_output_contains "unknown argument"
}

@test "--gsd-bin pointing at a non-file is a usage error" {
  run bash "$CAP_SH" detect --gsd-bin "$BATS_TEST_TMPDIR/nope"
  [ "$status" -eq 2 ]
  assert_output_contains "is not a file"
}

# ─── Lineage ─────────────────────────────────────────────────────────────────

@test "the 4.x lineage is a failure with the upgrade command, not a shrug" {
  stub="$(make_gsd_stub legacy)"
  run bash "$CAP_SH" install --project-dir "$PROJ" --gsd-bin "$stub"
  [ "$status" -eq 7 ]
  assert_output_contains "legacy"
  assert_output_contains "claude plugin install gsd-core@cairngo"
}

@test "a GSD that answers with something other than JSON is 'unknown', not 'ok'" {
  stub="$(make_gsd_stub garbage)"
  stage_bundle "$PROJ"
  run bash "$CAP_SH" detect --project-dir "$PROJ" --gsd-bin "$stub"
  [ "$status" -eq 7 ]
  assert_output_contains "unknown"
}

@test "gsd-core wins discovery over a higher-numbered legacy install" {
  # The two lines version independently, so plain newest-wins would pick
  # gsd 4.4.0 over gsd-core 1.8.0 and report 'legacy' on a machine that has
  # the official core installed. Lineage has to outrank the version number.
  command -v node >/dev/null 2>&1 || skip "node is not on PATH"
  cache="$BATS_TEST_TMPDIR/cache/mk"
  mkdir -p "$cache/cairn/1.3.0" \
           "$cache/gsd/4.4.0/bin" \
           "$cache/gsd-core/1.8.0/gsd-core/bin"

  cat > "$cache/gsd/4.4.0/bin/gsd-tools.cjs" <<'EOF'
console.error("Error: Unknown command: capability");
process.exit(1);
EOF
  cp "$(make_gsd_stub core-active)" "$cache/gsd-core/1.8.0/gsd-core/bin/gsd_run"
  chmod +x "$cache/gsd-core/1.8.0/gsd-core/bin/gsd_run"

  stage_bundle "$PROJ"
  run env CLAUDE_PLUGIN_ROOT="$cache/cairn/1.3.0" HOME="$BATS_TEST_TMPDIR/nohome" \
    PATH="/usr/bin:/bin:$(dirname "$(command -v node)")" \
    bash "$CAP_SH" detect --project-dir "$PROJ"
  [ "$status" -eq 0 ]
  assert_output_contains "gsd-core"
  assert_output_contains "fusion is active"
}

@test "no GSD binary anywhere exits 5, not 7" {
  # Scrub PATH and HOME so neither discovery route can find a real install.
  run env -u CLAUDE_PLUGIN_ROOT HOME="$BATS_TEST_TMPDIR/nohome" \
    PATH="/usr/bin:/bin" bash "$CAP_SH" detect --project-dir "$PROJ"
  [ "$status" -eq 5 ]
  assert_output_contains "no GSD binary on PATH"
}

# ─── Verification is the verdict ─────────────────────────────────────────────

@test "install succeeds when the capability registers and the bundle is complete" {
  stub="$(make_gsd_stub core-active)"
  stage_bundle "$PROJ"
  run bash "$CAP_SH" install --project-dir "$PROJ" --gsd-bin "$stub" \
    --capability-dir "$BUNDLE"
  [ "$status" -eq 0 ]
  assert_output_contains "fusion is active"
}

@test "an install the registry does not list is a failure even though the installer exited 0" {
  stub="$(make_gsd_stub core-absent)"
  stage_bundle "$PROJ"
  run bash "$CAP_SH" install --project-dir "$PROJ" --gsd-bin "$stub" \
    --capability-dir "$BUNDLE"
  [ "$status" -eq 7 ]
  assert_output_contains "did not register"
}

@test "a registered but disabled capability is not treated as active" {
  stub="$(make_gsd_stub core-inactive)"
  stage_bundle "$PROJ"
  run bash "$CAP_SH" detect --project-dir "$PROJ" --gsd-bin "$stub"
  [ "$status" -eq 7 ]
  assert_output_contains "status 'disabled'"
}

@test "a bundle staged without the gate script fails — the ship gate would pass vacuously" {
  stub="$(make_gsd_stub core-active)"
  stage_bundle "$PROJ" no-scripts
  run bash "$CAP_SH" detect --project-dir "$PROJ" --gsd-bin "$stub"
  [ "$status" -eq 7 ]
  assert_output_contains "scripts/cairn-loop-gate.sh"
  assert_output_contains "pass without ever checking"
}

@test "nothing staged at all is reported as missing, not as registered" {
  stub="$(make_gsd_stub core-active)"
  run bash "$CAP_SH" detect --project-dir "$PROJ" --gsd-bin "$stub"
  [ "$status" -eq 7 ]
  assert_output_contains "capability.json"
}

# ─── detect is read-only ─────────────────────────────────────────────────────

@test "detect writes nothing to the project" {
  stub="$(make_gsd_stub core-active)"
  before="$(find "$PROJ" | sort)"
  run bash "$CAP_SH" detect --project-dir "$PROJ" --gsd-bin "$stub"
  after="$(find "$PROJ" | sort)"
  [ "$before" = "$after" ]
}

# ─── JSON ────────────────────────────────────────────────────────────────────

@test "--json emits one parseable object carrying the verdict" {
  stub="$(make_gsd_stub core-active)"
  stage_bundle "$PROJ"
  run bash "$CAP_SH" detect --project-dir "$PROJ" --gsd-bin "$stub" --json
  [ "$status" -eq 0 ]
  echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["ok"] is True, d
assert d["lineage"] == "gsd-core", d
assert d["registered"] is True, d
assert d["staged_complete"] is True, d
assert d["capability"]["id"] == "cairn", d
'
}

@test "--json carries the remedy when verification fails" {
  stub="$(make_gsd_stub core-absent)"
  stage_bundle "$PROJ"
  run bash "$CAP_SH" detect --project-dir "$PROJ" --gsd-bin "$stub" --json
  [ "$status" -eq 7 ]
  echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["ok"] is False, d
assert "remedy" in d and d["remedy"], d
'
}

# ─── The gsd-core manifest defect (upstream, open-gsd/gsd-core#2077) ─────────
#
# gsd-core declares the STANDARD hooks path in its own manifest. Claude Code
# loads that path automatically, so the declaration is a duplicate and the
# loader refuses the whole plugin — no /gsd:* commands at all. The capability
# checks cannot see it, because the gsd-tools CLI keeps working.

# A fake plugin install: <root>/.claude-plugin/plugin.json + <root>/hooks/ +
# a gsd_run at <root>/gsd-core/bin/. $1 = the hooks value, "" for none.
make_plugin_tree() {
  local root="$BATS_TEST_TMPDIR/plug" hooks="$1"
  mkdir -p "$root/.claude-plugin" "$root/hooks" "$root/gsd-core/bin"
  cp "$(make_gsd_stub core-active)" "$root/gsd-core/bin/gsd_run"
  chmod +x "$root/gsd-core/bin/gsd_run"
  printf '{"hooks":[]}\n' > "$root/hooks/hooks.json"
  python3 - "$root/.claude-plugin/plugin.json" "$hooks" <<'PY'
import json, sys, pathlib
d = {"name": "gsd-core", "version": "1.8.0", "commands": "./commands/gsd/"}
if sys.argv[2]:
    d["hooks"] = sys.argv[2]
pathlib.Path(sys.argv[1]).write_text(json.dumps(d, indent=2) + "\n")
PY
  printf '%s\n' "$root/gsd-core/bin/gsd_run"
}

manifest_hooks() {
  python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
print(d.get("hooks", "(absent)"))
' "$BATS_TEST_TMPDIR/plug/.claude-plugin/plugin.json"
}

@test "the redundant standard hooks declaration is detected and removed" {
  bin="$(make_plugin_tree './hooks/hooks.json')"
  run bash "$CAP_SH" repair-manifest --project-dir "$PROJ" --gsd-bin "$bin"
  [ "$status" -eq 0 ]
  assert_output_contains "removed the redundant hooks declaration"
  assert_output_contains "/reload-plugins"
  [ "$(manifest_hooks)" = "(absent)" ]
}

@test "the unprefixed spelling of the standard path is caught too" {
  bin="$(make_plugin_tree 'hooks/hooks.json')"
  run bash "$CAP_SH" repair-manifest --project-dir "$PROJ" --gsd-bin "$bin"
  [ "$status" -eq 0 ]
  [ "$(manifest_hooks)" = "(absent)" ]
}

@test "a manifest naming ADDITIONAL hook files is never touched" {
  # This is the field used correctly. Stripping it would break a working
  # plugin, which is worse than the defect being repaired.
  bin="$(make_plugin_tree './hooks/extra-hooks.json')"
  run bash "$CAP_SH" repair-manifest --project-dir "$PROJ" --gsd-bin "$bin"
  [ "$status" -eq 0 ]
  assert_output_contains "left alone"
  [ "$(manifest_hooks)" = "./hooks/extra-hooks.json" ]
}

@test "a declaration whose target does not exist is left alone" {
  bin="$(make_plugin_tree './hooks/hooks.json')"
  rm -f "$BATS_TEST_TMPDIR/plug/hooks/hooks.json"
  run bash "$CAP_SH" repair-manifest --project-dir "$PROJ" --gsd-bin "$bin"
  [ "$status" -eq 0 ]
  [ "$(manifest_hooks)" = "./hooks/hooks.json" ]
}

@test "repair is idempotent — a clean manifest reports and changes nothing" {
  bin="$(make_plugin_tree '')"
  run bash "$CAP_SH" repair-manifest --project-dir "$PROJ" --gsd-bin "$bin"
  [ "$status" -eq 0 ]
  assert_output_contains "declares no hooks path"
  [ "$(manifest_hooks)" = "(absent)" ]
}

@test "repair rewrites only the hooks key, leaving the rest of the manifest" {
  bin="$(make_plugin_tree './hooks/hooks.json')"
  run bash "$CAP_SH" repair-manifest --project-dir "$PROJ" --gsd-bin "$bin"
  [ "$status" -eq 0 ]
  python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
assert d["name"] == "gsd-core", d
assert d["version"] == "1.8.0", d
assert d["commands"] == "./commands/gsd/", d
assert "hooks" not in d, d
' "$BATS_TEST_TMPDIR/plug/.claude-plugin/plugin.json"
}

@test "detect reports an unloadable plugin, and install repairs it first" {
  bin="$(make_plugin_tree './hooks/hooks.json')"
  stage_bundle "$PROJ"
  run bash "$CAP_SH" detect --project-dir "$PROJ" --gsd-bin "$bin" --json
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["manifest_loadable"] is False, d
assert "refused" in d["manifest_detail"], d
'
  # install clears it on the way through, because a plugin that will not load
  # exposes no /gsd:* commands for the capability to attach to.
  run bash "$CAP_SH" install --project-dir "$PROJ" --gsd-bin "$bin" \
    --capability-dir "$BUNDLE"
  [ "$status" -eq 0 ]
  [ "$(manifest_hooks)" = "(absent)" ]
}

@test "with two copies of the same version, the repair lands on the loaded one" {
  # The cache can hold the same gsd-core twice, once per marketplace it was
  # installed from. Version-and-lineage ordering cannot break that tie, so a
  # repair could land on the copy nobody loads and leave the live plugin
  # broken. installed_plugins.json is the tiebreaker.
  command -v node >/dev/null 2>&1 || skip "node is not on PATH"
  home="$BATS_TEST_TMPDIR/home"
  cache="$home/.claude/plugins/cache"
  live="$cache/cairngo/gsd-core/1.8.0"
  dead="$cache/gsd-core/gsd-core/1.8.0"

  for root in "$live" "$dead"; do
    mkdir -p "$root/.claude-plugin" "$root/hooks" "$root/gsd-core/bin"
    printf '{"hooks":[]}\n' > "$root/hooks/hooks.json"
    printf '{"name":"gsd-core","hooks":"./hooks/hooks.json"}\n' \
      > "$root/.claude-plugin/plugin.json"
    cp "$(make_gsd_stub core-active)" "$root/gsd-core/bin/gsd_run"
    chmod +x "$root/gsd-core/bin/gsd_run"
  done

  mkdir -p "$home/.claude/plugins"
  cat > "$home/.claude/plugins/installed_plugins.json" <<EOF
{"plugins": {"gsd-core@cairngo": [{"scope": "user", "installPath": "$live"}]}}
EOF

  run env -u CAIRN_GSD_BIN -u CLAUDE_PLUGIN_ROOT HOME="$home" \
    PATH="/usr/bin:/bin:$(dirname "$(command -v node)")" \
    bash "$CAP_SH" repair-manifest --project-dir "$PROJ"
  [ "$status" -eq 0 ]

  live_hooks="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("hooks","(absent)"))' "$live/.claude-plugin/plugin.json")"
  dead_hooks="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("hooks","(absent)"))' "$dead/.claude-plugin/plugin.json")"
  [ "$live_hooks" = "(absent)" ]
  # The copy nobody loads is left exactly as it was.
  [ "$dead_hooks" = "./hooks/hooks.json" ]
}

# ─── Two GSD lineages on one machine ─────────────────────────────────────────
#
# The likeliest shape for anyone who had GSD before meeting cairn: they run the
# 4.x `gsd` plugin, install cairn, and cairn's dependency pulls `gsd-core` in
# beside it. Nothing errors, both provide the same workflow surface, and only
# one of them can host the capability.

# Write a fake installed_plugins.json under $1 (a HOME). $2... = plugin ids.
write_installed() {
  local home="$1"; shift
  mkdir -p "$home/.claude/plugins"
  python3 - "$home/.claude/plugins/installed_plugins.json" "$@" <<'PY'
import json, sys, pathlib
out = {"plugins": {k: [{"scope": "user"}] for k in sys.argv[2:]}}
pathlib.Path(sys.argv[1]).write_text(json.dumps(out, indent=2))
PY
}

@test "both GSD lineages installed is a failure, not a green board" {
  stub="$(make_gsd_stub core-active)"
  stage_bundle "$PROJ"
  home="$BATS_TEST_TMPDIR/h1"
  write_installed "$home" "gsd@cairngo" "gsd-core@cairngo"

  run env HOME="$home" bash "$CAP_SH" detect --project-dir "$PROJ" \
    --gsd-bin "$stub"
  [ "$status" -eq 7 ]
  assert_output_contains "both lineages installed"
  assert_output_contains "claude plugin uninstall gsd@cairngo"
}

@test "only gsd-core installed passes" {
  stub="$(make_gsd_stub core-active)"
  stage_bundle "$PROJ"
  home="$BATS_TEST_TMPDIR/h2"
  write_installed "$home" "gsd-core@cairngo"

  run env HOME="$home" bash "$CAP_SH" detect --project-dir "$PROJ" \
    --gsd-bin "$stub"
  [ "$status" -eq 0 ]
  assert_output_contains "fusion is active"
}

@test "an unreadable installed-plugins state does not invent a collision" {
  # Absent or corrupt state must not be read as "two lineages" — that would
  # fail every machine whose plugin state cairn cannot parse.
  stub="$(make_gsd_stub core-active)"
  stage_bundle "$PROJ"
  home="$BATS_TEST_TMPDIR/h3"
  mkdir -p "$home/.claude/plugins"
  printf 'not json at all\n' > "$home/.claude/plugins/installed_plugins.json"

  run env HOME="$home" bash "$CAP_SH" detect --project-dir "$PROJ" \
    --gsd-bin "$stub"
  [ "$status" -eq 0 ]
}

@test "--json reports the two lineages for scripting" {
  stub="$(make_gsd_stub core-active)"
  stage_bundle "$PROJ"
  home="$BATS_TEST_TMPDIR/h4"
  write_installed "$home" "gsd@cairngo" "gsd-core@cairngo"

  run env HOME="$home" bash "$CAP_SH" detect --project-dir "$PROJ" \
    --gsd-bin "$stub" --json
  [ "$status" -eq 7 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["both_lineages"] is True, d
assert d["installed_gsd"]["legacy"] == ["gsd@cairngo"], d
assert d["installed_gsd"]["core"] == ["gsd-core@cairngo"], d
assert d["ok"] is False, d
'
}
