#!/usr/bin/env bats
# cairn-parallel.bats — exercises the parallel-phase driver's CLI contract
# (cairn-parallel.py / the cairn-parallel.sh wrapper): `prepare N` (create
# phase N's deterministically named worktree and take its lease pointing AT
# that worktree), `batch` (consume cairn-status.py's parallelism block and
# announce what can run, with each phase's branch and worktree resolved), and
# `reconcile` (report, without merging anything, what each phase produced and
# which lines both branches changed to the SAME value).
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

@test "cairn-parallel.sh with no subcommand exits 2; --help lists batch, prepare and reconcile" {
  run bash "$PARALLEL"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash "$PARALLEL" --help
  [ "$status" -eq 0 ]
  grep -qF "batch" <<<"$output"
  grep -qF "prepare" <<<"$output"
  grep -qF "reconcile" <<<"$output"
}

#=============================================================================
# Plan 18-02 — reconcile.
#
# These tests need `git` and nothing else: no bd, no lease, no worktree. They
# build ordinary phase/* branches by hand, which is the only thing reconcile
# looks at (it discovers work by the name prepare gave it, never by asking).
#
# TWO RULES HOLD IN EVERY TEST BELOW, and both are about not measuring the
# measurement:
#   - `reconcile` runs BEFORE any verification merge. A `git merge` in the
#     fixture's own tree moves a branch, and the next `merge-base` then
#     includes the other side — the detection would be measured against a
#     base that already contains what it is looking for.
#   - every verification merge happens in a THROWAWAY CLONE, so the fixture
#     the report was built from is never disturbed at all.
#=============================================================================

# Rewrite checks.txt: bump the count on line 1 to 14 (the convergent edit,
# byte-identical on both branches) and insert TEXT right after MARKER (the
# distinct block, in a different place on each branch). python3 rather than
# `sed -i`, whose in-place flag takes an argument on BSD and none on GNU.
bump_count_and_insert() {
  python3 - "$1" "$2" <<'PYEOF'
import sys
marker, text = sys.argv[1], sys.argv[2]
lines = open("checks.txt").read().splitlines()
lines[0] = "checks = 14"
lines.insert(lines.index(marker) + 1, text)
open("checks.txt", "w").write("\n".join(lines) + "\n")
PYEOF
}

# FIXTURE 1 — the REAL shape of the 14/15 incident (18-CONTEXT.md D-02).
# One file carrying both the convergence (the count on line 1, changed to the
# same value by both branches) and the divergence (each branch adds its own
# distinct block, at its own marker). The markers sit ~40 lines from the count
# and from each other, which is what keeps `-U0` from coalescing the two
# changes into one hunk — and what kept git from conflicting in the real
# incident. Leaves HEAD on the base branch, so `merge-base HEAD <branch>` is
# the base commit.
make_incident_fixture() {
  make_tmp_repo
  {
    echo "checks = 13"
    for i in $(seq 2 40); do echo "body line $i"; done
    echo "# MARKER-A"
    for i in $(seq 42 80); do echo "body line $i"; done
    echo "# MARKER-B"
    for i in $(seq 82 120); do echo "body line $i"; done
  } > checks.txt
  git add checks.txt >/dev/null
  git commit -qm "base: 13 checks"
  MAIN_ROOT="$(git rev-parse --show-toplevel)"
  BASE_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

  git checkout -qb phase/7-alpha
  bump_count_and_insert "# MARKER-A" "check 13: alpha added this one"
  git commit -qam "phase 7: one more check"

  git checkout -q "$BASE_BRANCH"
  git checkout -qb phase/9-beta
  bump_count_and_insert "# MARKER-B" "check 13: beta added this one"
  git commit -qam "phase 9: one more check"

  git checkout -q "$BASE_BRANCH"
}

# FIXTURE 2 — the PURE silent class: the convergent line is the ONLY change
# the two branches have in common, and each touches one more file of its own.
make_silent_fixture() {
  make_tmp_repo
  {
    echo "checks = 13"
    for i in $(seq 2 30); do echo "body line $i"; done
  } > shared.txt
  git add shared.txt >/dev/null
  git commit -qm "base: 13 checks"
  MAIN_ROOT="$(git rev-parse --show-toplevel)"
  BASE_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

  git checkout -qb phase/7-alpha
  python3 -c "
lines = open('shared.txt').read().splitlines()
lines[0] = 'checks = 14'
open('shared.txt', 'w').write('\n'.join(lines) + '\n')"
  echo "alpha only" > a.txt
  git add a.txt >/dev/null
  git commit -qam "phase 7"

  git checkout -q "$BASE_BRANCH"
  git checkout -qb phase/9-beta
  python3 -c "
lines = open('shared.txt').read().splitlines()
lines[0] = 'checks = 14'
open('shared.txt', 'w').write('\n'.join(lines) + '\n')"
  echo "beta only" > b.txt
  git add b.txt >/dev/null
  git commit -qam "phase 9"

  git checkout -q "$BASE_BRANCH"
}

# FIXTURE 3 — a real conflict: both branches add DIFFERENT lines at the SAME
# insertion point. This is the half git already handles well.
make_conflict_fixture() {
  make_tmp_repo
  { for i in $(seq 1 20); do echo "body line $i"; done; } > code.txt
  git add code.txt >/dev/null
  git commit -qm base
  MAIN_ROOT="$(git rev-parse --show-toplevel)"
  BASE_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

  git checkout -qb phase/7-alpha
  python3 -c "
lines = open('code.txt').read().splitlines()
lines.insert(10, 'alpha wrote this line')
open('code.txt', 'w').write('\n'.join(lines) + '\n')"
  git commit -qam "phase 7"

  git checkout -q "$BASE_BRANCH"
  git checkout -qb phase/9-beta
  python3 -c "
lines = open('code.txt').read().splitlines()
lines.insert(10, 'beta wrote a DIFFERENT line')
open('code.txt', 'w').write('\n'.join(lines) + '\n')"
  git commit -qam "phase 9"

  git checkout -q "$BASE_BRANCH"
}

# FIXTURE 4 — the false-positive guard: both branches edit the SAME file, far
# apart, with no line in common and no converging count. Nothing here is a
# finding of any kind.
make_disjoint_fixture() {
  make_tmp_repo
  { for i in $(seq 1 60); do echo "body line $i"; done; } > code.txt
  mkdir -p .planning
  printf 'status: executing\n' > .planning/STATE.md
  git add code.txt .planning >/dev/null
  git commit -qm base
  MAIN_ROOT="$(git rev-parse --show-toplevel)"
  BASE_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

  git checkout -qb phase/7-alpha
  python3 -c "
lines = open('code.txt').read().splitlines()
lines[4] = 'alpha rewrote line 5'
open('code.txt', 'w').write('\n'.join(lines) + '\n')"
  git commit -qam "phase 7"

  git checkout -q "$BASE_BRANCH"
  git checkout -qb phase/9-beta
  python3 -c "
lines = open('code.txt').read().splitlines()
lines[49] = 'beta rewrote line 50'
open('code.txt', 'w').write('\n'.join(lines) + '\n')"
  git commit -qam "phase 9"

  git checkout -q "$BASE_BRANCH"
}

# A throwaway clone of the fixture. Every verification merge happens in here:
# merging in the fixture's own tree would move a branch and poison the
# `merge-base` of anything measured afterwards.
clone_fixture() {
  CLONE="$BATS_TEST_TMPDIR/verify-clone-$$-${BATS_TEST_NUMBER:-0}"
  rm -rf "$CLONE"
  git clone -q "$MAIN_ROOT" "$CLONE"
  git -C "$CLONE" config user.email "cairn-tests@example.com"
  git -C "$CLONE" config user.name "Cairn Tests"
}

# A `git` shim on PATH that fails `merge-tree` the way a pre-2.38 git does —
# an "unknown option --write-tree" on stderr and exit 129 — and delegates
# everything else to the real binary, captured by absolute path so the shim
# cannot recurse into itself.
write_old_git_stub() {
  OLD_GIT_DIR="$BATS_TEST_TMPDIR/old-git"
  mkdir -p "$OLD_GIT_DIR"
  local real
  real="$(command -v git)"
  cat > "$OLD_GIT_DIR/git" <<EOF
#!/usr/bin/env bash
for a in "\$@"; do
  if [ "\$a" = "merge-tree" ]; then
    echo "error: unknown option --write-tree" >&2
    exit 129
  fi
done
exec "$real" "\$@"
EOF
  chmod +x "$OLD_GIT_DIR/git"
}

#-----------------------------------------------------------------------------
# Task 2, fixture 1: the incident itself. The two measurements live in ONE
# test, side by side, because it is the PAIR that documents why the command
# exists — a merge git is satisfied with, and a report that names the damage.
#
# How to break it, measured rather than assumed: replace the strict base-range
# equality in convergent_edits() with anything looser, or stop comparing the
# range at all, and the reported base_line stops being 1. Skipping the
# `-U0` and taking git's default context coalesces the count hunk with the
# nearby body and the file drops out entirely. (Deleting the CONTENT
# comparison does NOT redden this test — in this fixture the only co-located
# hunk is the convergent one. That mutation is caught by fixture 3, where the
# same base range carries different text; the note there explains why.)
# Moving the inserted block ADJACENT to the count makes the convergence stop
# being declared: that is the MEASURED LIMIT written into the docstring, not a
# bug — in that arrangement `-U0` coalesces the hunks and git conflicts on its
# own, so the operator is stopped either way.
#-----------------------------------------------------------------------------

@test "reconcile names the convergent edit in the incident's real shape — the same file where the git merge succeeds without reporting a single conflict" {
  make_incident_fixture

  # (a) reconcile FIRST, before any merge exists anywhere.
  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 6 ]
  local report="$output"
  assert_json_eq "$report" '.pairs | length' '1'
  assert_json_eq "$report" '.pairs[0].convergent_edits | length' '1'
  assert_json_eq "$report" '.pairs[0].convergent_edits[0].file' 'checks.txt'
  assert_json_eq "$report" '.pairs[0].convergent_edits[0].base_line' '1'
  assert_json_eq "$report" '.pairs[0].convergent_edits[0].new_lines | join("")' 'checks = 14'
  assert_json_eq "$report" '.pairs[0].convergent_edits[0].branches | join(",")' 'phase/7-alpha,phase/9-beta'
  # git has nothing to say about this pair — that is the entire point.
  assert_json_eq "$report" '.pairs[0].conflicts | length' '0'
  assert_json_eq "$report" '.findings_total' '1'
  # PAR-04's other half: what each phase produced.
  assert_json_eq "$report" '.branches | length' '2'
  assert_json_eq "$report" '[.branches[] | select(.phase == 7) | .commits][0]' '1'
  assert_json_eq "$report" '[.branches[] | select(.phase == 9) | .files][0]' '1'

  # (b) and now the real merge, in a throwaway clone, on the very same file.
  clone_fixture
  run git -C "$CLONE" merge --no-edit origin/phase/7-alpha
  [ "$status" -eq 0 ]
  run git -C "$CLONE" merge --no-edit origin/phase/9-beta
  [ "$status" -eq 0 ]
  refute_in_output "CONFLICT"
  # git is not silent about the FILE here — both branches touched it in
  # different places, so it says `Auto-merging checks.txt`. What it never says
  # is that anything about it needs a human. `Auto-merging` is git reporting
  # success.
  grep -qF "Auto-merging checks.txt" <<<"$output"

  # (c) the damage, concretely: one count, two blocks numbered the same.
  run head -1 "$CLONE/checks.txt"
  [ "$output" = "checks = 14" ]
  run grep -c "^check 13" "$CLONE/checks.txt"
  [ "$output" -eq 2 ]
}

#-----------------------------------------------------------------------------
# Task 2, fixture 2: the pure silent class, where git does not mention the
# shared file AT ALL.
#
# The literal assertion is MERGE-ORDER DEPENDENT, and it is pinned here rather
# than discovered at run time. Measured:
#   merge 1 (phase/7-alpha):  a.txt | 1 +   shared.txt | 2 +-
#   merge 2 (phase/9-beta):   b.txt | 1 +
# The first merge still lists the shared file, because the count really did
# change against the base. Only after the count is already 14 in HEAD does the
# other side stop changing anything in it and the file vanish completely.
# Merging just ONE branch here writes a red test, and the tempting repair —
# weakening to `refute_in_output CONFLICT` — would pass with the feature
# removed and would erase the mutest end of the class.
#
# How to break it: loosen the base-range equality in convergent_edits(), or
# drop the shared-file intersection, and the report stops naming shared.txt
# line 1.
#-----------------------------------------------------------------------------

@test "reconcile names the convergent edit in the pure silent class, where the SECOND merge does not mention the shared file at all" {
  make_silent_fixture

  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" '.pairs[0].convergent_edits | length' '1'
  assert_json_eq "$output" '.pairs[0].convergent_edits[0].file' 'shared.txt'
  assert_json_eq "$output" '.pairs[0].convergent_edits[0].base_line' '1'
  assert_json_eq "$output" '.pairs[0].convergent_edits[0].new_lines | join("")' 'checks = 14'
  assert_json_eq "$output" '.pairs[0].conflicts | length' '0'

  clone_fixture
  # Merge 1 — the shared file IS still listed here, and that is why the
  # assertion below is about merge 2.
  run git -C "$CLONE" merge --no-edit origin/phase/7-alpha
  [ "$status" -eq 0 ]
  grep -qF "shared.txt" <<<"$output"

  # Merge 2 — the strongest form of the claim: git says nothing whatsoever
  # about the file both branches changed.
  run git -C "$CLONE" merge --no-edit origin/phase/9-beta
  [ "$status" -eq 0 ]
  refute_in_output "shared.txt"
  refute_in_output "CONFLICT"
  grep -qF "b.txt" <<<"$output"

  run head -1 "$CLONE/shared.txt"
  [ "$output" = "checks = 14" ]
}

#-----------------------------------------------------------------------------
# Task 2, fixture 3: a real conflict is reported with its file — and reconcile
# still merges nothing, which is why the fixture is byte-identical afterwards.
#
# This fixture is ALSO where the content half of the detection rule is proven,
# and it is the only place in this suite where it can be. Measured: both
# branches insert at the same point, so both sides produce `@@ -10,0 +11 @@` —
# the SAME base range carrying DIFFERENT text. Deleting the
# `by_range_a[key] != by_range_b[key]` comparison in convergent_edits() turns
# this conflict into a reported "convergent edit", and the assertion below
# goes red. (The plan expected that mutation to redden fixtures 1 and 2
# instead; measured, it does not — in those two the only co-located hunk IS
# the convergent one, so dropping the comparison changes nothing there. The
# check has to live here or it is not covered at all.)
#-----------------------------------------------------------------------------

@test "reconcile reports a real merge conflict by file, never as a convergent edit, exits 6, and leaves the fixture's own tree untouched" {
  make_conflict_fixture
  local head_before
  head_before="$(git -C "$MAIN_ROOT" rev-parse "$BASE_BRANCH")"

  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 6 ]
  # Same base range, different text: a conflict, and emphatically NOT an
  # accidental agreement. Reporting it as one would tell the operator that
  # git had already silently taken a side, which is the opposite of true.
  assert_json_eq "$output" '.pairs[0].convergent_edits | length' '0'
  assert_json_eq "$output" '.pairs[0].conflicts | length' '1'
  assert_json_eq "$output" '.pairs[0].conflicts[0].path' 'code.txt'
  assert_json_eq "$output" '.pairs[0].conflicts[0].messages | length' '1'
  assert_json_eq "$output" '.pairs[0].conflicts[0].messages[0] | startswith("CONFLICT (content)")' 'true'
  assert_json_eq "$output" '.pairs[0].conflicts_note' 'null'
  # Reported, never resolved: no merge happened, so no MERGE_HEAD, no moved
  # branch, no conflict markers on disk.
  [ ! -f "$MAIN_ROOT/.git/MERGE_HEAD" ]
  [ "$(git -C "$MAIN_ROOT" rev-parse "$BASE_BRANCH")" = "$head_before" ]
  run git -C "$MAIN_ROOT" status --porcelain
  [ -z "$output" ]
  refute_in_output "<<<<<<<"

  # And git agrees it is a conflict, in a clone that is allowed to try.
  clone_fixture
  run git -C "$CLONE" merge --no-edit origin/phase/7-alpha
  [ "$status" -eq 0 ]
  run git -C "$CLONE" merge --no-edit origin/phase/9-beta
  [ "$status" -ne 0 ]
  grep -qF "CONFLICT" <<<"$output"
}

#-----------------------------------------------------------------------------
# Task 2, fixture 4: the false-positive guard.
#
# How to break it: replace the strict base-range equality in
# convergent_edits() with an overlap test, or drop the range comparison
# entirely, and this goes red — both branches DID edit the same file, just
# nowhere near each other.
#-----------------------------------------------------------------------------

@test "reconcile does NOT call two disjoint edits to the same file a convergent edit, and exits 0" {
  make_disjoint_fixture

  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  # Both branches really did touch code.txt — the guard is about WHERE.
  assert_json_eq "$output" '[.branches[] | select(.phase == 7) | .files][0]' '1'
  assert_json_eq "$output" '[.branches[] | select(.phase == 9) | .files][0]' '1'
  assert_json_eq "$output" '.pairs | length' '1'
  assert_json_eq "$output" '.pairs[0].convergent_edits | length' '0'
  assert_json_eq "$output" '.pairs[0].conflicts | length' '0'
  assert_json_eq "$output" '.findings_total' '0'

  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT"
  [ "$status" -eq 0 ]
  grep -qF "no convergent edit and no conflict" <<<"$output"
}

#-----------------------------------------------------------------------------
# Task 2, fixture 5: a phase branch that wrote to a planning file is a NAMED
# finding and, on its own, changes nothing about the exit code (D-03's
# reporting half; the failing variant is parked in 18-CONTEXT.md's <deferred>,
# and reporting is not failing).
#-----------------------------------------------------------------------------

@test "reconcile names a phase branch that wrote to .planning/STATE.md, and that alone does not move the exit code off 0" {
  make_disjoint_fixture
  git checkout -q phase/7-alpha
  printf 'status: executing\nactive_phase: "7"\n' > .planning/STATE.md
  git commit -qam "phase 7 wrote a planning file it was told not to"
  git checkout -q "$BASE_BRANCH"

  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.planning_writes | length' '1'
  assert_json_eq "$output" '.planning_writes[0].branch' 'phase/7-alpha'
  assert_json_eq "$output" '.planning_writes[0].phase' '7'
  assert_json_eq "$output" '.planning_writes[0].files | join(",")' '.planning/STATE.md'
  # The finding exists and the exit code is still 0 — that is the assertion.
  assert_json_eq "$output" '.findings_total' '0'

  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT"
  [ "$status" -eq 0 ]
  grep -qF ".planning/STATE.md" <<<"$output"
}

#-----------------------------------------------------------------------------
# Task 2, fixture 6: a git that cannot pre-compute conflicts produces UNKNOWN,
# never agreement (Pitfall 3).
#
# The fixture is the disjoint one on purpose: it has no convergent edit and no
# conflict, so findings_total is 0 and the ONLY thing that can push the exit
# to 6 is not-knowing. On any other fixture this test would pass for the wrong
# reason.
#-----------------------------------------------------------------------------

@test "reconcile reports conflicts as null with a note, and still exits 6, when git cannot run merge-tree --write-tree" {
  make_disjoint_fixture
  write_old_git_stub

  run env PATH="$OLD_GIT_DIR:$PATH" \
    bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 6 ]
  refute_in_output "Traceback"
  assert_json_eq "$output" '.pairs[0].conflicts' 'null'
  assert_json_eq "$output" '.pairs[0].conflicts_note | contains("UNKNOWN")' 'true'
  assert_json_eq "$output" '.pairs[0].conflicts_note | contains("not clean")' 'true'
  # Nothing else is a finding here: the 6 is bought entirely by not-knowing.
  assert_json_eq "$output" '.findings_total' '0'
  assert_json_eq "$output" '.pairs[0].convergent_edits | length' '0'
  assert_json_eq "$output" '.git_version != null' 'true'

  run env PATH="$OLD_GIT_DIR:$PATH" \
    bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT"
  [ "$status" -eq 6 ]
  grep -qF "UNKNOWN" <<<"$output"
  # The same fixture on a git that CAN run it exits 0 — so the 6 above is the
  # degradation and not the fixture.
  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT"
  [ "$status" -eq 0 ]
}

@test "reconcile in a repo with no phase/* branch exits 0, with empty lists and a line saying there is nothing to reconcile" {
  make_tmp_repo
  echo "nothing to see" > file.txt
  git add file.txt >/dev/null
  git commit -qm base
  MAIN_ROOT="$(git rev-parse --show-toplevel)"

  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.branches | length' '0'
  assert_json_eq "$output" '.pairs | length' '0'
  assert_json_eq "$output" '.planning_writes | length' '0'
  assert_json_eq "$output" '.findings_total' '0'

  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT"
  [ "$status" -eq 0 ]
  grep -qF "nothing to reconcile" <<<"$output"
}

@test "reconcile --phases restricts the report to the phases named, and a non-numeric value is a usage error rather than a quietly empty report" {
  make_incident_fixture

  run bash "$PARALLEL" reconcile --phases 7 --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.branches | length' '1'
  assert_json_eq "$output" '[.branches[].phase] | join(",")' '7'
  # One branch is no pair, so the convergence cannot be seen at all — which
  # is exactly why the filter must never be applied silently.
  assert_json_eq "$output" '.pairs | length' '0'

  run bash "$PARALLEL" reconcile --phases 7,nine --project-dir "$MAIN_ROOT"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"
}

#-----------------------------------------------------------------------------
# Task 3: the non-write guarantee, proven twice — by mutation against a real
# fixture, and statically over the source. Phase 17 used both for
# cairn-reconcile.py for the same reason: one proof is about what the code
# does, the other about what it says, and neither substitutes for the other.
#-----------------------------------------------------------------------------

# sha256 of every file in DIR outside .git, path-sorted. The `.git` exclusion
# is deliberate and named in the test: `merge-tree --write-tree` DOES add
# loose objects to the object database — that is what lets it compute a merge
# with no working tree — while moving no ref and touching no file. Branch
# heads are snapshotted separately, which is the part that would actually
# matter.
tree_digest() {
  python3 - "$1" <<'PYEOF'
import hashlib, os, sys
root = sys.argv[1]
rows = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = sorted(d for d in dirnames if d != ".git")
    for name in sorted(filenames):
        path = os.path.join(dirpath, name)
        with open(path, "rb") as fh:
            rows.append(os.path.relpath(path, root) + "  "
                        + hashlib.sha256(fh.read()).hexdigest())
print("\n".join(sorted(rows)))
PYEOF
}

@test "read-only, by mutation: reconcile leaves the working tree, every phase/* head and every file hash exactly as it found them" {
  make_incident_fixture

  local status_before heads_before digest_before
  status_before="$(git -C "$MAIN_ROOT" status --porcelain)"
  heads_before="$(git -C "$MAIN_ROOT" for-each-ref \
    --format='%(refname:short) %(objectname)' refs/heads/)"
  digest_before="$(tree_digest "$MAIN_ROOT")"

  # The run that has the most to do: it finds something, so every code path
  # that could have written is exercised.
  run bash "$PARALLEL" reconcile --project-dir "$MAIN_ROOT" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" '.pairs[0].convergent_edits | length' '1'

  [ "$(git -C "$MAIN_ROOT" status --porcelain)" = "$status_before" ]
  [ "$(git -C "$MAIN_ROOT" for-each-ref \
       --format='%(refname:short) %(objectname)' refs/heads/)" = "$heads_before" ]
  [ "$(tree_digest "$MAIN_ROOT")" = "$digest_before" ]
  # A merge, a checkout or a commit would have left one of these behind.
  [ ! -f "$MAIN_ROOT/.git/MERGE_HEAD" ]
  [ "$(git -C "$MAIN_ROOT" rev-parse --abbrev-ref HEAD)" = "$BASE_BRANCH" ]
}

@test "read-only, statically: the reconcile region of the source carries no bd write verb, no journal write subcommand and no writing git verb" {
  local src="$CAIRN_SCRIPTS_DIR/cairn-parallel.py"
  [ -f "$src" ]

  # The region is delimited by markers in the source itself, because the
  # claim is about `reconcile` — `prepare` legitimately creates worktrees and
  # takes leases a few hundred lines above.
  local region="$BATS_TEST_TMPDIR/reconcile-region.py"
  awk '/RECONCILE-READ-ONLY-REGION-BEGIN/,/RECONCILE-READ-ONLY-REGION-END/' \
    "$src" > "$BATS_TEST_TMPDIR/region-raw.py"
  grep -v '^#' "$BATS_TEST_TMPDIR/region-raw.py" > "$region"

  # The extraction found the real thing, and ONLY the real thing. Without
  # these three, every count below would be a vacuous zero — and a range that
  # over-matched into `prepare` (which legitimately creates worktrees and
  # deletes branches) would fail for the opposite reason.
  grep -qF "def cmd_reconcile" "$region"
  grep -qF "def convergent_edits" "$region"
  [ "$(grep -c . "$region")" -gt 100 ]
  run bash -c "grep -cF 'def cmd_prepare' '$region'"
  [ "$output" -eq 0 ]

  run bash -c "grep -Ec '\"(create|update|close|reopen)\"' '$region'"
  [ "$output" -eq 0 ]
  run bash -c "grep -Ec '\"(observe|lease|append)\"' '$region'"
  [ "$output" -eq 0 ]
  # Head-of-argument-list, because "branch" and "worktree" are also honest
  # JSON keys in this script's own output while `["branch"` can only be an
  # invocation of `git branch`. Read subcommands survive for free:
  # `["merge-base"` and `["merge-tree"` do not match `["merge"`.
  run bash -c "grep -Ec '\[\"(merge|checkout|commit|reset|clean|stash|branch|worktree|apply|push|rebase)\"' '$region'"
  [ "$output" -eq 0 ]

  # The comment filter is load-bearing, not decoration: the region's own
  # banner NAMES those tokens in the shape the grep looks for, so the same
  # check over the UNFILTERED text finds them. Asserting that here is what
  # keeps someone from "simplifying" the filter away and quietly turning the
  # check into one that only ever reads comments.
  run bash -c "grep -Ec '\[\"(merge|checkout|commit|reset|clean|stash|branch|worktree|apply|push|rebase)\"' '$BATS_TEST_TMPDIR/region-raw.py'"
  [ "$output" -gt 0 ]
}
