#!/usr/bin/env python3
"""bench-matrix — seeded, reproducible interleaved batch runner: one
bench-run.py invocation per declared baseline, in a deterministically
shuffled order, so no baseline ever benefits from always running first
(prompt-cache warm-up bias).

Usage:
    bench-matrix.py --baselines <name,name,...> --task <task-dir>
                    --out <jsonl-path> --seed <int>
                    [--baselines-dir <dir>]

Behavior:
    1. Split --baselines into names (e.g. "vanilla,gsd-only,cairn") and
       shuffle them with an instance-scoped random.Random(seed) — the same
       seed always yields the same execution order across invocations.
    2. Resolve every name in the shuffled order to
       <baselines-dir>/<name>.json and validate the FULL resolved list
       exists on disk BEFORE invoking anything (validate-before-spend).
    3. Invoke bench-run.py once per baseline in that order, passing --task /
       --out through plus --baseline <manifest>, --seed <seed> and
       --run-order-index <idx>, so every row records its provenance.
    4. A single bench-run.py exit code is data about that run, never a batch
       abort: every ordered invocation is always launched, one report line
       per completed invocation, one final summary line.

Exit codes:
    0  every ordered invocation was launched (regardless of each individual
       bench-run.py's own exit code)
    2  usage error (missing manifest file, empty --baselines, bad arguments)
"""
import argparse
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


def build_execution_order(baselines, seed):
    """Deterministic seeded shuffle of the declared baseline names.

    Instance-scoped RNG (random.Random(seed)), never the shared random
    module: two calls with the same inputs always return the same order.
    """
    order = list(baselines)
    random.Random(seed).shuffle(order)
    return order


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
    args = parser.parse_args()

    names = [n.strip() for n in args.baselines.split(",") if n.strip()]
    if not names:
        die("--baselines needs at least one baseline name", EXIT_USAGE)

    order = build_execution_order(names, args.seed)

    # Validate the full resolved list before invoking anything: a missing
    # manifest must fail the batch loudly BEFORE any run spends anything.
    resolved = []
    for name in order:
        manifest_path = Path(args.baselines_dir) / f"{name}.json"
        if not manifest_path.is_file():
            die(f"baseline manifest not found: {manifest_path}", EXIT_USAGE)
        resolved.append((name, manifest_path))

    for idx, (name, manifest_path) in enumerate(resolved):
        cmd = [sys.executable, str(BENCH_RUN_PY),
               "--task", args.task,
               "--out", args.out,
               "--baseline", str(manifest_path),
               "--seed", str(args.seed),
               "--run-order-index", str(idx)]
        # No check=True: an individual run's exit code is data about that
        # run (matching bench-run.py's own EXIT_OK-regardless-of-outcome
        # contract); the batch always continues.
        subprocess.run(cmd)
        print(f"[bench-matrix] {idx}: {name}")
    print(f"[bench-matrix] {len(resolved)} run(s) completed in order: "
          f"{', '.join(order)}")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
