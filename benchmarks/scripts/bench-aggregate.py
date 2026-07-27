#!/usr/bin/env python3
"""bench-aggregate — deterministically fold one or more raw benchmark JSONL
files into a single aggregated.json of per-(task, baseline) cell statistics.

Usage:
    bench-aggregate.py --in <jsonl> [--in <jsonl> ...] --out <aggregated.json>

Behavior:
    1. Validate before reading anything: every --in path must be an existing
       file and --out's parent directory must exist (die EXIT_USAGE otherwise
       — fail loud before doing any work).
    2. Load rows from every --in file in sorted-path order (argument order
       never affects output). Per line: strip, skip blanks, json.loads.
       A line that is not valid JSON, or a row missing any REQUIRED key
       (usage, verify_passed, baseline_id, task_id), is COUNTED in
       rejected_rows and excluded from every cell — never a die(), never a
       silent drop. Row rejection is data, not a harness failure.
    3. Group rows into (task_id, baseline_id) cells and compute per-cell
       statistics, gated by the belt-and-braces headline-pass rule:
       verify_passed is True AND NOT is_error. The two axes are independent
       (a run can hit max-turns with the task already solved), so a row that
       is verify_passed=true but is_error=true never counts toward n_passed
       and never contributes to any cost/token stat. Every cell also
       surfaces the source task's category (null when no row carried one) —
       always present, never omitted.
    4. Token decomposition is 4-way (input / cache_creation / cache_read /
       output) and PREFERS modelUsage over the flat usage dict: modelUsage's
       per-model token fields reconcile with total_cost_usd on real captured
       rows, while the flat usage dict under-reports (~30% gap observed on
       live data). usage is the fallback for rows without modelUsage.
    5. Cost stats per cell: median + min/max over passing rows' total_cost_usd
       (primary spread at small N), plus IQR via
       statistics.quantiles(method="inclusive") as a secondary measure —
       only when >= 2 passing costs exist (the quantiles API requires it).
       A cell with zero passing rows reports null cost/token medians (never
       a fabricated 0, never a crash) while keeping pass_rate/n_total/
       n_passed visible, so an all-fail baseline is loud in the artifact.
    6. Write aggregated.json via json.dumps(sort_keys=True,
       separators=(",", ":")) with cells iterated in sorted key order and no
       timestamps anywhere: identical input always produces byte-identical
       output.

Exit codes:
    0  aggregation completed (regardless of how many rows were rejected —
       rejection counts are data in the artifact, not a failure)
    2  usage error (bad args, missing --in file, missing --out parent dir)
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
REQUIRED = ("usage", "verify_passed", "baseline_id", "task_id")

USAGE = ("usage: bench-aggregate.py --in <jsonl> [--in <jsonl> ...] "
         "--out <aggregated.json>")


def die(msg, code):
    print(f"[bench-aggregate] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    opts = {"in": [], "out": None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--in":
            if i + 1 >= len(argv):
                die(f"--in needs a value\n{USAGE}", EXIT_USAGE)
            opts["in"].append(argv[i + 1])
            i += 2
        elif arg == "--out":
            if i + 1 >= len(argv):
                die(f"--out needs a value\n{USAGE}", EXIT_USAGE)
            if opts["out"] is not None:
                die(f"--out given more than once\n{USAGE}", EXIT_USAGE)
            opts["out"] = argv[i + 1]
            i += 2
        else:
            die(f"unknown option '{arg}'\n{USAGE}", EXIT_USAGE)
    if not opts["in"]:
        die(f"at least one --in is required\n{USAGE}", EXIT_USAGE)
    if opts["out"] is None:
        die(f"--out is required\n{USAGE}", EXIT_USAGE)
    return opts


def load_rows(paths):
    """Parse JSONL rows from every path (sorted for determinism).

    A malformed JSON line or a row missing any REQUIRED key is COUNTED as
    rejected, never a die() — this is data, not a usage error. One bad line
    never aborts the rest of the file's rows from loading.
    """
    rows, rejected = [], 0
    for p in sorted(paths):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    rejected += 1
                    continue
                if any(k not in row for k in REQUIRED):
                    rejected += 1
                    continue
                rows.append(row)
    return rows, rejected


def is_headline_pass(row):
    """Belt-and-braces double gate: verify_passed alone is not enough — an
    is_error row (api_error, max_turns, ...) is excluded even if verify
    happened to pass (the two axes are independent on real captured rows)."""
    return row.get("verify_passed") is True and not row.get("is_error", False)


def token_components(row):
    """Prefer modelUsage (reconciles with total_cost_usd on real rows; the
    flat usage dict under-reports by ~30% on live data); fall back to the
    flat usage dict when modelUsage is absent (e.g. minimal/stub rows)."""
    mu = row.get("modelUsage")
    if mu:
        agg = {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}
        for m in mu.values():
            agg["input"] += m.get("inputTokens", 0)
            agg["cache_creation"] += m.get("cacheCreationInputTokens", 0)
            agg["cache_read"] += m.get("cacheReadInputTokens", 0)
            agg["output"] += m.get("outputTokens", 0)
        return agg
    u = row.get("usage") or {}
    return {"input": u.get("input_tokens", 0),
            "cache_creation": u.get("cache_creation_input_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0),
            "output": u.get("output_tokens", 0)}


def group_cells(rows):
    cells = defaultdict(list)
    for r in rows:
        cells[(r["task_id"], r["baseline_id"])].append(r)
    return cells


def cell_stats(rows):
    task_id, baseline_id = rows[0]["task_id"], rows[0]["baseline_id"]
    passed = [r for r in rows if is_headline_pass(r)]
    n_total, n_passed = len(rows), len(passed)
    stats = {
        "task_id": task_id, "baseline_id": baseline_id,
        "n_total": n_total, "n_passed": n_passed,
        "pass_rate": (n_passed / n_total) if n_total else 0.0,
    }
    # Task-level metadata surfaced automatically per CORP-01's bias-
    # control decision: every cell reports the source task's category
    # (null when no row in the cell carried one) so a reader/chart can
    # group or flag "honest-non-win" cells without joining task.json.
    stats["category"] = rows[0].get("category")
    costs = sorted(r["total_cost_usd"] for r in passed if "total_cost_usd" in r)
    if costs:
        stats["cost_median"] = statistics.median(costs)
        stats["cost_min"] = costs[0]
        stats["cost_max"] = costs[-1]
    else:
        stats["cost_median"] = stats["cost_min"] = stats["cost_max"] = None
    stats["cost_iqr"] = None
    if len(costs) >= 2:   # statistics.quantiles requires len(data) >= 2
        q = statistics.quantiles(costs, n=4, method="inclusive")
        stats["cost_iqr"] = q[2] - q[0]

    components = [token_components(r) for r in passed]
    tokens = {}
    for key in ("input", "cache_creation", "cache_read", "output"):
        values = sorted(c[key] for c in components)
        tokens[f"{key}_sum"] = sum(values)
        tokens[f"{key}_median"] = statistics.median(values) if values else None
    stats["tokens"] = tokens
    return stats


def main():
    opts = parse_args(sys.argv[1:])
    for p in opts["in"]:
        if not Path(p).is_file():
            die(f"input file not found: {p}", EXIT_USAGE)
    out_path = Path(opts["out"])
    if not out_path.parent.is_dir():
        die(f"output directory not found: {out_path.parent} (create it first)",
            EXIT_USAGE)

    rows, rejected = load_rows(opts["in"])
    cells = group_cells(rows)
    out = {"cells": {}, "rejected_rows": rejected}
    for key in sorted(cells):                 # sorted cell keys: determinism
        task_id, baseline_id = key
        out["cells"][f"{task_id}::{baseline_id}"] = cell_stats(cells[key])
    out_path.write_text(json.dumps(out, sort_keys=True,
                                   separators=(",", ":")) + "\n")
    print(f"[bench-aggregate] wrote {out_path} — {len(out['cells'])} cell(s), "
          f"{rejected} row(s) rejected")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
