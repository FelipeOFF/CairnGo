#!/usr/bin/env python3
"""cairn-capability — install the cairn GSD capability and PROVE it registered.

The cairn capability is what fuses the two loops: with it registered, plain
/gsd:plan-phase, /gsd:execute-phase, /gsd:verify-work and /gsd:ship link,
claim, close and gate bd issues without the /cairn:* wrappers. Without it the
wrappers still work but the fusion the plugin is built around does not exist.

This script exists because that failure used to be silent. /cairn:init ran

    "$GSD_BIN" capability install ... --yes \\
      || "$GSD_BIN" capability update cairn ... --yes \\
      || echo "capability install skipped"

and the trailing echo turned every failure into exit 0. On the gsd 4.x
distribution there is no 'capability' subcommand at all, so BOTH attempts
exit 1 and the echo swallowed it: the install never happened and init said
nothing. Attempting is not installing — this script verifies.

Usage:
    cairn-capability.py detect  [--project-dir <dir>] [--gsd-bin <path>]
                                [--json]
    cairn-capability.py install [--project-dir <dir>] [--gsd-bin <path>]
                                [--capability-dir <dir>] [--json]

Commands:
    detect   Read-only. Report which GSD lineage is installed, whether it
             supports capabilities at all, and whether cairn is registered
             and completely staged. Never writes.
    install  Install (or update) the bundle, then run the same verification
             detect does. A verification that does not pass is a FAILURE
             with a stated remedy, never a shrug.

Lineage is one of:
    gsd-core  the official open-gsd/gsd-core line — 'capability' exists.
    legacy    the jnuyens/gsd-plugin 4.x line — no 'capability' subcommand,
              so the fusion CANNOT be installed. Reported as a failure with
              the upgrade command, because on this lineage cairn silently
              delivers half of what it promises.
    unknown   a GSD binary answered, but neither shape was recognised.

Registration is proven by two independent checks, both required:
    1. 'capability list' contains an entry with id 'cairn' whose status is
       'active'. This is GSD's own view of the world.
    2. The staged bundle on disk carries capability.json AND every script
       the manifest's gates reference — specifically
       scripts/cairn-loop-gate.sh. Check 2 is not redundant: the ship gate
       predicate is written 'test -f <gate script> || exit 0', so a bundle
       staged without its scripts leaves a gate that passes vacuously. A
       gate that cannot fail is worse than no gate, and only a filesystem
       check catches it.

Exit codes:
    0  ok — capability registered and completely staged (or, for detect,
       the report was produced; detect exits 7 when it finds the capability
       missing so callers can branch on it).
    2  usage error.
    5  GSD unavailable — no gsd_run/gsd on PATH and no --gsd-bin. Callers
       that treat GSD as optional may ignore this; /cairn:init reports it.
    7  FAILURE — legacy lineage, install failed, or the install did not
       register. stderr carries what to do about it.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_GSD = 5
EXIT_FAILED = 7

USAGE = (
    "usage: cairn-capability.py detect|install|repair-manifest\n"
    "       [--project-dir <dir>] [--gsd-bin <path>] [--capability-dir <dir>]\n"
    "       [--json]"
)

CAPABILITY_ID = "cairn"

# Files the staged bundle must carry for the capability to actually work.
# cairn-loop-gate.sh is load-bearing: the ship gate predicate no-ops when it
# is absent, so a bundle missing it yields a gate that can never block.
REQUIRED_STAGED = ("capability.json", "scripts/cairn-loop-gate.sh")

# --------------------------------------------------------------------------- #
# The gsd-core manifest defect (upstream open-gsd/gsd-core, 1.7.0 and 1.8.0)
#
# gsd-core's .claude-plugin/plugin.json declares
#
#     "hooks": "./hooks/hooks.json"
#
# but Claude Code loads that standard path automatically. The declaration is
# therefore a duplicate, and the loader does not merely skip the hooks — it
# refuses the WHOLE plugin:
#
#     Status: ✘ failed to load
#     Error: Hook load failed: Duplicate hooks file detected: ./hooks/hooks.json
#
# So a user who follows cairn's own migration guide installs gsd-core and gets
# no /gsd:* commands at all. The gsd-tools CLI still works, which is why the
# capability install succeeds and hides how bad this is.
#
# Upstream has the one-line fix already written (open-gsd/gsd-core#2077); it was
# auto-closed twelve seconds after opening because the project requires a
# maintainer-approved issue before any PR, and no such issue exists. The line is
# still present on main, next and v1.8.0.
#
# cairn removes that one line from the INSTALLED copy rather than forking
# gsd-core: users keep receiving genuine upstream code, there is no 41 MB vendored
# tree to rebase against a weekly release cadence, and the repair becomes a no-op
# the moment upstream drops the field.
# --------------------------------------------------------------------------- #

# Only the STANDARD path is redundant. A manifest pointing at ADDITIONAL hook
# files is using the field correctly and must never be touched.
STANDARD_HOOKS_PATHS = ("hooks/hooks.json", "./hooks/hooks.json")

# What the 4.x line prints when asked for a subcommand it does not have.
LEGACY_MARKER = "unknown command: capability"

UPGRADE_HINT = (
    "the installed GSD is the 4.x line (jnuyens/gsd-plugin), which has no "
    "'capability' subcommand — the cairn fusion cannot be installed on it.\n"
    "  Fix: install the official core, then reload:\n"
    "    claude plugin install gsd-core@cairngo\n"
    "    /reload-plugins\n"
    "  Until then /cairn:* commands and the cairn skill still work; plain "
    "/gsd:* will NOT touch bd issues."
)


def die(msg, code):
    print(f"[cairn-capability] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    opts = {
        "command": None,
        "project_dir": None,
        "gsd_bin": None,
        "capability_dir": None,
        "json": False,
    }
    if not argv:
        die(f"a command is required\n{USAGE}", EXIT_USAGE)
    opts["command"] = argv[0]
    if opts["command"] not in ("detect", "install", "repair-manifest"):
        die(f"unknown command '{opts['command']}'\n{USAGE}", EXIT_USAGE)
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("--project-dir", "--gsd-bin", "--capability-dir"):
            if i + 1 >= len(argv):
                die(f"{arg} needs a value\n{USAGE}", EXIT_USAGE)
            opts[arg[2:].replace("-", "_")] = argv[i + 1]
            i += 2
        elif arg == "--json":
            opts["json"] = True
            i += 1
        else:
            die(f"unknown argument '{arg}'\n{USAGE}", EXIT_USAGE)
    return opts


def resolve_project_dir(given):
    if given:
        return Path(given).resolve()
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env).resolve() if env else Path.cwd().resolve()


def resolve_capability_dir(given):
    """The bundle to install: --capability-dir, else the plugin's own copy."""
    if given:
        return Path(given).resolve()
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        cand = Path(env).resolve() / "capability"
        if cand.is_dir():
            return cand
    # scripts/ and capability/ are siblings inside the plugin.
    return (Path(__file__).resolve().parent.parent / "capability").resolve()


def _discovery_key(path):
    """Sort key for candidate GSD entry points, best first.

    Lineage outranks version, and deliberately so: the two lines version
    independently, so the legacy 4.x line would otherwise beat gsd-core 1.8.0
    on the number alone and cairn would report 'legacy' on a machine that has
    the official core installed. Within a lineage, newest wins
    ('1.10.0' > '1.9.0' — tuple compare, not string).
    """
    parts = Path(path).parts
    is_core = 1 if any(p == "gsd-core" for p in parts) else 0
    version = (0,)
    for part in reversed(parts):
        bits = part.split(".")
        if len(bits) >= 2 and all(b.isdigit() for b in bits):
            version = tuple(int(b) for b in bits)
            break
    return (is_core, version)


def _plugin_cache_roots():
    """Marketplace cache dirs to search for a GSD install.

    The plugin cache is laid out <cache>/<marketplace>/<plugin>/<version>/.
    cairn knows its own root via CLAUDE_PLUGIN_ROOT, so its sibling plugins
    live two levels up; the default cache location is searched as well for
    installs from a different marketplace.
    """
    roots = []
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        marketplace = Path(env).resolve().parent.parent  # <cache>/<marketplace>
        roots.append(marketplace)
        roots.append(marketplace.parent)
    roots.append(Path.home() / ".claude" / "plugins" / "cache")
    seen, out = set(), []
    for root in roots:
        key = str(root)
        if key not in seen and root.is_dir():
            seen.add(key)
            out.append(root)
    return out


def discover_gsd_bins():
    """Every plausible GSD entry point, newest first.

    PATH first (an explicitly exported gsd_run wins), then the plugin cache.
    gsd_run is a shim that gsd-core ships; the 4.x line has no gsd_run at all,
    only gsd-tools.cjs, so that is searched too — finding it is what lets the
    legacy lineage be REPORTED instead of mistaken for 'GSD not installed'.
    """
    found = []
    for name in ("gsd_run", "gsd"):
        hit = shutil.which(name)
        if hit:
            found.append(hit)
    globs = (
        "*/*/gsd-core/bin/gsd_run",   # <marketplace>/<plugin>/<ver>/gsd-core/bin
        "*/*/bin/gsd_run",
        "*/*/*/gsd-core/bin/gsd_run",
        "*/*/*/bin/gsd_run",
        "*/*/gsd-core/bin/gsd-tools.cjs",
        "*/*/bin/gsd-tools.cjs",
        "*/*/*/gsd-core/bin/gsd-tools.cjs",
        "*/*/*/bin/gsd-tools.cjs",
    )
    cached = []
    for root in _plugin_cache_roots():
        for pattern in globs:
            cached.extend(str(p) for p in root.glob(pattern) if p.is_file())
    cached.sort(key=_discovery_key, reverse=True)
    for hit in cached:
        if hit not in found:
            found.append(hit)
    return found


def find_gsd_bin(given):
    """--gsd-bin, else $CAIRN_GSD_BIN, else discovery.

    The env override exists because this check reads GLOBAL state (which GSD
    is installed on the machine) while everything else cairn does reads the
    repo. Without a seam, the doctor's verdict would depend on the developer's
    plugin cache and the same repo would report differently on two machines —
    untestable, and confusing to debug.
    """
    if not given:
        given = os.environ.get("CAIRN_GSD_BIN") or None
    if given:
        p = Path(given)
        if not p.is_file():
            die(f"--gsd-bin '{given}' is not a file", EXIT_USAGE)
        return str(p.resolve())
    bins = discover_gsd_bins()
    return bins[0] if bins else None


def run_gsd(gsd_bin, args, cwd):
    """Run a GSD subcommand; return (exit_code, stdout, stderr).

    A .cjs entry point is invoked through node — the 4.x line ships
    gsd-tools.cjs with no executable shim beside it.
    """
    argv = ["node", gsd_bin] if gsd_bin.endswith(".cjs") else [gsd_bin]
    try:
        proc = subprocess.run(
            [*argv, *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def list_capabilities(gsd_bin, project_dir):
    """(lineage, capabilities|None, detail).

    lineage: 'gsd-core' when the subcommand exists and answered with a JSON
    array, 'legacy' when the binary reports the subcommand is unknown,
    'unknown' otherwise.
    """
    code, out, err = run_gsd(gsd_bin, ["capability", "list"], project_dir)
    blob = f"{out}\n{err}".strip()
    if LEGACY_MARKER in blob.lower():
        return "legacy", None, "no 'capability' subcommand"
    if code != 0:
        return "unknown", None, (blob.splitlines() or ["no output"])[0][:200]
    try:
        parsed = json.loads(out)
    except (ValueError, TypeError):
        return "unknown", None, "'capability list' did not return JSON"
    if not isinstance(parsed, list):
        return "unknown", None, "'capability list' did not return a JSON array"
    return "gsd-core", parsed, f"{len(parsed)} capabilities registered"


def find_plugin_manifest(gsd_bin):
    """The .claude-plugin/plugin.json of the install that owns this binary.

    Walked up from the entry point rather than assumed, because the layout
    differs between the npm package, a git checkout and the plugin cache.
    """
    if not gsd_bin:
        return None
    for anc in list(Path(gsd_bin).resolve().parents)[:6]:
        cand = anc / ".claude-plugin" / "plugin.json"
        if cand.is_file():
            return cand
    return None


def manifest_defect(manifest_path):
    """(defective, detail) for the duplicate-standard-hooks defect.

    Narrow on purpose. The field is only redundant when it names the standard
    path AND that file exists; a manifest listing additional hook files is
    using it correctly and is left alone.
    """
    if manifest_path is None or not manifest_path.is_file():
        return False, "no plugin manifest found"
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"manifest unreadable ({exc})"
    if not isinstance(data, dict):
        return False, "manifest is not an object"
    declared = data.get("hooks")
    if not isinstance(declared, str):
        return False, "declares no hooks path"
    if declared.strip() not in STANDARD_HOOKS_PATHS:
        return False, f"declares additional hooks ({declared}) — left alone"
    if not (manifest_path.parent.parent / "hooks" / "hooks.json").is_file():
        return False, f"declares {declared}, which does not exist"
    return True, (f"declares the standard {declared}, which Claude Code loads "
                  "automatically — the plugin is refused as a duplicate")


def repair_manifest(manifest_path):
    """Drop the redundant hooks declaration. (changed, detail).

    Idempotent, and never touches anything else in the file: the manifest is
    re-serialised from the object it parsed, with one key removed.
    """
    defective, detail = manifest_defect(manifest_path)
    if not defective:
        return False, detail
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data.pop("hooks", None)
        keep_mode = manifest_path.stat().st_mode & 0o777
        tmp = manifest_path.with_name(manifest_path.name + ".cairn-tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        os.chmod(str(tmp), keep_mode)
        os.replace(str(tmp), str(manifest_path))
    except OSError as exc:
        return False, f"could not rewrite the manifest: {exc}"
    return True, "removed the redundant hooks declaration"


def staged_dir(project_dir):
    return project_dir / ".gsd" / "capabilities" / CAPABILITY_ID


def missing_staged_files(project_dir):
    """Required files absent from the staged bundle (empty == complete)."""
    root = staged_dir(project_dir)
    if not root.is_dir():
        return list(REQUIRED_STAGED)
    return [rel for rel in REQUIRED_STAGED if not (root / rel).is_file()]


def inspect(gsd_bin, project_dir):
    """Full read-only report. Never writes, never raises on a bad install."""
    lineage, caps, detail = list_capabilities(gsd_bin, project_dir)
    entry = None
    if caps is not None:
        for cap in caps:
            if isinstance(cap, dict) and cap.get("id") == CAPABILITY_ID:
                entry = cap
                break
    missing = missing_staged_files(project_dir)
    manifest = find_plugin_manifest(gsd_bin)
    defective, manifest_detail = manifest_defect(manifest)
    return {
        "gsd_bin": gsd_bin,
        "lineage": lineage,
        "lineage_detail": detail,
        "capability_command": lineage == "gsd-core",
        "registered": bool(entry) and entry.get("status") == "active",
        "capability": entry,
        "staged_dir": str(staged_dir(project_dir)),
        "staged_complete": not missing,
        "missing_staged": missing,
        # The installed GSD's own manifest. A plugin that will not load is a
        # bigger problem than a capability that will not register, and it is
        # invisible from inside the capability checks — the gsd-tools CLI keeps
        # working while Claude Code refuses the plugin.
        "plugin_manifest": str(manifest) if manifest else None,
        "manifest_loadable": not defective,
        "manifest_detail": manifest_detail,
    }


LABEL_WIDTH = 12


def _row(ok, label, detail):
    """One report row, columns aligned the way cairn-doctor aligns its checks."""
    return f" {'✓' if ok else '✗'} {label.ljust(LABEL_WIDTH)} {detail}"


def report_lines(info):
    """Human-readable report; the ✓/✗ vocabulary cairn-doctor uses."""
    lines = [
        _row(
            info["capability_command"],
            "lineage",
            f"{info['lineage']} — {info['lineage_detail']}",
        )
    ]
    if info["plugin_manifest"] and not info["manifest_loadable"]:
        lines.append(_row(False, "plugin load",
                          "gsd-core will NOT load — " + info["manifest_detail"]))
    if info["capability_command"]:
        cap = info["capability"]
        if info["registered"]:
            detail = (
                f"{CAPABILITY_ID} v{cap.get('version', '?')} "
                f"({cap.get('scope', '?')} scope, status {cap.get('status', '?')})"
            )
        elif cap:
            detail = f"present but status '{cap.get('status')}'"
        else:
            detail = "not in 'capability list'"
        lines.append(_row(info["registered"], "registered", detail))
        lines.append(
            _row(
                info["staged_complete"],
                "staged",
                info["staged_dir"]
                if info["staged_complete"]
                else "missing " + ", ".join(info["missing_staged"]),
            )
        )
    return lines


def failure_remedy(info):
    """What the operator should do, given a verification that did not pass."""
    if info["lineage"] == "legacy":
        return UPGRADE_HINT
    if info["lineage"] == "unknown":
        return (
            f"could not read the capability registry ({info['lineage_detail']}).\n"
            f"  Fix: check that '{info['gsd_bin']}' is a working GSD install, "
            "then re-run /cairn:init."
        )
    if not info["registered"]:
        return (
            "the capability did not register — 'capability list' does not "
            f"report '{CAPABILITY_ID}' as active.\n"
            "  Fix: re-run /cairn:init. If it keeps failing, a "
            "capabilities.strict_known_registries lockdown may be refusing "
            "third-party bundles; the cairn skill covers the same conventions "
            "conversationally in the meantime."
        )
    return (
        "the capability registered but its bundle is incomplete — missing "
        + ", ".join(info["missing_staged"])
        + f" under {info['staged_dir']}.\n"
        "  This matters: the ship gate no-ops when its script is absent, so "
        "the gate would pass without ever checking.\n"
        "  Fix: re-run /cairn:init to re-stage the bundle."
    )


def emit(info, opts, ok, remedy=None):
    if opts["json"]:
        payload = dict(info)
        payload["ok"] = ok
        if remedy:
            payload["remedy"] = remedy
        print(json.dumps(payload))
        return
    print(f"[cairn-capability] {opts['command']} — {info['gsd_bin']}")
    for line in report_lines(info):
        print(line)
    if ok:
        print("[cairn-capability] ok — the cairn ↔ GSD fusion is active")
    elif remedy:
        print(f"[cairn-capability] FAILED: {remedy}", file=sys.stderr)


def cmd_detect(opts, gsd_bin, project_dir):
    info = inspect(gsd_bin, project_dir)
    ok = info["registered"] and info["staged_complete"]
    emit(info, opts, ok, None if ok else failure_remedy(info))
    return EXIT_OK if ok else EXIT_FAILED


def cmd_repair_manifest(opts, gsd_bin, project_dir):
    """Make the installed gsd-core loadable again by dropping one line.

    Deliberately narrow: it removes a declaration that names the standard
    hooks path and nothing else. Runs before the capability install, because a
    plugin Claude Code refuses has no /gsd:* commands for the fusion to hook.
    """
    manifest = find_plugin_manifest(gsd_bin)
    changed, detail = repair_manifest(manifest)
    info = inspect(gsd_bin, project_dir)
    payload = dict(info)
    payload["repaired"] = changed
    payload["repair_detail"] = detail
    if opts["json"]:
        payload["ok"] = info["manifest_loadable"]
        print(json.dumps(payload))
    else:
        print(f"[cairn-capability] repair-manifest — {manifest or '(none)'}")
        if changed:
            print(f" ✓ repaired      {detail}")
            print(" ! run /reload-plugins for Claude Code to pick it up")
        else:
            mark = "✓" if info["manifest_loadable"] else "✗"
            print(f" {mark} manifest      {detail}")
    return EXIT_OK if info["manifest_loadable"] else EXIT_FAILED


def cmd_install(opts, gsd_bin, project_dir):
    # A plugin Claude Code refuses to load exposes no /gsd:* commands, so the
    # fusion has nothing to fuse. Clear that before installing the capability.
    repair_manifest(find_plugin_manifest(gsd_bin))
    lineage, _, detail = list_capabilities(gsd_bin, project_dir)
    if lineage != "gsd-core":
        info = inspect(gsd_bin, project_dir)
        emit(info, opts, False, failure_remedy(info))
        return EXIT_FAILED

    bundle = resolve_capability_dir(opts["capability_dir"])
    if not (bundle / "capability.json").is_file():
        die(
            f"no capability.json under '{bundle}' — pass --capability-dir",
            EXIT_USAGE,
        )

    attempts = [
        ["capability", "install", str(bundle), "--scope", "project", "--yes"],
        ["capability", "update", CAPABILITY_ID, "--scope", "project", "--yes"],
    ]
    last = ""
    for args in attempts:
        code, out, err = run_gsd(gsd_bin, args, project_dir)
        last = (err or out).strip()
        if code == 0:
            break

    # The install's own exit code is not the verdict — verification is.
    info = inspect(gsd_bin, project_dir)
    ok = info["registered"] and info["staged_complete"]
    remedy = None
    if not ok:
        remedy = failure_remedy(info)
        if last:
            remedy += f"\n  Last output from GSD: {last.splitlines()[0][:300]}"
    emit(info, opts, ok, remedy)
    return EXIT_OK if ok else EXIT_FAILED


def main():
    opts = parse_args(sys.argv[1:])
    project_dir = resolve_project_dir(opts["project_dir"])
    gsd_bin = find_gsd_bin(opts["gsd_bin"])
    if not gsd_bin:
        msg = (
            "no GSD binary on PATH (looked for gsd_run, gsd). GSD ships as a "
            "declared dependency of cairn — install it and reload:\n"
            "    claude plugin install gsd-core@cairngo\n"
            "    /reload-plugins"
        )
        if opts["json"]:
            print(json.dumps({"ok": False, "gsd_bin": None,
                              "lineage": "absent", "remedy": msg}))
            sys.exit(EXIT_NO_GSD)
        die(msg, EXIT_NO_GSD)

    if opts["command"] == "detect":
        sys.exit(cmd_detect(opts, gsd_bin, project_dir))
    if opts["command"] == "repair-manifest":
        sys.exit(cmd_repair_manifest(opts, gsd_bin, project_dir))
    sys.exit(cmd_install(opts, gsd_bin, project_dir))


if __name__ == "__main__":
    main()
