# Phase 2: Baseline Isolation + Multi-Baseline Harness - Pattern Map

**Mapped:** 2026-07-25
**Files analyzed:** 8 (new/modified)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `benchmarks/scripts/bench-run.py` (modify: `env=`, `--plugin-dir`, `--baseline`) | service/runner (subprocess orchestration) | request-response (subprocess invoke → parse → append) | itself (`benchmarks/scripts/bench-run.py`, current state) | exact — extending, not replacing |
| `benchmarks/baselines/vanilla.json` | config (manifest) | CRUD (static, read-only) | `cairn/.cairn/sync.json`-shaped config consumed by `cairn/scripts/gbsync.py` (`enabled_backends`, `load_json`) — no committed example on disk, but the *consumption* pattern is concrete | role-match |
| `benchmarks/baselines/gsd-only.json` | config (manifest) | CRUD | same as above | role-match |
| `benchmarks/baselines/cairn.json` | config (manifest) | CRUD | same as above | role-match |
| `benchmarks/scripts/bench-matrix.py` (or `bench-run.py --baselines/--seed` mode) | service/orchestrator (thin loop over runner) | batch (seeded shuffle → N sequential invocations) | `cairn/scripts/cairn-relabel.py` (`do_pair`/`do_renumber`: build candidate list → iterate → one line of output per item → final count) | role-match |
| `benchmarks/scripts/bench-run.py` — plugin provisioning resolution (staged path lookup, `--plugin-dir` flag construction) | utility (config → CLI-flag translation) | transform | `cairn/scripts/gbsync.py` `resolve_adapter()` (name → filesystem path resolution, tries candidates, returns `None` on miss) | role-match |
| `tests/bench-run.bats` (extend: isolation assertions, baseline manifest tests, order/seed tests) | test | request-response (stub-in, JSONL-out, jq assertions) | itself (`tests/bench-run.bats`, current state) + `tests/helpers.bash` (`assert_json_eq`) | exact — extending, not replacing |
| stub upgrades — `CAIRN_BENCH_CLAUDE_BIN` stub prints `$HOME`/env markers into canned JSON | test fixture / stub | event-driven (stub observes its own launch env, emits it as data) | `tests/bench-run.bats` `make_claude_stub()` (lines 33-44) | exact — extending the existing stub helper |

## Pattern Assignments

### `benchmarks/scripts/bench-run.py` — env isolation + `--plugin-dir` + `--baseline` (service/runner, request-response)

**Analog:** itself, current committed state (`benchmarks/scripts/bench-run.py:1-153`)

This file is being extended, not replaced — the existing structure (`die`, `resolve_claude_bin`, `parse_args`, `main`) is the pattern to continue, not a different file to imitate.

**Imports pattern** (lines 32-39, unchanged, stdlib-only house style):
```python
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
```
No new imports needed for `env=` isolation (all stdlib already present). `random` and `itertools.product` are the only additions needed for the seeded-interleaving piece (Pattern 3 below), both stdlib.

**Binary/tool resolution pattern to copy for baseline-manifest resolution** (lines 52-53):
```python
def resolve_claude_bin():
    return os.environ.get("CAIRN_BENCH_CLAUDE_BIN") or shutil.which("claude") or "claude"
```
Follow this exact shape for any new "resolve X, env override first" helper (e.g. resolving a baseline manifest path or a staged plugin dir) — env var seam first, sane default fallback second, never hard-fail at resolution time.

**Argv parsing pattern to extend for `--baseline`** (lines 56-75):
```python
def parse_args(argv):
    opts = {"task": None, "out": None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--task":
            if i + 1 >= len(argv):
                die(f"--task needs a value\n{USAGE}", EXIT_USAGE)
            opts["task"] = argv[i + 1]
            i += 2
        elif arg == "--out":
            ...
        else:
            die(f"unknown option '{arg}'\n{USAGE}", EXIT_USAGE)
    if opts["task"] is None or opts["out"] is None:
        die(f"--task and --out are both required\n{USAGE}", EXIT_USAGE)
    return opts
```
Add `--baseline` as a third required-or-optional (Claude's Discretion: required, since CONTEXT.md locks "same task/prompt/fixture, only provisioning differs" — a baseline-less run has no defined isolation behavior) key using the identical `if arg == "--x": ... i += 2` branch shape — no argparse, matches the repo's zero-dependency stdlib-only style already visible in `bench-run.py` (hand-rolled) vs `cairn-relabel.py` (uses `argparse` — see Shared Patterns note below on which to pick).

**Core pattern — the exact call site the isolation fix targets** (lines 120-123, THE bug this phase exists to fix per RESEARCH.md's own Anti-Patterns section):
```python
start = time.time()
try:
    proc = subprocess.run(cmd, cwd=workdir, capture_output=True,
                          text=True, timeout=task["timeout_s"])
```
`env=` is absent → full operator environment inherited. RESEARCH.md Pattern 1 (verified) is the exact replacement:
```python
def isolated_claude_env(fresh_home: str) -> dict:
    env = {"HOME": fresh_home, "PATH": os.environ.get("PATH", "")}
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    return env

proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                       timeout=task["timeout_s"], env=isolated_claude_env(fresh_home))
```
Critical: this `env=` must be added ONLY to the `claude` subprocess call (line 122), never to the `verify.sh` call (line 141) — see Common Pitfall 5 in RESEARCH.md and the Shared Pattern note below.

**cmd-list construction pattern to extend with `--plugin-dir`/`--bare` flags** (lines 114-119):
```python
cmd = [resolve_claude_bin(), "-p", prompt_text,
       "--output-format", "json",
       "--max-turns", str(task["max_turns"]),
       "--model", task["model"],
       "--permission-mode", "acceptEdits",
       "--no-session-persistence"]
```
Append baseline-driven flags the same way — a flat Python list, one `--plugin-dir <staged_path>` pair per provisioning entry, `cmd += ["--plugin-dir", staged_path]` per plugin, `cmd.append("--bare")` when the baseline manifest says so. Never string-interpolate into a shell string (`shell=True` is never used anywhere in this codebase — preserve that).

**Error/timeout handling pattern (unchanged, extend the `payload` dict shape)** (lines 121-140):
```python
except subprocess.TimeoutExpired:
    wall_ms = int((time.time() - start) * 1000)
    payload = {"is_error": True,
               "parse_error": f"timeout after {task['timeout_s']}s"}
except FileNotFoundError as e:
    wall_ms = int((time.time() - start) * 1000)
    payload = {"is_error": True,
               "parse_error": f"claude binary not found: {e}"}
else:
    wall_ms = int((time.time() - start) * 1000)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        payload = {"is_error": True, "parse_error": str(e),
                   "raw_stdout": proc.stdout[:2000]}
```
Add a new failure mode here for provisioning/staging failures (e.g. a `--plugin-dir` path that doesn't exist) — same `{"is_error": True, "parse_error": "..."}` synthesized-payload shape, so a bad manifest still produces one valid JSONL row rather than crashing the whole batch.

**Row-assembly pattern to extend with `seed`/`run_order_index`/`baseline_id`** (lines 143-146):
```python
row = {"task_id": task["id"], "wall_clock_ms": wall_ms, **payload,
       "verify_passed": verify_proc.returncode == 0}
with open(out_path, "a") as f:
    f.write(json.dumps(row, sort_keys=True) + "\n")
```
Add `"baseline_id": baseline["name"]` (and, when invoked from the interleaving loop, `"seed"`/`"run_order_index"`) as additional dict-literal keys merged the same way `**payload` is spread today — `sort_keys=True` must be preserved (it is what makes the "byte-identical JSONL" bats test in `tests/bench-run.bats:90-105` possible).

**Validate-before-spend pattern (already established house style, replicate for baseline manifest validation)** (lines 96-100, 112-113):
```python
out_parent = Path(out_path).parent
if not out_parent.is_dir():
    die(f"output directory not found: {out_parent} (create it first)", EXIT_USAGE)
...
if "model" not in task:
    die("task.json missing required 'model' (full pinned model id)", EXIT_USAGE)
```
Apply the identical shape to baseline-manifest loading: parse the JSON, validate required keys (`name`, `model`, `claude_flags`, `provisioning.plugin_dirs`) BEFORE `tempfile.mkdtemp`/before any subprocess spend — this is a documented, deliberate house convention (comment at line 96-97 explains why), not incidental.

---

### `benchmarks/baselines/{vanilla,gsd-only,cairn}.json` (config/manifest, CRUD)

**Analog for consumption shape:** `cairn/scripts/gbsync.py` — `enabled_backends()` (line 150-151) and `load_json()` (lines 74-81), which show this repo's established "read a small JSON config, treat missing file as a hard `die()`, iterate a list of typed dict entries" idiom:
```python
def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e}")

def enabled_backends(cfg):
    return [b for b in cfg.get("backends", []) if b.get("enabled")]
```
Baseline manifests should be loaded with the same `json.loads(Path(path).read_text())` + explicit `json.JSONDecodeError` → `die()` shape already used in `bench-run.py` for `task.json` (lines 87-90) — do not introduce a different JSON-loading idiom for baseline manifests than the one `task.json` already uses in the same file.

**Manifest schema (from RESEARCH.md Code Examples, already vetted against this repo's conventions — use verbatim as the starting shape):**
```json
{
  "name": "vanilla",
  "description": "Stock Claude Code, no plugins, no ambient config.",
  "model": "claude-haiku-4-5-20251001",
  "claude_flags": {
    "bare": true,
    "max_turns": 8,
    "no_session_persistence": true,
    "permission_mode": "acceptEdits"
  },
  "provisioning": {
    "plugin_dirs": []
  }
}
```
`gsd-only.json`/`cairn.json` add typed `provisioning.plugin_dirs[]` entries (`plugin`, `source.{type,repo,ref}` or `source.{type,path}`, `staged_path`, `build`) — see RESEARCH.md lines 357-411 for the two fully-worked examples. Field-naming convention to match: `snake_case` keys throughout (matches `task.json`'s `timeout_s`/`max_turns`/`prompt_file`, and `.cairn/sync.json`'s `backends`/`adapter`/`config` shape in `gbsync.py`).

---

### `benchmarks/scripts/bench-matrix.py` (or `bench-run.py --baselines/--seed` mode) — orchestrator (batch)

**Analog:** `cairn/scripts/cairn-relabel.py` `do_pair()`/`do_renumber()` (lines 116-190) — the closest existing "build a candidate list, iterate it, one line of output per item, final summary count" pattern in this codebase, directly transferable to "build the shuffled (baseline × rep) order, iterate it, invoke `bench-run.py` once per item, one JSONL row per item":

**Core iteration + reporting pattern** (lines 116-145, `do_pair`):
```python
def do_pair(args):
    candidates = []
    for issue in list_issues(args.dir):
        phases = phase_labels(issue)
        if not phases or has_milestone_label(issue):
            continue
        ...
        candidates.append(issue)

    label = f"m-{args.milestone}"
    change = f"+{label} gsd.milestone={args.milestone}"
    if args.dry_run:
        for issue in candidates:
            print(f"DRY-RUN: {issue['id']} {change}")
        return 0

    failed = 0
    for issue in candidates:
        bd_id = issue["id"]
        _, err = run_bd(["label", "add", bd_id, label], args.dir)
        ...
        if err:
            failed += 1
            print(f"[cairn-relabel] FAIL {bd_id}: {err}", file=sys.stderr)
            continue
        print(f"{bd_id} {change}")
    print(f"[cairn-relabel] pair: {len(candidates) - failed} issue(s) updated")
    return 1 if failed else 0
```
Map directly onto the seeded-interleaving loop: `candidates` → `build_execution_order(baselines, reps, seed)` (RESEARCH.md Pattern 3, lines 219-231); the per-item `for` loop → one `bench-run.py --baseline ... --rep ...` subprocess invocation per `(baseline, rep)` tuple; the `failed`-counter + final summary line → the same shape, reporting how many of the N ordered runs completed vs. errored (distinct from `verify_passed`, which stays a per-row data column per Phase 1's established `is_error ⊥ verify_passed` invariant — do not conflate "runner failed to execute" with "task not solved").

**argparse subcommand-with-shared-flags pattern** (lines 193-227, `main()`), reusable if the orchestrator is a separate script rather than a `bench-run.py` mode:
```python
def main():
    parser = argparse.ArgumentParser(prog="cairn-relabel", description="...")
    sub = parser.add_subparsers(dest="command", required=True)
    pair = sub.add_parser("pair", help="...")
    pair.add_argument("--milestone", required=True, metavar="M", help="...")
    ...
    for p in (pair, ren):
        p.add_argument("--dry-run", action="store_true", help="...")
        p.add_argument("--dir", metavar="DIR", help="...")
    args = parser.parse_args()
    sys.exit(args.func(args))
```
Note the codebase has TWO argv-parsing idioms in active use: `bench-run.py`'s hand-rolled `while i < len(argv)` loop (Phase 1, zero deps) and `cairn-relabel.py`'s `argparse` (also stdlib, but a different sub-style). Since the orchestrator introduces genuinely new flags (`--baselines`, `--seed`, `--reps`) not shared with `bench-run.py`'s existing `--task`/`--out` contract, `argparse` is the better fit if it becomes its OWN script (`bench-matrix.py`) — but if it becomes a `bench-run.py` mode instead, extend the existing hand-rolled loop for consistency within that one file. This exact fork (new script vs. new flag) is explicitly flagged as Claude's Discretion in `02-CONTEXT.md`; ARCHITECTURE.md's Recommended Project Structure (line 173) leans toward a **new sibling script**, `bench-matrix.py`.

**Seeded shuffle mechanic (from RESEARCH.md, stdlib-only, drop-in):**
```python
import random
from itertools import product

def build_execution_order(baselines: list[str], reps: int, seed: int) -> list[tuple[str, int]]:
    order = list(product(baselines, range(reps)))
    random.Random(seed).shuffle(order)
    return order
```
Instance-scoped `random.Random(seed)`, never the shared `random` module — matches this codebase's existing discipline of not touching shared/global mutable state casually (see `gbsync.py`'s per-call `now_iso()`/`EPOCH` constant-not-global-mutation pattern).

---

### Plugin-dir resolution helper (utility, transform: manifest entry → `--plugin-dir` CLI flag)

**Analog:** `cairn/scripts/gbsync.py` `resolve_adapter()` (lines 128-133):
```python
def resolve_adapter(name):
    for cand in (name, f"{name}.py", f"{name}.sh"):
        p = ADAPTERS_DIR / cand
        if p.exists():
            return p
    return None
```
This is the exact shape for "given a declared name in a manifest, resolve it to a concrete filesystem path, trying known candidate forms, returning `None`/failing cleanly on miss" — apply it to resolving a `provisioning.plugin_dirs[].staged_path` entry to a real, pre-built directory before constructing the `--plugin-dir` flag. Callers of `resolve_adapter()` (lines 168-181, 219-225) show the follow-up idiom: check for `None`, emit a clear skip/fail message including the attempted name, never silently continue. Apply the same to a missing/unbuilt staged plugin dir — this is exactly Pitfall 4 in RESEARCH.md (lazy `npm install`): fail loudly and BEFORE spend if `staged_path` doesn't exist or lacks `node_modules`, do not attempt to build it inline.

---

### `tests/bench-run.bats` — isolation + baseline manifest + order/seed assertions (test, request-response)

**Analog:** itself, current committed state (`tests/bench-run.bats:1-105`) + `tests/helpers.bash` (`assert_json_eq`, lines 343-351).

**Stub-factory pattern to extend** (lines 33-44):
```bash
make_claude_stub() {
  local name="$1" json_body="$2" exit_code="$3"
  STUB="$BATS_TEST_TMPDIR/$name"
  {
    printf '#!/usr/bin/env bash\n'
    printf "cat <<'JSON'\n"
    printf '%s\n' "$json_body"
    printf 'JSON\n'
    printf 'exit %s\n' "$exit_code"
  } > "$STUB"
  chmod +x "$STUB"
}
```
RESEARCH.md's Pattern 4 (lines 240-262) is the direct extension of this exact helper — swap the static `cat <<'JSON' ... JSON` body for a `python3 -c "..."` one-liner that reads `os.environ.get('HOME', '')` and a planted leak-marker var and folds them into the emitted JSON as `stub_observed_home`/`stub_observed_leak_marker`/`stub_observed_api_key_present` keys. Add this as a SECOND stub factory (`make_env_asserting_claude_stub`) alongside the existing `make_claude_stub`, in either `tests/helpers.bash` (if reused across multiple `.bats` files) or locally in `tests/bench-run.bats` (if scoped to this one file) — `tests/helpers.bash`'s own header comment (lines 1-16) documents "Fixture builders defined here" as the place for cross-file reusable ones.

**Assertion pattern to reuse verbatim** (`tests/helpers.bash:343-351`):
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
Use for every new field assertion (`stub_observed_home`, `baseline_id`, `seed`, `run_order_index`) — do not hand-roll a new jq-comparison idiom.

**Test-body pattern to copy for the new isolation test** (lines 46-65, adapted per RESEARCH.md lines 264-279):
```bash
@test "bench-run.py builds a scoped HOME and scrubs unrelated operator env vars" {
  make_env_asserting_claude_stub
  export OPERATOR_ONLY_LEAK_MARKER="this-must-not-reach-the-claude-subprocess"
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-run.py" \
      --task "$BENCH_TASKS_DIR/smoke-convert" --baseline "$BENCH_BASELINES_DIR/vanilla.json" \
      --out "$BATS_TEST_TMPDIR/raw.jsonl"
  [ "$status" -eq 0 ]
  row="$(cat "$BATS_TEST_TMPDIR/raw.jsonl")"
  observed_home="$(echo "$row" | jq -r '.stub_observed_home')"
  [ "$observed_home" != "$HOME" ]
  assert_json_eq "$row" '.stub_observed_leak_marker' ''
}
```
Note the file-header comment (`tests/bench-run.bats:7-9`) documents a real house convention worth preserving: *"a failing `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this bash, so positive substring checks use `grep -qF` and negative checks use `refute_in_output`"* — apply the same discipline to any new negative assertion (e.g. asserting a leak marker is ABSENT), preferring `assert_json_eq "$row" '.field' ''` (works because `jq -r` on empty/absent renders `null`/empty predictably) over a bare `[[ ! ... ]]`.

**Directory-constant pattern to extend** (lines 13-14):
```bash
BENCH_SCRIPTS_DIR="$CAIRN_REPO_ROOT/benchmarks/scripts"
BENCH_TASKS_DIR="$CAIRN_REPO_ROOT/benchmarks/tasks"
```
Add `BENCH_BASELINES_DIR="$CAIRN_REPO_ROOT/benchmarks/baselines"` alongside these two, same declaration style, at the top of the file.

---

## Shared Patterns

### Isolation boundary: minimal explicit `env=` for the arm under test ONLY
**Source:** RESEARCH.md Architecture Patterns Pattern 1 + Anti-Patterns (verified live against installed `claude` v2.1.220)
**Apply to:** `bench-run.py`'s `claude` subprocess call (line 122) exclusively.
**Do NOT apply to:** the `verify.sh` subprocess call (line 141) — it must keep `env=None` (full inherited environment), per RESEARCH.md Common Pitfall 5. Any plan/test that adds `env=` to BOTH call sites is wrong and will break `verify.sh`'s ability to shell out to `pytest`/`bats`.
```python
def isolated_claude_env(fresh_home: str) -> dict:
    env = {"HOME": fresh_home, "PATH": os.environ.get("PATH", "")}
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    return env
```

### JSON manifest loading: parse → validate-required-keys → `die()` on failure, always BEFORE spend
**Source:** `benchmarks/scripts/bench-run.py:87-90` (task.json) and `96-100`/`112-113` (validate-before-spend), `cairn/scripts/gbsync.py:74-81` (`load_json`)
**Apply to:** Baseline manifest loading (new), plugin-provisioning staged-path validation (new). This ordering is a load-bearing, previously-proven-costly convention: `benchmarks/README.md` lines 48-54 document a real ~$1.30 loss from a validation-order bug in Phase 1 (missing output dir discovered only after a live API call) — the fix pattern (validate first) is already in the file at lines 96-100 and must be extended, not bypassed, for every new manifest-driven input this phase adds.

### `cmd` as a Python list, never `shell=True`
**Source:** `benchmarks/scripts/bench-run.py:114-119`, `cairn/scripts/gbsync.py:143` (`subprocess.run(cmd, input=..., ...)`), `cairn/scripts/cairn-relabel.py:49-56` (`run_bd`)
**Apply to:** Every new `--plugin-dir`/`--bare` flag appended to the `claude` invocation's `cmd` list. RESEARCH.md's Security Domain (V5 Input Validation) explicitly calls this out as a must-preserve convention for baseline-manifest-driven flags.

### One JSONL row per unit of work, `sort_keys=True`, append-only
**Source:** `benchmarks/scripts/bench-run.py:143-146`
**Apply to:** Every new field this phase adds to a row (`baseline_id`, `seed`, `run_order_index`, `stub_observed_*` in test-only stub payloads) — merge into the existing dict-literal/`**payload`-spread shape, keep `sort_keys=True` (required for the byte-identical-JSONL bats test at `tests/bench-run.bats:90-105` to keep passing), keep the `open(out_path, "a")` append-only write.

## No Analog Found

None — every file this phase touches or creates has at least a role-match analog already in the codebase. The closest thing to a gap is that no committed `benchmarks/baselines/*.json` example exists yet (they are new in this phase), but their *consumption* pattern (small JSON config, `snake_case` keys, list-of-typed-dict-entries) is already well-established by `task.json` + `cairn/.cairn/sync.json`'s consumer `gbsync.py`, so this is not treated as a true gap.

## Conventions

Convention derivation (`gsd-tools.cjs verify conventions --derive`) is the shared deterministic module used by both `gsd-pattern-mapper` and `gsd-code-reviewer`. It was run scoped to `benchmarks/` (this phase's new-file directory) and again repo-wide as a sanity check.

**Result: convention derivation skipped (no-readable-files).** The derivation tool's corpus walker (`collectConventionCorpus` in `bin/lib/verify.cjs`) only collects `.js`/`.mjs`/`.cjs`/`.jsx`/`.ts`/`.mts`/`.tsx` files — it is JS/TS-scoped by design (per its own header comment: "Idiom checks ... are JS/TS rule packs"). Phase 2's new/modified files are exclusively Python (`bench-run.py`, `bench-matrix.py`), JSON (`benchmarks/baselines/*.json`), and Bash/bats (`tests/bench-run.bats`) — zero JS/TS files in scope, so the 4-axis casing/export/import table has no corpus to derive from in this phase.

In place of the automated table, the **manually-observed conventions already established by the analogs above** (and which this phase's new files must match) are:

| Axis | Observed convention | Evidence |
|------|---------------------|----------|
| File naming | `kebab-case.py` for scripts (`bench-run.py`, `cairn-relabel.py`), `snake_case.json`/`kebab-case.json` mixed for data files (`task.json`, would-be `gsd-only.json`) | `benchmarks/scripts/`, `cairn/scripts/` |
| JSON key naming | `snake_case` throughout every manifest/config (`timeout_s`, `max_turns`, `prompt_file`, `total_cost_usd`, `bd_id`, `external_id`) | `task.json`, `gbsync.py`'s `sync.json` schema, `bench-run.py`'s row shape |
| Python function naming | `snake_case`, verb-first (`resolve_claude_bin`, `parse_args`, `load_json`, `run_adapter`, `do_push`, `do_pull`) | `bench-run.py`, `gbsync.py`, `cairn-relabel.py` |
| Error handling | A local `die(msg, code)` helper (`print(..., file=sys.stderr); sys.exit(code)`), never a raised-and-uncaught exception, present independently in all three analog scripts | `bench-run.py:47-49`, `gbsync.py:51-53`, `cairn-relabel.py:44-46` |
| Subprocess invocation | Always a Python list `cmd`, never `shell=True`; `capture_output=True, text=True` | all three analog scripts |
| Module docstring | A long triple-quoted module-level docstring documenting usage, behavior (numbered steps), and exit codes, at the very top of every script | `bench-run.py:1-31`, `gbsync.py:1-37`, `cairn-relabel.py:1-34` |

**Contested hotspots (author's choice):** this repo's one documented intentional-contested split is the **CJS↔SDK dual resolver** inside the GSD plugin itself (`bin/lib/**` is CJS `module.exports`/`require`; `sdk/src/**` is ESM `export`/`import`) — each half is internally consistent per-directory and the split is contested only repo-wide, never within either directory. Phase 2's new files do not touch that boundary (they are Python/JSON/bash, not JS/TS at all), but the same principle applies locally: match whichever directory's local style you are extending (`benchmarks/scripts/`'s hand-rolled-argv-loop style in `bench-run.py` vs. `cairn/scripts/`'s `argparse` style in `cairn-relabel.py` are two valid, directory-local idioms — see the orchestrator's Pattern Assignment above for how this phase resolves that specific fork).

## Metadata

**Analog search scope:** `benchmarks/`, `cairn/scripts/`, `tests/`, `.planning/research/ARCHITECTURE.md`, `.claude-plugin/marketplace.json`, `cairn/.claude-plugin/plugin.json`
**Files scanned:** `benchmarks/scripts/bench-run.py`, `benchmarks/scripts/bench-run.sh`, `benchmarks/tasks/smoke-convert/{task.json,verify.sh}`, `benchmarks/README.md`, `tests/bench-run.bats`, `tests/helpers.bash`, `cairn/scripts/gbsync.py`, `cairn/scripts/cairn-relabel.py`, `.claude-plugin/marketplace.json`, `cairn/.claude-plugin/plugin.json`, `.planning/research/ARCHITECTURE.md` (component-split table)
**Pattern extraction date:** 2026-07-25
