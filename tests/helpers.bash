# helpers.bash — shared bats helpers for the cairn test suite.
#
# Seam philosophy: tests exercise the CLI contracts of cairn/scripts/ against
# throwaway fixture repos. They assert on files, exit codes, and bd state via
# `bd list --json` — never on script internals.
#
# Fixture builders defined here:
#   require_bd              skip the current test when bd is not on PATH
#   make_tmp_repo           mktemp dir + git init + cd into it
#   make_gsd_fixture DIR    minimal but structurally faithful .planning/ tree
#   make_bd_fixture DIR [PREFIX]
#                           bd init + epic, two children (one closed),
#                           one standalone with a blocks dep and a label
#   make_board_fixture DIR  deterministic board fixture: .planning/ tree with
#                           every roadmap shape + bd db with FIXED issue ids
#                           (needs bd >= 1.1.0 for `bd create --id`)
#   make_drift_fixture DIR  this repo's OWN planning files, frozen while they
#                           still disagree (tests/fixtures/bookkeep-drift/),
#                           plus the phase tree rebuilt from phases.tsv and a
#                           baseline commit
#   make_env_asserting_claude_stub
#                           claude stub that echoes its own observed HOME/env/
#                           argv into the canned JSON payload it emits
#   make_pinned_home DIR    an empty HOME to pass as HOME=..., with the
#                           toolchain still resolvable inside it
#   extract_frontmatter F   print the YAML frontmatter block of F
#   assert_frontmatter_key F KEY
#   assert_json_eq JSON FILTER EXPECTED

CAIRN_TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAIRN_REPO_ROOT="$(dirname "$CAIRN_TESTS_DIR")"
CAIRN_SCRIPTS_DIR="$CAIRN_REPO_ROOT/cairn/scripts"

# Skip the current test with a clear message when bd is missing.
require_bd() {
  if ! command -v bd >/dev/null 2>&1; then
    skip "bd is not on PATH — install beads (https://github.com/gastownhall/beads) to run this test"
  fi
}

# Create a throwaway git repo and cd into it.
# The dir lives under BATS_TEST_TMPDIR when available, so bats removes it
# automatically after the test. Outside bats it falls back to TMPDIR and is
# tracked in CAIRN_TMP_DIRS for manual cleanup via cleanup_tmp_repos.
make_tmp_repo() {
  local parent="${BATS_TEST_TMPDIR:-${TMPDIR:-/tmp}}"
  CAIRN_TMP_REPO="$(mktemp -d "$parent/cairn-repo.XXXXXX")"
  if [ -z "${BATS_TEST_TMPDIR:-}" ]; then
    CAIRN_TMP_DIRS+=("$CAIRN_TMP_REPO")
  fi
  git init -q "$CAIRN_TMP_REPO"
  git -C "$CAIRN_TMP_REPO" config user.email "cairn-tests@example.com"
  git -C "$CAIRN_TMP_REPO" config user.name "Cairn Tests"
  cd "$CAIRN_TMP_REPO" || return 1
}

# Remove dirs registered by make_tmp_repo outside bats (no-op under bats).
cleanup_tmp_repos() {
  local dir
  for dir in "${CAIRN_TMP_DIRS[@]:-}"; do
    [ -n "$dir" ] && rm -rf "$dir"
  done
  CAIRN_TMP_DIRS=()
}

# Write a minimal but structurally faithful GSD .planning/ tree into DIR.
# Shapes follow gsd-core templates: roadmap.md, requirements.md, state.md,
# phase-prompt.md (PLAN), summary-minimal.md, verification-report.md.
# Phase 1 (01-auth) is complete and verified; phase 2 (02-api) is mid-flight
# (PLAN present, no SUMMARY).
make_gsd_fixture() {
  local dir="$1"
  local p="$dir/.planning"
  mkdir -p "$p/phases/01-auth" "$p/phases/02-api"

  cat > "$p/ROADMAP.md" <<'EOF'
# Roadmap: Fixture Project

## Overview

Two-phase fixture: auth foundation, then the API layer on top of it.

## Phases

- [x] **Phase 1: Auth** - Signup and login flows
- [ ] **Phase 2: API** - Rate-limited public API

## Phase Details

### Phase 1: Auth
**Goal**: Users can sign up and log in
**Depends on**: Nothing (first phase)
**Requirements**: [AUTH-01, AUTH-02]
**Success Criteria** (what must be TRUE):
  1. User can sign up with email and password
  2. User can log in with valid credentials
**Plans**: 1 plan

Plans:
- [x] 01-01: Implement signup and login

### Phase 2: API
**Goal**: Public API is rate limited
**Depends on**: Phase 1
**Requirements**: [API-01]
**Success Criteria** (what must be TRUE):
  1. Requests beyond the limit receive HTTP 429
**Plans**: 1 plan

Plans:
- [ ] 02-01: Add rate limiting middleware
EOF

  cat > "$p/REQUIREMENTS.md" <<'EOF'
# Requirements: Fixture Project

**Defined:** 2026-07-01
**Core Value:** Deterministic fixture for the cairn test suite

## v1 Requirements

### Authentication

- [x] **AUTH-01**: User can sign up with email and password
- [x] **AUTH-02**: User can log in with valid credentials

### API

- [ ] **API-01**: Public API requests beyond the limit receive HTTP 429

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| API-01 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 3 total
- Mapped to phases: 3
- Unmapped: 0
EOF

  cat > "$p/STATE.md" <<'EOF'
---
gsd_state_version: '1.0'
status: executing
active_phase: "2"
next_action: execute-phase
progress:
  total_phases: 2
  completed_phases: 1
  total_plans: 2
  completed_plans: 1
  percent: 50
---

# Project State

## Current Position

Phase: 2 of 2 (API)
Plan: 1 of 1 in current phase
Status: In progress
Last activity: 2026-07-20 — Phase 1 verified, phase 2 execution started

Progress: [█████░░░░░] 50%
EOF

  cat > "$p/phases/01-auth/01-01-PLAN.md" <<'EOF'
---
phase: 01-auth
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified: [src/auth.py]
autonomous: true
requirements: [AUTH-01, AUTH-02]
status: complete
must_haves:
  truths:
    - User can sign up with email and password
    - User can log in with valid credentials
  artifacts:
    - src/auth.py
  key_links: []
---

<objective>
Implement signup and login.

Purpose: Auth is the foundation every later phase depends on.
Output: src/auth.py with signup and login handlers.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Implement signup and login handlers</name>
  <files>src/auth.py</files>
  <action>Create signup(email, password) and login(email, password) handlers.</action>
  <verify>python3 -m pytest tests/test_auth.py</verify>
  <done>Both handlers exist and their tests pass.</done>
</task>

</tasks>

<verification>
Before declaring plan complete:
- [ ] tests/test_auth.py passes
</verification>
EOF

  cat > "$p/phases/01-auth/01-01-SUMMARY.md" <<'EOF'
---
phase: 01-auth
plan: "01"
subsystem: auth
tags: [python, auth]
provides:
  - signup and login handlers in src/auth.py
key-files:
  created: [src/auth.py]
  modified: []
key-decisions: []
duration: 12min
completed: 2026-07-18
status: complete
---

# Phase 1: Auth Summary (Minimal)

**Signup and login handlers implemented and tested.**

## Accomplishments
- src/auth.py with signup and login handlers

## Next Phase Readiness
Ready for phase 2.
EOF

  cat > "$p/phases/01-auth/01-VERIFICATION.md" <<'EOF'
---
phase: 01-auth
verified: 2026-07-19T10:00:00Z
status: passed
score: 2/2 must-haves verified
behavior_unverified: 0
---

# Phase 1: Auth Verification Report

**Phase Goal:** Users can sign up and log in
**Status:** passed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can sign up with email and password | ✓ VERIFIED | tests/test_auth.py |
| 2 | User can log in with valid credentials | ✓ VERIFIED | tests/test_auth.py |

**Score:** 2/2 truths verified
EOF

  cat > "$p/phases/02-api/02-01-PLAN.md" <<'EOF'
---
phase: 02-api
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified: [src/api.py]
autonomous: true
requirements: [API-01]
status: in_progress
must_haves:
  truths:
    - Requests beyond the limit receive HTTP 429
  artifacts:
    - src/api.py
  key_links: []
---

<objective>
Add rate limiting middleware.

Purpose: Protect the public API from abuse.
Output: src/api.py with a rate limiting middleware.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Add rate limiting middleware</name>
  <files>src/api.py</files>
  <action>Wrap public routes in a token-bucket rate limiter returning HTTP 429.</action>
  <verify>python3 -m pytest tests/test_api.py</verify>
  <done>Requests beyond the limit receive HTTP 429.</done>
</task>

</tasks>

<verification>
Before declaring plan complete:
- [ ] tests/test_api.py passes
</verification>
EOF
}

# Rewrite make_gsd_fixture's ROADMAP.md so it lists NO phase at all, keeping
# everything else about the fixture intact. This is the VOID-02 scenario: a
# repo whose roadmap has nothing to compare against, where a check that counts
# zero must not read as success.
#
# It EDITS the standard fixture rather than standing up a parallel one on
# purpose — two fixtures for the same repo shape diverge inside a month, and
# then a test proves something about a repo nobody has.
#
# NOTE, measured: this affects the checks that read ROADMAP.md (req-issue,
# orphans, phase-complete-open), and NOT maps-fresh, which walks the phase
# DIRECTORIES on disk. Emptying `.planning/phases/` is a different lever.
make_roadmap_without_phases() {
  local dir="${1:-$PWD}"
  cat > "$dir/.planning/ROADMAP.md" <<'EOF'
# Roadmap: Fixture Project

## Overview

The phases have not been written down yet.

## Phases

## Phase Details
EOF
}

# Initialize bd in DIR (default prefix "tst") and create four issues:
#   BD_EPIC          epic, P1
#   BD_CHILD_OPEN    task, child of the epic, open
#   BD_CHILD_CLOSED  task, child of the epic, closed
#   BD_STANDALONE    feature, labeled, blocks BD_CHILD_OPEN
# IDs are exported in those globals for assertions. Callers must require_bd
# first. Runs inside DIR and restores the previous cwd.
make_bd_fixture() {
  local dir="$1"
  local prefix="${2:-tst}"
  pushd "$dir" >/dev/null || return 1
  bd init -q --prefix "$prefix" --non-interactive >/dev/null 2>&1
  BD_EPIC="$(bd create "Auth epic" -t epic -p 1 --silent)"
  BD_CHILD_OPEN="$(bd create "Implement login flow" -t task --parent "$BD_EPIC" --silent)"
  BD_CHILD_CLOSED="$(bd create "Scaffold auth module" -t task --parent "$BD_EPIC" --silent)"
  bd close "$BD_CHILD_CLOSED" >/dev/null
  BD_STANDALONE="$(bd create "API rate limiting" -t feature -l cairn-sync --deps "blocks:$BD_CHILD_OPEN" --silent)"
  # A wired repo has a way back. Added 2026-08-07 with check 22,
  # issues-recoverable, and the reason is a measurement on THIS repository:
  # the database was 27 MB inside .gitignore, no export was tracked, and the
  # remote carried 0 refs/dolt out of 42 — a clean clone recovered none of the
  # 176 issues, while CLAUDE.md had been stating the opposite for weeks.
  #
  # The fixture models a CORRECTLY wired repo, so it exports and commits like
  # one. Leaving it without a recovery path would have made every fixture
  # carry a permanent warning and pushed seven tests to assert an unhealthy
  # baseline as healthy — teaching the suite that the defect is normal.
  bd export --all -o .beads/issues.jsonl >/dev/null 2>&1
  git add -f .beads/issues.jsonl >/dev/null 2>&1
  git -c user.email=t@t -c user.name=t commit -q -m "beads: export" \
    -- .beads/issues.jsonl >/dev/null 2>&1 || true
  popd >/dev/null || return 1
}

# Build the deterministic board fixture in DIR: a .planning/ tree carrying
# every roadmap shape the phase model reads, plus a bd database whose issue
# ids are FIXED. Callers must require_bd first. Runs inside DIR and restores
# the previous cwd.
#
# Determinism is the whole point of this one. tests/fixtures/board-render/
# holds a byte-for-byte reference render of this fixture, so anything that
# varies between two builds destroys it. Two guards, both load-bearing:
#
#   * `bd init --prefix brd` passes a LITERAL prefix. bd derives the prefix
#     from the directory name when nobody passes one, and make_tmp_repo names
#     that directory with mktemp — so a derived prefix varies per build and
#     drags the "explicit" ids along with it.
#   * every `bd create` passes --id (needs bd >= 1.1.0), and every issue gets
#     a distinct priority: fetch_lanes sorts by (priority, id), and equal
#     priorities would leave lane order resting on the id tiebreak alone.
#
# Without both, two identical builds render different boards — measured
# during planning: pm-ghk/pm-ezn on one build, pm-11m/pm-org on the next.
#
# DELIBERATE, do not "fix" it: STATE.md and ROADMAP.md disagree about the
# current milestone. STATE.md names v1.0, the ARCHIVED cycle, while the
# roadmap marks v1.1 as the open one. That reproduces the defect measured on
# 2026-08-03, ten minutes after v1.4 was archived — main() does
# `milestone = fm["milestone"] or roadmap_milestone(...)`, so STATE.md wins
# and the board keeps announcing a dead cycle. Phase 20-02 needs this trap
# armed: a group model that takes the label from STATE.md renders the
# archived name and turns that plan's test red, which is the point.
make_board_fixture() {
  local dir="$1"
  local p="$dir/.planning"
  mkdir -p "$p/phases/03-phase-model"

  # All three shapes at once: a `## Milestones` list (one archived, one
  # open), `## Phases` checkbox lines (two complete, two pending), and a
  # `## Progress` table carrying the per-phase milestone column. The grammar
  # mirrors write_roadmap() in tests/cairn-phase-model.bats on purpose —
  # inventing a second dialect of the same fixture helps nobody.
  cat > "$p/ROADMAP.md" <<'EOF'
# Roadmap: Board Fixture

## Milestones

- ✅ **v1.0 Foundations** — Phases 1-2
- 🚧 **v1.1 Surface** — Phases 3-4

## Phases

- [x] Phase 1: Signup and login (2/2 plans) — completed 2026-07-01
- [x] **Phase 2: Rate limiting** - the API layer on top
- [ ] Phase 3: Phase model — read what a phase actually is (PANEL-01)
- [ ] Phase 4: Board fills the screen (PANEL-04, PANEL-05)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
| ----- | --------- | -------------- | ------ | --------- |
| 1. Signup and login | v1.0 | 2/2 | Complete | 2026-07-01 |
| 2. Rate limiting | v1.0 | 1/1 | Complete | 2026-07-02 |
| 3. Phase model | v1.1 | 0/1 | Not started | — |
| 4. Board fills the screen | v1.1 | 0/? | Not started | — |
EOF

  cat > "$p/STATE.md" <<'EOF'
---
milestone: v1.0
active_phase: 3
next_action: execute-phase
---

# Project State

Phase 3 of 4 (Phase model)
EOF

  cat > "$p/phases/03-phase-model/03-01-PLAN.md" <<'EOF'
---
phase: 03-phase-model
plan: "01"
type: execute
wave: 1
depends_on: []
autonomous: true
---

<objective>
Read what a phase actually is.
</objective>
EOF

  pushd "$dir" >/dev/null || return 1
  bd init -q --prefix brd --non-interactive >/dev/null 2>&1
  # Created blocked-first so the blocker can name it: `blocks:X` puts X on
  # the BLOCKED lane, so X has to exist by then.
  bd create "Wait on the phase model" --id brd-005 -t task -p 4 \
    -l phase-4 --silent >/dev/null
  bd create "Read the roadmap into a phase model" --id brd-001 -t feature \
    -p 0 -l phase-3 --deps "blocks:brd-005" --silent >/dev/null
  bd create "Fill the screen at any width" --id brd-002 -t feature -p 1 \
    -l phase-4 --silent >/dev/null
  # No phase label at all: the loose issue phase 20-02's unphased group needs.
  bd create "Sweep the backlog" --id brd-003 -t chore -p 2 --silent >/dev/null
  # DOING lane. The assignee is a literal, never $USER — the reference render
  # is committed and read back on other machines.
  bd create "Hold the lease while executing" --id brd-004 -t task -p 3 \
    -l phase-3 -a cairn-tests --silent >/dev/null
  bd update brd-004 --status in_progress >/dev/null 2>&1
  # One closed issue, so the footer's `done:` count is not zero.
  bd create "Ship the foundations" --id brd-006 -t task -p 2 -l phase-1 \
    --silent >/dev/null
  bd close brd-006 >/dev/null 2>&1
  popd >/dev/null || return 1
}

# Build the drift fixture in DIR: this repository's OWN ROADMAP.md,
# REQUIREMENTS.md and STATE.md as frozen by
# tests/fixtures/bookkeep-drift/capture.sh, while they still disagree with
# each other, plus the phase tree those files describe.
#
# The .md files are COPIED, never rewritten — the whole value of this fixture
# is that it is a byte copy of a real, committed, drifted state (29-CONTEXT.md,
# D-02). The phase tree is rebuilt from phases.tsv with EMPTY files of the
# right names, because every counter under test counts NAMES, not content.
#
# It ends with `git add -A` + `git commit`, and that commit is load-bearing:
# make_tmp_repo runs `git init` and configures a user but never commits
# anything (there is no `git commit` anywhere else in this file), so without
# this one the fixture files stay untracked and `git diff` against a tree with
# no HEAD returns empty. A write test proving "only the planned lines moved"
# would then pass against a 35-line reflow just as happily as against a
# one-character edit. The commit is the denominator of that diff. If
# make_tmp_repo ever grows a commit of its own this becomes harmless
# redundancy — do not assume it will.
make_drift_fixture() {
  local dir="$1"
  local src="$CAIRN_TESTS_DIR/fixtures/bookkeep-drift"
  local p="$dir/.planning"
  mkdir -p "$p/phases"

  local name
  for name in ROADMAP REQUIREMENTS STATE; do
    cp "$src/$name.md" "$p/$name.md"
  done

  # phases.tsv: phase_dir<TAB>plans<TAB>summaries<TAB>has_verification<TAB>
  # has_phase_summary. Comment lines start with '#'. The plan/summary numbers
  # are regenerated as NN-01..NN-<count>, which is how the frozen ROADMAP's
  # own `Plans:` lists name them.
  #
  # has_phase_summary writes NN-SUMMARY.md — the summary of the PHASE, which
  # is not a plan. It exists because its absence is what kept CairnGo-6bx away
  # from every test in this repository: `*-SUMMARY.md` matched both shapes and
  # nothing on disk ever carried the second one.
  local phase_dir plans summaries has_ver has_phase_sum nn i idx
  while IFS=$'\t' read -r phase_dir plans summaries has_ver has_phase_sum; do
    case "$phase_dir" in ''|'#'*) continue ;; esac
    mkdir -p "$p/phases/$phase_dir"
    nn="${phase_dir%%-*}"
    for ((i = 1; i <= plans; i++)); do
      idx="$(printf '%02d' "$i")"
      : > "$p/phases/$phase_dir/$nn-$idx-PLAN.md"
    done
    for ((i = 1; i <= summaries; i++)); do
      idx="$(printf '%02d' "$i")"
      : > "$p/phases/$phase_dir/$nn-$idx-SUMMARY.md"
    done
    if [ "$has_ver" = "1" ]; then
      : > "$p/phases/$phase_dir/$nn-VERIFICATION.md"
    fi
    if [ "$has_phase_sum" = "1" ]; then
      : > "$p/phases/$phase_dir/$nn-SUMMARY.md"
    fi
  done < "$src/phases.tsv"

  git -C "$dir" add -A
  git -C "$dir" commit -q -m "fixture baseline"
}

# Write an executable claude stub to $BATS_TEST_TMPDIR/claude-env-stub (path
# exported in STUB) that emits a minimal valid-result payload plus what it
# OBSERVED of its own launch: stub_observed_home, stub_observed_leak_marker,
# stub_observed_api_key_present, stub_observed_argv. bench-run.py passes
# unknown payload fields through untouched, so these observations land in the
# output JSONL row where bats can assert on the environment and argv the
# harness actually constructed. Only boolean API-key PRESENCE is echoed; the
# literal key value never reaches any file.
make_env_asserting_claude_stub() {
  STUB="$BATS_TEST_TMPDIR/claude-env-stub"
  cat > "$STUB" <<'EOF'
#!/usr/bin/env bash
python3 -c "
import json, os, sys
print(json.dumps({
    'type': 'result', 'subtype': 'success', 'is_error': False, 'num_turns': 1,
    'total_cost_usd': 0.0,
    'usage': {'input_tokens': 0, 'output_tokens': 0,
              'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0},
    'session_id': 'stub-env-check',
    'stub_observed_home': os.environ.get('HOME', ''),
    'stub_observed_leak_marker': os.environ.get('OPERATOR_ONLY_LEAK_MARKER', ''),
    'stub_observed_api_key_present': bool(os.environ.get('ANTHROPIC_API_KEY')),
    'stub_observed_argv': sys.argv[1:],
}))
" "$@"
EOF
  chmod +x "$STUB"
}

# Print the YAML frontmatter block of FILE (content between the first two
# `---` lines). Fails when the file has no frontmatter.
extract_frontmatter() {
  local file="$1"
  awk 'NR==1 && $0!="---" {exit 1}
       NR>1 && $0=="---" {found=1; exit}
       NR>1 {print}
       END {exit found ? 0 : 1}' "$file"
}

# Assert that FILE's frontmatter contains a top-level KEY.
assert_frontmatter_key() {
  local file="$1" key="$2"
  extract_frontmatter "$file" | grep -q "^${key}:" || {
    echo "frontmatter key '$key' missing in $file" >&2
    return 1
  }
}

# Refresh the tracked beads export after a test mutates bd state.
#
# A wired repo keeps its export current — bd does it on an interval, and this
# repository sets export.auto plus git-add for exactly that. An interval is
# not deterministic inside a test, so the tests that mutate bd and then assert
# a clean doctor run call this instead of waiting on a timer.
#
# Added 2026-08-07 with check 22, issues-recoverable. Without it those tests
# assert "nothing warns" over a store whose export is genuinely behind, which
# would mean weakening the check until it stopped noticing the lag it exists
# to notice.
beads_export_refresh() {
  bd export --all -o .beads/issues.jsonl >/dev/null 2>&1
}

# Nanosecond mtime of FILE, through python3.
#
# `stat` is the trap here and it has bitten this suite twice. The flag differs
# by platform (`stat -f %m` on macOS, `stat -c %Y` on GNU), so the portable
# spelling people reach for is `stat -f %m f 2>/dev/null || stat -c %Y f` —
# which is what tests/cairn-wrap.bats carried until 2026-08-07, when the full
# suite passed on macOS and the same test failed on the CI runner. Nobody wants
# a portability shim deciding a verdict, so this reads the number from the same
# stdlib call on every platform.
#
# Nanoseconds, not seconds, and that is the other half: a rewrite inside the
# same second is invisible to a seconds-resolution comparison, so a test that
# exists to prove "no write happened" would pass over the write it was written
# to catch.
file_mtime_ns() {
  python3 -c "import os,sys;print(os.stat(sys.argv[1]).st_mtime_ns)" "$1"
}

# Create DIR and print it, as a HOME to pin with `env HOME=...`.
#
# Why this exists, measured 2026-08-06. Tests pin HOME so that a contributor's
# own config cannot decide a test — cairn-jira.bats reads `mcp` from
# ~/.claude.json, cairn-migrate.bats reads the same. That intent is right and
# stays. What the pin did NOT intend is to move the language runtime, and on a
# machine where python3 is an asdf shim it does exactly that: asdf resolves the
# version from $HOME/.tool-versions, so an empty HOME kills python3 with exit
# 126 before a single line of cairn runs.
#
#   $ cd /tmp/repo && env HOME=/tmp/empty python3 --version
#   No version is set for command python3
#   STATUS=126
#
# That took out 17 tests (14 in cairn-jira.bats, 3 in cairn-migrate.bats) in
# the full suite of 2026-08-06 — none of them a code regression; the same tests
# passed on 2026-08-05. So the pinned HOME carries the version manager's
# manifest and nothing else. A machine without asdf has no ~/.tool-versions and
# the copy is simply skipped, which is why this is not guarded on `asdf`
# itself: the file's presence IS the condition.
#
# Deliberately NOT copied: ~/.claude.json, ~/.claude/, or anything else from
# the real HOME. Widening this past the toolchain would give back exactly the
# contamination the pin exists to prevent.
make_pinned_home() {
  local dir="$1"
  mkdir -p "$dir"
  [ -f "$HOME/.tool-versions" ] && cp "$HOME/.tool-versions" "$dir/.tool-versions"
  printf '%s\n' "$dir"
}

# Assert that JSON piped through a jq FILTER equals EXPECTED (raw output).
assert_json_eq() {
  local json="$1" filter="$2" expected="$3"
  local actual
  actual="$(jq -r "$filter" <<<"$json")"
  if [ "$actual" != "$expected" ]; then
    echo "jq '$filter' returned '$actual', expected '$expected'" >&2
    return 1
  fi
}
