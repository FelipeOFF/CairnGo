# Phase 3: Repetition, Aggregation & Cost Decomposition - Pattern Map

**Mapped:** 2026-07-26
**Files analyzed:** 6 (2 extended, 4 new/new-group)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `benchmarks/scripts/bench-matrix.py` (extend: `--reps`, cell builder) | orchestrator / CLI | batch / event-driven (subprocess fan-out) | itself (extend in place) | exact |
| `benchmarks/scripts/bench-run.py` (extend: `--rep-index`, row stamp) | runner / CLI | request-response (one subprocess call) | itself (extend in place) | exact |
| `benchmarks/scripts/bench-aggregate.py` (new) | aggregator / batch transform | file-I/O, batch (JSONL → JSON) | `cairn/scripts/cairn-map.py` (deterministic generated-output CLI) + `benchmarks/scripts/stage-plugins.py` (sorted multi-file collection) | role-match (strong) |
| `benchmarks/scripts/bench-aggregate.sh` (new) | CLI wrapper | passthrough | `benchmarks/scripts/bench-run.sh` | exact |
| `tests/bench-aggregate.bats` (new) | test | file-I/O / determinism | `tests/bench-run.bats` (byte-identical double-run test) + `tests/gbsync.bats` (dry-run/no-side-effect assertions) | role-match (strong) |
| Fixture JSONL files (new, under `tests/fixtures/` or `$BATS_TEST_TMPDIR`) | fixture / test data | file-I/O | `tests/helpers.bash`'s `make_fixture_baselines`/`make_env_asserting_claude_stub` (heredoc-authored fixtures) + `benchmarks/results/smoke-convert.jsonl` (real rows, rejection-path fixture) | exact |
| `tests/bench-matrix.bats` (updates for `--reps`) | test | batch | itself (extend in place) | exact |

## Pattern Assignments

### `benchmarks/scripts/bench-matrix.py` (orchestrator, extend for `--reps`)

**Analog:** itself — `benchmarks/scripts/bench-matrix.py` (read in full this session)

**Imports pattern** (lines 31-35):
```python
import argparse
import random
import subprocess
import sys
from pathlib import Path
```
Add `itertools` for the cross-product cell builder (stdlib, matches the "no new dependency" constraint).

**argparse flag pattern** (lines 60-82) — `--reps` should mirror `--seed`'s shape exactly (required-with-explicit-int-type via argparse's own `type=int`, not manual parsing — bench-matrix.py already uses argparse, unlike bench-run.py's manual loop):
```python
parser.add_argument("--seed", required=True, type=int, metavar="N",
                    help="shuffle seed — required, no silent random "
                         "default: reproducibility of the execution "
                         "order is the point")
```
CONTEXT.md locks `--reps` default N=5 (not required-no-default like `--seed`) — use `argparse.add_argument("--reps", type=int, default=5, metavar="N", ...)`. Per RESEARCH.md Pitfall 7, existing `tests/bench-matrix.bats` invocations (which assert 3-row output for 3 baselines, implicit reps=1) must gain an explicit `--reps 1` — do not rely on the new default silently.

**Core cell-builder pattern to extend** (lines 48-56, `build_execution_order`):
```python
def build_execution_order(baselines, seed):
    """Deterministic seeded shuffle of the declared baseline names.

    Instance-scoped RNG (random.Random(seed)), never the shared random
    module: two calls with the same inputs always return the same order.
    """
    order = list(baselines)
    random.Random(seed).shuffle(order)
    return order
```
Extend (don't redesign — RESEARCH.md Pattern 1) to a `(name, rep_idx)` cross-product, same instance-scoped RNG:
```python
def build_execution_order(baselines, reps, seed):
    cells = list(itertools.product(baselines, range(reps)))
    random.Random(seed).shuffle(cells)
    return cells
```

**Validate-before-spend pattern** (lines 90-97) — stays a per-*name* check, unchanged; re-checking `manifest_path.is_file()` once per rep is cheap idempotent local IO, not worth deduping (RESEARCH.md Pattern 1 note).

**Subprocess invocation + provenance stamping loop** (lines 99-113) — extend the existing per-cell loop to pass `--rep-index` alongside the existing `--seed`/`--run-order-index`:
```python
for idx, (name, manifest_path) in enumerate(resolved):
    cmd = [sys.executable, str(BENCH_RUN_PY),
           "--task", args.task,
           "--out", args.out,
           "--baseline", str(manifest_path),
           "--seed", str(args.seed),
           "--run-order-index", str(idx)]
    subprocess.run(cmd)  # no check=True: exit code is data, not a batch abort
```

**Error handling pattern** (lines 43-45, `die`):
```python
def die(msg, code):
    print(f"[bench-matrix] error: {msg}", file=sys.stderr)
    sys.exit(code)
```
Keep the `[bench-matrix] error: ` prefix convention — every script in this repo (`bench-run.py`, `cairn-map.py`, `gbsync.py`, `stage-plugins.py`) uses `[<script-name>] error: <msg>` to stderr + `sys.exit(code)`, never a raised exception that reaches the user.

---

### `benchmarks/scripts/bench-run.py` (runner, extend for `--rep-index`)

**Analog:** itself — `benchmarks/scripts/bench-run.py` (read in full this session)

**Manual arg-parsing pattern to mirror exactly** (lines 137-154, the `--run-order-index` block — RESEARCH.md Pattern 2 confirms `--rep-index` should copy this shape verbatim):
```python
elif arg == "--run-order-index":
    if i + 1 >= len(argv):
        die(f"--run-order-index needs a value\n{USAGE}", EXIT_USAGE)
    try:
        opts["run_order_index"] = int(argv[i + 1])
    except ValueError:
        die("--run-order-index must be an integer, "
            f"got '{argv[i + 1]}'", EXIT_USAGE)
    i += 2
```
Add `opts["rep_index"] = None` to the initial `opts` dict (line 117-118) alongside `seed`/`run_order_index`, and a matching `elif arg == "--rep-index":` branch.

**Conditional row-stamping pattern** (lines 241-246) — only present when provided, so standalone invocations keep the existing schema:
```python
if opts["seed"] is not None:
    row["seed"] = opts["seed"]
if opts["run_order_index"] is not None:
    row["run_order_index"] = opts["run_order_index"]
```
Add `if opts["rep_index"] is not None: row["rep_index"] = opts["rep_index"]` in the same block.

**Row-write / determinism pattern** (line 247-248):
```python
with open(out_path, "a") as f:
    f.write(json.dumps(row, sort_keys=True) + "\n")
```
`sort_keys=True` is already the house convention for every JSONL row written by this repo — bench-aggregate.py's own output must follow the same `sort_keys=True` discipline (see below).

---

### `benchmarks/scripts/bench-aggregate.py` (new)

**Analog 1 (CLI shape, deterministic generated output, `--check`/`--json` conventions):** `cairn/scripts/cairn-map.py`

**Imports pattern** (lines 43-50):
```python
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
```
bench-aggregate.py's own import block: `json`, `statistics`, `sys`, `itertools` or `collections.defaultdict`, `pathlib.Path`, `argparse` — no new external dependency (RESEARCH.md, "no new packages this phase").

**`die()` pattern** (lines 68-70):
```python
def die(msg, code):
    print(f"[cairn-map] error: {msg}", file=sys.stderr)
    sys.exit(code)
```
Use `[bench-aggregate] error: <msg>` with the same shape; reserve this for usage errors only (bad args, unreadable path) — required-field row rejection is NOT a `die()` (that's data, counted and reported per METR-03, not a harness failure).

**`--json` / `--check`-style machine-summary emission pattern** (lines 289-332, `main()`'s tail):
```python
summary = {
    "phase": n, "milestone": milestone, "rows": n_rows,
    "gaps": {...}, "file": str(map_path.resolve()), "changed": changed,
}
if opts["check"]:
    if opts["json"]:
        print(json.dumps(summary))
    ...
if opts["json"]:
    print(json.dumps(summary))
else:
    print(f"[cairn-map] {state} {map_path} — {n_rows} row(s), ...")
```
bench-aggregate.py should print a one-line human summary to stdout after writing `aggregated.json` (e.g. `[bench-aggregate] wrote <path> — N cell(s), M row(s) rejected`), mirroring this "always print one summary line" convention already used by `bench-matrix.py` (line 111-112) and `cairn-map.py`.

**Analog 2 (sorted multi-file input collection — directly answers RESEARCH.md Pitfall 3):** `benchmarks/scripts/stage-plugins.py`

**Repeatable-flag + `--all`-glob pattern** (lines 168-197):
```python
def parse_args(argv):
    opts = {"baselines": [], "all": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--baseline":
            if i + 1 >= len(argv):
                die(f"--baseline needs a value\n{USAGE}", EXIT_USAGE)
            opts["baselines"].append(argv[i + 1])
            i += 2
        elif arg == "--all":
            opts["all"] = True
            i += 1
        ...
    if not opts["baselines"] and not opts["all"]:
        die(f"at least one --baseline (or --all) is required\n{USAGE}", EXIT_USAGE)
    return opts

def main():
    opts = parse_args(sys.argv[1:])
    paths = list(opts["baselines"])
    if opts["all"]:
        found = sorted(str(p) for p in BASELINES_GLOB_DIR.glob("*.json"))
        if not found:
            die(f"--all found no manifests under {BASELINES_GLOB_DIR}/", EXIT_USAGE)
        paths += found
```
This is the exact repeatable-flag + `sorted(glob(...))` shape CONTEXT.md's "reads raw JSONL (one or more files)" requires, and it is already proven, tested code in this repo (not a hypothetical pattern) — reuse this shape for bench-aggregate.py's `--in <jsonl> [--in <jsonl> ...]` (or equivalent) plus a required `--out <aggregated.json>`.

**Core loop / gating / decomposition pattern (illustrative, from RESEARCH.md's Code Examples section — matches house style directly)**:
```python
REQUIRED = ("usage", "verify_passed", "baseline_id", "task_id")

def load_rows(paths):
    rows, rejected = [], 0
    for p in sorted(paths):                      # sorted: determinism
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if any(k not in row for k in REQUIRED):
                    rejected += 1
                    continue
                rows.append(row)
    return rows, rejected

def is_headline_pass(row):
    return row.get("verify_passed") is True and not row.get("is_error", False)
```

**Deterministic JSON emission** — matches `bench-run.py` line 248's `json.dumps(row, sort_keys=True)`, tightened per RESEARCH.md Pitfall 3/4 (fixed `separators` too, since this is a multi-key nested structure, not a flat row):
```python
json.dumps(aggregated, sort_keys=True, separators=(",", ":"))
```
Never let a bare `set()` or unsorted `glob`/`Path.glob` reach output ordering (RESEARCH.md Pitfalls 3-4, verified this session against this repo's Python 3.12.1).

**No live-call / stub-first testing precedent** — `cairn-map.py`'s `--check` mode (diff against expected, no mutation) is the closest existing "prove determinism without touching real state" pattern; `bench-aggregate.py`'s own determinism proof is a bats-level double-run diff (see test analog below), not a `--check` flag of its own (not required by CONTEXT.md).

---

### `benchmarks/scripts/bench-aggregate.sh` (new)

**Analog:** `benchmarks/scripts/bench-run.sh` (full file, 9 lines)

```bash
#!/usr/bin/env bash
# Thin wrapper around the bench-run harness. See bench-run.py for the contract.
# Usage: bench-run.sh --task <dir> --baseline <manifest.json> --out <path>
#        [--seed <int> --run-order-index <int>]
# Exit codes: 0 run completed, 2 usage error
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/bench-run.py" "$@"
```
Copy verbatim, retargeting the comment/usage line and script name (`bench-aggregate.py`). This exact 9-line shape (`set -euo pipefail`, `HERE=` self-locate, `exec python3 "$HERE/<script>.py" "$@"`) is used identically by `gbsync.sh` and `cairn-map.sh` — it is the repo's one canonical `.sh` wrapper template, zero variation across all four existing wrappers.

---

### `tests/bench-aggregate.bats` (new)

**Analog 1 (byte-identical double-run determinism proof):** `tests/bench-run.bats`, test `"running twice against identical stub input yields byte-identical JSONL, wall-clock excluded"` (lines 98-117):
```bash
@test "running twice against identical stub input yields byte-identical JSONL, wall-clock excluded" {
  make_claude_stub claude-success "$SUCCESS_JSON" 0
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    bash "$BENCH_SCRIPTS_DIR/bench-run.sh" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --baseline "$BENCH_BASELINES_DIR/vanilla.json" \
      --out "$BATS_TEST_TMPDIR/raw_a.jsonl"
  [ "$status" -eq 0 ]
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    bash "$BENCH_SCRIPTS_DIR/bench-run.sh" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --baseline "$BENCH_BASELINES_DIR/vanilla.json" \
      --out "$BATS_TEST_TMPDIR/raw_b.jsonl"
  [ "$status" -eq 0 ]
  run diff \
    <(jq -S 'del(.wall_clock_ms)' "$BATS_TEST_TMPDIR/raw_a.jsonl") \
    <(jq -S 'del(.wall_clock_ms)' "$BATS_TEST_TMPDIR/raw_b.jsonl")
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
```
This is CONTEXT.md's own required test ("Determinism proven by double-run diff in bats") — reuse the exact `run bench-aggregate ... twice, then diff -S normalized JSON, expect empty output` shape. Because `bench-aggregate.py`'s output has no non-deterministic field like `wall_clock_ms`, the `del(...)` step should be unnecessary — a true byte-for-byte `diff` of `aggregated.json` (no `jq -S` needed if `bench-aggregate.py` already emits `sort_keys=True`) is the stronger, more literal proof CONTEXT.md asks for ("deterministic byte-for-byte over the same input").

**Assertion style note** — this repo's bats suite has an established caveat (documented at the top of both `bench-run.bats` and `bench-matrix.bats`): a failing `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this bash, so positive checks use `run jq -e '<predicate>'` / `grep -qF`, and negative checks use `refute_in_output`/`refute_in_file` helper functions (defined per-file, e.g. `cairn-map.bats` lines 16-21) rather than bare `!`. Carry this convention into `bench-aggregate.bats` verbatim — do not write bare `[[ ! ... ]]` assertions.

**Analog 2 (fixture-JSONL-driven, no-live-call test style + jq predicate assertions):** `tests/bench-matrix.bats`, test `"bench-matrix.py runs each declared baseline exactly once..."` (lines 80-102) — the `jq -s -e 'map(...) | ...'` slurp-mode aggregate-assertion idiom:
```bash
run jq -s -e 'map(.run_order_index) | sort == [0, 1, 2]' \
  "$BATS_TEST_TMPDIR/matrix.jsonl"
[ "$status" -eq 0 ]
```
Use `jq -s -e` (slurp mode) for any assertion that needs to reason across multiple JSONL rows or multiple `aggregated.json` cells at once — this is the established idiom in this suite, not `jq` per-line.

**Analog 3 (required-field rejection / loud-reject test shape):** `tests/bench-run.bats`, test `"manifest missing a required key dies EXIT_USAGE naming the key"` (lines 214-236) — the shape for "malformed input is rejected loudly, named, and produces no output artifact":
```bash
run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
  bash "$BENCH_SCRIPTS_DIR/bench-run.sh" \
    --task "$BENCH_TASKS_DIR/smoke-convert" \
    --baseline "$BATS_TEST_TMPDIR/broken-manifest.json" \
    --out "$BATS_TEST_TMPDIR/raw-broken.jsonl"
[ "$status" -eq 2 ]
echo "$output" | grep -qF "model"
[ ! -e "$BATS_TEST_TMPDIR/raw-broken.jsonl" ]
```
`bench-aggregate.py`'s required-field-row-rejection is NOT a `die()`/exit-2 case (it's per-row data, counted in the output per METR-03) — so the analogous test shape here is "run bench-aggregate against a fixture with N well-formed + M malformed rows, assert exit 0, assert `aggregated.json`'s reject-count field == M, assert the M rejected rows are absent from any cell's stats" — same *structure* (assert on the artifact's content, not internals), different exit-code expectation.

---

### Fixture JSONL files (new)

**Analog 1 (real committed data — the "reject loudly" fixture per RESEARCH.md Pitfall 1 / CONTEXT.md's resolved Open Question 2):** `benchmarks/results/smoke-convert.jsonl` (2 rows, read in full this session) — use **unmodified**, both rows lack `baseline_id`, which is exactly the required-field-missing rejection path. Do not patch this committed file.

**Analog 2 (hand-authored heredoc fixtures — the pattern for the new *synthetic* gating/decomposition fixture):** `tests/helpers.bash`'s `make_fixture_baselines` (lines 23-44):
```bash
make_fixture_baselines() {
  FIXTURE_BASELINES_DIR="$BATS_TEST_TMPDIR/baselines"
  mkdir -p "$FIXTURE_BASELINES_DIR"
  local name
  for name in alpha beta gamma; do
    cat > "$FIXTURE_BASELINES_DIR/$name.json" <<EOF
{
  "name": "$name",
  ...
}
EOF
  done
}
```
and `make_env_asserting_claude_stub` (lines 334-354) for the shape of a hand-authored canned-JSON generator. For the new synthetic gating fixture (5 rows covering pass/fail/is_error/missing-fields per CONTEXT.md's test strategy), author it the same way this repo already authors every other test fixture: either a `tests/fixtures/*.jsonl` static file (simplest — the file IS the fixture, no bash templating needed since JSONL rows don't need per-test variables) or a `make_*_fixture()` helper in `tests/helpers.bash` if the test needs several parameterized variants. Given the rows are static (pass/fail/is_error/missing-field combinations, not templated per-test), prefer a plain static file under a new `tests/fixtures/` dir over a bash heredoc generator — simpler, and it can be `cat`-inspected directly like `benchmarks/results/smoke-convert.jsonl` already is.

**Field-shape reference for the synthetic fixture rows** — copy the live-schema field shape from `tests/bench-run.bats`'s `SUCCESS_JSON`/`ERROR_JSON` constants (lines 31-32) and the real `smoke-convert.jsonl` rows, not a hand-guessed minimal shape: `usage.cache_creation_input_tokens`, `modelUsage.<model>.cacheCreationInputTokens` (both present, since RESEARCH.md Pitfall 2 requires the decomposition logic to prefer `modelUsage`), `total_cost_usd`, `verify_passed`, `is_error`, `baseline_id`, `task_id`.

---

### `tests/bench-matrix.bats` (updates)

**Analog:** itself — every existing test in this file invokes `bench-matrix.py` without `--reps` (lines 83-89, 107-113, 115-121, 138-144). Per RESEARCH.md Pitfall 7, add `--reps 1` to every existing invocation so row-count assertions (`wc -l == 3`, `run_order_index sort == [0,1,2]`) keep their current meaning; add new `@test` blocks (same file, same `make_fixture_baselines` helper) exercising `--reps 5` explicitly — assert `wc -l == 15` (3 baselines × 5 reps), assert `rep_index` values are `sort == [0,0,0,1,1,1,2,2,2,3,3,3,4,4,4]` per baseline or `[0,1,2,3,4]` per baseline via `jq -s 'group_by(.baseline_id) | map(map(.rep_index)|sort)'`, and assert interleaving still holds (no baseline's 5 reps are all contiguous in `run_order_index`).

---

## Shared Patterns

### Error/exit convention (`die()`)
**Source:** `benchmarks/scripts/bench-matrix.py` lines 43-45, identical shape in `bench-run.py` lines 66-68, `cairn-map.py` lines 68-70, `gbsync.py` lines 51-53, `stage-plugins.py`.
**Apply to:** `bench-aggregate.py` — usage errors only (bad CLI args, unreadable `--out` parent dir). Required-field row rejection is explicitly NOT this pattern (it's counted data, per METR-03).
```python
def die(msg, code):
    print(f"[bench-aggregate] error: {msg}", file=sys.stderr)
    sys.exit(code)
```
`EXIT_OK = 0`, `EXIT_USAGE = 2` constants at module top, matching every script in the repo.

### Deterministic JSON output (`sort_keys=True`, sorted collections)
**Source:** `bench-run.py` line 248 (`json.dumps(row, sort_keys=True)`); `cairn-map.py`'s `roadmap_requirements`/`infer_milestone` (`sorted({...})`, lines 158, 238); `stage-plugins.py` line 193 (`sorted(str(p) for p in BASELINES_GLOB_DIR.glob("*.json"))`).
**Apply to:** `bench-aggregate.py` exclusively (the only new file that produces a multi-row aggregate artifact) — every `glob`/`Path.glob`, every `set()`, and every dict key destined for `aggregated.json` must pass through `sorted()` before emission; final emission via `json.dumps(obj, sort_keys=True, separators=(",", ":"))`.

### `.sh` wrapper template
**Source:** `benchmarks/scripts/bench-run.sh` (9 lines, byte-identical pattern in `cairn/scripts/gbsync.sh` and `cairn/scripts/cairn-map.sh`).
**Apply to:** `benchmarks/scripts/bench-aggregate.sh`.
```bash
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/bench-aggregate.py" "$@"
```

### Success gating (belt-and-braces dual boolean)
**Source:** RESEARCH.md Pattern 3, locked by CONTEXT.md METR-02; no direct existing-code analog (this is new logic), but the shape matches the repo's existing "two independent checks must both hold" precedent in `bench-run.py`'s `verify_proc.returncode == 0` (objective, external oracle) combined separately from `is_error` (subjective, from the `claude` payload) at row-write time (lines 236-240).
**Apply to:** `bench-aggregate.py`'s cell-stats computation, applied to every cell before any median/cost stat is computed.
```python
def is_headline_pass(row):
    return row.get("verify_passed") is True and not row.get("is_error", False)
```

### bats assertion-style caveat (no bare `!`/`[[ ]]` mid-test)
**Source:** documented at the top of `tests/bench-run.bats` (lines 9-11) and `tests/bench-matrix.bats` (lines 9-11), enforced via `refute_in_file`/`refute_in_output` helpers (e.g. `tests/cairn-map.bats` lines 16-21) and `run jq -e '<predicate>'` for positive checks.
**Apply to:** `tests/bench-aggregate.bats` in full — copy the same header comment and the same `refute_in_*` helper shape for any "field must be absent" assertion.

## No Analog Found

None — every file in scope has at least a role-match analog already read this session. `bench-aggregate.py`'s core statistics/gating logic (median, IQR, 4-way token decomposition) is genuinely new to this codebase (no prior stats code exists), but its *structural* shape (CLI parsing, die/exit convention, deterministic JSON emission, sorted-glob multi-file input) is fully covered by the analogs above; the statistics computation itself should follow RESEARCH.md's Code Examples section directly (already vetted against `statistics.median`/`statistics.quantiles(method='inclusive')` behavior at N=5, this session).

## Metadata

**Analog search scope:** `benchmarks/scripts/`, `cairn/scripts/`, `tests/` (bats + helpers.bash), `benchmarks/results/smoke-convert.jsonl`
**Files read in full this session:** `bench-matrix.py`, `bench-run.py`, `bench-run.sh`, `cairn-map.py`, `gbsync.py`, `gbsync.sh`, `stage-plugins.py` (partial), `tests/bench-matrix.bats`, `tests/bench-run.bats`, `tests/helpers.bash`, `tests/cairn-map.bats` (partial), `tests/gbsync.bats` (partial), `benchmarks/results/smoke-convert.jsonl`, `.planning/research/ARCHITECTURE.md` (aggregation section, grep-targeted)
**Pattern extraction date:** 2026-07-26

## Conventions

Convention derivation was run via the shared deterministic module (`gsd-tools.cjs verify conventions --derive`), scoped first to this phase's actual new-file directories.

**convention derivation skipped (no-readable-files)** — the shared conventions tool's corpus walker only scans JS/TS source (`/\.(c|m)?[jt]sx?$/`); this phase's files are 100% Python (`.py`), Bash (`.sh`), and Bats (`.bats`), so both `--scope benchmarks/scripts` and `--scope tests` returned `{ "skipped": true, "reason": "no-readable-files" }`. A repo-wide (unscoped) run does find JS/TS elsewhere in the tree (vendored plugin assets under `benchmarks/plugins/`), but that corpus is unrelated to this phase's file set and its axes are not reproduced here — they would mischaracterize conventions for files this phase does not touch.

In place of the tool's 4-axis table, the conventions actually load-bearing for this phase's files (derived by direct reading of the analogs above, not the automated tool) are:

| Axis | Dominant (observed) | Status |
|------|----------------------|--------|
| Python file naming | `kebab-case.py` (`bench-matrix.py`, `bench-run.py`, `stage-plugins.py`, `cairn-map.py`, `gbsync.py`) | named contract (100% of Python scripts in `benchmarks/scripts/` and `cairn/scripts/`) |
| Python identifier casing | `snake_case` for functions/vars, `UPPER_SNAKE` for module constants (`EXIT_OK`, `USAGE`, `BENCH_RUN_PY`) | named contract |
| Export/entry style | no package/module exports — every script is a standalone CLI with `def main(): ...` + `if __name__ == "__main__": main()` | named contract |
| Import style | stdlib-only, plain `import x` / `from pathlib import Path`, no relative package imports (each script is self-contained, not a package member) | named contract |
| `.sh` wrapper style | `set -euo pipefail` + `HERE=$(cd ... && pwd)` + `exec python3 "$HERE/<script>.py" "$@"`, byte-identical across all 4 existing wrappers | named contract |
| Error/exit style | `die(msg, code)` → `print(f"[<script>] error: {msg}", file=sys.stderr); sys.exit(code)`; `EXIT_OK=0`/`EXIT_USAGE=2` module constants | named contract |

**Contested hotspots (author's choice):** this repo's one documented intentional-contested split is the CJS↔SDK dual resolver inside the GSD plugin itself (`bin/lib/**` is CJS `module.exports`/`require`; `sdk/src/**` is ESM `export`/`import`) — each half is internally consistent per-directory, contested only when compared repo-wide. That split is orthogonal to this phase (Phase 3 touches none of `bin/lib/**` or `sdk/src/**`), but it is the prototype for how to read any future contested-axis finding here: match the directory's local style, never force one side's convention onto the other. Nothing in this phase's own scope (`benchmarks/scripts/`, `cairn/scripts/`, `tests/`) shows a comparable internal split — the six axes above are uniformly named contracts across every existing analog read this session.
