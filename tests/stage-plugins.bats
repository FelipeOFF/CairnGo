#!/usr/bin/env bats
# stage-plugins.bats — exercises stage-plugins.py's provisioning
# materialization contract: pinned git clone + build + post-build MCP
# entrypoint syntax check, idempotent skip via .staged-ref, fail-loud on
# build/verification errors with nothing left at staged_path, and local_path
# verification — all against LOCAL git fixtures, no real network, $0.
#
# Network seam: stage-plugins.py always clones https://github.com/<repo>.git;
# the tests rewrite that URL prefix to a local bare fixture repo via git's
# url.<base>.insteadOf mechanism (GIT_CONFIG_* env vars), so the script under
# test is byte-identical to production and no request ever leaves the machine.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so positive substring checks use grep -qF and
# negative checks assert on file non-existence with `[ ! -e ... ]`.

load 'helpers'

BENCH_SCRIPTS_DIR="$CAIRN_REPO_ROOT/benchmarks/scripts"
STAGE_PLUGINS="$BENCH_SCRIPTS_DIR/stage-plugins.py"

setup() {
  # Rewrite https://github.com/ to the local fixture root for every git
  # subprocess the script spawns (and only for that URL prefix).
  export GIT_CONFIG_COUNT=1
  export GIT_CONFIG_KEY_0="url.file://$BATS_TEST_TMPDIR/src/.insteadOf"
  export GIT_CONFIG_VALUE_0="https://github.com/"
}

# make_fixture_plugin_repo [SERVER_JS] — build a local bare git repo at
# $BATS_TEST_TMPDIR/src/fixture/fixture.git tagged v0.0.1, carrying a trivial
# package.json (no dependencies), a .claude-plugin/plugin.json declaring a
# node MCP server, and mcp/server.cjs with SERVER_JS as its body (default:
# valid JS, so `node --check` passes).
make_fixture_plugin_repo() {
  # NB: no braces in the default value — a `}` inside ${1:-...} would
  # terminate the parameter expansion early.
  local server_body="${1:-module.exports = 0;}"
  local work="$BATS_TEST_TMPDIR/fixture-work"
  mkdir -p "$work/.claude-plugin" "$work/mcp"
  printf '{ "name": "fixture-plugin", "version": "0.0.1", "private": true }\n' \
    > "$work/package.json"
  cat > "$work/.claude-plugin/plugin.json" <<'EOF'
{
  "name": "fixture-plugin",
  "mcpServers": {
    "fixture": {
      "type": "stdio",
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/server.cjs"]
    }
  }
}
EOF
  printf '%s\n' "$server_body" > "$work/mcp/server.cjs"
  git -C "$work" init -q
  git -C "$work" -c user.name=fixture -c user.email=fixture@test add -A
  git -C "$work" -c user.name=fixture -c user.email=fixture@test \
    commit -qm "fixture plugin"
  git -C "$work" tag v0.0.1
  mkdir -p "$BATS_TEST_TMPDIR/src/fixture"
  git clone -q --bare "$work" "$BATS_TEST_TMPDIR/src/fixture/fixture.git"
}

# write_git_manifest BUILD_JSON — manifest with one git-type plugin_dirs
# entry pointing at the fixture repo. BUILD_JSON is the raw JSON contents of
# the build array (e.g. '"npm install --no-audit --no-fund"', '"false"', '').
write_git_manifest() {
  local build_json="$1"
  MANIFEST="$BATS_TEST_TMPDIR/fixture-manifest.json"
  STAGED="$BATS_TEST_TMPDIR/plugins/fixture/v0.0.1"
  cat > "$MANIFEST" <<EOF
{
  "name": "fixture-arm",
  "model": "claude-haiku-4-5-20251001",
  "claude_flags": {
    "bare": true,
    "max_turns": 8,
    "no_session_persistence": true,
    "permission_mode": "acceptEdits"
  },
  "provisioning": {
    "plugin_dirs": [
      {
        "plugin": "fixture",
        "source": { "type": "git", "repo": "fixture/fixture", "ref": "v0.0.1" },
        "staged_path": "$STAGED",
        "build": [$build_json]
      }
    ]
  }
}
EOF
}

@test "git-type entry: clones the pinned tag, runs the build, writes .staged-ref" {
  make_fixture_plugin_repo
  # The behavior contract is build=["npm install"]; --no-audit --no-fund only
  # guarantees the zero-dependency install never contacts the npm registry.
  write_git_manifest '"npm install --no-audit --no-fund"'
  run python3 "$STAGE_PLUGINS" --baseline "$MANIFEST"
  [ "$status" -eq 0 ]
  [ -f "$STAGED/package.json" ]
  [ -f "$STAGED/mcp/server.cjs" ]
  [ "$(cat "$STAGED/.staged-ref")" = "v0.0.1" ]
  echo "$output" | grep -qF "[stage-plugins] fixture-arm: 1 plugin(s) staged/verified"
  # No stray sibling temp dirs left behind next to the staged checkout.
  [ "$(ls -A "$BATS_TEST_TMPDIR/plugins/fixture" | wc -l | tr -d ' ')" = "1" ]
}

@test "second invocation is an idempotent skip: no re-clone even after the source repo is gone" {
  make_fixture_plugin_repo
  write_git_manifest ''
  run python3 "$STAGE_PLUGINS" --baseline "$MANIFEST"
  [ "$status" -eq 0 ]
  # Deleting the fixture source proves the second run cannot possibly clone.
  rm -rf "$BATS_TEST_TMPDIR/src"
  run python3 "$STAGE_PLUGINS" --baseline "$MANIFEST"
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF "fixture already staged at v0.0.1, skipping"
  [ "$(cat "$STAGED/.staged-ref")" = "v0.0.1" ]
}

@test "broken build command dies EXIT_USAGE and nothing appears at staged_path" {
  make_fixture_plugin_repo
  write_git_manifest '"false"'
  run python3 "$STAGE_PLUGINS" --baseline "$MANIFEST"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "staging 'fixture' failed at step"
  [ ! -e "$STAGED/.staged-ref" ]
  # Atomic rename-on-success: the failed attempt leaves NOTHING at
  # staged_path, and no sibling temp dir survives either.
  [ ! -e "$STAGED" ]
  [ -z "$(ls -A "$BATS_TEST_TMPDIR/plugins/fixture" 2>/dev/null)" ]
}

@test "missing local_path staged_path dies EXIT_USAGE before any git operation" {
  # Tripwire git: records the fact the script ever spawned git at all.
  mkdir -p "$BATS_TEST_TMPDIR/bin"
  cat > "$BATS_TEST_TMPDIR/bin/git" <<EOF
#!/usr/bin/env bash
touch "$BATS_TEST_TMPDIR/git-was-invoked"
exit 1
EOF
  chmod +x "$BATS_TEST_TMPDIR/bin/git"
  MANIFEST="$BATS_TEST_TMPDIR/local-manifest.json"
  cat > "$MANIFEST" <<EOF
{
  "name": "local-arm",
  "model": "claude-haiku-4-5-20251001",
  "claude_flags": {
    "bare": true,
    "max_turns": 8,
    "no_session_persistence": true,
    "permission_mode": "acceptEdits"
  },
  "provisioning": {
    "plugin_dirs": [
      {
        "plugin": "cairn",
        "source": { "type": "local_path", "path": "cairn" },
        "staged_path": "$BATS_TEST_TMPDIR/does-not-exist",
        "build": []
      }
    ]
  }
}
EOF
  run env PATH="$BATS_TEST_TMPDIR/bin:$PATH" \
    python3 "$STAGE_PLUGINS" --baseline "$MANIFEST"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "cairn"
  echo "$output" | grep -qF "not found"
  [ ! -e "$BATS_TEST_TMPDIR/git-was-invoked" ]
}

@test "syntactically broken MCP server entrypoint fails the post-build check, nothing staged" {
  make_fixture_plugin_repo 'function { this is not javascript'
  write_git_manifest ''
  run python3 "$STAGE_PLUGINS" --baseline "$MANIFEST"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "staging 'fixture' failed at step 'node --check"
  [ ! -e "$STAGED" ]
}
