#!/usr/bin/env bats
# cairn-land.bats — "did this work enter the control branch", answered from the
# git repository already on disk, and the proof that answering it opens no
# socket and invokes no network tool.
#
# Under test: cairn/scripts/cairn-land.py — the control-branch detection
# (detect), the one confirmation that puts it on record (apply), and the
# per-phase landing verdict (report) that cairn-status.py and cairn-doctor.py
# both render from without re-deriving a byte of it.
#
# ─────────────────────────────────────────────────────────────────────────────
# EVERY ASSERTION IS ON THE EXACT VALUE, NEVER ON A NEGATION
#
# The vocabulary is `landed` / `partial` / `unlanded` / `unknown`, and
# `!= "landed"` is satisfied by all three of the others — which are three
# different instructions to whoever reads the board. So every check below
# names the value it expects.
#
# ─────────────────────────────────────────────────────────────────────────────
# THE ABSENCE OF NETWORK: MEASURED versus ASSUMED
#
# The same three layers plan 29-05 built for the board, pointed at this script,
# because this is the file that grew git into the answer and a live PR fetch is
# the change somebody will plausibly write here next.
#
# MEASURED (reproduced offline by the layer-2 liveness test): with the socket
# tripwire installed, `subprocess.run(["curl", ...])` inside the SAME process
# raises nothing at all — a child does not inherit a patched `socket` module.
# A socket-only test would therefore be green on the day this script learned to
# shell out to `gh`.
#
#   Layer 1, inside the process: a sitecustomize that raises on
#     socket.connect / connect_ex. Liveness control: an in-process connection
#     under the same PYTHONPATH, which MUST fail.
#   Layer 2, outside the process: a PATH holding only git / python3 / jq plus a
#     trapped curl and wget that log their own argv. Liveness control: a curl
#     started as a child under both layers, which MUST show up in the log while
#     layer 1 stays silent.
#   Layer 3, before either runs: a structural inventory of every
#     subprocess.run in cairn-land.py, asserting each invokes an allowlisted
#     binary. Liveness control: a synthetic source carrying a curl call site,
#     which the same inventory MUST reject.
#
# ASSUMED, and out of reach of all three: what `git` itself does inside its own
# process. It is a third-party binary on the allowlist because the whole answer
# depends on it. What is proved here is that THIS script opens no socket and
# invokes no network tool, in its own process or in any child it starts.
#
# Assertion style note (same as cairn-status.bats): a failing `[[ ]]` or
# `! cmd` mid-test does NOT fail a bats test on this bash, so every check lands
# on a plain `[ ]` over a run-captured `$status`, or on an explicit
# `if ... return 1` block.

load 'helpers'

LAND_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-land.sh"
LAND_PY="$CAIRN_SCRIPTS_DIR/cairn-land.py"
STATUS_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-status.sh"
STATUS_PY="$CAIRN_SCRIPTS_DIR/cairn-status.py"

# A repo with a real, small, fully-known history:
#
#   c1  feat(03-01): alpha plan        touches .planning/phases/03-alpha/
#   c2  chore(03): close phase 3       touches NOTHING under phases/
#   c3  feat(04-01): beta plan         touches .planning/phases/04-beta/
#
# c2 is the whole reason attribution has two sources. It is modelled on
# `6545a5c chore(29): fecha a fase 29 …` in this repository, MEASURED
# 2026-08-06 to touch ROADMAP.md / STATE.md / REQUIREMENTS.md and NOT the phase
# directory: path attribution alone never sees the commit that closes a phase.
make_land_repo() {
  make_tmp_repo
  mkdir -p .planning/phases/03-alpha .planning/phases/04-beta

  echo "plan" > .planning/phases/03-alpha/03-01-PLAN.md
  git add -A >/dev/null
  git commit -qm "feat(03-01): alpha plan"
  C1="$(git rev-parse HEAD)"

  echo "roadmap" > .planning/ROADMAP.md
  git add -A >/dev/null
  git commit -qm "chore(03): close phase 3"
  C2="$(git rev-parse HEAD)"

  echo "plan" > .planning/phases/04-beta/04-01-PLAN.md
  git add -A >/dev/null
  git commit -qm "feat(04-01): beta plan"
  C3="$(git rev-parse HEAD)"
}

# A remote-tracking ref without a remote: update-ref writes exactly the same
# ref a fetch would, which is what detection and `rev-list --not` read.
set_remote_branch() {
  git update-ref "refs/remotes/origin/$1" "$2"
}

land_json() {
  run bash "$LAND_SH" "$@" --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
}

assert_output_has() {
  if ! printf '%s\n' "$output" | grep -qF -- "$1"; then
    echo "expected the output to contain '$1', it does not:" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}

assert_output_lacks() {
  if printf '%s\n' "$output" | grep -qF -- "$1"; then
    echo "expected the output NOT to contain '$1', it does:" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}

# ─── Detection: it degrades, it never dies ───────────────────────────────────

@test "detect reads refs/remotes/origin/HEAD when the remote publishes one" {
  make_land_repo
  set_remote_branch main "$C2"
  git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
  land_json detect
  assert_json_eq "$output" '.source' 'origin-head'
  assert_json_eq "$output" '.branches | join(",")' 'origin/main'
}

@test "detect degrades to the conventional names when origin/HEAD is absent" {
  # THE MEASUREMENT THIS BRANCH EXISTS FOR. In THIS repository,
  # `git symbolic-ref refs/remotes/origin/HEAD` exits 128 — the most obvious
  # source of the answer simply is not there. A detector that read only it
  # would report nothing on the repo it was written in.
  make_land_repo
  set_remote_branch main "$C2"
  run git symbolic-ref refs/remotes/origin/HEAD
  [ "$status" -ne 0 ]

  land_json detect
  assert_json_eq "$output" '.source' 'conventional'
  assert_json_eq "$output" '.branches | join(",")' 'origin/main'
}

@test "detect returns BOTH control branches when gitflow has both" {
  # develop before main is precedence, not taste: in a gitflow repo work lands
  # on develop FIRST, and a detector that answered only `main` would call every
  # merged feature "not landed" for the whole life of a release.
  make_land_repo
  set_remote_branch main "$C2"
  set_remote_branch develop "$C3"
  land_json detect
  assert_json_eq "$output" '.branches | join(",")' 'origin/develop,origin/main'
}

@test "a local branch named feature/develop is not read as remote-tracking" {
  # Breaks by: resolving branch names through `%(refname:short)` and splitting
  # on the slash. `feature/develop` short-forms to something with a slash in it
  # exactly like `origin/develop` does, and a reader that guessed from the
  # short name would file this local topic branch as the remote control branch.
  make_land_repo
  git branch feature/develop "$C1"
  git branch develop "$C1"
  land_json detect
  assert_json_eq "$output" '.source' 'conventional'
  assert_json_eq "$output" '.branches | join(",")' 'develop'
  assert_json_eq "$output" '.branches | index("feature/develop")' 'null'
}

@test "the branch HEAD is standing on is never detected as the control branch" {
  # MEASURED 2026-08-06, and this test exists because the measurement was a
  # DEFECT this fixture caught: `git init` leaves the checkout on a branch
  # called `main` or `master`, both conventional names, and a detector that
  # took them reported every phase of a fresh repository as `landed` — a green
  # produced by the fixture rather than by the work. A branch you are standing
  # on contains your work by construction; asking whether the work entered it
  # is not the question anybody has.
  make_land_repo
  local head_branch
  head_branch="$(git rev-parse --abbrev-ref HEAD)"
  case "$head_branch" in
    main|master) : ;;
    *) skip "git init did not leave HEAD on a conventional name" ;;
  esac
  land_json detect
  assert_json_eq "$output" '.source' 'none'
  assert_json_eq "$output" '.branches | length' '0'
}

@test "detect says so, in words, when there is nothing to compare against" {
  make_tmp_repo
  land_json detect
  assert_json_eq "$output" '.source' 'none'
  assert_json_eq "$output" '.branches | length' '0'
  assert_json_eq "$output" '.ask' 'false'
}

# ─── The one confirmation, and it goes through the config's owner ────────────

@test "apply records the branches through cairn-config.py and nothing else" {
  make_land_repo
  set_remote_branch main "$C2"
  run bash "$LAND_SH" apply --branches origin/main --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written' 'true'

  # It lives in the file cairn-config.py owns, under that script's own key.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-config.sh" get git.control_branches \
    --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' 'origin/main'
  assert_json_eq "$output" '.source' 'file'
}

@test "apply on record twice writes nothing and exits 3" {
  make_land_repo
  set_remote_branch main "$C2"
  bash "$LAND_SH" apply --branches origin/main --project-dir "$PWD" >/dev/null
  local before
  before="$(cat .cairn/config.json)"
  run bash "$LAND_SH" apply --branches origin/main --project-dir "$PWD" --json
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.written' 'false'
  [ "$before" = "$(cat .cairn/config.json)" ]
}

@test "apply refuses a branch no ref resolves, and writes nothing" {
  # A control branch nobody can resolve turns every verdict into `unknown`
  # forever. A config that reads plausibly while answering nothing is worse
  # than no config at all, so this is a refusal and not a warning.
  make_land_repo
  set_remote_branch main "$C2"
  run bash "$LAND_SH" apply --branches origin/main,origin/nope \
    --project-dir "$PWD" --json
  [ "$status" -eq 2 ]
  [ ! -f .cairn/config.json ]
}

@test "a recorded answer outranks detection, and the report says which" {
  make_land_repo
  set_remote_branch main "$C2"
  set_remote_branch develop "$C3"
  bash "$LAND_SH" apply --branches origin/main --project-dir "$PWD" >/dev/null
  land_json report
  assert_json_eq "$output" '.control.source' 'config'
  assert_json_eq "$output" '.control.branches | join(",")' 'origin/main'
}

@test "before anyone confirms, the report says the branch was detected" {
  make_land_repo
  set_remote_branch main "$C2"
  land_json report
  # `detected`, not `config`: the board is useful before the question is
  # answered, and it never pretends a guess is a decision.
  assert_json_eq "$output" '.control.source' 'detected'
}

# ─── The verdict, on exact values ────────────────────────────────────────────

@test "a phase whose every commit is on the control branch reads landed" {
  make_land_repo
  set_remote_branch main "$C2"
  land_json report
  assert_json_eq "$output" '.phases["3"].status' 'landed'
  assert_json_eq "$output" '.phases["3"].branches["origin/main"]' 'landed'
}

@test "a phase whose commits are all ahead of the branch reads unlanded" {
  make_land_repo
  set_remote_branch main "$C2"
  land_json report
  assert_json_eq "$output" '.phases["4"].status' 'unlanded'
  assert_json_eq "$output" '.phases["4"].branches["origin/main"]' 'unlanded'
}

@test "the closing commit is attributed by SCOPE, not by the phase directory" {
  # THE LOAD-BEARING TEST FOR TWO SOURCES. c2 (`chore(03): close phase 3`)
  # touches nothing under .planning/phases/, so path attribution alone finds
  # ONE commit for phase 3. Breaks by: deleting the scope pass, which drops
  # this count to 1 and the sources list to just `path`.
  make_land_repo
  set_remote_branch main "$C2"
  land_json report
  assert_json_eq "$output" '.phases["3"].commits' '2'
  assert_json_eq "$output" '.phases["3"].sources | sort | join(",")' \
    'path,scope'
}

@test "entrou na develop, ainda nao na main is partial, and the map says which" {
  # Gitflow, stated exactly: phase 4 is on develop and not on main. That is
  # information, not ambiguity, so the one-word verdict is `partial` and the
  # per-branch map right beside it carries the two different answers.
  make_land_repo
  set_remote_branch main "$C2"
  set_remote_branch develop "$C3"
  land_json report
  assert_json_eq "$output" '.phases["4"].status' 'partial'
  assert_json_eq "$output" '.phases["4"].branches["origin/develop"]' 'landed'
  assert_json_eq "$output" '.phases["4"].branches["origin/main"]' 'unlanded'
  # And a phase that made BOTH is landed, in the same report — without this
  # the previous three lines would pass against a report that answered
  # `partial` for everything.
  assert_json_eq "$output" '.phases["3"].status' 'landed'
}

@test "no control branch is unknown with a reason, never unlanded" {
  # The distinction the whole phase rests on: "I looked and it is not there"
  # and "I could not look" are different sentences, and only the first one
  # licenses anybody to push.
  make_land_repo
  land_json report
  assert_json_eq "$output" '.answered' 'false'
  assert_json_eq "$output" '.reason' 'no-branch'
  assert_json_eq "$output" '.phases["3"].status' 'unknown'
  assert_json_eq "$output" '.phases["3"].reason' 'no-branch'
}

@test "a phase with no commit at all is simply absent from the report" {
  # And that absence is the consumer's `no-commits`: this script reports what
  # the history carries and never invents a row for a phase the history does
  # not mention. Phase 9 exists nowhere in this fixture.
  make_land_repo
  set_remote_branch main "$C2"
  land_json report
  assert_json_eq "$output" '.phases | has("9")' 'false'
  assert_json_eq "$output" '.phases | keys | sort | join(",")' '3,4'
}

@test "report degrades instead of crashing outside a git work tree" {
  local outside="$BATS_TEST_TMPDIR/not-a-repo"
  mkdir -p "$outside/.planning"
  run bash "$LAND_SH" report --project-dir "$outside" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.answered' 'false'
  assert_json_eq "$output" '.reason' 'no-git'
}

# ─── The board consumes it, and only when there is something to consume ──────

@test "the board carries the landing suffix on the phase row and the task row" {
  require_bd
  make_tmp_repo
  make_board_fixture "$PWD"
  git add -A >/dev/null 2>&1 || true
  git commit -qm "feat(03-01): board fixture" >/dev/null 2>&1
  set_remote_branch main "$(git rev-parse HEAD)"
  echo x > x.txt
  git add x.txt >/dev/null
  git commit -qm "feat(04-01): ahead of the control branch" >/dev/null

  run bash "$STATUS_SH" --width 140 --color=never
  [ "$status" -eq 0 ]
  assert_output_has "⤒ origin/main"
}

@test "with no control branch the board renders no landing suffix at all" {
  # The rule plan 29-05 proved and this one inherits: no datum, no suffix, no
  # byte. It is what keeps tests/cairn-board-invariance.bats' seven committed
  # renders identical — their fixture is a git repo with no remote.
  require_bd
  make_tmp_repo
  make_board_fixture "$PWD"
  run bash "$STATUS_SH" --width 140 --color=never
  [ "$status" -eq 0 ]
  assert_output_lacks "⤒"
  assert_output_lacks "not in"
}

@test "--json carries landing per phase and per task, always in the same shape" {
  require_bd
  make_tmp_repo
  make_board_fixture "$PWD"
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  # Additive for EVERY row, not only the ones with a value — the same rule
  # `tracker` follows one plan earlier.
  assert_json_eq "$output" '[.phases[] | has("landed")] | unique | join(",")' \
    'true'
  assert_json_eq "$output" \
    '[.ready[], .doing[], .blocked[]] | map(has("landed")) | unique | join(",")' \
    'true'
  # With no remote in this fixture the answer is unknown, and it says why.
  assert_json_eq "$output" '.phases[0].landed.status' 'unknown'
  assert_json_eq "$output" '.landing.control.source' 'none'
}

@test "a task naming no phase reads unknown with no-phase, never landed" {
  require_bd
  make_tmp_repo
  make_board_fixture "$PWD"
  # `brd-` is this fixture's own id prefix; bd refuses any other.
  bd create "unlabelled work" --id brd-900 -p 1 >/dev/null
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.ready[] | select(.id=="brd-900") | .landed.status' 'unknown'
  assert_json_eq "$output" \
    '.ready[] | select(.id=="brd-900") | .landed.reason' 'no-phase'
}

# ─── Which pull request took it there — two words, neither is "none" ────────

@test "a squash-merge title suffix is found, with its exact source" {
  make_land_repo
  git commit -q --allow-empty -m "feat(03-02): alpha follow-up (#18)"
  set_remote_branch main "$(git rev-parse HEAD)"
  land_json report
  assert_json_eq "$output" '.phases["3"].pr.status' 'found'
  assert_json_eq "$output" '.phases["3"].pr.number' '18'
  assert_json_eq "$output" '.phases["3"].pr.source' 'squash-subject'
}

@test "a GitHub merge subject is found, and outranks a trailing paren" {
  # The commit touches phase 3's directory, so PATH attribution places it —
  # a merge subject carries no conventional-commit scope, which is exactly why
  # the two attribution sources exist.
  make_land_repo
  echo more > .planning/phases/03-alpha/03-02-PLAN.md
  git add -A >/dev/null
  git commit -qm "Merge pull request #6 from FelipeOFF/feat/alpha (#99)"
  set_remote_branch main "$(git rev-parse HEAD)"
  land_json report
  # Precedence on the exact value: `merge-subject`, not `squash-subject`, even
  # though `(#99)` sits in the very same string. Breaks by: testing the squash
  # pattern first, which would answer 99 for a merge that says 6.
  assert_json_eq "$output" '.phases["3"].pr.source' 'merge-subject'
  assert_json_eq "$output" '.phases["3"].pr.number' '6'
  # ONE subject names ONE pull request, and 99 is deliberately not reported.
  # MEASURED while writing this test, and the reason the assertion changed
  # from `6,99`: a trailing paren inside a merge subject belongs to the branch
  # name GitHub pasted into it, not to a second pull request. Reporting both
  # would be the board inventing a delivery that never happened.
  assert_json_eq "$output" '.phases["3"].pr.numbers | join(",")' '6'
}

@test "a phase delivered across two pull requests reports both numbers" {
  make_land_repo
  git commit -q --allow-empty -m "feat(03-02): first half (#7)"
  git commit -q --allow-empty -m "feat(03-03): second half (#8)"
  set_remote_branch main "$(git rev-parse HEAD)"
  land_json report
  # `number` is the NEWEST reference (git log order), `numbers` is every
  # distinct one — dropping the older would hide half the delivery.
  assert_json_eq "$output" '.phases["3"].pr.number' '8'
  assert_json_eq "$output" '.phases["3"].pr.numbers | join(",")' '7,8'
}

@test "a merge that names no number is unknown with no-reference, never no PR" {
  # THE PROPERTY THE WHOLE PLAN EXISTS FOR. Phase 4's commits are real, they
  # are attributed, and not one of them carries a pull-request reference —
  # exactly the shape of #21. The verdict is `unknown` with a named reason,
  # and no surface is allowed to say the work had no pull request.
  make_land_repo
  set_remote_branch main "$C2"
  land_json report
  assert_json_eq "$output" '.phases["4"].pr.status' 'unknown'
  assert_json_eq "$output" '.phases["4"].pr.reason' 'no-reference'
  assert_json_eq "$output" '.phases["4"].pr.number' 'null'
  # The detail names the limit rather than making a claim about the forge.
  assert_json_eq "$output" \
    '.phases["4"].pr.detail | test("never evidence that no pull request")' \
    'true'
}

@test "no surface prints the words that would claim there is no pull request" {
  # Breaks by: rendering `unknown` as "no PR" / "none" / "sem PR". Asserted
  # over the HUMAN output, which is the surface a person actually reads, and
  # over the whole report rather than one row.
  make_land_repo
  set_remote_branch main "$C2"
  run bash "$LAND_SH" report --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_output_has "pr unknown :: no-reference"
  local phrase
  for phrase in "no PR" "no pull request found" "sem PR" "pr none" "pr: none"; do
    if printf '%s\n' "$output" | grep -qiF -- "$phrase"; then
      echo "the report claims '$phrase' about a history that only proves" \
        "it found no reference:" >&2
      printf '%s\n' "$output" >&2
      return 1
    fi
  done
}

@test "the real #21 of this repository is unknown, not 'no PR'" {
  # THE ACCEPTANCE CASE, run against the ACTUAL history rather than a fixture.
  # Guarded by its own precondition so a future rewrite makes it skip loudly
  # instead of failing for the wrong reason.
  cd "$CAIRN_REPO_ROOT" || return 1
  run git cat-file -e 7fa133c^{commit}
  [ "$status" -eq 0 ] || skip "7fa133c is not in this checkout"

  # The premise, asserted rather than assumed: it IS a merge commit, and its
  # subject names no pull request.
  run python3 -c '
import re, subprocess, sys
out = subprocess.run(["git", "show", "-s", "--format=%P\x1f%s\x1f%b",
                      "7fa133c"], capture_output=True, text=True).stdout
parents, subject, body = out.split("\x1f", 2)
assert len(parents.split()) == 2, "not a merge commit: %r" % parents
assert not re.match(r"^Merge pull request #(\d+)\b", subject), subject
assert not re.search(r"\(#(\d+)\)\s*$", subject.strip()), subject
assert "#21" not in subject and "#21" not in body, (subject, body)
print("premise holds: a two-parent merge naming no pull request")'
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]

  # And a phase that #21 carried into main reports `unknown`, never a claim
  # that no pull request existed. Phase 13 is inside the v1.4 milestone #21
  # merged.
  run bash "$LAND_SH" report --project-dir "$CAIRN_REPO_ROOT" --json
  [ "$status" -eq 0 ]
  local st
  st="$(printf '%s' "$output" | jq -r '.phases["13"].pr.status')"
  if [ "$st" != "unknown" ] && [ "$st" != "found" ]; then
    echo "phase 13's pr status is '$st' — the vocabulary is exactly two" \
      "words, and neither of them says a pull request does not exist" >&2
    return 1
  fi
  # Whatever it answers, it never answers with the forbidden claim.
  assert_json_eq "$output" \
    '[.phases[].pr.status] | unique - ["found","unknown"] | length' '0'
}

@test "the board carries the pull request number only when one was found" {
  require_bd
  make_tmp_repo
  make_board_fixture "$PWD"
  git add -A >/dev/null 2>&1 || true
  git commit -qm "feat(03-01): board fixture (#42)" >/dev/null 2>&1
  set_remote_branch main "$(git rev-parse HEAD)"

  run bash "$STATUS_SH" --width 140 --color=never
  [ "$status" -eq 0 ]
  assert_output_has "⤒ origin/main · #42"
  # And the unknown case prints no marker of any kind — a card that prints
  # nothing claims nothing.
  assert_output_lacks "#null"
  assert_output_lacks "no PR"
}

# ─── The absence of network, proved at all three boundaries ──────────────────

arm_tripwires() {
  TRIP_SITE="$BATS_TEST_TMPDIR/tripwire-site"
  TRIP_BIN="$BATS_TEST_TMPDIR/tripwire-bin"
  TRIP_LOG="$BATS_TEST_TMPDIR/network-tools.log"
  mkdir -p "$TRIP_SITE" "$TRIP_BIN"
  : > "$TRIP_LOG"

  cat > "$TRIP_SITE/sitecustomize.py" <<'PY'
"""Layer 1: no socket leaves this interpreter."""
import socket


def _refuse(self, address, *rest):
    raise RuntimeError(
        "CAIRN-NET-TRIPWIRE: this process tried to open a socket to %r"
        % (address,))


socket.socket.connect = _refuse
socket.socket.connect_ex = _refuse
PY

  # The REAL interpreter, not whatever `command -v python3` resolves to.
  # MEASURED (plan 29-05, still true): `python3` on this machine is an asdf
  # shim written in bash, so a PATH holding only the allowlist made the run
  # exit 127 with `env: bash: No such file or directory` — the allowlist was
  # accidentally testing the version manager instead of the script.
  local real
  real="$(python3 -c 'import sys; print(sys.executable)')"
  printf '#!/bin/sh\nexec %s "$@"\n' "$real" > "$TRIP_BIN/python3"
  chmod +x "$TRIP_BIN/python3"

  local tool
  for tool in git jq; do
    real="$(command -v "$tool" || true)"
    [ -n "$real" ] || continue
    printf '#!/bin/sh\nexec %s "$@"\n' "$real" > "$TRIP_BIN/$tool"
    chmod +x "$TRIP_BIN/$tool"
  done

  # Present and TRAPPED, not merely absent: an absent binary proves only that
  # the call failed, a trapped one records that the call was ATTEMPTED.
  for tool in curl wget gh glab; do
    cat > "$TRIP_BIN/$tool" <<'SH'
#!/bin/sh
printf '%s %s\n' "$0" "$*" >> "$CAIRN_NET_LOG"
exit 1
SH
    chmod +x "$TRIP_BIN/$tool"
  done
}

write_inventory() {
  INVENTORY="$BATS_TEST_TMPDIR/subprocess-inventory.py"
  cat > "$INVENTORY" <<'PY'
"""Layer 3: every subprocess.run in a script invokes an allowlisted binary.

A runtime tripwire only catches a path that actually executes. This one reads
the source, so it goes red the day a network tool is WRITTEN into the file,
long before anybody runs a report with it.
"""
import ast
import sys

ALLOWED_BINARIES = {"git", "bd", "jq"}
path = sys.argv[1]
tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)


def head(node, assigns, depth=0):
    if depth > 4:
        return None
    if isinstance(node, ast.List) and node.elts:
        return node.elts[0]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return head(node.left, assigns, depth + 1)
    if isinstance(node, ast.Name) and node.id in assigns:
        return head(assigns[node.id], assigns, depth + 1)
    return None


def describe(h):
    if isinstance(h, ast.Constant) and isinstance(h.value, str):
        return h.value
    if isinstance(h, ast.Attribute) and h.attr == "executable":
        return "<sys.executable>"
    return None


def scan(scope, assigns):
    """subprocess.run sites in ONE scope, resolved against that scope only.

    Per-function and not module-wide: MEASURED in plan 29-05, resolving names
    module-wide collapsed two different `cmd` variables and named the wrong
    binary. A green that names the wrong binary is worse than no inventory.
    """
    out = []
    for node in ast.walk(scope):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    assigns[t.id] = node.value
    for node in ast.walk(scope):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr == "run"
                and isinstance(f.value, ast.Name)
                and f.value.id == "subprocess"):
            continue
        argv = node.args[0] if node.args else None
        name = describe(head(argv, assigns)) if argv is not None else None
        out.append((node.lineno, name))
    return out


module_assigns = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                module_assigns[t.id] = node.value

sites = []
for fn in ast.walk(tree):
    if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        sites += scan(fn, dict(module_assigns))

assert sites, "no subprocess.run found - the inventory read the wrong file"
for lineno, name in sorted(sites):
    print("line %-5d %s" % (lineno, name))
bad = [(ln, nm) for ln, nm in sites
       if nm is None
       or (nm != "<sys.executable>" and nm not in ALLOWED_BINARIES)]
assert not bad, "subprocess.run invoking something off the allowlist: %r" % bad
print("ok: %d subprocess.run sites, all on the allowlist" % len(sites))
PY
}

@test "the whole report runs under both tripwires and still answers" {
  make_land_repo
  set_remote_branch main "$C2"
  arm_tripwires

  # `python3` deliberately unqualified: it has to resolve out of the
  # allowlisted PATH, or the layer being tested is not the one in force.
  run env PATH="$TRIP_BIN" PYTHONPATH="$TRIP_SITE" CAIRN_NET_LOG="$TRIP_LOG" \
    python3 "$LAND_PY" report --project-dir "$PWD" --json
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]
  # It answered for real, not a degraded report that happens to exit 0.
  assert_json_eq "$output" '.phases["3"].status' 'landed'
  assert_json_eq "$output" '.phases["4"].status' 'unlanded'

  if [ -s "$TRIP_LOG" ]; then
    echo "a network tool was invoked during the report:" >&2
    cat "$TRIP_LOG" >&2
    return 1
  fi
}

@test "layer 1 is alive: an in-process socket raises under the same PYTHONPATH" {
  arm_tripwires
  # 127.0.0.1:9 (discard) — the tripwire fires on connect(), before anything is
  # sent, so this needs no network and no listener.
  run env PATH="$TRIP_BIN" PYTHONPATH="$TRIP_SITE" CAIRN_NET_LOG="$TRIP_LOG" \
    python3 -c 'import socket; socket.create_connection(("127.0.0.1", 9))'
  [ "$status" -ne 0 ]
  # Named, not merely nonzero: a python that failed to start also exits
  # nonzero, and would leave this green with the tripwire never loaded.
  assert_output_has "CAIRN-NET-TRIPWIRE"
}

@test "layer 2 is alive exactly where layer 1 is blind" {
  arm_tripwires
  # THE MEASUREMENT, reproduced offline. Both layers armed. curl is started as
  # a CHILD, so it never sees the patched socket module: layer 1 raises nothing
  # and the call reaches the tool. What catches it is layer 2, and the proof is
  # the log.
  run env PATH="$TRIP_BIN" PYTHONPATH="$TRIP_SITE" CAIRN_NET_LOG="$TRIP_LOG" \
    python3 -c 'import subprocess
p = subprocess.run(["curl", "-s", "https://example.com"])
print("curl was reached, layer 1 raised nothing, rc=%d" % p.returncode)'
  [ "$status" -eq 0 ]
  assert_output_has "layer 1 raised nothing"
  assert_output_lacks "CAIRN-NET-TRIPWIRE"

  if [ ! -s "$TRIP_LOG" ]; then
    echo "layer 2 did not record the curl call — the allowlisted PATH is not" \
      "in force, and the previous test is the only thing standing" >&2
    return 1
  fi
  grep -qF "https://example.com" "$TRIP_LOG"
}

@test "every subprocess.run in cairn-land.py invokes an allowlisted binary" {
  write_inventory
  run python3 "$INVENTORY" "$LAND_PY"
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]
  # MEASURED at the time of writing: TWO sites — one `git` (git(), the single
  # funnel every git read in the file goes through) and one `sys.executable`
  # (run_config(), the config's owner). The count is asserted so a site DELETED
  # by a refactor is noticed too; a legitimate third site updates this number
  # and stays on the allowlist.
  assert_output_has "ok: 2 subprocess.run sites"
}

@test "layer 3 is alive: a synthetic gh call site in this script is rejected" {
  write_inventory
  # What a live PR fetch would plausibly look like when somebody adds it here.
  cat > "$BATS_TEST_TMPDIR/fake-fetch.py" <<'PY'
import subprocess


def fetch_pr(number):
    cmd = ["gh", "pr", "view", str(number), "--json", "state"]
    return subprocess.run(cmd, capture_output=True)
PY
  run python3 "$INVENTORY" "$BATS_TEST_TMPDIR/fake-fetch.py"
  [ "$status" -ne 0 ]
  assert_output_has "off the allowlist"
  assert_output_has "gh"
}
