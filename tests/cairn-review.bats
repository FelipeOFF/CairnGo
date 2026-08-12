#!/usr/bin/env bats
# cairn-review.bats — the one cairn surface that talks to the forge, the switch
# that keeps it silent by default, and the stamp that stops a cached answer from
# looking current.
#
# Under test: cairn/scripts/cairn-review.py (fetch / show), the
# `git.review_state` switch, and the `.cairn/pr-cache.json` that cairn-land.py
# READS — a plain file read, never a fetch.
#
# ─────────────────────────────────────────────────────────────────────────────
# THE BOUNDARY THIS FILE GUARDS IS STRUCTURAL, NOT A PROMISE
#
#     cairn-status.py -> cairn-land.py -> git, and the cache FILE
#     cairn-review.py -> gh / glab                    (never the reverse)
#
# tests/cairn-land.bats asserts TWO subprocess.run sites in cairn-land.py and
# tests/cairn-tracker-card.bats asserts FIVE in cairn-status.py, none of them a
# network tool. Moving the fetch into either file would require deleting those
# assertions to ship — which is the conversation that should happen out loud.
# The assertion at the bottom of this file states that boundary from this side.
#
# No real network call happens anywhere in this suite: `gh` is a stub on PATH
# that answers from a canned payload, so the fetch path is exercised for real
# without ever leaving the machine.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so every check lands on a plain `[ ]` over a
# run-captured `$status`.

load 'helpers'

REVIEW_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-review.sh"
REVIEW_PY="$CAIRN_SCRIPTS_DIR/cairn-review.py"
LAND_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-land.sh"
LAND_PY="$CAIRN_SCRIPTS_DIR/cairn-land.py"
STATUS_PY="$CAIRN_SCRIPTS_DIR/cairn-status.py"
CONFIG_SH="$CAIRN_SCRIPTS_DIR/cairn-config.sh"

# A repo whose history names pull request #18 for phase 3.
make_review_repo() {
  make_tmp_repo
  mkdir -p .planning/phases/03-alpha
  echo plan > .planning/phases/03-alpha/03-01-PLAN.md
  git add -A >/dev/null
  git commit -qm "feat(03-01): alpha plan (#18)"
  git update-ref refs/remotes/origin/main "$(git rev-parse HEAD)"
}

# A `gh` on PATH that answers from a canned payload and records that it was
# called. Present and observable, so a test can assert both that the fetch
# happened and — elsewhere — that it did NOT.
stub_gh() {
  STUB_BIN="$BATS_TEST_TMPDIR/stub-bin"
  STUB_LOG="$BATS_TEST_TMPDIR/gh-calls.log"
  mkdir -p "$STUB_BIN"
  : > "$STUB_LOG"
  cat > "$STUB_BIN/gh" <<SH
#!/bin/sh
printf '%s\n' "\$*" >> "$STUB_LOG"
if [ -n "\${GH_STUB_FAIL:-}" ]; then
  echo "stub failure" >&2
  exit 1
fi
printf '%s\n' '{"number":18,"state":"MERGED","title":"the alpha plan","url":"https://example.invalid/pr/18","mergedAt":"2026-08-01T10:00:00Z"}'
SH
  chmod +x "$STUB_BIN/gh"
  PATH="$STUB_BIN:$PATH"
  export PATH
}

assert_output_has() {
  if ! printf '%s\n' "$output" | grep -qF -- "$1"; then
    echo "expected the output to contain '$1', it does not:" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}

# ─── The switch is off, and off is an answer ─────────────────────────────────

@test "with the switch off, fetch makes no call and writes nothing" {
  make_review_repo
  stub_gh
  run bash "$REVIEW_SH" fetch --project-dir "$PWD" --json
  # 3, not 0 and not a failure: the switch being off is the answer to the
  # question, not an error somebody has to handle.
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.reason' 'switch-off'
  assert_json_eq "$output" '.written' 'false'
  [ ! -f .cairn/pr-cache.json ]
  # And the proof that `off` is not merely "the tool was missing": the stub is
  # RIGHT THERE on PATH and was never invoked.
  [ ! -s "$STUB_LOG" ]
}

@test "the default value of the switch is off, in the schema itself" {
  make_review_repo
  run bash "$CONFIG_SH" get git.review_state --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.value' 'off'
  assert_json_eq "$output" '.source' 'default'
  assert_json_eq "$output" '.reader' 'cairn-review.py fetch'
}

# ─── Switched on, it fetches — and stamps ────────────────────────────────────

@test "with the switch on, fetch writes a cache carrying its own timestamp" {
  make_review_repo
  stub_gh
  bash "$CONFIG_SH" set git.review_state gh --project-dir "$PWD" >/dev/null
  run bash "$REVIEW_SH" fetch --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written' 'true'
  assert_json_eq "$output" '.tool' 'gh'
  assert_json_eq "$output" '.fetched' '1'

  # The stamp is not optional. Breaks by: writing the entries without
  # `fetched_at`, which is exactly how a cached state starts looking current.
  run jq -r '.fetched_at' .cairn/pr-cache.json
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'
  run jq -r '.prs["18"].state' .cairn/pr-cache.json
  [ "$output" = "MERGED" ]

  # The number came from the local history through cairn-land.py — nobody
  # typed it and this script re-read no git.
  grep -qF "pr view 18" "$STUB_LOG"
}

@test "a fetch that answers for nothing leaves the previous cache alone" {
  # Replacing a stale-but-stamped answer with a fresh-looking void is the exact
  # failure this whole plan exists to prevent.
  make_review_repo
  stub_gh
  bash "$CONFIG_SH" set git.review_state gh --project-dir "$PWD" >/dev/null
  bash "$REVIEW_SH" fetch --project-dir "$PWD" >/dev/null
  local before
  before="$(cat .cairn/pr-cache.json)"

  GH_STUB_FAIL=1 run env GH_STUB_FAIL=1 bash "$REVIEW_SH" fetch \
    --project-dir "$PWD" --json
  [ "$status" -eq 5 ]
  assert_json_eq "$output" '.written' 'false'
  assert_json_eq "$output" '.reason' 'no-answer'
  [ "$before" = "$(cat .cairn/pr-cache.json)" ]
}

@test "show reports the cache and its age, and exits 3 when there is none" {
  make_review_repo
  run bash "$REVIEW_SH" show --project-dir "$PWD" --json
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.cached' 'false'

  stub_gh
  bash "$CONFIG_SH" set git.review_state gh --project-dir "$PWD" >/dev/null
  bash "$REVIEW_SH" fetch --project-dir "$PWD" >/dev/null
  run bash "$REVIEW_SH" show --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.cached' 'true'
  assert_json_eq "$output" '.prs["18"].state' 'MERGED'
}

# ─── The report reads the cache, and the age travels with the state ──────────

@test "the landing report carries the review state WITH its age and staleness" {
  make_review_repo
  stub_gh
  bash "$CONFIG_SH" set git.review_state gh --project-dir "$PWD" >/dev/null
  bash "$REVIEW_SH" fetch --project-dir "$PWD" >/dev/null

  run bash "$LAND_SH" report --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.phases["3"].pr.review.state' 'MERGED'
  assert_json_eq "$output" '.phases["3"].pr.review.tool' 'gh'
  # Exact value, not "is present": a freshly written cache is `false`, and an
  # assertion that merely checked for the KEY would pass with `stale` hardwired
  # to true.
  assert_json_eq "$output" '.phases["3"].pr.review.stale' 'false'
  run jq -e '.phases["3"].pr.review.age_seconds >= 0' <<<"$output"
  [ "$status" -eq 0 ]
}

@test "a cache older than the threshold reads stale: true" {
  make_review_repo
  mkdir -p .cairn
  cat > .cairn/pr-cache.json <<'JSON'
{
  "fetched_at": "2020-01-01T00:00:00Z",
  "tool": "gh",
  "prs": {"18": {"number": 18, "state": "OPEN", "title": "old", "url": null}}
}
JSON
  run bash "$LAND_SH" report --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.phases["3"].pr.review.stale' 'true'
  assert_json_eq "$output" '.phases["3"].pr.review.state' 'OPEN'
}

@test "a cache with no fetched_at is treated as absent, never as current" {
  # THE RULE, stated as a test: a pull-request state with no age is worse than
  # no state at all, because it looks current. There is no branch anywhere that
  # renders one.
  make_review_repo
  mkdir -p .cairn
  cat > .cairn/pr-cache.json <<'JSON'
{"tool": "gh", "prs": {"18": {"number": 18, "state": "MERGED"}}}
JSON
  run bash "$LAND_SH" report --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.phases["3"].pr.review' 'null'
  # The report still answers everything it could answer offline.
  assert_json_eq "$output" '.phases["3"].pr.number' '18'
}

@test "the human report prints the state and the age together, never alone" {
  make_review_repo
  mkdir -p .cairn
  cat > .cairn/pr-cache.json <<'JSON'
{
  "fetched_at": "2020-01-01T00:00:00Z",
  "tool": "gh",
  "prs": {"18": {"number": 18, "state": "MERGED", "title": "old"}}
}
JSON
  run bash "$LAND_SH" report --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_output_has "MERGED — cached"
  assert_output_has "stale"
}

@test "the board renders the cached state with its age, or not at all" {
  require_bd
  make_tmp_repo
  make_board_fixture "$PWD"
  git add -A >/dev/null 2>&1 || true
  git commit -qm "feat(03-01): board fixture (#18)" >/dev/null 2>&1
  git update-ref refs/remotes/origin/main "$(git rev-parse HEAD)"

  # Without a cache: the number renders, the state does not.
  run bash "$CAIRN_REPO_ROOT/cairn/scripts/cairn-status.sh" --width 140 \
    --color=never
  [ "$status" -eq 0 ]
  assert_output_has "#18"
  if printf '%s\n' "$output" | grep -qF "merged"; then
    echo "the board printed a review state with no cache behind it" >&2
    return 1
  fi

  mkdir -p .cairn
  cat > .cairn/pr-cache.json <<'JSON'
{
  "fetched_at": "2020-01-01T00:00:00Z",
  "tool": "gh",
  "prs": {"18": {"number": 18, "state": "MERGED", "title": "old"}}
}
JSON
  run bash "$CAIRN_REPO_ROOT/cairn/scripts/cairn-status.sh" --width 160 \
    --color=never
  [ "$status" -eq 0 ]
  # Breaks by: printing `merged` on its own. The age and the staleness word
  # travel with it or it does not print.
  assert_output_has "#18 merged ("
  assert_output_has "ago, stale)"
}

# ─── The boundary, stated from this side ─────────────────────────────────────

@test "the network tools appear in cairn-review.py and in no other script" {
  # Breaks by: adding a `gh`/`glab`/`curl` call to cairn-land.py or
  # cairn-status.py — which the structural inventories in the other two suites
  # also catch, from the other direction. Two independent statements of one
  # boundary, because this one is the load-bearing claim of the whole phase.
  run python3 -c '
import ast, sys

TOOLS = {"gh", "glab", "curl", "wget"}


def heads(path):
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr == "run"
                and isinstance(f.value, ast.Name)
                and f.value.id == "subprocess"):
            continue
        argv = node.args[0] if node.args else None
        # A literal list, or a lambda table indexed by tool name (the shape
        # cairn-review.py uses) - both resolved down to their string heads.
        for sub in ast.walk(argv) if argv is not None else []:
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if sub.value in TOOLS:
                    found.add(sub.value)
    return found


offline = {}
for path in (sys.argv[1], sys.argv[2]):
    offline[path] = heads(path)
    assert not offline[path], "%s names a network tool: %r" % (
        path, offline[path])
# And the review script really does carry them, so the assertion above is not
# green because the scan is broken.
src = open(sys.argv[3], encoding="utf-8").read()
assert "\"gh\"" in src and "\"glab\"" in src, "the scan read the wrong file"
print("ok: the network lives in %s and nowhere else" % sys.argv[3])
' "$LAND_PY" "$STATUS_PY" "$REVIEW_PY"
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]
  assert_output_has "the network lives in"
}
