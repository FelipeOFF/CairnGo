#!/usr/bin/env bats
# hooks.bats — exercises the cairn Claude Code hooks as processes:
#   post-bd-write.sh  (PostToolUse, matcher Bash) — fake hook JSON on stdin;
#                     background gbsync mirror push + phase map refresh are
#                     observed through recorder stubs (CAIRN_GBSYNC/CAIRN_MAP
#                     seams) that append their argv to a log file.
#   session-start.sh  — migration-discovery nudge branches.
#   session-stop.sh   — in_progress-issues warning, silent when clean.
# Every hook must ALWAYS exit 0 and never break the tool call / session.

load 'helpers'

CAIRN_HOOKS_DIR="$CAIRN_REPO_ROOT/cairn/hooks"

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# Recorder stubs: append "$@" to a log, exit 0. Wired in via the CAIRN_GBSYNC
# and CAIRN_MAP env seams (the hook invokes them through bash). Also seeds
# default CAIRN_GH / CAIRN_BD stubs (gh: silent no-op, "no PR yet" — the
# common case; bd: a recorder, same shape as gbsync/map) so every test stays
# hermetic against the external-ref job without needing to care about it —
# tests that DO exercise that job override CAIRN_GH/CAIRN_BD themselves
# before calling post_bd_write (see post_bd_write's fallback expansion).
make_recorders() {
  GBSYNC_STUB="$BATS_TEST_TMPDIR/gbsync-recorder"
  GBSYNC_LOG="$BATS_TEST_TMPDIR/gbsync.log"
  MAP_STUB="$BATS_TEST_TMPDIR/map-recorder"
  MAP_LOG="$BATS_TEST_TMPDIR/map.log"
  printf '#!/usr/bin/env bash\necho "$@" >> "%s"\n' "$GBSYNC_LOG" > "$GBSYNC_STUB"
  printf '#!/usr/bin/env bash\necho "$@" >> "%s"\n' "$MAP_LOG" > "$MAP_STUB"
  chmod +x "$GBSYNC_STUB" "$MAP_STUB"

  GH_STUB="$BATS_TEST_TMPDIR/gh-recorder"
  BD_STUB="$BATS_TEST_TMPDIR/bd-recorder"
  BD_LOG="$BATS_TEST_TMPDIR/bd.log"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$GH_STUB"
  printf '#!/usr/bin/env bash\necho "$@" >> "%s"\n' "$BD_LOG" > "$BD_STUB"
  chmod +x "$GH_STUB" "$BD_STUB"
}

# Feed a fake PostToolUse payload for COMMAND into the hook. CAIRN_GH/CAIRN_BD
# default to the hermetic no-op stubs from make_recorders when the caller
# hasn't already set them (bash dynamic scoping: a plain `CAIRN_GH=...`
# assignment in the calling @test is visible here, same as GBSYNC_STUB etc.).
post_bd_write() {
  printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1" \
    | env CLAUDE_PROJECT_DIR="$PWD" \
          CAIRN_GBSYNC="$GBSYNC_STUB" CAIRN_MAP="$MAP_STUB" \
          CAIRN_GH="${CAIRN_GH:-$GH_STUB}" CAIRN_BD="${CAIRN_BD:-$BD_STUB}" \
          bash "$CAIRN_HOOKS_DIR/post-bd-write.sh"
}

# $PATH with every directory containing a `gh` executable removed. Used only
# by the "gh genuinely absent" test below — everything else the hook needs
# (bash, python3, possibly via an asdf/pyenv shim chain) stays resolvable,
# because this is a deny-list (strip gh's dir(s)), not a hand-picked
# allow-list that would have to know about every transitive tool a shim
# might invoke.
path_without_gh() {
  local dir out=""
  IFS=':' read -ra dirs <<< "$PATH"
  for dir in "${dirs[@]}"; do
    [ -x "$dir/gh" ] && continue
    out="${out:+$out:}$dir"
  done
  printf '%s' "$out"
}

write_sync_json() {  # $1 = true|false (enabled flag of the single backend)
  mkdir -p .cairn
  printf '{"backends":[{"type":"github","enabled":%s,"adapter":"github","config":{"repo":"o/n"}}]}\n' \
    "$1" > .cairn/sync.json
}

# The hook backgrounds its work (nohup + &): poll for the recorder log.
wait_for_lines() {  # $1 = file, $2 = minimum line count
  local i
  for i in $(seq 1 50); do
    if [ -f "$1" ] && [ "$(wc -l < "$1")" -ge "$2" ]; then
      return 0
    fi
    sleep 0.1
  done
  echo "timed out waiting for $2 line(s) in $1" >&2
  return 1
}

#-----------------------------------------------------------------------------
# post-bd-write.sh
#-----------------------------------------------------------------------------

@test "post-bd-write: bd close with enabled sync fires gbsync close <id> in background" {
  make_tmp_repo
  make_recorders
  write_sync_json true

  run post_bd_write "bd close map-1 --reason=done"
  [ "$status" -eq 0 ]
  # At most one short stdout line.
  [ "${#lines[@]}" -le 1 ]
  grep -qF "queued" <<<"$output"

  wait_for_lines "$GBSYNC_LOG" 1
  grep -qxF "close map-1" "$GBSYNC_LOG"
  [ ! -f "$MAP_LOG" ]   # no phase label in the command, no .planning/
}

@test "post-bd-write: id AFTER a value flag — bd close --reason \"x\" <id> still mirrors" {
  # The reason value is a quoted token that fails the id shape, so the scanner
  # must keep going and find the id later in the command line.
  make_tmp_repo
  make_recorders
  write_sync_json true

  # \" keeps the payload valid JSON (the real Claude Code payload arrives
  # properly escaped too); the decoded command carries the quoted reason.
  run post_bd_write 'bd close --reason \"superseded by map-9\" map-7'
  [ "$status" -eq 0 ]
  wait_for_lines "$GBSYNC_LOG" 1
  grep -qxF "close map-7" "$GBSYNC_LOG"
}

@test "post-bd-write: --parent value is never mistaken for the issue id" {
  make_tmp_repo
  make_recorders
  write_sync_json true

  run post_bd_write 'bd update --parent map-epic map-3 -s open'
  [ "$status" -eq 0 ]
  wait_for_lines "$GBSYNC_LOG" 1
  grep -qxF "update map-3" "$GBSYNC_LOG"
}

@test "post-bd-write: bd update <id> mirrors as gbsync update <id>" {
  make_tmp_repo
  make_recorders
  write_sync_json true

  run post_bd_write "bd update map-2 -s open"
  [ "$status" -eq 0 ]
  wait_for_lines "$GBSYNC_LOG" 1
  grep -qxF "update map-2" "$GBSYNC_LOG"
}

@test "post-bd-write: hyphenated repo prefix — id like my-app-3fk still mirrors" {
  # bd derives the id prefix from the directory name, so ids routinely carry
  # interior hyphens (my-app-3fk). The extractor must not degrade those to the
  # full-push path.
  make_tmp_repo
  make_recorders
  write_sync_json true

  run post_bd_write "bd close my-hyphen-app-e3i --reason done"
  [ "$status" -eq 0 ]
  wait_for_lines "$GBSYNC_LOG" 1
  grep -qxF "close my-hyphen-app-e3i" "$GBSYNC_LOG"
}

@test "post-bd-write: --add-label value is never mistaken for the issue id" {
  # Label values are id-shaped (phase-3); without --add-label in the
  # value-flag table the scanner would extract 'phase-3' as the issue and
  # gbsync would fire on a nonexistent id.
  make_tmp_repo
  make_recorders
  write_sync_json true

  run post_bd_write 'bd update --add-label phase-3 map-7'
  [ "$status" -eq 0 ]
  wait_for_lines "$GBSYNC_LOG" 1
  grep -qxF "update map-7" "$GBSYNC_LOG"
}

@test "post-bd-write: bd reopen mirrors as gbsync update <id>" {
  # gbsync's push vocabulary is create|update|close — a reopen rides as
  # update so the mirror's status change is not silently dropped.
  make_tmp_repo
  make_recorders
  write_sync_json true

  run post_bd_write "bd reopen map-4 --reason follow-up"
  [ "$status" -eq 0 ]
  wait_for_lines "$GBSYNC_LOG" 1
  grep -qxF "update map-4" "$GBSYNC_LOG"
}

@test "post-bd-write: sync.json disabled — no gbsync call" {
  make_tmp_repo
  make_recorders
  write_sync_json false

  run post_bd_write "bd close map-1"
  [ "$status" -eq 0 ]
  sleep 0.5
  [ ! -f "$GBSYNC_LOG" ]
}

@test "post-bd-write: non-bd command is a silent no-op" {
  make_tmp_repo
  make_recorders
  write_sync_json true

  run post_bd_write "git status"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  sleep 0.5
  [ ! -f "$GBSYNC_LOG" ]
  [ ! -f "$MAP_LOG" ]
}

@test "post-bd-write: phase-N in the command refreshes that phase's map" {
  make_tmp_repo
  make_recorders
  mkdir .planning

  run post_bd_write "bd update gate-1 --add-label phase-2"
  [ "$status" -eq 0 ]
  wait_for_lines "$MAP_LOG" 1
  grep -qxF "2" "$MAP_LOG"
  [ ! -f "$GBSYNC_LOG" ]   # no sync.json in this repo
}

@test "post-bd-write: no .planning/ — phase label does NOT trigger a map refresh" {
  make_tmp_repo
  make_recorders

  run post_bd_write "bd update gate-1 --add-label phase-2"
  [ "$status" -eq 0 ]
  sleep 0.5
  [ ! -f "$MAP_LOG" ]
}

@test "post-bd-write: bd create runs a full push of every unmapped issue" {
  require_bd
  make_tmp_repo
  make_recorders
  write_sync_json true
  bd init -q --prefix hok --non-interactive >/dev/null 2>&1
  local a b
  a="$(bd create "First" -t task --silent)"
  b="$(bd create "Second" -t task --silent)"

  run post_bd_write "bd create Third -t task"
  [ "$status" -eq 0 ]
  wait_for_lines "$GBSYNC_LOG" 2
  grep -qxF "create $a" "$GBSYNC_LOG"
  grep -qxF "create $b" "$GBSYNC_LOG"
}

#-----------------------------------------------------------------------------
# post-bd-write.sh — external-ref backfill on bd close (CORR-08 / D-12)
#-----------------------------------------------------------------------------

@test "post-bd-write: bd close on a branch with an open PR fires bd update --external-ref in background" {
  make_tmp_repo
  make_recorders

  CAIRN_GH="$BATS_TEST_TMPDIR/gh-stub-success"
  printf '#!/usr/bin/env bash\necho 42\n' > "$CAIRN_GH"
  chmod +x "$CAIRN_GH"
  # CAIRN_BD left unset — post_bd_write falls back to the default $BD_STUB
  # recorder from make_recorders.

  run post_bd_write "bd close map-9 --reason=done"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -le 1 ]
  grep -qF "queued" <<<"$output"

  # Proves the write was ATTEMPTED with the right arguments.
  wait_for_lines "$BD_LOG" 1
  grep -qF "update map-9 --external-ref gh-42" "$BD_LOG"
}

@test "post-bd-write: gh genuinely absent from PATH — bd close is a silent no-op, no hook.log" {
  make_tmp_repo
  make_recorders

  # No CAIRN_GH stub at all: the hook falls back to the literal name "gh",
  # and this PATH has every directory that could resolve it stripped out —
  # proves the `command -v gh` guard itself fails closed, not just that a
  # stub returned nothing.
  run env CLAUDE_PROJECT_DIR="$PWD" PATH="$(path_without_gh)" \
      bash "$CAIRN_HOOKS_DIR/post-bd-write.sh" \
      <<<'{"tool_name":"Bash","tool_input":{"command":"bd close map-1 --reason=done"}}'

  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -le 1 ]
  [ ! -f "$PWD/.cairn/hook.log" ]
}

@test "post-bd-write: external-ref write failure is observable in .cairn/hook.log, never swallowed" {
  # The load-bearing test: this hook's contract is "never fail the caller",
  # so a write failure here would otherwise vanish into /dev/null exactly
  # like the bug shape D-12 names. Force bd to fail and prove the failure
  # surfaces somewhere durable instead of disappearing.
  make_tmp_repo
  make_recorders

  CAIRN_GH="$BATS_TEST_TMPDIR/gh-stub-forced-failure"
  printf '#!/usr/bin/env bash\necho 77\n' > "$CAIRN_GH"
  chmod +x "$CAIRN_GH"

  CAIRN_BD="$BATS_TEST_TMPDIR/bd-stub-forced-failure"
  printf '#!/usr/bin/env bash\necho "bd: external-ref write failed: simulated failure" >&2\nexit 1\n' > "$CAIRN_BD"
  chmod +x "$CAIRN_BD"

  run post_bd_write "bd close map-13 --reason=done"
  # Contract intact even though the underlying write failed.
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -le 1 ]

  # The failure is observable, not discarded.
  wait_for_lines "$PWD/.cairn/hook.log" 1
  grep -qF "simulated failure" "$PWD/.cairn/hook.log"
}

#-----------------------------------------------------------------------------
# session-start.sh — migration discovery branches
#-----------------------------------------------------------------------------

@test "session-start: .planning/ without .beads/ nudges /cairn:migrate" {
  require_bd
  make_tmp_repo
  mkdir .planning

  run env CLAUDE_PROJECT_DIR="$PWD" bash "$CAIRN_HOOKS_DIR/session-start.sh"
  [ "$status" -eq 0 ]
  grep -qF "/cairn:migrate" <<<"$output"
  refute_in_output "integration is active"
}

@test "session-start: both dirs but no NN-BEADS-MAP.md nudges the wire-up" {
  require_bd
  make_tmp_repo
  mkdir -p .planning/phases/01-auth .beads

  run env CLAUDE_PROJECT_DIR="$PWD" bash "$CAIRN_HOOKS_DIR/session-start.sh"
  [ "$status" -eq 0 ]
  grep -qF "BEADS-MAP" <<<"$output"
  grep -qF "/cairn:migrate" <<<"$output"
  # The integration-active reminder still fires alongside the nudge, and it
  # teaches the pair + stamp convention (not the old single-label one).
  grep -qF "integration is active" <<<"$output"
  grep -qF "m-<milestone>,phase-<N>" <<<"$output"
  grep -qF "dedup key" <<<"$output"
}

@test "session-start: dedup — no migrate nudge once a phase map exists" {
  require_bd
  make_tmp_repo
  mkdir -p .planning/phases/01-auth .beads
  touch .planning/phases/01-auth/01-BEADS-MAP.md

  run env CLAUDE_PROJECT_DIR="$PWD" bash "$CAIRN_HOOKS_DIR/session-start.sh"
  [ "$status" -eq 0 ]
  refute_in_output "/cairn:migrate"
  grep -qF "integration is active" <<<"$output"
}

#-----------------------------------------------------------------------------
# session-stop.sh
#-----------------------------------------------------------------------------

@test "session-stop: silent and exit 0 when nothing is in_progress" {
  require_bd
  make_tmp_repo
  bd init -q --prefix hok --non-interactive >/dev/null 2>&1
  bd create "Open but unclaimed" -t task --silent >/dev/null

  run env CLAUDE_PROJECT_DIR="$PWD" BEADS_ACTOR="tester" \
      bash "$CAIRN_HOOKS_DIR/session-stop.sh"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "session-stop: warns (one line) about in_progress issues assigned to the actor" {
  require_bd
  make_tmp_repo
  bd init -q --prefix hok --non-interactive >/dev/null 2>&1
  local id
  id="$(bd create "Mid-flight work" -t task --silent)"
  env BEADS_ACTOR="tester" bd update "$id" --claim >/dev/null

  run env CLAUDE_PROJECT_DIR="$PWD" BEADS_ACTOR="tester" \
      bash "$CAIRN_HOOKS_DIR/session-stop.sh"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
  grep -qF "$id" <<<"$output"
  grep -qF "in_progress" <<<"$output"

  # A different actor's session stays silent — the issue isn't theirs.
  run env CLAUDE_PROJECT_DIR="$PWD" BEADS_ACTOR="someone-else" \
      bash "$CAIRN_HOOKS_DIR/session-stop.sh"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "session-stop: no .beads/ — silent exit 0" {
  make_tmp_repo

  run env CLAUDE_PROJECT_DIR="$PWD" bash "$CAIRN_HOOKS_DIR/session-stop.sh"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
