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
    cairn-config.py get <key> [--project-dir DIR] [--json]
    cairn-config.py set <key> <value> [--project-dir DIR] [--json]

    --project-dir DIR   project root the .cairn/ directory hangs off
                        (default: $CLAUDE_PROJECT_DIR or cwd)
    --json              machine-readable output instead of the bare value /
                        the `[cairn-config] ...` human line

Behavior:
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

    | key                     | type/default | reader                    |
    |-------------------------|--------------|---------------------------|
    | autonomous.max_parallel | int >=1, 3   | cairn-parallel.py batch   |
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
    "autonomous.max_parallel": {
        "type": "int",
        "default": 3,
        "min": 1,
        "reader": "cairn-parallel.py batch",
        "effect": "how many phases `batch` selects to run at once",
    },
}

USAGE = ("usage: cairn-config.py {get <key>|set <key> <value>} "
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
def valid_value(spec, value):
    """Is this already-typed value acceptable for the key? Used on READ, to
    decide whether a hand-edited file value is usable."""
    if spec["type"] == "int":
        # bool is an int subclass in Python; `true` is not a parallelism
        # ceiling, so it is rejected here on purpose.
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        low = spec.get("min")
        return low is None or value >= low
    return False


def coerce_value(key, spec, raw):
    """Command-line string -> typed value, or die(EXIT_VALUE) having written
    nothing. Validation happens BEFORE any write, which is what makes "a
    rejected value leaves the file untouched" true rather than hoped for."""
    if spec["type"] == "int":
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            die(f"{key} takes an integer, got {raw!r}", EXIT_VALUE)
        low = spec.get("min")
        if low is not None and value < low:
            die(f"{key} must be at least {low}, got {value}", EXIT_VALUE)
        return value
    # Defensive: a schema entry whose type this function does not handle is a
    # bug in the schema, not in the user's input.
    die(f"unhandled type {spec['type']!r} for key {key}", EXIT_USAGE)


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
    an int is `5` and nothing has to be un-quoted by the caller."""
    return json.dumps(value)


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
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

    get = sub.add_parser("get", help="print a key's effective value")
    get.add_argument("key", help="dotted key name")
    get.set_defaults(func=cmd_get)

    set_ = sub.add_parser("set", help="write a key's value")
    set_.add_argument("key", help="dotted key name")
    set_.add_argument("value", help="new value")
    set_.set_defaults(func=cmd_set)

    for p in (get, set_):
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
