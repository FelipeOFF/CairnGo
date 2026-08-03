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
#   make_env_asserting_claude_stub
#                           claude stub that echoes its own observed HOME/env/
#                           argv into the canned JSON payload it emits
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
