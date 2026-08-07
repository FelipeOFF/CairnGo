#!/usr/bin/env python3
"""cairn-land — did this work enter the control branch, and which PR took it.

TWO QUESTIONS, TWO CONFIDENCES, AND THIS SCRIPT NEVER CONFUSES THEM
--------------------------------------------------------------------
    did the work enter the control branch?   git ancestry, local   EXACT
    which pull request took it there?        the local history     PARTIAL
    what state is that PR in?                gh/glab              NOT HERE

The first is what phase 30 exists for and it is answered offline, from the
repository already on disk, with no guess anywhere in the path. The second is
answered only as far as the local history actually carries it, and where it
does not, the answer is `unknown` WITH A NAMED REASON — never "no PR". The
third needs the network and lives behind config in a separate verb; the
default path of this script, and every path the board reaches, opens no
socket and invokes no network tool.

WHY THE ANSWER IS COMPUTED FROM `<branch>..HEAD` AND NOT FROM ONE
`git merge-base --is-ancestor` PER COMMIT
-------------------------------------------------------------------
`git merge-base --is-ancestor A B` is the exact primitive and it is what the
phase context prescribes, but it answers ONE pair per process. A board with
ten phases and two control branches would pay twenty processes per render.

`git rev-list HEAD --not <branch>` answers the same question for every commit
at once: it is exactly the set of commits reachable from HEAD that did NOT
enter <branch>. A commit read out of `git log HEAD` is therefore landed if and
only if it is absent from that set. Same verdict, one process per control
branch, and the set is bounded by how far ahead the checkout is — which is
precisely the quantity a healthy repo keeps small.

MEASURED 2026-08-06 in this repository: 530 commits reachable from HEAD, 385
from origin/main, and `git rev-list HEAD --not origin/main` is 145 lines. The
verdict for phase 29 is `unlanded`, which agrees with
`git merge-base --is-ancestor 6545a5c origin/main` returning false.

HOW A COMMIT IS ATTRIBUTED TO A PHASE — TWO SOURCES, BOTH NAMED
----------------------------------------------------------------
    path    the commit touched `<planning>/phases/<NN>-*/`
    scope   the conventional-commit scope names the phase: `feat(29-05)`,
            `chore(29)`, `docs(29-03)`

Both, because MEASURED 2026-08-06 each one alone loses real commits:

  * `6545a5c chore(29): fecha a fase 29 …`, the commit that CLOSES phase 29,
    touches ROADMAP.md / STATE.md / REQUIREMENTS.md and NOT the phase
    directory. Path alone never sees it.
  * 313 of this repository's 530 HEAD commits carry a phase scope, but that is
    a convention of this project. A repo that does not use it would be left
    with nothing. Scope alone is not portable.

An archived phase (its directory moved out of `<planning>/phases/`) is still
found by scope, which is the case that matters for the doctor's `fail` rung.

THE VERDICT VOCABULARY — EXACT VALUES, NEVER A NEGATION
--------------------------------------------------------
    landed     every attributed commit is reachable from the control branch
    partial    some are, some are not
    unlanded   none is
    unknown    the question could not be answered, and `reason` says why:
               `no-commits`   nothing in the local history is attributed to
                              this phase
               `no-branch`    no control branch could be resolved
               `no-git`       there is no readable git repository here

`unknown` is the state phase 23 made first class (VOID-01) wearing this
script's own noun. It is NEVER collapsed into `unlanded`: "I looked and it is
not there" and "I could not look" are different sentences, and only the first
one licenses anybody to act.

WHICH PULL REQUEST — TWO WORDS, AND NEITHER OF THEM IS "NONE"
--------------------------------------------------------------
    found     a commit attributed to the phase names a pull request, either
              in GitHub's own merge subject (`Merge pull request #6 from …`)
              or in the squash-merge title suffix (`… (#18)`)
    unknown   it does not, and `reason` says which kind of silence it is:
              `no-commits`    nothing is attributed to this phase at all
              `no-reference`  commits are attributed and none names a PR

THERE IS DELIBERATELY NO THIRD VERDICT. "There is no pull request" is a claim
about the forge, and nothing offline can make it. MEASURED 2026-08-06 over this
repository, and it is the case that decides whether this file is honest:

    commits carrying `(#N)` in the subject ......... 14
    merge commits naming `pull request #N` ......... 6
    pull request #21, which merged the whole v1.4
      milestone, became `7fa133c v1.4 Honest State:
      phase state that proves what it claims` —
      a real merge commit with two parents whose
      subject and body name no number at all ....... no trace

The most important merge in the project is invisible offline. Any surface here
that reported "no PR" for it would be lying about it while passing a green
suite, which is why `PR_LIMIT_DETAIL` is carried alongside every `unknown` and
why cmd_report() prints the word `unknown` and never the word `none`.

WHICH BRANCH IS THE CONTROL BRANCH
-----------------------------------
`git.control_branches` in `.cairn/config.json` — a comma-separated list,
because gitflow really does have two at once and "entrou na develop, ainda não
na main" is information rather than ambiguity. Read (never written) here
through cairn-config.py, which owns that file.

Empty config falls back to DETECTION, and the report says which of the two it
used, in `control.source`. The board is useful before anyone answers the
question, and `apply` is what turns a detection into a decision.

Detection precedence, and the first entry is why it degrades instead of dying:
    1. refs/remotes/origin/HEAD — MEASURED: `git symbolic-ref
       refs/remotes/origin/HEAD` exits 128 in THIS repository. The most
       obvious source does not exist here.
    2. conventional names present as refs: develop, dev, main, master, trunk
       (remote-tracking preferred over local, and BOTH develop and main are
       returned when both exist — that is the gitflow case, not a tie to
       break).
    3. the branch the current HEAD most descends from.

Usage:
    cairn-land.py detect [--project-dir DIR] [--json]
    cairn-land.py apply --branches a,b [--project-dir DIR] [--json]
    cairn-land.py report [--project-dir DIR] [--planning-dir DIR] [--json]

Exit codes:
    0  ok — including a report that answers `unknown` everywhere, which is an
       answer and not a failure
    2  usage error, or `apply` with a branch name no ref resolves
    3  nothing to do: `apply` with exactly the branches already on record
    5  a script this one depends on is unavailable or unreadable
       (cairn-config.py, the config's owner)
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
EXIT_NOTHING = 3
EXIT_NO_HELPER = 5

SCRIPT_DIR = Path(__file__).resolve().parent
CAIRN_CONFIG = SCRIPT_DIR / "cairn-config.py"

CONTROL_KEY = "git.control_branches"

# The names a project actually uses for a branch everything has to reach. Order
# is precedence: develop before main is deliberate, because in a gitflow repo
# develop is where work lands FIRST, and a board that reported only main would
# call every merged feature "not landed" for the whole life of a release.
CONVENTIONAL_BRANCHES = ("develop", "dev", "main", "master", "trunk")

# `feat(29-05): …`, `chore(29): …`, `docs(29-05)!: …`. The scope is the whole
# of what a conventional commit puts in parentheses, and the phase is the
# leading number in it — `29-05` is plan 5 of phase 29, so both forms attribute
# to 29.
COMMIT_SCOPE = re.compile(r"^[a-zA-Z]+(?:\(([^)]*)\))?!?:")
SCOPE_PHASE = re.compile(r"^0*(\d+)(?:-\d+)?$")
# The same directory grammar cairn-map and cairn-status resolve: an optional
# project-code prefix, then the zero-padded phase number.
PHASE_DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")

# Pull-request references a LOCAL history can actually carry, and nothing else
# is inferred from anywhere.
#
#   `Merge pull request #6 from FelipeOFF/…`   — GitHub's own merge subject
#   `feat(doctor): … (#18)`                    — the squash-merge title suffix
#
# MEASURED 2026-08-06 over this repository: 14 commits carry `(#N)`, 6 merge
# commits name a pull request, and the single most important merge in the
# project carries NEITHER. `7fa133c` is a real merge commit (two parents) whose
# subject reads `v1.4 Honest State: phase state that proves what it claims
# (ships cairn 1.5.0)` — it is pull request #21, and the local history does not
# say so anywhere.
#
# That measurement is the whole reason this file has no third verdict. "I found
# no reference" is a fact about the history; "there is no pull request" is a
# claim about GitHub, and nothing offline can make it.
MERGE_PR = re.compile(r"^Merge pull request #(\d+)\b")
SQUASH_PR = re.compile(r"\(#(\d+)\)\s*$")

PR_FOUND = "found"
PR_UNKNOWN = "unknown"
PR_SOURCE_MERGE = "merge-subject"
PR_SOURCE_SQUASH = "squash-subject"
REASON_NO_REFERENCE = "no-reference"
PR_LIMIT_DETAIL = (
    "the local git history is the only source consulted — a merge or squash "
    "whose subject was rewritten leaves no reference behind, so an absent "
    "number is never evidence that no pull request existed")

STATUS_LANDED = "landed"
STATUS_PARTIAL = "partial"
STATUS_UNLANDED = "unlanded"
STATUS_UNKNOWN = "unknown"

REASON_NO_COMMITS = "no-commits"
REASON_NO_BRANCH = "no-branch"
REASON_NO_GIT = "no-git"

# Record separator between commits, unit separator between a commit's fields.
# Neither can occur in a git object name, a subject line or a path, so the
# parse never has to guess where a record ended.
REC, UNIT = "\x1e", "\x1f"

USAGE = ("usage: cairn-land.py {detect | apply --branches a,b | report} "
         "[--project-dir DIR] [--planning-dir DIR] [--json]")


def die(msg, code=EXIT_USAGE):
    print(f"[cairn-land] error: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# git, read-only, and never through a shell
# --------------------------------------------------------------------------- #
def git(root, args):
    """(returncode, stdout) for one git invocation, or (None, "") when git
    could not be run at all.

    Every git read in this file goes through here, which is what makes the
    structural inventory in tests/cairn-land.bats able to say something: there
    is exactly ONE subprocess.run site for git, its argv literally starts with
    "git", and a repo with no git at all degrades to (None, "") rather than a
    traceback.
    """
    try:
        proc = subprocess.run(["git", "-C", str(root)] + [str(a) for a in args],
                              capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return proc.returncode, proc.stdout


def git_ok(root):
    """True when `root` is inside a readable git work tree."""
    code, out = git(root, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and out.strip() == "true"


def resolve_ref(root, name):
    """The object name a ref resolves to, or None.

    `--verify` plus the `^{commit}` peel is what stops a tag or a stray file of
    the same name from being mistaken for a branch.
    """
    code, out = git(root, ["rev-parse", "--verify", "--quiet",
                           f"{name}^{{commit}}"])
    if code != 0:
        return None
    return out.strip() or None


def all_branch_names(root):
    """[(short name, is_remote)] for every branch ref, in one for-each-ref call.

    The FULL refname is read and the prefix stripped here rather than asking
    for `%(refname:short)`, because the short form loses the one distinction
    that matters: a LOCAL branch called `feature/develop` and a
    remote-tracking `origin/develop` both short-form to something with a slash
    in it, and a reader that split on the slash would file the first one as a
    remote-tracking `develop`. The prefix says which is which; a heuristic
    over the short name does not.

    `origin/HEAD` is dropped: it is a symbolic pointer at another entry in this
    very list, not a branch anybody merges into.
    """
    code, out = git(root, ["for-each-ref", "--format=%(refname)",
                           "refs/remotes", "refs/heads"])
    if code != 0:
        return []
    out_names = []
    for line in out.splitlines():
        ref = line.strip()
        if ref.startswith("refs/remotes/"):
            short, remote = ref[len("refs/remotes/"):], True
        elif ref.startswith("refs/heads/"):
            short, remote = ref[len("refs/heads/"):], False
        else:
            continue
        if not short or short.endswith("/HEAD"):
            continue
        out_names.append((short, remote))
    return out_names


# --------------------------------------------------------------------------- #
# the control branch: detect, then confirm ONCE, then it is on record
# --------------------------------------------------------------------------- #
def detect_control(root):
    """(branches, source, detail) — the candidates, and the evidence for them.

    Never raises and never dies: a repo with no branches at all answers
    ([], "none", "..."), which is a fact the caller states rather than a
    failure it has to handle.
    """
    if not git_ok(root):
        return [], "none", f"{root} is not a readable git work tree"

    # 1. The symbolic ref the remote itself publishes. MEASURED 2026-08-06:
    #    exits 128 in this repository, so this branch of the code is the one
    #    that does NOT fire here, and everything below exists because of it.
    code, out = git(root, ["symbolic-ref", "refs/remotes/origin/HEAD"])
    if code == 0 and out.strip():
        short = out.strip()
        for prefix in ("refs/remotes/", "refs/heads/"):
            if short.startswith(prefix):
                short = short[len(prefix):]
                break
        return [short], "origin-head", (
            f"refs/remotes/origin/HEAD points at {short}")

    # 2. The conventional names, remote-tracking preferred. ALL of the ones
    #    that exist, not the first: two control branches at once is the
    #    gitflow case, and picking one in silence is the family of defect
    #    this milestone keeps paying for.
    # The branch HEAD is standing on, needed by BOTH passes below. A branch you
    # are already on contains your work by construction, so "did it enter that
    # branch" answers `landed` for everything and means nothing. MEASURED
    # 2026-08-06 while writing tests/cairn-land.bats: `git init` leaves the
    # checkout on a branch called `main` or `master`, so a detector that read
    # the conventional names without this exclusion reported EVERY phase of a
    # fresh repository as landed — a false green produced by the fixture, not
    # by the work. Only an explicit `apply` can name the current branch, and
    # then it is a decision somebody made rather than one this script invented.
    code, out = git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    current = out.strip() if code == 0 else ""

    names = all_branch_names(root)
    remote_by_tail, local = {}, set()
    for short, remote in names:
        if remote:
            remote_by_tail.setdefault(short.split("/", 1)[-1], short)
        elif short != current:
            local.add(short)
    found = []
    for conv in CONVENTIONAL_BRANCHES:
        if conv in remote_by_tail:
            found.append(remote_by_tail[conv])
        elif conv in local:
            found.append(conv)
    if found:
        return found, "conventional", (
            "conventional control branch name(s) present as refs: "
            + ", ".join(found))

    # 3. Last resort: the branch HEAD most descends from. `--count` over
    #    `<candidate>..HEAD` is small-first — the fewer commits HEAD is ahead
    #    by, the closer that branch is to being what HEAD was cut from. The
    #    current branch is excluded here for the same reason as above.
    best = None
    for short, _ in names:
        if short == current:
            continue
        code, out = git(root, ["rev-list", "--count", f"{short}..HEAD"])
        if code != 0:
            continue
        try:
            ahead = int(out.strip())
        except ValueError:
            continue
        if best is None or ahead < best[1]:
            best = (short, ahead)
    if best is not None:
        return [best[0]], "ancestry", (
            f"HEAD is {best[1]} commit(s) ahead of {best[0]}, the closest "
            "branch in this repository")
    return [], "none", "this repository has no branch to compare against"


def run_config(root, argv):
    """(returncode, stdout) for cairn-config.py, or (None, "") when it could
    not be run. Same defensive shape cairn-jira.py uses for the same file: the
    config has ONE owner, and this script is not it."""
    try:
        proc = subprocess.run(
            [sys.executable, str(CAIRN_CONFIG)] + [str(a) for a in argv],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return proc.returncode, proc.stdout


def read_control_config(root):
    """The recorded control branches, as a list (empty = never answered).

    Exit 5 when the config's owner cannot be read. An unreadable record must
    never be reported as "never answered", because that is how a decision
    quietly loses its force — the same rule cairn-jira.py's read_answer()
    states for the same file.
    """
    code, out = run_config(root, ["get", CONTROL_KEY, "--project-dir",
                                  str(root), "--json"])
    if code is None or code != EXIT_OK:
        die(f"could not read {CONTROL_KEY} through {CAIRN_CONFIG.name} — the "
            "recorded control branch is unknown, and falling back to "
            "detection would silently overrule a decision somebody made",
            EXIT_NO_HELPER)
    try:
        payload = json.loads(out or "null")
    except json.JSONDecodeError:
        payload = None
    value = payload.get("value") if isinstance(payload, dict) else None
    return split_branches(value)


def split_branches(value):
    """A comma-separated config string as a list, order preserved, blanks and
    duplicates dropped."""
    out = []
    for part in str(value or "").split(","):
        part = part.strip()
        if part and part not in out:
            out.append(part)
    return out


def control_branches(root):
    """(branches, source, detail) — config if it was answered, detection
    otherwise, and the caller is always told which."""
    recorded = read_control_config(root)
    if recorded:
        return recorded, "config", (
            f"{CONTROL_KEY} on record: {', '.join(recorded)}")
    branches, source, detail = detect_control(root)
    if not branches:
        return [], "none", detail
    return branches, "detected", detail + " (not confirmed — run /cairn:land)"


# --------------------------------------------------------------------------- #
# the history, read once
# --------------------------------------------------------------------------- #
def phase_dir_numbers(planning_dir):
    """{phase number: directory name} under <planning>/phases/."""
    out = {}
    root = Path(planning_dir) / "phases"
    if not root.is_dir():
        return out
    try:
        entries = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError:
        return out
    for d in entries:
        m = PHASE_DIR_PREFIX.match(d.name)
        if m:
            out.setdefault(int(m.group(1)), d.name)
    return out


def scope_phase(subject):
    """The phase number a conventional-commit subject names in its scope, or
    None. `feat(29-05): …` and `chore(29): …` both answer 29; `fix(sync): …`
    and a subject with no scope answer None."""
    m = COMMIT_SCOPE.match(subject or "")
    if not m or not m.group(1):
        return None
    m2 = SCOPE_PHASE.match(m.group(1).strip())
    return int(m2.group(1)) if m2 else None


def read_history(root, planning_dir):
    """{phase number: [commit dicts]} plus the flat list, from git log of HEAD.

    TWO log calls, deliberately, and neither one carries a commit body:

      1. `--name-only` restricted to the phases pathspec, so the output is
         bounded by the planning tree rather than by the whole repository.
      2. subjects only, over HEAD, for the scope attribution and (plan 30-02)
         the pull-request scan. MEASURED 2026-08-06: 80605 bytes for this
         repository's 530 commits. The same log WITH bodies is 476216 bytes,
         which is why the body is not read: the only thing it was going to be
         used for was attributing a commit to a bd issue, and MEASURED, all 41
         body mentions of a bd id in this history are prose references
         (`bd issue CairnGo-gbu`, `(CairnGo-0rk)`), not attributions. Reading
         six times the bytes to infer a link nobody wrote is how a board
         invents a fact.
    """
    commits = {}
    order = []

    def note(sha, subject):
        if sha not in commits:
            commits[sha] = {"sha": sha, "subject": subject, "phases": set(),
                            "sources": set()}
            order.append(sha)
        return commits[sha]

    dirs = phase_dir_numbers(planning_dir)
    rel = phases_pathspec(root, planning_dir)
    if dirs and rel is not None:
        code, out = git(root, ["log", f"--format={REC}%H{UNIT}%s",
                               "--name-only", "HEAD", "--", rel])
        if code == 0:
            by_name = {name: n for n, name in dirs.items()}
            for record in out.split(REC):
                if not record.strip():
                    continue
                head, _, names = record.partition("\n")
                sha, _, subject = head.partition(UNIT)
                sha = sha.strip()
                if not sha:
                    continue
                for path in names.splitlines():
                    part = path.strip()
                    if not part:
                        continue
                    n = phase_of_path(part, by_name)
                    if n is None:
                        continue
                    c = note(sha, subject)
                    c["phases"].add(n)
                    c["sources"].add("path")

    code, out = git(root, ["log", f"--format={REC}%H{UNIT}%s", "HEAD"])
    if code == 0:
        for record in out.split(REC):
            if not record.strip():
                continue
            sha, _, subject = record.strip("\n").partition(UNIT)
            sha = sha.strip()
            if not sha:
                continue
            subject = subject.strip("\n")
            n = scope_phase(subject)
            if n is None:
                # Still recorded: plan 30-02 scans every subject for a pull
                # request, and a commit with no phase scope can perfectly well
                # be the merge that carried one.
                note(sha, subject)
                continue
            c = note(sha, subject)
            c["phases"].add(n)
            c["sources"].add("scope")

    by_phase = {}
    for sha in order:
        c = commits[sha]
        for n in c["phases"]:
            by_phase.setdefault(n, []).append(c)
    return by_phase, [commits[s] for s in order]


def phases_pathspec(root, planning_dir):
    """`<planning>/phases` relative to the repo root, or None when the planning
    dir is not inside it (a --planning-dir pointed at another checkout)."""
    try:
        return str((Path(planning_dir) / "phases").resolve().relative_to(
            Path(root).resolve()))
    except (ValueError, OSError):
        return None


def phase_of_path(path, by_name):
    """The phase number a `<planning>/phases/<dir>/...` path belongs to."""
    parts = path.split("/")
    for i, part in enumerate(parts):
        if part == "phases" and i + 1 < len(parts):
            return by_name.get(parts[i + 1])
    return None


def unlanded_sets(root, branches):
    """{branch: set of shas reachable from HEAD but NOT from that branch}.

    One `git rev-list HEAD --not <branch>` per control branch. A branch that
    does not resolve is absent from the result, which is what makes
    `no-branch` reachable instead of a silent all-landed.
    """
    out = {}
    for name in branches:
        if resolve_ref(root, name) is None:
            continue
        code, text = git(root, ["rev-list", "HEAD", "--not", name])
        if code != 0:
            continue
        out[name] = {line.strip() for line in text.splitlines() if line.strip()}
    return out


def pr_of_subject(subject):
    """(number, source) for one commit subject, or (None, None).

    Merge subject before squash suffix: `Merge pull request #6 from …` is
    unambiguous, while a trailing `(#N)` is a convention a project can also use
    for an issue. Both are read only from the SUBJECT — the body is never
    fetched (see read_history() for the 476216-versus-80605 measurement).
    """
    m = MERGE_PR.match(subject or "")
    if m:
        return int(m.group(1)), PR_SOURCE_MERGE
    m = SQUASH_PR.search(subject or "")
    if m:
        return int(m.group(1)), PR_SOURCE_SQUASH
    return None, None


def pr_for_commits(commits):
    """The pull request a phase's commits name, or `unknown` WITH ITS REASON.

    THERE IS NO THIRD VERDICT, AND THAT IS THE POINT. This function can answer
    `found` or `unknown`; it can never answer "there is no pull request",
    because that sentence is a claim about the forge and this function only
    ever read a git repository. Reporting "no PR" for `7fa133c` — pull request
    #21, the merge that brought an entire milestone — would be the loudest
    possible version of the defect, and it would pass a green suite.

    `commits` arrives newest-first (git log order), so `number` is the newest
    reference and `numbers` carries every distinct one, which is what a phase
    delivered across two pull requests actually looks like.
    """
    if not commits:
        return {"status": PR_UNKNOWN, "number": None, "numbers": [],
                "source": None, "commit": None, "reason": REASON_NO_COMMITS,
                "detail": PR_LIMIT_DETAIL}
    numbers, first = [], None
    for c in commits:
        n, source = pr_of_subject(c["subject"])
        if n is None:
            continue
        if n not in numbers:
            numbers.append(n)
        if first is None:
            first = (n, source, c["sha"])
    if first is None:
        return {"status": PR_UNKNOWN, "number": None, "numbers": [],
                "source": None, "commit": None, "reason": REASON_NO_REFERENCE,
                "detail": f"{len(commits)} commit(s) attributed to this phase "
                          f"and none of them names a pull request — "
                          f"{PR_LIMIT_DETAIL}"}
    return {"status": PR_FOUND, "number": first[0], "numbers": sorted(numbers),
            "source": first[1], "commit": first[2], "reason": None,
            "detail": None}


def verdict(shas, unlanded):
    """`landed` / `partial` / `unlanded` for a commit set against ONE branch.

    Asserted on the exact counts, never on "not all": a set with nothing in it
    never reaches here — read_phase_state() answers `unknown` first — so these
    three are exhaustive over a non-empty set.
    """
    missing = sum(1 for s in shas if s in unlanded)
    if missing == 0:
        return STATUS_LANDED
    if missing == len(shas):
        return STATUS_UNLANDED
    return STATUS_PARTIAL


def combine(per_branch):
    """The one word for a phase across every control branch.

    The RULE, and it is the gitflow case stated as code: a phase is `landed`
    only when it is landed on EVERY control branch. Landed on develop and not
    on main is `partial` — which is exactly "entrou na develop, ainda não na
    main", and the per-branch map right beside it says which is which.
    """
    values = list(per_branch.values())
    if not values:
        return STATUS_UNKNOWN
    if all(v == STATUS_LANDED for v in values):
        return STATUS_LANDED
    if all(v == STATUS_UNLANDED for v in values):
        return STATUS_UNLANDED
    return STATUS_PARTIAL


def build_report(root, planning_dir):
    """The whole answer, as one dict — the report every consumer renders from.

    Consumers (cairn-status.py's board, cairn-doctor.py's phase-landed check)
    read THIS and re-derive nothing. Two readers of git that could disagree
    about the same repository is the defect this milestone has already paid
    for twice.
    """
    branches, source, detail = control_branches(root)
    control = {"branches": branches, "source": source, "detail": detail}
    if not git_ok(root):
        # Every key the answered path returns, including `answered` itself. A
        # degraded return that drops a key is a KeyError in the renderer two
        # lines later, which is how "degrades gracefully" becomes a traceback.
        return {"control": control, "phases": {}, "answered": False,
                "reason": REASON_NO_GIT, "_commits": [],
                "detail": f"{root} is not a readable git work tree"}
    by_phase, all_commits = read_history(root, planning_dir)
    unlanded = unlanded_sets(root, branches)
    phases = {}
    for n in sorted(by_phase):
        commits = by_phase[n]
        shas = [c["sha"] for c in commits]
        row = {
            "commits": len(shas),
            "tip": shas[0],
            "sources": sorted({s for c in commits for s in c["sources"]}),
            "branches": {},
            "reason": None,
            "pr": pr_for_commits(commits),
        }
        if not unlanded:
            row["status"] = STATUS_UNKNOWN
            row["reason"] = REASON_NO_BRANCH
        else:
            for name, missing in unlanded.items():
                row["branches"][name] = verdict(shas, missing)
            row["status"] = combine(row["branches"])
        phases[str(n)] = row

    # `answered` is a DIFFERENT question from any phase's status, so it gets a
    # different key and a different vocabulary: it says whether the report
    # could be produced at all, never how the roadmap is doing. One word
    # summarising every phase would be a second number for a quantity that
    # already has a row per phase directly below it.
    if not unlanded:
        answered, reason, why = False, REASON_NO_BRANCH, detail
    elif not phases:
        answered, reason, why = (
            False, REASON_NO_COMMITS,
            "no commit in the local history is attributed to any phase")
    else:
        answered, reason, why = (
            True, None,
            f"{len(phases)} phase(s) located in the local history, compared "
            f"against {', '.join(sorted(unlanded))}")
    return {"control": control, "phases": phases, "answered": answered,
            "reason": reason, "detail": why, "_commits": all_commits}


# --------------------------------------------------------------------------- #
# the verbs
# --------------------------------------------------------------------------- #
def emit(as_json, payload, lines):
    if as_json:
        print(json.dumps({k: v for k, v in payload.items()
                          if not k.startswith("_")}))
    else:
        for line in lines:
            print(line)


def cmd_detect(args, root):
    branches, source, detail = detect_control(root)
    recorded = read_control_config(root)
    payload = {"branches": branches, "source": source, "detail": detail,
               "recorded": recorded,
               "already": bool(recorded),
               "ask": bool(branches) and not recorded}
    lines = [f"[cairn-land] {root}"]
    if recorded:
        lines.append(f"[cairn-land] ✓ on record: {', '.join(recorded)} "
                     f"({CONTROL_KEY})")
    if branches:
        lines.append(f"[cairn-land] ▸ detected: {', '.join(branches)}")
        lines.append(f"[cairn-land]   evidence: {detail}")
        if not recorded:
            lines.append("[cairn-land] ! not on record yet — confirm with "
                         f"cairn-land.sh apply --branches {','.join(branches)}")
    else:
        lines.append(f"[cairn-land] ⚠ nothing detected: {detail}")
    emit(args.json, payload, lines)
    sys.exit(EXIT_OK)


def cmd_apply(args, root):
    branches = split_branches(args.branches)
    if not branches:
        die("--branches needs at least one branch name", EXIT_USAGE)
    unknown = [b for b in branches if resolve_ref(root, b) is None]
    if unknown:
        # Refused, not written. A control branch nobody can resolve turns every
        # verdict into `unknown` forever, and a config that reads plausibly
        # while answering nothing is worse than no config at all.
        die(f"no ref resolves: {', '.join(unknown)} — nothing was written",
            EXIT_USAGE)
    recorded = read_control_config(root)
    if recorded == branches:
        payload = {"branches": recorded, "written": False,
                   "reason": "already on record"}
        emit(args.json, payload,
             [f"[cairn-land] ✓ {CONTROL_KEY} already reads "
              f"{', '.join(recorded)} — nothing rewritten"])
        sys.exit(EXIT_NOTHING)
    code, _ = run_config(root, ["set", CONTROL_KEY, ",".join(branches),
                                "--project-dir", str(root), "--json"])
    if code is None or code != EXIT_OK:
        die(f"could not record {CONTROL_KEY} through {CAIRN_CONFIG.name} — "
            "the answer would not survive the session", EXIT_NO_HELPER)
    payload = {"branches": branches, "written": True, "reason": None}
    emit(args.json, payload,
         [f"[cairn-land] ✓ {CONTROL_KEY} = {', '.join(branches)} "
          f"(.cairn/config.json) — read by cairn-status.py and cairn-doctor.py"])
    sys.exit(EXIT_OK)


def cmd_report(args, root):
    planning_dir = (Path(args.planning_dir).resolve() if args.planning_dir
                    else root / ".planning")
    report = build_report(root, planning_dir)
    control = report["control"]
    lines = [f"[cairn-land] {root} — control branch: "
             f"{', '.join(control['branches']) or 'unresolved'} "
             f"({control['source']})"]
    for n in sorted(report["phases"], key=lambda s: int(s)):
        row = report["phases"][n]
        where = ", ".join(f"{b}: {v}" for b, v in sorted(
            row["branches"].items())) or (row["reason"] or "")
        pr = row["pr"]
        # `pr unknown :: <reason>`, never "no PR". The word this line is not
        # allowed to print is the one an offline reader cannot justify.
        pr_text = (f"pr #{pr['number']} ({pr['source']})"
                   if pr["status"] == PR_FOUND
                   else f"pr {PR_UNKNOWN} :: {pr['reason']}")
        lines.append(f" phase {n:>3}  {row['status']:<9} {row['commits']:>3} "
                     f"commit(s)  {where}  {pr_text}")
    if not report["answered"]:
        lines.append(f" {STATUS_UNKNOWN} :: {report['reason']} — "
                     f"{report['detail']}")
    emit(args.json, report, lines)
    sys.exit(EXIT_OK)


def build_parser():
    p = argparse.ArgumentParser(prog="cairn-land.py", add_help=True,
                                description=USAGE)
    p.add_argument("--project-dir")
    p.add_argument("--json", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    for name in ("detect", "apply", "report"):
        s = sub.add_parser(name)
        s.add_argument("--project-dir")
        s.add_argument("--json", action="store_true")
        if name == "apply":
            s.add_argument("--branches")
        if name == "report":
            s.add_argument("--planning-dir")
    return p


def resolve_root(project_dir):
    if project_dir:
        return Path(project_dir).resolve()
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()


def main():
    argv = sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        die(USAGE, EXIT_USAGE)
    root = resolve_root(args.project_dir)
    if not root.is_dir():
        die(f"no such directory: {root}", EXIT_USAGE)
    {"detect": cmd_detect, "apply": cmd_apply,
     "report": cmd_report}[args.cmd](args, root)


if __name__ == "__main__":
    main()
