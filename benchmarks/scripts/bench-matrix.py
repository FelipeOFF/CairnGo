#!/usr/bin/env python3
"""bench-matrix — seeded, reproducible interleaved batch runner: one
bench-run.py invocation per (task, baseline, repetition) cell, in a
deterministically shuffled order, so no task/baseline combination ever
benefits from always running first (prompt-cache warm-up bias) and no
cell's repetitions are launched as one contiguous block.

Usage:
    bench-matrix.py (--task <task-dir> | --tasks <spec>)
                    --baselines <name,name,...>
                    --out <jsonl-path> --seed <int>
                    [--baselines-dir <dir>] [--reps <N>]

    --task and --tasks are mutually exclusive; exactly one is required.
    --tasks accepts either a comma-separated list of task-dir paths, or a
    single glob pattern (containing '*', e.g. "benchmarks/tasks/*"),
    resolved via sorted(glob.glob(...)) for deterministic ordering (stdlib
    glob module — pathlib Path().glob() raises NotImplementedError on
    absolute patterns in Python 3.12, and $BENCH_TASKS_DIR-style absolute
    globs are the repo convention)
    independent of filesystem iteration order.

Behavior:
    1. Resolve --task/--tasks into a sorted list of task directories;
       validate every resolved directory contains task.json BEFORE doing
       anything else (fail loud before spend).
    2. Split --baselines into names (e.g. "vanilla,gsd-only,cairn"), build
       the full task x baseline x rep cross-product (--reps repetitions per
       cell, default 5 per METR-01), and shuffle the whole cell list with
       one instance-scoped random.Random(seed) — the same seed always
       yields the same execution order across invocations, and no
       task/baseline combination's repetitions are launched as a
       contiguous block.
    3. Resolve every shuffled cell's baseline name to
       <baselines-dir>/BASELINE_NAME.json and validate the FULL resolved list
       exists on disk BEFORE invoking anything (validate-before-spend).
    4. Invoke bench-run.py once per cell in that order, passing --task
       <task-dir> / --out through plus --baseline <manifest>, --seed
       <seed>, --run-order-index <idx> and --rep-index <rep>, so every row
       records its provenance. The Phase 3 aggregator already keys cells by
       task_id::baseline_id (task_id comes from task.json, not the
       directory path), so adding more tasks here requires zero
       aggregation changes.
    5. A single bench-run.py exit code is data about that run, never a
       batch abort: every ordered invocation is always launched, one
       report line per completed invocation, one final summary line.

Exit codes:
    0  every ordered invocation was launched (regardless of each individual
       bench-run.py's own exit code)
    2  usage error (missing manifest/task.json, empty --baselines, bad
       arguments, --task and --tasks both/neither given)
"""
import argparse
import glob
import itertools
import random
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2

BENCH_RUN_PY = Path(__file__).parent / "bench-run.py"


def die(msg, code):
    print(f"[bench-matrix] error: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_tasks(task_arg, tasks_arg):
    """Resolve --task/--tasks into a sorted list of task-dir Path objects.

    --tasks accepts a comma-separated list of paths, or a single glob
    pattern (containing '*') resolved via sorted(glob.glob(...)) — stdlib
    glob module, NOT pathlib (absolute-pattern support). Every
    resolved directory must contain task.json — validated here, before
    anything else runs.
    """
    if task_arg:
        dirs = [Path(task_arg)]
    elif "*" in tasks_arg:
        dirs = sorted(Path(p) for p in glob.glob(tasks_arg))  # stdlib glob: handles absolute patterns; Path.glob() does not (py3.12 NotImplementedError)
    else:
        dirs = sorted(Path(t.strip()) for t in tasks_arg.split(",") if t.strip())
    if not dirs:
        die(f"--tasks resolved to zero task directories: {tasks_arg}", EXIT_USAGE)
    for d in dirs:
        if not (d / "task.json").is_file():
            die(f"task.json not found in {d}", EXIT_USAGE)
    return dirs


def build_execution_order(tasks, baselines, reps, seed):
    """Deterministic seeded shuffle of the full task x baseline x rep
    cross-product.

    Cells are (task_dir, baseline_name, rep_idx) tuples spanning the whole
    cross-product, shuffled with an instance-scoped RNG (random.Random(seed)),
    never the shared random module: two calls with the same inputs always
    return the same order, and no task/baseline combination's repetitions
    are launched as a contiguous block. For a single-task list (legacy
    --task), this shuffles the identical (baseline, rep) permutation the
    pre-Phase-5 two-field cross-product produced for the same seed — Python's
    Fisher-Yates shuffle depends only on list length and seed, never on
    tuple contents, so a constant task_dir prefix changes nothing.
    """
    cells = list(itertools.product(tasks, baselines, range(reps)))
    random.Random(seed).shuffle(cells)
    return cells


def main():
    parser = argparse.ArgumentParser(
        prog="bench-matrix",
        description="Run bench-run.py once per task x baseline x rep cell "
                    "in a seeded, reproducible shuffled order, stamping "
                    "seed and run-order provenance into every row.")
    task_group = parser.add_mutually_exclusive_group(required=True)
    task_group.add_argument("--task", metavar="TASK_DIR",
                        help="single task fixture dir (legacy single-task "
                             "mode, unchanged since Phase 2)")
    task_group.add_argument("--tasks", metavar="SPEC",
                        help="comma-separated task-dir paths, or a single "
                             "glob pattern containing '*' (e.g. "
                             "'benchmarks/tasks/*'), sorted for determinism")
    parser.add_argument("--baselines", required=True, metavar="NAMES",
                        help="comma-separated baseline names, e.g. "
                             "vanilla,gsd-only,cairn (names, not paths)")
    parser.add_argument("--baselines-dir", default="benchmarks/baselines",
                        metavar="DIR",
                        help="directory holding BASELINE_NAME.json manifests "
                             "(default: benchmarks/baselines)")
    parser.add_argument("--out", required=True, metavar="JSONL",
                        help="output JSONL path, passed through to "
                             "bench-run.py (rows append in execution order)")
    parser.add_argument("--seed", required=True, type=int, metavar="N",
                        help="shuffle seed — required, no silent random "
                             "default: reproducibility of the execution "
                             "order is the point")
    parser.add_argument("--reps", type=int, default=5, metavar="N",
                        help="repetitions per (task, baseline) cell — "
                             "default 5 (METR-01); pass a smaller explicit "
                             "value only for pilots")
    args = parser.parse_args()

    task_dirs = resolve_tasks(args.task, args.tasks)

    names = [n.strip() for n in args.baselines.split(",") if n.strip()]
    if not names:
        die("--baselines needs at least one baseline name", EXIT_USAGE)

    order = build_execution_order(task_dirs, names, args.reps, args.seed)

    # Validate the full resolved baseline-manifest list before invoking
    # anything: a missing manifest must fail the batch loudly BEFORE any run
    # spends anything. Re-checking is_file() once per cell is cheap
    # idempotent local IO — not worth deduping across repetitions.
    resolved = []
    for task_dir, name, rep_idx in order:
        manifest_path = Path(args.baselines_dir) / f"{name}.json"
        if not manifest_path.is_file():
            die(f"baseline manifest not found: {manifest_path}", EXIT_USAGE)
        resolved.append((task_dir, name, rep_idx, manifest_path))

    for idx, (task_dir, name, rep_idx, manifest_path) in enumerate(resolved):
        cmd = [sys.executable, str(BENCH_RUN_PY),
               "--task", str(task_dir),
               "--out", args.out,
               "--baseline", str(manifest_path),
               "--seed", str(args.seed),
               "--run-order-index", str(idx),
               "--rep-index", str(rep_idx)]
        # No check=True: an individual run's exit code is data about that
        # run (matching bench-run.py's own EXIT_OK-regardless-of-outcome
        # contract); the batch always continues.
        subprocess.run(cmd)
        print(f"[bench-matrix] {idx}: {task_dir.name} :: {name} (rep {rep_idx})")
    print(f"[bench-matrix] {len(resolved)} run(s) completed in order: "
          f"{', '.join(f'{t.name}::{n}#{r}' for t, n, r, _ in resolved)}")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
