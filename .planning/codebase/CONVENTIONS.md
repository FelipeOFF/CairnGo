# Coding Conventions

**Analysis Date:** 2026-07-25

## Project Shape

CairnGo ("cairn") is a Claude Code plugin: mostly bash CLI scripts with Python
companions, markdown slash-command/skill definitions, and a `bats-core` test
suite. There is no JS/TS/frontend code. Conventions below are drawn from
`cairn/scripts/`, `cairn/hooks/`, `cairn/adapters/`, `cairn/capability/scripts/`,
and the stated rules in `CONTRIBUTING.md`.

## Naming Patterns

**Files:**
- CLI scripts: kebab-case with a `cairn-` prefix — `cairn-gate.py`,
  `cairn-doctor.py`, `cairn-map.py`, `cairn-migrate.py`, `cairn-relabel.py`,
  `cairn-init.sh`. One exception: `gbsync.py` / `gbsync.sh` (no `cairn-`
  prefix — it's the sync dispatcher, named after its role).
- Every Python script `cairn-X.py` has a thin bash wrapper `cairn-X.sh` of the
  same basename (see "Script pairing" below).
- Hooks: `<lifecycle>.sh` under `cairn/hooks/` — `session-start.sh`,
  `session-stop.sh`, `post-bd-write.sh` (named after the Claude Code hook
  event they bind to: SessionStart, Stop, PostToolUse).
- Adapters: `<service>.py` under `cairn/adapters/` — `github.py`, `jira.py`,
  `gitlab.py`, `asana.py`, `azure-boards.py`.
- Tests: `<script-basename>.bats` under `tests/` — one bats file per script
  (`cairn-gate.bats` tests `cairn-gate.py`/`.sh`), plus `smoke.bats` (harness
  self-test) and `hooks.bats` (all three hooks together).
- Slash commands: `cairn/commands/<verb>.md` — `init.md`, `plan.md`,
  `ship.md`, `sync-config.md`. Multi-word commands use hyphens.
- Skills: `cairn/skills/<name>/SKILL.md` — `cairn`, `cairn-sync`,
  `cairn-context`.

**Functions (Python):**
- `snake_case` throughout, verb-first or noun-phrase: `bd_open_issues`,
  `completed_phases`, `state_milestone`, `roadmap_milestone`, `resolve_adapter`.
- Every script's Python entry point is `main()`, guarded by
  `if __name__ == "__main__":`.
- A `die(msg, code=1)` helper (present in every script with distinct exit
  codes) prints `[<script-name>] error: <msg>` to stderr and calls
  `sys.exit(code)`. Copy this helper's shape when adding a new script rather
  than raising bare exceptions for user-facing failures.
- Argument parsing splits by script complexity: simple scripts (`cairn-gate.py`,
  `cairn-map.py`, `cairn-loop-gate.py`) hand-roll a `parse_args(argv)` loop
  over `sys.argv[1:]`; scripts with several flags (`cairn-doctor.py`,
  `cairn-migrate.py`, `cairn-relabel.py`) use stdlib `argparse`. Prefer
  hand-rolled parsing for scripts with ≤2 flags, `argparse` beyond that.

**Functions (Bash):**
- Lowercase `snake_case` for local helper functions defined inline in a
  `.bats` file (`require_bd`, `make_tmp_repo`, `make_gsd_fixture`,
  `wait_for_lines`). Scripts themselves are mostly linear (no functions) —
  bash scripts under `cairn/scripts/` and `cairn/hooks/` are short,
  step-numbered procedures rather than function libraries.

**Variables:**
- Bash: `UPPER_CASE` for script-scoped "constants" set once near the top
  (`HERE`, `DIR`, `GI`, `SHIM`, `SHIM_MARKER`, `HOOKS_DIR`, `PROJECT_DIR`),
  lowercase for transient loop/local values (`entry`, `dir`, `line`).
- Python: `UPPER_CASE` module-level constants for exit codes and compiled
  regexes (`EXIT_OK`, `EXIT_GATE_FAILED`, `CHECKED_PHASE = re.compile(...)`),
  `snake_case` for everything else.
- Environment variable seams (test/override points) are always `UPPER_CASE`
  with a `CAIRN_` prefix — `CAIRN_GBSYNC`, `CAIRN_MAP`, `CAIRN_GATE`,
  `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_DATA`.

**Types (Python):**
- No type hints anywhere in the codebase (stdlib-only, keep it simple —
  matches the "Python: stdlib only" rule in `CONTRIBUTING.md`). Do not
  introduce `typing` imports or dataclasses; stay consistent with the
  existing plain-function style.

## Code Style

**Shell (bash):**
- Every script/hook opens with `#!/usr/bin/env bash` then `set -euo pipefail`
  (hooks that must never fail the tool call use `set -uo pipefail` instead —
  see `cairn/hooks/post-bd-write.sh` line 27 — because a hook's contract is
  "always exit 0", so `-e` would be wrong there).
- CONTRIBUTING.md states the rule explicitly: "Shell: bash, `set -euo
  pipefail`, shellcheck-clean." No `.shellcheckrc` exists and CI does not run
  shellcheck automatically — treat the rule as a manual pre-commit discipline,
  not an enforced gate.
- Heredocs (`cat <<'EOF'` / `cat <<SHIM_EOF`) generate multi-line output
  blocks and embedded scripts (see the pre-push shim generation in
  `cairn/scripts/cairn-init.sh:102-140`). Quote the heredoc delimiter
  (`<<'EOF'`) to suppress interpolation when embedding literal `$` — use an
  unquoted, uniquely-named delimiter (`<<SHIM_EOF`) only when interpolation
  of the outer script's variables is intentional.
- Numbered step comments organize longer scripts: `# 1. git repo`, `# 2.
  beads binary must be present`, etc. (`cairn-init.sh`). Section-banner
  comments (`# --- (a) mirror push ---`) mark logical blocks in hooks.
- User-facing stdout lines are prefixed with a bracketed tag and use
  ASCII-safe status glyphs consistently: `✓` (done), `✗` (hard failure), `⚠`
  (soft warning), `▸` (section/step marker), `!` (attention). Every line a
  script prints starts with `[cairn-<script>]` or `[cairn]` so output is
  greppable and attributable when scripts run inside hooks or CI.
- Prefer `command -v X >/dev/null 2>&1` over `which X` for existence checks.

**Python:**
- Every script/adapter starts with `#!/usr/bin/env python3` and a triple-
  quoted module docstring documenting: what the script does, its usage
  string, its exit code contract (numbered list), and any data-shape
  contracts (adapter stdin/stdout JSON shapes, state file locations). Treat
  the docstring as the canonical spec — write it before or alongside the
  code, not as an afterthought.
- Imports: stdlib only, one per line, alphabetical within the block —
  `json`, `os`, `re`, `shutil`, `subprocess`, `sys`, then `from pathlib
  import Path` / `from datetime import datetime, timezone` last. No
  third-party dependencies anywhere in `cairn/scripts/`, `cairn/adapters/`,
  or `cairn/capability/scripts/` — this is a hard constraint ("the sync
  layer must run anywhere Claude Code runs").
- `subprocess.run(..., capture_output=True, text=True)` is the standard shape
  for shelling out to `bd`, `gh`, or another script; check `.returncode`
  explicitly rather than relying on `check=True` + exception handling in
  most call sites (exception is `bd_fetch` in `gbsync.py`, which does use
  `check=True` + `except subprocess.CalledProcessError`).
- JSON I/O: `json.loads`/`json.dumps(obj, indent=2, sort_keys=True) + "\n"`
  when writing state files (`gbsync.py:write_json`) — always sorted keys and
  a trailing newline for git-diff-friendliness.
- Line length is soft-wrapped near 79-88 cols with continuation strings
  broken mid-sentence (`f"..." \n f"..."` patterns); no enforced formatter
  (no `black`/`ruff` config in the repo) — match the surrounding file's
  wrap width by eye.

## Script Pairing (the `.sh` / `.py` seam)

Every deterministic script ships as a Python implementation plus a thin bash
wrapper of the identical basename:

```bash
#!/usr/bin/env bash
# Thin wrapper around the cairn ship gate. See cairn-gate.py for the contract.
# Usage: cairn-gate.sh [--planning-dir <dir>] [--json]
# Exit:  0 clear / not applicable, 2 usage, 5 bd unavailable, 6 gate failed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-gate.py" "$@"
```

The wrapper's header comment restates the exit-code contract (so a reader
never has to open the `.py` file just to know what a given exit code means)
and `exec`s into `python3`, passing `"$@"` through unmodified. When adding a
new deterministic behavior: write the `.py` implementation and its `.sh`
wrapper together, and update the header comment's exit-code line in lockstep
with `EXIT_*` constants in the Python file.

## Exit Code Convention

Exit codes are a deliberate, script-specific contract — always documented in
the module docstring and mirrored by `EXIT_*` constants at the top of the
file. Shared meanings across scripts:

| Code | Meaning | Convention |
|------|---------|------------|
| 0 | OK, or not applicable | Always: success or "this repo doesn't need this check" |
| 2 | Usage error | Bad flags/arguments |
| 5 | `bd` unavailable | Availability failure, never treated as a check failure — callers (e.g. the pre-push shim) must NOT block on 5 |
| 6 | Gate failed (`cairn-gate.py`) | The only code the pre-push shim blocks a push on |
| 7 | Doctor check failed (`cairn-doctor.py`) | One or more consistency checks failed |
| 3, 4, 8 | Script-specific (`cairn-map.py`: 3=stale, 4=no such phase; `cairn-migrate.py`: 8=partial) | See each script's docstring |

When adding a new script with distinct failure modes, define `EXIT_*`
constants (never bare integers inline) and document every code in the
docstring's numbered list, following `cairn-gate.py` as the template.

## Import Organization

Not applicable in the JS/TS sense — this is a bash+Python CLI codebase. Python
import order: stdlib modules grouped together, no blank-line separation
convention observed beyond "stdlib general imports first, `from X import Y`
last" (see `gbsync.py:38-43`).

## Error Handling

**Python:**
- User-facing errors go through `die(msg, code)`, never a raw traceback.
  `die` prints to stderr with the `[<tool>] error: ...` prefix and exits with
  the documented code.
- Subprocess failures are caught explicitly and converted to either a `die()`
  call (fatal) or a per-item error string appended to a `results` list
  (non-fatal, aggregated — see `gbsync.py:do_push`/`do_pull`, which continue
  processing other backends after one fails and report `FAIL` inline rather
  than aborting).
- JSON parse failures are always wrapped: `except json.JSONDecodeError as e:
  die(f"... is not valid JSON: {e}")` — never let a bare `JSONDecodeError`
  propagate to the user.
- Availability vs. correctness failures are distinguished by exit code (5 vs.
  everything else) so callers can choose to warn-and-continue on
  unavailability while still hard-failing on a real check failure. Preserve
  this distinction in new scripts that shell out to `bd` or another external
  tool.

**Bash:**
- `set -euo pipefail` is the baseline; hooks that must never abort in the
  middle of user work drop `-e` deliberately (`post-bd-write.sh`) and instead
  guard every risky step with explicit `|| exit 0` / `2>/dev/null || true`.
- Hooks follow a strict "never break the caller" contract: `post-bd-write.sh`,
  `session-start.sh`, and `session-stop.sh` all `exit 0` unconditionally at
  the end, regardless of internal outcome — their job is to inject context or
  fire background work, never to fail the tool call or the session.
- Background/fire-and-forget work uses `nohup ... >/dev/null 2>&1 &` so the
  hook returns immediately; tests poll for the side effect (`wait_for_lines`)
  rather than waiting synchronously.

## Comments

- Every script/hook file has a substantial header comment or docstring
  explaining *why* it exists, its usage, and its contract (exit codes, data
  shapes, background-job behavior) — not just a one-line description.
- Inline comments explain **non-obvious "why"** decisions, especially around
  edge cases discovered from real bugs: e.g. `cairn-gate.py:139-145` explains
  why `--all` + client-side filtering is used instead of a server-side status
  filter; `post-bd-write.sh:83-93` explains the flag/value-token heuristic
  for extracting a bd issue id from an arbitrary `bd` command line.
- Bats test files open with a comment block explaining what's under test,
  the assertion-style gotcha for that bash (`refute_in_output` vs `! cmd`),
  and any test-harness-specific caveats — read the top of a `.bats` file
  before reading its tests.

## Documentation-as-Contract

`cairn/adapters/_contract.md` and `cairn/docs/*.md` are the canonical specs
for cross-cutting contracts (adapter stdin/stdout shape, sync state files,
capability manifest). When a script's behavior touches one of these
contracts, update the doc in the same change — the doc is not optional
descriptive prose, it is load-bearing for anyone implementing a new adapter
or backend.

## Module Design

- Each script is a single flat file — no package structure, no shared
  `lib/` module imported across scripts (the `stdlib only` / "must run
  anywhere Claude Code runs" constraint favors self-contained files over a
  shared library, even at the cost of some duplication, e.g. `die()` is
  reimplemented per-script rather than imported).
- Adapters are fully independent executables (any language) invoked via
  subprocess with a JSON stdin/stdout contract (`cairn/adapters/_contract.md`)
  — never imported as Python modules. This keeps `gbsync.py` decoupled from
  adapter implementation details and lets adapters be written in any
  language.
- `cairn/capability/scripts/` intentionally re-vendors thin wrappers
  (`cairn-loop-gate.sh`, `cairn-map.sh`) rather than importing from
  `cairn/scripts/` — the capability bundle must be self-contained since GSD
  loads it independently.

## Markdown Command/Skill Conventions

- `cairn/commands/*.md` are "thin wrappers": prose that delegates
  deterministic work to a `cairn/scripts/*.sh` invocation rather than
  re-describing logic in prose. Per `CONTRIBUTING.md`: "If a SKILL.md
  sentence can be a script check, make it one."
- `cairn/skills/<name>/SKILL.md` documents conventions the agent follows
  (label pairing, metadata stamps, generated-file markers) — these are
  read by Claude at runtime, so precision and explicit examples matter more
  than brevity.
- Generated content inside markdown (e.g. `NN-BEADS-MAP.md`) is fenced with
  `<!-- cairn:generated:start -->` / `<!-- cairn:generated:end -->` markers;
  content between the markers is written only by `cairn-map.sh` and must
  never be hand-edited — this convention is enforced by tests, not tooling.

## Commits

- Conventional Commits, scoped to the affected area: `feat(cairn): …`,
  `fix(sync): …` (per `CONTRIBUTING.md`).

---

*Convention analysis: 2026-07-25*
