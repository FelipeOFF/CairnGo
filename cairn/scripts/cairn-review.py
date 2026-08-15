#!/usr/bin/env python3
"""cairn-review — the ONE cairn surface that talks to the forge, behind a switch.

WHY THIS IS A SEPARATE FILE, AND WHY THAT IS THE WHOLE POINT
-------------------------------------------------------------
Plan 30-01 proved, in three layers with a negative control each, that
cairn-land.py opens no socket and invokes no network tool — and cairn-status.py
reaches the answer through it. Writing `subprocess.run(["gh", ...])` inside
either of them would turn the structural inventory red, and that inventory
would be RIGHT: the board must stay offline.

So the network does not live there. It lives here, in a file the board never
invokes. The boundary stops being a promise and becomes structure:

    cairn-status.py  ->  cairn-land.py  ->  git, and the local cache FILE
    cairn-review.py  ->  gh / glab                       (never the reverse)

tests/cairn-land.bats keeps asserting TWO subprocess.run sites in
cairn-land.py, and tests/cairn-tracker-card.bats keeps asserting five in
cairn-status.py, none of them a network tool. A future plan that moved the
fetch into either file would have to delete those assertions to ship, which is
exactly the conversation that should happen out loud.

THE SWITCH IS OFF BY DEFAULT AND `off` IS AN ANSWER, NOT AN ERROR
------------------------------------------------------------------
`git.review_state` in .cairn/config.json — `off` (default) | `gh` | `glab`.
With `off` this command exits 3 having read one config key and touched nothing
else: no network, no file, no cache. `gh` is present on the machine this was
written on (gh version 2.87.3); that is local convenience, never a licence to
call out by default.

THE CACHE CARRIES ITS OWN AGE, ALWAYS
--------------------------------------
`.cairn/pr-cache.json` is per-machine state (gitignored, like .cairn/state.json
and .cairn/id-map.json) and every entry sits under a top-level `fetched_at`
stamp in ISO 8601 UTC. A pull-request state with no age is WORSE than no state
at all, because it looks current — so the stamp is not optional, the reader
computes an age from it, and the board prints that age beside the state.

WHERE THE NUMBERS COME FROM
----------------------------
`cairn-land.py report --json`, whose `phases[].pr.numbers` is the set of pull
requests the local history actually names. This script invents no number and
re-reads no git: one fact, one owner. A number given explicitly with `--pr`
skips that read, for the case where somebody knows the number the history does
not carry (measured: in this repository the history carries none at all).

Usage:
    cairn-review.py fetch [--pr N]... [--project-dir DIR] [--json]
    cairn-review.py show [--project-dir DIR] [--json]

Exit codes:
    0  ok
    2  usage error
    3  nothing to do: the switch is `off`, or there is no pull request to ask
       about. Not a failure — it is the answer.
    5  a script or binary this one depends on is unavailable: cairn-config.py,
       cairn-land.py, or the `gh`/`glab` the switch names
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOTHING = 3
EXIT_NO_HELPER = 5

SCRIPT_DIR = Path(__file__).resolve().parent
CAIRN_CONFIG = SCRIPT_DIR / "cairn-config.py"
CAIRN_LAND = SCRIPT_DIR / "cairn-land.py"

SWITCH_KEY = "git.review_state"
SWITCH_OFF = "off"
CACHE_RELPATH = ".cairn/pr-cache.json"

# Seconds per subprocess. Owning the only network call in cairn means owning
# the only way cairn can hang on a dead forge: `gh`/`glab` are given a bound,
# and so are the sibling scripts, which shell out to git. Test seam (house
# CAIRN_* env-var pattern, same as the adapters' CAIRN_JIRA_TIMEOUT): a bats
# test shortens it to prove the bound is real without waiting 30s.
try:
    TIMEOUT = float(os.environ.get("CAIRN_REVIEW_TIMEOUT") or 30)
except ValueError:
    TIMEOUT = 30

# What each tool is asked for, and nothing more. No token is read, written or
# printed anywhere in this file; `gh`/`glab` carry their own auth and this
# script never sees it.
TOOL_ARGV = {
    "gh": lambda n: ["gh", "pr", "view", str(n), "--json",
                     "number,state,title,url,mergedAt"],
    "glab": lambda n: ["glab", "mr", "view", str(n), "-F", "json"],
}

USAGE = ("usage: cairn-review.py {fetch [--pr N] | show} "
         "[--project-dir DIR] [--json]")


def die(msg, code=EXIT_USAGE):
    print(f"[cairn-review] error: {msg}", file=sys.stderr)
    sys.exit(code)


def now_stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_helper(argv):
    """(returncode, stdout) for a sibling cairn script, or (None, "").

    Bounded like the forge call: these scripts shell out to git, and a git
    that never returns would hang this one just as surely as a dead forge
    would. TimeoutExpired is a SubprocessError, so it lands in the same
    (None, "") that every caller already turns into a named exit.
    """
    try:
        proc = subprocess.run([sys.executable] + [str(a) for a in argv],
                              capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return proc.returncode, proc.stdout


def read_switch(root):
    """`off` / `gh` / `glab`, read through the config's owner.

    An unreadable config is an exit, never a default: silently reading `off` as
    `gh` would call out over a decision nobody made, and reading `gh` as `off`
    would silently stop a fetch somebody asked for. Both directions are wrong,
    so neither is guessed.
    """
    code, out = run_helper([CAIRN_CONFIG, "get", SWITCH_KEY,
                            "--project-dir", str(root), "--json"])
    if code is None or code != EXIT_OK:
        die(f"could not read {SWITCH_KEY} through {CAIRN_CONFIG.name} — "
            "refusing to guess whether this repo wants network calls",
            EXIT_NO_HELPER)
    try:
        payload = json.loads(out or "null")
    except json.JSONDecodeError:
        payload = None
    value = payload.get("value") if isinstance(payload, dict) else None
    return value if value in TOOL_ARGV else SWITCH_OFF


def pr_numbers_from_land(root):
    """Every pull request the local history names, via cairn-land.py.

    One fact, one owner: this script re-reads no git and invents no number.
    """
    code, out = run_helper([CAIRN_LAND, "report", "--json",
                            "--project-dir", str(root)])
    if code is None or code != EXIT_OK:
        die(f"could not run {CAIRN_LAND.name} — the pull request numbers come "
            "from there and are not re-derived here", EXIT_NO_HELPER)
    try:
        report = json.loads(out or "null")
    except json.JSONDecodeError:
        report = None
    if not isinstance(report, dict):
        return []
    numbers = []
    for row in (report.get("phases") or {}).values():
        for n in ((row.get("pr") or {}).get("numbers") or []):
            if n not in numbers:
                numbers.append(n)
    return sorted(numbers)


def fetch_one(tool, number):
    """(entry, error) for one pull request. THE ONLY NETWORK CALL IN CAIRN.

    A failure is per-item and never fatal: a forge that is down, a number that
    does not exist, an unauthenticated CLI, a forge that never answers — each
    becomes an error string beside the others and leaves every entry that DID
    answer in the cache. Same aggregate-and-continue shape gbsync.py's
    do_push/do_pull already use.

    The TIMEOUT is what makes "a forge that is down" a member of that list
    rather than an exception to it. A `gh` that accepts the connection and
    then says nothing is the failure mode a live-but-wedged forge produces,
    and without a bound it is not a slow fetch — it is a fetch that never
    ends, holding this command and whatever invoked it open on one socket.
    Named separately from the OSError branch so the report says which of the
    two happened; "could not run gh" and "gh never answered" send a reader to
    different places.
    """
    argv = TOOL_ARGV[tool](number)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"#{number}: {tool} timed out after {TIMEOUT:g}s"
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"#{number}: could not run {tool}: {e}"
    if proc.returncode != 0:
        return None, f"#{number}: {tool} exited {proc.returncode}: " \
                     f"{(proc.stderr or '').strip()[:200]}"
    try:
        payload = json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return None, f"#{number}: {tool} did not answer with JSON"
    if not isinstance(payload, dict):
        return None, f"#{number}: {tool} did not answer with an object"
    # Normalised to ONE shape across both tools. `state` is carried in the
    # forge's own spelling (`MERGED`, `OPEN`, `merged`) rather than rewritten:
    # a board that lowercases a vendor's vocabulary invents a fourth one.
    return {"number": number,
            "state": payload.get("state"),
            "title": payload.get("title"),
            "url": payload.get("url") or payload.get("web_url"),
            "merged_at": payload.get("mergedAt") or payload.get("merged_at"),
            }, None


def cache_path(root):
    return Path(root) / CACHE_RELPATH


def read_cache(root):
    path = cache_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_cache(root, data):
    path = cache_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def cmd_fetch(args, root):
    tool = read_switch(root)
    if tool == SWITCH_OFF:
        payload = {"tool": None, "fetched": 0, "written": False,
                   "reason": "switch-off"}
        emit(args.json, payload,
             [f"[cairn-review] {SWITCH_KEY} is `off` — no network call was "
              "made and nothing was written. Turn it on with "
              f"`cairn-config.sh set {SWITCH_KEY} gh`."])
        sys.exit(EXIT_NOTHING)
    numbers = ([int(n) for n in args.pr] if args.pr
               else pr_numbers_from_land(root))
    if not numbers:
        payload = {"tool": tool, "fetched": 0, "written": False,
                   "reason": "no-pull-request"}
        emit(args.json, payload,
             ["[cairn-review] the local history names no pull request, so "
              "there is nothing to ask about — pass --pr N to name one."])
        sys.exit(EXIT_NOTHING)

    entries, errors = {}, []
    for n in numbers:
        entry, err = fetch_one(tool, n)
        if err:
            errors.append(err)
            continue
        entries[str(n)] = entry
    if not entries:
        # Nothing answered: the previous cache is LEFT ALONE. Overwriting a
        # stamped answer with an empty one would replace a stale truth with a
        # fresh-looking void, which is the exact failure this whole plan is
        # about.
        payload = {"tool": tool, "fetched": 0, "written": False,
                   "reason": "no-answer", "errors": errors}
        emit(args.json, payload,
             [f"[cairn-review] ✗ {tool} answered for none of "
              f"{len(numbers)} pull request(s) — the existing cache was left "
              "untouched"] + [f"     - {e}" for e in errors])
        sys.exit(EXIT_NO_HELPER)

    data = {"fetched_at": now_stamp(), "tool": tool, "prs": entries}
    write_cache(root, data)
    payload = {"tool": tool, "fetched": len(entries), "written": True,
               "fetched_at": data["fetched_at"], "errors": errors}
    emit(args.json, payload,
         [f"[cairn-review] ✓ {len(entries)} pull request(s) from {tool} at "
          f"{data['fetched_at']} -> {CACHE_RELPATH}"]
         + [f"     - {e}" for e in errors])
    sys.exit(EXIT_OK)


def cmd_show(args, root):
    data = read_cache(root)
    if not data:
        payload = {"cached": False, "fetched_at": None, "prs": {}}
        emit(args.json, payload,
             [f"[cairn-review] no {CACHE_RELPATH} — nothing has been fetched "
              "on this machine"])
        sys.exit(EXIT_NOTHING)
    prs = data.get("prs") or {}
    payload = {"cached": True, "fetched_at": data.get("fetched_at"),
               "tool": data.get("tool"), "prs": prs}
    lines = [f"[cairn-review] {len(prs)} pull request(s), fetched "
             f"{data.get('fetched_at')} via {data.get('tool')}"]
    for key in sorted(prs, key=lambda s: int(s) if s.isdigit() else 0):
        entry = prs[key]
        lines.append(f" #{key:<5} {entry.get('state')}  "
                     f"{entry.get('title') or ''}")
    emit(args.json, payload, lines)
    sys.exit(EXIT_OK)


def emit(as_json, payload, lines):
    if as_json:
        print(json.dumps(payload))
    else:
        for line in lines:
            print(line)


def build_parser():
    p = argparse.ArgumentParser(prog="cairn-review.py", add_help=True,
                                description=USAGE)
    p.add_argument("--project-dir")
    p.add_argument("--json", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch")
    f.add_argument("--project-dir")
    f.add_argument("--json", action="store_true")
    f.add_argument("--pr", action="append", default=[])
    s = sub.add_parser("show")
    s.add_argument("--project-dir")
    s.add_argument("--json", action="store_true")
    return p


def resolve_root(project_dir):
    if project_dir:
        return Path(project_dir).resolve()
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()


def main():
    args = build_parser().parse_args(sys.argv[1:])
    if not args.cmd:
        die(USAGE, EXIT_USAGE)
    root = resolve_root(args.project_dir)
    if not root.is_dir():
        die(f"no such directory: {root}", EXIT_USAGE)
    if args.cmd == "fetch":
        for n in args.pr:
            if not str(n).isdigit():
                die(f"--pr takes a number, got {n!r}", EXIT_USAGE)
    {"fetch": cmd_fetch, "show": cmd_show}[args.cmd](args, root)


if __name__ == "__main__":
    main()
