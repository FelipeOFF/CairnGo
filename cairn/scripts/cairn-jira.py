#!/usr/bin/env python3
"""cairn-jira — whether to ASK about Jira, and the record of both answers.

WHAT THIS IS
------------
The flow this script serves is hybrid on purpose. Detecting on its own and
configuring on its own would be guessing about somebody else's tracker; asking
for configuration that could have been detected is the sin this phase exists
to correct. So: detect, SHOW what was found, ask once, and write everything
from the confirmation.

This script owns the two deterministic halves — the decision to ask, and the
two writes. `/cairn:sync-config` owns the one sentence in between.

THERE IS EXACTLY ONE DETECTOR, AND IT IS NOT THIS FILE
------------------------------------------------------
`detect` shells out to `cairn-migrate.py detect --json` and reads
`external.jira`. It re-derives nothing: not the prefixes, not the frequency
bar, not the requirement-id denylist, not the weak-signal rule, not the
samples, not the site URL. The shape of that call is the house
shell-out-and-parse-defensively pattern (cairn-status.py's
`fetch_lease_status()`): a subprocess failure or unparsable JSON is an exit,
never a traceback and never a guess.

Two detectors that can disagree about the same repository is the disease this
milestone exists to cure. Adding a second regex here would be catching it.

WHERE EACH FACT LIVES (one fact, one owner)
-------------------------------------------
    .cairn/sync.json     HOW to sync — the backend, its project key, and the
                         NAMES of the env vars holding credentials. Written
                         here, read by gbsync.py and cairn/hooks/
                         post-bd-write.sh.
    .cairn/config.json   WHETHER we already asked, under `jira.link`
                         (unset|yes|no). Written and read through
                         cairn-config.py, which owns that file and validates
                         the value against its closed schema. This script
                         never opens it directly.

Keeping the answer out of sync.json is deliberate. A `no` has to be as durable
as a `yes` — a forgotten `no` brings the question back every session — and
sync.json has nowhere to put "we asked and they said no" that would not also
look like a half-configured backend.

NO CREDENTIAL IS EVER WRITTEN
-----------------------------
The gbsync contract is NAMES of environment variables in the committed file
(`email_env`, `token_env`), never values. `apply` writes names, prints which
env vars have to exist in the shell, and has no flag that would accept a
token. tests/cairn-jira.bats asserts the exact set of fields written.

MEASURED VERSUS ASSUMED
-----------------------
MEASURED — before the fix in the same plan, `cairn-migrate.py detect --json`
answered `detected: true` on THIS repository with nine prefixes, all of them
local requirement ids, on the strength of commit messages alone. That is why
`ask` is not a synonym for "found something".

MEASURED — a Jira base_url can only be derived without asking when a git
remote names an `*.atlassian.net` site. This repository has no such remote,
so `apply` needs `--base-url` here. That is a real gap, named rather than
papered over with a placeholder: a backend written with a fake base_url would
fail at push time with an error nobody could read.

ASSUMED — `~/.claude.json` -> `.claudeAiMcpEverConnected` lists display names
of MCP connectors and includes "claude.ai Atlassian Rovo" on the machine this
was written. Whether that list means "connected now" or "connected at some
point" was NOT measured, so it is not consulted by anything here. The `mcp`
signal that IS consulted answers a narrower and honest question: is an
Atlassian server DECLARED in a readable MCP config file? Declared, never
connected.

Usage:
    cairn-jira.py detect [--project-dir DIR] [--json]
    cairn-jira.py apply --key PREFIX [--base-url URL] [--project-dir DIR]
                        [--json]
    cairn-jira.py decline [--project-dir DIR] [--json]

    --project-dir DIR   project root the .cairn/ directory hangs off
                        (default: $CLAUDE_PROJECT_DIR or cwd)
    --json              machine-readable output instead of the
                        `[cairn-jira] ...` human lines

Behavior:
    detect   {"ask": bool, "reason": str, "already": str, "findings": {...}}.
             `ask` is false when there is no signal (`reason: "no signal"`)
             and when an answer is already on record (`reason: "already
             answered: yes"` / `": no"`). `findings` carries the prefixes, the
             signals, the declared-MCP report, the derived site, and the
             samples — up to three branch names and three commit subjects per
             prefix — because the question has to show evidence rather than a
             verdict.

    apply    Writes the jira backend into .cairn/sync.json (creating the file
             in the shape gbsync.py already reads, preserving any other
             backend and any unknown top-level key) and records the answer
             `yes`. The key comes from the detection; nobody types it.

    decline  Records the answer `no`. Nothing else — no file is created under
             .cairn/ except the config the answer lives in.

Exit codes:
    0  ok
    2  usage error, or `apply` without a base_url it could neither be given
       nor derive
    3  nothing to do: `apply`/`decline` when that same answer is already on
       record (idempotent re-run, nothing rewritten)
    5  a script this one depends on is unavailable or unreadable —
       cairn-migrate.py (the detector) or cairn-config.py (the answer's owner)

    `detect` exits 0 or 5, never 3: it is a REPORT, and `ask: false` is an
    answer to the question it was asked, not a failure. Exit 3 belongs to the
    verbs that write.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOTHING = 3
EXIT_NO_HELPER = 5

SCRIPT_DIR = Path(__file__).resolve().parent
CAIRN_MIGRATE = SCRIPT_DIR / "cairn-migrate.py"
CAIRN_CONFIG = SCRIPT_DIR / "cairn-config.py"

ANSWER_KEY = "jira.link"
ANSWER_YES = "yes"
ANSWER_NO = "no"
ANSWER_UNSET = "unset"

# The exact set of config fields `apply` writes for the jira backend, matching
# cairn/adapters/jira.py's documented contract. email_env/token_env hold the
# NAMES of environment variables; there is no field here that could hold a
# secret, which is the property tests/cairn-jira.bats asserts.
DEFAULT_ISSUE_TYPE = "Task"
DEFAULT_EMAIL_ENV = "JIRA_EMAIL"
DEFAULT_TOKEN_ENV = "JIRA_API_TOKEN"
DEFAULT_TRANSITIONS = {"in_progress": "In Progress", "closed": "Done"}

USAGE = ("usage: cairn-jira.py {detect | apply --key PREFIX [--base-url URL] "
         "| decline} [--project-dir DIR] [--json]")


def die(msg, code=EXIT_USAGE):
    print(f"[cairn-jira] error: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# the two scripts this one leans on
# --------------------------------------------------------------------------- #
def run_helper(argv):
    """(returncode, stdout) for a sibling cairn script, or (None, "") when it
    could not be run at all. Same defensive shape as cairn-status.py's
    fetch_lease_status(): a missing binary or a crashed child degrades to a
    named exit here, never to a traceback and never to a guess."""
    try:
        proc = subprocess.run([sys.executable] + [str(a) for a in argv],
                              capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return proc.returncode, proc.stdout


def detector_findings(root):
    """external.jira from `cairn-migrate.py detect --json`, or exit 5.

    This is the ONLY place Jira detection enters this script.
    """
    code, out = run_helper([CAIRN_MIGRATE, "detect", "--json",
                            "--project-dir", root])
    if code is None or code != EXIT_OK:
        die(f"could not run the detector ({CAIRN_MIGRATE.name}) — Jira "
            "detection is unavailable, so nothing is decided here",
            EXIT_NO_HELPER)
    try:
        payload = json.loads(out or "null")
    except json.JSONDecodeError:
        payload = None
    if not isinstance(payload, dict):
        die(f"{CAIRN_MIGRATE.name} detect --json did not answer with JSON — "
            "refusing to guess", EXIT_NO_HELPER)
    jira = (payload.get("external") or {}).get("jira")
    if not isinstance(jira, dict):
        die(f"{CAIRN_MIGRATE.name} detect --json carried no external.jira — "
            "refusing to guess", EXIT_NO_HELPER)
    return jira


def read_answer(root):
    """The recorded answer: "unset", "yes" or "no". Exit 5 when the config's
    owner cannot be read — an unreadable record must never be reported as
    "never asked", because that is how a `no` quietly loses its force."""
    code, out = run_helper([CAIRN_CONFIG, "get", ANSWER_KEY,
                            "--project-dir", root, "--json"])
    if code is None or code != EXIT_OK:
        die(f"could not read {ANSWER_KEY} through {CAIRN_CONFIG.name} — the "
            "previous answer is unknown, and re-asking would undo it",
            EXIT_NO_HELPER)
    try:
        payload = json.loads(out or "null")
    except json.JSONDecodeError:
        payload = None
    value = payload.get("value") if isinstance(payload, dict) else None
    return value if value in (ANSWER_YES, ANSWER_NO) else ANSWER_UNSET


def write_answer(root, value):
    """Record the answer through cairn-config.py, which owns and validates
    .cairn/config.json. Writing those bytes from here would make this script a
    second owner of that file — the shape of the next disagreement."""
    code, _ = run_helper([CAIRN_CONFIG, "set", ANSWER_KEY, value,
                          "--project-dir", root, "--json"])
    if code is None or code != EXIT_OK:
        die(f"could not record {ANSWER_KEY}={value} through "
            f"{CAIRN_CONFIG.name} — the answer would not survive the session",
            EXIT_NO_HELPER)


# --------------------------------------------------------------------------- #
# the decision
# --------------------------------------------------------------------------- #
def decide(root):
    """(ask, reason, already, findings) — the whole decision, in one place so
    `detect` and the write verbs cannot drift apart about it."""
    findings = detector_findings(root)
    already = read_answer(root)
    if already in (ANSWER_YES, ANSWER_NO):
        return False, f"already answered: {already}", already, findings
    if not findings.get("detected"):
        # No signal is not a weak yes. A repo with nothing pointing at Jira is
        # never asked — that is literal in this phase's success criteria, and
        # it is why `detected` (the guarded verdict) is read here rather than
        # `prefixes` (the unguarded information).
        return False, "no signal", already, findings
    if not (findings.get("prefixes") or []):
        # A signal with no key is a real case (a declared Atlassian MCP server
        # in a repo whose history names no issue key) and it is NOT the same
        # question. There is nothing to CONFIRM here, so the prose command
        # says so instead of pretending a choice exists — asking someone to
        # type a key is the sin this phase corrects, and it is worth naming
        # the one situation where confirmation is impossible.
        return True, "signal found, no key to confirm", already, findings
    return True, "signal found, no answer on record", already, findings


def evidence_lines(findings):
    """The human render of what was found — the same facts the prose command
    shows before it asks. Evidence, not a verdict."""
    lines = []
    for prefix in findings.get("prefixes") or []:
        sample = (findings.get("samples") or {}).get(prefix) or {}
        branches = sample.get("branch_count", 0)
        commits = sample.get("commit_count", 0)
        where = []
        if branches:
            where.append(f"{branches} branch(es)")
        if commits:
            where.append(f"{commits} commit(s)")
        detail = ", ".join(where) or "no branch or commit"
        lines.append(f"{prefix}- in {detail}")
        for example in (sample.get("branches") or [])[:2]:
            lines.append(f"    branch: {example}")
        for example in (sample.get("commits") or [])[:2]:
            lines.append(f"    commit: {example}")
    mcp = findings.get("mcp") or {}
    if mcp.get("declared"):
        lines.append(f"Atlassian MCP server '{mcp.get('server')}' declared in "
                     f"{mcp.get('source')}")
    if findings.get("site"):
        lines.append(f"site named by a git remote: {findings['site']}")
    return lines


# --------------------------------------------------------------------------- #
# sync.json
# --------------------------------------------------------------------------- #
def sync_path(root):
    return Path(root) / ".cairn" / "sync.json"


def load_sync(root):
    """The existing sync.json as a dict, or a fresh one. An unreadable file is
    a loud failure rather than a silent overwrite: it is committed, and other
    backends live in it."""
    path = sync_path(root)
    if not path.is_file():
        return {"backends": []}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        die(f"could not read {path}: {e}")
    if not text.strip():
        return {"backends": []}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e} — refusing to overwrite a file "
            "that already holds somebody's backend configuration")
    if not isinstance(data, dict):
        die(f"{path} must hold a JSON object, found {type(data).__name__}")
    if not isinstance(data.get("backends"), list):
        data["backends"] = []
    return data


def write_sync(root, data):
    path = sync_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Same rendering gbsync.py:write_json uses — sorted keys, two-space
        # indent, trailing newline — because this file is COMMITTED and its
        # diffs are read by people.
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    except OSError as e:
        die(f"could not write {path}: {e}")
    return path


def jira_backend(key, base_url, previous):
    """The backend entry, with the EXACT field set cairn/adapters/jira.py
    documents. Values already present in a previous jira entry win for the
    fields a person may have tuned (issue type, env var names, transitions):
    re-running this must not silently reset somebody's workflow mapping."""
    prev_config = {}
    if isinstance(previous, dict) and isinstance(previous.get("config"), dict):
        prev_config = previous["config"]
    transitions = prev_config.get("transitions")
    if not isinstance(transitions, dict):
        transitions = dict(DEFAULT_TRANSITIONS)
    return {
        "type": "jira",
        "enabled": True,
        "adapter": "jira",
        "config": {
            "base_url": base_url,
            "project_key": key,
            "issue_type": prev_config.get("issue_type") or DEFAULT_ISSUE_TYPE,
            "email_env": prev_config.get("email_env") or DEFAULT_EMAIL_ENV,
            "token_env": prev_config.get("token_env") or DEFAULT_TOKEN_ENV,
            "transitions": transitions,
        },
    }


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_detect(args, root):
    ask, reason, already, findings = decide(root)
    payload = {"ask": ask, "reason": reason, "already": already,
               "findings": findings}
    if args.json:
        print(json.dumps(payload))
        sys.exit(EXIT_OK)
    print(f"[cairn-jira] ask={'yes' if ask else 'no'} ({reason})")
    for line in evidence_lines(findings):
        print(f"[cairn-jira]   {line}")
    sys.exit(EXIT_OK)


def cmd_apply(args, root):
    key = (args.key or "").strip()
    if not key:
        die(f"apply needs --key <PREFIX>\n{USAGE}")
    already = read_answer(root)
    if already == ANSWER_YES:
        msg = (f"{ANSWER_KEY} is already '{ANSWER_YES}' — nothing rewritten; "
               f"edit {sync_path(root)} or run "
               f"cairn-config.sh set {ANSWER_KEY} unset to start over")
        if args.json:
            print(json.dumps({"applied": False, "reason": "already answered: "
                              "yes", "key": key}))
        else:
            print(f"[cairn-jira] {msg}")
        sys.exit(EXIT_NOTHING)

    base_url = (args.base_url or "").strip()
    if not base_url:
        base_url = (detector_findings(root).get("site") or "").strip()
    if not base_url:
        die("no Jira site to write: none of this repo's git remotes names an "
            "*.atlassian.net host, so base_url cannot be derived. Pass "
            "--base-url https://<site>.atlassian.net. A placeholder is NOT "
            "written — a backend with a fake base_url fails at push time with "
            f"an error nobody can read.\n{USAGE}")

    data = load_sync(root)
    backends = data["backends"]
    previous = None
    for i, backend in enumerate(backends):
        if isinstance(backend, dict) and backend.get("type") == "jira":
            previous = backend
            backends[i] = jira_backend(key, base_url, previous)
            break
    else:
        backends.append(jira_backend(key, base_url, None))
    path = write_sync(root, data)
    write_answer(root, ANSWER_YES)

    if args.json:
        print(json.dumps({"applied": True, "key": key, "base_url": base_url,
                          "path": str(path), "answer": ANSWER_YES,
                          "env_vars": [DEFAULT_EMAIL_ENV, DEFAULT_TOKEN_ENV]}))
        sys.exit(EXIT_OK)
    print(f"[cairn-jira] jira backend enabled for {key} at {base_url} "
          f"({path})")
    print(f"[cairn-jira] export these before a push — the file holds their "
          f"NAMES, never their values: {DEFAULT_EMAIL_ENV}, "
          f"{DEFAULT_TOKEN_ENV}")
    print(f"[cairn-jira] {ANSWER_KEY}={ANSWER_YES} recorded — you will not be "
          "asked again")
    sys.exit(EXIT_OK)


def cmd_decline(args, root):
    already = read_answer(root)
    if already == ANSWER_NO:
        if args.json:
            print(json.dumps({"declined": False,
                              "reason": "already answered: no"}))
        else:
            print(f"[cairn-jira] {ANSWER_KEY} is already '{ANSWER_NO}' — "
                  "nothing rewritten")
        sys.exit(EXIT_NOTHING)
    write_answer(root, ANSWER_NO)
    if args.json:
        print(json.dumps({"declined": True, "answer": ANSWER_NO}))
        sys.exit(EXIT_OK)
    print(f"[cairn-jira] {ANSWER_KEY}={ANSWER_NO} recorded — the question "
          "will not come back. Change it with "
          f"cairn-config.sh set {ANSWER_KEY} unset")
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        prog="cairn-jira",
        description="whether to ask about Jira, and the record of both "
                    "answers (detection lives in cairn-migrate.py)")
    sub = parser.add_subparsers(dest="command", required=True)

    detect = sub.add_parser("detect", help="decide whether to ask, and carry "
                                           "the evidence to ask with")
    detect.set_defaults(func=cmd_detect)

    apply_ = sub.add_parser("apply", help="write the jira backend and record "
                                          "the answer yes")
    apply_.add_argument("--key", required=True,
                        help="the detected project key prefix")
    apply_.add_argument("--base-url", metavar="URL",
                        help="the Jira site (default: derived from an "
                             "*.atlassian.net git remote)")
    apply_.set_defaults(func=cmd_apply)

    decline = sub.add_parser("decline", help="record the answer no")
    decline.set_defaults(func=cmd_decline)

    for p in (detect, apply_, decline):
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
        die(f"project directory does not exist: {root}\n{USAGE}")
    args.func(args, root)


if __name__ == "__main__":
    main()
