#!/usr/bin/env bats
# gbsync.bats — exercises the gbsync dispatcher's --dry-run contract through
# the real CLI (gbsync.py / the gbsync.sh wrapper): it walks the push/pull
# decision logic, prints one 'DRY-RUN:' line per would-be operation, exits 0,
# and never calls an adapter or writes id-map.json / state.json /
# conflicts.json under .cairn/.
#
# The import tests swap the adapters directory for a stub via the
# CAIRN_ADAPTERS_DIR env-var seam (same CAIRN_* stub pattern as CAIRN_GBSYNC /
# CAIRN_MAP in hooks.bats): a canned jira.py that logs each invocation and
# emits two fixed items. The no-credentials test runs the REAL jira adapter
# with the env vars unset — it must fail loud, naming them, before any network.

load 'helpers'

# Write a minimal .cairn/sync.json (github backend enabled) into the current
# repo. GH_TOKEN is a dummy on purpose: dry-run must never reach the gh CLI
# or the network, so a fake token must be harmless.
make_sync_config() {
  mkdir -p .cairn
  cat > .cairn/sync.json <<'EOF'
{
  "backends": [
    { "type": "github", "enabled": true, "adapter": "github",
      "config": { "repo": "example/fixture", "extra_labels": [] } }
  ]
}
EOF
  export GH_TOKEN="dummy-not-a-real-token"
}

@test "gbsync push --dry-run prints DRY-RUN lines, exits 0, writes no state" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_sync_config

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$BD_EPIC" --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [ "$output" = "DRY-RUN: github create $BD_EPIC -> (new)" ]

  [ ! -e .cairn/id-map.json ]
  [ ! -e .cairn/state.json ]
  [ ! -e .cairn/conflicts.json ]
}

@test "gbsync push --dry-run emits only DRY-RUN-prefixed lines" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_sync_config

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" update "$BD_STANDALONE" --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [ -n "$output" ]
  local line
  while IFS= read -r line; do
    case "$line" in
      DRY-RUN:*) ;;
      *) echo "unexpected non-DRY-RUN line: $line" >&2; return 1 ;;
    esac
  done <<< "$output"
}

@test "gbsync pull --dry-run lists mapped items and advances no watermark" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_sync_config
  printf '{ "%s": { "github": "42" } }\n' "$BD_EPIC" > .cairn/id-map.json
  local before
  before="$(cat .cairn/id-map.json)"

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" pull --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [ "$output" = "DRY-RUN: github pull $BD_EPIC <- 42 (since 1970-01-01T00:00:00Z)" ]

  # No watermark, no conflicts log, and the id-map is byte-identical.
  [ ! -e .cairn/state.json ]
  [ ! -e .cairn/conflicts.json ]
  [ "$(cat .cairn/id-map.json)" = "$before" ]
}

# Write a jira-backend sync.json (real adapter name; the stub tests override
# the lookup directory, not the config).
make_jira_sync_config() {
  mkdir -p .cairn
  cat > .cairn/sync.json <<'EOF'
{
  "backends": [
    { "type": "jira", "enabled": true, "adapter": "jira",
      "config": { "base_url": "https://example.atlassian.net",
                  "project_key": "CHN" } }
  ]
}
EOF
}

# Canned-output adapter stub on the CAIRN_ADAPTERS_DIR seam: appends every
# received event to calls.log (so tests can assert it was / was not invoked)
# and answers "import" with two fixed normalized items.
make_import_stub_adapter() {
  STUB_ADAPTERS_DIR="$BATS_TEST_TMPDIR/adapters"
  mkdir -p "$STUB_ADAPTERS_DIR"
  cat > "$STUB_ADAPTERS_DIR/jira.py" <<'EOF'
#!/usr/bin/env python3
import json, os, sys
event = json.load(sys.stdin)
with open(os.path.join(os.path.dirname(__file__), "calls.log"), "a") as fh:
    fh.write(json.dumps(event) + "\n")
if event.get("action") != "import":
    print(f"stub: unexpected action {event.get('action')}", file=sys.stderr)
    sys.exit(1)
print(json.dumps([
    {"external_id": "CHN-1", "title": "Imported card one", "body": "first body",
     "status": "open", "updated_at": "2026-01-01T00:00:00Z"},
    {"external_id": "CHN-2", "title": "Imported card two", "body": "second body",
     "status": "closed", "updated_at": "2026-01-02T00:00:00Z"},
]))
EOF
  export CAIRN_ADAPTERS_DIR="$STUB_ADAPTERS_DIR"
}

@test "gbsync import creates bd issues, seeds the id-map, and re-runs idempotently" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_jira_sync_config
  make_import_stub_adapter

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"
  [ "$status" -eq 0 ]
  [[ "$output" == *"created=2 skipped=0 failed=0"* ]]

  # id-map maps both external ids to freshly minted bd ids.
  local idmap bd1 bd2
  idmap="$(cat .cairn/id-map.json)"
  bd1="$(jq -r 'to_entries[] | select(.value.jira=="CHN-1") | .key' <<<"$idmap")"
  bd2="$(jq -r 'to_entries[] | select(.value.jira=="CHN-2") | .key' <<<"$idmap")"
  [ -n "$bd1" ] && [ "$bd1" != "null" ]
  [ -n "$bd2" ] && [ "$bd2" != "null" ]

  # bd issues carry the imported title/body and the statusCategory-mapped status.
  local one two
  one="$(bd show "$bd1" --json | jq 'if type=="array" then .[0] else . end')"
  two="$(bd show "$bd2" --json | jq 'if type=="array" then .[0] else . end')"
  assert_json_eq "$one" '.title' "Imported card one"
  assert_json_eq "$one" '.description' "first body"
  assert_json_eq "$one" '.status' "open"
  assert_json_eq "$two" '.title' "Imported card two"
  assert_json_eq "$two" '.status' "closed"

  # Re-run: already-mapped external ids are skipped, nothing is duplicated.
  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"
  [ "$status" -eq 0 ]
  [[ "$output" == *"created=0 skipped=2 failed=0"* ]]
  [ "$(jq 'length' .cairn/id-map.json)" -eq 2 ]
}

# One item whose title is a bd FLAG: the argument-injection regression.
# Passed positionally, 'bd create -- help' printed its help and exited 0, and
# the whole help text was stored as the bd id in id-map.json.
make_flag_title_stub_adapter() {
  STUB_ADAPTERS_DIR="$BATS_TEST_TMPDIR/adapters-flag"
  mkdir -p "$STUB_ADAPTERS_DIR"
  cat > "$STUB_ADAPTERS_DIR/jira.py" <<'EOF'
#!/usr/bin/env python3
import json, sys
json.load(sys.stdin)
print(json.dumps([
    {"external_id": "CHN-666", "title": "--help", "body": "hostile title",
     "status": "open", "updated_at": "2026-01-01T00:00:00Z"},
]))
EOF
  export CAIRN_ADAPTERS_DIR="$STUB_ADAPTERS_DIR"
}

@test "gbsync import treats a '--help' title as a title, never as a bd flag" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_jira_sync_config
  make_flag_title_stub_adapter
  local before
  before="$(bd list --all -n 0 --json | jq 'length')"

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "created=1 skipped=0 failed=0" <<<"$output"
  # bd's help text never reached stdout — the flag was never parsed as one.
  if grep -qF "Create a new issue" <<<"$output"; then
    echo "bd help leaked into the import output" >&2
    return 1
  fi

  # Exactly one new issue, carrying the literal title.
  [ "$(bd list --all -n 0 --json | jq 'length')" -eq "$((before + 1))" ]
  local bd_id
  bd_id="$(jq -r 'to_entries[] | select(.value.jira=="CHN-666") | .key' .cairn/id-map.json)"
  [ -n "$bd_id" ] && [ "$bd_id" != "null" ]
  assert_json_eq "$(bd show "$bd_id" --json)" '.[0].title' '--help'

  # The id-map key is a real single-token bd id, not a captured help dump.
  [ "$(jq -r 'keys | length' .cairn/id-map.json)" -eq 1 ]
  [ "${#bd_id}" -lt 32 ]
  case "$bd_id" in
    *[[:space:]]*) echo "id-map key holds whitespace: $bd_id" >&2; return 1 ;;
  esac

  # Re-run is a clean skip (the mapping points at a REAL issue, so the card
  # is not marked imported-forever against a phantom id).
  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "created=0 skipped=1 failed=0" <<<"$output"
}

@test "gbsync import --dry-run invokes no adapter and writes no state" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_jira_sync_config
  make_import_stub_adapter

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [ "$output" = "DRY-RUN: jira import project CHN -> bd create + id-map entries" ]

  [ ! -e "$STUB_ADAPTERS_DIR/calls.log" ]   # adapter never ran
  [ ! -e .cairn/id-map.json ]
  [ ! -e .cairn/state.json ]
  [ ! -e .cairn/conflicts.json ]
}

@test "gbsync import without credentials fails loud, naming the env vars" {
  make_tmp_repo
  make_jira_sync_config
  # Real jira adapter (no CAIRN_ADAPTERS_DIR override), credentials unset:
  # the adapter must exit before any network call, naming both env vars.
  run env -u CAIRN_ADAPTERS_DIR -u JIRA_EMAIL -u JIRA_API_TOKEN \
      python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"
  [ "$status" -ne 0 ]
  [[ "$output" == *"JIRA_EMAIL"* ]]
  [[ "$output" == *"JIRA_API_TOKEN"* ]]
  [ ! -e .cairn/id-map.json ]
}

# A free localhost port with nothing listening on it (bind, read, release).
free_port() {
  python3 -c 'import socket
s = socket.socket(); s.bind(("127.0.0.1", 0))
print(s.getsockname()[1]); s.close()'
}

# Write a jira sync.json pointing base_url at a local port.
make_jira_sync_config_at() {
  mkdir -p .cairn
  cat > .cairn/sync.json <<EOF
{
  "backends": [
    { "type": "jira", "enabled": true, "adapter": "jira",
      "config": { "base_url": "http://127.0.0.1:$1",
                  "project_key": "CHN" } }
  ]
}
EOF
}

# Socket that accepts a connection and then never writes a byte: the only
# way to prove the adapter's request timeout is real. Killed by the caller.
start_hung_server() {
  HUNG_PORT_FILE="$BATS_TEST_TMPDIR/hung-port"
  rm -f "$HUNG_PORT_FILE" "$HUNG_PORT_FILE.tmp"
  python3 - "$HUNG_PORT_FILE" >/dev/null 2>&1 <<'PYEOF' &
import os, socket, sys
srv = socket.socket()
srv.bind(("127.0.0.1", 0))
srv.listen(8)
with open(sys.argv[1] + ".tmp", "w") as fh:
    fh.write(str(srv.getsockname()[1]))
os.rename(sys.argv[1] + ".tmp", sys.argv[1])
held = []
while True:
    held.append(srv.accept()[0])
PYEOF
  HUNG_PID=$!
  local i
  for i in $(seq 1 40); do
    [ -s "$HUNG_PORT_FILE" ] && break
    sleep 0.1
  done
  HUNG_PORT="$(cat "$HUNG_PORT_FILE")"
}

@test "jira import: a hung endpoint times out cleanly, bounded, with no traceback" {
  make_tmp_repo
  start_hung_server
  [ -n "$HUNG_PORT" ]
  make_jira_sync_config_at "$HUNG_PORT"

  # Real adapter (no CAIRN_ADAPTERS_DIR override) with credentials present,
  # so it gets past cfg_auth and all the way to the socket.
  local t0=$SECONDS
  run env -u CAIRN_ADAPTERS_DIR JIRA_EMAIL=fixture@example.com \
      JIRA_API_TOKEN=dummy-not-a-real-token CAIRN_JIRA_TIMEOUT=1 \
      python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"
  kill "$HUNG_PID" 2>/dev/null || true
  wait "$HUNG_PID" 2>/dev/null || true

  [ "$status" -eq 2 ]                      # adapter failure -> import exit 2
  [ $((SECONDS - t0)) -lt 20 ]             # bounded: it did not hang
  grep -qF "timed out after 1s" <<<"$output"
  if grep -qF "Traceback" <<<"$output"; then
    echo "adapter leaked a traceback instead of failing clean" >&2
    return 1
  fi
  [ ! -e .cairn/id-map.json ]
}

@test "jira import: an unreachable endpoint fails clean, no traceback" {
  make_tmp_repo
  make_jira_sync_config_at "$(free_port)"   # nothing is listening there

  run env -u CAIRN_ADAPTERS_DIR JIRA_EMAIL=fixture@example.com \
      JIRA_API_TOKEN=dummy-not-a-real-token \
      python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"
  [ "$status" -eq 2 ]
  grep -qF "connection failed" <<<"$output"
  if grep -qF "Traceback" <<<"$output"; then
    echo "adapter leaked a traceback instead of failing clean" >&2
    return 1
  fi
  [ ! -e .cairn/id-map.json ]
}

@test "jira import: a project key carrying JQL operators is refused before any request" {
  make_tmp_repo
  make_jira_sync_config_at "$(free_port)"

  run env -u CAIRN_ADAPTERS_DIR JIRA_EMAIL=fixture@example.com \
      JIRA_API_TOKEN=dummy-not-a-real-token \
      python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import \
      --project 'CHN OR assignee is not EMPTY' --dir "$PWD"
  [ "$status" -eq 2 ]
  grep -qF "invalid project key" <<<"$output"
  # Refused by the validator, not by the (unreachable) endpoint.
  if grep -qF "connection failed" <<<"$output"; then
    echo "the malformed key reached the network" >&2
    return 1
  fi
}

@test "gbsync: a value-taking flag with no value is a usage error, not a traceback" {
  make_tmp_repo
  make_jira_sync_config

  local flag
  for flag in --query --project --backend --since --dir; do
    run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import "$flag"
    [ "$status" -ne 0 ]
    grep -qF -- "$flag needs a value" <<<"$output"
    grep -qF "usage: gbsync.py" <<<"$output"
    if grep -qF "Traceback" <<<"$output"; then
      echo "$flag without a value raised instead of dying" >&2
      return 1
    fi
  done
}

@test "gbsync import requires exactly one of --query / --project" {
  make_tmp_repo
  make_jira_sync_config
  make_import_stub_adapter

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --dir "$PWD"
  [ "$status" -ne 0 ]
  [[ "$output" == *"exactly one of --query"* ]]

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import \
      --query 'project = CHN' --project CHN --dir "$PWD"
  [ "$status" -ne 0 ]
  [[ "$output" == *"exactly one of --query"* ]]
}

@test "gbsync.sh wrapper forwards --dry-run to the dispatcher" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_sync_config

  run bash "$CAIRN_SCRIPTS_DIR/gbsync.sh" update "$BD_EPIC" --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  case "$output" in
    DRY-RUN:*) ;;
    *) echo "output does not start with DRY-RUN:: $output" >&2; return 1 ;;
  esac

  [ ! -e .cairn/id-map.json ]
  [ ! -e .cairn/state.json ]
  [ ! -e .cairn/conflicts.json ]
}

# Three items, and a bd shim that hard-kills the importer (SIGKILL, so no
# handler and no finally block runs) once two of them exist. This is the
# interrupted import: a laptop closing, a CI job cancelled, a crash.
make_kill_midway_stub() {
  STUB_ADAPTERS_DIR="$BATS_TEST_TMPDIR/adapters-kill"
  mkdir -p "$STUB_ADAPTERS_DIR"
  cat > "$STUB_ADAPTERS_DIR/jira.py" <<'EOF'
#!/usr/bin/env python3
import json, sys
json.load(sys.stdin)
print(json.dumps([
    {"external_id": "CHN-1", "title": "One", "body": "b", "status": "open",
     "updated_at": "2026-01-01T00:00:00Z"},
    {"external_id": "CHN-2", "title": "Two", "body": "b", "status": "open",
     "updated_at": "2026-01-01T00:00:00Z"},
    {"external_id": "CHN-3", "title": "Three", "body": "b", "status": "open",
     "updated_at": "2026-01-01T00:00:00Z"},
]))
EOF
  export CAIRN_ADAPTERS_DIR="$STUB_ADAPTERS_DIR"

  SHIM_DIR="$BATS_TEST_TMPDIR/shim"
  mkdir -p "$SHIM_DIR"
  REAL_BD="$(command -v bd)"
  cat > "$SHIM_DIR/bd" <<EOF
#!/usr/bin/env bash
# Count only 'create' calls; on the third, kill the importer outright.
if [ "\$1" = "create" ]; then
  n=\$(cat "$BATS_TEST_TMPDIR/creates" 2>/dev/null || echo 0)
  n=\$((n + 1)); echo "\$n" > "$BATS_TEST_TMPDIR/creates"
  if [ "\$n" -ge 3 ]; then kill -9 \$PPID; sleep 5; exit 137; fi
fi
exec "$REAL_BD" "\$@"
EOF
  chmod +x "$SHIM_DIR/bd"
  export PATH="$SHIM_DIR:$PATH"
}

@test "gbsync import survives being killed midway: what it created stays mapped" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_jira_sync_config
  make_kill_midway_stub

  # The importer is SIGKILLed during the third create. Its exit status is not
  # the point; what it left behind is.
  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"

  # The two issues that were created before the kill are in the map. Writing
  # the map once at the end left this file absent or empty, so the "safe to
  # re-run" contract created every one of them a second time.
  [ -f .cairn/id-map.json ]
  [ "$(jq 'length' .cairn/id-map.json)" -eq 2 ]
  jq -e 'to_entries | map(.value.jira) | index("CHN-1")' .cairn/id-map.json >/dev/null
  jq -e 'to_entries | map(.value.jira) | index("CHN-2")' .cairn/id-map.json >/dev/null

  # Re-running with the shim disarmed finishes the job instead of duplicating
  # it: the two known ones are skipped, only the third is created.
  rm -f "$BATS_TEST_TMPDIR/creates"
  export PATH="${PATH#"$BATS_TEST_TMPDIR/shim":}"
  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"
  [ "$status" -eq 0 ]
  [[ "$output" == *"created=1 skipped=2 failed=0"* ]]
  [ "$(jq 'length' .cairn/id-map.json)" -eq 3 ]
}

# ─── GUARD-01: every adapter's network call is bounded ───────────────────────
#
# _contract.md states it as a MUST: a request with no timeout hangs the whole
# dispatcher on one dead socket, and a traceback is a contract violation.
# jira.py obeyed it; asana, azure-boards, github and gitlab did not.
#
# The behavioural tests below run the adapter DIRECTLY against something that
# really hangs. That distinction is the whole point: every stub adapter and
# stub `gh` elsewhere in this suite answers instantly, and an instant answer
# cannot tell a bounded call from an unbounded one. The structural test at the
# end is the negative control — it fails the moment any `timeout=` is dropped.

adapter_path() { echo "$CAIRN_REPO_ROOT/cairn/adapters/$1"; }

@test "gitlab adapter: a hung endpoint times out cleanly, bounded, no traceback" {
  make_tmp_repo
  start_hung_server
  [ -n "$HUNG_PORT" ]

  local t0=$SECONDS
  run env GITLAB_TOKEN=dummy-not-a-real-token CAIRN_GITLAB_TIMEOUT=1 \
      python3 "$(adapter_path gitlab.py)" <<EOF
{"action":"create","bd_id":"tst-1","title":"t","body":"b","status":"open",
 "labels":[],"external_id":null,
 "config":{"base_url":"http://127.0.0.1:$HUNG_PORT","project":"ns/proj"}}
EOF
  kill "$HUNG_PID" 2>/dev/null || true
  wait "$HUNG_PID" 2>/dev/null || true

  [ "$status" -eq 1 ]
  [ $((SECONDS - t0)) -lt 20 ]             # bounded: it did not hang
  grep -qF "timed out after 1s" <<<"$output"
  if grep -qF "Traceback" <<<"$output"; then
    echo "gitlab leaked a traceback instead of failing clean" >&2
    return 1
  fi
}

@test "gitlab adapter: an unreachable endpoint fails clean, no traceback" {
  make_tmp_repo
  local port
  port="$(free_port)"                      # nothing is listening there
  run env GITLAB_TOKEN=dummy-not-a-real-token \
      python3 "$(adapter_path gitlab.py)" <<EOF
{"action":"create","bd_id":"tst-1","title":"t","body":"b","status":"open",
 "labels":[],"external_id":null,
 "config":{"base_url":"http://127.0.0.1:$port","project":"ns/proj"}}
EOF
  [ "$status" -eq 1 ]
  grep -qF "connection failed" <<<"$output"
  if grep -qF "Traceback" <<<"$output"; then
    echo "gitlab leaked a traceback instead of failing clean" >&2
    return 1
  fi
}

@test "azure-boards adapter: a hung endpoint times out cleanly, no traceback" {
  make_tmp_repo
  start_hung_server
  [ -n "$HUNG_PORT" ]

  local t0=$SECONDS
  run env AZURE_DEVOPS_PAT=dummy-not-a-real-token CAIRN_AZURE_TIMEOUT=1 \
      python3 "$(adapter_path azure-boards.py)" <<EOF
{"action":"create","bd_id":"tst-1","title":"t","body":"b","status":"open",
 "labels":[],"external_id":null,
 "config":{"org_url":"http://127.0.0.1:$HUNG_PORT","project":"Fixture"}}
EOF
  kill "$HUNG_PID" 2>/dev/null || true
  wait "$HUNG_PID" 2>/dev/null || true

  [ "$status" -eq 1 ]
  [ $((SECONDS - t0)) -lt 20 ]
  grep -qF "timed out after 1s" <<<"$output"
  if grep -qF "Traceback" <<<"$output"; then
    echo "azure-boards leaked a traceback instead of failing clean" >&2
    return 1
  fi
}

@test "github adapter: a hung gh times out cleanly, bounded, no traceback" {
  make_tmp_repo
  # github.py shells out to `gh`, so what hangs is the CLI, not a socket — a
  # stub that sleeps is the same dead-socket shape seen from the adapter.
  mkdir -p "$BATS_TEST_TMPDIR/hang-bin"
  printf '#!/bin/sh\nsleep 120\n' > "$BATS_TEST_TMPDIR/hang-bin/gh"
  chmod +x "$BATS_TEST_TMPDIR/hang-bin/gh"

  local t0=$SECONDS
  run env PATH="$BATS_TEST_TMPDIR/hang-bin:$PATH" CAIRN_GITHUB_TIMEOUT=1 \
      python3 "$(adapter_path github.py)" <<'EOF'
{"action":"create","bd_id":"tst-1","title":"t","body":"b","status":"open",
 "labels":[],"external_id":null,"config":{"repo":"example/fixture"}}
EOF
  [ "$status" -eq 1 ]
  [ $((SECONDS - t0)) -lt 20 ]
  grep -qF "timed out after 1s" <<<"$output"
  if grep -qF "Traceback" <<<"$output"; then
    echo "github leaked a traceback instead of failing clean" >&2
    return 1
  fi
}

@test "github adapter: a missing gh fails clean, no traceback" {
  make_tmp_repo
  mkdir -p "$BATS_TEST_TMPDIR/empty-bin"
  # An empty PATH hides `gh` — and python3 with it, which would make the shell
  # exit 127 and prove nothing. The interpreter is named absolutely so the
  # only thing missing is the tool under test.
  local py
  py="$(command -v python3)"
  run env PATH="$BATS_TEST_TMPDIR/empty-bin" \
      "$py" "$(adapter_path github.py)" <<'EOF'
{"action":"create","bd_id":"tst-1","title":"t","body":"b","status":"open",
 "labels":[],"external_id":null,"config":{"repo":"example/fixture"}}
EOF
  [ "$status" -eq 1 ]
  grep -qF "could not run gh" <<<"$output"
  if grep -qF "Traceback" <<<"$output"; then
    echo "github leaked a traceback when gh was absent" >&2
    return 1
  fi
}

@test "every adapter network call carries an explicit timeout (negative control)" {
  # THE NEGATIVE CONTROL. An AST scan of every adapter asserting each
  # urlopen()/subprocess.run() site passes `timeout=`. Breaks by: deleting one
  # `timeout=` — which is the exact state four of these five files shipped in,
  # and which no test driving an instant stub could ever have noticed.
  # asana.py's endpoint is a hardcoded constant with no local address to point
  # at, so this scan is the ONLY thing standing under it; the behavioural
  # proof above covers the same api() shape in gitlab and azure-boards.
  run python3 - "$CAIRN_REPO_ROOT/cairn/adapters" <<'PY'
import ast, pathlib, sys

bad, seen = [], 0
for path in sorted(pathlib.Path(sys.argv[1]).glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        f = node.func if isinstance(node, ast.Call) else None
        if not isinstance(f, ast.Attribute) or f.attr not in ("urlopen", "run"):
            continue
        root = f.value                    # subprocess.run / urllib.request.urlopen
        while isinstance(root, ast.Attribute):
            root = root.value
        if not (isinstance(root, ast.Name)
                and root.id in ("subprocess", "urllib")):
            continue
        seen += 1
        if not any(kw.arg == "timeout" for kw in node.keywords):
            bad.append(f"{path.name}:{node.lineno} {f.attr}() has no timeout=")
if seen < 5:
    print(f"the scan found only {seen} network call sites across the five "
          "adapters — the scan is broken, not the code", file=sys.stderr)
    sys.exit(2)
if bad:
    print("\n".join(bad), file=sys.stderr)
    sys.exit(1)
print(f"ok: {seen} adapter network call sites, all bounded")
PY
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]
}

# --------------------------------------------------------------------------- #
# refresh-map — the id-map is derived from external_ref (phase 44 / LINK-02)
# --------------------------------------------------------------------------- #

@test "refresh-map derives id-map entries from external_ref, and the bead wins over the file" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD"
  make_jira_sync_config
  bd update "$BD_EPIC" --external-ref jira-CHN-42 >/dev/null
  bd update "$BD_CHILD_OPEN" --external-ref gh-7 >/dev/null
  # A stale cache entry that disagrees with the bead.
  printf '{"%s": {"jira": "CHN-1"}}\n' "$BD_EPIC" > .cairn/id-map.json

  run bash "$CAIRN_SCRIPTS_DIR/gbsync.sh" refresh-map --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  grep -qF "DRY-RUN: refresh-map would rewrite 1 entry" <<<"$output"
  grep -qF '"CHN-1"' .cairn/id-map.json

  run bash "$CAIRN_SCRIPTS_DIR/gbsync.sh" refresh-map --dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "1 entry derived from external_ref" <<<"$output"
  run jq -r --arg id "$BD_EPIC" '.[$id].jira' .cairn/id-map.json
  [ "$output" = "CHN-42" ]
  # gh-7 names a backend that is not enabled here: not mapped.
  run jq -r --arg id "$BD_CHILD_OPEN" '.[$id]' .cairn/id-map.json
  [ "$output" = "null" ]
}

# --------------------------------------------------------------------------- #
# the hierarchy model — spec=Epic, ticket=Story, m-v*=Fix Version (v5)
# --------------------------------------------------------------------------- #

# A jira backend in the hierarchy model, pointed at a stub adapter that logs
# every event and answers a create with a fresh key.
make_hierarchy_jira() {
  mkdir -p .cairn
  cat > .cairn/sync.json <<'JSON'
{"backends": [{"type": "jira", "enabled": true, "adapter": "jira", "model": "hierarchy",
  "config": {"base_url": "https://example.atlassian.net", "project_key": "CHN",
             "issue_types": {"spec": "Epic", "ticket": "Story"}}}]}
JSON
  STUB_ADAPTERS_DIR="$BATS_TEST_TMPDIR/adapters"
  mkdir -p "$STUB_ADAPTERS_DIR"
  cat > "$STUB_ADAPTERS_DIR/jira.py" <<'PY'
#!/usr/bin/env python3
import json, os, sys
event = json.load(sys.stdin)
with open(os.path.join(os.path.dirname(__file__), "calls.log"), "a") as fh:
    fh.write(json.dumps(event) + "\n")
if event["action"] == "create":
    print("CHN-9" if event.get("level") == "spec" else "CHN-10")
else:
    print(event.get("external_id") or "")
PY
  export CAIRN_ADAPTERS_DIR="$STUB_ADAPTERS_DIR"
}

make_v5_beads() {
  bd init -q --prefix hy --non-interactive >/dev/null 2>&1
  HY_SPEC="$(bd create "The spec" -t epic -l m-v1.0,ready-for-agent \
    --metadata '{"cairn":{"kind":"spec"}}' --silent)"
  HY_TICKET="$(bd create "A ticket" -t task --parent "$HY_SPEC" \
    -l m-v1.0,ready-for-agent \
    --metadata '{"cairn":{"kind":"ticket"}}' --silent)"
  HY_STRAY="$(bd create "untyped stray" -t task --silent)"
}

@test "hierarchy: a bead that is not spec or ticket is skipped" {
  require_bd
  make_tmp_repo
  make_hierarchy_jira
  make_v5_beads

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$HY_STRAY" --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [ "$output" = "DRY-RUN: jira skip $HY_STRAY (not a spec or ticket)" ]

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$HY_STRAY" --dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "not a spec or ticket" <<<"$output"
  [ ! -e "$STUB_ADAPTERS_DIR/calls.log" ]
}

@test "hierarchy: a spec goes up as an Epic, Fix Version from m-v*, key lands on the bead" {
  require_bd
  make_tmp_repo
  make_hierarchy_jira
  make_v5_beads

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$HY_SPEC" --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [ "$output" = "DRY-RUN: jira create $HY_SPEC -> (new) [spec, parent (none), fix v1.0]" ]

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$HY_SPEC" --dir "$PWD"
  [ "$status" -eq 0 ]
  run jq -r '.level' "$STUB_ADAPTERS_DIR/calls.log"
  [ "$output" = "spec" ]
  run jq -r '.fix_versions[0]' "$STUB_ADAPTERS_DIR/calls.log"
  [ "$output" = "v1.0" ]
  grep -qF '"external_ref": "jira-CHN-9"' <<<"$(bd show "$HY_SPEC" --json)"
  run jq -r --arg id "$HY_SPEC" '.[$id].jira' .cairn/id-map.json
  [ "$output" = "CHN-9" ]
}

@test "hierarchy: a ticket needs the spec linked first, then goes up under the Epic" {
  require_bd
  make_tmp_repo
  make_hierarchy_jira
  make_v5_beads

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$HY_TICKET" --dir "$PWD"
  [ "$status" -eq 2 ]
  grep -qF "ticket with no parent: link the spec first" <<<"$output"
  [ ! -e "$STUB_ADAPTERS_DIR/calls.log" ]

  bd update "$HY_SPEC" --external-ref jira-CHN-9 >/dev/null
  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$HY_TICKET" --dir "$PWD"
  [ "$status" -eq 0 ]
  run jq -r '.level + " " + .parent' "$STUB_ADAPTERS_DIR/calls.log"
  [ "$output" = "ticket CHN-9" ]
  grep -qF '"external_ref": "jira-CHN-10"' <<<"$(bd show "$HY_TICKET" --json)"
}

@test "hierarchy: bd dep is passed as blocked_by on the ticket create" {
  require_bd
  make_tmp_repo
  make_hierarchy_jira
  make_v5_beads
  HY_BLOCKER="$(bd create "blocker ticket" -t task --parent "$HY_SPEC" \
    -l m-v1.0 --metadata '{"cairn":{"kind":"ticket"}}' --silent)"
  bd dep add "$HY_TICKET" "$HY_BLOCKER" >/dev/null
  bd update "$HY_SPEC" --external-ref jira-CHN-9 >/dev/null
  bd update "$HY_BLOCKER" --external-ref jira-CHN-8 >/dev/null

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$HY_TICKET" --dir "$PWD"
  [ "$status" -eq 0 ]
  run jq -r '.blocked_by[0]' "$STUB_ADAPTERS_DIR/calls.log"
  [ "$output" = "CHN-8" ]
}

@test "hierarchy: import refuses (exit 2) and points at linking the bead" {
  require_bd
  make_tmp_repo
  make_hierarchy_jira
  make_v5_beads

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" import --project CHN --dir "$PWD"
  [ "$status" -eq 2 ]
  grep -qF "external_ref" <<<"$output"
  [ ! -e "$STUB_ADAPTERS_DIR/calls.log" ]
}

@test "hierarchy: a comment reaches the linked card with its text; unlinked, it is skipped" {
  require_bd
  make_tmp_repo
  make_hierarchy_jira
  make_v5_beads

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" comment "$HY_SPEC" --text "Plano 01 registrado: x" --dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "not linked — nothing to comment on" <<<"$output"
  [ ! -e "$STUB_ADAPTERS_DIR/calls.log" ]

  bd update "$HY_SPEC" --external-ref jira-CHN-9 >/dev/null
  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" comment "$HY_SPEC" --text "Plano 01 registrado: x" --dir "$PWD"
  [ "$status" -eq 0 ]
  run jq -r '.action + "|" + .external_id + "|" + .text' "$STUB_ADAPTERS_DIR/calls.log"
  [ "$output" = "comment|CHN-9|Plano 01 registrado: x" ]

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" comment "$HY_STRAY" --text "nope" --dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "not a spec or ticket" <<<"$output"
}

@test "hierarchy: with no credentials in the shell the write is QUEUED on the bead, not attempted" {
  require_bd
  make_tmp_repo
  make_hierarchy_jira
  make_v5_beads
  python3 - <<'PY'
import json
p = ".cairn/sync.json"; d = json.load(open(p))
d["backends"][0]["config"].update({"email_env": "HY_EMAIL", "token_env": "HY_TOKEN"})
json.dump(d, open(p, "w"))
PY
  bd update "$HY_SPEC" --external-ref jira-CHN-9 >/dev/null

  run env -u HY_EMAIL -u HY_TOKEN python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" close "$HY_SPEC" --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  grep -qF "(queued: no credentials)" <<<"$output"

  run env -u HY_EMAIL -u HY_TOKEN python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" close "$HY_SPEC" --dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "close queued on the bead (no HY_EMAIL/HY_TOKEN in the shell)" <<<"$output"
  [ ! -e "$STUB_ADAPTERS_DIR/calls.log" ]
  run env -u HY_EMAIL -u HY_TOKEN python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" comment "$HY_SPEC" --text "Fechado: done" --dir "$PWD"
  [ "$status" -eq 0 ]

  local meta; meta="$(bd show "$HY_SPEC" --json | jq -c '.[0].metadata.gsd.mirror.pending')"
  [ "$(jq 'length' <<<"$meta")" = "2" ]
  [ "$(jq -r '.[0].action + " " + .[0].key + " " + .[0].backend' <<<"$meta")" = "close CHN-9 jira" ]
  [ "$(jq -r '.[1].text' <<<"$meta")" = "Fechado: done" ]

  run env HY_EMAIL=x HY_TOKEN=y python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" close "$HY_SPEC" --dir "$PWD"
  [ "$status" -eq 0 ]
  run jq -r '.action' "$STUB_ADAPTERS_DIR/calls.log"
  [ "$output" = "close" ]
}

@test "hierarchy: pull records what the tracker shows under state.json seen, and touches no bead" {
  require_bd
  make_tmp_repo
  make_hierarchy_jira
  make_v5_beads
  bd update "$HY_SPEC" --external-ref jira-CHN-9 >/dev/null
  cat > "$STUB_ADAPTERS_DIR/jira.py" <<'PY'
#!/usr/bin/env python3
import json, sys
event = json.load(sys.stdin)
assert event["action"] == "pull", event
print(json.dumps([{"bd_id": it["bd_id"], "external_id": it["external_id"],
                   "title": "renamed in jira", "body": "rewritten", "status": "closed",
                   "updated_at": "2099-01-01T00:00:00Z"} for it in event["items"]]))
PY

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" pull --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  grep -qF "DRY-RUN: jira pull $HY_SPEC <- CHN-9 (read only: seen)" <<<"$output"

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" pull --dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "seen=1 (read only" <<<"$output"
  run jq -r '.seen.jira["CHN-9"].status + " " + .seen.jira["CHN-9"].bd_id' .cairn/state.json
  [ "$output" = "closed $HY_SPEC" ]
  local shown; shown="$(bd show "$HY_SPEC" --json)"
  grep -qF '"status": "open"' <<<"$shown"
  grep -qF 'The spec' <<<"$shown"
  [ ! -e .cairn/conflicts.json ]
}
