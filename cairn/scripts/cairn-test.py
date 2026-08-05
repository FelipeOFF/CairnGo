#!/usr/bin/env python3
"""cairn-test — one door into the bats suite: detect, compose, warn, run.

WHAT THIS IS
------------
`bats tests/` works and keeps working. This runner is the door that also
answers the question nobody answers by hand: how many jobs, and can this
machine parallelize at all. It resolves the job count, checks what `bats -j`
actually requires BEFORE composing the command, drops `-j` when a requirement
is missing, says so with the cost and the fix, and passes bats's own exit code
through untranslated.

THE MEASUREMENT THAT INVERTS THE OBVIOUS REQUIREMENT
----------------------------------------------------
The obvious version of this script assumes `bats -j` degrades to serial when
GNU parallel is absent. It does not. Measured on bats 1.14.0, with the
parallel binary missing:

    1..2
    bats-exec-suite: line 323: parallel: command not found
    # bats warning: Executed 0 instead of expected 2 tests
    exit 1

ZERO tests executed, reported as a failure. There is no silent degradation to
serial; there is a suite that never ran.

bats does carry a guard for this, and the guard cannot fire. bats-exec-suite
line 110 reads:

    if ! type -p "${parallel_binary_name}" >/dev/null \\
       && "${parallel_binary_name}" --version &>/dev/null \\
       && [[ -z "$bats_no_parallelize_across_files" ]]; then
      abort "Cannot execute \\"${num_jobs}\\" jobs without GNU parallel"

The first clause is true only when the binary is NOT on PATH, and the second
is true only when running it succeeds — they cannot both hold, so the abort is
unreachable. That is why the failure arrives 200 lines later as a
`command not found` inside a pipeline instead of as a refusal. This runner
cannot delegate the check to bats; it has to make it itself.

Hence the shape of this script: detection happens BEFORE the command is
composed, so the sentence "the suite will run serial" is true at the moment it
is printed, and bats is never put in the position of executing zero tests.

WHAT `bats -j` ACTUALLY REQUIRES — BOTH OF THESE, MEASURED
-----------------------------------------------------------
1. the parallel binary (`parallel`, or whatever `BATS_PARALLEL_BINARY_NAME`
   names), used at bats-exec-suite:323 to fan files out;
2. `flock` OR `shlock`, required by bats_semaphore_setup() in
   lib/bats-core/semaphore.bash:26-33 to parallelize WITHIN a file. Missing
   both, bats prints `ERROR: flock/shlock is required for parallelization
   within files!` and exits 1 — again with zero tests executed.

The second requirement is not hypothetical on the machines this repo runs on:
macOS ships `shlock` and no `flock`. A runner that checked only for parallel
would compose `-j` on a machine with neither and reproduce the very state this
script exists to prevent, so both are checked and either one missing removes
the `-j`.

WHAT THE WARNING MAY NOT SAY
----------------------------
Nothing about bats "ignoring" the flag, and nothing about degrading silently
to serial. Both are false, and a tool built to remove unearned claims must not
make one about itself. What the warning states is what THIS RUNNER did — it
removed the flag — plus the measured cost of running serial and the command
that fixes it.

THE EXIT CODE CONTRACT, AND THE COLLISION IT HAS TO RESOLVE
------------------------------------------------------------
2 (usage) and 5 (bats unavailable) are this runner's own codes, and bats's own
code is passed through untranslated — including when bats itself exits 2 or 5.
A number that means two things is the ambiguity this phase removes from state
files, so it is resolved here by a TEMPORAL BOUNDARY rather than by
translating anything:

  * 2 and 5 can only be emitted BEFORE bats is invoked. They are decided while
    the command is being composed: bad flags, a path that does not exist, no
    bats on PATH.
  * from the moment bats starts, EVERY code is bats's, and it exits as it
    came. A runner that swallows the exit code of what it runs is a false
    green with a different name.
  * a nonzero code coming from bats is announced on stderr, naming its origin.
    That line is the only thing that distinguishes "bats exited 5" from "bats
    was not installed", which is the other 5.

A bats killed by a signal reports a negative returncode in Python; it is
converted to the shell's own 128+N so the number that leaves this script is
the number a shell would have reported.

Usage:
    cairn-test.py [--jobs N] [--print-command] [--check-env]
                  [--project-dir DIR] [paths...]

    --jobs N          how many jobs to run; 1 means serial and is honored
                      without comment
    --print-command   print the exact argv that WOULD be executed, one line on
                      stdout, and exit 0 having run nothing
    --check-env       print a JSON report of what this machine can do (bats,
                      the job count and its source, every prerequisite that is
                      missing and its fix) and exit 0. This exists so
                      cairn-doctor.py can ROUTE the verdict instead of
                      reimplementing the detection — the same
                      shell-out-to-a-sibling-script shape the doctor already
                      uses for cairn-map.py, cairn-lease.py and
                      cairn-release.py. Knowing what `bats -j` requires lives
                      in exactly one file, and this is it.
    --project-dir DIR project root the config and the default target resolve
                      from (default: this repo, derived from this file's own
                      location, never the cwd)
    paths...          what to hand bats (default: <project-dir>/tests)

Job count, in this precedence:
    --jobs N  >  test.jobs in .cairn/config.json  >  os.cpu_count()

`test.jobs` is read by shelling out to cairn-config.py in the same defensive
shape cairn-parallel.py's config_value() uses (which is cairn-status.py's
fetch_lease_status() shape): a subprocess that cannot start, a nonzero exit,
unparsable JSON or a payload without a `value` all degrade to the next source
down. Reading a setting must never be a reason a test run does not happen.

Note on `-j 1`: bats skips its whole parallel path when the job count is 1
(bats-exec-suite:109), so `-j 1` and no flag at all are the same run. This
runner composes no `-j` for one job, which also means a composed command
without `-j` says only "this run is serial" and never why — the warning above
it is what says why.

Exit codes:
    0  the suite passed (or --print-command printed and ran nothing)
    2  usage error: bad flags, a job count below 1, or a target path that does
       not exist. Decided BEFORE bats is invoked.
    5  bats is not on PATH. Decided BEFORE bats is invoked.
    *  anything else is bats's own exit code, passed through untranslated and
       announced as bats's on stderr.
"""
import argparse
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_BATS = 5

SCRIPTS_DIR = Path(__file__).resolve().parent
# <repo>/cairn/scripts/cairn-test.py -> <repo>. Deliberately not the cwd:
# running the suite from inside a subdirectory is ordinary, and `tests/`
# relative to wherever someone happens to stand is not a target.
REPO_ROOT = SCRIPTS_DIR.parent.parent

CAIRN_CONFIG = os.environ.get(
    "CAIRN_CONFIG", str(SCRIPTS_DIR / "cairn-config.py"))

DEFAULT_TARGET = "tests"

# The measured cost of the serial fallback, carried into every warning. A
# warning without the number and without the fix is noise.
MEASURED_COST = ("tests/cairn-map.bats takes 64s serial against 33s at -j 6 "
                 "(measured 2026-08-03)")

USAGE = ("usage: cairn-test.py [--jobs N] [--print-command] "
         "[--project-dir DIR] [paths...]")


def die(msg, code):
    print(f"[cairn-test] error: {msg}", file=sys.stderr)
    sys.exit(code)


def note(msg):
    """Every diagnostic this script writes goes to STDERR, including the
    parallel warning.

    The plan put the warning on stdout. It moved here because
    `--print-command` promises stdout is EXACTLY the argv, one line, and a
    warning sharing that channel would break the one thing that flag exists
    for. stderr keeps both promises at once, and bats' own `run` merges the
    two anyway, so nothing under test loses the warning.
    """
    print(f"[cairn-test] {msg}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# what `bats -j` requires
# --------------------------------------------------------------------------- #
def parallel_binary_name():
    """The binary bats will actually look for. bats reads
    BATS_PARALLEL_BINARY_NAME (bats-exec-suite:8) so that `rush` and friends
    can stand in for GNU parallel; checking for a hardcoded `parallel` would
    warn about an absence that does not exist on such a machine."""
    return os.environ.get("BATS_PARALLEL_BINARY_NAME") or "parallel"


def install_hint(what):
    """The concrete command, per platform. macOS gets brew, everything else
    gets the Debian family form, which is what CI runs."""
    if platform.system() == "Darwin":
        return f"brew install {what}"
    return f"sudo apt-get install {what}"


def parallel_blockers():
    """Everything missing that `bats -j >1` needs, each with its own fix.

    Checked BEFORE the command is composed — that ordering is the whole
    requirement, not an implementation detail. Returns [] when the machine can
    parallelize.
    """
    blockers = []
    binary = parallel_binary_name()
    if shutil.which(binary) is None:
        blockers.append({
            "what": f"GNU parallel (`{binary}`) is not on PATH",
            "why": "bats fans test files out through it "
                   "(bats-exec-suite:323)",
            "fix": install_hint("parallel"),
        })
    if shutil.which("flock") is None and shutil.which("shlock") is None:
        blockers.append({
            "what": "neither `flock` nor `shlock` is on PATH",
            "why": "bats needs one of them to parallelize WITHIN a file "
                   "(lib/bats-core/semaphore.bash:26-33), and without either "
                   "it prints `ERROR: flock/shlock is required for "
                   "parallelization within files!` and exits 1",
            "fix": install_hint("flock"),
        })
    return blockers


def warn_blockers(blockers, jobs):
    """Say what THIS RUNNER did, then the cost, then the fix.

    Never what bats "would have done": measured, bats does not degrade to
    serial, it executes zero tests and exits 1. Claiming otherwise would be
    this phase's own defect committed by the tool sent to remove it.
    """
    for b in blockers:
        note(f"⚠ {b['what']} — {b['why']}")
    note(f"⚠ the `-j {jobs}` was REMOVED from the command below by this "
         "runner, and that is why the suite runs serial")
    note("⚠ bats does NOT fall back to serial on its own: measured on bats "
         "1.14.0, `bats -j` without the parallel binary executes ZERO tests "
         "and exits 1 (`# bats warning: Executed 0 instead of expected 2 "
         "tests`)")
    note(f"⚠ cost of running serial: {MEASURED_COST}")
    for b in blockers:
        note(f"⚠ fix: {b['fix']}")


# --------------------------------------------------------------------------- #
# the job count
# --------------------------------------------------------------------------- #
def config_value(root, key):
    """One setting out of cairn-config.py, or None.

    Defensive in exactly the shape cairn-parallel.py's config_value() uses
    (itself cairn-status.py's fetch_lease_status() shape): a subprocess that
    cannot start, a nonzero exit, unparsable JSON or a payload with no `value`
    all degrade to None. A config that cannot be read is never a reason a test
    run does not happen — and the resolver is not reimplemented here, it is
    shelled out to, so there is exactly one place that knows the schema.
    """
    try:
        proc = subprocess.run(
            [sys.executable, str(CAIRN_CONFIG), "get", key, "--json",
             "--project-dir", str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "value" not in data:
        return None
    return data["value"]


def resolve_jobs(flag, root):
    """(jobs, source) — the flag, then test.jobs, then the CPU count.

    bool is an int subclass in Python and `true` is not a job count, so it is
    excluded explicitly; a config value below 1 is not usable either and falls
    through to the CPU count rather than being clamped silently.
    """
    if flag is not None:
        return flag, "--jobs"
    value = config_value(root, "test.jobs")
    if (value is not None and not isinstance(value, bool)
            and isinstance(value, int) and value >= 1):
        return value, "test.jobs"
    return os.cpu_count() or 1, "cpu count"


# --------------------------------------------------------------------------- #
# the command
# --------------------------------------------------------------------------- #
def resolve_targets(paths, root):
    """What to hand bats. A path that does not exist is a usage error decided
    HERE, on the runner's side of the temporal boundary — bats' own answer to
    a missing path is exit 1, which would be indistinguishable from a genuine
    test failure."""
    if not paths:
        target = root / DEFAULT_TARGET
        if not target.exists():
            die(f"no default target: {target} does not exist\n{USAGE}",
                EXIT_USAGE)
        return [str(target)]
    resolved = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            die(f"no such path: {p}\n{USAGE}", EXIT_USAGE)
        resolved.append(str(path))
    return resolved


def compose(bats, jobs, blockers, targets):
    """The exact argv. `-j` only when the job count asks for it AND the
    machine can honor it — the composition is where the detection is spent."""
    argv = [bats]
    if jobs > 1 and not blockers:
        argv += ["-j", str(jobs)]
    argv += targets
    return argv


def env_report(root, flag):
    """What this machine can do, as JSON, for a caller that only routes.

    One difference from a run, and it is deliberate: the blockers are computed
    unconditionally rather than only when the job count is above 1. This is a
    report about the MACHINE, not about one invocation — `--jobs 1` makes the
    prerequisites irrelevant to that run, and no less absent from the box.
    """
    jobs, source = resolve_jobs(flag, root)
    blockers = parallel_blockers()
    return {
        "bats": shutil.which("bats"),
        "jobs": jobs,
        "jobs_source": source,
        "parallel_binary": parallel_binary_name(),
        "can_parallelize": not blockers,
        "blockers": blockers,
        "measured_cost": MEASURED_COST,
    }


def bats_exit_code(returncode):
    """bats' code as a shell would report it. Python hands back a negative
    number for a signal-terminated child; 128+N is what `$?` would have
    been."""
    if returncode < 0:
        return 128 - returncode
    return returncode


def main():
    parser = argparse.ArgumentParser(
        prog="cairn-test", add_help=True,
        description="Run the bats suite: resolve the job count, check what "
                    "`bats -j` needs before composing the command, and pass "
                    "bats' exit code through.")
    parser.add_argument("--jobs", type=int, default=None, metavar="N",
                        help="jobs to run (default: test.jobs, else the CPU "
                             "count); 1 means serial")
    parser.add_argument("--print-command", action="store_true",
                        help="print the exact argv that would run, one line "
                             "on stdout, and exit 0 running nothing")
    parser.add_argument("--check-env", action="store_true",
                        help="print a JSON report of what this machine can "
                             "do and exit 0 (what cairn-doctor.py routes)")
    parser.add_argument("--project-dir", metavar="DIR", default=None,
                        help="project root the config and the default target "
                             "resolve from (default: this repo)")
    parser.add_argument("paths", nargs="*", metavar="PATH",
                        help="what to hand bats (default: tests/)")
    args = parser.parse_args()

    if args.jobs is not None and args.jobs < 1:
        die(f"--jobs must be at least 1 (got {args.jobs})\n{USAGE}",
            EXIT_USAGE)

    root = Path(args.project_dir).resolve() if args.project_dir else REPO_ROOT
    if not root.is_dir():
        die(f"project directory does not exist: {root}\n{USAGE}", EXIT_USAGE)

    # BEFORE target resolution on purpose: a report about the machine must not
    # depend on a suite directory existing, and it must be able to say "bats
    # is not here" rather than exit 5 over it. Reporting is not running.
    if args.check_env:
        print(json.dumps(env_report(root, args.jobs)))
        sys.exit(EXIT_OK)

    targets = resolve_targets(args.paths, root)

    # Availability before anything else that could be mistaken for a test
    # result. 5 is the house code for "the tool is not here", and it is never
    # a check failure.
    bats = shutil.which("bats")
    if bats is None:
        die("bats is not on PATH — install bats-core "
            "(https://github.com/bats-core/bats-core); nothing was run",
            EXIT_NO_BATS)

    jobs, source = resolve_jobs(args.jobs, root)
    blockers = parallel_blockers() if jobs > 1 else []
    if blockers:
        warn_blockers(blockers, jobs)

    argv = compose(bats, jobs, blockers, targets)

    if args.print_command:
        print(shlex.join(argv))
        sys.exit(EXIT_OK)

    if jobs > 1 and not blockers:
        note(f"running with -j {jobs} (from {source})")
    else:
        note(f"running serial (jobs resolved to {jobs} from {source})")

    try:
        proc = subprocess.run(argv)
    except OSError as e:
        die(f"could not execute {bats}: {e}", EXIT_NO_BATS)
    code = bats_exit_code(proc.returncode)
    if code != EXIT_OK:
        # The one line that keeps 2 and 5 from meaning two things. Without it,
        # a bats that exits 5 is indistinguishable from a bats that was never
        # installed.
        note(f"exit {code} is bats' own exit code, passed through "
             "untranslated (cairn-test's own codes are 2 and 5, and both are "
             "decided before bats is invoked)")
    sys.exit(code)


if __name__ == "__main__":
    main()
