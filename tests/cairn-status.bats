#!/usr/bin/env bats
# cairn-status.bats — exercises the status board renderer's CLI contract
# (cairn-status.py / the cairn-status.sh wrapper): the box-drawing kanban
# board, graceful width degradation (columns → stacked → raw list), the
# machine formats (--json, --plain, non-TTY default), --brief, color
# suppression (NO_COLOR / --color), the --html board (marker-scoped
# regeneration, escaping, zero network), and the documented exit codes
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

BOARD_START='<!-- cairn:generated:board:start -->'
BOARD_END='<!-- cairn:generated:board:end -->'

# Print everything OUTSIDE the generated board region of FILE, both markers
# included. This is the half of the file the user owns; regeneration must
# leave it byte for byte alone.
board_outside() {
  awk '/cairn:generated:board:start/ { print; inside = 1; next }
       /cairn:generated:board:end/   { inside = 0 }
       !inside                        { print }' "$1"
}

# Print only the generated region of FILE (markers excluded).
board_inside() {
  awk '/cairn:generated:board:end/   { inside = 0 }
       inside                         { print }
       /cairn:generated:board:start/ { inside = 1 }' "$1"
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

@test "open issues in roadmap-complete phases: lane marker + footer warning" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  # Phase 1 is [x] in the fixture ROADMAP — this p0 straggler is stale.
  local stale live
  stale="$(bd create "Leftover auth polish" -t task -p 0 -l phase-1 --silent)"
  live="$(bd create "Rate limit middleware" -t task -p 2 -l phase-2 --silent)"

  # NO_COLOR-safe: marker and warning survive as plain text, zero escapes.
  run env NO_COLOR=1 bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100
  [ "$status" -eq 0 ]
  refute_in_output "$(printf '\x1b')"
  # The stale issue keeps its lane (data is data) but carries the marker;
  # the live issue does not (exactly one marked card on the board).
  grep -qF "$stale" <<<"$output"
  grep -qF '·done-phase' <<<"$output"
  [ "$(grep -cF '·done-phase' <<<"$output")" -eq 1 ]
  grep -qF '1 open issue(s) belong to roadmap-complete phases. run /cairn:doctor --close-completed' <<<"$output"
  # next picks the active-phase issue, never the delivered-phase one.
  grep -qF "▶ next: start $live" <<<"$output"
  refute_in_output "start $stale"

  # --ascii swaps the marker glyph along with everything else.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100 --ascii
  [ "$status" -eq 0 ]
  grep -qF '*done-phase' <<<"$output"
  refute_in_output '·'
}

@test "--json exposes stale_complete and the ready fallback skips delivered phases" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  # No STATE.md: no active phase and no workflow step, so the OVERALL
  # ready fallback is the pick under test — it used to hand back the
  # highest-priority issue even when its phase was already delivered.
  rm .planning/STATE.md
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  local stale live
  stale="$(bd create "Leftover auth polish" -t task -p 0 -l phase-1 --silent)"
  live="$(bd create "Rate limit middleware" -t task -p 2 -l phase-2 --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
  assert_json_eq "$output" '.stale_complete | length' '1'
  assert_json_eq "$output" '.stale_complete[0]' "$stale"
  assert_json_eq "$output" '.next.kind' 'ready'
  assert_json_eq "$output" '.next.id' "$live"
  # The stale issue still ships in the ready lane payload.
  assert_json_eq "$output" ".ready | map(.id) | contains([\"$stale\"])" 'true'
}

@test "active_phase pointing at a roadmap-complete phase falls back to the workflow step" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  # STATE.md lagging the roadmap (active_phase 1, but ROADMAP marks phase 1
  # complete): the phase-labeled pick must not resurrect a delivered phase.
  sed -i.bak 's/^active_phase: "2"/active_phase: "1"/' .planning/STATE.md
  rm .planning/STATE.md.bak
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  local stale
  stale="$(bd create "Leftover auth polish" -t task -p 0 -l phase-1 --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.next.kind' 'workflow'
  assert_json_eq "$output" '.next.text' 'execute-phase (phase 1)'
  assert_json_eq "$output" '.stale_complete[0]' "$stale"

  # --plain carries the warning as a NOTE meta row.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --plain
  [ "$status" -eq 0 ]
  grep -qF "$(printf 'NOTE\t1 open issue(s) belong to roadmap-complete phases')" <<<"$output"
}

# ------------------------------------------------------------------- --html

@test "--html seeds a standalone page from the template, with the markers" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]
  grep -qF 'wrote' <<<"$output"
  [ -f board.html ]

  run cat board.html
  # A whole document, not a fragment: doctype, both html tags, inline styles.
  grep -qF '<!DOCTYPE html>' <<<"$output"
  grep -qF '<html lang="en">' <<<"$output"
  grep -qF '</html>' <<<"$output"
  grep -qF '<style>' <<<"$output"
  grep -qF '</style>' <<<"$output"
  grep -qF "$BOARD_START" <<<"$output"
  grep -qF "$BOARD_END" <<<"$output"
  # The board itself: three lanes, the issues, the one next action.
  grep -qF '>ready</h2>' <<<"$output"
  grep -qF '>doing</h2>' <<<"$output"
  grep -qF '>blocked</h2>' <<<"$output"
  grep -qF 'Gate regex hardening' <<<"$output"
  grep -qF "$ST_DOING" <<<"$output"
  grep -qF 'claimed by felipe' <<<"$output"
  grep -qF "waiting on $ST_READY1" <<<"$output"
  # The template placeholder was replaced, not left behind.
  refute_in_output 'no board rendered yet'
  # The closed issue is a card nowhere (it only feeds the profile + count).
  refute_in_output "$ST_CLOSED"
}

@test "--html profile: terrain from real per-phase counts, cairn on the active phase" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]

  run cat board.html
  grep -qF 'class="terrain-mass"' <<<"$output"
  grep -qF 'class="cairn-stack"' <<<"$output"
  grep -qF 'roadmap profile: 2 phases, standing at phase 2' <<<"$output"
  # Elevation is data: phase 1 carries the one closed issue, phase 2 the four
  # open ones. Phase 1 is [x] in the ROADMAP, phase 2 is where we stand.
  grep -qF '<span class="tick is-done"><span class="tick-n">01</span><span class="tick-c">1</span></span>' <<<"$output"
  grep -qF '<span class="tick is-here"><span class="tick-n">02</span><span class="tick-c">4</span></span>' <<<"$output"
}

@test "--html regeneration rewrites ONLY the generated region" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]
  board_outside board.html > "$BATS_TEST_TMPDIR/outside-1"
  board_inside board.html > "$BATS_TEST_TMPDIR/inside-1"

  # State moves on: a new claimable issue appears.
  local fresh
  fresh="$(bd create "Terrain smoothing pass" -t task -p 1 -l phase-2,m-v1.0 --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]
  board_outside board.html > "$BATS_TEST_TMPDIR/outside-2"
  board_inside board.html > "$BATS_TEST_TMPDIR/inside-2"

  # Everything outside the markers is untouched — proven by diff, then by a
  # byte-level compare (diff is line-based and would miss trailing bytes).
  run diff -u "$BATS_TEST_TMPDIR/outside-1" "$BATS_TEST_TMPDIR/outside-2"
  [ "$status" -eq 0 ]
  run cmp "$BATS_TEST_TMPDIR/outside-1" "$BATS_TEST_TMPDIR/outside-2"
  [ "$status" -eq 0 ]

  # …and the generated region really did move to the new state.
  run cmp -s "$BATS_TEST_TMPDIR/inside-1" "$BATS_TEST_TMPDIR/inside-2"
  [ "$status" -ne 0 ]
  run cat "$BATS_TEST_TMPDIR/inside-2"
  grep -qF "$fresh" <<<"$output"
  grep -qF 'Terrain smoothing pass' <<<"$output"
  run cat "$BATS_TEST_TMPDIR/inside-1"
  refute_in_output "$fresh"
}

@test "--html preserves the user's own edits outside the markers" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]

  # The user retitles the page, restyles a token and leaves a note below the
  # board — all outside the markers, all theirs.
  sed -i.bak 's|<title>cairn: status board</title>|<title>trail head</title>|' board.html
  sed -i.bak 's|--amber:     #D98A3A;|--amber:     #4FB8A0;|' board.html
  sed -i.bak "s|</main>|</main>\n<p id=\"mine\">my own note, hands off</p>|" board.html
  rm -f board.html.bak

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]

  run cat board.html
  grep -qF '<title>trail head</title>' <<<"$output"
  # `--` first: the pattern itself starts with dashes.
  grep -qF -- '--amber:     #4FB8A0;' <<<"$output"
  grep -qF '<p id="mine">my own note, hands off</p>' <<<"$output"
  refute_in_output '<title>cairn: status board</title>'
  # The board itself still regenerated inside the markers.
  grep -qF 'Gate regex hardening' <<<"$output"
}

@test "--html escapes issue text: markup in a title cannot execute" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  bd create '<script>alert(1)</script> tea & scones <img src=x onerror=alert(2)>' \
    -t task -p 0 -l phase-2 --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]

  run cat board.html
  # Escaped, so it renders as text…
  grep -qF '&lt;script&gt;alert(1)&lt;/script&gt; tea &amp; scones' <<<"$output"
  grep -qF '&lt;img src=x onerror=alert(2)&gt;' <<<"$output"
  # …and nothing from it survives as markup. The literal string "onerror="
  # is still in the file and that is FINE: escaping its angle brackets is
  # exactly what makes it inert text instead of an attribute. What must not
  # exist is an element — a title can never open a tag, because esc() takes
  # < > & " ' before anything reaches the page.
  refute_in_output '<script'
  refute_in_output '<img'
  run grep -ciE '<script|<img|<iframe|javascript:' board.html
  [ "$status" -eq 1 ]
}

@test "--html page makes zero network requests" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]

  # No absolute or protocol-relative URL, no @import, no fetch, no src: the
  # styles, the texture and the profile are all inline, so the page opens
  # offline and inside a locked-down viewer.
  run grep -nE 'https?://|//cdn|@import|fetch\(|<link |src=' board.html
  [ "$status" -eq 1 ]

  # The page DOES carry references: `url(#…)` for the mask and clip, and
  # `<use href="#pebble">` for the mark on a blocked or delivered-phase card.
  # Banning those attributes outright would fail on a board that has any
  # blocked work, so the rule is the one that actually matters: every
  # reference must point INSIDE this document. Listing forbidden shapes only
  # catches the ones we thought of; requiring a fragment catches the rest.
  run bash -c "grep -o 'url([^)]*)' board.html | sort -u | grep -cv 'url(#' \
    || true"
  [ "$output" = "0" ]
  run bash -c "grep -o 'href=\"[^\"]*\"' board.html | sort -u \
    | grep -cv 'href=\"#' || true"
  [ "$output" = "0" ]

  # …and the references are really there, so the two checks above cannot pass
  # by matching nothing. This board has a blocked card, so it has both kinds.
  run bash -c "grep -c 'url(#' board.html"
  [ "$output" != "0" ]
  grep -qF '<use href="#pebble">' board.html
}

@test "--html without a roadmap degrades to a flat band, no invented terrain" {
  require_bd
  make_tmp_repo
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  local solo
  solo="$(bd create "Solo issue" -t task --silent)"

  # No .planning at all: must not crash, must not draw phases it cannot know.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]
  [ -f board.html ]

  run cat board.html
  grep -qF 'no roadmap phases. counts only.' <<<"$output"
  grep -qF 'no roadmap position' <<<"$output"
  grep -qF "$solo" <<<"$output"
  refute_in_output 'class="cairn-stack"'
  refute_in_output 'class="ticks"'
}

@test "--html on a GSD repo without .beads renders the note and empty lanes" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]

  run cat board.html
  grep -qF 'no .beads/' <<<"$output"
  grep -qF 'no work ready. plan a phase.' <<<"$output"
  grep -qF 'nothing in flight.' <<<"$output"
  grep -qF 'nothing blocked.' <<<"$output"
  # The roadmap still draws, at zero elevation everywhere.
  grep -qF 'class="terrain-mass"' <<<"$output"
}

@test "--html composes with --json and --planning-dir, and refuses --plain/--brief" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture
  local target_repo="$CAIRN_TMP_REPO"

  # --json reports the write instead of the confirmation line.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json --html board.html
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
  assert_json_eq "$output" '.counts.ready' '2'
  assert_json_eq "$output" '.html.changed' 'true'
  # pwd -P: the reported path is fully resolved, and on macOS the tmpdir
  # reaches it through a /var -> /private/var symlink.
  [ "$(jq -r '.html.file' <<<"$output")" = "$(pwd -P)/board.html" ]

  # --planning-dir still points the board at another checkout.
  make_tmp_repo
  bd init -q --prefix other --non-interactive >/dev/null 2>&1
  local stray
  stray="$(bd create "Stray issue from the wrong repo" -t task --silent)"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html elsewhere.html \
    --planning-dir "$target_repo/.planning"
  [ "$status" -eq 0 ]
  run cat elsewhere.html
  grep -qF 'Gate regex hardening' <<<"$output"
  refute_in_output "$stray"

  # Stdout render modes are not file render targets.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html --plain
  [ "$status" -eq 2 ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html --brief
  [ "$status" -eq 2 ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html
  [ "$status" -eq 2 ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html /no/such/dir/board.html
  [ "$status" -eq 2 ]
}

@test "--html elevation is proportional: relief has no floor, and one strata band means one issue" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  # Phase 1 carries one issue, phase 2 carries four: a 4:1 reading.
  bd create "Auth one" -t task -l phase-1,m-v1.0 --silent >/dev/null
  for n in 1 2 3 4; do
    bd create "Api $n" -t task -l phase-2,m-v1.0 --silent >/dev/null
  done

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]

  # One band per issue of the busiest phase, and the bands sit at exactly
  # BASE_Y - k*(MAX_RELIEF/busiest) = 196 - k*31. A phase carrying one issue
  # therefore peaks on the FIRST band and the four-issue phase on the last:
  # that is the 4:1 the data says, and it is what a relief floor destroyed
  # (it used to render as 2.32:1).
  run bash -c "grep -o '<line x1=\"[^\"]*\" y1=\"[^\"]*\"' board.html | wc -l | tr -d ' '"
  [ "$output" = "4" ]
  grep -qF 'y1="165.0"' board.html
  grep -qF 'y1="134.0"' board.html
  grep -qF 'y1="103.0"' board.html
  grep -qF 'y1="72.0"' board.html
  # The caption names the band's unit, so counting them is a defined reading.
  grep -qF 'one band each' board.html
}

@test "--html a finished roadmap draws no climb ahead; an unfinished one does, and hands off without a shear" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  # Phase 2 is open in the fixture: there IS ground still ahead.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html mid.html
  [ "$status" -eq 0 ]
  grep -qF '<polyline class="terrain-ahead"' mid.html
  # …and the walked mass dissolves into it instead of being cut off square.
  grep -qF 'id="cairn-ground-cut"' mid.html

  # Tick every phase: nothing is left to climb.
  sed -i.bak 's/- \[ \] \*\*Phase 2/- [x] **Phase 2/' .planning/ROADMAP.md
  rm -f .planning/ROADMAP.md.bak
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html done.html
  [ "$status" -eq 0 ]
  # No dotted trail asserting work that does not exist, and with no cut
  # there is nothing to feather: the ground runs off the page.
  run bash -c "grep -c '<polyline class=\"terrain-ahead\"' done.html || true"
  [ "$output" = "0" ]
  run bash -c "grep -c 'id=\"cairn-ground-cut\"' done.html || true"
  [ "$output" = "0" ]
  # The crest itself is still drawn — the terrain did not disappear with it.
  grep -qF '<polyline class="terrain-crest"' done.html
}

@test "--html the caption reports work the terrain cannot show" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  bd create "Placed" -t task -l phase-2,m-v1.0 --silent >/dev/null
  bd create "No phase label at all" -t task --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]
  # Two issues tracked, one of them has no phase: the profile says so rather
  # than quietly under-reporting the board it sits on.
  grep -qF '1 of 2 issues carry a phase' board.html

  # With every issue placed, the caption does not carry the clause at all.
  rm -f board.html
  bd create "Also placed" -t task -l phase-2,m-v1.0 --silent >/dev/null
  bd list --status open --json >/dev/null 2>&1
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html full.html
  [ "$status" -eq 0 ]
  run bash -c "grep -c 'issues carry a phase' full.html || true"
  [ "$output" = "1" ]
}

@test "--html the next line points at its card instead of repeating it" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]

  # The card the next action names is marked, exactly once.
  run bash -c "grep -c 'class=\"card is-next\"' board.html"
  [ "$output" = "1" ]
  # …and the sentence is printed once on the page, in the card — not also
  # spelled out in the next line 130px above it. Scoped to the generated
  # region: the .next-title RULE still lives in the stylesheet, because the
  # line does carry a title when the next action has no card to point at.
  board_inside board.html > inside.html
  run bash -c "grep -c 'next-title' inside.html || true"
  [ "$output" = "0" ]
  # The line still names the id, which is what sends you to the card.
  grep -qF 'class="next-id"' board.html
}

@test "--html an empty lane keeps its heading but not an equal share of the width" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix st --non-interactive >/dev/null 2>&1
  bd create "The only work there is" -t task -l phase-2,m-v1.0 --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]
  # ready holds the one issue; doing and blocked are empty and get half its
  # track. The zero still states itself: "nothing blocked" and "blocked was
  # never checked" must not look the same.
  # `--` first: the pattern itself starts with dashes.
  grep -qF -- '--lane-tracks: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr)' \
    board.html
  grep -qF 'nothing blocked.' board.html
  grep -qF 'nothing in flight.' board.html
  # -o then count: the three lanes are emitted on ONE line, so grep -c would
  # report 1 however many matched.
  run bash -c "grep -o 'class=\"lane lane-[a-z]* is-empty\"' board.html \
    | wc -l | tr -d ' '"
  [ "$output" = "2" ]

  # With nothing anywhere, the three stay even: then the emptiness IS the
  # message and lopsided columns would only read as broken.
  rm -rf .beads && bd init -q --prefix e2 --non-interactive >/dev/null 2>&1
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html bare.html
  [ "$status" -eq 0 ]
  grep -qF -- '--lane-tracks: repeat(3, minmax(0, 1fr))' bare.html
}

@test "--html the header and the profile agree on which phase you stand in" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture
  # STATE.md says nothing about the active phase: the terrain resolves it,
  # and the header must not stay silent while the SVG label announces it.
  printf -- '---\nmilestone: v1.0\n---\n\n# State\n' > .planning/STATE.md

  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]
  # Phase 1 is delivered in the fixture, so the first phase not yet complete
  # is 2 — in the label a screen reader reads AND in the line a sighted
  # reader reads.
  grep -qF 'standing at phase 2' board.html
  grep -qF 'phase <span class="n">2</span> of' board.html
}

@test "--html refuses a page with broken markers and leaves every byte of it alone" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  # A page carrying only the START marker. Appending a block here would
  # forge the missing partner, and the NEXT run would splice between the
  # orphan and the newcomer, taking the user's closing tags with it.
  printf '<html><body>\n<p id="mine">hands off</p>\n%s\n</body></html>\n' \
    "$BOARD_START" > lone-start.html
  cp lone-start.html lone-start.expected
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html lone-start.html
  [ "$status" -eq 2 ]
  grep -qF 'broken board markers' <<<"$output"
  run diff lone-start.html lone-start.expected
  [ "$status" -eq 0 ]

  # The mirror case used to grow an extra board on every single run.
  printf '<html><body>\n%s\n</body></html>\n' "$BOARD_END" > lone-end.html
  cp lone-end.html lone-end.expected
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html lone-end.html
  [ "$status" -eq 2 ]
  run diff lone-end.html lone-end.expected
  [ "$status" -eq 0 ]

  # A duplicated pair is ambiguous, so it is refused rather than guessed at.
  printf '%s\n%s\n%s\n%s\n' "$BOARD_START" "$BOARD_END" "$BOARD_START" \
    "$BOARD_END" > doubled.html
  cp doubled.html doubled.expected
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html doubled.html
  [ "$status" -eq 2 ]
  run diff doubled.html doubled.expected
  [ "$status" -eq 0 ]

  # End before start: same refusal.
  printf '%s\n<p>x</p>\n%s\n' "$BOARD_END" "$BOARD_START" > inverted.html
  cp inverted.html inverted.expected
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html inverted.html
  [ "$status" -eq 2 ]
  run diff inverted.html inverted.expected
  [ "$status" -eq 0 ]

  # A page with NEITHER marker is still appended to, never destroyed.
  printf '<html><body>\n<p id="mine">keep me</p>\n</body></html>\n' > plain.html
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html plain.html
  [ "$status" -eq 0 ]
  grep -qF '<p id="mine">keep me</p>' plain.html
  grep -qF "$BOARD_START" plain.html
  grep -qF "$BOARD_END" plain.html
}

@test "--html on a target that is not UTF-8 text exits 2 instead of a traceback" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  printf '\xff\xfe\x00\x01not text at all' > binary.html
  cp binary.html binary.expected
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html binary.html
  # UnicodeDecodeError is a ValueError, so `except OSError` used to miss it
  # and the run died with a traceback and exit 1.
  [ "$status" -eq 2 ]
  grep -qF 'as UTF-8 text' <<<"$output"
  refute_in_output 'Traceback'
  run diff binary.html binary.expected
  [ "$status" -eq 0 ]
}

@test "--html writes a readable page and keeps a mode the reader chose" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_status_fixture

  # A board is opened in a browser and sometimes served from another machine.
  # The atomic write goes through a temp file, which Python creates 0600, and
  # os.replace carries that mode onto the target — so the mode has to be set
  # back to what an ordinary create would have produced.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]
  run bash -c "stat -f '%Lp' board.html 2>/dev/null || stat -c '%a' board.html"
  [ "$output" = "644" ]

  # And a mode the reader set themselves survives regeneration.
  chmod 640 board.html
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --html board.html
  [ "$status" -eq 0 ]
  run bash -c "stat -f '%Lp' board.html 2>/dev/null || stat -c '%a' board.html"
  [ "$output" = "640" ]
}
