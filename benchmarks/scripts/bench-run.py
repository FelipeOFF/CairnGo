#!/usr/bin/env python3
"""bench-run — invoke claude -p headless against one task fixture under one
baseline manifest, write one raw JSONL row per run.

Usage:
    bench-run.py --task <task-dir> --baseline <manifest.json> --out <jsonl-path>
                 [--seed <int> --run-order-index <int> --rep-index <int>]

Behavior:
    1. Read <task-dir>/task.json (id, timeout_s, prompt_file) and the prompt
       text from <task-dir>/<prompt_file> (default prompt.md). Claude flags
       are NOT read from task.json: the baseline manifest is the sole source
       of truth for model pinning and flags.
    2. Load and validate the --baseline manifest: required keys name, model
       (full pinned id), claude_flags, provisioning.plugin_dirs; every
       plugin_dirs[].staged_path (joined with the entry's optional
       plugin_dir_subpath, when declared) must already exist on disk. All
       validation happens BEFORE any subprocess is launched (fail loud,
       spend nothing).
    3. Stage a fresh mktemp workdir from <task-dir>/fixture/ and a fresh,
       empty mktemp HOME for the claude subprocess.
    4. Resolve the claude binary via CAIRN_BENCH_CLAUDE_BIN, falling back to
       the real `claude` on PATH.
    5. Invoke `claude -p <prompt> --output-format json` with every remaining
       flag read from the manifest: --max-turns, --model, --permission-mode,
       plus --no-session-persistence / --bare when set in claude_flags, plus
       one `--plugin-dir <target>` pair per provisioning.plugin_dirs entry,
       where <target> is staged_path joined with the entry's optional
       plugin_dir_subpath (for plugins whose plugin.json lives in a
       subdirectory of the staged repo; omitted, the target is the bare
       staged_path, unchanged). The subprocess environment is explicitly
       env={HOME: <fresh HOME>, PATH, ANTHROPIC_API_KEY-if-present}: the
       operator's environment is replaced, never merged. --bare skips
       claude.ai OAuth, so isolated runs authenticate strictly via
       ANTHROPIC_API_KEY.
    6. Parse stdout as JSON regardless of returncode; on parse failure,
       timeout, or an unlaunchable claude binary, synthesize
       {"is_error": true, "parse_error": "..."}.
    7. Invoke <task-dir>/verify.sh <workdir> with the FULL inherited
       environment (the oracle is deliberately not isolated: it needs
       PATH-discoverable pytest/bats and a normal shell environment);
       verify_passed = (returncode==0).
    8. Append one JSON line to --out: task_id, baseline_id, wall_clock_ms,
       payload fields, verify_passed; plus seed / run_order_index /
       rep_index (as JSON integers) when the optional flags were provided —
       bench-matrix.py passes them so every orchestrated row records its
       provenance. Absent flags leave the row schema untouched. The row
       also carries category when task.json declares one (optional task
       metadata, same present-only-when-provided philosophy).
    9. rmtree the workdir and the disposable HOME.

Exit codes:
    0  run completed (regardless of verify_passed or is_error — a run's
       outcome is a data column, not a harness failure)
    2  usage error (bad args, unreadable task/manifest, unstaged plugin dir)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2

USAGE = ("usage: bench-run.py --task <task-dir> --baseline <manifest.json> "
         "--out <jsonl-path> [--seed <int> --run-order-index <int>] "
         "[--rep-index <int>]")


def die(msg, code):
    print(f"[bench-run] error: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_claude_bin():
    return os.environ.get("CAIRN_BENCH_CLAUDE_BIN") or shutil.which("claude") or "claude"


def isolated_claude_env(fresh_home):
    """Explicit minimal env for the claude subprocess: replaces, never merges.

    HOME points at a disposable empty dir (no operator CLAUDE.md/MCP/hooks),
    PATH is preserved for tool discoverability only, and ANTHROPIC_API_KEY is
    passed through when present (--bare auth is strictly the API key).
    """
    env = {"HOME": fresh_home, "PATH": os.environ.get("PATH", "")}
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    return env


def load_baseline(path):
    """Parse + validate a baseline manifest; die(EXIT_USAGE) before any spend."""
    baseline_path = Path(path)
    if not baseline_path.is_file():
        die(f"baseline manifest not found: {baseline_path}", EXIT_USAGE)
    try:
        manifest = json.loads(baseline_path.read_text())
    except json.JSONDecodeError as e:
        die(f"baseline manifest failed to parse: {e}", EXIT_USAGE)
    for key in ("name", "model", "claude_flags", "provisioning"):
        if key not in manifest:
            die(f"baseline manifest missing required '{key}': {baseline_path}",
                EXIT_USAGE)
    if "plugin_dirs" not in manifest["provisioning"]:
        die("baseline manifest missing required 'provisioning.plugin_dirs': "
            f"{baseline_path}", EXIT_USAGE)
    for entry in manifest["provisioning"]["plugin_dirs"]:
        target = Path(entry["staged_path"]) / entry.get("plugin_dir_subpath", "")
        if not target.is_dir():
            die(f"plugin '{entry['plugin']}' staged_path (+ plugin_dir_subpath) "
                f"target not found: {target} (stage and build it before running)",
                EXIT_USAGE)
    return manifest


def parse_args(argv):
    # seed / run_order_index / rep_index are optional row-provenance stamps:
    # set by bench-matrix.py (or an operator) for interleaved batch runs,
    # None when bench-run.py is invoked standalone.
    opts = {"task": None, "out": None, "baseline": None,
            "seed": None, "run_order_index": None, "rep_index": None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--task":
            if i + 1 >= len(argv):
                die(f"--task needs a value\n{USAGE}", EXIT_USAGE)
            opts["task"] = argv[i + 1]
            i += 2
        elif arg == "--baseline":
            if i + 1 >= len(argv):
                die(f"--baseline needs a value\n{USAGE}", EXIT_USAGE)
            opts["baseline"] = argv[i + 1]
            i += 2
        elif arg == "--out":
            if i + 1 >= len(argv):
                die(f"--out needs a value\n{USAGE}", EXIT_USAGE)
            opts["out"] = argv[i + 1]
            i += 2
        elif arg == "--seed":
            if i + 1 >= len(argv):
                die(f"--seed needs a value\n{USAGE}", EXIT_USAGE)
            try:
                opts["seed"] = int(argv[i + 1])
            except ValueError:
                die(f"--seed must be an integer, got '{argv[i + 1]}'",
                    EXIT_USAGE)
            i += 2
        elif arg == "--run-order-index":
            if i + 1 >= len(argv):
                die(f"--run-order-index needs a value\n{USAGE}", EXIT_USAGE)
            try:
                opts["run_order_index"] = int(argv[i + 1])
            except ValueError:
                die("--run-order-index must be an integer, "
                    f"got '{argv[i + 1]}'", EXIT_USAGE)
            i += 2
        elif arg == "--rep-index":
            if i + 1 >= len(argv):
                die(f"--rep-index needs a value\n{USAGE}", EXIT_USAGE)
            try:
                opts["rep_index"] = int(argv[i + 1])
            except ValueError:
                die(f"--rep-index must be an integer, got '{argv[i + 1]}'",
                    EXIT_USAGE)
            i += 2
        else:
            die(f"unknown option '{arg}'\n{USAGE}", EXIT_USAGE)
    if opts["task"] is None or opts["out"] is None or opts["baseline"] is None:
        die(f"--task, --out, and --baseline are all required\n{USAGE}",
            EXIT_USAGE)
    return opts


def main():
    opts = parse_args(sys.argv[1:])
    task_dir = Path(opts["task"])
    out_path = opts["out"]
    if not task_dir.is_dir():
        die(f"task dir not found: {task_dir}", EXIT_USAGE)
    task_json = task_dir / "task.json"
    if not task_json.is_file():
        die(f"task.json not found in {task_dir}", EXIT_USAGE)
    try:
        task = json.loads(task_json.read_text())
    except json.JSONDecodeError as e:
        die(f"task.json failed to parse: {e}", EXIT_USAGE)
    prompt_path = task_dir / task.get("prompt_file", "prompt.md")
    if not prompt_path.is_file():
        die(f"prompt file not found: {prompt_path}", EXIT_USAGE)
    prompt_text = prompt_path.read_text()

    # Validate the baseline manifest (including every staged plugin dir)
    # BEFORE any API spend, same rationale as the output-path check below.
    manifest = load_baseline(opts["baseline"])

    # Validate the output path BEFORE any API spend: a live run whose row
    # cannot be written is money lost (observed live, 2026-07-25).
    out_parent = Path(out_path).parent
    if not out_parent.is_dir():
        die(f"output directory not found: {out_parent} (create it first)", EXIT_USAGE)

    workdir = tempfile.mkdtemp(prefix="cairn-bench-")
    fresh_home = tempfile.mkdtemp(prefix="cairn-bench-home-")
    try:
        shutil.copytree(task_dir / "fixture", workdir, dirs_exist_ok=True)
        # Every claude flag comes from the baseline manifest, the single
        # source of truth for pinning (bare model aliases like "claude-haiku"
        # are rejected by the API — the manifest carries the full pinned id).
        # claude_flags is identical across baselines; only
        # provisioning.plugin_dirs differs. --bare skips claude.ai OAuth
        # (verified live 2026-07-25), so isolated runs authenticate strictly
        # via ANTHROPIC_API_KEY in the scoped env.
        flags = manifest["claude_flags"]
        cmd = [resolve_claude_bin(), "-p", prompt_text,
               "--output-format", "json",
               "--max-turns", str(flags["max_turns"]),
               "--model", manifest["model"],
               "--permission-mode", flags["permission_mode"]]
        if flags.get("no_session_persistence"):
            cmd.append("--no-session-persistence")
        if flags.get("bare"):
            cmd.append("--bare")
        for entry in manifest["provisioning"]["plugin_dirs"]:
            target = Path(entry["staged_path"]) / entry.get("plugin_dir_subpath", "")
            cmd += ["--plugin-dir", str(target)]
        start = time.time()
        try:
            proc = subprocess.run(cmd, cwd=workdir, capture_output=True,
                                  text=True, timeout=task["timeout_s"],
                                  env=isolated_claude_env(fresh_home))
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
            # Parse regardless of returncode: error results still carry
            # usage/total_cost_usd, and the exit-code contract is undocumented.
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                payload = {"is_error": True, "parse_error": str(e),
                           "raw_stdout": proc.stdout[:2000]}
        verify_proc = subprocess.run(["bash", str(task_dir / "verify.sh"),
                                      workdir])
        row = {"task_id": task["id"], "baseline_id": manifest["name"],
               "wall_clock_ms": wall_ms, **payload,
               "verify_passed": verify_proc.returncode == 0}
        # Optional task-level metadata stamp: only present when task.json
        # declares "category" (CORP-01's bias-control decision), so rows
        # for tasks without one keep their pre-Phase-5 schema untouched.
        if "category" in task:
            row["category"] = task["category"]
        # Row-provenance stamps: only present when provided, so standalone
        # rows keep their existing schema (values already ints via parse_args).
        if opts["seed"] is not None:
            row["seed"] = opts["seed"]
        if opts["run_order_index"] is not None:
            row["run_order_index"] = opts["run_order_index"]
        if opts["rep_index"] is not None:
            row["rep_index"] = opts["rep_index"]
        with open(out_path, "a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        shutil.rmtree(fresh_home, ignore_errors=True)
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
