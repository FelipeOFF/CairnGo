#!/usr/bin/env bats
# cairn-parallel.bats — exercises the parallel-phase driver's CLI contract
# (cairn-parallel.py / the cairn-parallel.sh wrapper): `prepare N` (create
# phase N's deterministically named worktree and take its lease pointing AT
# that worktree) and `batch` (consume cairn-status.py's parallelism block and
# announce what can run, with each phase's branch and worktree resolved).
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so every check is a plain `[ ]` against a
# `run`-captured $status/$output, substring checks use grep -qF, and negative
# checks use refute_in_output.
#
# These tests use REAL `git worktree` trees and a REAL bd database — the
# isolation claim (PAR-02) and the cross-worktree lease claim (PAR-03) are
# not things a stub can honestly stand in for. The one place a stub IS used
# is the CAIRN_STATUS seam, on purpose: the whole point of those tests is
# that `batch` follows the stub even when the fixture's own ROADMAP says
# something else.

load 'helpers'

bats_require_minimum_version 1.5.0

PARALLEL="$CAIRN_SCRIPTS_DIR/cairn-parallel.sh"
LEASE="$CAIRN_SCRIPTS_DIR/cairn-lease.sh"

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# The physical path of an argument, symlinks and all. Used on BOTH sides of
# every path comparison: macOS TMPDIR resolves through a /var -> /private/var
# symlink and git reports the physical path, so comparing a raw string
# against a git-reported one proves nothing (the same lesson
# tests/cairn-lease.bats:35-41 records).
realpath_of() {
  python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

# A throwaway repo with bd initialized, the shared GSD fixture (.planning with
# phases 01-auth and 02-api), plus two extra phase directories (07-alpha,
# 09-beta) whose numbers the CAIRN_STATUS stubs below hand back as runnable.
# Their leading zeros are load-bearing: slug resolution has to match `07-` for
# phase 7, and the batch->prepare bridge test is what catches a resolver that
# only does so on one of the two paths.
# Exports MAIN_ROOT (git's PHYSICAL toplevel — on macOS TMPDIR resolves
# through a /var -> /private/var symlink, so bash's $PWD is not the same
# string the scripts see).
make_parallel_fixture() {
  make_tmp_repo
  bd init -q --prefix par --non-interactive >/dev/null 2>&1
  make_gsd_fixture "$PWD"
  mkdir -p .planning/phases/03-gamma .planning/phases/07-alpha \
           .planning/phases/09-beta
  echo "phase 3" > .planning/phases/03-gamma/03-01-PLAN.md
  echo "phase 7" > .planning/phases/07-alpha/07-01-PLAN.md
  echo "phase 9" > .planning/phases/09-beta/09-01-PLAN.md
  git add .planning >/dev/null
  git commit -qm "fixture: planning tree"
  MAIN_ROOT="$(git rev-parse --show-toplevel)"
}

# A cairn-status.py stand-in whose parallelism.runnable is exactly $1..$N.
# Deliberately contradicts the fixture's own ROADMAP (which describes phases
# 1 and 2, with only phase 2 pending): an implementation that derived
# independence from the roadmap instead of consuming parallelism() cannot
# pass a test built on this stub.
write_status_stub() {
  STATUS_STUB="$BATS_TEST_TMPDIR/status-stub.py"
  cat > "$STATUS_STUB" <<'PYEOF'
#!/usr/bin/env python3
import json
print(json.dumps({
    "parallelism": {
        "runnable": [7, 9],
        "blocked": [11],
        "declared": True,
        "note": "Phases 7 and 9 are independent — stub note.",
    },
    "next_commands": [
        {"command": "/cairn:plan 7", "phase": 7, "title": "Alpha",
         "reason": "nothing blocks it", "blocked": False},
        {"command": "/cairn:plan 9", "phase": 9, "title": "Beta",
         "reason": "nothing blocks it", "blocked": False},
        {"command": "/cairn:work 11", "phase": 11, "title": "Eleven",
         "reason": "waits on phase 7", "blocked": True},
    ],
    "phases": [
        {"number": 1, "title": "Auth", "complete": True},
        {"number": 2, "title": "API", "complete": False},
    ],
}))
PYEOF
}

#-----------------------------------------------------------------------------
# Task 1: prepare — the named worktree, its isolation, and the lease that
# points at it rather than at the main checkout.
#-----------------------------------------------------------------------------

@test "the tracer: prepare creates the named worktree, isolates it from the main tree, and points the phase lease at it" {
  require_bd
  make_parallel_fixture

  run bash "$PARALLEL" prepare 2 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.slug' 'api'
  assert_json_eq "$output" '.branch' 'phase/2-api'
  assert_json_eq "$output" '.created' 'true'
  assert_json_eq "$output" '.planning_files_forbidden | length' '3'

  local wt
  wt="$(jq -r '.worktree' <<<"$output")"
  [ "$wt" = "$MAIN_ROOT-phase-2" ]
  [ -d "$wt" ]

  run git -C "$wt" rev-parse --abbrev-ref HEAD
  [ "$status" -eq 0 ]
  [ "$output" = "phase/2-api" ]

  # PAR-02 — the isolation claim, proven by writing, not by reading code.
  echo "written by the phase agent" > "$wt/only-in-the-phase-worktree.txt"
  [ -f "$wt/only-in-the-phase-worktree.txt" ]
  [ ! -f "$MAIN_ROOT/only-in-the-phase-worktree.txt" ]

  # PAR-03 — the lease's holder is the PHYSICAL worktree path, not the main
  # root. This is the assertion that separates "a worktree exists" from "the
  # worktree owns the phase": pointing the acquire's --project-dir at the
  # main root instead would leave every other assertion here green.
  local wt_real
  wt_real="$(git -C "$wt" rev-parse --show-toplevel)"
  [ "$wt_real" != "$MAIN_ROOT" ]
  run bash "$LEASE" status 2 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'true'
  assert_json_eq "$output" '.holder' "$wt_real"
}

@test "prepare on a phase with no phase directory names the branch phase/<N>, with a null slug" {
  require_bd
  make_parallel_fixture

  run bash "$PARALLEL" prepare 44 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.slug' 'null'
  assert_json_eq "$output" '.branch' 'phase/44'

  local wt
  wt="$(jq -r '.worktree' <<<"$output")"
  run git -C "$wt" rev-parse --abbrev-ref HEAD
  [ "$output" = "phase/44" ]
}

@test "prepare refuses to run from a linked worktree, exit 2, creating nothing" {
  require_bd
  make_parallel_fixture

  local other="$BATS_TEST_TMPDIR/linked"
  git worktree add -q "$other" -b some-other-branch

  run bash "$PARALLEL" prepare 2 --project-dir "$other"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"
  [ ! -d "$MAIN_ROOT-phase-2" ]
}

@test "prepare refuses, exit 4, when the target path exists and is not a worktree of this repo" {
  require_bd
  make_parallel_fixture

  mkdir -p "$MAIN_ROOT-phase-2"
  echo "someone else's directory" > "$MAIN_ROOT-phase-2/keep-me.txt"

  run bash "$PARALLEL" prepare 2 --project-dir "$MAIN_ROOT"
  [ "$status" -eq 4 ]
  refute_in_output "Traceback"
  # Nothing touched: the pre-existing content is still there and no branch
  # was created.
  [ -f "$MAIN_ROOT-phase-2/keep-me.txt" ]
  run git -C "$MAIN_ROOT" rev-parse --verify --quiet refs/heads/phase/2-api
  [ "$status" -ne 0 ]
}

@test "prepare refuses, exit 4, when the phase branch already exists without its worktree" {
  require_bd
  make_parallel_fixture

  git -C "$MAIN_ROOT" branch phase/2-api

  run bash "$PARALLEL" prepare 2 --project-dir "$MAIN_ROOT"
  [ "$status" -eq 4 ]
  refute_in_output "Traceback"
  [ ! -d "$MAIN_ROOT-phase-2" ]
}

#-----------------------------------------------------------------------------
# Task 2: batch — a CONSUMER of cairn-status.py's parallelism block, and the
# bridge to prepare.
#-----------------------------------------------------------------------------

@test "batch consumes parallelism.runnable and never recomputes it: the stub says 7 and 9 while the fixture ROADMAP says otherwise, and batch follows the stub" {
  require_bd
  make_parallel_fixture
  write_status_stub

  # The fixture's own ROADMAP describes phases 1 (complete) and 2 (pending),
  # so any implementation that derived independence from the roadmap would
  # select 2 — or nothing — instead of 7 and 9.
  grep -qF "Phase 2: API" "$MAIN_ROOT/.planning/ROADMAP.md"

  run env CAIRN_STATUS="$STATUS_STUB" \
    bash "$PARALLEL" batch --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.runnable | join(",")' '7,9'
  assert_json_eq "$output" '.selected | length' '2'
  assert_json_eq "$output" '[.selected[].phase] | join(",")' '7,9'
  assert_json_eq "$output" '.deferred | length' '0'
  # blocked / declared / note are passed through verbatim — they belong to
  # whoever computed independence, not to this script.
  assert_json_eq "$output" '.blocked | join(",")' '11'
  assert_json_eq "$output" '.declared' 'true'
  assert_json_eq "$output" '.note' 'Phases 7 and 9 are independent — stub note.'
  # next_command and reason come from next_commands[], also verbatim.
  assert_json_eq "$output" '[.selected[] | select(.phase == 7) | .next_command][0]' '/cairn:plan 7'
  assert_json_eq "$output" '[.selected[] | select(.phase == 7) | .reason][0]' 'nothing blocks it'
  assert_json_eq "$output" '[.selected[] | select(.phase == 9) | .title][0]' 'Beta'
}

@test "batch drops a runnable phase whose lease is held by a live holder, names the holder, and keeps the other one" {
  require_bd
  make_parallel_fixture
  write_status_stub

  local wt_b="$BATS_TEST_TMPDIR/holder"
  git worktree add -q "$wt_b" -b holder-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 7 --project-dir "$wt_b"
  [ "$status" -eq 0 ]

  run env CAIRN_STATUS="$STATUS_STUB" \
    bash "$PARALLEL" batch --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.selected[].phase] | join(",")' '9'
  assert_json_eq "$output" '[.deferred[].phase] | join(",")' '7'
  assert_json_eq "$output" '[.deferred[] | select(.phase == 7) | .reason][0] | startswith("lease held by ")' 'true'
  grep -qF "$wt_b" <<<"$output"
  # The announcement the operator reads names the exclusion too.
  assert_json_eq "$output" '.announcement | contains("phase 7 stays out")' 'true'
}

@test "batch defers everything past --max with the ceiling named as the reason" {
  require_bd
  make_parallel_fixture
  write_status_stub

  run env CAIRN_STATUS="$STATUS_STUB" \
    bash "$PARALLEL" batch --max 1 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.max' '1'
  assert_json_eq "$output" '[.selected[].phase] | join(",")' '7'
  assert_json_eq "$output" '[.deferred[].phase] | join(",")' '9'
  assert_json_eq "$output" '[.deferred[] | select(.phase == 9) | .reason][0]' 'above the --max 1 ceiling'
}

@test "the bridge: for TWO phases, the branch and worktree batch announces are byte-for-byte the ones prepare creates, and the two trees are isolated" {
  require_bd
  make_parallel_fixture
  write_status_stub

  run env CAIRN_STATUS="$STATUS_STUB" \
    bash "$PARALLEL" batch --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  local announced_branch_7 announced_branch_9 announced_wt_7 announced_wt_9
  announced_branch_7="$(jq -r '[.selected[] | select(.phase == 7) | .branch][0]' <<<"$output")"
  announced_branch_9="$(jq -r '[.selected[] | select(.phase == 9) | .branch][0]' <<<"$output")"
  announced_wt_7="$(jq -r '[.selected[] | select(.phase == 7) | .worktree][0]' <<<"$output")"
  announced_wt_9="$(jq -r '[.selected[] | select(.phase == 9) | .worktree][0]' <<<"$output")"

  # The slugs come from the 07-/09- phase directories, leading zero and all.
  [ "$announced_branch_7" = "phase/7-alpha" ]
  [ "$announced_branch_9" = "phase/9-beta" ]

  run bash "$PARALLEL" prepare 7 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  local created_branch_7 created_wt_7
  created_branch_7="$(jq -r '.branch' <<<"$output")"
  created_wt_7="$(jq -r '.worktree' <<<"$output")"

  run bash "$PARALLEL" prepare 9 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  local created_branch_9 created_wt_9
  created_branch_9="$(jq -r '.branch' <<<"$output")"
  created_wt_9="$(jq -r '.worktree' <<<"$output")"

  [ "$created_branch_7" = "$announced_branch_7" ]
  [ "$created_branch_9" = "$announced_branch_9" ]
  # Compared through realpath on BOTH sides: on macOS TMPDIR resolves via a
  # /var -> /private/var symlink, so a raw string compare could pass or fail
  # for reasons that have nothing to do with the bridge.
  [ "$(realpath_of "$created_wt_7")" = "$(realpath_of "$announced_wt_7")" ]
  [ "$(realpath_of "$created_wt_9")" = "$(realpath_of "$announced_wt_9")" ]

  [ -d "$created_wt_7" ]
  [ -d "$created_wt_9" ]
  [ "$created_wt_7" != "$created_wt_9" ]

  run git -C "$created_wt_7" rev-parse --abbrev-ref HEAD
  [ "$output" = "phase/7-alpha" ]
  run git -C "$created_wt_9" rev-parse --abbrev-ref HEAD
  [ "$output" = "phase/9-beta" ]

  # Two phases running at once means two trees that cannot see each other.
  echo "seven" > "$created_wt_7/from-phase-7.txt"
  echo "nine" > "$created_wt_9/from-phase-9.txt"
  [ ! -f "$created_wt_9/from-phase-7.txt" ]
  [ ! -f "$created_wt_7/from-phase-9.txt" ]
  [ ! -f "$MAIN_ROOT/from-phase-7.txt" ]
  [ ! -f "$MAIN_ROOT/from-phase-9.txt" ]
}

@test "batch refuses to invent a lot when cairn-status.py cannot be driven" {
  require_bd
  make_parallel_fixture

  local broken="$BATS_TEST_TMPDIR/nowhere/cairn-status.py"
  run env CAIRN_STATUS="$broken" \
    bash "$PARALLEL" batch --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 5 ]
  refute_in_output "Traceback"

  local garbage="$BATS_TEST_TMPDIR/garbage-status.py"
  cat > "$garbage" <<'PYEOF'
#!/usr/bin/env python3
print("this is not json")
PYEOF
  run env CAIRN_STATUS="$garbage" \
    bash "$PARALLEL" batch --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"
}

#-----------------------------------------------------------------------------
# Task 3: the refusal by lease leaves no trace, and the rollback only ever
# undoes what the refusing invocation itself created.
#
# Two distinct paths reach EXIT_HELD and they need two distinct tests:
#   - the read-only PRE-CHECK, reachable with a real second worktree, which
#     refuses before anything is created;
#   - the post-acquire RACE branch, only reachable when the lease is taken
#     inside the window between the pre-check and the acquire, which is what
#     the CAIRN_LEASE seam simulates. That is the only path where a rollback
#     has anything to undo, so it is the only test that can prove one.
#-----------------------------------------------------------------------------

@test "prepare on a phase held by a live holder exits 3 naming the holder and since-when, and leaves no worktree and no branch behind" {
  require_bd
  make_parallel_fixture

  local wt_b="$BATS_TEST_TMPDIR/holder"
  git worktree add -q "$wt_b" -b holder-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 3 --project-dir "$wt_b"
  [ "$status" -eq 0 ]
  run bash "$LEASE" status 3 --project-dir "$wt_b" --json
  local acquired_at
  acquired_at="$(jq -r '.acquired_at' <<<"$output")"

  run bash "$PARALLEL" prepare 3 --project-dir "$MAIN_ROOT"
  [ "$status" -eq 3 ]
  grep -qF "$wt_b" <<<"$output"
  grep -qF "$acquired_at" <<<"$output"

  # The two assertions that carry the weight.
  [ ! -d "$MAIN_ROOT-phase-3" ]
  run git -C "$MAIN_ROOT" rev-parse --verify --quiet refs/heads/phase/3-gamma
  [ "$status" -ne 0 ]

  # And the lease itself was not disturbed: still the other worktree's.
  run bash "$LEASE" status 3 --project-dir "$MAIN_ROOT" --json
  assert_json_eq "$output" '.holder' "$wt_b"
  assert_json_eq "$output" '.acquired_at' "$acquired_at"
}

@test "prepare rolls back its own worktree and branch when the lease is lost in the race window between the pre-check and the acquire" {
  require_bd
  make_parallel_fixture

  # A cairn-lease.py stand-in that reports the phase VACANT on the read-only
  # pre-check and then refuses the acquire with EXIT_HELD — precisely the
  # race the four-step order exists to survive, and unreachable with a real
  # lease because a real one is already held by the time the pre-check runs.
  local racing="$BATS_TEST_TMPDIR/racing-lease.py"
  cat > "$racing" <<'PYEOF'
#!/usr/bin/env python3
import json
import sys

VACANT = {"phase": 3, "id": None, "held": False, "holder": None,
          "actor": None, "host": None, "acquired_at": None,
          "heartbeat_at": None, "stale": False, "ttl_hours": 4}
TAKEN = {"phase": 3, "id": "stub-lease-1", "held": True,
         "holder": "/somewhere/else-phase-3", "actor": "the rival",
         "host": "elsewhere", "acquired_at": "2026-07-31T09:15:00+00:00",
         "heartbeat_at": "2026-07-31T09:15:00+00:00", "stale": False,
         "ttl_hours": 4}

verb = sys.argv[1] if len(sys.argv) > 1 else ""
if verb == "acquire":
    print(json.dumps(TAKEN))
    sys.exit(3)
print(json.dumps(VACANT))
sys.exit(0)
PYEOF

  run env CAIRN_LEASE="$racing" \
    bash "$PARALLEL" prepare 3 --project-dir "$MAIN_ROOT"
  [ "$status" -eq 3 ]
  grep -qF "/somewhere/else-phase-3" <<<"$output"
  grep -qF "2026-07-31T09:15:00+00:00" <<<"$output"

  # The rollback's whole job: the worktree this invocation created is gone,
  # and so is the branch it created with it.
  [ ! -d "$MAIN_ROOT-phase-3" ]
  run git -C "$MAIN_ROOT" rev-parse --verify --quiet refs/heads/phase/3-gamma
  [ "$status" -ne 0 ]
  run git -C "$MAIN_ROOT" worktree list --porcelain
  refute_in_output "$MAIN_ROOT-phase-3"
}

@test "prepare never removes a worktree it did not create, even when the acquire refuses" {
  require_bd
  make_parallel_fixture

  # Pre-create the phase-3 worktree by hand, exactly where and how prepare
  # would — so the refusing invocation finds it already there and creates
  # nothing of its own.
  git -C "$MAIN_ROOT" worktree add -q "$MAIN_ROOT-phase-3" -b phase/3-gamma
  echo "work already done here" > "$MAIN_ROOT-phase-3/precious.txt"

  local racing="$BATS_TEST_TMPDIR/racing-lease.py"
  cat > "$racing" <<'PYEOF'
#!/usr/bin/env python3
import json
import sys

verb = sys.argv[1] if len(sys.argv) > 1 else ""
if verb == "acquire":
    print(json.dumps({"phase": 3, "id": "stub-lease-1", "held": True,
                      "holder": "/somewhere/else-phase-3",
                      "actor": "the rival", "host": "elsewhere",
                      "acquired_at": "2026-07-31T09:15:00+00:00",
                      "heartbeat_at": "2026-07-31T09:15:00+00:00",
                      "stale": False, "ttl_hours": 4}))
    sys.exit(3)
print(json.dumps({"phase": 3, "id": None, "held": False, "holder": None,
                  "actor": None, "host": None, "acquired_at": None,
                  "heartbeat_at": None, "stale": False, "ttl_hours": 4}))
sys.exit(0)
PYEOF

  run env CAIRN_LEASE="$racing" \
    bash "$PARALLEL" prepare 3 --project-dir "$MAIN_ROOT"
  [ "$status" -eq 3 ]

  # Untouched: the pre-existing worktree, its content, and its branch.
  [ -d "$MAIN_ROOT-phase-3" ]
  [ -f "$MAIN_ROOT-phase-3/precious.txt" ]
  run git -C "$MAIN_ROOT" rev-parse --verify --quiet refs/heads/phase/3-gamma
  [ "$status" -eq 0 ]
}

@test "prepare repeated on the same phase from the same worktree exits 0 with created=false and creates no second branch" {
  require_bd
  make_parallel_fixture

  run bash "$PARALLEL" prepare 3 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.created' 'true'
  assert_json_eq "$output" '.branch' 'phase/3-gamma'
  local first_holder
  first_holder="$(jq -r '.lease.holder' <<<"$output")"

  run bash "$PARALLEL" prepare 3 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.created' 'false'
  assert_json_eq "$output" '.branch' 'phase/3-gamma'
  assert_json_eq "$output" '.lease.holder' "$first_holder"

  run git -C "$MAIN_ROOT" branch --list "phase/*"
  [ "$(grep -c . <<<"$output")" -eq 1 ]
}

@test "prepare on a phase whose lease is STALE proceeds and reclaims it, naming who it was reclaimed from" {
  require_bd
  make_parallel_fixture

  local wt_b="$BATS_TEST_TMPDIR/holder"
  git worktree add -q "$wt_b" -b holder-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 3 --project-dir "$wt_b" --json
  [ "$status" -eq 0 ]
  local lease_id acquired_at
  lease_id="$(jq -r '.id' <<<"$output")"
  acquired_at="$(jq -r '.acquired_at' <<<"$output")"

  # Age the heartbeat past the 4h TTL through bd directly, bypassing every
  # cairn script, rather than sleeping.
  local stale_ts
  stale_ts="$(python3 -c "
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) - timedelta(hours=5)).isoformat())
")"
  run bd update "$lease_id" --metadata \
    "{\"cairn\":{\"lease\":{\"phase\":3,\"holder\":\"$wt_b\",\"actor\":\"a\",\"host\":\"h\",\"acquired_at\":\"$acquired_at\",\"heartbeat_at\":\"$stale_ts\"}}}"
  [ "$status" -eq 0 ]

  run bash "$PARALLEL" prepare 3 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.created' 'true'
  local wt
  wt="$(jq -r '.worktree' <<<"$output")"
  local wt_real
  wt_real="$(git -C "$wt" rev-parse --show-toplevel)"
  assert_json_eq "$output" '.lease.holder' "$wt_real"
}

@test "cairn-parallel.sh with no subcommand exits 2; --help lists batch and prepare" {
  run bash "$PARALLEL"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash "$PARALLEL" --help
  [ "$status" -eq 0 ]
  grep -qF "batch" <<<"$output"
  grep -qF "prepare" <<<"$output"
}
