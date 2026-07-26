#!/usr/bin/env python3
"""stage-plugins — materialize the pinned, pre-built plugin sources that a
baseline manifest's provisioning.plugin_dirs entries declare.

Usage:
    stage-plugins.py --baseline <manifest.json> [--baseline <manifest.json> ...]
    stage-plugins.py --all

Behavior:
    1. Collect manifests: every --baseline path given (the flag is
       repeatable), or with --all every benchmarks/baselines/*.json relative
       to the cwd.
    2. Load + validate each manifest with the same parse-then-required-keys
       shape as bench-run.py's load_baseline() (name, model, claude_flags,
       provisioning.plugin_dirs). Deliberately duplicated: this pre-flight
       staging step and the runner are separate entry points, each validating
       its own input.
    3. For each provisioning.plugin_dirs entry:
       - local_path source: verify staged_path is an existing directory
         (already in-repo, nothing to fetch); fail loud naming the plugin.
       - git source: if staged_path already exists and its .staged-ref marker
         matches the pinned ref, skip (idempotent — no re-clone, no
         re-build). Otherwise clone --branch <ref> --depth 1 into a sibling
         temp dir, run every build command there, syntax-check any
         node-command MCP server entrypoint declared by the plugin's own
         .claude-plugin/plugin.json (node --check only — the server is never
         started), write .staged-ref, then atomically rename the temp dir
         onto staged_path. A failed or interrupted attempt never leaves
         anything at staged_path that looks complete.
    4. Print one summary line per manifest:
       [stage-plugins] <name>: N plugin(s) staged/verified

Staging is a one-time, out-of-band step: a benchmarked claude invocation must
never absorb a lazy npm install into its measured wall-clock/cost.

Exit codes:
    0  every plugin_dirs entry across every requested manifest staged/verified
    2  usage error, or the first staging/build/verification failure (loud,
       attributed to the specific plugin and step)
"""
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2

USAGE = ("usage: stage-plugins.py --baseline <manifest.json> "
         "[--baseline <manifest.json> ...] | --all")

BASELINES_GLOB_DIR = Path("benchmarks/baselines")


def die(msg, code):
    print(f"[stage-plugins] error: {msg}", file=sys.stderr)
    sys.exit(code)


def load_baseline(path):
    """Parse + validate a baseline manifest; die(EXIT_USAGE) on any defect.

    Same parse-then-required-keys shape as bench-run.py's load_baseline(),
    minus the staged_path existence check — creating those paths is exactly
    this script's job, while verifying them per-invocation is the runner's.
    """
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
    return manifest


def run_step(plugin, step, cmd, cwd=None):
    """subprocess.run(check=True) wrapper: every failure is loud, non-zero,
    and attributed to the specific plugin/step. cmd is always an argv list,
    never a string handed to a shell."""
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        die(f"staging '{plugin}' failed at step '{step}': {e}", EXIT_USAGE)


def check_mcp_server_syntax(plugin, tree):
    """node --check every node-command MCP server entrypoint the staged
    plugin's own .claude-plugin/plugin.json declares. Syntax-only sanity
    check: never starts the server, never blocks on stdio."""
    plugin_json = tree / ".claude-plugin" / "plugin.json"
    if not plugin_json.is_file():
        return
    try:
        meta = json.loads(plugin_json.read_text())
    except json.JSONDecodeError as e:
        die(f"staging '{plugin}' failed at step 'plugin.json parse': {e}",
            EXIT_USAGE)
    for server_name, server in meta.get("mcpServers", {}).items():
        if server.get("command") != "node":
            continue
        args = server.get("args", [])
        if not args:
            continue
        entry = args[0].replace("${CLAUDE_PLUGIN_ROOT}", str(tree))
        run_step(plugin, f"node --check ({server_name})",
                 ["node", "--check", entry])


def stage_entry(entry):
    """Stage/verify one provisioning.plugin_dirs entry; die(EXIT_USAGE) on
    any failure."""
    plugin = entry["plugin"]
    source = entry["source"]
    staged = Path(entry["staged_path"])

    if source["type"] == "local_path":
        if not staged.is_dir():
            die(f"plugin '{plugin}' local_path staged_path not found: {staged}",
                EXIT_USAGE)
        print(f"[stage-plugins] {plugin} is a local_path at {staged}, verified")
        return

    if source["type"] != "git":
        die(f"plugin '{plugin}' has unknown source type '{source['type']}'",
            EXIT_USAGE)

    ref = source["ref"]
    marker = staged / ".staged-ref"
    if staged.is_dir() and marker.is_file() and marker.read_text().strip() == ref:
        print(f"[stage-plugins] {plugin} already staged at {ref}, skipping")
        return

    # Stale, partial, or ref-mismatched checkout: rebuild from scratch.
    shutil.rmtree(staged, ignore_errors=True)
    staged.parent.mkdir(parents=True, exist_ok=True)
    # Clone into a SIBLING temp dir (same filesystem), rename on success:
    # a failed attempt never leaves something at staged_path that looks
    # complete.
    tmp = Path(tempfile.mkdtemp(prefix=".staging-", dir=staged.parent))
    try:
        run_step(plugin, "git clone",
                 ["git", "clone", "--branch", ref, "--depth", "1",
                  f"https://github.com/{source['repo']}.git", str(tmp)])
        for build_cmd in entry.get("build", []):
            run_step(plugin, build_cmd, shlex.split(build_cmd), cwd=tmp)
        check_mcp_server_syntax(plugin, tmp)
        # Only once every step above succeeded: marker, then atomic rename.
        (tmp / ".staged-ref").write_text(ref)
        shutil.move(str(tmp), str(staged))
        print(f"[stage-plugins] {plugin} staged at {ref} -> {staged}")
    finally:
        # No-op after a successful move; removes the partial tree when any
        # step die()d (die raises SystemExit, so finally still runs).
        shutil.rmtree(tmp, ignore_errors=True)


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
        else:
            die(f"unknown option '{arg}'\n{USAGE}", EXIT_USAGE)
    if not opts["baselines"] and not opts["all"]:
        die(f"at least one --baseline (or --all) is required\n{USAGE}",
            EXIT_USAGE)
    return opts


def main():
    opts = parse_args(sys.argv[1:])
    paths = list(opts["baselines"])
    if opts["all"]:
        found = sorted(str(p) for p in BASELINES_GLOB_DIR.glob("*.json"))
        if not found:
            die(f"--all found no manifests under {BASELINES_GLOB_DIR}/",
                EXIT_USAGE)
        paths += found
    for path in paths:
        manifest = load_baseline(path)
        entries = manifest["provisioning"]["plugin_dirs"]
        for entry in entries:
            stage_entry(entry)
        print(f"[stage-plugins] {manifest['name']}: "
              f"{len(entries)} plugin(s) staged/verified")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
