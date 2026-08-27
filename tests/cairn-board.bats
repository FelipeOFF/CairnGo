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
