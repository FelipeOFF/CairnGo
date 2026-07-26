#!/usr/bin/env python3
"""bench-matrix — seeded, reproducible interleaved batch runner: one
bench-run.py invocation per (baseline, repetition) cell, in a
deterministically shuffled order, so no baseline ever benefits from always
running first (prompt-cache warm-up bias) and no baseline's repetitions are
launched as one contiguous block.

Usage:
    bench-matrix.py --baselines <name,name,...> --task <task-dir>
                    --out <jsonl-path> --seed <int>
                    [--baselines-dir <dir>] [--reps <N>]

Behavior:
    1. Split --baselines into names (e.g. "vanilla,gsd-only,cairn"), build
       the full baseline x rep cross-product (--reps repetitions per
       baseline, default 5 per METR-01), and shuffle the whole cell list
       with one instance-scoped random.Random(seed) — the same seed always
       yields the same execution order across invocations, and a baseline's
       repetitions are free to interleave with other baselines' runs.
    2. Resolve every shuffled cell's name to <baselines-dir>/<name>.json
       and validate the FULL resolved list exists on disk BEFORE invoking
       anything (validate-before-spend).
    3. Invoke bench-run.py once per cell in that order, passing --task /
       --out through plus --baseline <manifest>, --seed <seed>,
       --run-order-index <idx> and --rep-index <rep>, so every row records
       its provenance.
    4. A single bench-run.py exit code is data about that run, never a batch
       abort: every ordered invocation is always launched, one report line
       per completed invocation, one final summary line.

Exit codes:
    0  every ordered invocation was launched (regardless of each individual
       bench-run.py's own exit code)
    2  usage error (missing manifest file, empty --baselines, bad arguments)
"""
import argparse
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


def build_execution_order(baselines, reps, seed):
    """Deterministic seeded shuffle of the full baseline x rep cross-product.

    Cells are (name, rep_idx) tuples spanning the whole cross-product,
    shuffled with an instance-scoped RNG (random.Random(seed)), never the
    shared random module: two calls with the same inputs always return the
    same order, and repetitions of one baseline interleave freely with the
    others'.
    """
    cells = list(itertools.product(baselines, range(reps)))
    random.Random(seed).shuffle(cells)
    return cells


def main():
    parser = argparse.ArgumentParser(
        prog="bench-matrix",
        description="Run bench-run.py once per baseline in a seeded, "
                    "reproducible shuffled order, stamping seed and "
                    "run-order provenance into every row.")
    parser.add_argument("--baselines", required=True, metavar="NAMES",
                        help="comma-separated baseline names, e.g. "
                             "vanilla,gsd-only,cairn (names, not paths)")
    parser.add_argument("--baselines-dir", default="benchmarks/baselines",
                        metavar="DIR",
                        help="directory holding <name>.json manifests "
                             "(default: benchmarks/baselines)")
    parser.add_argument("--task", required=True, metavar="TASK_DIR",
                        help="task fixture dir, passed through to "
                             "bench-run.py")
    parser.add_argument("--out", required=True, metavar="JSONL",
                        help="output JSONL path, passed through to "
                             "bench-run.py (rows append in execution order)")
    parser.add_argument("--seed", required=True, type=int, metavar="N",
                        help="shuffle seed — required, no silent random "
                             "default: reproducibility of the execution "
                             "order is the point")
    parser.add_argument("--reps", type=int, default=5, metavar="N",
                        help="repetitions per baseline — default 5 "
                             "(METR-01); pass a smaller explicit value "
                             "only for pilots")
    args = parser.parse_args()

    names = [n.strip() for n in args.baselines.split(",") if n.strip()]
    if not names:
        die("--baselines needs at least one baseline name", EXIT_USAGE)

    order = build_execution_order(names, args.reps, args.seed)

    # Validate the full resolved list before invoking anything: a missing
    # manifest must fail the batch loudly BEFORE any run spends anything.
    # Re-checking is_file() once per rep is cheap idempotent local IO — not
    # worth deduping across repetitions of the same name.
    resolved = []
    for name, rep_idx in order:
        manifest_path = Path(args.baselines_dir) / f"{name}.json"
        if not manifest_path.is_file():
            die(f"baseline manifest not found: {manifest_path}", EXIT_USAGE)
        resolved.append((name, rep_idx, manifest_path))

    for idx, (name, rep_idx, manifest_path) in enumerate(resolved):
        cmd = [sys.executable, str(BENCH_RUN_PY),
               "--task", args.task,
               "--out", args.out,
               "--baseline", str(manifest_path),
               "--seed", str(args.seed),
               "--run-order-index", str(idx),
               "--rep-index", str(rep_idx)]
        # No check=True: an individual run's exit code is data about that
        # run (matching bench-run.py's own EXIT_OK-regardless-of-outcome
        # contract); the batch always continues.
        subprocess.run(cmd)
        print(f"[bench-matrix] {idx}: {name} (rep {rep_idx})")
    print(f"[bench-matrix] {len(resolved)} run(s) completed in order: "
          f"{', '.join(f'{name}#{rep_idx}' for name, rep_idx, _ in resolved)}")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
