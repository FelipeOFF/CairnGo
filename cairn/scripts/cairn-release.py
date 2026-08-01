#!/usr/bin/env python3
"""cairn-release — turns "the versions match" from something a human eyeballed
into an exit code.

Why this exists (REL-02): the roadmap for this phase said the version lives in
TWO files. It lives in THREE. `.claude-plugin/marketplace.json` carries it too,
at `metadata.version` — a DIFFERENT key path from the other two — and it went
unnoticed across three consecutive releases (1.4.0, 1.4.1, 1.4.2). Three
carriers at three different JSON paths is half the reason this command has to
exist: the eyeball check already failed here, in public, three times.

MEASURED on this repo at the time this script was written (not assumed — every
number below came from `jq` against the real files, and the exact key paths are
the ones that answered):

    cairn/.claude-plugin/plugin.json      .version            = 1.4.2
    .claude-plugin/marketplace.json       .metadata.version   = 1.4.2   (nested)
    CHANGELOG.md                          ## [1.4.2] - ...    = 1.4.2
    cairn/capability/capability.json      .version            = 1.0.0
    git tag v1.4.2                                            = present

ASSUMED, and deliberately so: nothing about the CHANGELOG beyond Keep a
Changelog's `## [x.y.z] - date` heading shape, which this repo already follows.

The two rules, which are NOT the same rule (Phase 19, D-02)
----------------------------------------------------------
    plugin.json  ==  marketplace.json  ==  CHANGELOG head  ==  git tag
    capability.json  ->  its own axis; must only be VALID SEMVER

`cairn/capability/capability.json` sits at 1.0.0 ON PURPOSE while the plugin
sits at 1.4.2. The capability is installed INSIDE gsd-core and keeps its own
release cycle. Folding it into the equality set would invent an equality that
does not exist — the same class of green-without-proof this whole milestone was
named after. The next person reading this file will assume the exemption is a
bug; it is not, and `tests/cairn-release.bats` pins BOTH halves: capability at
1.0.0 while the rest read 1.5.0 must exit 0, and capability at `1.0` must exit
6 saying `invalid semver`, never `mismatch`.

Semver validity is checked on EVERY carrier, lockstep members included. D-02
exempts capability.json from EQUALITY, not from validity — and without that,
three carriers all reading a malformed `1.4` would compare equal and pass.

The three-nothings trap
-----------------------
Every version is read by an EXPLICIT key path with no default. A `.get(key, "")`
would make three unreadable carriers compare equal as three empty strings and
report agreement — a green light that means the opposite of what it says. A
missing file, a missing key, a key holding a non-string, and malformed JSON are
each a finding that names the file AND the key, and each exits 6.

The git tag
-----------
The fourth lockstep carrier. It is only consulted once the three file carriers
agree on a version (with nothing to look up, a tag query is noise). An absent
tag is reported `pending` and is NOT a failure by default — creating it is a
later plan's step. `--require-tag` promotes that absence to a finding, which is
how the plan that DOES create the tag proves the fourth equality.

Usage:
    cairn-release.py check [--project-dir DIR] [--json] [--require-tag]

    --project-dir DIR   project root the carriers are resolved against
                        (default: $CLAUDE_PROJECT_DIR or cwd)
    --json              machine-readable report instead of the human lines
    --require-tag       an absent `v<version>` git tag becomes a finding
                        instead of the default `pending`

Finding tokens (stable — the tests grep these, so they are contract):
    mismatch        two lockstep carriers disagree; the finding names both
                    paths, both keys and both values
    invalid semver  a carrier's value is not valid semver
    missing         a carrier's file, its key, or (with --require-tag) the git
                    tag is absent; the finding names the file AND the key
    invalid json    a carrier's file exists but does not parse
    pending         the `v<version>` git tag does not exist yet; reported, not
                    a finding, unless --require-tag was passed

Exit codes:
    0  every lockstep carrier agrees, every carrier is valid semver, and the
       tag is either present or (without --require-tag) merely pending
    2  usage error (unknown subcommand, bad flag)
    6  at least one finding — a mismatch, an invalid semver, a missing/
       unparsable carrier, or an absent tag under --require-tag
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FINDINGS = 6

# The official semver.org recommended regex. `1.0` is NOT valid semver by it,
# which is exactly the capability.json case tests/cairn-release.bats pins.
SEMVER = re.compile(
    r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-(?:(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?:[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")

# Keep a Changelog's version heading. `## [Unreleased]` matches this too and is
# SKIPPED by read_changelog_version — it is not a released version.
CHANGELOG_HEADING = re.compile(r"^##\s+\[([^\]]+)\]")

PLUGIN_MANIFEST = "cairn/.claude-plugin/plugin.json"

# (name, path relative to the project root, key path, rule). The key paths
# differ per carrier ON PURPOSE — see the module docstring; marketplace.json
# nests it under `metadata`, which is what three releases of eyeballing missed.
CARRIERS = (
    ("plugin", PLUGIN_MANIFEST, ("version",), "lockstep"),
    ("marketplace", ".claude-plugin/marketplace.json",
     ("metadata", "version"), "lockstep"),
    ("changelog", "CHANGELOG.md", None, "lockstep"),
    ("capability", "cairn/capability/capability.json", ("version",),
     "own-axis"),
)

USAGE = ("usage: cairn-release.py check [--project-dir DIR] [--json] "
         "[--require-tag]")


def die(msg, code):
    print(f"[cairn-release] error: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_root(project_dir):
    if project_dir:
        return Path(project_dir).resolve()
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()


# --------------------------------------------------------------------------- #
# reading the carriers — explicit key paths, never a default
# --------------------------------------------------------------------------- #
def read_json_version(root, rel, keypath):
    """(value, finding) for one JSON carrier's version, read by EXPLICIT key
    path. Returns (None, finding) — never ("", None) — when the file is
    absent, unparsable, the key is absent, or the key holds anything but a
    non-empty string. A default-on-missing read here would let three
    unreadable carriers compare equal as three empty strings and report
    agreement (see the module docstring's three-nothings trap)."""
    dotted = ".".join(keypath)
    path = root / rel
    if not path.is_file():
        return None, f"missing: {rel} does not exist (expected key '{dotted}')"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"missing: {rel} could not be read: {e}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"invalid json: {rel} is not valid JSON: {e}"
    node = data
    for key in keypath:
        if not isinstance(node, dict) or key not in node:
            return None, f"missing: {rel} has no '{dotted}' key"
        node = node[key]
    if not isinstance(node, str) or not node.strip():
        return None, (f"missing: {rel}'s '{dotted}' key holds no version "
                      f"string ({node!r})")
    return node.strip(), None


def read_changelog_version(root, rel):
    """(value, finding) for the FIRST released version heading in a Keep a
    Changelog file. A `## [Unreleased]` heading above it is skipped — it is a
    staging area, not a version. Blindly taking the first `## [` would read
    'Unreleased' as the version and then report a mismatch against every
    manifest."""
    path = root / rel
    if not path.is_file():
        return None, (f"missing: {rel} does not exist (expected a "
                      f"'## [x.y.z]' heading)")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"missing: {rel} could not be read: {e}"
    for line in text.splitlines():
        m = CHANGELOG_HEADING.match(line)
        if not m:
            continue
        label = m.group(1).strip()
        if label.lower() == "unreleased":
            continue
        return label, None
    return None, (f"missing: {rel} has no '## [x.y.z]' version heading")


def git_tag_exists(root, tag):
    """True/False, or None when git itself could not answer (not installed,
    not a repo). Always an argument LIST, never shell=True (T-19-02)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "tag", "--list", tag],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return tag in proc.stdout.split()


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #
def collect_carriers(root):
    """[carrier dict] in CARRIERS order, each already carrying its own read
    finding (if any). Status is filled in by cmd_check."""
    out = []
    for name, rel, keypath, rule in CARRIERS:
        if keypath is None:
            value, finding = read_changelog_version(root, rel)
            key = "## [x.y.z] heading"
        else:
            value, finding = read_json_version(root, rel, keypath)
            key = ".".join(keypath)
        out.append({"name": name, "path": rel, "key": key, "value": value,
                    "rule": rule, "status": "ok" if finding is None else
                    ("invalid json" if finding.startswith("invalid json")
                     else "missing"),
                    "finding": finding})
    return out


def cmd_check(args, root):
    carriers = collect_carriers(root)
    findings = [c["finding"] for c in carriers if c["finding"]]

    # Semver validity — EVERY carrier, lockstep members included. D-02 exempts
    # capability.json from EQUALITY, never from validity.
    for c in carriers:
        if c["value"] is None:
            continue
        if not SEMVER.match(c["value"]):
            c["status"] = "invalid semver"
            findings.append(f"invalid semver: {c['path']} ('{c['key']}') = "
                            f"'{c['value']}' is not valid semver")

    lockstep = [c for c in carriers if c["rule"] == "lockstep"]
    present = [c for c in lockstep if c["value"] is not None]

    # Mismatches are reported against the first readable lockstep carrier, so
    # every finding names two paths, two keys and two values — a finding that
    # only said "the versions differ" would send the reader back to opening all
    # four files by hand, which is the work this command exists to delete.
    version = None
    if present:
        ref = present[0]
        version = ref["value"]
        for c in present[1:]:
            if c["value"] != ref["value"]:
                c["status"] = "mismatch"
                if ref["status"] == "ok":
                    ref["status"] = "mismatch"
                findings.append(
                    f"mismatch: {ref['path']} ('{ref['key']}') = "
                    f"'{ref['value']}' but {c['path']} ('{c['key']}') = "
                    f"'{c['value']}'")

    agreed = (len(present) == len(lockstep)
              and all(c["value"] == version for c in present))

    # The tag is only consulted once the file carriers agree — with no single
    # version to look up, a tag query answers a question nobody asked.
    tag_entry = {"name": "tag", "path": "git", "key": None, "value": None,
                 "rule": "lockstep", "status": "skipped", "finding": None}
    if agreed and version:
        tag = f"v{version}"
        tag_entry["key"] = tag
        exists = git_tag_exists(root, tag)
        if exists is True:
            tag_entry["value"] = tag
            tag_entry["status"] = "ok"
        elif exists is None:
            tag_entry["status"] = "skipped"
            tag_entry["finding"] = None
        else:
            tag_entry["status"] = "pending"
            if args.require_tag:
                tag_entry["status"] = "missing"
                msg = (f"missing: git tag {tag} does not exist "
                       f"(--require-tag)")
                tag_entry["finding"] = msg
                findings.append(msg)
    carriers.append(tag_entry)

    ok = not findings
    if args.json:
        print(json.dumps({
            "ok": ok,
            "version": version if agreed else None,
            "carriers": [{k: c[k] for k in
                          ("name", "path", "key", "value", "rule", "status")}
                         for c in carriers],
            "findings": findings,
        }))
    else:
        if ok:
            equal = ", ".join(c["path"] for c in lockstep)
            cap = next(c for c in carriers if c["name"] == "capability")
            tag_note = {
                "ok": f"git tag {tag_entry['key']} present",
                "pending": f"git tag {tag_entry['key']} pending (not created "
                           f"yet)",
                "skipped": "git tag not consulted",
            }[tag_entry["status"]]
            print(f"[cairn-release] ok — version {version} in {equal}; "
                  f"{tag_note}; capability {cap['value']} on its own axis "
                  f"(valid semver, D-02)")
        else:
            print(f"[cairn-release] {len(findings)} finding(s):")
            for f in findings:
                print(f"  {f}")
    sys.exit(EXIT_OK if ok else EXIT_FINDINGS)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        prog="cairn-release",
        description="Verify that every carrier of the cairn plugin version "
                    "agrees, and that the capability's own axis is valid "
                    "semver.")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser(
        "check", help="compare the version carriers and report disagreement")
    check.add_argument("--require-tag", action="store_true",
                       help="an absent v<version> git tag becomes a finding "
                            "instead of the default 'pending'")
    check.set_defaults(func=cmd_check)

    for p in (check,):
        p.add_argument("--project-dir", metavar="DIR",
                       help="project root the carriers are resolved against "
                            "(default: $CLAUDE_PROJECT_DIR or cwd)")
        p.add_argument("--json", action="store_true",
                       help="machine-readable JSON report")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    root = resolve_root(args.project_dir)
    args.func(args, root)


if __name__ == "__main__":
    main()
