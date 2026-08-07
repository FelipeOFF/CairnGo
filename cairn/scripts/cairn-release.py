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

NO FIELD HERE SAYS "CORRECT", BECAUSE NOTHING HERE CAN KNOW (FIX-03)
---------------------------------------------------------------------
MEASURED live, with the CHANGELOG already at 1.5.0 and both manifests still at
1.4.2, against the version of this file that carried the defect:

    marketplace  1.4.2 (the OLD version)    ->  status: ok
    changelog    1.5.0 (the only correct)   ->  status: mismatch

The top-level verdict, the finding text and exit 6 were all right — the gate
never lied. The per-carrier field did: comparisons run against present[0], so
`status` MEANT "agrees with the first readable lockstep carrier" while READING
as "this file is correct". A consumer filtering `status == "mismatch"` to learn
what to fix would have been sent to the file that was already right.

Deriving the answer from the MAJORITY was rejected by that same measurement:
two carriers at 1.4.2 against one at 1.5.0 makes the majority accuse the
changelog too. Majority is not correctness, it is a second guess with a better
name. Which version was INTENDED is not a fact this repository holds, so the
payload answers what it measured and names its yardstick:

    status                  a fact about this carrier ALONE — `ok` (a valid
                            semver string was read), `missing`, `invalid json`,
                            `invalid semver`; on the `tag` entry also
                            `pending` and `skipped`. `mismatch` is NOT one of
                            them: "does not match" is a statement about a pair.
    agrees_with_reference   true / false for the lockstep carriers that were
                            actually compared; null when no comparison
                            happened — an unreadable carrier, the own-axis
                            carrier, the tag when it was not consulted. null
                            rather than false, for the same reason the readers
                            above return None rather than "": a comparison
                            that did not happen is not a disagreement.
    reference (top level)   the carrier the comparison ran against, by name.
                            A YARDSTICK, never a verdict — it is simply the
                            first readable lockstep carrier.

`mismatch` remains a FINDING token, which is where it belongs: a finding names
two paths, two keys and two values, and is a claim about the pair.

The git tag
-----------
The fourth lockstep carrier. It is only consulted once the three file carriers
agree on a version (with nothing to look up, a tag query is noise). An absent
tag is reported `pending` and is NOT a failure by default — creating it is a
later plan's step. `--require-tag` promotes that absence to a finding, which is
how the plan that DOES create the tag proves the fourth equality.

notes: derived, never written a second time (REL-03)
-----------------------------------------------------
`notes <version>` prints the release notes for one CHANGELOG section on
stdout. It exists because this repository used to carry THREE texts for one
release — the CHANGELOG section, the annotated tag's message, and the body of
the published release — and keeping them in agreement was manual discipline.
Two sources of truth for what shipped diverge, and the published one is the
one users read. Here there is one derivation with three consumers.

The rule is fixed and deliberately dumb. The command never writes prose; it
cuts and labels:

    1. Find `## [<version>] - <date>`, cut to the next version heading,
       exclusive (end of file also ends the cut, for the oldest section).
    2. Print `## Am I affected?` and then the migration subsection's body,
       LITERAL.
    3. Print `## What changed` and then the rest of the section — the section
       preamble first, then every other subsection in the order it appears,
       LITERAL, with its own `###` heading preserved.

Step 2 before step 3 is the order of the three published releases: they open
with the user's question and leave the change list for last. Keep a Changelog's
order is the other one, and it is the right one for the FILE — which is why the
derivation reorders instead of demanding the CHANGELOG be written in release
order. Reordering and labelling is deterministic; rewriting would not be, and
`tests/cairn-release.bats` pins the whole output byte for byte so any
normalisation, reflow or rewrite on this path turns red.

A section with NO migration subsection exits 6. That is what makes publishing
a release that cannot answer "what do I have to do?" mechanically impossible
instead of a reminder — the three 1.4.x releases exist precisely because that
question went unanswered.

MEASURED on this repo's CHANGELOG.md when `notes` was written (`awk` over the
real file, not assumed):

    ## [1.5.0]  ->  ### Added, ### Fixed, ### Upgrading
    ## [1.4.2]  ->  ### Added
    ## [1.4.1]  ->  ### Fixed
    ## [1.4.0]  ->  ### Added, ### Changed, ### Added, ### Removed

So 1.5.0 is the only section `notes` can currently derive; `notes 1.4.2` exits
6, which is correct behaviour and not a bug. Note also that 1.4.0 repeats
`### Added`: duplicate headings are kept, in order, untouched.

ASSUMED, and deliberately so: that the migration subsection is spelled
`### Upgrading`. One spelling, no alias list — an alias nobody tested is a
second way to be wrong. Rename it in the CHANGELOG and this constant moves
with it.

Usage:
    cairn-release.py check [--project-dir DIR] [--json] [--require-tag]
    cairn-release.py notes VERSION [--project-dir DIR]

    --project-dir DIR   project root the carriers are resolved against
                        (default: $CLAUDE_PROJECT_DIR or cwd)
    --json              machine-readable report instead of the human lines
                        (check only)
    --require-tag       an absent `v<version>` git tag becomes a finding
                        instead of the default `pending`

Finding tokens (stable — the tests grep these, so they are contract):
    mismatch        two lockstep carriers disagree; the finding names both
                    paths, both keys and both values
    invalid semver  a carrier's value is not valid semver
    missing         a carrier's file, its key, or (with --require-tag) the git
                    tag is absent; the finding names the file AND the key.
                    `notes` reuses this token for a CHANGELOG section that does
                    not exist and for one with no migration subsection — both
                    name the version they were asked for
    invalid json    a carrier's file exists but does not parse
    pending         the `v<version>` git tag does not exist yet; reported, not
                    a finding, unless --require-tag was passed

Exit codes:
    0  check: every lockstep carrier agrees, every carrier is valid semver,
       and the tag is either present or (without --require-tag) merely
       pending. notes: the section was found and printed with its migration
       answer.
    2  usage error (unknown subcommand, bad flag, `notes` with no version)
    6  at least one finding — a mismatch, an invalid semver, a missing/
       unparsable carrier, an absent tag under --require-tag, or (notes) a
       CHANGELOG section that does not exist or carries no migration answer
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

# A Keep a Changelog subsection inside one version's section.
SUBSECTION_HEADING = re.compile(r"^###\s+(.*\S)\s*$")

# A fenced code block's delimiter. Both heading scans honour fences, so a
# CHANGELOG entry that quotes a markdown heading inside ``` cannot cut a
# section in half.
FENCE = re.compile(r"^\s*(?:```|~~~)")

# The one spelling of the migration subsection (see the docstring: one
# spelling, no alias list). Compared case-insensitively.
MIGRATION_HEADING = "Upgrading"

# The two labels the derivation adds. They are the ONLY text `notes` writes;
# everything else is cut from the CHANGELOG unchanged.
NOTES_MIGRATION_TITLE = "## Am I affected?"
NOTES_CHANGES_TITLE = "## What changed"

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
         "[--require-tag] | cairn-release.py notes VERSION "
         "[--project-dir DIR]")

CHANGELOG = "CHANGELOG.md"


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
    finding (if any).

    `status` is a fact about THIS carrier alone and nothing else — see the
    module docstring's "two questions" note. `agrees_with_reference` starts
    None and is answered by cmd_check for the lockstep carriers it actually
    compares; None means no comparison happened, which is not the same
    sentence as False."""
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
                    "agrees_with_reference": None,
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
    #
    # That reference is a YARDSTICK, never a verdict (FIX-03). It is named in
    # the payload so nobody has to infer it from ordering, and the comparison
    # it produces lives in its own field rather than inside `status`.
    version = None
    reference = None
    if present:
        ref = present[0]
        reference = ref["name"]
        version = ref["value"]
        ref["agrees_with_reference"] = True
        for c in present[1:]:
            c["agrees_with_reference"] = c["value"] == ref["value"]
            if not c["agrees_with_reference"]:
                findings.append(
                    f"mismatch: {ref['path']} ('{ref['key']}') = "
                    f"'{ref['value']}' but {c['path']} ('{c['key']}') = "
                    f"'{c['value']}'")

    agreed = (len(present) == len(lockstep)
              and all(c["value"] == version for c in present))

    # The tag is only consulted once the file carriers agree — with no single
    # version to look up, a tag query answers a question nobody asked.
    tag_entry = {"name": "tag", "path": "git", "key": None, "value": None,
                 "rule": "lockstep", "status": "skipped",
                 "agrees_with_reference": None, "finding": None}
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
            "reference": reference,
            "carriers": [{k: c[k] for k in
                          ("name", "path", "key", "value", "rule", "status",
                           "agrees_with_reference")}
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
# notes — one derivation, three consumers (REL-03)
# --------------------------------------------------------------------------- #
def cut_section(text, version):
    """(section body lines, finding) for one `## [version] - date` section.

    The cut ends at the NEXT version heading, exclusive — not at end of file,
    which would let every older release leak into the notes. End of file ends
    the cut only for the oldest section. Headings inside a fenced code block
    are not headings."""
    lines = text.splitlines()
    start = None
    end = len(lines)
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = CHANGELOG_HEADING.match(line)
        if not m:
            continue
        if start is None:
            if m.group(1).strip() == version:
                start = i
            continue
        end = i
        break
    if start is None:
        return None, (f"missing: {CHANGELOG} has no '## [{version}]' section "
                      f"— nothing to derive release notes from")
    return lines[start + 1:end], None


def split_subsections(section):
    """(preamble lines, [[heading line, title, body lines], ...]).

    Everything before the first `###` is the preamble; each `###` opens a
    subsection that runs to the next one. Duplicate titles are kept, in order
    — this repo's [1.4.0] section carries `### Added` twice."""
    preamble = []
    subs = []
    body = preamble
    in_fence = False
    for line in section:
        if FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            m = SUBSECTION_HEADING.match(line)
            if m:
                subs.append([line, m.group(1).strip(), []])
                body = subs[-1][2]
                continue
        body.append(line)
    return preamble, subs


def trim_blank(lines):
    """The lines with leading and trailing blank lines dropped. Interior lines
    are untouched — indentation, code fences and blank lines inside a block
    all survive, because the notes are cut, never reflowed."""
    out = list(lines)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def block(lines):
    """One output block: the trimmed lines, joined, and NOTHING else. Every
    block in the notes goes through here, so this is the single place a
    normalisation could be slipped in — and the golden test in
    tests/cairn-release.bats is what stops it."""
    return "\n".join(trim_blank(lines))


def cmd_notes(args, root):
    path = root / CHANGELOG
    if not path.is_file():
        die(f"missing: {CHANGELOG} does not exist under {root}", EXIT_FINDINGS)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        die(f"missing: {CHANGELOG} could not be read: {e}", EXIT_FINDINGS)

    section, finding = cut_section(text, args.version)
    if finding:
        die(finding, EXIT_FINDINGS)

    preamble, subs = split_subsections(section)
    wanted = MIGRATION_HEADING.lower()
    migration = next((s for s in subs if s[1].lower() == wanted), None)
    # An absent OR empty migration subsection is the same failure: the release
    # would go out unable to answer what the reader has to do, which is the
    # question the whole 1.4.x line existed to answer (REL-04).
    if migration is None or not trim_blank(migration[2]):
        die(f"missing: the [{args.version}] section of {CHANGELOG} has no "
            f"'### {MIGRATION_HEADING}' content — a release that cannot say "
            f"what the reader must do is not publishable", EXIT_FINDINGS)

    blocks = [NOTES_MIGRATION_TITLE, block(migration[2]), NOTES_CHANGES_TITLE]
    if trim_blank(preamble):
        blocks.append(block(preamble))
    for heading, title, body in subs:
        if title.lower() == wanted:
            continue
        kept = block(body)
        blocks.append(heading if not kept else heading + "\n\n" + kept)
    print("\n\n".join(blocks))
    sys.exit(EXIT_OK)


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
    check.add_argument("--json", action="store_true",
                       help="machine-readable JSON report")
    check.set_defaults(func=cmd_check)

    notes = sub.add_parser(
        "notes",
        help="derive one release's notes from its CHANGELOG section")
    notes.add_argument("version",
                       help="the version whose '## [x.y.z]' section is "
                            "derived (exit 6 if it does not exist)")
    notes.set_defaults(func=cmd_notes)

    for p in (check, notes):
        p.add_argument("--project-dir", metavar="DIR",
                       help="project root the carriers are resolved against "
                            "(default: $CLAUDE_PROJECT_DIR or cwd)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    root = resolve_root(args.project_dir)
    args.func(args, root)


if __name__ == "__main__":
    main()
