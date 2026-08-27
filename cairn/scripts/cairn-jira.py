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
import datetime
import json
import re
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
DEFAULT_ISSUE_TYPES = {"milestone": "Story", "phase": "Sub-task"}

USAGE = ("usage: cairn-jira.py {detect | apply --key PREFIX [--base-url URL] "
         "| decline | link --from-json FILE (--milestone M | --phase N) "
         "| unlink (--milestone M | --phase N) | links [--milestone M]} "
         "[--project-dir DIR] [--json]")

# The link half (phase 44 / LINK-02). One fact, one owner: the link IS bd's
# own `external_ref`, spelled `jira-<KEY>`; .cairn/id-map.json is a cache
# gbsync derives from it (derive_idmap). Nothing here talks to Jira — the
# card arrives as JSON the session saved from the MCP (or the REST adapter
# fetched), in the REST shape, and the script only decides and writes.
JIRA_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$")
REF_PREFIX = "jira-"
SUBTASK_NAMES = {"sub-task", "subtask"}


def source():
    """cairn_source, imported on first use and not at module level: a bats
    case copies this script alone into a tmpdir to prove detection is not
    reimplemented here, and a top-level import of a sibling would turn that
    exit 5 into an ImportError for every subcommand."""
    sys.path.insert(0, str(SCRIPT_DIR))
    import cairn_source
    return cairn_source


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
    issue_types = prev_config.get("issue_types")
    if not isinstance(issue_types, dict):
        issue_types = dict(DEFAULT_ISSUE_TYPES)
    return {
        "type": "jira",
        "enabled": True,
        "adapter": "jira",
        # The hierarchy model (phase 45): cairn mirrors its cycle as a Story
        # and its phases as Sub-tasks under it, and nothing else. A backend
        # written by this script is born in that model; a hand-written one
        # without the key keeps the flat mirror.
        "model": "hierarchy",
        "config": {
            "base_url": base_url,
            "project_key": key,
            "issue_type": prev_config.get("issue_type") or DEFAULT_ISSUE_TYPE,
            "issue_types": issue_types,
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
# --------------------------------------------------------------------------- #
# link / unlink / links — the vinculo lives in the bead (LINK-02)
# --------------------------------------------------------------------------- #
def read_card(path):
    """The card as the session saved it — a subset of Jira's REST shape
    (D-04): {key, fields: {summary, status: {name}, issuetype: {name,
    subtask}, parent: {key, fields: {issuetype: {name}}}}}. Anything the
    shape does not carry is None; anything malformed is a usage error."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        die(f"cannot read card JSON {path}: {exc}")
    if not isinstance(raw, dict):
        die(f"card JSON {path} is not an object")
    key = str(raw.get("key") or "").strip()
    if not JIRA_KEY_RE.match(key):
        die(f"card JSON {path}: 'key' {key!r} is not a Jira key (PROJ-123)")
    fields = raw.get("fields") or {}
    if not isinstance(fields, dict):
        die(f"card JSON {path}: 'fields' is not an object")
    itype = (fields.get("issuetype") or {})
    parent = fields.get("parent") or {}
    ptype = ((parent.get("fields") or {}).get("issuetype") or {})
    name = str(itype.get("name") or "").strip()
    return {
        "key": key,
        "summary": str(fields.get("summary") or "").strip(),
        "status": str((fields.get("status") or {}).get("name") or "").strip(),
        "type": name,
        "is_subtask": bool(itype.get("subtask")) or name.lower() in SUBTASK_NAMES,
        "parent_key": str(parent.get("key") or "").strip() or None,
        "parent_type": str(ptype.get("name") or "").strip() or None,
    }


def link_target(args, root):
    """(carrier, scope) — scope is ("milestone", key) or ("phase", N). A
    cycle without exactly one carrier, or a phase without one, is exit 4:
    there is no bead to write on, and inventing one is the milestone
    command's job, not this one's."""
    if bool(args.milestone) == bool(args.phase is not None):
        die("link/unlink need exactly one of --milestone <vX.Y> or "
            f"--phase <N>\n{USAGE}")
    if not source().bd_available():
        die("'bd' not found on PATH", EXIT_NO_HELPER)
    if args.milestone:
        key = args.milestone.lstrip("m-") if args.milestone.startswith("m-") \
            else args.milestone
        carriers = source().milestone_carriers(root, key)
        if len(carriers) != 1:
            die(f"m-{key} has {len(carriers)} milestone carrier(s) — the link "
                "needs exactly one (cairn-doctor: milestone-carrier)", 4)
        return carriers[0], ("milestone", key)
    carrier = source().phase_carrier(root, args.phase)
    if carrier is None:
        die(f"phase {args.phase} has no carrier bead to link", 4)
    return carrier, ("phase", args.phase)


def bd_cmd(root, argv):
    proc = subprocess.run(["bd", "-C", str(root)] + argv,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"bd {' '.join(argv[:2])} failed: {proc.stderr.strip()[:300]}", 1)
    return proc.stdout


def carrier_metadata(root, bd_id):
    data = json.loads(bd_cmd(root, ["show", bd_id, "--json"]) or "[]")
    issue = data[0] if isinstance(data, list) else data
    meta = issue.get("metadata")
    return meta if isinstance(meta, dict) else {}


def write_gsd_jira(root, bd_id, jira):
    """metadata.gsd.jira = jira (or removed when None) by read-modify-write:
    bd replaces a provided top-level key wholesale, so the whole metadata
    object goes back."""
    meta = carrier_metadata(root, bd_id)
    gsd = meta.get("gsd") if isinstance(meta.get("gsd"), dict) else {}
    if jira is None:
        gsd.pop("jira", None)
    else:
        gsd["jira"] = jira
    # Always send the `gsd` key, even empty: bd merges top-level keys and
    # replaces a PROVIDED key wholesale, so `{}` changes nothing while
    # `{"gsd": {}}` is the clear (measured, bd 1.1.0).
    meta["gsd"] = gsd
    bd_cmd(root, ["update", bd_id, "--metadata", json.dumps(meta)])


def milestone_story(root, key):
    """The story key the cycle's carrier is linked to, or None."""
    carriers = source().milestone_carriers(root, key)
    ref = str(carriers[0].get("external_ref") or "") if len(carriers) == 1 else ""
    return ref[len(REF_PREFIX):] if ref.startswith(REF_PREFIX) else None


def cmd_link(args, root):
    card = read_card(args.from_json)
    carrier, (kind, scope) = link_target(args, root)
    # D-03: the type is the hierarchy. Story <-> milestone, Sub-task <-> phase.
    if kind == "milestone" and (card["is_subtask"] or card["type"] != "Story"):
        die(f"{card['key']} is a {card['type'] or '?'}, and a milestone links "
            f"to a Story — fix the card in Jira, or pick the story", EXIT_USAGE)
    if kind == "phase" and not card["is_subtask"]:
        die(f"{card['key']} is a {card['type'] or '?'}, and a phase links to a "
            f"Sub-task — fix the card in Jira, or pick the sub-task", EXIT_USAGE)
    ref = REF_PREFIX + card["key"]
    current = str(carrier.get("external_ref") or "").strip()
    # D-02: never over an existing link. unlink first, on purpose.
    if current and current != ref:
        die(f"{carrier['id']} already carries external_ref {current!r} — run "
            f"'cairn-jira.py unlink --{kind} {scope}' first, then link",
            EXIT_NOTHING)
    # 1:1 strict: one card, one bead.
    holders = [i["id"] for i in source().issues(root)
               if str(i.get("external_ref") or "").strip() == ref
               and i.get("id") != carrier.get("id")]
    if holders:
        die(f"{card['key']} is already linked to {', '.join(holders)} — one "
            f"card, one bead; the session decides which is right "
            f"({carrier['id']} or {', '.join(holders)}) and offers to create "
            "another card for the other", EXIT_NOTHING)
    warnings = []
    epic = None
    if kind == "milestone":
        if card["parent_key"] and (card["parent_type"] or "").lower() == "epic":
            epic = card["parent_key"]
    else:
        ms_keys = source().issue_milestones(carrier)
        story = milestone_story(root, ms_keys[0]) if ms_keys else None
        if story and card["parent_key"] and card["parent_key"] != story:
            warnings.append(f"{card['key']} hangs under {card['parent_key']}, "
                            f"and the cycle's story is {story} — the doctor "
                            "will call this drift")
        elif story is None:
            warnings.append("the cycle has no story linked yet — link the "
                            "milestone so the sub-task's parent can be checked")
    changed = current != ref
    if changed:
        bd_cmd(root, ["update", carrier["id"], "--external-ref", ref])
    if kind == "milestone":
        write_gsd_jira(root, carrier["id"],
                       {"story": card["key"], "epic": epic})
    source().invalidate(root)
    payload = {"linked": carrier["id"], "kind": kind, "scope": scope,
               "key": card["key"], "type": card["type"], "epic": epic,
               "summary": card["summary"], "changed": changed,
               "warnings": warnings}
    if args.json:
        print(json.dumps(payload))
        sys.exit(EXIT_OK)
    verb = "linked" if changed else "already linked"
    print(f"[cairn-jira] {verb} {carrier['id']} ({kind} {scope}) -> "
          f"{card['key']} [{card['type']}] {card['summary']}")
    if epic:
        print(f"[cairn-jira] epic {epic} cached on the milestone carrier")
    for w in warnings:
        print(f"[cairn-jira] warning: {w}")
    sys.exit(EXIT_OK)


def cmd_unlink(args, root):
    carrier, (kind, scope) = link_target(args, root)
    current = str(carrier.get("external_ref") or "").strip()
    if current:
        bd_cmd(root, ["update", carrier["id"], "--external-ref", ""])
    if kind == "milestone":
        write_gsd_jira(root, carrier["id"], None)
    source().invalidate(root)
    payload = {"unlinked": carrier["id"], "kind": kind, "scope": scope,
               "was": current or None}
    if args.json:
        print(json.dumps(payload))
        sys.exit(EXIT_OK)
    print(f"[cairn-jira] {carrier['id']} ({kind} {scope}): "
          f"{'cleared ' + current if current else 'nothing to clear'}")
    sys.exit(EXIT_OK)


def links_model(root, key):
    """{milestone: {key, carrier, story, epic}, phases: [{phase, carrier,
    title, key}]} — the whole cycle's vinculo, read from beads only."""
    carriers = source().milestone_carriers(root, key)
    ms = {"key": key, "carrier": None, "story": None, "epic": None}
    if len(carriers) == 1:
        c = carriers[0]
        ms["carrier"] = c.get("id")
        ref = str(c.get("external_ref") or "")
        ms["story"] = ref[len(REF_PREFIX):] if ref.startswith(REF_PREFIX) else None
        ms["epic"] = (source().gsd(c).get("jira") or {}).get("epic")
    phases = []
    for n in sorted(source().milestone_phases(root, key),
                    key=lambda x: (not isinstance(x, (int, float)), x)):
        c = source().phase_carrier(root, n)
        ref = str((c or {}).get("external_ref") or "")
        phases.append({"phase": n, "carrier": (c or {}).get("id"),
                       "title": (c or {}).get("title"),
                       "key": ref[len(REF_PREFIX):]
                       if ref.startswith(REF_PREFIX) else None})
    return {"milestone": ms, "phases": phases}


def cmd_links(args, root):
    if not source().bd_available():
        die("'bd' not found on PATH", EXIT_NO_HELPER)
    key = args.milestone or source().milestone(root)
    if not key:
        die("no open cycle and no --milestone given", 4)
    key = key[2:] if key.startswith("m-") else key
    model = links_model(root, key)
    if args.json:
        print(json.dumps(model))
        sys.exit(EXIT_OK)
    ms = model["milestone"]
    print(f"[cairn-jira] m-{key}: carrier {ms['carrier'] or '-'} -> story "
          f"{ms['story'] or '(unlinked)'}"
          + (f", epic {ms['epic']}" if ms["epic"] else ""))
    for ph in model["phases"]:
        print(f"[cairn-jira]   phase {ph['phase']}: {ph['carrier'] or '-'} -> "
              f"{ph['key'] or '(unlinked)'}"
              + (f"  {ph['title']}" if ph.get("title") else ""))
    sys.exit(EXIT_OK)


def pending_model(root):
    """[{bead, title, pending: [...]}] — every bead with mirror writes
    waiting in metadata.gsd.mirror.pending (phase 45, D-02)."""
    out = []
    for iss in source().issues(root):
        mirror = source().gsd(iss).get("mirror") or {}
        pending = mirror.get("pending") if isinstance(mirror, dict) else None
        if pending:
            out.append({"bead": iss.get("id"), "title": iss.get("title"),
                        "external_ref": iss.get("external_ref") or None,
                        "pending": pending})
    return sorted(out, key=lambda x: x["bead"] or "")


def cmd_pending(args, root):
    if not source().bd_available():
        die("'bd' not found on PATH", EXIT_NO_HELPER)
    if args.clear:
        meta = carrier_metadata(root, args.clear)
        gsd = meta.get("gsd") if isinstance(meta.get("gsd"), dict) else {}
        mirror = gsd.get("mirror") if isinstance(gsd.get("mirror"), dict) else {}
        n = len(mirror.get("pending") or [])
        mirror.pop("pending", None)
        if mirror:
            gsd["mirror"] = mirror
        else:
            gsd.pop("mirror", None)
        meta["gsd"] = gsd   # sent even when empty — see write_gsd_jira()
        bd_cmd(root, ["update", args.clear, "--metadata", json.dumps(meta)])
        source().invalidate(root)
        if args.json:
            print(json.dumps({"cleared": args.clear, "count": n}))
        else:
            print(f"[cairn-jira] cleared {n} pending write(s) on {args.clear}")
        sys.exit(EXIT_OK)
    model = pending_model(root)
    if args.json:
        print(json.dumps(model))
        sys.exit(EXIT_OK)
    if not model:
        print("[cairn-jira] no pending mirror writes")
        sys.exit(EXIT_OK)
    for row in model:
        print(f"[cairn-jira] {row['bead']} ({row['external_ref'] or 'unlinked'}): "
              f"{row['title']}")
        for e in row["pending"]:
            extra = f" — {e['text'][:60]}" if e.get("text") else ""
            print(f"[cairn-jira]   {e.get('backend')} {e.get('action')} "
                  f"{e.get('key') or ''}{extra} ({e.get('at')})")
    sys.exit(EXIT_OK)


STATUS_WORDS = {"closed": {"done", "closed", "resolved", "concluído",
                           "concluido", "finalizado"},
                "in_progress": {"in progress", "em andamento", "doing"}}


def card_status(card):
    """The bead-side status the card's status maps to: the REST/MCP
    statusCategory when the card carries one (new / indeterminate / done),
    else the status name, else open."""
    status = ((card.get("fields") or {}).get("status") or {})
    cat = ((status.get("statusCategory") or {}).get("key") or "").lower()
    if cat:
        return {"new": "open", "indeterminate": "in_progress",
                "done": "closed"}.get(cat, "open")
    name = (status.get("name") or "").strip().lower()
    for bd_status, words in STATUS_WORDS.items():
        if name in words:
            return bd_status
    return "open"


def cmd_seen(args, root):
    """`seen --from-json FILE` — the session's half of a pull without a
    token (phase 45 / MIRROR-04): the card the MCP returned is recorded
    under .cairn/state.json seen.jira[key], exactly as gbsync pull would
    have, and the doctor names the divergence. Writes no bead."""
    try:
        raw = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        die(f"cannot read card JSON {args.from_json}: {exc}")
    key = str((raw or {}).get("key") or "").strip()
    if not JIRA_KEY_RE.match(key):
        die(f"card JSON {args.from_json}: 'key' {key!r} is not a Jira key")
    ref = REF_PREFIX + key
    holders = [i["id"] for i in source().issues(root)
               if str(i.get("external_ref") or "").strip() == ref]
    path = Path(root) / ".cairn" / "state.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except ValueError:
        state = {}
    if not isinstance(state, dict):
        state = {}
    entry = {"bd_id": holders[0] if holders else None,
             "status": card_status(raw),
             "title": ((raw.get("fields") or {}).get("summary") or "").strip(),
             "updated_at": (raw.get("fields") or {}).get("updated"),
             "at": datetime.datetime.now(datetime.timezone.utc)
             .strftime("%Y-%m-%dT%H:%M:%SZ")}
    state.setdefault("seen", {}).setdefault("jira", {})[key] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    if args.json:
        print(json.dumps({"key": key, **entry}))
        sys.exit(EXIT_OK)
    print(f"[cairn-jira] seen {key}: {entry['status']} "
          f"({'on ' + entry['bd_id'] if entry['bd_id'] else 'no bead linked'})")
    sys.exit(EXIT_OK)


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

    link = sub.add_parser("link", help="write external_ref jira-<KEY> on a "
                                       "milestone or phase carrier from a "
                                       "saved card JSON (REST shape)")
    link.add_argument("--from-json", required=True, metavar="FILE",
                      help="the card as the MCP/REST returned it")
    unlink = sub.add_parser("unlink", help="clear a carrier's jira link")
    for p in (link, unlink):
        p.add_argument("--milestone", metavar="vX.Y",
                       help="the cycle whose carrier is the target")
        p.add_argument("--phase", type=int, metavar="N",
                       help="the phase whose carrier is the target")
    link.set_defaults(func=cmd_link)
    unlink.set_defaults(func=cmd_unlink)

    links = sub.add_parser("links", help="list the cycle's links: story, "
                                         "epic, one sub-task per phase")
    links.add_argument("--milestone", metavar="vX.Y",
                       help="the cycle (default: the open one)")
    links.set_defaults(func=cmd_links)

    pending = sub.add_parser("pending", help="mirror writes waiting on beads "
                                             "(no credentials when they were "
                                             "made); --clear after a flush")
    pending.add_argument("--clear", metavar="BEAD",
                         help="drop the queue of this bead (after applying it)")
    pending.set_defaults(func=cmd_pending)

    seen = sub.add_parser("seen", help="record a card's status under "
                                       ".cairn/state.json seen.jira, as a "
                                       "pull would (read only)")
    seen.add_argument("--from-json", required=True, metavar="FILE",
                      help="the card as the MCP/REST returned it")
    seen.set_defaults(func=cmd_seen)

    for p in (detect, apply_, decline, link, unlink, links, pending, seen):
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
