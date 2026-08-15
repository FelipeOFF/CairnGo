#!/usr/bin/env python3
"""cairn-wrap — the /cairn:* wrappers: refuse when the GSD command is gone,
and derive the documented list from what is actually on disk.

WHY THIS EXISTS
---------------
Decision GSD-05 (2026-07-28) named thirteen gsd-core commands that earn a
/cairn:* wrapper, because running them changes work beads has to know about.
Two failure modes come free with wrappers, and both have already happened in
this codebase:

    1. A wrapper whose /gsd:* command is not installed exits 0 in silence.
       cairn-capability.py's docstring records the exact shape of this bug:
       an install line ending in `|| echo "capability install skipped"` turned
       every failure into a success, and the install never happened while
       nothing said so. `preflight` is the answer: attempting is not running.

    2. The documented list of wrappers is typed by hand and starts lying.
       Measured in this repository on 2026-08-05, before this script existed:
       cairn/docs/commands.md opened with "22 in total", linked 23 pages, and
       cairn/commands/ held 25 commands — /cairn:config and /cairn:reconcile
       existed, worked, and appeared nowhere. The same defect had already been
       fixed BY HAND two days earlier in cairn/docs/commands/doctor.md, which
       claimed "fifteen checks in total" with sixteen registered (commit
       8d3db19). A hand fix guarantees the next drift. `docs` is the answer:
       the page is a VIEW of the disk, not a second source.

Phase 37 pointed `preflight` at a different surface without changing why it
exists. cairn stopped depending on an external gsd-core plugin: the runtime is
vendored under the plugin's own `gsd/`. So the question moved from "is
/gsd:<command> installed on this machine?" to "does THIS PLUGIN carry an
implementation for <command>?" — same refusal, same exit codes, a target that
no longer depends on what else the operator happens to have installed.

Usage:
    cairn-wrap.py preflight <gsd-command> [--json]
    cairn-wrap.py list [--commands-dir <dir>] [--json]
    cairn-wrap.py docs [--check] [--commands-dir <dir>] [--doc <file>]
                       [--doc-pages-dir <dir>] [--json]

Commands:
    preflight   Is /gsd:<command> installed on THIS machine? Read-only. The
                first step of every wrapper, so a missing GSD command stops
                the wrapper instead of being discovered halfway through.
    list        Enumerate cairn's commands FROM DISK. A cairn/commands/*.md
                whose frontmatter carries `wraps:` implements a GSD verb; the
                value NAMES that verb, `wrap-family:` says which bookkeeping
                shape it follows, and `implementation:` says where the
                implementation lives (`vendored` under the plugin's gsd/, or
                `inline` in the command file itself). No list of wrapper names
                is written in this file — that list living in code would be
                the very defect `docs` exists to remove, moved one file over.
    docs        Regenerate the derived block inside the command reference,
                between the house markers. Everything outside them survives.
                Three kinds of gap are NAMED in the block rather than hidden:
                a command with no row (undocumented), a row whose page does
                not exist (missing page), and a page for no command (orphan).

Exit codes:
    0  ok — the command is installed / the block is current.
    2  usage — bad flags, an explicit --commands-dir or CAIRN_GSD_COMMANDS_DIR
       pointing at something that is not a directory, or an unknown
       wrap-family value in a command's frontmatter.
    3  stale (`docs --check` only) — the block on disk differs from what
       derivation produces; a unified diff goes to stdout. Same 3 = stale that
       cairn-map.py --check already established.
    5  GSD unavailable — COULD NOT LOOK: no GSD command surface was found at
       all, so whether the command exists is unknown.
    6  missing — LOOKED AND IT IS NOT THERE: a surface was found and it does
       not carry the named command.

    5 and 6 are two codes because they are two different facts for whoever is
    debugging, and the message differs accordingly. Both are failures for a
    wrapper. Note that 5 here deliberately does NOT inherit the "callers must
    NOT block on 5" rule the conventions record for `bd` in the pre-push shim:
    there, 5 is an optional check degrading; here the delegated command IS the
    whole job, and continuing would be the silent exit 0 this script exists to
    prevent.

MEASURED VERSUS ASSUMED
-----------------------
MEASURED (2026-08-12, phase 37, against this plugin's own vendored tree):
  - The vendored surface is `gsd/commands/gsd/*.md`, 8 files, and
    `gsd/gsd-core/workflows/*.md`, 8 files. Phase 32 cut the runtime closure
    at those eight verbs; nothing outside them is carried.
  - Of the thirteen commands decision GSD-05 named, exactly ONE
    (`discuss-phase`) has a vendored counterpart. The other twelve delegated
    to gsd-core commands this plugin does not carry — which is why phase 37
    made them implement inline and stop calling preflight. A command that
    declares `implementation: inline` and still preflights would be asserting
    a delegation that does not exist.
  - The guard still bites against the new target: `preflight spec-phase`
    exits 6 here, because `spec-phase` is not one of the eight. A preflight
    that cannot fail is the vacuous gate cairn-capability.py's docstring
    warns about, and the inversion did not create one.

MEASURED EARLIER (2026-08-05, against the external gsd-core Claude Code then
loaded — kept because it is the reason the seam exists at all):
  - That surface was `commands/gsd/*.md`, 71 files; the `gsd/` SUBDIRECTORY
    is what produces the /gsd: namespace. The vendored tree keeps the same
    shape, which is why the first candidate path did not have to change form.
  - gsd-core used eight distinct frontmatter keys across those files, and
    unknown keys are tolerated by the loader — which is why adding
    `wraps:`/`wrap-family:`/`implementation:` to a cairn command is safe.

ASSUMED (not measured):
  - That every install carries a complete `gsd/` tree. That assumption is
    exactly why `preflight` still exists after the inversion: exit 5 now
    means THIS PLUGIN is incomplete, which is a different fact from the one
    it used to report, and worth reporting for the same reason.

The frontmatter parser here is deliberately minimal — the `---` fenced block,
top-level `key: value` lines only. stdlib only, no YAML dependency: the same
hard constraint the rest of cairn/scripts/ runs under.
"""
import difflib
import json
import os
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
# 3 = stale, the same meaning cairn-map.py --check already gives it.
EXIT_STALE = 3
# 5 = could not look at all. NOT the "callers may ignore 5" kind — see the
# docstring's exit table: for a wrapper the delegated command is the whole job.
EXIT_NO_GSD = 5
# 6 = looked, and the command is not there. The WRAP-02 refusal.
EXIT_MISSING = 6

START_MARKER = "<!-- cairn:generated:start -->"
END_MARKER = "<!-- cairn:generated:end -->"
HEADER_LINE = "Generated by cairn-wrap — do not edit between markers"
SECTION_HEADING = "## Wrapped GSD commands"

# Closed vocabulary. An unknown value is a named usage error rather than a
# silently mis-grouped row: a typo'd family would otherwise produce a table
# section nobody asked for and nobody notices.
FAMILIES = ("phase", "structural", "milestone")

# Where a command's implementation actually lives (phase 37, PLUG-01). A closed
# vocabulary, checked like FAMILIES is: a typo must be a named usage error, not
# a silent "this is not a wrapper".
#   vendored  the plugin carries the implementation under gsd/; the command
#             preflights it and then delegates to the file.
#   inline    the command file IS the implementation. It does not preflight,
#             because there is nothing external to check and a preflight that
#             cannot fail is the vacuous gate this script exists to prevent.
IMPLEMENTATIONS = ("vendored", "inline")

FIX_LINE = ("the vendored GSD runtime under the plugin's gsd/ is missing "
            "or incomplete — reinstall cairn (claude plugin install "
            "cairn@cairngo), then /reload-plugins")

USAGE = (
    "usage: cairn-wrap.py preflight <gsd-command> [--json]\n"
    "       cairn-wrap.py list [--commands-dir <dir>] [--json]\n"
    "       cairn-wrap.py docs [--check] [--commands-dir <dir>] [--doc <file>]\n"
    "                          [--doc-pages-dir <dir>] [--json]"
)

DOC_LINK = re.compile(r"\./commands/([A-Za-z0-9._-]+)\.md")


def die(msg, code):
    print(f"[cairn-wrap] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    opts = {"command": None, "gsd_command": None, "commands_dir": None,
            "doc": None, "doc_pages_dir": None, "check": False, "json": False}
    if not argv:
        die(f"missing command\n{USAGE}", EXIT_USAGE)
    opts["command"] = argv[0]
    if opts["command"] not in ("preflight", "list", "docs"):
        die(f"unknown command '{opts['command']}'\n{USAGE}", EXIT_USAGE)
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("--commands-dir", "--doc", "--doc-pages-dir"):
            if i + 1 >= len(argv):
                die(f"{arg} needs a value\n{USAGE}", EXIT_USAGE)
            opts[arg[2:].replace("-", "_")] = argv[i + 1]
            i += 2
        elif arg == "--check":
            opts["check"] = True
            i += 1
        elif arg == "--json":
            opts["json"] = True
            i += 1
        elif arg.startswith("-"):
            die(f"unknown argument '{arg}'\n{USAGE}", EXIT_USAGE)
        elif opts["command"] == "preflight" and opts["gsd_command"] is None:
            opts["gsd_command"] = arg
            i += 1
        else:
            die(f"unexpected argument '{arg}'\n{USAGE}", EXIT_USAGE)
    if opts["command"] == "preflight" and not opts["gsd_command"]:
        die(f"preflight needs a gsd command name\n{USAGE}", EXIT_USAGE)
    if opts["command"] != "docs" and opts["check"]:
        die(f"--check is only meaningful for 'docs'\n{USAGE}", EXIT_USAGE)
    return opts


# ---------------------------------------------------------------------------
# Frontmatter (stdlib only, no YAML)
# ---------------------------------------------------------------------------

def read_frontmatter(path):
    """{key: value} for the top-level `key: value` lines of the --- block.

    Nested keys and lists are ignored on purpose: cairn's command files use
    flat scalars only, and a real YAML parser is not available under the
    stdlib-only constraint. A file without a leading `---` fence yields {}.
    """
    out = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line or line[0] in " \t-#":
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


# ---------------------------------------------------------------------------
# Discovery: where the GSD command surface lives
# ---------------------------------------------------------------------------

def _plugin_root():
    """The plugin's own root — CLAUDE_PLUGIN_ROOT, or this script's grandparent.

    scripts/ and gsd/ are siblings inside the plugin, so the fallback resolves
    from __file__ and works when the repo is used directly (tests, development)
    with no plugin cache in play at all.
    """
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def find_gsd_command_dir():
    """(dir | None, searched) — the VENDORED GSD surface, and every path tried.

    Phase 37 turned this around. It used to sweep installed_plugins.json and
    the marketplace cache for an EXTERNAL gsd-core install, because that is
    where the delegated commands lived. cairn no longer has an external GSD:
    the runtime is vendored under the plugin's own gsd/, so the only honest
    place to look is inside the plugin.

    The seam is CAIRN_GSD_COMMANDS_DIR and it SURVIVES the inversion. It was
    introduced because the old lookup read global machine state and the same
    repo answered differently on two machines; the new lookup reads the
    plugin, but tests still need to point it at a fixture without staging a
    whole plugin tree.

    A seam pointing at a non-directory is a USAGE error, not "not found":
    degrading there would hide a mis-wired test instead of naming it.
    """
    searched = []
    env = os.environ.get("CAIRN_GSD_COMMANDS_DIR")
    if env:
        cand = Path(env)
        if not cand.is_dir():
            die(f"CAIRN_GSD_COMMANDS_DIR '{env}' is not a directory",
                EXIT_USAGE)
        searched.append(f"CAIRN_GSD_COMMANDS_DIR={env} (used)")
        return cand, searched
    searched.append("CAIRN_GSD_COMMANDS_DIR (unset)")

    # `gsd/commands/gsd` before `gsd/gsd-core/workflows`: MEASURED 2026-08-12,
    # the vendored tree carries 8 command files in the first and 8 workflow
    # files in the second, and the command file is the one a /gsd: namespace
    # verb resolves to. The workflow dir is searched second because four of
    # the eight verbs are reachable only through it.
    root = _plugin_root()
    candidates = [root / "gsd" / "commands" / "gsd",
                  root / "gsd" / "gsd-core" / "workflows"]
    for cand in candidates:
        if cand.is_dir() and any(cand.glob("*.md")):
            searched.append(f"{cand} (used)")
            return cand, searched
        searched.append(f"{cand} (absent or empty)")
    return None, searched


def surface_commands(dirpath):
    return sorted(p.stem for p in dirpath.glob("*.md"))


# ---------------------------------------------------------------------------
# preflight — WRAP-02
# ---------------------------------------------------------------------------

def do_preflight(opts):
    name = opts["gsd_command"]
    dirpath, searched = find_gsd_command_dir()

    if dirpath is None:
        payload = {"command": name, "installed": False, "surface": None,
                   "surface_command_count": 0, "searched": searched,
                   "exit": EXIT_NO_GSD}
        if opts["json"]:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("[cairn-wrap] error: the plugin carries no vendored GSD "
                  f"surface — cannot tell whether '{name}' is implemented.",
                  file=sys.stderr)
            for line in searched:
                print(f"  searched: {line}", file=sys.stderr)
            print(f"  fix: {FIX_LINE}", file=sys.stderr)
        sys.exit(EXIT_NO_GSD)

    present = surface_commands(dirpath)
    installed = name in present
    payload = {"command": name, "installed": installed, "surface": str(dirpath),
               "surface_command_count": len(present), "searched": searched,
               "exit": EXIT_OK if installed else EXIT_MISSING}
    if opts["json"]:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif installed:
        print(f"[cairn-wrap] ✓ '{name}' is implemented here ({dirpath})")
    else:
        # Names three things: what is missing, where we looked, what to do.
        print(f"[cairn-wrap] error: '{name}' is not implemented by this "
              f"plugin — /cairn:{name} delegates to it and cannot run.",
              file=sys.stderr)
        print(f"  looked in: {dirpath} ({len(present)} command(s) found there)",
              file=sys.stderr)
        print(f"  fix: {FIX_LINE}", file=sys.stderr)
    sys.exit(EXIT_OK if installed else EXIT_MISSING)


# ---------------------------------------------------------------------------
# list — the derived source of truth
# ---------------------------------------------------------------------------

def resolve_commands_dir(given):
    if given:
        cand = Path(given)
        if not cand.is_dir():
            die(f"--commands-dir '{given}' is not a directory", EXIT_USAGE)
        return cand
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        cand = Path(env).resolve() / "commands"
        if cand.is_dir():
            return cand
    # scripts/ and commands/ are siblings inside the plugin.
    cand = (Path(__file__).resolve().parent.parent / "commands").resolve()
    if not cand.is_dir():
        die(f"no cairn commands directory found (looked at {cand})",
            EXIT_USAGE)
    return cand


def collect(commands_dir):
    """Every cairn command, and which of them wrap a /gsd:* command.

    Derived by reading each file's frontmatter. Nothing here knows the names
    of the thirteen — that knowledge lives on disk, which is the point.
    """
    wrappers, own = [], []
    for path in sorted(commands_dir.glob("*.md")):
        fm = read_frontmatter(path)
        name = path.stem
        wraps = fm.get("wraps")
        if wraps:
            family = fm.get("wrap-family", "")
            if family not in FAMILIES:
                die(f"{path.name}: wrap-family '{family}' is not one of "
                    f"{', '.join(FAMILIES)}", EXIT_USAGE)
            impl = fm.get("implementation", "")
            if impl not in IMPLEMENTATIONS:
                die(f"{path.name}: implementation '{impl}' is not one of "
                    f"{', '.join(IMPLEMENTATIONS)}", EXIT_USAGE)
            wrappers.append({"command": name, "wraps": wraps,
                             "family": family, "implementation": impl,
                             "description": fm.get("description", "")})
        else:
            own.append({"command": name,
                        "description": fm.get("description", "")})
    return wrappers, own


def do_list(opts):
    commands_dir = resolve_commands_dir(opts["commands_dir"])
    wrappers, own = collect(commands_dir)
    payload = {
        "commands_dir": str(commands_dir),
        "wrappers": wrappers,
        "commands": sorted([w["command"] for w in wrappers]
                           + [c["command"] for c in own]),
        "counts": {"total": len(wrappers) + len(own),
                   "wrappers": len(wrappers), "own": len(own)},
    }
    if opts["json"]:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"[cairn-wrap] {payload['counts']['total']} command(s) in "
              f"{commands_dir}: {payload['counts']['wrappers']} wrapper(s), "
              f"{payload['counts']['own']} cairn's own")
        for w in wrappers:
            print(f"  /cairn:{w['command']} -> {w['wraps']} "
                  f"[{w['family']}/{w['implementation']}]")
    sys.exit(EXIT_OK)


# ---------------------------------------------------------------------------
# docs — WRAP-03
# ---------------------------------------------------------------------------

def resolve_doc(given, commands_dir):
    if given:
        return Path(given)
    return (commands_dir.parent / "docs" / "commands.md").resolve()


def resolve_doc_pages_dir(given, doc):
    if given:
        return Path(given)
    return doc.parent / "commands"


FAMILY_TITLES = {
    "phase": "Phase-scoped — claim the phase's issues, delegate, refresh the map",
    "structural": "Structural — changes the phase list itself, so labels move",
    "milestone": "Milestone-scoped — the label pair is `m-<milestone>`",
}


def build_block(wrappers, own, doc_text, doc_pages_dir):
    """The generated block: the count sentence, the table, and the leftovers.

    THE LEFTOVERS ARE NAMED RATHER THAN HIDDEN. Three of them, and each is a
    different way for this page to lie:

      undocumented  a command with no row anywhere. Exactly how /cairn:config
                    and /cairn:reconcile stayed invisible; a generator that
                    quietly omitted them would have preserved that.
      missing_page  a row whose link points at a page that does not exist. The
                    generator itself can produce these — it writes a row per
                    wrapper whether or not anyone wrote the page — so a table
                    of broken links is a lie this tool is capable of authoring,
                    which is why it must report it.
      orphan_page   a page documenting no installed command.

    Every warning disappears on its own once the gap is closed.
    """
    linked = set(DOC_LINK.findall(doc_text))
    wrapper_names = {w["command"] for w in wrappers}
    undocumented = sorted(c["command"] for c in own
                          if c["command"] not in linked)
    pages = set()
    if doc_pages_dir.is_dir():
        pages = {p.stem for p in doc_pages_dir.glob("*.md")}
    all_commands = wrapper_names | {c["command"] for c in own}
    orphan_pages = sorted(pages - all_commands)
    missing_pages = sorted(all_commands - pages)

    total = len(wrappers) + len(own)
    lines = [START_MARKER, HEADER_LINE, ""]
    verb = "wraps" if len(wrappers) == 1 else "wrap"
    lines.append(
        f"cairn ships **{total}** commands: **{len(wrappers)}** {verb} a "
        f"`/gsd:*` command (listed below, derived from each command file's "
        f"`wraps:` frontmatter) and **{len(own)}** are cairn's own (grouped "
        f"above)."
    )
    lines.append("")

    if wrappers:
        for family in FAMILIES:
            rows = [w for w in wrappers if w["family"] == family]
            if not rows:
                continue
            lines.append(f"**{FAMILY_TITLES[family]}**")
            lines.append("")
            lines.append("| Command | Wraps | Description |")
            lines.append("|---|---|---|")
            for w in sorted(rows, key=lambda r: r["command"]):
                lines.append(
                    f"| [`/cairn:{w['command']}`](./commands/"
                    f"{w['command']}.md) | `/gsd:{w['wraps']}` | "
                    f"{w['description']} |"
                )
            lines.append("")
    else:
        lines.append("No wrappers are installed.")
        lines.append("")

    for name in undocumented:
        lines.append(f"⚠ Not documented: `/cairn:{name}` exists in "
                     f"`cairn/commands/` and has no row on this page.")
    for name in missing_pages:
        lines.append(f"⚠ Missing page: `commands/{name}.md` is linked and "
                     f"does not exist.")
    for name in orphan_pages:
        lines.append(f"⚠ Orphan page: `commands/{name}.md` documents no "
                     f"installed command.")
    if undocumented or missing_pages or orphan_pages:
        lines.append("")

    lines.append(END_MARKER)
    return "\n".join(lines), undocumented, missing_pages, orphan_pages


def splice(text, block):
    """Replace the marker block, or append a new section carrying it.

    Never rewrites the file wholesale: everything outside the markers survives
    byte for byte. A file with no markers gains the block under its own
    heading, appended — the same contract cairn-map.py established.
    """
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start != -1 and end != -1 and end > start:
        return text[:start] + block + text[end + len(END_MARKER):]
    suffix = "" if text.endswith("\n") else "\n"
    return f"{text}{suffix}\n{SECTION_HEADING}\n\n{block}\n"


def do_docs(opts):
    commands_dir = resolve_commands_dir(opts["commands_dir"])
    doc = resolve_doc(opts["doc"], commands_dir)
    if not doc.is_file():
        die(f"doc file not found: {doc}", EXIT_USAGE)
    doc_pages_dir = resolve_doc_pages_dir(opts["doc_pages_dir"], doc)

    wrappers, own = collect(commands_dir)
    current = doc.read_text(encoding="utf-8")
    block, undocumented, missing_pages, orphan_pages = build_block(
        wrappers, own, current, doc_pages_dir)
    updated = splice(current, block)
    changed = updated != current

    payload = {"doc": str(doc), "wrappers": [w["command"] for w in wrappers],
               "undocumented": undocumented, "missing_pages": missing_pages,
               "orphan_pages": orphan_pages, "changed": changed}

    if opts["check"]:
        if opts["json"]:
            print(json.dumps(payload, indent=2, sort_keys=True))
        elif changed:
            diff = difflib.unified_diff(
                current.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=f"{doc} (on disk)", tofile=f"{doc} (derived)")
            sys.stdout.writelines(diff)
            print(f"[cairn-wrap] {doc} is stale — run "
                  f"`cairn-wrap.sh docs` to regenerate", file=sys.stderr)
        else:
            print(f"[cairn-wrap] ✓ {doc} is current "
                  f"({len(wrappers)} wrapper(s))")
        sys.exit(EXIT_STALE if changed else EXIT_OK)

    # A byte-identical rewrite is still a write: only touch the file when the
    # content actually differs, so mtime stays put on a no-op run.
    if changed:
        doc.write_text(updated, encoding="utf-8")
    if opts["json"]:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        verb = "updated" if changed else "already current"
        print(f"[cairn-wrap] {doc} {verb} — {len(wrappers)} wrapper(s)")
        for name in undocumented:
            print(f"[cairn-wrap] ⚠ not documented: /cairn:{name}")
        for name in missing_pages:
            print(f"[cairn-wrap] ⚠ missing page: commands/{name}.md")
        for name in orphan_pages:
            print(f"[cairn-wrap] ⚠ orphan page: commands/{name}.md")
    sys.exit(EXIT_OK)


def main():
    opts = parse_args(sys.argv[1:])
    if opts["command"] == "preflight":
        do_preflight(opts)
    elif opts["command"] == "list":
        do_list(opts)
    else:
        do_docs(opts)


if __name__ == "__main__":
    main()
