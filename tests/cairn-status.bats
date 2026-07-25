#!/usr/bin/env bats
# cairn-status.bats — exercises the status board renderer's CLI contract
# (cairn-status.py / the cairn-status.sh wrapper): the box-drawing kanban
# board, graceful width degradation (columns → stacked → raw list), the
# machine formats (--json, --plain, non-TTY default), --brief, color
# suppression (NO_COLOR / --color), --ascii, and the documented exit codes
# (0 ok, 2 usage, 5 bd unavailable).
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so substring checks use grep -qF and negative
# checks use refute_in_output.

load 'helpers'

# Assert NEEDLE does not appear in $output. (`! grep` cannot be used inline:
# bash's `!` suppresses errexit, so its failure would never fail the test.)
refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# Deterministic board fixture on top of make_gsd_fixture (active_phase 2,
# next_action execute-phase, no milestone):
#   ST_READY1   p1, phase-2 — blocks ST_BLOCKED, so it also feeds the ⧗ chain
#   ST_READY2   p2, phase-2
#   ST_DOING    p1, phase-2, in_progress, assignee felipe
#   ST_BLOCKED  phase-2, blocked by ST_READY1
#   ST_CLOSED   phase-1, closed (the done count)
# Callers must require_bd and make_tmp_repo first.
make_status_fixture() {
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  ST_BLOCKED="$(bd create "Docs index page" -t task -l phase-2,m-v1.0 --silent)"
  ST_READY1="$(bd create "Gate regex hardening" -t task -p 1 -l phase-2,m-v1.0 \
    --deps "blocks:$ST_BLOCKED" --silent)"
  ST_READY2="$(bd create "Timeout tuning" -t task -p 2 -l phase-2,m-v1.0 --silent)"
  ST_DOING="$(bd create "Status board renderer" -t task -p 1 -l phase-2,m-v1.0 --silent)"
  bd update "$ST_DOING" --status in_progress -a felipe >/dev/null
  ST_CLOSED="$(bd create "Login handler" -t task -l phase-1,m-v1.0 --silent)"
  bd close "$ST_CLOSED" >/dev/null
}

@test "board at --width 100: lanes, glyphs, footer, next action" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 0 ]

  # One shared grid in light box-drawing with lane headers + counts.
  grep -qF '┌─ READY (2)' <<<"$output"
  grep -qF '┬─ DOING (1)' <<<"$output"
  grep -qF '┬─ BLOCKED (1)' <<<"$output"
  grep -qF '└─' <<<"$output"

  # Cards: id + title; ◆ assignee on DOING; ⧗ blocking dep on BLOCKED.
  grep -qF "$ST_READY1  Gate regex hardening" <<<"$output"
  grep -qF "$ST_READY2  Timeout tuning" <<<"$output"
  grep -qF "$ST_DOING" <<<"$output"
  grep -qF '◆ felipe' <<<"$output"
  grep -qF "⧗ $ST_READY1" <<<"$output"

  # Footer outside the grid: GSD position, done count, ONE next action.
  grep -qF 'phase 2/2' <<<"$output"
  grep -qF 'done: 1' <<<"$output"
  grep -qF "▶ next: continue $ST_DOING" <<<"$output"

  # The closed issue never appears as a card.
  refute_in_output "$ST_CLOSED"
}

@test "long titles are truncated with an ellipsis inside the cell" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  bd create "An enormously long issue title that cannot possibly fit inside one board cell" \
    -t task --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 0 ]
  grep -qF '…' <<<"$output"
  refute_in_output "cannot possibly fit inside one board cell"
}

@test "long id prefixes are truncated so the grid stays aligned" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix an-extremely-long-project-prefix-name \
    --non-interactive >/dev/null 2>&1
  bd create "Long prefix issue" -t task --silent >/dev/null

  # --ascii keeps every grid character single-byte, so byte length == width.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100 --ascii
  [ "$status" -eq 0 ]
  grep -qF '...' <<<"$output"
  # Every bordered grid line (starts with + or |) has the same width.
  [ "$(grep -E '^[+|]' <<<"$output" | awk '{ print length }' \
      | sort -u | wc -l | tr -d ' ')" -eq 1 ]
}

@test "--max-rows caps a lane and shows the +k more overflow row" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100 --max-rows 1
  [ "$status" -eq 0 ]
  grep -qF '+1 more' <<<"$output"
  refute_in_output "$ST_READY2"
}

@test "--json prints one machine line: lanes, counts, phase, next" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
  assert_json_eq "$output" '.counts.ready' '2'
  assert_json_eq "$output" '.counts.doing' '1'
  assert_json_eq "$output" '.counts.blocked' '1'
  assert_json_eq "$output" '.counts.closed' '1'
  assert_json_eq "$output" '.phase.active' '2'
  assert_json_eq "$output" '.phase.total' '2'
  assert_json_eq "$output" '.phase.completed' '1'
  assert_json_eq "$output" '.milestone' 'null'
  assert_json_eq "$output" '.next.kind' 'continue'
  assert_json_eq "$output" '.next.id' "$ST_DOING"
  assert_json_eq "$output" '.ready[0].id' "$ST_READY1"
  assert_json_eq "$output" '.blocked[0].blocked_by[0]' "$ST_READY1"
  assert_json_eq "$output" '.sync.configured' 'false'
  refute_in_output '│'
}

@test "--brief is exactly three lines: position, counts, next" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --brief
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 3 ]
  grep -qF '[cairn-status] phase 2/2' <<<"${lines[0]}"
  grep -qF 'ready 2 · doing 1 · blocked 1 · done 1' <<<"${lines[1]}"
  grep -qF "next: continue $ST_DOING" <<<"${lines[2]}"
}

@test "non-TTY without flags defaults to --plain: tabs, no box, no escapes" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  # bats captures a pipe, so this run IS non-TTY — the gh model applies.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh"
  [ "$status" -eq 0 ]
  grep -qF "$(printf 'READY\t%s\t1\tGate regex hardening' "$ST_READY1")" <<<"$output"
  grep -qF "$(printf 'DOING\t%s\t1\tStatus board renderer\tfelipe' "$ST_DOING")" <<<"$output"
  grep -qF "$(printf 'BLOCKED\t%s\t2\tDocs index page\t%s' "$ST_BLOCKED" "$ST_READY1")" <<<"$output"
  grep -qF "$(printf 'PHASE\t2/2')" <<<"$output"
  grep -qF "$(printf 'DONE\t1')" <<<"$output"
  grep -qF "$(printf 'NEXT\tcontinue')" <<<"$output"
  refute_in_output '│'
  refute_in_output "$(printf '\x1b')"

  # Explicit --plain is byte-identical to the non-TTY default.
  local piped="$output"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --plain
  [ "$status" -eq 0 ]
  [ "$output" = "$piped" ]
}

@test "titles are never truncated in plain mode" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  bd create "An enormously long issue title that cannot possibly fit inside one board cell" \
    -t task --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --plain
  [ "$status" -eq 0 ]
  grep -qF 'cannot possibly fit inside one board cell' <<<"$output"
  refute_in_output '…'
}

@test "--width 50 degrades to stacked lanes (no grid, headers kept)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 50
  [ "$status" -eq 0 ]
  grep -qF 'READY (2)' <<<"$output"
  grep -qF 'DOING (1)' <<<"$output"
  grep -qF 'BLOCKED (1)' <<<"$output"
  grep -qF "▶ next: continue $ST_DOING" <<<"$output"
  refute_in_output '┌'
  refute_in_output '│'
}

@test "--width 30 degrades to the raw LANE id title list" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 30
  [ "$status" -eq 0 ]
  grep -qF "READY  $ST_READY1  Gate regex hardening" <<<"$output"
  grep -qF "DOING  $ST_DOING  Status board renderer" <<<"$output"
  grep -qF "BLOCKED  $ST_BLOCKED  Docs index page" <<<"$output"
  refute_in_output '┌'
  refute_in_output '│'
}

@test "color: --color=always emits SGR; NO_COLOR strips it; the flag wins" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100 --color=always
  [ "$status" -eq 0 ]
  grep -qF "$(printf '\x1b[')" <<<"$output"

  run env NO_COLOR=1 bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 0 ]
  refute_in_output "$(printf '\x1b')"

  # Precedence: an explicit --color=always overrides NO_COLOR.
  run env NO_COLOR=1 bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" \
    --width 100 --color=always
  [ "$status" -eq 0 ]
  grep -qF "$(printf '\x1b[')" <<<"$output"
}

@test "color precedence: CAIRN_NO_COLOR, TERM=dumb, empty NO_COLOR, --color=never" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  # CAIRN_NO_COLOR — the tool's own kill switch, above NO_COLOR.
  run env CAIRN_NO_COLOR=1 bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 0 ]
  refute_in_output "$(printf '\x1b')"

  # The explicit flag beats TERM=dumb (and an unset-but-empty NO_COLOR).
  run env TERM=dumb NO_COLOR= bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" \
    --width 100 --color=always
  [ "$status" -eq 0 ]
  grep -qF "$(printf '\x1b[')" <<<"$output"

  # Empty NO_COLOR must not disable color (no-color.org: present AND
  # non-empty). Only approximable without a pty: the flag-forced board
  # still carries SGR with NO_COLOR="" in the environment.
  run env NO_COLOR="" bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" \
    --width 100 --color=always
  [ "$status" -eq 0 ]
  grep -qF "$(printf '\x1b[')" <<<"$output"

  # --color=never suppresses SGR in an otherwise color-friendly context.
  run env TERM=xterm-256color bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" \
    --width 100 --color=never
  [ "$status" -eq 0 ]
  refute_in_output "$(printf '\x1b')"
}

@test "--color=always piped without --width opts into the board renderer" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  # A piped run would default to --plain; --color=always must never be
  # silently ignored, so it forces the board renderer (like --width does).
  # SGR paints each span separately, so grep the border and the header text
  # on their own rather than as one contiguous string.
  run env COLUMNS=100 bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --color=always
  [ "$status" -eq 0 ]
  grep -qF '┌' <<<"$output"
  grep -qF 'READY (2)' <<<"$output"
  grep -qF "$(printf '\x1b[')" <<<"$output"
}

@test "--ascii swaps the borders, ellipsis, and glyphs" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100 --ascii
  [ "$status" -eq 0 ]
  grep -qF '+- READY (2)' <<<"$output"
  grep -qF '> next: continue' <<<"$output"
  grep -qF '@ felipe' <<<"$output"
  refute_in_output '┌'
  refute_in_output '▶'
  refute_in_output '…'
}

@test "no phase-labeled ready work falls back to STATE.md's workflow step" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  # Issues WITHOUT phase labels: bd has ready work, but none of it belongs
  # to the active phase — STATE.md wins for workflow steps.
  make_bd_fixture "$PWD"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.next.kind' 'workflow'
  assert_json_eq "$output" '.next.text' 'execute-phase (phase 2)'
}

@test "configured but never-pulled sync surfaces a staleness line" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture
  mkdir -p .cairn
  echo '{"backends": []}' > .cairn/sync.json

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 0 ]
  grep -qF 'sync: never pulled — run /cairn:sync-pull' <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.sync.configured' 'true'
  assert_json_eq "$output" '.sync.stale' 'true'
}

@test "usage errors exit 2" {
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --nope
  [ "$status" -eq 2 ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width abc
  [ "$status" -eq 2 ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json --brief
  [ "$status" -eq 2 ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --color sometimes
  [ "$status" -eq 2 ]
}

@test "bd missing from PATH exits 5" {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  local stub="$BATS_TEST_TMPDIR/nobd-bin"
  mkdir -p "$stub"
  # Link the real interpreter (not a version-manager shim needing PATH).
  ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$stub/python3"
  ln -s "$(command -v bash)" "$stub/bash"
  ln -s "$(command -v dirname)" "$stub/dirname"

  run env PATH="$stub" "$stub/bash" "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 5 ]
}

@test "--planning-dir pointed at another checkout renders THAT repo, not the cwd's" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture
  local target_repo="$CAIRN_TMP_REPO"

  # A second bd repo becomes the cwd; its issues must never leak into the
  # target repo's board (the renderer pins bd to the planning dir's parent).
  make_tmp_repo
  bd init -q --prefix other --non-interactive >/dev/null 2>&1
  local stray
  stray="$(bd create "Stray issue from the wrong repo" -t task --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100 \
    --planning-dir "$target_repo/.planning"
  [ "$status" -eq 0 ]
  grep -qF "$ST_READY1" <<<"$output"
  grep -qF 'phase 2/2' <<<"$output"
  refute_in_output "$stray"
}

@test "bd-only repo without .planning degrades to an issues-only board" {
  require_bd
  make_tmp_repo
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  local solo
  solo="$(bd create "Solo issue" -t task --silent)"

  # The board footer always carries the done count, so the roadmap-less
  # marker only shows in --brief (which omits it); here assert done: 0.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 0 ]
  grep -qF "$solo" <<<"$output"
  grep -qF 'done: 0' <<<"$output"
  grep -qF "▶ next: start $solo" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --brief
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 3 ]
  grep -qF '(no roadmap position)' <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --plain
  [ "$status" -eq 0 ]
  refute_in_output "$(printf 'PHASE\t')"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.phase.total' 'null'
  assert_json_eq "$output" '.phase.active' 'null'
  assert_json_eq "$output" '.next.kind' 'ready'
}

@test "GSD repo without .beads degrades to a GSD-only board with a note" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  # No bd init: bd would walk UP to an ancestor database — the board must
  # not query bd at all (cairn-gate's applicability decision, mirrored).

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 0 ]
  grep -qF 'READY (0)' <<<"$output"
  grep -qF 'no .beads/' <<<"$output"
  grep -qF '▶ next: execute-phase (phase 2)' <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --plain
  [ "$status" -eq 0 ]
  grep -qF "$(printf 'NOTE\tno .beads/')" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.counts.ready' '0'
  assert_json_eq "$output" '.next.kind' 'workflow'
  [ "$(jq -r '.note' <<<"$output")" != "null" ]
}

@test "control bytes in titles cannot inject escapes or forge rows" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  local evil
  evil="$(bd create "$(printf 'x\033[31my\nREADY\tfake\t0\tz')" \
    -t task -p 0 -l phase-2 --silent)"

  # --plain: zero escape bytes, and the embedded newline/tabs never become
  # a forged lane row — every line still starts with a known tag.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --plain
  [ "$status" -eq 0 ]
  refute_in_output "$(printf '\x1b')"
  refute_in_output "$(printf '\tfake\t')"
  [ "$(grep -c $'^READY\t' <<<"$output")" -eq 1 ]
  local tag_re=$'^(READY|DOING|BLOCKED|PHASE|MILESTONE|DONE|NEXT|SYNC|NOTE)\t'
  [ "$(grep -Evc "$tag_re" <<<"$output" || true)" -eq 0 ]
  grep -qF "$(printf 'NEXT\tstart %s' "$evil")" <<<"$output"

  # Board render (non-TTY, no color): still zero escape bytes.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 0 ]
  refute_in_output "$(printf '\x1b')"

  # --brief stays exactly three lines even with \n inside the next title.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --brief
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 3 ]
}
