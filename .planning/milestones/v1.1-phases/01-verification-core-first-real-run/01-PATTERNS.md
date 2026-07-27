# Phase 1: Verification Core + First Real Run - Pattern Map

**Mapped:** 2026-07-25
**Files analyzed:** 10 (new)
**Analogs found:** 7 / 10 (3 have no close analog — data/prose fixtures)

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|-----------------|----------------|
| `benchmarks/scripts/bench-run.py` | controller / CLI harness | request-response (subprocess invoke + JSON parse) + batch (JSONL append) | `cairn/scripts/gbsync.py` (subprocess+JSON pattern) and `cairn/scripts/cairn-map.py` (docstring/exit-code contract, arg parsing) | role-match (composite of two analogs) |
| `benchmarks/scripts/bench-run.sh` | wrapper | request-response (exec passthrough) | `cairn/scripts/cairn-map.sh` | exact |
| `benchmarks/tasks/smoke-convert/verify.sh` | test oracle / gate script | request-response (exit code = verdict) | `cairn/scripts/cairn-gate.py` / `cairn-gate.sh` (exit-code-is-the-verdict philosophy) — no bash analog shells to pytest anywhere in repo | partial (philosophy match, shape from RESEARCH.md) |
| `benchmarks/tasks/smoke-convert/task.json` | config/manifest | static data (JSON) | `.cairn/sync.json` (small hand-authored committed JSON config, seen in `tests/gbsync.bats:15-24`) | partial (role-match, different domain) |
| `benchmarks/tasks/smoke-convert/prompt.md` | fixture content | static data | none — plain prose, no code pattern applies | no analog |
| `benchmarks/tasks/smoke-convert/fixture/convert.py` + `fixture/tests/test_convert.py` | fixture / test data | static data | none — repo has no pytest-tested application code (cairn's own scripts are bats-tested, not pytest-tested) | no analog |
| `tests/bench-run.bats` | test (bats) | request-response (CLI-contract test) + event-driven (recorder-stub assertions) | `tests/hooks.bats` (env-var seam + recorder stub) + `tests/gbsync.bats` (invoke `python3 script.py` directly, JSON output) + `tests/cairn-map.bats` (PATH-stub absence test, exit-code table) | exact (composite of three analogs) |
| `benchmarks/README.md` | doc | n/a | `tests/README.md` (terse, prescriptive doc style) | style-only |
| `benchmarks/results/` (`.gitkeep` + the one committed JSONL row) | output artifact | batch (append-only) | none — new artifact category | no analog |

## Pattern Assignments

### `benchmarks/scripts/bench-run.py` (controller, request-response + batch)

**Primary analog (subprocess + JSON + env-var seam):** `cairn/scripts/gbsync.py`
**Secondary analog (docstring contract, arg parsing, exit codes):** `cairn/scripts/cairn-map.py`

**Module docstring contract** (`cairn/scripts/cairn-map.py` lines 1-42) — the canonical shape every new script's docstring must follow: one-line summary, `Usage:` block, numbered `Behavior:` steps, `Exit codes:` list. Copy this shape verbatim for `bench-run.py`'s docstring (RESEARCH.md's own Code Examples section already drafts one in this exact shape — use that draft, not a fresh format).

**Imports pattern** (`cairn/scripts/gbsync.py` lines 38-43, confirmed by `CONVENTIONS.md` lines 108-113):
```python
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
```
Stdlib only, one per line, alphabetical within the block, `from X import Y` last. `bench-run.py` additionally needs `shutil`, `tempfile`, `time` — same ordering rule applies.

**`die()` helper** (`cairn/scripts/gbsync.py` lines 51-53, identical shape in `cairn-map.py` lines 68-70 and `cairn-gate.py` lines 68-70):
```python
def die(msg, code=1):
    print(f"[gbsync] error: {msg}", file=sys.stderr)
    sys.exit(code)
```
For `bench-run.py`: `def die(msg, code): print(f"[bench-run] error: {msg}", file=sys.stderr); sys.exit(code)` — tag prefix matches the script's own bracketed name per `CONVENTIONS.md` line 94-98.

**`EXIT_*` constants** (`cairn/scripts/cairn-map.py` lines 56-60):
```python
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_STALE = 3
EXIT_NO_PHASE = 4
EXIT_NO_BD = 5
```
`bench-run.py` needs at minimum `EXIT_OK = 0` and `EXIT_USAGE = 2` per RESEARCH.md's own draft (run failures are recorded as JSONL data, not harness exit failures — see RESEARCH.md's docstring skeleton, "Exit codes: 0 run completed ... 2 usage error").

**Env-var seam (the core pattern for HARN-03's stub-ability)** — exact mechanics from `cairn/hooks/post-bd-write.sh` lines 32-33:
```bash
GBSYNC="${CAIRN_GBSYNC:-$PLUGIN_ROOT/scripts/gbsync.sh}"
CAIRN_MAP="${CAIRN_MAP:-$PLUGIN_ROOT/scripts/cairn-map.sh}"
```
Python equivalent for `bench-run.py` (already spec'd in RESEARCH.md "Pattern 2"):
```python
def resolve_claude_bin():
    return os.environ.get("CAIRN_BENCH_CLAUDE_BIN") or shutil.which("claude") or "claude"
```
Confirmed naming rule: `.planning/codebase/CONVENTIONS.md` lines 64-66 — "Environment variable seams ... are always `UPPER_CASE` with a `CAIRN_` prefix." Use `CAIRN_BENCH_CLAUDE_BIN`, not the bare `BENCH_CLAUDE_BIN` CONTEXT.md used illustratively.

**Core subprocess + JSON pattern** (`cairn/scripts/gbsync.py` lines 88-97, `136-147`) — the closest existing "shell out to an external binary, capture JSON, handle failure without raising" pattern in the repo:
```python
def bd_fetch(bd_id):
    try:
        out = subprocess.run(["bd", "show", bd_id, "--json"],
                             capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        die("'bd' not found on PATH")
    except subprocess.CalledProcessError as e:
        die(f"bd show {bd_id} failed: {e.stderr.strip()}")
    data = json.loads(out)
    ...

def run_adapter(adapter_path, event):
    ...
    proc = subprocess.run(cmd, input=json.dumps(event),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return None, proc.stderr.strip() or f"exit {proc.returncode}"
    return proc.stdout.strip(), None
```
Adapt for `bench-run.py`: call `subprocess.run([...], cwd=workdir, capture_output=True, text=True, timeout=timeout_s)`, then `json.loads(proc.stdout)` **regardless of `proc.returncode`** (RESEARCH.md Pitfall 1 — do not gate JSON parsing on the exit code, unlike `gbsync.py`'s `check=True` pattern which is the one documented exception per `CONVENTIONS.md` lines 114-118: "check `.returncode` explicitly rather than relying on `check=True`... most call sites").

**JSON write pattern** (`cairn/scripts/gbsync.py` lines 83-85, confirmed `CONVENTIONS.md` lines 119-121):
```python
def write_json(path, obj):
    Path(path).parent.mkdir(exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
```
`bench-run.py` writes one JSONL *line* per run (append mode, `sort_keys=True`, no indent since it's one line) rather than a whole-file rewrite — same `json.dumps(..., sort_keys=True)` discipline, different I/O shape (`open(out_path, "a")` + single `f.write(json.dumps(row, sort_keys=True) + "\n")`, already drafted in RESEARCH.md's Code Examples section).

**Error handling pattern** (`CONVENTIONS.md` lines 177-193): user-facing errors go through `die()`, never a raw traceback; subprocess failures are either fatal (`die()`) or aggregated into a results list; JSON parse failures are always wrapped in a caught `except json.JSONDecodeError`. For `bench-run.py` specifically: **never let a `subprocess.TimeoutExpired` or `json.JSONDecodeError` propagate raw** — catch both, the latter becomes a synthetic `{"is_error": true, "parse_error": ...}` row (per RESEARCH.md Pitfall 1), not a `die()` call, since a malformed `claude` response is data to record, not a harness usage error.

**Argument parsing:** `bench-run.py`'s surface is tiny (`--task`, `--out`) — per `CONVENTIONS.md` lines 44-48 ("Prefer hand-rolled parsing for scripts with ≤2 flags"), hand-roll a `parse_args(argv)` loop like `cairn-map.py` lines 73-108, not `argparse`.

---

### `benchmarks/scripts/bench-run.sh` (wrapper, request-response)

**Analog:** `cairn/scripts/cairn-map.sh` (full file, 8 lines) — copy verbatim, substituting the script name:
```bash
#!/usr/bin/env bash
# Thin wrapper around the cairn-map generator. See cairn-map.py for the contract.
# Usage: cairn-map.sh <phase-number> [--milestone <m>] [--planning-dir <dir>]
#        [--check] [--json]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-map.py" "$@"
```
Per `CONVENTIONS.md` lines 127-147: the wrapper's header comment must restate the exit-code contract so a reader never has to open the `.py` file, and it `exec`s into `python3` passing `"$@"` through unmodified. Keep the header's exit-code line in lockstep with `bench-run.py`'s `EXIT_*` constants.

---

### `benchmarks/tasks/smoke-convert/verify.sh` (test oracle, request-response)

**No close bash analog exists in this repo** — nothing currently shells out to `pytest`. The closest *philosophical* analog is `cairn/scripts/cairn-gate.py`'s exit-code-is-the-verdict contract (docstring lines 36-46: exit 0 clear, exit 6 = GATE FAILED, "Only exit 6 may block a push") — same principle HARN-01 requires ("exit code = pass/fail... never LLM self-report"). Use RESEARCH.md's own Pattern 1 skeleton directly (it is the concrete, already-vetted shape for this file — no repo rewrite needed):
```bash
#!/usr/bin/env bash
# verify.sh <workdir> — exit 0 = task solved, non-zero = not solved.
# Never staged inside <workdir>; invoked with its path as an argument.
set -euo pipefail
WORKDIR="$1"
cd "$WORKDIR"
exec python3 -m pytest tests/test_convert.py -q
```
Bash header convention still applies from the repo's own house style: `#!/usr/bin/env bash` + `set -euo pipefail` (`CONVENTIONS.md` lines 76-84), and a one-line "why" comment block (`CONVENTIONS.md` lines 207-213) — RESEARCH.md's skeleton already carries both.

---

### `benchmarks/tasks/smoke-convert/task.json` (config/manifest, static data)

**Analog:** `.cairn/sync.json`, the closest small hand-authored committed JSON config in the repo, shown inline in `tests/gbsync.bats` lines 15-24:
```json
{
  "backends": [
    { "type": "github", "enabled": true, "adapter": "github",
      "config": { "repo": "example/fixture", "extra_labels": [] } }
  ]
}
```
Structural takeaway for `task.json`: flat, hand-readable JSON object, no nesting beyond one level where avoidable, committed to git, consumed by `json.loads(Path(...).read_text())` (matching `gbsync.py`'s `load_json` helper, lines 74-80) rather than any schema validation library — this repo never validates JSON config against a schema, it just reads the keys it expects and lets a `KeyError`/`.get(..., default)` handle absence. Recommended shape per RESEARCH.md: `{"id": "smoke-convert", "timeout_s": 60, "max_turns": 5, "prompt_file": "prompt.md"}`.

---

### `tests/bench-run.bats` (test, request-response + event-driven)

**Primary analog (env-var seam + recorder stub):** `tests/hooks.bats`
**Secondary analog (invoke `python3 script.py` directly, JSON assertions):** `tests/gbsync.bats`
**Tertiary analog (PATH-stub absence test, exit-code table header comment):** `tests/cairn-map.bats`

**File header pattern** (`tests/cairn-map.bats` lines 1-11, `TESTING.md` lines 346-351) — every `.bats` file opens with a comment block naming what's under test, the exit-code contract, and the assertion-style gotcha:
```bash
#!/usr/bin/env bats
# bench-run.bats — exercises bench-run.py / the bench-run.sh wrapper's CLI
# contract: fixture staging, claude subprocess invocation via the
# CAIRN_BENCH_CLAUDE_BIN stub seam, one JSONL row per run, verify.sh
# integration. Never invokes the real claude binary.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so substring checks use grep -qF and negative
# checks use refute_in_output.

load 'helpers'
```

**Env-var seam / recorder-stub pattern** (`tests/hooks.bats` lines 22-32, confirmed `TESTING.md` lines 185-203) — this is the exact mechanism to adapt for stubbing `claude` via `CAIRN_BENCH_CLAUDE_BIN`:
```bash
make_claude_stub() {
  STUB="$BATS_TEST_TMPDIR/claude-stub"
  cat > "$STUB" <<'EOF'
#!/usr/bin/env bash
cat <<'JSON'
{"type":"result","subtype":"success","is_error":false, ...}
JSON
EOF
  chmod +x "$STUB"
}
```
This is a **canned-output stub**, not the plain "recorder" (`echo "$@" >> log`) hooks.bats uses for `CAIRN_GBSYNC`/`CAIRN_MAP` — `bench-run.py`'s test needs the stub to emit a JSON payload on stdout, not just log its invocation. RESEARCH.md's "Pattern 2" code example already has this exact stub written out; use it verbatim.

**Invocation pattern** (`tests/gbsync.bats` lines 26-39, `TESTING.md` line 143 — "or `run python3 ... .py` when testing the Python entry point directly, as in `gbsync.bats`"):
```bash
run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$BD_EPIC" --dir "$PWD" --dry-run
[ "$status" -eq 0 ]
[ "$output" = "DRY-RUN: github create $BD_EPIC -> (new)" ]
```
For `bench-run.py`, invoke via `env CAIRN_BENCH_CLAUDE_BIN="$STUB" python3 "$BENCH_SCRIPTS_DIR/bench-run.py" --task ... --out ...` (exact test drafted in RESEARCH.md Pattern 2).

**PATH-stub absence-test pattern** (`tests/cairn-map.bats` lines 219-231, confirmed `TESTING.md` lines 212-226) — reserved for a *possible additional* "claude missing" test, not the main HARN-03 ask:
```bash
local stub="$BATS_TEST_TMPDIR/nobd-bin"
mkdir -p "$stub"
ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$stub/python3"
ln -s "$(command -v bash)" "$stub/bash"
run env PATH="$stub" "$stub/bash" "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1
[ "$status" -eq 5 ]
```
Use this shape **only** if `bench-run.py` gets its own "claude binary entirely absent" exit-code test — a different scenario from canned-output stubbing (RESEARCH.md's own caveat, "Pattern 2" closing note).

**JSON assertion helper** (`tests/helpers.bash` lines 343-351, already loaded via `load 'helpers'`):
```bash
assert_json_eq() {
  local json="$1" filter="$2" expected="$3"
  local actual
  actual="$(jq -r "$filter" <<<"$json")"
  if [ "$actual" != "$expected" ]; then
    echo "jq '$filter' returned '$actual', expected '$expected'" >&2
    return 1
  fi
}
```
Use for asserting individual JSONL row fields, e.g. `assert_json_eq "$(cat "$BATS_TEST_TMPDIR/raw.jsonl")" '.total_cost_usd' '0.0031'` (drafted in RESEARCH.md Pattern 2).

**Assertion-style gotcha** (`TESTING.md` lines 150-177, `tests/hooks.bats` lines 15-20) — never `[[ "$output" == *"text"* ]]` or a bare `! cmd`; always `grep -qF "text" <<<"$output"` for positive substring checks and a locally-redefined `refute_in_output` for negative ones:
```bash
refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}
```

---

## Shared Patterns

### Script docstring contract (Usage / Behavior / Exit codes)
**Source:** `cairn/scripts/cairn-map.py` lines 1-42, `cairn/scripts/cairn-gate.py` lines 1-46
**Apply to:** `benchmarks/scripts/bench-run.py`
Every deterministic script's module docstring documents what it does, a `Usage:` line, numbered `Behavior:` steps, and a numbered `Exit codes:` list — treat the docstring as the spec, write it first.

### `die(msg, code)` helper
**Source:** `cairn/scripts/gbsync.py` lines 51-53
**Apply to:** `benchmarks/scripts/bench-run.py`
```python
def die(msg, code):
    print(f"[bench-run] error: {msg}", file=sys.stderr)
    sys.exit(code)
```

### `.sh` / `.py` wrapper pairing
**Source:** `.planning/codebase/CONVENTIONS.md` lines 127-147, `cairn/scripts/cairn-map.sh` (full file)
**Apply to:** `benchmarks/scripts/bench-run.sh` + `benchmarks/scripts/bench-run.py`
Every deterministic Python script ships with a thin bash wrapper of the identical basename that `exec`s into `python3 "$HERE/<name>.py" "$@"`, header comment restating the exit-code contract.

### `CAIRN_`-prefixed env-var seam, default to real binary
**Source:** `cairn/hooks/post-bd-write.sh` lines 32-33, `.planning/codebase/CONVENTIONS.md` lines 64-66
**Apply to:** `benchmarks/scripts/bench-run.py` (resolves `claude` via `CAIRN_BENCH_CLAUDE_BIN`)
```bash
GBSYNC="${CAIRN_GBSYNC:-$PLUGIN_ROOT/scripts/gbsync.sh}"
```
```python
CLAUDE_BIN = os.environ.get("CAIRN_BENCH_CLAUDE_BIN") or shutil.which("claude") or "claude"
```

### Subprocess invocation: argv list, never shell string
**Source:** `cairn/scripts/gbsync.py` lines 88-97, 136-147; `.planning/codebase/CONVENTIONS.md` lines 114-118
**Apply to:** `benchmarks/scripts/bench-run.py`
`subprocess.run([...], capture_output=True, text=True)` with an argv list, never `shell=True` with interpolated strings (also the ASVS V5 control called out in RESEARCH.md's Security Domain section).

### Bats CLI-contract testing, black-box only
**Source:** `tests/README.md`, `.planning/codebase/TESTING.md` lines 88-107
**Apply to:** `tests/bench-run.bats`
Tests invoke the real script binary (`bash bench-run.sh` / `python3 bench-run.py`) against a throwaway fixture and assert on exit code, stdout, and the written JSONL file — never source the script or call an inner function directly.

### Recorder / canned-output stub via env-var seam
**Source:** `tests/hooks.bats` lines 22-32, `.planning/codebase/TESTING.md` lines 185-210
**Apply to:** `tests/bench-run.bats`
A tiny executable stub, wired in via `CAIRN_BENCH_CLAUDE_BIN`, that emits fixed output (here: a canned JSON blob, not just a log line) so the harness's deterministic logic is tested with zero API cost.

### Assertion-style gotcha
**Source:** `.planning/codebase/TESTING.md` lines 150-177
**Apply to:** `tests/bench-run.bats`
`grep -qF` for positive substring checks, a locally-redefined `refute_in_output` for negative ones — never `[[ ... == *...* ]]` or bare `! cmd` mid-test.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `benchmarks/tasks/smoke-convert/prompt.md` | fixture content | static data | Plain prose task instructions — no code pattern applies; write directly from RESEARCH.md's recommended text ("Implement `celsius_to_fahrenheit(c)` in `convert.py` so the tests pass."). |
| `benchmarks/tasks/smoke-convert/fixture/convert.py` + `fixture/tests/test_convert.py` | fixture / test data | static data | Repo has no pytest-tested application code to mirror (cairn's own scripts are bats-tested, not pytest-tested) — build directly from RESEARCH.md's Pattern 1 recipe (one missing function, one currently-failing test). |
| `benchmarks/results/` (`.gitkeep` + first committed JSONL row) | output artifact | batch/append | New artifact category with no existing analog; shape is fully specified by RESEARCH.md's "Verified JSON Result Schema" section plus `bench-run.py`'s own row-writing code. |

## Conventions

Convention derivation (`node bin/gsd-tools.cjs verify conventions --derive`) was run against this repo (both scoped to `cairn/scripts/` and repo-wide) and returned `{"skipped": true, "reason": "no-readable-files"}` both times — the deterministic derivation tool targets JS/TS axes (file-name casing, identifier casing, export style, import style) and this repo has no JS/TS source files (it is Python + bash + Markdown only, confirmed by `.planning/codebase/CONVENTIONS.md` line 8: "There is no JS/TS/frontend code"). Convention derivation skipped (no applicable JS/TS files in this repo).

In its place, the repo's own committed `.planning/codebase/CONVENTIONS.md` is the authoritative, human-derived convention source for this phase (read in full above) — its equivalent axes for a Python/bash codebase:

| Axis | Dominant | Share | Status |
|------|----------|-------|--------|
| Script file naming | kebab-case, `cairn-` prefix (`.py`/`.sh` pair); one named exception `gbsync.py`/`.sh` | ~90% (9/10 scripts follow `cairn-*`, 1 named-after-role exception) | named contract |
| Python identifier casing | `snake_case` functions/vars, `UPPER_CASE` module constants (`EXIT_*`, compiled regexes) | 100% (no deviation found across 5 scripts read) | named contract |
| Bash variable casing | `UPPER_CASE` for script-scoped constants, lowercase for transient loop/local values | 100% | named contract |
| Env-var seam naming | `UPPER_CASE`, `CAIRN_` prefix (`CAIRN_GBSYNC`, `CAIRN_MAP`) | 100% (2/2 existing seams) | named contract |
| Test file naming | `<script-basename>.bats`, flat `tests/` dir | 100% (10/10 existing `.bats` files) | named contract |

**Contested hotspots (author's choice):** None found specific to this phase's file set — every axis above is a clean, unanimous house convention (no JS/TS dual-resolver split applies here, since this repo carries no `bin/lib/**`-CJS-vs-`sdk/src/**`-ESM split; that pattern is specific to the `gsd-plugin` tooling repo itself, not to CairnGo). If a future phase introduces genuinely divergent style pockets (e.g. a vendored third-party script), match that pocket's own local convention rather than the table above, per the standing "match the directory's local style" rule.

## Metadata

**Analog search scope:** `cairn/scripts/`, `cairn/hooks/`, `tests/`, `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/TESTING.md`
**Files scanned:** `cairn-map.py`, `cairn-map.sh`, `cairn-gate.py`, `gbsync.py`, `gbsync.sh` (read), `post-bd-write.sh`, `tests/helpers.bash`, `tests/hooks.bats`, `tests/cairn-map.bats`, `tests/gbsync.bats`, `tests/README.md` (all read in full)
**Pattern extraction date:** 2026-07-25
