#!/usr/bin/env python3
"""bench-run — invoke claude -p headless against one task fixture, write one
raw JSONL row per run.

Usage:
    bench-run.py --task <task-dir> --out <jsonl-path>

Behavior:
    1. Read <task-dir>/task.json (id, timeout_s, max_turns, prompt_file) and
       the prompt text from <task-dir>/<prompt_file> (default prompt.md).
    2. Stage a fresh mktemp workdir from <task-dir>/fixture/.
    3. Resolve the claude binary via CAIRN_BENCH_CLAUDE_BIN, falling back to
       the real `claude` on PATH.
    4. Invoke `claude -p <prompt> --bare --output-format json --max-turns N
       --model claude-haiku --permission-mode acceptEdits
       --no-session-persistence`, cwd=workdir, capture_output=True,
       timeout=timeout_s.
    5. Parse stdout as JSON regardless of returncode; on parse failure or
       timeout, synthesize {"is_error": true, "parse_error": "..."}.
    6. Invoke <task-dir>/verify.sh <workdir>; verify_passed = (returncode==0).
    7. Append one JSON line to --out: task_id, wall_clock_ms, payload fields,
       verify_passed.
    8. rmtree(workdir).

Exit codes:
    0  run completed (regardless of verify_passed or is_error — a run's
       outcome is a data column, not a harness failure)
    2  usage error
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

USAGE = "usage: bench-run.py --task <task-dir> --out <jsonl-path>"


def die(msg, code):
    print(f"[bench-run] error: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_claude_bin():
    return os.environ.get("CAIRN_BENCH_CLAUDE_BIN") or shutil.which("claude") or "claude"


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
            if i + 1 >= len(argv):
                die(f"--out needs a value\n{USAGE}", EXIT_USAGE)
            opts["out"] = argv[i + 1]
            i += 2
        else:
            die(f"unknown option '{arg}'\n{USAGE}", EXIT_USAGE)
    if opts["task"] is None or opts["out"] is None:
        die(f"--task and --out are both required\n{USAGE}", EXIT_USAGE)
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

    workdir = tempfile.mkdtemp(prefix="cairn-bench-")
    try:
        shutil.copytree(task_dir / "fixture", workdir, dirs_exist_ok=True)
        cmd = [resolve_claude_bin(), "-p", prompt_text,
               "--bare", "--output-format", "json",
               "--max-turns", str(task["max_turns"]),
               "--model", "claude-haiku",
               "--permission-mode", "acceptEdits",
               "--no-session-persistence"]
        start = time.time()
        try:
            proc = subprocess.run(cmd, cwd=workdir, capture_output=True,
                                  text=True, timeout=task["timeout_s"])
        except subprocess.TimeoutExpired:
            wall_ms = int((time.time() - start) * 1000)
            payload = {"is_error": True,
                       "parse_error": f"timeout after {task['timeout_s']}s"}
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
        row = {"task_id": task["id"], "wall_clock_ms": wall_ms, **payload,
               "verify_passed": verify_proc.returncode == 0}
        with open(out_path, "a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
