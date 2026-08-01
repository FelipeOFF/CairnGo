#!/usr/bin/env python3
"""cairn-parallel — turn the parallelism ANNOUNCEMENT into real, isolated
working trees.

cairn-status.py's parallelism() has been answering "phases 14 and 15 are
independent — one agent per phase, or one worktree each" since phase 13, and
until this script nobody consumed that answer: the loop announced parallelism
and then ran in single file. That gap is the dishonesty this milestone exists
to remove, and this file is the missing consumer.

Three verbs ship now; `cleanup` (18-03) lands in this SAME file later, which
is why argparse arrived with subparsers from the first commit.

    batch      what can run at once, with each phase's branch name and
               worktree path already resolved — the text /cairn:autonomous
               step 0.4 announces before it spawns anything.
    prepare N  create that named worktree for phase N and take phase N's
               lease pointing AT it.
    reconcile  read-only report over the branches `prepare` named: what each
               phase produced, the merge conflicts git will raise, and — the
               part nobody else does — the CONVERGENT EDIT git resolves in
               silence.


WHY CAIRN NAMES THE WORKTREE, NOT THE HARNESS (D-01)
----------------------------------------------------
The worktree is `<parent-of-root>/<root-basename>-phase-<N>` on branch
`phase/<N>-<slug>`, both derived from the phase number and the phase
directory's own basename. Nothing about either is negotiated with the agent
that works there: `prepare` prints the path, and the caller hands it over.

The rejected alternative was letting the harness create it (the Agent tool's
`isolation: "worktree"`). A harness worktree is temporary and generated-named,
so reconciliation (plan 18-02) would have to ASK THE AGENT where it worked —
self-declared information, the exact vice phase 17 removed when it moved the
list of what an investigator read out of the agent's narrative and into the
collector. Determinism here is what lets `reconcile` discover the work by
scanning `refs/heads/phase/*`, with no agent testimony involved. It also keeps
cairn to `git` and `bd` and nothing else, instead of binding it to one
harness's feature.


WHY THERE IS NO `--holder` FLAG (D-01, and phase 17's principle again)
----------------------------------------------------------------------
`prepare` never tells cairn-lease.py who is acquiring. It points
`--project-dir` at the freshly created worktree and lets cairn-lease.py
resolve identity itself, the way it always does: `git -C <dir> rev-parse
--show-toplevel`. A `--holder` flag would let the caller DECLARE an identity,
and a declared identity is not evidence of anything. Provoking the existing
resolver is the whole mechanism — the lease ends up naming the physical
worktree path, and that is what makes "phase N is owned by that tree over
there" a checkable fact rather than a claim.


ORDER OF ACQUISITION IN `prepare`, AND WHY THE PRE-CHECK IS ONLY ECONOMY
------------------------------------------------------------------------
1. `cairn-lease.py status <N> --json` (read-only; it NEVER creates the lease
   issue). Held by someone ELSE with a live heartbeat -> refuse right here,
   naming the holder and acquired_at, EXIT_HELD, having created nothing. A
   live lease whose holder IS the worktree this call would use is not a
   refusal — that is the idempotent re-prepare, and acquire reads it as
   already_mine. The comparison goes through realpath on both sides, never a
   string compare, for the /var -> /private/var reason below.
2. `git worktree add -b <branch> <path> HEAD`.
3. `cairn-lease.py acquire <N> --project-dir <the new worktree>`.
4. If THAT returns 3 — someone won the race inside the window between 1 and 3
   — undo what THIS invocation created and exit EXIT_HELD.

Step 1 is an economy, never a guarantee: it makes the common refusal cost one
read and zero writes. The authority over the race is step 3, because
cairn-lease.py's acquire is the only place the check and the write happen
against the same bd state. Step 4 exists precisely because step 1 can be
raced, and it is the branch the rollback test exercises through the
CAIRN_LEASE seam — a real second worktree can only ever exercise step 1.

The rollback only ever touches what this invocation created: `created_worktree`
and `created_branch` are recorded as local facts, and before removing anything
the path is re-confirmed through `git worktree list --porcelain` to still be a
worktree OF THIS REPO on the expected branch. A pre-existing worktree is never
removed and a pre-existing branch is never deleted (T-18-03).


KNOWN, ACCEPTED LIMITATION: THE PARALLEL AGENT'S JOURNAL DIES WITH ITS TREE
---------------------------------------------------------------------------
Measured, not assumed: `.planning/` and `.cairn/` live under each worktree's
OWN checkout, not under `--git-common-dir`. So the journal a parallel agent
writes lands in `<worktree>/.cairn/journal.jsonl` and disappears when that
worktree is removed. This is recorded and NOT solved here; a durable
cross-worktree journal is JOUR-06 (v2). The same split is why D-03 forbids
STATE.md / ROADMAP.md / REQUIREMENTS.md inside a phase worktree, which
`prepare` reports back as `planning_files_forbidden` for whoever assembles the
subagent's prompt.

The opposite was also measured: `bd list` AND `bd create`/`bd update` from a
second worktree resolve to the MAIN repo's database — no local DB, no daemon,
no global registry. That is what makes the lease work across worktrees at all
(cairn-lease.py's own docstring records the same measurement).


NOTHING HERE USES `git stash`
-----------------------------
Measured: `refs/stash` is SHARED across every worktree of a repo — it lives in
the common git dir, so a stash pushed in one tree is visible, and poppable, in
all of them. A script that stashed to make room for a checkout would silently
reach into a sibling agent's working state. Every git operation in this file is
therefore additive (`worktree add`) or scoped to a path this invocation itself
created (`worktree remove`, `branch -D`).


WHY `batch` CONSUMES parallelism() AND NEVER RECOMPUTES IT
-----------------------------------------------------------
`batch` reads `parallelism.runnable` / `.blocked` / `.declared` / `.note` from
one `cairn-status.py --json` call and treats those numbers as given.
Independence is computed in exactly one place in this codebase, and this
script is a consumer of it. A second computation here would be a SECOND TRUTH
about what can run — which is the defect this whole milestone exists to
eliminate. `declared` and `note` are passed through verbatim for the same
reason: the honesty flag belongs to whoever computed it.

`batch` then subtracts two things, each with a named reason: a phase whose
lease is held by a live holder (it already has an owner), and anything past
`--max`. A `stale` lease does NOT disqualify a phase — cairn-lease.py's own
acquire knows how to reclaim one — it is only flagged `lease_stale: true`.

`--max` defaults to 3, and the number is discretionary: three full checkouts
and three agents is about what one person can actually review before the
review becomes rubber-stamping. It is a ceiling on human attention, not on
anything git or bd cares about, and `--max` exists so it can be raised.

The bridge from `batch` to `prepare` is a CONTRACT, not just a shared function:
what `batch` announces as `branch`/`worktree` has to be byte-for-byte what
`prepare` creates, because `reconcile` (18-02) finds the work by the name
`prepare` gave it, not by the name `batch` announced. One shared resolver
(`phase_layout`) makes divergence unlikely; the test that runs both verbs over
two phases and compares by realpath is what makes it PROVEN.


WHAT `reconcile` IS FOR: THE EDIT GIT RESOLVES IN SILENCE (D-02)
-----------------------------------------------------------------
The division of labour is the whole design. git reports merge conflicts, and
it reports them well; nobody needs cairn for that. What only cairn can report
is the ACCIDENTAL AGREEMENT — the line both branches changed to the SAME
value, which git merges without a word precisely because the two sides are
byte-identical. `reconcile` reports both, but only the second is a claim git
does not already make.

It exists because it happened, here. Phases 14 and 15 of this milestone were
executed in parallel, in two worktrees, and merged. Each had added one check,
so each changed the same count from 13 to 14, for its own reason. git saw two
identical changes and took one. The merged tree carried 15 checks, a docstring
saying 14, and TWO items numbered 13.

Measured on the two REAL parents of that merge (b9c608f / b0466aa of 672e754),
not reconstructed from memory:

    $ git merge-tree --write-tree b9c608f b0466aa        # exit 1
    CONFLICT (content): Merge conflict in cairn/docs/commands/doctor.md
    Auto-merging cairn/scripts/cairn-doctor.py
    Auto-merging tests/cairn-doctor.bats

One conflict, and in a DIFFERENT file. The two files carrying the damage —
each holding the convergent count AND the distinct block its own phase had
added — merged clean. `Auto-merging <path>` is not a warning about anything:
it is git saying it joined that file with no trouble at all.

The same shape, rebuilt as this plan's fixture and measured again: the count
on line 1 convergent on both sides, each branch adding its own block at its
own distant marker. `merge-tree --write-tree` exits 0 with no CONFLICT line at
all; the real `git merge` exits 0 printing `Auto-merging checks.txt` and
`1 file changed, 1 insertion(+)`; and the merged file reads `checks = 14` with
two items numbered `check 13`. The entire incident, duplicate numbering
included, inside a merge git called clean.

Distance is what decides, not same-file-ness. The convergence and the
divergence can live in one file without conflicting, as long as they are far
enough apart — which is exactly what made the real merge look fine.


HOW THE CONVERGENT EDIT IS DETECTED, AND EXACTLY WHAT THAT CLAIM COVERS
------------------------------------------------------------------------
For every unordered pair of phase branches: base = `git merge-base X Y`. Each
side's `git diff -U0 <base>..<side>` is parsed into, per file, a list of
`(start in the base, how many base lines are replaced, the new lines
verbatim)`. A CONVERGENT EDIT is declared when a file appears on BOTH sides
carrying a hunk whose base range is EQUAL on both sides and whose new block of
lines is byte-for-byte identical. Nothing looser than that.

The measured hunks of the fixture above are what strict equality catches:

    base..X    @@ -1 +1 @@    -checks = 13    +checks = 14
    base..Y    @@ -1 +1 @@    -checks = 13    +checks = 14

An identical-and-empty new block (both sides deleting the same base range) is
convergent by the same rule and for the same reason: two silent agreements
about what should go away is still an agreement nobody reviewed.

What the claim does NOT cover, said out loud so nobody reads more into it:
partial overlap with different content is a CONFLICT, and conflicts are git's
job. This script asserts exactly what it measured and no more.

MEASURED LIMIT, with the arrangement that produces it. When a branch's added
block sits ADJACENT to the convergent line, `-U0` coalesces the two changes
into a single hunk:

    base..A    @@ -1 +1,2 @@        base..B    @@ -1 +1,2 @@

The base ranges now match while the new blocks differ, so convergence is NOT
declared. In that same arrangement git itself conflicts (`merge-tree` exits 1,
`CONFLICT (content)`), so the operator is stopped anyway: the detector's gap
coincides with git's catch. This is recorded as a measured limit rather than
discovered later as a bug, which is the difference between "does not cover"
and "covers and stays quiet".


WHY `reconcile` ONLY READS COMMITTED REFS, AND WRITES NOTHING
--------------------------------------------------------------
Every fact in the report comes from `git for-each-ref`, `git rev-list`,
`git diff`, `git merge-base` and `git merge-tree` over committed refs. No path
inside a live phase worktree is ever opened. A parallel agent is still editing
those files while this runs, and a report built from a half-written file is
confidently wrong (Pitfall 15).

`reconcile` performs no merge, no checkout and no write. It cannot resolve a
conflict — silently or otherwise — because resolving is not among the things
it is able to do. That is a property of the code, not a promise of prose, and
it is proven twice, the way phase 17 proved the same thing for
cairn-reconcile.py. First, a grep over the region delimited by the
`reconcile: read-only region BEGIN` / `END` markers, with comment lines
filtered out (the comments in there DISCUSS the verbs they forbid, so a grep
over the raw text would invalidate itself), finds no bd write verb, no
cairn-journal write subcommand, and no writing git verb. Second, a bats test
runs the command against a real fixture and shows `git status --porcelain`,
every `phase/*` branch head, and a hash of every file in the tree unchanged
afterwards. One proof is about what the code says; the other is about what it
does, and neither substitutes for the other.

`merge-tree --write-tree` does add loose objects to the object database — that
is precisely what lets it compute a merge without a working tree. It moves no
ref and touches no file, which is why the mutation test above is the right
shape of proof for it.


WHY A CLEAN REPORT AND AN UNKNOWN ONE ARE NOT THE SAME EXIT (Pitfall 3)
------------------------------------------------------------------------
`git merge-tree --write-tree` needs git 2.38+. On an older git the option does
not exist, and the honest answer there is not an empty conflict list: an empty
list reads as "clean", and failing open into a false all-clear reproduces the
exact bug this milestone exists to kill. So `conflicts` becomes null,
`conflicts_note` says why and says git will report them at merge time, and the
exit is 6 all the same — the script cannot say the merge is clean, so it does
not say it. Every report carries `git_version` for the same reason.

Exit 6 (EXIT_FINDINGS) is a report, not a verdict: it fires on a convergent
edit, on a conflict, and on not-knowing. A planning write does NOT change it —
D-03's reporting half is a named finding, and "fail the reconciliation when a
phase branch touched a planning file" is deliberately parked in
18-CONTEXT.md's <deferred>. Reporting is not failing. What 6 buys is that a
caller running under `set -e` cannot mistake a silently-convergent merge for
success, which is the entire mechanism; it resolves nothing.


Usage:
    cairn-parallel.py batch     [--max N] [--project-dir DIR] [--json]
    cairn-parallel.py prepare N [--project-dir DIR] [--json]
    cairn-parallel.py reconcile [--phases 7,9] [--project-dir DIR] [--json]

    --project-dir DIR   project root for git/bd discovery (default:
                        $CLAUDE_PROJECT_DIR or cwd)
    --max N             ceiling on how many phases `batch` selects
                        (default: 3)
    --phases LIST       comma-separated phase numbers `reconcile` restricts
                        itself to (default: every phase/* branch)
    --json              machine-readable output instead of the
                        `[cairn-parallel] ...` human lines

Behavior:
    batch      Calls `cairn-status.py --json` ONCE (through the CAIRN_STATUS
               seam) and reports:
                 {runnable, blocked, declared, note, max, selected[],
                  deferred[], announcement}
               `selected[]` entries carry {phase, title, slug, branch,
               worktree, next_command, reason, lease_stale}; `deferred[]`
               entries carry {phase, reason}. `announcement` is the ready-made
               text for /cairn:autonomous step 0.4: how many phases run, why
               each one, what was left out and why, plus the honesty line when
               `declared` is false.

    prepare N  Runs from the MAIN checkout only — invoked from a linked
               worktree it refuses with EXIT_USAGE, because a worktree of a
               worktree is not what any of this names. Resolves slug, branch
               and path; runs the four-step acquisition above; reports:
                 {phase, slug, branch, worktree, base_commit, created,
                  lease: {holder, acquired_at}, planning_files_forbidden[]}
               Idempotent: an existing worktree at the expected path, on the
               expected branch, re-acquires (already ours -> exit 0) and
               reports `created: false`. A path that exists but is NOT a
               worktree of this repo on that branch, or a branch that already
               exists with no worktree at the expected path, is EXIT_GIT with
               nothing touched.

    reconcile  Discovers the work by scanning `refs/heads/phase/*` — the
               names `prepare` gave it, never an agent's testimony (D-01) —
               and reports, writing nothing anywhere:
                 {git_version, branches[], pairs[], planning_writes[],
                  findings_total}
               `branches[]` entries carry {phase, branch, base, commits,
               files, insertions, deletions}: what that phase produced,
               measured against `git merge-base HEAD <branch>` (PAR-04).
               `pairs[]` entries carry {branches, base, convergent_edits,
               conflicts, conflicts_note}; a convergent edit is
               {file, base_line, base_count, new_lines, branches}, its text
               truncated to 200 characters per line. `planning_writes[]`
               names any branch whose diff touches .planning/STATE.md,
               .planning/ROADMAP.md or .planning/REQUIREMENTS.md — a named
               finding with no effect on the exit code (D-03).
               A repo with no phase/* branch exits 0 with empty lists and
               says there is nothing to reconcile.

Exit codes:
    0  ok (including `created: false` — reusing an existing tree is success,
       and a `reconcile` that found neither a conflict nor a convergent edit)
    2  usage error (bad/missing phase, `prepare` run from a linked worktree,
       unusable --max or --phases, or a downstream script that could not be
       driven)
    3  the phase's lease is held by another live holder — nothing was
       created, or everything this invocation created was rolled back. A
       report, not an error, exactly as cairn-lease.py reads its own 3
    4  git refused: the worktree path is occupied by something else, the
       branch already exists without its worktree, or `git worktree add`
       itself failed
    5  bd unavailable, or a companion script (cairn-lease.py /
       cairn-status.py) is missing
    6  `reconcile` has findings: a convergent edit, a merge conflict, or a
       git too old to pre-compute conflicts at all. A report the caller
       cannot mistake for success, never a resolution

Test/override seams (CONVENTIONS.md's CAIRN_* env-seam note, same shape as
CAIRN_GBSYNC / CAIRN_MAP / CAIRN_GATE / CAIRN_JOURNAL):
    CAIRN_LEASE    default: the sibling cairn-lease.py
    CAIRN_STATUS   default: the sibling cairn-status.py
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
EXIT_HELD = 3
EXIT_GIT = 4
EXIT_NO_BD = 5
# `reconcile` found something, or could not rule something out. Follows the
# house reading of 6 as "gate failed" (cairn-gate.py); it is the mechanism
# that stops a silent pass, and it resolves nothing.
EXIT_FINDINGS = 6

SCRIPTS_DIR = Path(__file__).resolve().parent

CAIRN_LEASE = os.environ.get(
    "CAIRN_LEASE", str(SCRIPTS_DIR / "cairn-lease.py"))
CAIRN_STATUS = os.environ.get(
    "CAIRN_STATUS", str(SCRIPTS_DIR / "cairn-status.py"))

# Phase directory numeric-prefix matching — the house convention is that each
# script carries its own copy of this regex rather than sharing a lib (same
# shape as cairn-gate.py's PHASE_DIR_PREFIX, cairn-doctor.py's DIR_PREFIX and
# cairn-reconcile.py's PHASE_DIR_PREFIX). Matches with AND without a leading
# zero: `18-parallel-phase-execution` and `07-alpha` both resolve.
PHASE_DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")

# A resolved slug becomes both a branch name and a path component, so it is
# re-checked against this before either use (T-18-01) even though it can only
# ever come from an existing directory's basename.
SLUG_OK = re.compile(r"^[A-Za-z0-9._-]+$")

# D-03: the three files every phase writes, and therefore the guaranteed
# collision surface. Reported by `prepare` so whoever assembles the subagent
# prompt can forbid them by name.
PLANNING_FILES_FORBIDDEN = [".planning/STATE.md", ".planning/ROADMAP.md",
                            ".planning/REQUIREMENTS.md"]

USAGE = ("usage: cairn-parallel.py {batch [--max N]|prepare N|"
         "reconcile [--phases 7,9]} [--project-dir DIR] [--json]")


def die(msg, code):
    print(f"[cairn-parallel] error: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #
def run_git(cwd, args):
    """(returncode, stdout, stderr) of `git -C <cwd> <args>`. git missing
    from PATH is EXIT_GIT, never a traceback."""
    try:
        proc = subprocess.run(["git", "-C", str(cwd)] + args,
                              capture_output=True, text=True)
    except FileNotFoundError:
        die("'git' not found on PATH", EXIT_GIT)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def run_git_raw(cwd, args):
    """run_git without the .strip() on stdout. Diff parsing needs the bytes
    exactly as git emitted them: a trailing space on an added line is part of
    that line's content, and byte-for-byte content equality is the entire
    convergent-edit detector. Stripping here would let two lines that differ
    only in trailing whitespace be reported as identical."""
    try:
        proc = subprocess.run(["git", "-C", str(cwd)] + args,
                              capture_output=True, text=True)
    except FileNotFoundError:
        die("'git' not found on PATH", EXIT_GIT)
    return proc.returncode, proc.stdout, proc.stderr


def git_toplevel(project_dir):
    """The repo root containing project_dir, canonicalized by git itself.
    Not the same as Path.resolve() of the argument: --project-dir may point
    at any subdirectory, and every name this script builds hangs off the
    ROOT's basename."""
    rc, out, err = run_git(project_dir, ["rev-parse", "--show-toplevel"])
    if rc != 0 or not out:
        die(f"not inside a git repository: {project_dir}"
            + (f" ({err})" if err else ""), EXIT_GIT)
    return Path(out)


def is_linked_worktree(top):
    """True when `top` is a linked worktree rather than the main checkout —
    the git dir and the COMMON git dir differ. `prepare` refuses there: the
    names this script builds are all relative to the main checkout."""
    rc_a, git_dir, _ = run_git(top, ["rev-parse", "--absolute-git-dir"])
    rc_b, common, _ = run_git(top, ["rev-parse", "--git-common-dir"])
    if rc_a != 0 or rc_b != 0:
        return False
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = Path(top) / common_path
    return os.path.realpath(git_dir) != os.path.realpath(str(common_path))


def worktree_entries(top):
    """[{path, branch}] for every worktree of this repo, parsed from
    `git worktree list --porcelain`. `branch` is the short name, or None for
    a detached/bare entry. Paths are realpath'd because macOS TMPDIR resolves
    through a /var -> /private/var symlink and git reports the PHYSICAL
    path."""
    rc, out, _ = run_git(top, ["worktree", "list", "--porcelain"])
    if rc != 0:
        return []
    entries = []
    current = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = {"path": os.path.realpath(line[len("worktree "):]),
                       "branch": None}
            entries.append(current)
        elif line.startswith("branch ") and current is not None:
            ref = line[len("branch "):]
            current["branch"] = ref[len("refs/heads/"):] \
                if ref.startswith("refs/heads/") else ref
    return entries


def same_path(a, b):
    """Whether two paths name the same place, compared through realpath on
    BOTH sides. Never a string compare: on macOS TMPDIR resolves through a
    /var -> /private/var symlink and git (which is where every holder
    identity in this codebase comes from) reports the PHYSICAL path."""
    if not a or not b:
        return False
    return os.path.realpath(str(a)) == os.path.realpath(str(b))


def worktree_entry_at(top, path):
    """The `git worktree list` entry registered at `path`, or None."""
    target = os.path.realpath(str(path))
    for entry in worktree_entries(top):
        if entry["path"] == target:
            return entry
    return None


def branch_exists(top, branch):
    rc, _, _ = run_git(top, ["rev-parse", "--verify", "--quiet",
                             f"refs/heads/{branch}"])
    return rc == 0


# --------------------------------------------------------------------------- #
# the ONE resolver both verbs share (see the docstring's bridge note)
# --------------------------------------------------------------------------- #
def phase_slug(top, phase):
    """The slug half of phase N's directory basename under
    .planning/phases/, or None when no such directory exists. Matches the
    number with and without a leading zero (`07-alpha` and `7-alpha` both
    resolve for 7), and returns None rather than a slug that fails
    SLUG_OK."""
    try:
        names = sorted(p.name for p in (top / ".planning" / "phases").iterdir()
                       if p.is_dir())
    except OSError:
        return None
    for name in names:
        m = PHASE_DIR_PREFIX.match(name)
        if not m:
            continue
        try:
            if int(m.group(1)) != phase:
                continue
        except ValueError:
            continue
        slug = name[m.end():]
        return slug if slug and SLUG_OK.match(slug) else None
    return None


def phase_layout(top, phase):
    """{phase, slug, branch, worktree} — the single naming authority for both
    verbs. `batch` announces what this returns and `prepare` creates what
    this returns; the bridge test compares the two by realpath.

    The path is built from the ROOT's own basename plus an int phase, never
    from a user-supplied string, and is asserted to be a SIBLING of the root
    before any caller writes there (T-18-01)."""
    slug = phase_slug(top, phase)
    branch = f"phase/{phase}-{slug}" if slug else f"phase/{phase}"
    worktree = Path(top).parent / f"{Path(top).name}-phase-{phase}"
    if worktree.parent != Path(top).parent:
        die(f"refusing to place a worktree outside the repo's parent "
            f"directory: {worktree}", EXIT_GIT)
    return {"phase": phase, "slug": slug, "branch": branch,
            "worktree": str(worktree)}


# --------------------------------------------------------------------------- #
# companion scripts (cairn-lease.py / cairn-status.py) through their seams
# --------------------------------------------------------------------------- #
def run_script(path, args, cwd, label):
    """Run a companion cairn script and hand back the completed process. A
    missing script is EXIT_NO_BD (the same 'the tool is not there' category
    bd-missing falls into), never a traceback."""
    if not os.path.exists(path):
        die(f"{label} not found at {path}", EXIT_NO_BD)
    try:
        proc = subprocess.run([sys.executable, str(path)] + args,
                              capture_output=True, text=True, cwd=str(cwd))
    except (OSError, subprocess.SubprocessError) as e:
        die(f"could not run {label}: {e}", EXIT_NO_BD)
    return proc


def lease_json(top, args, cwd=None):
    """A cairn-lease.py call whose JSON output is required. Its exit codes
    are propagated as this script's own: 3 stays 3 (held — a report), 5 stays
    5 (bd unavailable), anything else becomes a usage error."""
    proc = run_script(CAIRN_LEASE, args + ["--json"], cwd or top,
                      "cairn-lease.py")
    if proc.returncode not in (EXIT_OK, EXIT_HELD):
        detail = proc.stderr.strip() or proc.stdout.strip() or "(no output)"
        code = EXIT_NO_BD if proc.returncode == EXIT_NO_BD else EXIT_USAGE
        die(f"cairn-lease.py {args[0]} exited {proc.returncode}: "
            f"{detail.splitlines()[0]}", code)
    try:
        data = json.loads(proc.stdout or "null")
    except json.JSONDecodeError as e:
        die(f"cairn-lease.py {args[0]} returned invalid JSON: {e}",
            EXIT_USAGE)
    return proc.returncode, data


def lease_status(top, phase):
    _, data = lease_json(top, ["status", str(phase),
                               "--project-dir", str(top)])
    return data if isinstance(data, dict) else {}


def lease_status_all(top):
    _, data = lease_json(top, ["status", "--all", "--project-dir", str(top)])
    return data if isinstance(data, list) else []


def lease_acquire(top, phase, worktree):
    """Acquire phase N's lease FOR the worktree, by pointing --project-dir at
    it and letting cairn-lease.py resolve the holder identity from there.
    There is deliberately no way to declare a holder — see the docstring."""
    return lease_json(top, ["acquire", str(phase),
                            "--project-dir", str(worktree)], cwd=worktree)


def status_json(top):
    """One `cairn-status.py --json` read. Exit 0 and exit 5 both pair with
    real output (5 is its documented bd-unavailable degrade — every phase's
    bd evidence reads 'unknown' but the parallelism block is still computed
    from the roadmap model), the same contract cairn-doctor.py and
    cairn-reconcile.py already rely on. Anything else, or unparsable JSON, is
    a hard stop: a batch invented from a hand-read ROADMAP is exactly what
    this script must never produce."""
    proc = run_script(CAIRN_STATUS,
                      ["--json", "--planning-dir", str(top / ".planning")],
                      top, "cairn-status.py")
    if proc.returncode not in (EXIT_OK, EXIT_NO_BD):
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        die(f"cairn-status.py --json exited {proc.returncode}: {first}",
            EXIT_USAGE)
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        die(f"cairn-status.py --json returned invalid JSON: {e}", EXIT_USAGE)
    return data if isinstance(data, dict) else {}


# --------------------------------------------------------------------------- #
# prepare
# --------------------------------------------------------------------------- #
def refuse_held(phase, entry, rolled_back, json_mode):
    """The EXIT_HELD report, shared by the pre-check and the post-acquire
    race branch. Names the holder and since when, either way."""
    holder = entry.get("holder")
    acquired_at = entry.get("acquired_at")
    if json_mode:
        print(json.dumps({"phase": phase, "prepared": False, "held": True,
                          "holder": holder, "acquired_at": acquired_at,
                          "rolled_back": rolled_back}))
    else:
        undo = " — rolled back what this run created" if rolled_back else ""
        print(f"[cairn-parallel] phase {phase} is already held by {holder} "
              f"since {acquired_at} — not prepared{undo}")
    sys.exit(EXIT_HELD)


def rollback(top, worktree, branch, created_worktree, created_branch):
    """Undo ONLY what this invocation created (T-18-03). The porcelain
    re-check immediately before the removal is the guard: a path that is no
    longer a worktree of this repo on the expected branch is left completely
    alone. --force only defeats git's dirty-tree refusal on a tree this same
    invocation created seconds ago; it never widens what is targeted."""
    removed = False
    if created_worktree:
        entry = worktree_entry_at(top, worktree)
        if entry is not None and entry.get("branch") == branch:
            rc, _, _ = run_git(top, ["worktree", "remove", "--force",
                                     str(worktree)])
            removed = rc == 0
    if created_branch and worktree_entry_at(top, worktree) is None:
        run_git(top, ["branch", "-D", branch])
    return removed


def cmd_prepare(args, top):
    phase = args.phase
    if is_linked_worktree(top):
        die(f"prepare runs from the main checkout only, and {top} is a "
            f"linked worktree — run it from the repo the worktrees hang off",
            EXIT_USAGE)

    layout = phase_layout(top, phase)
    worktree = Path(layout["worktree"])
    branch = layout["branch"]

    # (1) read-only pre-check — cheap refusal, writes nothing anywhere. A
    # live lease already held BY THE VERY WORKTREE this call would use is not
    # a refusal: that is the idempotent re-prepare, and cairn-lease.py's
    # acquire will read it as already_mine and just heartbeat it.
    pre = lease_status(top, phase)
    if (pre.get("held") and not pre.get("stale")
            and not same_path(pre.get("holder"), worktree)):
        refuse_held(phase, pre, False, args.json)

    created_worktree = False
    created_branch = False
    existing = worktree_entry_at(top, worktree)
    if existing is not None:
        if existing.get("branch") != branch:
            die(f"{worktree} is already a worktree of this repo on branch "
                f"'{existing.get('branch')}', not '{branch}' — refusing to "
                f"touch it", EXIT_GIT)
    elif worktree.exists():
        die(f"{worktree} already exists and is not a worktree of this repo "
            f"— refusing to touch it", EXIT_GIT)
    else:
        if branch_exists(top, branch):
            die(f"branch '{branch}' already exists but has no worktree at "
                f"{worktree} — refusing to guess which one is the phase's "
                f"work; remove or rename it first", EXIT_GIT)
        # (2) create.
        rc, _, err = run_git(top, ["worktree", "add", "-b", branch,
                                   str(worktree), "HEAD"])
        if rc != 0:
            die(f"git worktree add failed: {err or 'unknown error'}",
                EXIT_GIT)
        created_worktree = True
        created_branch = True

    # (3) acquire, with identity resolved BY the lease FROM the worktree.
    rc, entry = lease_acquire(top, phase, worktree)
    if rc == EXIT_HELD:
        # (4) somebody won the race in the window between (1) and (3).
        rolled_back = rollback(top, worktree, branch, created_worktree,
                               created_branch)
        refuse_held(phase, entry if isinstance(entry, dict) else {},
                    rolled_back, args.json)

    _, base_commit, _ = run_git(worktree, ["rev-parse", "HEAD"])
    out = {
        "phase": phase,
        "slug": layout["slug"],
        "branch": branch,
        "worktree": str(worktree),
        "base_commit": base_commit or None,
        "created": created_worktree,
        "lease": {"holder": entry.get("holder"),
                  "acquired_at": entry.get("acquired_at")},
        "planning_files_forbidden": list(PLANNING_FILES_FORBIDDEN),
    }
    if args.json:
        print(json.dumps(out))
    else:
        verb = "prepared" if created_worktree else "reused"
        print(f"[cairn-parallel] {verb} worktree {worktree} on branch "
              f"{branch} (base {base_commit})")
        print(f"[cairn-parallel] phase {phase} lease held by "
              f"{out['lease']['holder']} since "
              f"{out['lease']['acquired_at']}")
        print(f"[cairn-parallel] forbidden in this worktree (D-03): "
              f"{', '.join(PLANNING_FILES_FORBIDDEN)}")
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# batch
# --------------------------------------------------------------------------- #
def build_announcement(result):
    """The text /cairn:autonomous step 0.4 prints before it spawns anything:
    how many phases run and why each one, what was left out and why, and the
    honesty line when the roadmap declares no dependencies at all. The
    operator interrupts HERE — so nothing is summarized away."""
    lines = []
    selected = result["selected"]
    if not selected:
        lines.append("No phase can start in parallel right now.")
    elif len(selected) == 1:
        s = selected[0]
        lines.append(f"1 phase runs now: phase {s['phase']}"
                     f"{' — ' + s['title'] if s['title'] else ''}.")
    else:
        lines.append(f"{len(selected)} phases run at the same time, one "
                     f"worktree each: "
                     + ", ".join(f"phase {s['phase']}" for s in selected)
                     + ".")
    for s in selected:
        stale = " (reclaiming a stale lease)" if s["lease_stale"] else ""
        lines.append(f"  phase {s['phase']}: {s['next_command']} — "
                     f"{s['reason']}{stale}; worktree {s['worktree']} on "
                     f"{s['branch']}")
    for d in result["deferred"]:
        lines.append(f"  phase {d['phase']} stays out: {d['reason']}")
    if result["note"]:
        lines.append(result["note"])
    if not result["declared"]:
        lines.append("No dependencies are declared in this roadmap, so this "
                     "split reflects what is recorded, not a verified "
                     "ordering.")
    return "\n".join(lines)


def cmd_batch(args, top):
    if args.max < 1:
        die(f"--max must be at least 1 (got {args.max})\n" + USAGE,
            EXIT_USAGE)

    data = status_json(top)
    par = data.get("parallelism") or {}
    runnable = []
    for n in par.get("runnable") or []:
        try:
            runnable.append(int(n))
        except (TypeError, ValueError):
            continue

    commands = {}
    for c in data.get("next_commands") or []:
        if isinstance(c, dict) and isinstance(c.get("phase"), int):
            commands[c["phase"]] = c

    held = {}
    for e in lease_status_all(top):
        if isinstance(e, dict) and e.get("held"):
            try:
                held[int(e.get("phase"))] = e
            except (TypeError, ValueError):
                continue

    selected = []
    deferred = []
    for n in runnable:
        entry = held.get(n)
        if entry is not None and not entry.get("stale"):
            deferred.append({"phase": n,
                             "reason": f"lease held by {entry.get('holder')} "
                                       f"since {entry.get('acquired_at')}"})
            continue
        if len(selected) >= args.max:
            deferred.append({"phase": n,
                             "reason": f"above the --max {args.max} ceiling"})
            continue
        layout = phase_layout(top, n)
        cmd = commands.get(n) or {}
        selected.append({
            "phase": n,
            "title": cmd.get("title"),
            "slug": layout["slug"],
            "branch": layout["branch"],
            "worktree": layout["worktree"],
            "next_command": cmd.get("command"),
            "reason": cmd.get("reason"),
            "lease_stale": bool(entry is not None and entry.get("stale")),
        })

    result = {
        # Passed through verbatim: whoever computed independence owns these.
        "runnable": runnable,
        "blocked": [b for b in (par.get("blocked") or [])],
        "declared": bool(par.get("declared")),
        "note": par.get("note"),
        "max": args.max,
        "selected": selected,
        "deferred": deferred,
    }
    result["announcement"] = build_announcement(result)

    if args.json:
        print(json.dumps(result))
    else:
        for line in result["announcement"].splitlines():
            print(f"[cairn-parallel] {line}")
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# reconcile
#
# === reconcile: read-only region BEGIN ===
#
# Everything between this marker and the END one speaks to git in read
# invocations only. tests/cairn-parallel.bats greps this exact region — with
# comment lines filtered out, because the comments in here NAME the verbs they
# forbid and a grep over the raw text would invalidate itself — for bd write
# verbs (create / update / close / reopen), cairn-journal write subcommands
# (observe / lease / append) and writing git verbs (merge, checkout, commit,
# reset, clean, stash, branch, worktree, apply), and asserts there are none.
# Adding one here without noticing is exactly what that test exists to stop.
# The companion proof is the mutation test: reconcile runs against a real
# fixture and the tree, the branch heads and every file hash come out
# unchanged. See the module docstring for why both proofs, not one.
# --------------------------------------------------------------------------- #

# Phase number out of a branch name, by the SAME rule prepare used to build
# it: `phase/<N>-<slug>`, or `phase/<N>` for a phase with no directory. These
# constants live beside the code they serve rather than with the module-level
# block above, so the greppable region is self-contained.
PHASE_BRANCH = re.compile(r"^phase/0*(\d+)(?:-|$)")

# `@@ -a[,b] +c[,d] @@` — the raw material of the detector. `b` defaults to 1
# when absent (`@@ -1 +1 @@` replaces exactly one base line); `b == 0` is a
# pure insertion after base line a (`@@ -41,0 +42 @@`).
HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

# `100644 <oid> 1\t<path>` — merge-tree's conflicted-entry lines, which name
# the paths reliably. The prose `CONFLICT (...)` lines are carried through as
# messages but never parsed for a path: their shape varies by conflict kind
# (`Merge conflict in <path>` puts it last, `modify/delete` puts it first).
MERGE_TREE_STAGE = re.compile(r"^\d{6} [0-9a-f]{40,} [123]\t(.+)$")

# Cap on one reported line of a convergent edit (T-18-07). The COMPARISON is
# always over the full lines; truncation happens at report time only.
TRUNCATE_AT = 200


def truncate(line):
    if len(line) <= TRUNCATE_AT:
        return line
    return line[:TRUNCATE_AT - 1] + "…"


def git_version(top):
    """The version string of the git this report was produced with. Carried
    in every report because what the report can ASSERT depends on it: below
    2.38 there is no `merge-tree --write-tree` and conflicts are unknown."""
    rc, out, _ = run_git(top, ["--version"])
    if rc != 0 or not out:
        return None
    parts = out.split()
    return parts[2] if len(parts) >= 3 else out


def phase_branches(top):
    """[(phase, branch)] for every refs/heads/phase/* ref, sorted by phase.

    This is the ONLY discovery mechanism (D-01): the work is found by the
    name prepare gave it, and no agent is ever asked where it worked."""
    rc, out, _ = run_git(top, ["for-each-ref", "--format=%(refname:short)",
                               "refs/heads/phase/*"])
    if rc != 0 or not out:
        return []
    found = []
    for name in out.splitlines():
        name = name.strip()
        m = PHASE_BRANCH.match(name)
        if not m:
            continue
        found.append((int(m.group(1)), name))
    found.sort()
    return found


def common_ancestor(top, a, b):
    rc, out, _ = run_git(top, ["merge-base", a, b])
    return out if rc == 0 and out else None


def numstat(top, base, ref):
    """{files, insertions, deletions, paths} of `git diff --numstat
    base..ref`. Binary files count as a changed file with no line counts,
    which is what git's own `-` means there."""
    rc, out, _ = run_git(top, ["diff", "--numstat", f"{base}..{ref}"])
    if rc != 0:
        return {"files": None, "insertions": None, "deletions": None,
                "paths": []}
    files = 0
    insertions = 0
    deletions = 0
    paths = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        files += 1
        paths.append(parts[2])
        for raw, key in ((parts[0], "ins"), (parts[1], "del")):
            if not raw.isdigit():
                continue
            if key == "ins":
                insertions += int(raw)
            else:
                deletions += int(raw)
    return {"files": files, "insertions": insertions, "deletions": deletions,
            "paths": paths}


def diff_hunks(top, base, ref):
    """{path: [(base_start, base_count, tuple_of_new_lines)]} from
    `git diff -U0 base..ref`.

    -U0 is deliberate: with zero context every hunk's base range is the
    changed range and nothing else, which is what makes range equality a
    meaningful comparison between two independent branches. The measured
    cost of that choice is in the docstring — an added block ADJACENT to the
    changed line coalesces into one hunk, and convergence stops being
    declared there."""
    rc, out, _ = run_git_raw(top, ["diff", "-U0", f"{base}..{ref}"])
    if rc != 0:
        return {}
    per_path = {}
    path = None
    current = None
    for line in out.split("\n"):
        if line.startswith("diff --git "):
            path = None
            current = None
        elif line.startswith("+++ "):
            target = line[4:]
            path = None if target == "/dev/null" else target[2:] \
                if target.startswith("b/") else target
            current = None
        elif line.startswith("--- "):
            current = None
        elif line.startswith("@@ "):
            m = HUNK_HEADER.match(line)
            if not m or path is None:
                current = None
                continue
            start = int(m.group(1))
            count = 1 if m.group(2) is None else int(m.group(2))
            current = []
            per_path.setdefault(path, []).append([start, count, current])
        elif current is not None and line.startswith("+"):
            current.append(line[1:])
    return {p: [(s, c, tuple(lines)) for s, c, lines in hunks]
            for p, hunks in per_path.items()}


def convergent_edits(hunks_a, hunks_b, branch_a, branch_b):
    """The finding this whole subcommand exists for.

    A convergent edit is a file present on BOTH sides carrying a hunk whose
    base range (start AND count) is equal on the two sides and whose new
    block of lines is byte-for-byte identical. That is the entire rule; it is
    strict on purpose, so what is reported is what was measured. Two sides
    deleting the very same base range (both new blocks empty) satisfies it
    for the same reason: an agreement nobody reviewed is still an agreement
    nobody reviewed.

    git resolves precisely this case without a word — the two sides are
    identical, so there is nothing for it to ask about — which is why it can
    only ever be found here."""
    found = []
    for path in sorted(set(hunks_a) & set(hunks_b)):
        by_range_a = {(s, c): lines for s, c, lines in hunks_a[path]}
        by_range_b = {(s, c): lines for s, c, lines in hunks_b[path]}
        for key in sorted(set(by_range_a) & set(by_range_b)):
            if by_range_a[key] != by_range_b[key]:
                continue
            found.append({
                "file": path,
                "base_line": key[0],
                "base_count": key[1],
                "new_lines": [truncate(x) for x in by_range_a[key]],
                "branches": [branch_a, branch_b],
            })
    return found


def merge_tree_conflicts(top, ref_a, ref_b, version):
    """(conflicts, note) for one pair, computed WITHOUT a working tree.

    `git merge-tree --write-tree` exits 0 clean and 1 with conflicts. Any
    other code, or a stderr complaining about the option, means this git
    cannot pre-compute the answer — and the honest report of that is
    (None, note), never an empty list. An empty list reads as "clean", and
    failing open into a false all-clear is the bug this milestone exists to
    kill (Pitfall 3)."""
    rc, out, err = run_git(top, ["merge-tree", "--write-tree", ref_a, ref_b])
    unknown_option = "unknown option" in err.lower() or "usage:" in err.lower()
    if rc not in (EXIT_OK, 1) or unknown_option:
        detail = err.splitlines()[0] if err else f"exit {rc}"
        return None, (f"git {version or 'unknown'} cannot pre-compute merge "
                      f"conflicts ({detail}) — conflicts are UNKNOWN here, "
                      f"not clean; git will report them at merge time")
    if rc == EXIT_OK:
        return [], None
    paths = []
    messages = []
    for line in out.split("\n"):
        m = MERGE_TREE_STAGE.match(line)
        if m:
            if m.group(1) not in paths:
                paths.append(m.group(1))
        elif line.startswith("CONFLICT "):
            messages.append(line)
    conflicts = []
    for path in paths:
        conflicts.append({"path": path,
                          "messages": [m for m in messages if path in m]})
    if not conflicts and messages:
        conflicts.append({"path": None, "messages": messages})
    return conflicts, None


def parse_phases(raw):
    """`--phases 7,9` -> [7, 9]. A non-numeric entry is a usage error rather
    than a silently ignored filter: a filter that quietly matched nothing
    would produce an empty, reassuring report."""
    if raw is None:
        return None
    wanted = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            wanted.append(int(chunk))
        except ValueError:
            die(f"--phases takes comma-separated phase numbers (got "
                f"'{chunk}')\n" + USAGE, EXIT_USAGE)
    return wanted


def print_report(result):
    """The human report: one section per category, every finding as
    file:line, and a closing total."""
    def say(line):
        print(f"[cairn-parallel] {line}")

    if not result["branches"]:
        say("no phase/* branch found — nothing to reconcile")
        return
    for b in result["branches"]:
        counts = (f"{b['commits']} commit(s), {b['files']} file(s), "
                  f"+{b['insertions']} -{b['deletions']}"
                  if b["commits"] is not None and b["files"] is not None
                  else "unmeasurable (no common ancestor with HEAD)")
        say(f"phase {b['phase']} ({b['branch']}): {counts}")

    edits = [(p, e) for p in result["pairs"] for e in p["convergent_edits"]]
    if edits:
        say("convergent edits — both branches changed these to the SAME "
            "value, and git took one without asking:")
        for pair, e in edits:
            say(f"  {e['file']}:{e['base_line']}  "
                f"{' + '.join(e['branches'])}")
            for line in e["new_lines"]:
                say(f"    {line}")
    for pair in result["pairs"]:
        if pair["conflicts"] is None:
            say(f"conflicts between {' + '.join(pair['branches'])}: UNKNOWN — "
                f"{pair['conflicts_note']}")
        elif pair["conflicts"]:
            say(f"merge conflicts between {' + '.join(pair['branches'])} "
                f"(git reports these too, at merge time):")
            for c in pair["conflicts"]:
                say(f"  {c['path']}")
    if result["planning_writes"]:
        say("planning writes (D-03) — reported, and deliberately NOT a "
            "failure:")
        for w in result["planning_writes"]:
            say(f"  {w['branch']}: {', '.join(w['files'])}")
    if result["findings_total"]:
        say(f"{result['findings_total']} finding(s) — reported, none "
            f"resolved; reconcile does not merge")
    else:
        say("no convergent edit and no conflict between these branches")


def cmd_reconcile(args, top):
    wanted = parse_phases(args.phases)
    version = git_version(top)

    pairs_input = [(n, b) for n, b in phase_branches(top)
                   if wanted is None or n in wanted]

    branches = []
    planning_writes = []
    for phase, branch in pairs_input:
        base = common_ancestor(top, "HEAD", branch)
        entry = {"phase": phase, "branch": branch, "base": base,
                 "commits": None, "files": None, "insertions": None,
                 "deletions": None}
        if base:
            rc, out, _ = run_git(top, ["rev-list", "--count",
                                       f"{base}..{branch}"])
            entry["commits"] = int(out) if rc == 0 and out.isdigit() else None
            stat = numstat(top, base, branch)
            entry["files"] = stat["files"]
            entry["insertions"] = stat["insertions"]
            entry["deletions"] = stat["deletions"]
            touched = [p for p in stat["paths"]
                       if p in PLANNING_FILES_FORBIDDEN]
            if touched:
                planning_writes.append({"phase": phase, "branch": branch,
                                        "files": touched})
        branches.append(entry)

    pairs = []
    findings = 0
    unknown = False
    for i in range(len(pairs_input)):
        for j in range(i + 1, len(pairs_input)):
            branch_a = pairs_input[i][1]
            branch_b = pairs_input[j][1]
            base = common_ancestor(top, branch_a, branch_b)
            edits = []
            if base:
                edits = convergent_edits(diff_hunks(top, base, branch_a),
                                         diff_hunks(top, base, branch_b),
                                         branch_a, branch_b)
            conflicts, note = merge_tree_conflicts(top, branch_a, branch_b,
                                                   version)
            if conflicts is None:
                unknown = True
            findings += len(edits) + (len(conflicts) if conflicts else 0)
            pairs.append({"branches": [branch_a, branch_b], "base": base,
                          "convergent_edits": edits, "conflicts": conflicts,
                          "conflicts_note": note})

    result = {"git_version": version, "branches": branches, "pairs": pairs,
              "planning_writes": planning_writes, "findings_total": findings}

    if args.json:
        print(json.dumps(result))
    else:
        print_report(result)
    # A planning write on its own does NOT reach here (D-03 / <deferred>):
    # reporting is not failing. An unknown conflict list DOES, because the
    # script cannot say the merge is clean and will not pretend to.
    sys.exit(EXIT_FINDINGS if (findings or unknown) else EXIT_OK)


# --------------------------------------------------------------------------- #
# === reconcile: read-only region END ===
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        prog="cairn-parallel",
        description="Turn cairn-status.py's parallelism announcement into "
                    "real, isolated worktrees — one per phase.")
    sub = parser.add_subparsers(dest="command", required=True)

    batch = sub.add_parser("batch", help="what can run at once, with each "
                                         "phase's branch and worktree "
                                         "already resolved")
    batch.add_argument("--max", type=int, default=3,
                       help="ceiling on how many phases are selected "
                            "(default: 3)")
    batch.set_defaults(func=cmd_batch)

    prepare = sub.add_parser("prepare", help="create phase N's named "
                                             "worktree and take its lease "
                                             "pointing at it")
    prepare.add_argument("phase", type=int, help="phase number")
    prepare.set_defaults(func=cmd_prepare)

    reconcile = sub.add_parser("reconcile",
                               help="read-only report over the phase/* "
                                    "branches: what each phase produced, the "
                                    "merge conflicts, and the convergent "
                                    "edits git resolves in silence")
    reconcile.add_argument("--phases", metavar="LIST",
                           help="comma-separated phase numbers to restrict "
                                "to (default: every phase/* branch)")
    reconcile.set_defaults(func=cmd_reconcile)

    for p in (batch, prepare, reconcile):
        p.add_argument("--project-dir", metavar="DIR",
                       help="project root for git/bd discovery (default: "
                            "$CLAUDE_PROJECT_DIR or cwd)")
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
        die(f"project directory does not exist: {root}", EXIT_USAGE)
    args.func(args, git_toplevel(root))


if __name__ == "__main__":
    main()
