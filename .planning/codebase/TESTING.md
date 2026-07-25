# Testing Patterns

**Analysis Date:** 2026-07-25

## Test Framework

**Runner:**
- [bats-core](https://github.com/bats-core/bats-core) (Bash Automated Testing
  System). No version pinned in-repo; CI installs the latest via
  `npm install -g bats` (`.github/workflows/ci.yml`).
- Config: none (no `.bats-run` / config file). Test discovery is just
  `bats tests/` — bats runs every `*.bats` file in the given directory.

**Assertion Library:**
- None external — bats' own `run`/`$status`/`$output`/`$lines` plus plain
  POSIX test (`[ ]`), `grep`, and `jq` for JSON. See "Assertion Style Gotcha"
  below for a documented pitfall specific to this repo's bash.

**Run Commands:**
```bash
bats tests/                     # run the whole suite
bats tests/cairn-gate.bats      # run one file
bats tests/cairn-gate.bats -f "milestone scoping"   # filter by test name (-f)
```
No watch mode, no coverage tooling (shell test coverage is not commonly
instrumented; none is configured here).

**Prerequisites (documented in `tests/README.md` and `CONTRIBUTING.md`):**
- `bats-core`
- `jq`
- `bd` (the beads CLI) — required for `bd`-dependent tests, which skip
  cleanly via `require_bd` when it's missing. Install: `brew install beads`.
- `python3` (used pervasively for JSON handling inside tests and for the
  scripts under test).
- `gh` CLI is NOT required even for the GitHub adapter test — dry-run tests
  never reach the network (see `gbsync.bats`).

## Test File Organization

**Location:**
- Flat directory: `tests/*.bats`, one file per script (mirrors
  `cairn/scripts/*.py` one-to-one), plus `tests/helpers.bash` (shared
  fixtures, not itself a test file) and `tests/README.md` (philosophy doc).

**Naming:**
- `<script-basename>.bats` — `cairn-gate.bats` tests `cairn-gate.py` /
  `cairn-gate.sh` together (through the `.sh` wrapper, exercising both in the
  same file since the wrapper just `exec`s the `.py`).
- `smoke.bats` — proves the test harness itself works (fixture builders
  produce valid state); no cairn script is under test here.
- `hooks.bats` — the three Claude Code hooks together (`post-bd-write.sh`,
  `session-start.sh`, `session-stop.sh`), since they're small and share
  fixture/stub patterns.
- `capability.bats` — the GSD capability bundle under `cairn/capability/`
  (manifest shape, fragment/script integrity, the bundled gate).

**Current inventory (100 tests total):**
| File | Tests | Subject |
|------|-------|---------|
| `hooks.bats` | 18 | session-start, session-stop, post-bd-write |
| `cairn-doctor.bats` | 16 | consistency doctor's 9 checks |
| `cairn-gate.bats` | 13 | ship gate + pre-push shim |
| `capability.bats` | 13 | GSD capability bundle |
| `cairn-map.bats` | 12 | NN-BEADS-MAP.md generation |
| `cairn-migrate.bats` | 11 | migration engine |
| `smoke.bats` | 6 | harness self-test |
| `cairn-relabel.bats` | 4 | label/metadata repair |
| `gbsync.bats` | 4 | sync dispatcher dry-run contract |
| `cairn-init.bats` | 3 | git+beads bootstrap |

**Structure:**
```
tests/
├── README.md          # philosophy + fixture helper index (read first)
├── helpers.bash        # load 'helpers' — shared fixture builders + assertions
├── smoke.bats
├── hooks.bats
├── cairn-init.bats
├── cairn-gate.bats
├── cairn-doctor.bats
├── cairn-map.bats
├── cairn-migrate.bats
├── cairn-relabel.bats
├── gbsync.bats
└── capability.bats
```

## The Testing Philosophy (read `tests/README.md` first)

> Deterministic behavior lives in CLI scripts under `cairn/scripts/`. Tests
> invoke those scripts against temp fixture repos and assert on resulting
> files, exit codes, and bd state via `bd list --json` — never on script
> internals. If a behavior can't be asserted through a script's CLI
> contract, move the behavior into a script first.

This is the load-bearing rule for the whole suite ("the seam"): **tests are
black-box, CLI-contract tests against a real script binary, run inside a
disposable git repo.** Never:
- Import/source a script's internals to unit-test individual functions.
- Reach into `.beads/` storage directly to assert state — always go through
  `bd list --json` / `bd show --json`.
- Mock `bd` itself for tests that exercise real bd behavior — `require_bd`
  skips cleanly instead, keeping tests honest about real tracker behavior.

`CONTRIBUTING.md` reinforces this as a contribution rule: **"Every new
script ships with a `.bats` file. Every bug fix in a script ships with the
test that would have caught it."**

## Test Structure

Every test follows the same shape: build a throwaway fixture, run the script
via `run`, assert on `$status` and `$output` (or on files/`bd list --json`
written as a side effect).

```bash
@test "reopened completed-phase issue fails the gate: exit 6, id listed" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  bd update "$GATE_A1" -s open >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 6 ]
  grep -qF "GATE FAILED" <<<"$output"
  grep -qE "^${GATE_A1}[[:space:]]" <<<"$output"
  refute_in_output "$GATE_P2"
}
```

**Patterns:**
- **Setup:** `require_bd` first (if the test needs `bd`), then
  `make_tmp_repo` (creates + `cd`s into a throwaway git repo), then one or
  more fixture builders (`make_gsd_fixture`, `make_bd_fixture`, or a local
  per-file fixture helper like `make_gate_fixture` in `cairn-gate.bats`).
- **Local fixture helpers:** test files define their own scenario-specific
  builder functions on top of the shared ones — e.g.
  `cairn-gate.bats:make_gate_fixture` layers bd issues with GSD-style labels
  on top of `make_gsd_fixture`; `cairn-doctor.bats:add_plan_beads` mutates a
  fixture's PLAN.md frontmatter via an inline `python3 - <<'PY'` heredoc.
- **Invocation:** always `run bash "$CAIRN_SCRIPTS_DIR/<script>.sh" [args]`
  (or `run python3 "$CAIRN_SCRIPTS_DIR/<script>.py" [args]` when testing the
  Python entry point directly, as in `gbsync.bats`) — never a bare function
  call.
- **Teardown:** none needed — `make_tmp_repo` places the fixture under
  `BATS_TEST_TMPDIR` when running inside bats, so bats removes it
  automatically after the test. A manual `cleanup_tmp_repos` exists for the
  (rare) case of calling helpers outside bats.

## Assertion Style Gotcha (documented in-repo, read before writing tests)

Every `.bats` file that needs it carries this comment verbatim:

> Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
> bats test on this bash, so substring checks use `grep -qF` over `"$output"`
> and negative checks use `refute_in_output`.

Concretely:
- **Positive substring check:** `grep -qF "expected text" <<<"$output"` (or
  `printf '%s\n' "$output" | grep -qF -- "$1"` inside a helper), never
  `[[ "$output" == *"text"* ]]`.
- **Negative substring check:** use the locally-defined `refute_in_output`
  helper (redefined per test file, not shared in `helpers.bash`):
  ```bash
  refute_in_output() {
    if grep -qF -- "$1" <<<"$output"; then
      echo "unexpectedly found '$1' in output" >&2
      return 1
    fi
  }
  ```
- Exact-match checks use `[ "$output" = "..." ]` or `[ "$line" = "..." ]`
  freely — the pitfall is specific to negated conditionals mid-test, not to
  `[ ]` itself.
- Regex line-anchored checks use `grep -qE "^${ID}[[:space:]]"` to assert an
  id starts its own output line (avoids false positives from ids appearing
  as substrings elsewhere).

## Mocking / Stubbing

No mocking framework — bash scripts are stubbed by **replacing the binary on
`$PATH` or via an env-var seam**, matching the CLI-contract testing
philosophy.

**Env-var seams (preferred, used by hooks):**
`post-bd-write.sh` reads `CAIRN_GBSYNC` / `CAIRN_MAP` to locate the scripts
it shells out to; tests override them with **recorder stubs** — tiny
executable scripts that log their invocation and exit 0:

```bash
make_recorders() {
  GBSYNC_STUB="$BATS_TEST_TMPDIR/gbsync-recorder"
  GBSYNC_LOG="$BATS_TEST_TMPDIR/gbsync.log"
  printf '#!/usr/bin/env bash\necho "$@" >> "%s"\n' "$GBSYNC_LOG" > "$GBSYNC_STUB"
  chmod +x "$GBSYNC_STUB"
}

post_bd_write() {
  printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1" \
    | env CLAUDE_PROJECT_DIR="$PWD" CAIRN_GBSYNC="$GBSYNC_STUB" \
      bash "$CAIRN_HOOKS_DIR/post-bd-write.sh"
}
```
Assertions then check the recorder's log file for the expected invocation
(`grep -qxF "close map-1" "$GBSYNC_LOG"`), after polling for it since the
hook backgrounds the work (see "Background Job Testing" below). The same
pattern stubs the ship gate for the pre-push shim test (`CAIRN_GATE`,
`cairn-gate.bats:make_gate_stub`) — a stub that just echoes and exits a
fixed code, used to isolate the shim's exit-code-to-behavior contract from
the real gate's logic (already covered by `cairn-gate.bats` itself).

**PATH-replacement seams (for binary unavailability):**
`cairn-gate.bats`'s "bd missing from PATH" test builds a minimal stub `bin/`
directory containing only symlinks to the real interpreter/binaries it needs
(`python3`, `bash`, `dirname`) — deliberately excluding `bd` — then runs the
script with `PATH` pointed only at that directory:
```bash
local stub="$BATS_TEST_TMPDIR/nobd-bin"
mkdir -p "$stub"
ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$stub/python3"
ln -s "$(command -v bash)" "$stub/bash"
run env PATH="$stub" "$stub/bash" "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
[ "$status" -eq 5 ]
```
This avoids a fragile version-manager shim on PATH — link the real
interpreter binary directly.

**Network isolation:**
`gbsync.bats` never touches the network: `--dry-run` is a first-class CLI
contract (documented in `gbsync.py`'s own docstring) that walks the same
decision logic but only prints `DRY-RUN:` lines without invoking any
adapter. Tests set a deliberately fake `GH_TOKEN="dummy-not-a-real-token"`
to prove dry-run never reaches `gh`/the network even with bogus credentials
present.

**What to Mock:**
- External side effects with real-world consequences (network calls via
  adapters, background sync pushes) — via recorder stubs or `--dry-run`.
- Binary *unavailability* — via a minimal stub PATH.

**What NOT to Mock:**
- `bd` itself for tests that need real tracker semantics — use `require_bd`
  and a real `bd init`/`bd create` fixture instead of faking `bd list --json`
  output. This keeps tests honest against the actual CLI contract.
- Script internals — never source a script to call an inner function
  directly; always invoke the full CLI.

## Fixtures and Factories (`tests/helpers.bash`)

All shared fixture builders live in `tests/helpers.bash`, loaded via `load
'helpers'` at the top of every `.bats` file.

| Helper | Produces |
|--------|----------|
| `require_bd` | Skips the test (`skip "..."`) when `bd` is not on `$PATH` |
| `make_tmp_repo` | `mktemp -d` under `$BATS_TEST_TMPDIR`, `git init -q`, sets a fixed test committer identity, `cd`s in |
| `make_gsd_fixture DIR` | A structurally faithful `.planning/` tree: `ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md` (with YAML frontmatter), phase 1 (complete: PLAN+SUMMARY+VERIFICATION) and phase 2 (mid-flight: PLAN only) |
| `make_bd_fixture DIR [PREFIX]` | `bd init` + an epic, two children (one closed), one standalone issue with a `blocks` dep and a label; issue ids exported as `BD_EPIC`, `BD_CHILD_OPEN`, `BD_CHILD_CLOSED`, `BD_STANDALONE` |
| `extract_frontmatter FILE` | Prints the YAML frontmatter block (between the first two `---` lines) via `awk` |
| `assert_frontmatter_key FILE KEY` | Fails with a message if `KEY:` is absent from the frontmatter |
| `assert_json_eq JSON FILTER EXPECTED` | `jq -r "$FILTER" <<<"$JSON"` compared to `$EXPECTED`, with a diagnostic message on mismatch |

**Test Data:**
Fixture content is written inline via heredocs in `helpers.bash` (see
`make_gsd_fixture`, ~150 lines of realistic ROADMAP/REQUIREMENTS/STATE/PLAN/
SUMMARY/VERIFICATION markdown with real GSD frontmatter shapes) — not loaded
from separate fixture files. Keep new fixtures in this same inline-heredoc
style so they stay next to the helper that builds them.

**Location:** `tests/helpers.bash` only — no `tests/fixtures/` directory.

## Background Job / Async Testing

Hooks that fire background work (`nohup ... &`) are tested by **polling for
the observable side effect** rather than sleeping a fixed duration or making
the code synchronous for tests:

```bash
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
```
Use this pattern (poll with a short sleep and a bounded retry count, fail
loudly with a clear message on timeout) for any new background-job test
rather than a bare `sleep N`. For proving *absence* of a side effect, a
single `sleep 0.5` followed by `[ ! -f "$LOG" ]` is used instead (acceptable
since there's nothing to poll for).

## Coverage

**Requirements:** None enforced — no coverage tool is configured for bash or
Python in this repo. Coverage is a qualitative contract instead: "every new
script ships with a `.bats` file" and "every bug fix ships with the test
that would have caught it" (`CONTRIBUTING.md`).

## Test Types

**Unit-equivalent (CLI-contract) tests:**
The bulk of the suite — treats each script as the unit under test, exercised
through its full CLI surface with a real (disposable) filesystem/git/bd
backing store. This is the dominant and expected style for new tests.

**Integration tests:**
`hooks.bats`'s end-to-end-flavored tests and `cairn-gate.bats`'s
`"end to end: git push blocked..."` test chain multiple scripts/binaries
together (git hooks + the gate script + a bare remote) to prove the whole
pre-push flow works, not just one script in isolation.

**E2E:** Not used (no browser/UI layer exists — this is a CLI plugin).

## CI

`.github/workflows/ci.yml` runs on every push to `main` and every PR:
1. Install `bd` from the beads install script.
2. Install `bats-core` globally via npm.
3. **Lint Python** — `python3 -m py_compile cairn/scripts/*.py
   cairn/adapters/*.py cairn/capability/scripts/*.py` (a syntax check only,
   not a real linter — there is no `ruff`/`flake8`/`pylint` configured).
4. Run the full suite: `bats tests/`.

There is no shellcheck step in CI despite `CONTRIBUTING.md`'s
"shellcheck-clean" rule — treat that rule as a manual discipline to uphold
when writing/reviewing shell, not something CI currently catches.

## Common Patterns

**Skip pattern (external dependency unavailable):**
```bash
require_bd() {
  if ! command -v bd >/dev/null 2>&1; then
    skip "bd is not on PATH — install beads (https://github.com/gastownhall/beads) to run this test"
  fi
}
```
Call `require_bd` as the very first line of any test needing a real `bd`
binary — it must run before any `bd`-touching setup so the skip is clean.

**Exit-code table docstring at the top of a test file:**
Every `.bats` file for a script with a documented exit-code contract restates
that contract in its header comment (mirroring the script's own docstring),
e.g. `cairn-doctor.bats`: "0 all ok or warnings only ..., 2 usage / refused
--fix-labels, 5 bd unavailable, 7 any check failed." Keep this comment in
sync with the script's `EXIT_*` constants when either changes.

**JSON assertion pattern:**
```bash
run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
[ "$status" -eq 0 ]
assert_json_eq "$output" '.applicable' 'true'
assert_json_eq "$output" '.offending | length' '0'
```

**Frontmatter mutation for negative-path tests:**
Small inline `python3 - "$1" <<'PY' ... PY` scripts insert/mutate YAML
frontmatter lines in a fixture file to construct an otherwise-hard-to-build
broken state (e.g. `stamp_state_milestone`, `add_plan_beads`) — prefer this
over hand-writing a second full fixture variant.

---

*Testing analysis: 2026-07-25*
