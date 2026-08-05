#!/usr/bin/env python3
"""cairn-config — cairn's own settings, with two doors into one place.

WHAT THIS IS
------------
GSD carries 30+ keys in `.planning/config.json`; cairn carried none. What
existed was scattered across `.cairn/context.json` and `.cairn/sync.json`, and
nothing listed the set — `response_language` had to be discovered and set in
the middle of a milestone because no inventory existed to read it off.

This script is the one place cairn's own knobs live, and there are TWO doors
into it:

  * `/cairn:config` asks (ONE AskUserQuestion batch, sections named, current
    value pre-selected — the /gsd:config shape) and writes through `set`;
  * `.cairn/config.json` is a plain JSON file, edited by hand.

Both doors reach the same bytes. That is not a claim, it is a test:
tests/cairn-config.bats writes the file by hand and reads it through `get`,
then writes through `set` and reads the file raw, and compares the two files
byte for byte.

THE ENTRY RULE: NO KEY WITHOUT A READER
---------------------------------------
Every key in SCHEMA names the executable that reads it, and `set` of a key
that is not in SCHEMA is a usage error rather than a write. This is not
tidiness. `cairn.sync_push` is declared in `capability.json:43`, documented in
three prompt fragments and asserted in `tests/capability.bats:97`, and it is
read by no executable code at all — the push is decided solely by the
existence of `.cairn/sync.json` with an enabled backend
(`cairn/hooks/post-bd-write.sh:126-152`). A config that offers that button
would write a value the hook ignores. A closed schema with a named reader per
key is the mechanism that stops this file from becoming a second such promise.

`bookkeep.*`, `ship.pr_scope` and `test.jobs` are in the schema before their
readers ship (plans 29-02 and 29-06 of this same phase). That is a different
thing from `sync_push` in a way that can be checked rather than argued: the
reader is NAMED here, it lands in the same cycle, and the plan that implements
it is the plan that tests it. If a cycle ends with one of those keys still
unread, the key is the thing to delete — not the rule.

AND WHAT IS DELIBERATELY MISSING
--------------------------------
`cairn.sync_push` is NOT here, and its absence is a decision rather than an
oversight. Making it real changes behavior for everyone who already has a
`sync.json`: today the push happens because that file exists with an enabled
backend, so wiring the flag would silently stop pushes that currently happen.
That is a product decision — grooming — and this phase automates mechanics.
Until the grooming decides, the key does not appear in this config, and
`tests/cairn-config.bats` asserts the exact key SET so that adding the button
turns a test red instead of slipping in.

WHERE THIS FILE LIVES, AND WHY (measured versus assumed)
--------------------------------------------------------
`.cairn/config.json`, its own file, rather than a `cairn.*` block inside
`.planning/config.json`. Two measured reasons:

  1. `config-loader.cjs:609` rewrites `.planning/config.json` during a read,
     outside the lock. That window is not ours to close.
  2. `.cairn/` is already the home of what cairn owns (`sync.json`,
     `context.json`, `journal.jsonl`), one owner per file.

MEASURED, and it corrects an earlier claim rather than deleting it: planning
recorded that `gsd-tools query config-set cairn.enabled` "exits 1, so writing a
`cairn.*` key through gsd-tools is not proven". That was an ARITY error, not a
capability one — the command answers `Error: Usage: config-set <key.path>
<value>` because the value was missing. Completed with a value it exits 0 and
writes `"cairn": {"enabled": true}`. **Writing `cairn.*` through gsd-tools IS
proven.** The decision above still stands on its two measured reasons; the
correction is written here instead of the sentence quietly disappearing.

`cairn.enabled` does NOT move: it is the capability's activation key, read by
`cairn-loop-gate.py:96` out of `.planning/config.json`. This script never
writes it — `list` only points at it.

The config resolves from the project dir and nothing else. No git-toplevel
walk, no `.planning/active-workstream` lookup: per-workstream config is out of
scope for this phase, in writing rather than by omission.

Usage:
    cairn-config.py list [--project-dir DIR] [--json]
    cairn-config.py get <key> [--project-dir DIR] [--json]
    cairn-config.py set <key> <value> [--project-dir DIR] [--json]

    --project-dir DIR   project root the .cairn/ directory hangs off
                        (default: $CLAUDE_PROJECT_DIR or cwd)
    --json              machine-readable output instead of the bare value /
                        the `[cairn-config] ...` human line

Behavior:
    list  Every key with its effective value, its default, where that value
          came from (`file` or `default`), and its reader — PLUS an inventory
          of the config cairn already keeps elsewhere, one line each with its
          file and its owner. The inventory is informative and named: `list`
          neither reads nor writes those files, it says where they are and who
          owns them. That second half is the point — the complaint was never
          "there is no config", it was "nothing lists the set".

    get   Prints the EFFECTIVE value: the file's value when present and of the
          key's type, otherwise the schema default. A missing config file is
          normal and silent — every default is today's behavior, so a repo
          without the file behaves exactly as it did before this script
          existed.

    set   Validates against the key's type FIRST and writes only then: a
          rejected value leaves the file exactly as it was (and leaves an
          absent file absent). Writes with `json.dumps(obj, indent=2,
          sort_keys=True) + "\\n"` — sorted keys, trailing newline — the same
          shape `gbsync.py:write_json` uses, for the same reason: the file is
          COMMITTED, like `sync.json` and `context.json`, so its diffs are
          read by people.

Exit codes:
    0  ok
    2  usage error: bad flags, or a key that is not in the schema (the message
       names every key that is)
    3  the value is not valid for that key's type, or the config file on disk
       is not readable JSON

Keys, and what reads each one:

    | key                     | type/default        | reader                  |
    |-------------------------|---------------------|-------------------------|
    | autonomous.max_cycles   | int >=0, 0 = no cap | cairn-parallel.py batch |
    |                         |                     |   --cycle K             |
    | autonomous.max_parallel | int >=1, 3          | cairn-parallel.py batch |
    | bookkeep.auto_commit    | bool, false         | cairn-bookkeep.py       |
    | jira.link               | unset|yes|no,       | cairn-jira.py detect    |
    |                         |   "unset"           |                         |
    | ship.pr_scope           | phase|milestone|    | cairn-bookkeep.py       |
    |                         |   none, "phase"     |                         |
    | test.jobs               | int >=1 or null     | cairn-test.py           |
    |                         |   (= available CPUs)|                         |

`jira.link` is the record of an ANSWER, not a preference — which is why it
lives here rather than in `sync.json`. One fact, one owner: `sync.json` says
HOW to sync, this key says WHETHER we already asked. Storing the same thing in
both is where the next disagreement starts.

Config cairn keeps ELSEWHERE, listed by `list` and written by nobody here:

    .cairn/sync.json        which backends bd mirrors to — /cairn:sync-config
                            writes it, gbsync.py reads it
    .cairn/context.json     context-mode scope template and capacity
                            threshold — /cairn:context-config writes it
    .planning/config.json   the key `cairn.enabled`, the capability's
                            activation switch, read by cairn-loop-gate.py:96.
                            It does NOT move here: moving an activation key
                            out from under the thing that activates is how a
                            capability goes quiet.
"""
import argparse
import json
import os
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_VALUE = 3

CONFIG_RELPATH = ".cairn/config.json"

# The closed schema. `reader` is not documentation: it is the entry rule made
# checkable — a key lands here only when an executable that reads it exists or
# lands in the same cycle, and tests/cairn-config.bats asserts the exact key
# SET, so a sixth key cannot slip in unnoticed.
SCHEMA = {
    "autonomous.max_cycles": {
        "type": "int",
        "default": 0,
        "min": 0,
        "reader": "cairn-parallel.py batch --cycle K",
        "effect": "how many cycles an autonomous run may take before `batch` "
                  "selects nothing (0 = no ceiling)",
    },
    "autonomous.max_parallel": {
        "type": "int",
        "default": 3,
        "min": 1,
        "reader": "cairn-parallel.py batch",
        "effect": "how many phases `batch` selects to run at once",
    },
    "bookkeep.auto_commit": {
        "type": "bool",
        "default": False,
        "reader": "cairn-bookkeep.py",
        "effect": "whether the bookkeeping commit is created after --apply, "
                  "or left for you to make",
    },
    "ship.pr_scope": {
        "type": "enum",
        "choices": ["phase", "milestone", "none"],
        "default": "phase",
        "reader": "cairn-bookkeep.py",
        "effect": "when a pull request comes due: once per phase, once per "
                  "milestone, or never",
    },
    "test.jobs": {
        "type": "int_or_null",
        "default": None,
        "min": 1,
        "reader": "cairn-test.py",
        "effect": "the -j the composed test command runs with (null = as "
                  "many as there are CPUs)",
    },
    "jira.link": {
        "type": "enum",
        "choices": ["unset", "yes", "no"],
        "default": "unset",
        "reader": "cairn-jira.py detect",
        "effect": "whether this repo's bd issues mirror to Jira — and, just "
                  "as importantly, whether the question was already asked: "
                  "`unset` means never asked, and BOTH answers stop it being "
                  "asked again",
    },
}

# The config cairn already keeps elsewhere. Named here so `list` can answer
# "where does cairn keep its settings" completely, and INERT on purpose: this
# script never opens these files. It says where they are and who owns them.
ELSEWHERE = [
    {
        "path": ".cairn/sync.json",
        "what": "which backends bd mirrors to (GitHub/GitLab/Jira/Asana/"
                "Azure Boards), and whether each is enabled",
        "written_by": "/cairn:sync-config",
        "read_by": "gbsync.py, cairn/hooks/post-bd-write.sh",
    },
    {
        "path": ".cairn/context.json",
        "what": "context-mode tuning: the scope template and the capacity "
                "threshold (defaults apply with no file at all)",
        "written_by": "/cairn:context-config",
        "read_by": "the cairn-context skill",
    },
    {
        "path": ".planning/config.json",
        "key": "cairn.enabled",
        "what": "the capability's activation switch — it stays with GSD's "
                "config, and this script never writes it",
        "written_by": "/gsd:config",
        "read_by": "cairn-loop-gate.py",
    },
]

USAGE = ("usage: cairn-config.py {list|get <key>|set <key> <value>} "
         "[--project-dir DIR] [--json]")


def die(msg, code=EXIT_USAGE):
    print(f"[cairn-config] error: {msg}", file=sys.stderr)
    sys.exit(code)


def known_keys_line():
    return "known keys: " + ", ".join(sorted(SCHEMA))


def spec_for(key):
    spec = SCHEMA.get(key)
    if spec is None:
        die(f"unknown key: {key}\n{known_keys_line()}", EXIT_USAGE)
    return spec


# --------------------------------------------------------------------------- #
# the file
# --------------------------------------------------------------------------- #
def config_path(root):
    return Path(root) / CONFIG_RELPATH


def load_file(root):
    """The raw dict from .cairn/config.json.

    An absent file is the normal case and silent. Invalid JSON is a die() that
    names the file — never a traceback, per the house rule.
    """
    path = config_path(root)
    if not path.is_file():
        return {}
    try:
        text = path.read_text()
    except OSError as e:
        die(f"could not read {path}: {e}", EXIT_VALUE)
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e}", EXIT_VALUE)
    if not isinstance(data, dict):
        die(f"{path} must hold a JSON object, found "
            f"{type(data).__name__}", EXIT_VALUE)
    return data


def write_file(root, data):
    path = config_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    except OSError as e:
        die(f"could not write {path}: {e}", EXIT_VALUE)
    return path


def dotted_get(data, key):
    """(value, found) for a dotted key over nested dicts."""
    cur = data
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


def dotted_set(data, key, value):
    """Set a dotted key, creating the intermediate objects. A non-dict sitting
    where a container belongs is replaced — the schema owns the shape."""
    parts = key.split(".")
    cur = data
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


# --------------------------------------------------------------------------- #
# values
# --------------------------------------------------------------------------- #
BOOL_TRUE = ("true", "yes", "on", "1")
BOOL_FALSE = ("false", "no", "off", "0")
NULL_WORDS = ("null", "none", "auto", "")


def valid_int(spec, value):
    # bool is an int subclass in Python; `true` is not a parallelism ceiling,
    # so it is rejected here on purpose.
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    low = spec.get("min")
    return low is None or value >= low


def valid_value(spec, value):
    """Is this already-typed value acceptable for the key? Used on READ, to
    decide whether a hand-edited file value is usable."""
    kind = spec["type"]
    if kind == "int":
        return valid_int(spec, value)
    if kind == "int_or_null":
        return value is None or valid_int(spec, value)
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "enum":
        return value in spec["choices"]
    return False


def coerce_value(key, spec, raw):
    """Command-line string -> typed value, or die(EXIT_VALUE) having written
    nothing. Validation happens BEFORE any write, which is what makes "a
    rejected value leaves the file untouched" true rather than hoped for."""
    kind = spec["type"]
    text = str(raw).strip()

    if kind in ("int", "int_or_null"):
        if kind == "int_or_null" and text.lower() in NULL_WORDS:
            return None
        try:
            value = int(text)
        except (TypeError, ValueError):
            expected = ("an integer, or null" if kind == "int_or_null"
                        else "an integer")
            die(f"{key} takes {expected}, got {raw!r}", EXIT_VALUE)
        low = spec.get("min")
        if low is not None and value < low:
            die(f"{key} must be at least {low}, got {value}", EXIT_VALUE)
        return value

    if kind == "bool":
        lowered = text.lower()
        if lowered in BOOL_TRUE:
            return True
        if lowered in BOOL_FALSE:
            return False
        die(f"{key} takes a boolean ({'/'.join(BOOL_TRUE)} or "
            f"{'/'.join(BOOL_FALSE)}), got {raw!r}", EXIT_VALUE)

    if kind == "enum":
        if text in spec["choices"]:
            return text
        die(f"{key} takes one of: {', '.join(spec['choices'])} — got {raw!r}",
            EXIT_VALUE)

    # Defensive: a schema entry whose type this function does not handle is a
    # bug in the schema, not in the user's input.
    die(f"unhandled type {kind!r} for key {key}", EXIT_USAGE)


def effective(data, key):
    """(value, source): the file's value when present AND valid for the key's
    type, otherwise the schema default.

    A file value of the wrong type does not fail a read. Reading has to keep
    working for every caller (`batch` shells out to this on every run), so a
    bad value degrades to the default and `source` says `default` — the
    divergence is visible without being fatal.
    """
    spec = SCHEMA[key]
    value, found = dotted_get(data, key)
    if found and valid_value(spec, value):
        return value, "file"
    return spec["default"], "default"


def scalar_text(value):
    """The bare-value rendering `get` prints without --json: JSON scalars, so
    an int is `5`, a bool is `true` and a null is `null` — but a string is
    printed bare, because a caller doing `$(cairn-config.sh get ship.pr_scope)`
    wants `phase`, not `"phase"`."""
    if isinstance(value, str):
        return value
    return json.dumps(value)


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_list(args, root):
    data = load_file(root)
    keys = []
    for key in sorted(SCHEMA):
        spec = SCHEMA[key]
        value, source = effective(data, key)
        entry = {"key": key, "type": spec["type"], "value": value,
                 "default": spec["default"], "source": source,
                 "reader": spec["reader"], "effect": spec["effect"]}
        if "choices" in spec:
            entry["choices"] = spec["choices"]
        keys.append(entry)

    payload = {"path": str(config_path(root)), "keys": keys,
               "elsewhere": ELSEWHERE}
    if args.json:
        print(json.dumps(payload))
        sys.exit(EXIT_OK)

    print(f"[cairn-config] {payload['path']} — edit it by hand or run "
          f"/cairn:config; both reach the same file")
    width = max(len(k["key"]) for k in keys)
    for k in keys:
        origin = ("default" if k["source"] == "default"
                  else f"file, default {scalar_text(k['default'])}")
        print(f"[cairn-config]   {k['key']:<{width}} = "
              f"{scalar_text(k['value'])}  ({origin}) — read by "
              f"{k['reader']}")
    print("[cairn-config] elsewhere (named here, never read or written by "
          "this command):")
    for item in ELSEWHERE:
        where = item["path"]
        if item.get("key"):
            where = f"{where} -> {item['key']}"
        print(f"[cairn-config]   {where}: {item['what']} "
              f"(written by {item['written_by']}, read by {item['read_by']})")
    sys.exit(EXIT_OK)


def cmd_get(args, root):
    spec = spec_for(args.key)
    value, source = effective(load_file(root), args.key)
    if args.json:
        print(json.dumps({"key": args.key, "value": value, "source": source,
                          "default": spec["default"],
                          "reader": spec["reader"]}))
    else:
        print(scalar_text(value))
    sys.exit(EXIT_OK)


def cmd_set(args, root):
    spec = spec_for(args.key)
    value = coerce_value(args.key, spec, args.value)
    data = load_file(root)
    dotted_set(data, args.key, value)
    path = write_file(root, data)
    if args.json:
        print(json.dumps({"key": args.key, "value": value, "source": "file",
                          "path": str(path), "reader": spec["reader"]}))
    else:
        print(f"[cairn-config] {args.key} = {scalar_text(value)} "
              f"({path}) — read by {spec['reader']}")
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        prog="cairn-config",
        description="cairn's own settings (.cairn/config.json): the same "
                    "place /cairn:config writes and a hand edit reaches.")
    sub = parser.add_subparsers(dest="command", required=True)

    listing = sub.add_parser("list", help="every key with its effective "
                                          "value, plus the config cairn "
                                          "keeps elsewhere")
    listing.set_defaults(func=cmd_list)

    get = sub.add_parser("get", help="print a key's effective value")
    get.add_argument("key", help="dotted key name")
    get.set_defaults(func=cmd_get)

    set_ = sub.add_parser("set", help="write a key's value")
    set_.add_argument("key", help="dotted key name")
    set_.add_argument("value", help="new value")
    set_.set_defaults(func=cmd_set)

    for p in (listing, get, set_):
        p.add_argument("--project-dir", metavar="DIR",
                       help="project root the .cairn/ directory hangs off "
                            "(default: $CLAUDE_PROJECT_DIR or cwd)")
        p.add_argument("--json", action="store_true",
                       help="machine-readable JSON output")

    return parser


def resolve_root(project_dir):
    if project_dir:
        return Path(project_dir).resolve()
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()


def main():
    args = build_parser().parse_args()
    root = resolve_root(args.project_dir)
    if not root.is_dir():
        die(f"project directory does not exist: {root}\n{USAGE}", EXIT_USAGE)
    args.func(args, root)


if __name__ == "__main__":
    main()
