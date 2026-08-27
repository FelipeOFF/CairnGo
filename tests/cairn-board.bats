#!/usr/bin/env bats
# cairn-board.bats — the live board's lifecycle (phase 48 / BOARD-01):
# start writes board.json and answers on 127.0.0.1, POST is 405, a second
# start reuses, a busy --port is exit 4, stop kills and cleans. Everything
# talks to the loopback only; nothing leaves the machine.

load 'helpers'

BOARD="$CAIRN_SCRIPTS_DIR/cairn-board.sh"

teardown() {
  if [ -n "${BOARD_ROOT:-}" ]; then
    bash "$BOARD" stop --project-dir "$BOARD_ROOT" >/dev/null 2>&1 || true
  fi
}

make_board_repo() {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD" brd
  BOARD_ROOT="$PWD"
}

@test "start serves the board on 127.0.0.1, records board.json, and /api/status is the status model" {
  make_board_repo

  run bash "$BOARD" start --project-dir "$BOARD_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.reused' 'false'
  local url pid port
  url="$(jq -r '.url' <<<"$output")"; pid="$(jq -r '.pid' <<<"$output")"; port="$(jq -r '.port' <<<"$output")"
  [[ "$url" == http://127.0.0.1:* ]]
  run jq -r '.pid' "$BOARD_ROOT/.cairn/board.json"
  [ "$output" = "$pid" ]
  kill -0 "$pid"

  run curl -s -o /dev/null -w '%{http_code}' "${url}healthz"
  [ "$output" = "200" ]
  run curl -s "${url}api/status"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.counts | has("ready")' 'true'
  assert_json_eq "$output" '.board.fetched_at | type' 'string'
  run curl -s -o /dev/null -w '%{http_code}' "$url"
  [ "$output" = "200" ]
  run curl -s -o /dev/null -w '%{http_code}' -X POST "${url}api/status"
  [ "$output" = "405" ]

  # A second start reuses the live server.
  run bash "$BOARD" start --project-dir "$BOARD_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.reused' 'true'
  assert_json_eq "$output" '.pid' "$pid"

  run bash "$BOARD" status --project-dir "$BOARD_ROOT" --json
  assert_json_eq "$output" '.running' 'true'

  run bash "$BOARD" stop --project-dir "$BOARD_ROOT"
  [ "$status" -eq 0 ]
  [ ! -e "$BOARD_ROOT/.cairn/board.json" ]
  sleep 0.3
  ! kill -0 "$pid" 2>/dev/null
}

@test "a busy --port is exit 4 and names the port; a dead pid in board.json is cleaned up on start" {
  make_board_repo
  local busy; busy="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')"
  # Hold the port for the duration of the assertion.
  python3 -c "import socket,time; s=socket.socket(); s.bind(('127.0.0.1',$busy)); s.listen(1); time.sleep(3)" &
  local holder=$!
  sleep 0.3
  run bash "$BOARD" start --project-dir "$BOARD_ROOT" --port "$busy"
  [ "$status" -eq 4 ]
  grep -qF "port $busy is busy" <<<"$output"
  kill "$holder" 2>/dev/null || true

  mkdir -p .cairn
  echo '{"port": 1, "pid": 999999, "url": "http://127.0.0.1:1/"}' > .cairn/board.json
  run bash "$BOARD" start --project-dir "$BOARD_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.reused' 'false'
  [ "$(jq -r '.pid' .cairn/board.json)" != "999999" ]
}

@test "stop with nothing running is a no-op, and a repo without .beads/ is refused" {
  make_tmp_repo
  BOARD_ROOT="$PWD"
  run bash "$BOARD" stop --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "nothing to stop" <<<"$output"
  run bash "$BOARD" start --project-dir "$PWD"
  [ "$status" -eq 2 ]
  grep -qF "no .beads/" <<<"$output"
}

@test "the page is the board plus the live blocks and the poller; a held lease shows under now; buttons copy commands" {
  make_board_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-lease.sh" acquire 2 --project-dir "$BOARD_ROOT" >/dev/null
  run bash "$BOARD" start --project-dir "$BOARD_ROOT" --json
  [ "$status" -eq 0 ]
  local url; url="$(jq -r '.url' <<<"$output")"

  run curl -s "$url"
  [ "$status" -eq 0 ]
  grep -qF '<title>cairn: live board</title>' <<<"$output"
  grep -qF 'id="live-status"' <<<"$output"
  grep -qF 'id="live-attention"' <<<"$output"
  grep -qF 'id="live-now"' <<<"$output"
  grep -qF 'id="live-jira"' <<<"$output"
  grep -qF 'id="live-commands"' <<<"$output"
  grep -qF "fetch('/api/status'" <<<"$output"
  # The board region itself is there — the same renderer as --html.
  grep -qF 'class="lanes"' <<<"$output"
  # The held lease is what "now" shows.
  grep -qF 'phase 2</span>' <<<"$output"
  # A ready row carries the exact bd command to copy.
  grep -qF "data-cmd=\"bd update $BD_STANDALONE --claim\"" <<<"$output"
  # No external resource: no http(s) URL loaded by the page.
  ! grep -qE '(src|href)="https?://' <<<"$output"

  run curl -s "${url}api/fragment"
  [ "$status" -eq 0 ]
  grep -qF 'id="live-now"' <<<"$output"
}

# --------------------------------------------------------------------------- #
# actions — the panel writes through the CLIs (phase 49 / ACT-01, ACT-02)
# --------------------------------------------------------------------------- #

post_action() {  # post_action <url> <json> [extra curl args...]
  local url="$1" body="$2"; shift 2
  curl -s -o "$BATS_TEST_TMPDIR/resp.json" -w '%{http_code}' -X POST \
    -H 'Content-Type: application/json' "$@" --data "$body" "${url}api/action"
}

@test "POST /api/action: claim and close run the CLI as board, log a line, and the next poll sees it" {
  make_board_repo
  run bash "$BOARD" start --project-dir "$BOARD_ROOT" --json
  [ "$status" -eq 0 ]
  local url; url="$(jq -r '.url' <<<"$output")"

  run post_action "$url" "{\"action\":\"claim\",\"id\":\"$BD_STANDALONE\"}"
  [ "$output" = "200" ]
  assert_json_eq "$(cat "$BATS_TEST_TMPDIR/resp.json")" '.ok' 'true'
  run bd show "$BD_STANDALONE" --json
  grep -qF '"status": "in_progress"' <<<"$output"
  grep -qF '"assignee": "board"' <<<"$output"
  grep -qF "action claim $BD_STANDALONE exit 0 actor board" "$BOARD_ROOT/.cairn/board.log"
  run curl -s "${url}api/status"
  assert_json_eq "$output" '.counts.doing' '1'

  # close needs a reason; with one, it closes.
  run post_action "$url" "{\"action\":\"close\",\"id\":\"$BD_STANDALONE\"}"
  [ "$output" = "400" ]
  grep -qF "close needs a reason" "$BATS_TEST_TMPDIR/resp.json"
  run post_action "$url" "{\"action\":\"close\",\"id\":\"$BD_STANDALONE\",\"reason\":\"done from the board\"}"
  [ "$output" = "200" ]
  run bd show "$BD_STANDALONE" --json
  grep -qF '"status": "closed"' <<<"$output"
  # reopen undoes it.
  run post_action "$url" "{\"action\":\"reopen\",\"id\":\"$BD_STANDALONE\"}"
  [ "$output" = "200" ]
  run bd show "$BD_STANDALONE" --json
  grep -qF '"status": "open"' <<<"$output"

  # A CLI refusal is 409 with the reason, not a crash.
  run post_action "$url" "{\"action\":\"claim\",\"id\":\"$BD_CHILD_CLOSED\"}"
  [ "$output" = "409" ]
  assert_json_eq "$(cat "$BATS_TEST_TMPDIR/resp.json")" '.ok' 'false'
  # An id that is not one is 400, and never reaches a shell.
  run post_action "$url" '{"action":"claim","id":"x; rm -rf /"}'
  [ "$output" = "400" ]
  run post_action "$url" '{"action":"explode","id":"brd-1"}'
  [ "$output" = "400" ]
}

@test "POST /api/action is refused from another origin or host, and a local curl without Origin passes" {
  make_board_repo
  run bash "$BOARD" start --project-dir "$BOARD_ROOT" --json
  local url port; url="$(jq -r '.url' <<<"$output")"; port="$(jq -r '.port' <<<"$output")"

  run post_action "$url" '{"action":"gate-check"}' -H "Origin: http://evil.example:$port"
  [ "$output" = "403" ]
  run post_action "$url" '{"action":"gate-check"}' -H "Origin: http://127.0.0.1:1"
  [ "$output" = "403" ]
  run post_action "$url" '{"action":"gate-check"}' -H "Host: evil.example:$port"
  [ "$output" = "403" ]
  run post_action "$url" '{"action":"gate-check"}' -H "Origin: http://127.0.0.1:$port"
  [ "$output" = "200" ]
  run post_action "$url" '{"action":"gate-check"}' -H "Origin: http://localhost:$port" -H "Host: localhost:$port"
  [ "$output" = "200" ]
  run post_action "$url" '{"action":"gate-check"}'
  [ "$output" = "200" ]
  # GET stays free of the check.
  run curl -s -o /dev/null -w '%{http_code}' -H "Origin: http://evil.example" "${url}api/status"
  [ "$output" = "200" ]
}

@test "an action mirrors through gbsync when a sync config exists, and releases a lease by key" {
  make_board_repo
  local stub log; stub="$BATS_TEST_TMPDIR/gbsync.sh"; log="$BATS_TEST_TMPDIR/gbsync.log"
  printf '#!/usr/bin/env bash\nprintf "CALL: %%s\\n" "$*" >> "%s"\necho "[gbsync] ok"\n' "$log" > "$stub"; chmod +x "$stub"
  mkdir -p .cairn && echo '{"backends": []}' > .cairn/sync.json
  bash "$CAIRN_SCRIPTS_DIR/cairn-lease.sh" acquire 2 --project-dir "$BOARD_ROOT" >/dev/null
  run env CAIRN_GBSYNC="$stub" bash "$BOARD" start --project-dir "$BOARD_ROOT" --json
  local url; url="$(jq -r '.url' <<<"$output")"

  run post_action "$url" "{\"action\":\"claim\",\"id\":\"$BD_STANDALONE\"}"
  [ "$output" = "200" ]
  assert_json_eq "$(cat "$BATS_TEST_TMPDIR/resp.json")" '.mirror.ok' 'true'
  grep -qF "CALL: update $BD_STANDALONE --dir" "$log"

  run post_action "$url" '{"action":"lease-release","id":"2"}'
  [ "$output" = "200" ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-lease.sh" status 2 --project-dir "$BOARD_ROOT" --json
  assert_json_eq "$output" '.held' 'false'
  # The page carries the action controls.
  run curl -s "$url"
  grep -qF 'class="act" data-action="claim"' <<<"$output"
  grep -qF 'class="why"' <<<"$output"
}

@test "stop from the board writes the flag, releases the lease, and the now block says so until cleared" {
  make_board_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-lease.sh" acquire 2 --project-dir "$BOARD_ROOT" >/dev/null
  run bash "$BOARD" start --project-dir "$BOARD_ROOT" --json
  local url; url="$(jq -r '.url' <<<"$output")"
  run curl -s "$url"
  grep -qF 'data-action="stop" data-id="2"' <<<"$output"

  run post_action "$url" '{"action":"stop","id":"2","reason":"enough for today"}'
  [ "$output" = "200" ]
  assert_json_eq "$(cat "$BATS_TEST_TMPDIR/resp.json")" '.lease_released' 'true'
  run jq -r '.phase + " " + .actor' "$BOARD_ROOT/.cairn/stop"
  [ "$output" = "2 board" ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-lease.sh" status 2 --project-dir "$BOARD_ROOT" --json
  assert_json_eq "$output" '.held' 'false'
  run curl -s "${url}api/fragment"
  grep -qF 'stop requested' <<<"$output"
  grep -qF 'enough for today' <<<"$output"

  run post_action "$url" '{"action":"stop-clear"}'
  [ "$output" = "200" ]
  [ ! -f "$BOARD_ROOT/.cairn/stop" ]
}
