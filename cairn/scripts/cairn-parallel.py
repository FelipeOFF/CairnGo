#!/usr/bin/env python3
"""cairn-parallel — turn the parallelism ANNOUNCEMENT into real, isolated
working trees.

cairn-status.py's parallelism() has been answering "phases 14 and 15 are
independent — one agent per phase, or one worktree each" since phase 13, and
until this script nobody consumed that answer: the loop announced parallelism
and then ran in single file. That gap is the dishonesty this milestone exists
to remove, and this file is the missing consumer.

Four verbs, all in this ONE file — which is why argparse arrived with
subparsers from the first commit.

    batch      what can run at once, with each phase's branch name and
               worktree path already resolved — the text /cairn:autonomous
               step 0.4 announces before it spawns anything.
    prepare N  create that named worktree for phase N and take phase N's
               lease pointing AT it.
    reconcile  read-only report over the branches `prepare` named: what each
               phase produced, the merge conflicts git will raise, and — the
               part nobody else does — the CONVERGENT EDIT git resolves in
               silence.
    cleanup    what a dead run left behind — a worktree registration whose
               directory is gone, and a lease nobody will ever renew or
               release — and, behind `--apply`, exactly those two and nothing
               else.


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


WHY `prepare` REPORTS THE RESPONSE LANGUAGE (phase 24, LANG-02)
----------------------------------------------------------------
The prompt assembler reads this payload and nothing else about the phase, so
anything the subagent must be told has to come out of here. The language is
one of those things, and the reason it is mechanical rather than remembered is
a measured defect: in the v1.4 cycle every subagent this loop spawned answered
in English against an all-Portuguese plan, and it did so with
`.planning/config.json:response_language` ALREADY SET to `pt-BR`. A test
asserting "the key is in the file" would have been GREEN on the exact day the
defect happened — which is why the phase-24 test reads the value out of THIS
payload instead.

The value is resolved by cairn-config.py (`agents.response_language`, which
GSD's own `response_language` outranks when set); it is not resolved a second
time here, for the same reason independence is not recomputed here. The
fallback when the subprocess fails is `(None, "unavailable")` and deliberately
NOT `("English", ...)`: repeating the default here would be the second place
it lives, and one setting with two defaults is where the next disagreement
starts. A null is visible in both renders; a guessed "English" would not be.

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
therefore additive (`worktree add`), scoped to a path this invocation itself
created (`prepare`'s rollback: `worktree remove`, `branch -D`), or — in
`cleanup --apply` — scoped to a path git itself has already certified as safe
to touch: a registration whose directory is gone, or a worktree with nothing
uncommitted and nothing unmerged. Uncommitted work is the one thing in this
whole file that cannot be recreated from git, so it is reported and left
exactly where it is; there is no flag that stashes it and no flag that forces
past it.


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

That default is now a SETTING rather than a literal: with no `--max`, the
ceiling comes from `cairn-config.py get autonomous.max_parallel`, whose own
schema default is 3 — so a repo with no `.cairn/config.json` behaves exactly
as it did before. An explicit `--max` always wins over the config. The config
is read by SUBPROCESS, in cairn-status.py's fetch_lease_status() shape: a
failed subprocess or unparsable JSON degrades to the fallback and never takes
`batch` down with it. Config resolution is not reimplemented here, for the
same reason independence is not recomputed here — two implementations of one
question eventually disagree.

The OTHER ceiling, `autonomous.max_cycles`, bounds a run rather than a batch,
and it has a deliberate asymmetry: it applies only when the caller passes
`--cycle K`. A caller that does not count cycles cannot be over one, and
inventing a cycle number here would be exactly the second truth this file
refuses everywhere else. Above the ceiling nothing is selected, every runnable
phase is deferred with the ceiling named as its reason, `cycle_note` says it
in one sentence, and the exit stays 0 — the ceiling is a planning input, not a
gate, and the caller is what stops. `cycle_note` is its own field rather than
a rewrite of `note`: `note` belongs to whoever computed independence.

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


WHERE A CONFLICT IS, NOT MERELY WHICH FILE (D-02)
---------------------------------------------------
D-02 asks the report to name file AND line on both sides of the split, and a
convergent edit gets that for free — the diff hunk header carries the base
line. A conflict does not: `merge-tree`'s prose (`CONFLICT (content): Merge
conflict in code.txt`) names the file and stops there, and its stage lines
carry OIDs, not positions. Naming only the file would leave the shipped prose
in cairn/commands/autonomous.md promising the operator something no shipped
line of this script produced.

The line is recoverable, and here is the measurement it rests on. The FIRST
line of `git merge-tree --write-tree A B` is the OID of the tree it just
wrote, and in that tree the conflicted path's blob carries the standard
markers — the same ones a real merge would leave in the working tree:

    $ git merge-tree --write-tree phase/7-alpha phase/9-beta   # exit 1
    2f2bcd14c1bf1c89ade97d540c2e895e7c3fbee5
    100644 c3c3aa5f… 1  code.txt
    ...
    CONFLICT (content): Merge conflict in code.txt

    $ git grep -n -I -e '^<<<<<<<' 2f2bcd14… -- ':(literal)code.txt'
    2f2bcd14…:code.txt:11:<<<<<<< phase/7-alpha

And 11 is git's own answer, not this script's approximation: cloning that
fixture and letting the merge actually happen puts `<<<<<<<` on line 11 of
the working file too. The bats test asserts both numbers against each other
for exactly that reason.

So `conflicts[]` entries carry `lines`: EVERY `<<<<<<<` in the merged blob,
1-based, in file order — a file with two conflicting hunks reports both
(measured: markers at 5 and 34 of the same file, one CONFLICT message). The
line is where the merged blob's conflict region BEGINS, which is the marker
line itself, one line above the first contested line of the A side.

Two shapes cannot produce a line, and both say so instead of guessing:

  - modify/delete, rename/*, and binary. Measured: a modify/delete conflict
    leaves the surviving side's content WHOLE in the tree, with no marker
    anywhere in it; `-I` skips binary outright. There is a file, there is no
    position.
  - a CONFLICT message git attached to no path at all.

In both, `lines` is null and `lines_note` says why — never 0, never 1.
Null is the same choice `conflicts` itself makes for a git too old to
pre-compute anything (Pitfall 3): an empty list reads as "no conflicting
lines" and a 1 reads as "the top of the file", and both are answers this
script did not measure.

`git grep` over a tree object is a read, and one call per conflicted path
rather than a blob pulled into memory and scanned here. It is not in the
static check's forbidden-token list and the list was NOT widened to admit it:
`["grep"` is a read verb in the same family as `["merge-base"` and
`["merge-tree"`, and it writes nothing.


WHY `reconcile` ONLY READS COMMITTED REFS, AND WRITES NOTHING
--------------------------------------------------------------
Every fact in the report comes from `git for-each-ref`, `git rev-list`,
`git diff`, `git merge-base`, `git merge-tree` and `git grep` over committed
refs (and, for the conflict lines, over the tree `merge-tree` itself wrote —
reading back an object git had already been asked to produce). No path
inside a live phase worktree is ever opened. A parallel agent is still editing
those files while this runs, and a report built from a half-written file is
confidently wrong (Pitfall 15).

`reconcile` performs no merge, no checkout and no write. It cannot resolve a
conflict — silently or otherwise — because resolving is not among the things
it is able to do. That is a property of the code, not a promise of prose, and
it is proven twice, the way phase 17 proved the same thing for
cairn-reconcile.py. First, a grep over the region delimited by this file's
RECONCILE-READ-ONLY-REGION markers, with comment lines filtered out (the
comments in there DISCUSS the verbs they forbid, so a grep over the raw text
would invalidate itself), finds no bd write verb, no cairn-journal write
subcommand, and no writing git subcommand. Second, a bats test
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


WHAT `cleanup` DETECTS, AND WHY IT IS A MECHANISM AND NOT A CLOCK
------------------------------------------------------------------
A run that dies mid-flight leaves two marks. A worktree registration whose
directory is gone, which git will drop the moment anyone asks it to. And a
lease nobody will ever renew or release, which would otherwise hold the phase
for the whole 4-hour TTL.

The second one is detectable AT ALL because of the identity phase 15 chose:
THE HOLDER IS A WORKTREE PATH. So a holder that is not in `git worktree list`
is, by construction, an owner that does not exist — a fact about the machine,
not an inference from elapsed time. That distinction is the entire design, and
it is worth stating in the sharpest form: a lease killed ONE MINUTE ago is not
stale, and never will be for another four hours. A TTL check would call it
healthy and walk past it. This one names it dead immediately, because the
directory its holder points at is not there.

The five categories, and what `--apply` does to each:

  orphan_registration  a worktree entry git marks `prunable` (its gitdir file
                       points nowhere), or whose directory is simply missing.
                       --apply: `git worktree prune`. Reported repo-wide, not
                       just for phase/* worktrees, because `prune` itself is
                       repo-wide — a report narrower than the action it
                       triggers would understate what --apply is about to do.

  orphan_lease         a HELD lease whose holder, realpath'd, is not among
                       this repo's live worktrees. --apply: `cairn-lease.py
                       release <N>`, which is also what writes the `released`
                       record to the journal. This script never writes lease
                       metadata itself — cairn-lease.py owns that object
                       WHOLE (a partial bd --metadata patch erases sibling
                       fields), so the release goes through the verb, always.

  stale_but_live       a lease marked `stale` whose holder IS still a live
                       worktree. REPORTED, NEVER RELEASED. Staleness means one
                       thing: nobody has heartbeated in four hours. It does
                       not mean nobody is there — the tree is right there on
                       disk. cairn-lease.py's own `acquire` already knows how
                       to reclaim a stale lease, and it does so at the moment
                       somebody actually wants the phase, which is the only
                       moment where the reclaim is worth its risk. Releasing
                       here would race that reclaim on behalf of an agent that
                       may merely be slow. The gap between THIS category and
                       orphan_lease is the whole point of the design: same
                       staleness, opposite verdict, decided by whether the
                       owner exists.

  retained             a live phase worktree that must not be removed, with
                       the reason named and a manual command printed. Three
                       reasons, and any one is enough: `git status
                       --porcelain` is non-empty (uncommitted work — the only
                       state here that git cannot reconstruct); `git rev-list
                       --count HEAD..<branch>` is above zero (commits not yet
                       in HEAD, so removing the branch would strand them); or
                       the phase's lease is still held BY THAT VERY WORKTREE,
                       stale or not (an agent is plausibly still working in
                       it, and a freshly prepared empty tree is otherwise
                       indistinguishable from finished work). Retained is the
                       default verdict, not the exception: everything that is
                       not provably safe lands here.

  removable            a live phase worktree that is clean AND wholly merged
                       into HEAD AND not holding its own lease. --apply:
                       `git worktree remove` (never `--force`) followed by
                       `git branch -d` (never `-D`). Both are the SAFE forms
                       on purpose, so git re-checks the same claim
                       independently a second time and refuses if this
                       script's reading was wrong. This is the ordinary end of
                       a phase, after reconciliation.

MEASURED CONSEQUENCE OF THE JOURNAL SPLIT, worth knowing before `removable`
is ever expected to fire: `prepare` takes the lease from inside the new
worktree, cairn-lease.py journals that acquisition, and the record lands in
`<worktree>/.cairn/journal.jsonl` (the split this file's docstring records
above). If a project does not ignore that path, every prepared worktree
reports `?? .cairn/` and is therefore RETAINED forever — safe, but it means
`removable` never fires at all. cairn's own repo ignores it
(`.gitignore`: `.cairn/journal.jsonl*`), and a project adopting cairn should
do the same. Retaining is the right failure direction either way, which is
why this is a note and not a special case in the code.

An inventory this script cannot trust is a hard stop, not an empty list: if
`git worktree list` comes back without the main checkout itself in it, every
lease in the repo would suddenly look orphaned and --apply would evict live
owners wholesale (T-18-11). So that case exits EXIT_GIT having decided
nothing.

Every path comparison — holder against worktree, worktree against worktree —
goes through `os.path.realpath` on BOTH sides. macOS resolves TMPDIR through a
/var -> /private/var symlink and git reports the PHYSICAL path, and a string
compare there would silently classify a live holder as an orphan (T-18-12).


WHY `cleanup` EXITS 0 WHERE `reconcile` EXITS 6
------------------------------------------------
`reconcile` exits 6 on a finding because its findings are JUDGEMENTS a person
has to make: which of two convergent intentions was meant, how a conflict
resolves. Nobody can automate that, so the exit code exists to stop a caller
under `set -e` from reading silence as agreement.

`cleanup`'s findings are the opposite kind of thing. An orphaned registration
and a dead lease are conditions THIS COMMAND ITSELF repairs, completely, with
one flag. There is no judgement left over, so there is nothing for a nonzero
exit to protect. `cleanup` exits 0 with orphans, without orphans, with
`--apply` and without it; `retained` is likewise a report and not a failure,
because a worktree with unsaved work in it is a normal state of the world and
not an error. What the exit code says here is "the sweep ran", and that is all
it is asked to say.


Usage:
    cairn-parallel.py batch     [--max N] [--cycle K] [--project-dir DIR]
                                [--json]
    cairn-parallel.py prepare N [--project-dir DIR] [--json]
    cairn-parallel.py reconcile [--phases 7,9] [--project-dir DIR] [--json]
    cairn-parallel.py cleanup   [--apply] [--phase N] [--project-dir DIR]
                                [--json]

    --project-dir DIR   project root for git/bd discovery (default:
                        $CLAUDE_PROJECT_DIR or cwd)
    --max N             ceiling on how many phases `batch` selects (default:
                        `autonomous.max_parallel` from .cairn/config.json,
                        itself 3 when that file says nothing)
    --cycle K           which cycle of an autonomous run this is. Past
                        `autonomous.max_cycles` (0 = no ceiling) `batch`
                        selects nothing and says why, exit 0 — it is a
                        read-only planner, not a gate. Omit the flag and the
                        cycle ceiling does not apply at all: a caller that
                        does not count cycles cannot be over one
    --phases LIST       comma-separated phase numbers `reconcile` restricts
                        itself to (default: every phase/* branch)
    --phase N           narrows `cleanup` to phase N's CANONICAL worktree
                        (`<root>-phase-N`, exactly what `prepare` builds) and
                        that phase's own lease. NOT the branch number, and
                        the difference is measured: `phase/25-tools` and
                        `phase/25-surfaces` both match phase 25, so a sweep
                        keyed on the branch and fired by the close of phase
                        25 would delete two live fronts' work. Every guard of
                        the full sweep still applies — it is a filter on the
                        inventory, not a laxer rule
    --apply             `cleanup` writes. Without it nothing anywhere is
                        touched, in any branch of the code — reading is the
                        default and writing is behind a named flag, as
                        everywhere else in this plugin
    --json              machine-readable output instead of the
                        `[cairn-parallel] ...` human lines

Behavior:
    batch      Calls `cairn-status.py --json` ONCE (through the CAIRN_STATUS
               seam) and reports:
                 {runnable, blocked, inconsistent, declared, note, max, cycle,
                  max_cycles, cycle_note, selected[], deferred[], announcement}
               `selected[]` entries carry {phase, title, slug, branch,
               worktree, next_command, reason, lease_stale}; `deferred[]`
               entries carry {phase, reason}; `inconsistent[]` entries carry
               {phase, reason, command} and name a phase that has a directory
               under .planning/phases/ and NO entry in ROADMAP.md — left out of
               the answer rather than scheduled (CairnGo-4oq). `deferred` means
               "runnable, not this round"; `inconsistent` means "the roadmap
               does not say this phase exists". `announcement` is the ready-made
               text for /cairn:autonomous step 0.4: how many phases run, why
               each one, what was left out and why, plus the honesty line when
               `declared` is false.

    prepare N  Runs from the MAIN checkout only — invoked from a linked
               worktree it refuses with EXIT_USAGE, because a worktree of a
               worktree is not what any of this names. Resolves slug, branch
               and path; runs the four-step acquisition above; reports:
                 {phase, slug, branch, worktree, base_commit, created,
                  lease: {holder, acquired_at}, planning_files_forbidden[],
                  response_language, response_language_source}
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
               truncated to 200 characters per line. A conflict is
               {path, lines, lines_note, messages}, where `lines` holds every
               `<<<<<<<` marker line of the merged blob — file AND line on
               both sides of the split (D-02) — and is null with a
               `lines_note` when no marker exists to point at (modify/delete,
               rename, binary), never 0 and never 1. `planning_writes[]`
               names any branch whose diff touches .planning/STATE.md,
               .planning/ROADMAP.md or .planning/REQUIREMENTS.md — a named
               finding with no effect on the exit code (D-03).
               A repo with no phase/* branch exits 0 with empty lists and
               says there is nothing to reconcile.

    cleanup    Crosses `git worktree list --porcelain` with `cairn-lease.py
               status --all --json` and reports the five categories above:
                 {apply, orphan_registrations[], orphan_leases[],
                  stale_but_live[], retained[], removable[], applied[]}
               `orphan_registrations[]` entries carry {path, branch, reason};
               `orphan_leases[]` and `stale_but_live[]` carry {phase, id,
               holder, acquired_at, heartbeat_at, stale}; `retained[]` carries
               {phase, path, branch, reasons[], manual_command}; `removable[]`
               carries {phase, path, branch}. `applied[]` is empty without
               `--apply` and otherwise lists, item by item, exactly what was
               done: {action: worktree_prune|lease_release|worktree_remove,
               ...}. Exit is 0 either way — see the asymmetry note above.
               With `--phase N` the report carries `phase` and the whole scan
               is narrowed to that phase's canonical worktree and lease.

               A `worktree_remove` entry also carries `journal_dropped`.
               MEASURED while wiring roadmap criterion 8: with D-05 in place
               this script calls a journal-only worktree removable, and git's
               own `worktree remove` refuses it (`contains modified or
               untracked files`) because git never heard of DJOUR-03.
               `--force` would answer that by switching off git's re-check —
               the second independent verdict this function keeps on purpose.
               So `.cairn/journal/`, and only it, is deleted first, and git
               judges everything else on its own terms. A refusal after that
               is a real one, and it is reported.

Exit codes:
    0  ok (including `created: false` — reusing an existing tree is success;
       a `reconcile` that found neither a conflict nor a convergent edit; and
       EVERY `cleanup`, orphans or not, applied or not)
    2  usage error (bad/missing phase, `prepare` run from a linked worktree,
       unusable --max or --phases, or a downstream script that could not be
       driven)
    3  the phase's lease is held by another live holder — nothing was
       created, or everything this invocation created was rolled back. A
       report, not an error, exactly as cairn-lease.py reads its own 3
    4  git refused: the worktree path is occupied by something else, the
       branch already exists without its worktree, `git worktree add` itself
       failed, or (`cleanup`) `git worktree list` came back without the main
       checkout in it and is therefore not an inventory anything may be
       declared orphaned against
    5  bd unavailable, or a companion script (cairn-lease.py /
       cairn-status.py) is missing
    6  `reconcile` has findings: a convergent edit, a merge conflict, or a
       git too old to pre-compute conflicts at all. A report the caller
       cannot mistake for success, never a resolution

Test/override seams (CONVENTIONS.md's CAIRN_* env-seam note, same shape as
CAIRN_GBSYNC / CAIRN_MAP / CAIRN_GATE / CAIRN_JOURNAL):
    CAIRN_LEASE    default: the sibling cairn-lease.py
    CAIRN_STATUS   default: the sibling cairn-status.py
    CAIRN_CONFIG   default: the sibling cairn-config.py
"""
import argparse
import json
import os
import re
import shutil
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
CAIRN_CONFIG = os.environ.get(
    "CAIRN_CONFIG", str(SCRIPTS_DIR / "cairn-config.py"))

# Last-resort fallback for the parallelism ceiling, used only when
# cairn-config.py cannot be run or answers with something unreadable. It
# echoes that script's schema default on purpose: the schema is the source,
# this number is what keeps `batch` working when the source cannot be
# reached. If the two ever disagree, the schema is right.
MAX_PARALLEL_FALLBACK = 3
# Same contract for the cycle ceiling, and 0 is the value that means "no
# ceiling" — so a config that cannot be reached imposes none.
MAX_CYCLES_FALLBACK = 0

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
         "reconcile [--phases 7,9]|cleanup [--apply] [--phase N]} "
         "[--project-dir DIR] [--json]")


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
    """[{path, branch, prunable, prunable_reason}] for every worktree of this
    repo, parsed from `git worktree list --porcelain`. `branch` is the short
    name, or None for a detached/bare entry. Paths are realpath'd because
    macOS TMPDIR resolves through a /var -> /private/var symlink and git
    reports the PHYSICAL path.

    `prunable` is git's OWN verdict, measured rather than inferred: delete a
    worktree's directory and the very next `git worktree list --porcelain`
    carries `prunable gitdir file points to non-existent location` for it.
    That line is what makes a dead run's leftover registration a fact this
    script reads instead of a state it guesses at (`cleanup`)."""
    rc, out, _ = run_git(top, ["worktree", "list", "--porcelain"])
    if rc != 0:
        return []
    entries = []
    current = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = {"path": os.path.realpath(line[len("worktree "):]),
                       "branch": None, "prunable": False,
                       "prunable_reason": None}
            entries.append(current)
        elif line.startswith("branch ") and current is not None:
            ref = line[len("branch "):]
            current["branch"] = ref[len("refs/heads/"):] \
                if ref.startswith("refs/heads/") else ref
        elif line.startswith("prunable") and current is not None:
            current["prunable"] = True
            current["prunable_reason"] = line[len("prunable"):].strip() or None
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
    """{phase, slug, branch, branch_source, worktree} — the single naming
    authority for both verbs. `batch` announces what this returns and
    `prepare` creates what this returns; the bridge test compares the two by
    realpath.

    The path is built from the ROOT's own basename plus an int phase, never
    from a user-supplied string, and is asserted to be a SIBLING of the root
    before any caller writes there (T-18-01).

    THE NAME IS ADOPTED BEFORE IT IS DERIVED (FIX-02, CairnGo-r4g). MEASURED
    live on v1.4: `batch --json` returned `slug: null` and `branch: phase/19`
    for phase 19, which had no directory yet. Once
    `.planning/phases/19-<slug>` exists the same phase would resolve to
    `phase/19-<slug>` — a DIFFERENT branch for the same work. Nothing breaks
    today because the worktree path never moves and reconcile discovers by
    `refs/heads/phase/*`, but two branches for one phase are reachable:
    prepare refuses a branch of the SAME name with no worktree
    (cairn-parallel.py, cmd_prepare) and has nothing to say about one of a
    NEW name, which is precisely what a late slug produces.

    So the name comes from whatever already exists, strongest evidence first:

      worktree         the canonical worktree is registered and git says what
                       branch is checked out there. This is the identity the
                       issue itself names as stable — the path does not move.
      existing-branch  no canonical worktree, and EXACTLY ONE refs/heads/
                       phase/<N> ref. That is the name prepare gave it.
      derived          neither of those, so build the name from the slug —
                       byte for byte what this function has always done.

    WHY MORE THAN ONE BRANCH DOES NOT DIE HERE, against the house rule of
    never taking the first of an ambiguous match: two branches for one phase
    is the ORDINARY state of a phase split across two fronts. MEASURED in
    this repository right now — `phase/25-tools` and `phase/25-surfaces` both
    match phase 25. Dying would take the whole `batch` down over one phase,
    and `batch` is the surface that decides what runs at all. The third rung
    keeps today's behaviour exactly, and `branch_source` says the choice was
    derived rather than read — a surface that picks among three sources and
    does not say which is the shape of lie this phase exists to remove.
    """
    slug = phase_slug(top, phase)
    worktree = Path(top).parent / f"{Path(top).name}-phase-{phase}"
    if worktree.parent != Path(top).parent:
        die(f"refusing to place a worktree outside the repo's parent "
            f"directory: {worktree}", EXIT_GIT)

    branch, source = None, "derived"
    entry = worktree_entry_at(top, worktree)
    if entry is not None and entry.get("branch"):
        branch, source = entry["branch"], "worktree"
    else:
        same = [name for n, name in phase_branches(top) if n == phase]
        if len(same) == 1:
            branch, source = same[0], "existing-branch"
    if branch is None:
        branch = f"phase/{phase}-{slug}" if slug else f"phase/{phase}"

    return {"phase": phase, "slug": slug, "branch": branch,
            "branch_source": source, "worktree": str(worktree)}


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
    # Read from the MAIN checkout, never from the freshly created worktree:
    # the config the operator configured is the one that governs, and a
    # worktree is a copy of a commit, not a place anyone configured.
    language, language_source = config_language(top)
    out = {
        "phase": phase,
        "slug": layout["slug"],
        "branch": branch,
        "branch_source": layout["branch_source"],
        "worktree": str(worktree),
        "base_commit": base_commit or None,
        "created": created_worktree,
        "lease": {"holder": entry.get("holder"),
                  "acquired_at": entry.get("acquired_at")},
        "planning_files_forbidden": list(PLANNING_FILES_FORBIDDEN),
        "response_language": language,
        "response_language_source": language_source,
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
        if language is None:
            print("[cairn-parallel] response language: unavailable "
                  "(cairn-config could not be read) — say so in the "
                  "announcement rather than guessing one")
        else:
            print(f"[cairn-parallel] response language: {language} "
                  f"({language_source}) — the subagent's user-facing output "
                  f"goes in it")
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# batch
# --------------------------------------------------------------------------- #
def cmd_prepare_bead(args, top):
    """`prepare-bead <id> [--base <ref>]` — the bead unit of `prepare`
    (phase 47 / IMPL-01): one worktree per bead, branched from the PR
    branch the implement verb is building, its lease keyed `bead:<id>` and
    pointing at that worktree. Same refusals as `prepare`, same output
    shape, plus the bead's title so the implementer prompt can carry it."""
    bead_id = args.bead
    if is_linked_worktree(top):
        die(f"prepare-bead runs from the main checkout only, and {top} is a "
            f"linked worktree — run it from the repo the worktrees hang off",
            EXIT_USAGE)
    title = bead_title(top, bead_id)
    layout = bead_layout(top, bead_id, title)
    worktree = Path(layout["worktree"])
    branch = layout["branch"]
    key = f"bead:{bead_id}"
    base = args.base or "HEAD"
    if args.base:
        rc, _, _ = run_git(top, ["rev-parse", "--verify", "--quiet",
                                 f"{args.base}^{{commit}}"])
        if rc != 0:
            die(f"--base {args.base!r} is not a branch or commit of this "
                "repo", EXIT_USAGE)
    pre = lease_status(top, key)
    if (pre.get("held") and not pre.get("stale")
            and not same_path(pre.get("holder"), worktree)):
        refuse_held(key, pre, False, args.json)
    created_worktree = created_branch = False
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
                f"{worktree} — refusing to guess which one is the bead's "
                f"work; remove or rename it first", EXIT_GIT)
        rc, _, err = run_git(top, ["worktree", "add", "-b", branch,
                                   str(worktree), base])
        if rc != 0:
            die(f"git worktree add failed: {err or 'unknown error'}",
                EXIT_GIT)
        created_worktree = created_branch = True
    rc, entry = lease_acquire(top, key, worktree)
    if rc == EXIT_HELD:
        rolled_back = rollback(top, worktree, branch, created_worktree,
                               created_branch)
        refuse_held(key, entry if isinstance(entry, dict) else {},
                    rolled_back, args.json)
    _, base_commit, _ = run_git(worktree, ["rev-parse", "HEAD"])
    language, language_source = config_language(top)
    out = {
        "bead": bead_id, "title": title, "short": layout["short"],
        "slug": layout["slug"], "branch": branch, "base": base,
        "worktree": str(worktree), "base_commit": base_commit or None,
        "created": created_worktree,
        "lease": {"key": key, "holder": entry.get("holder"),
                  "acquired_at": entry.get("acquired_at")},
        "planning_files_forbidden": list(PLANNING_FILES_FORBIDDEN),
        "response_language": language,
        "response_language_source": language_source,
    }
    if args.json:
        print(json.dumps(out))
    else:
        verb = "prepared" if created_worktree else "reused"
        print(f"[cairn-parallel] {verb} worktree {worktree} on branch "
              f"{branch} from {base} (base {base_commit})")
        print(f"[cairn-parallel] bead {bead_id} lease held by "
              f"{out['lease']['holder']} since {out['lease']['acquired_at']}")
        print(f"[cairn-parallel] forbidden in this worktree (D-03): "
              f"{', '.join(PLANNING_FILES_FORBIDDEN)}")
    sys.exit(EXIT_OK)


def reconcile_beads(args, top):
    """The bead unit of reconcile (phase 47): every bead/* branch against
    ONE base — the PR branch the merger folds them into — not against each
    other. The merger takes them one at a time, so what matters is what
    each one will raise when it lands, and what it would change in silence
    on lines the base moved too."""
    version = git_version(top)
    base_ref = args.base or "HEAD"
    branches, pairs, planning_writes = [], [], []
    findings, unknown = 0, False
    for short, branch in bead_branches(top):
        anc = common_ancestor(top, base_ref, branch)
        entry = {"bead": short, "phase": None, "branch": branch, "base": anc,
                 "commits": None, "files": None, "insertions": None,
                 "deletions": None}
        edits = []
        if anc:
            rc, out, _ = run_git(top, ["rev-list", "--count",
                                       f"{anc}..{branch}"])
            entry["commits"] = int(out) if rc == 0 and out.isdigit() else None
            stat = numstat(top, anc, branch)
            entry.update(files=stat["files"], insertions=stat["insertions"],
                         deletions=stat["deletions"])
            touched = [p for p in stat["paths"]
                       if p in PLANNING_FILES_FORBIDDEN]
            if touched:
                planning_writes.append({"bead": short, "branch": branch,
                                        "files": touched})
            edits = convergent_edits(diff_hunks(top, anc, base_ref),
                                     diff_hunks(top, anc, branch),
                                     base_ref, branch)
        conflicts, note = merge_tree_conflicts(top, base_ref, branch, version)
        if conflicts is None:
            unknown = True
        findings += len(edits) + (len(conflicts) if conflicts else 0)
        branches.append(entry)
        pairs.append({"branches": [base_ref, branch], "base": anc,
                      "convergent_edits": edits, "conflicts": conflicts,
                      "conflicts_note": note})
    result = {"git_version": version, "unit": "bead", "base_ref": base_ref,
              "branches": branches, "pairs": pairs,
              "planning_writes": planning_writes, "findings_total": findings}
    if args.json:
        print(json.dumps(result))
    else:
        print_report(result)
    sys.exit(EXIT_FINDINGS if (findings or unknown) else EXIT_OK)


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
    # Named BEFORE the note and the honesty line, because this one is not about
    # scheduling at all: it says a phase on disk was left out of the answer
    # entirely, and prints the command that fixes it (CairnGo-4oq).
    for i in result.get("inconsistent") or []:
        lines.append(f"  phase {i['phase']} is not schedulable: {i['reason']}"
                     f" — {i['command']}")
    if result.get("cycle_note"):
        lines.append(result["cycle_note"])
    if result["note"]:
        lines.append(result["note"])
    if not result["declared"]:
        # The twin of cairn-status.py's own sentence, off the SAME flag this
        # script never recomputes. "in this project" since v1.7: `declared`
        # reads tracker edges too, and a migrated repo has no roadmap to name.
        lines.append("No dependencies are declared anywhere in this project, "
                     "so this split reflects what is recorded, not a verified "
                     "ordering.")
    return "\n".join(lines)


def config_value(top, key, fallback):
    """One setting out of cairn-config.py, or `fallback`.

    Defensive in exactly the shape cairn-status.py's fetch_lease_status()
    uses: a subprocess that cannot be started, a nonzero exit, unparsable
    JSON or a payload without a `value` all degrade to the fallback. `batch`
    is a read-only planner and a missing/broken config file is not a reason
    to take it down — nor is it a reason to invent a second config resolver
    here (see the docstring).
    """
    try:
        proc = subprocess.run(
            [sys.executable, str(CAIRN_CONFIG), "get", key, "--json",
             "--project-dir", str(top)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return fallback
    if proc.returncode != 0:
        return fallback
    try:
        data = json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return fallback
    if not isinstance(data, dict) or "value" not in data:
        return fallback
    return data["value"]


def config_language(top):
    """(value, source) for `agents.response_language`, or (None,
    "unavailable").

    Same defensive shape as config_value(): a subprocess that cannot start, a
    nonzero exit, unparsable JSON, or a payload missing either field degrades.
    It degrades to a NULL rather than to the string "English" on purpose — see
    the docstring: the default lives in cairn-config.py's schema and nowhere
    else, and a guessed language would be indistinguishable from a configured
    one at the point where it matters.
    """
    try:
        proc = subprocess.run(
            [sys.executable, str(CAIRN_CONFIG), "get",
             "agents.response_language", "--json", "--project-dir", str(top)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None, "unavailable"
    if proc.returncode != 0:
        return None, "unavailable"
    try:
        data = json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return None, "unavailable"
    if not isinstance(data, dict):
        return None, "unavailable"
    value, source = data.get("value"), data.get("source")
    if not isinstance(value, str) or not value or not isinstance(source, str):
        return None, "unavailable"
    return value, source


def config_int(top, key, fallback, minimum):
    """config_value() narrowed to an int at or above `minimum`. bool is an int
    subclass in Python and `true` is not a ceiling, so it is excluded."""
    value = config_value(top, key, fallback)
    if isinstance(value, bool) or not isinstance(value, int):
        return fallback
    return value if value >= minimum else fallback


def cmd_batch(args, top):
    if args.max is not None and args.max < 1:
        die(f"--max must be at least 1 (got {args.max})\n" + USAGE,
            EXIT_USAGE)
    if args.cycle is not None and args.cycle < 0:
        die(f"--cycle must be zero or more (got {args.cycle})\n" + USAGE,
            EXIT_USAGE)
    # An explicit --max always wins over the setting; with no flag the ceiling
    # is autonomous.max_parallel, whose own schema default is 3 — so a repo
    # with no .cairn/config.json selects exactly what it selected before.
    max_selected = (args.max if args.max is not None
                    else config_int(top, "autonomous.max_parallel",
                                    MAX_PARALLEL_FALLBACK, 1))

    # The cycle ceiling only exists for a caller that counts cycles: with no
    # --cycle it does not apply at all, and 0 means no ceiling. Above it,
    # `batch` selects nothing and SAYS SO — a limit enforced in silence is
    # indistinguishable from a run that simply found no work (T-29-10).
    max_cycles = config_int(top, "autonomous.max_cycles",
                            MAX_CYCLES_FALLBACK, 0)
    over_cycle = (args.cycle is not None and max_cycles > 0
                  and args.cycle > max_cycles)
    cycle_note = None
    if over_cycle:
        cycle_note = (f"cycle {args.cycle} is past the "
                      f"autonomous.max_cycles ceiling of {max_cycles}, so no "
                      f"phase is selected. Raise or clear it with "
                      f"`cairn-config.sh set autonomous.max_cycles N` "
                      f"(0 = no ceiling).")

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
        if over_cycle:
            deferred.append({"phase": n,
                             "reason": f"cycle {args.cycle} is above the "
                                       f"autonomous.max_cycles ceiling of "
                                       f"{max_cycles}"})
            continue
        entry = held.get(n)
        if entry is not None and not entry.get("stale"):
            deferred.append({"phase": n,
                             "reason": f"lease held by {entry.get('holder')} "
                                       f"since {entry.get('acquired_at')}"})
            continue
        if len(selected) >= max_selected:
            deferred.append({"phase": n,
                             "reason": f"above the --max {max_selected} "
                                       f"ceiling"})
            continue
        layout = phase_layout(top, n)
        cmd = commands.get(n) or {}
        selected.append({
            "phase": n,
            "title": cmd.get("title"),
            "slug": layout["slug"],
            "branch": layout["branch"],
            # Which of the three sources named that branch — adopted from the
            # canonical worktree, adopted from the one existing ref, or
            # derived from the slug (FIX-02).
            "branch_source": layout["branch_source"],
            "worktree": layout["worktree"],
            "next_command": cmd.get("command"),
            "reason": cmd.get("reason"),
            "lease_stale": bool(entry is not None and entry.get("stale")),
        })

    result = {
        # Passed through verbatim: whoever computed independence owns these.
        "runnable": runnable,
        "blocked": [b for b in (par.get("blocked") or [])],
        # Passed through verbatim for the same reason as `runnable`: whoever
        # computed independence owns the judgement that a phase is on disk
        # without a roadmap entry. `batch` reports it, never recomputes it.
        "inconsistent": [i for i in (par.get("inconsistent") or [])
                         if isinstance(i, dict)],
        "declared": bool(par.get("declared")),
        "note": par.get("note"),
        "max": max_selected,
        # The cycle ceiling gets its OWN field rather than overwriting `note`:
        # that one is passed through verbatim from whoever computed
        # independence, and borrowing it here would put two authors' words in
        # one place. `cycle` is null when the caller does not count cycles.
        "cycle": args.cycle,
        "max_cycles": max_cycles,
        "cycle_note": cycle_note,
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
# === RECONCILE-READ-ONLY-REGION-BEGIN ===
#
# Everything between this marker and the END one speaks to git in read
# invocations only. tests/cairn-parallel.bats extracts exactly this region and
# asserts none of the following appears in it: the bd write verbs "create",
# "update", "close", "reopen"; the cairn-journal write subcommands "observe",
# "lease", "append"; or a writing git subcommand at the head of an argument
# list — ["merge", ["checkout", ["commit", ["reset", ["clean", ["stash",
# ["branch", ["worktree", ["apply", ["push", ["rebase". Adding one here
# without noticing is exactly what that test exists to stop.
#
# (Head-of-list is how the git ones are matched because "branch" and
# "worktree" are also legitimate KEYS in this script's own JSON output, while
# ["branch" can only ever be an invocation of `git branch`. Read subcommands
# survive it for free: ["merge-base" and ["merge-tree" do not match ["merge".)
#
# The conflict-line lookup added here calls `git grep` over the tree
# merge-tree wrote. That is a read, and the forbidden list above was NOT
# widened to let it through — ["grep" was never on it, for the same reason
# ["merge-base" is not: it produces no object, moves no ref and touches no
# file. Said out loud because "the check went quiet after I edited it" and
# "the check never had anything to say" are different sentences.
#
# That test filters `^#` comment lines FIRST, and this banner is why: it has
# to name the forbidden tokens in the very shape the grep looks for, or it
# would be stating a rule in words the check cannot see. A grep over the
# unfiltered text therefore matches this comment — which the test also
# asserts, so the filter cannot be quietly dropped and turned into a check
# that only ever reads comments. The filter is load-bearing, not decoration.
# The companion proof is the mutation test: reconcile runs against a real
# fixture and the tree, the branch heads and every file hash come out
# unchanged. See the module docstring for why both proofs, not one.
# --------------------------------------------------------------------------- #

# Phase number out of a branch name, by the SAME rule prepare used to build
# it: `phase/<N>-<slug>`, or `phase/<N>` for a phase with no directory. These
# constants live beside the code they serve rather than with the module-level
# block above, so the greppable region is self-contained.
PHASE_BRANCH = re.compile(r"^phase/0*(\d+)(?:-|$)")
# The bead unit (phase 47 / IMPL-01): `bead/<short>-<slug>`, `<short>` being
# the bead id without its project prefix (`CairnGo-o1vm` -> `o1vm`).
BEAD_BRANCH = re.compile(r"^bead/([A-Za-z0-9.]+)(?:-|$)")


def bead_short(bead_id):
    return bead_id.split("-", 1)[1] if "-" in bead_id else bead_id


def bead_slug(title, words=4):
    toks = re.findall(r"[a-z0-9]+",
                      (title or "").lower().encode("ascii", "ignore").decode())
    return "-".join(toks[:words])


def bead_title(top, bead_id):
    proc = subprocess.run(["bd", "-C", str(top), "show", bead_id, "--json"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"bd show {bead_id} failed: {proc.stderr.strip()[:200]} — the "
            "bead has to exist before a worktree is named after it",
            EXIT_USAGE)
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        die(f"bd show {bead_id} returned no JSON", EXIT_NO_BD)
    issue = data[0] if isinstance(data, list) and data else data
    return (issue or {}).get("title") or ""


def bead_layout(top, bead_id, title):
    """{bead, short, slug, branch, worktree} — the single naming authority
    for the bead unit, the same way phase_layout() is for phases: the path
    is the ROOT's basename plus the bead's short id, a sibling of the root,
    and the branch carries the short id and a slug of the title."""
    short = bead_short(bead_id)
    if not SLUG_OK.match(short):
        die(f"bead id {bead_id!r} does not yield a safe path component",
            EXIT_USAGE)
    worktree = Path(top).parent / f"{Path(top).name}-bead-{short}"
    if worktree.parent != Path(top).parent:
        die(f"refusing to place a worktree outside the repo's parent "
            f"directory: {worktree}", EXIT_GIT)
    slug = bead_slug(title)
    branch = f"bead/{short}-{slug}" if slug else f"bead/{short}"
    return {"bead": bead_id, "short": short, "slug": slug or None,
            "branch": branch, "worktree": str(worktree)}


def bead_branches(top):
    """[(short, branch)] for every refs/heads/bead/* ref — discovery by the
    name prepare-bead gave it (D-01), never by what an agent reports."""
    rc, out, _ = run_git(top, ["for-each-ref", "--format=%(refname:short)",
                               "refs/heads/bead/*"])
    if rc != 0 or not out:
        return []
    found = []
    for name in out.splitlines():
        m = BEAD_BRANCH.match(name.strip())
        if m:
            found.append((m.group(1), name.strip()))
    found.sort()
    return found

# `@@ -a[,b] +c[,d] @@` — the raw material of the detector. `b` defaults to 1
# when absent (`@@ -1 +1 @@` replaces exactly one base line); `b == 0` is a
# pure insertion after base line a (`@@ -41,0 +42 @@`).
HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

# `100644 <oid> 1\t<path>` — merge-tree's conflicted-entry lines, which name
# the paths reliably. The prose `CONFLICT (...)` lines are carried through as
# messages but never parsed for a path: their shape varies by conflict kind
# (`Merge conflict in <path>` puts it last, `modify/delete` puts it first).
MERGE_TREE_STAGE = re.compile(r"^\d{6} [0-9a-f]{40,} [123]\t(.+)$")

# The FIRST line of `merge-tree --write-tree` output is the OID of the tree it
# wrote, and that tree is where the conflicted blobs — markers and all — can
# be read back from. Matched rather than assumed: an unexpected first line
# yields "line unknown" with a note, not a lookup against a bogus rev.
MERGE_TREE_OID = re.compile(r"^[0-9a-f]{40,}$")

# The opening marker of a conflict region in a merged blob, anchored at
# column 1. `git grep` reads this as a basic regular expression.
CONFLICT_MARKER = "^<<<<<<<"

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


def conflict_lines(top, tree, path):
    """(lines, note) — WHERE the conflict is, not merely which file.

    `tree` is the tree `merge-tree --write-tree` just wrote; in it the
    conflicted path's blob carries the same `<<<<<<<` markers a real merge
    would leave on disk. Every marker line is returned, 1-based and in file
    order, so a file with two conflicting hunks reports both.

    Reading it back is a read: `git grep` over an existing object produces
    nothing and moves nothing. `-I` skips binary, which is also why a binary
    conflict lands in the (None, note) branch rather than reporting a match
    against bytes nobody can read.

    (None, note) is the answer whenever no marker exists to point at — a
    modify/delete conflict leaves the surviving side's content whole, with
    no marker in it at all. Naming line 0 or line 1 there would be an
    invented position dressed as a measured one."""
    if tree is None:
        return None, ("git did not name the tree it wrote, so its merged "
                      "blobs cannot be read back — the conflicting lines are "
                      "UNKNOWN here; git will point at them at merge time")
    rc, out, err = run_git(top, ["grep", "-n", "-I", "--no-color",
                                 "-e", CONFLICT_MARKER, tree,
                                 "--", f":(literal){path}"])
    # `git grep` exits 1 on "no match", which is a finding, not a failure.
    if rc not in (EXIT_OK, 1):
        detail = err.splitlines()[0] if err else f"exit {rc}"
        return None, (f"the merged blob could not be read ({detail}) — the "
                      f"conflicting lines are UNKNOWN here, not absent")
    prefix = f"{tree}:{path}:"
    found = []
    for line in out.split("\n"):
        if not line.startswith(prefix):
            continue
        number = line[len(prefix):].split(":", 1)[0]
        if number.isdigit():
            found.append(int(number))
    if not found:
        return None, ("no conflict marker in the merged blob — a "
                      "modify/delete or rename conflict leaves one side's "
                      "content whole and a binary one is never marked, so "
                      "the file is named and the line is not knowable here")
    return found, None


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
    emitted = out.split("\n")
    head = emitted[0].strip() if emitted else ""
    tree = head if MERGE_TREE_OID.match(head) else None
    paths = []
    messages = []
    for line in emitted:
        m = MERGE_TREE_STAGE.match(line)
        if m:
            if m.group(1) not in paths:
                paths.append(m.group(1))
        elif line.startswith("CONFLICT "):
            messages.append(line)
    conflicts = []
    for path in paths:
        lines, note = conflict_lines(top, tree, path)
        conflicts.append({"path": path, "lines": lines, "lines_note": note,
                          "messages": [m for m in messages if path in m]})
    if not conflicts and messages:
        conflicts.append({"path": None, "lines": None,
                          "lines_note": ("git named no file for this "
                                         "conflict, so there is nothing to "
                                         "locate a line inside of"),
                          "messages": messages})
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
        who = (f"bead {b['bead']}" if b.get("bead") else f"phase {b['phase']}")
        say(f"{who} ({b['branch']}): {counts}")

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
                where = c["path"] or "(git named no file)"
                if c["lines"]:
                    say(f"  {where}:"
                        f"{','.join(str(n) for n in c['lines'])}")
                else:
                    say(f"  {where}  (line unknown: {c['lines_note']})")
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
    if getattr(args, "beads", False):
        return reconcile_beads(args, top)
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
# === RECONCILE-READ-ONLY-REGION-END ===
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# cleanup
#
# Deliberately BELOW the read-only region's END marker: this verb prunes
# registrations, removes worktrees and deletes branches, and none of that
# belongs inside a block whose whole claim is that it writes nothing.
# --------------------------------------------------------------------------- #
def lease_release(top, phase):
    """`cairn-lease.py release <N>` through the CAIRN_LEASE seam. The verb
    does the whole job — it vacates the metadata object WHOLE and writes the
    `released` record to the journal itself — which is exactly why this
    script calls it instead of touching bd metadata directly: a partial
    `bd update --metadata` patch would erase the lease's sibling fields."""
    _, data = lease_json(top, ["release", str(phase),
                               "--project-dir", str(top)])
    return data if isinstance(data, dict) else {}


# The one path whose loss changes no verdict anywhere (DJOUR-03), and
# therefore the one path that may not hold a worktree hostage.
JOURNAL_PREFIX = ".cairn/journal/"


def worktree_dirty(path):
    """Does that worktree carry work git cannot reconstruct from any ref?

    Uncommitted changes AND untracked files both count, because git can
    rebuild neither. A worktree whose directory is gone reads as 'not dirty'
    here and never reaches this function anyway: it is an
    orphan_registration before any of this is asked.

    EXCEPT `.cairn/journal/` (D-05, CairnGo-rhq). MEASURED at the close of
    phase 28: versioning the journal made every worktree that journals stop
    being removable, and the trap closes from both sides —

        uncommitted partition -> "uncommitted changes (git cannot recreate
                                  these)"
        committed partition   -> "carries commits HEAD lacks"

    — so a worktree only becomes removable after its partition is committed
    AND merged back, and nothing in cairn's flow does either. The journal is
    the one cairn artifact whose loss changes NO verdict (DJOUR-03), and that
    is exactly why it cannot be grounds for retention: retention is for work
    git cannot recreate, and this is not that.

    THE CALL CHANGED WITH THE FILTER, AND HAD TO. MEASURED 2026-08-07 against
    this project's own .gitignore (`.cairn/journal/*` plus
    `!.cairn/journal/*.jsonl`):

        $ git status --porcelain            # what this used to run
        ?? .cairn/                          <- the DIRECTORY, collapsed
        $ git status --porcelain -uall
        ?? .cairn/journal/-0001.jsonl       <- and only now does a path
                                               filter have a path to match

    With `-u normal` git collapses a wholly-untracked directory into one
    line, and `.cairn/` does not start with `.cairn/journal/`. A filter over
    the old call would have been inert — correct-looking, and doing nothing.
    `-z` comes along so paths arrive raw (no quoting, no escapes) and a
    rename arrives as two fields instead of one line with an arrow in it.

    AND IT READS THE BYTES RAW. run_git() .strip()s stdout, which eats the
    LEADING SPACE of a porcelain status pair: ` M .cairn/journal/-0001.jsonl`
    arrives as `M .cairn/...`, the path offset moves by one, and the filter
    silently stops matching. MEASURED — an untracked `?? path` survives the
    strip (it starts with `?`) while a modified ` M path` does not, so the
    filter would have worked for the case that was tested and failed for the
    case that was not. run_git_raw() exists for exactly this.

    Anything that cannot be measured is retained, never removed.
    """
    rc, out, _ = run_git_raw(path, ["status", "--porcelain", "-z", "-uall"])
    if rc != 0:
        return True
    for entry in out.split("\0"):
        # `XY <path>`: the status pair, one space, then the path. A rename's
        # second field is a bare path with no status pair, and it is measured
        # by the same rule — a rename INTO .cairn/journal/ is still journal.
        path_part = entry[3:] if len(entry) > 3 and entry[2] == " " else entry
        if not path_part.strip():
            continue
        if path_part.startswith(JOURNAL_PREFIX):
            continue
        return True
    return False


def commits_ahead(top, branch):
    """How many commits `branch` carries that HEAD does not. None when the
    count cannot be taken — which, like an unreadable status, retains."""
    rc, out, _ = run_git(top, ["rev-list", "--count", f"HEAD..{branch}"])
    if rc != 0 or not out.isdigit():
        return None
    return int(out)


def held_lease_by_holder(leases):
    """{realpath'd holder: entry} for every HELD lease, stale or not.

    This keeps `cleanup --apply` from removing a worktree that still owns its
    phase — a freshly prepared, still-empty tree is clean and wholly merged,
    and would otherwise look exactly like finished work. Staleness is
    deliberately NOT a discriminator here, for the same reason it is not one
    in stale_but_live: a stale lease whose tree is right there on disk means
    an agent that has not heartbeated, not an agent that is gone. Refusing to
    release that lease while deleting the tree underneath it would be the
    incoherent half-measure — so both halves retain."""
    by_holder = {}
    for entry in leases:
        if not entry.get("held"):
            continue
        holder = entry.get("holder")
        if holder:
            by_holder[os.path.realpath(str(holder))] = entry
    return by_holder


def cleanup_scan(top, phase=None):
    """The whole report, computed without writing anything anywhere.

    With `phase`, the scan is narrowed to the CANONICAL worktree of that
    phase — `phase_layout(top, phase)["worktree"]`, exactly and only what
    `prepare` builds — and to that phase's own lease.

    WHY THE CANONICAL PATH AND NOT THE BRANCH PATTERN, measured 2026-08-07 in
    cairn's own repository and the reason this parameter exists at all:

        $ cairn-parallel.py cleanup --json --project-dir ~/Projects/CairnGo
        removable: CairnGo-25-surfaces, CairnGo-25-tools,
                   CairnGo-phase-21, CairnGo-phase-24, CairnGo-phase-26

    The first two are the LIVE worktrees of the two fronts of phase 25 — both
    clean, both level with HEAD, neither holding a lease. `PHASE_BRANCH`
    matches `phase/25-tools` and `phase/25-surfaces` as phase 25 just as
    surely as it matches `phase/21`, so a per-phase sweep keyed on the branch
    number, fired by the close of phase 25, would delete two agents' live
    work. Keyed on the canonical path, the three orphans match and the two
    live trees do not.

    Everything else is unchanged: a narrowed scan applies the same dirty /
    unmerged / lease-held guards, and the inventory check below still runs
    against the FULL worktree list, because an inventory that cannot be
    trusted must stop the sweep no matter how narrow it is.
    """
    entries = worktree_entries(top)

    # The inventory has to contain the main checkout, or it is not an
    # inventory. Without this, a failed/empty `git worktree list` would make
    # every lease in the repo look orphaned and --apply would evict live
    # owners wholesale (T-18-11).
    if not any(same_path(e["path"], top) for e in entries):
        die(f"`git worktree list` did not report {top} itself — refusing to "
            f"call anything orphaned against an inventory this incomplete",
            EXIT_GIT)

    # The narrowing, applied AFTER the inventory check above and before any
    # verdict: one path, and one phase's lease.
    only_path = None
    if phase is not None:
        only_path = os.path.realpath(phase_layout(top, phase)["worktree"])
        entries = [e for e in entries if e["path"] == only_path]

    orphan_registrations = []
    live = []
    for entry in entries:
        gone = entry["prunable"] or not os.path.isdir(entry["path"])
        if gone:
            orphan_registrations.append({
                "path": entry["path"],
                "branch": entry["branch"],
                "reason": entry["prunable_reason"] or "directory is missing",
            })
        else:
            live.append(entry)

    live_paths = set(e["path"] for e in live)
    leases = lease_status_all(top)
    if phase is not None:
        leases = [e for e in leases if e.get("phase") == phase]
        # A narrowed scan cannot see the other worktrees, so it cannot tell an
        # orphan lease from one whose holder it simply did not look at. It
        # reports none rather than guessing — the same posture as the
        # inventory guard above, one scope down.
        live_paths = set(os.path.realpath(e["path"])
                         for e in worktree_entries(top)
                         if os.path.isdir(e["path"]))

    orphan_leases = []
    stale_but_live = []
    for entry in leases:
        if not entry.get("held"):
            continue
        holder = entry.get("holder")
        holder_real = os.path.realpath(str(holder)) if holder else None
        row = {"phase": entry.get("phase"), "bead": entry.get("bead"),
               "id": entry.get("id"),
               "holder": holder, "acquired_at": entry.get("acquired_at"),
               "heartbeat_at": entry.get("heartbeat_at"),
               "stale": bool(entry.get("stale"))}
        if holder_real in live_paths:
            # The owner exists. Staleness alone is never grounds to release:
            # cairn-lease.py's acquire reclaims a stale lease at the moment
            # somebody actually wants the phase, and racing that reclaim from
            # here would evict an agent that is merely slow.
            if row["stale"]:
                stale_but_live.append(row)
            continue
        # The holder is a worktree path that is not a worktree. By
        # construction — phase 15's identity — that owner does not exist.
        # This is the fact a TTL check cannot see: at four hours of TTL, a
        # lease killed a minute ago is not stale and never looks it.
        orphan_leases.append(row)

    held_here = held_lease_by_holder(leases)

    retained = []
    removable = []
    for entry in live:
        if same_path(entry["path"], top):
            continue
        m = PHASE_BRANCH.match(entry["branch"] or "")
        mb = BEAD_BRANCH.match(entry["branch"] or "")
        if not m and not mb:
            continue
        # The bead unit (phase 47) goes through the same three guards —
        # dirty, unmerged, lease held here — with `bead` where `phase` was.
        phase = int(m.group(1)) if m else None
        bead = mb.group(1) if mb else None
        reasons = []
        manual = None
        if worktree_dirty(entry["path"]):
            reasons.append("uncommitted changes (git cannot recreate these)")
            manual = f"git -C {entry['path']} status --short"
        ahead = commits_ahead(top, entry["branch"])
        if ahead is None:
            reasons.append("could not count commits against HEAD")
            manual = manual or f"git -C {top} log HEAD..{entry['branch']}"
        elif ahead > 0:
            reasons.append(f"{ahead} commit(s) not merged into HEAD")
            manual = manual or f"git -C {top} merge {entry['branch']}"
        lease = held_here.get(entry["path"])
        if lease is not None:
            note = " (stale, but the tree is right here)" \
                if lease.get("stale") else ""
            lease_key = (f"bead:{lease.get('bead')}" if lease.get("bead")
                         else str(lease.get("phase")))
            what = (f"bead {lease.get('bead')}" if lease.get("bead")
                    else f"phase {lease.get('phase')}")
            reasons.append(f"lease for {what} still held by this worktree "
                           f"since {lease.get('acquired_at')}{note}")
            manual = manual or (f"cairn-lease.sh status {lease_key} "
                                f"--project-dir {top}")
        row = {"phase": phase, "bead": bead, "path": entry["path"],
               "branch": entry["branch"]}
        if reasons:
            row["reasons"] = reasons
            row["manual_command"] = manual
            retained.append(row)
        else:
            removable.append(row)

    return {"orphan_registrations": orphan_registrations,
            "orphan_leases": orphan_leases,
            "stale_but_live": stale_but_live,
            "retained": retained,
            "removable": removable}


def cleanup_apply(top, scan):
    """The ONLY writing path in this verb, and it resolves exactly the two
    orphan categories plus the provably-safe removals. `stale_but_live` and
    `retained` are never reached from here — they have no branch in this
    function at all, which is a stronger statement than a promise about
    them."""
    applied = []
    if scan["orphan_registrations"]:
        rc, _, err = run_git(top, ["worktree", "prune"])
        applied.append({
            "action": "worktree_prune",
            "paths": [r["path"] for r in scan["orphan_registrations"]],
            "ok": rc == 0,
            "error": err or None,
        })
    for row in scan["orphan_leases"]:
        after = lease_release(top, row["phase"])
        applied.append({"action": "lease_release", "phase": row["phase"],
                        "holder": row["holder"],
                        "held_after": bool(after.get("held"))})
    for row in scan["removable"]:
        # THE TWO VERDICTS DISAGREED, AND NOT BY ACCIDENT (measured while
        # wiring criterion 8). worktree_dirty() stopped counting
        # `.cairn/journal/` as work git cannot recreate (D-05); git's own
        # `worktree remove` never heard of D-05 and refuses any tree holding
        # untracked files:
        #
        #   fatal: '<path>' contains modified or untracked files, use --force
        #
        # `--force` would answer that by switching git's whole re-check off,
        # and that re-check is the second independent verdict this function
        # deliberately keeps. So instead: delete EXACTLY the path this script
        # declared irrelevant, and let git judge everything else on its own
        # terms. If git still refuses afterwards, something else was in
        # there, the refusal is right, and it is reported.
        dropped = None
        journal = os.path.join(row["path"], *JOURNAL_PREFIX.strip("/")
                               .split("/"))
        if os.path.isdir(journal):
            try:
                shutil.rmtree(journal)
                dropped = journal
            except OSError as e:
                dropped = f"could not remove {journal}: {e}"
        # No --force, and `branch -d` rather than -D: git re-checks "clean"
        # and "merged" on its own terms and refuses if this script read the
        # tree wrong. Two independent verdicts for one irreversible act.
        rc, _, err = run_git(top, ["worktree", "remove", row["path"]])
        deleted = False
        branch_error = None
        if rc == 0:
            rc_b, _, err_b = run_git(top, ["branch", "-d", row["branch"]])
            deleted = rc_b == 0
            branch_error = err_b or None
        applied.append({"action": "worktree_remove", "path": row["path"],
                        "branch": row["branch"], "ok": rc == 0,
                        "error": err or None, "branch_deleted": deleted,
                        "branch_error": branch_error,
                        "journal_dropped": dropped})
    return applied


def print_cleanup(result):
    def say(line):
        print(f"[cairn-parallel] {line}")

    for row in result["orphan_registrations"]:
        say(f"orphan registration: {row['path']} ({row['branch']}) — "
            f"{row['reason']}")
    for row in result["orphan_leases"]:
        say(f"orphan lease: phase {row['phase']} held by {row['holder']}, "
            f"which is not a worktree of this repo — the owner does not "
            f"exist (held since {row['acquired_at']})")
    for row in result["stale_but_live"]:
        say(f"stale lease, LIVE holder: phase {row['phase']} held by "
            f"{row['holder']} — reported only; cairn-lease acquire reclaims "
            f"a stale lease when somebody wants the phase")
    for row in result["retained"]:
        say(f"retained: {row['path']} ({row['branch']}) — "
            f"{'; '.join(row['reasons'])}")
        say(f"  manual: {row['manual_command']}")
    for row in result["removable"]:
        say(f"removable: {row['path']} ({row['branch']}) — clean and wholly "
            f"merged into HEAD")
    for row in result["applied"]:
        say(f"applied: {json.dumps(row)}")
    if not result["apply"]:
        total = (len(result["orphan_registrations"])
                 + len(result["orphan_leases"]) + len(result["removable"]))
        if total:
            say(f"{total} item(s) would be resolved by --apply; nothing was "
                f"written")
        else:
            say("nothing to clean up")


def cmd_cleanup(args, top):
    result = cleanup_scan(top, args.phase)
    result["phase"] = args.phase
    result["apply"] = bool(args.apply)
    result["applied"] = cleanup_apply(top, result) if args.apply else []

    if args.json:
        print(json.dumps(result))
    else:
        print_cleanup(result)
    # Always 0 — see the docstring's asymmetry note. An orphan is a condition
    # this command repairs, not a judgement somebody has to make.
    sys.exit(EXIT_OK)


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
    # default=None, not 3: the flag has to be distinguishable from its own
    # absence, or `--max` could never lose to the setting it overrides.
    batch.add_argument("--max", type=int, default=None,
                       help="ceiling on how many phases are selected "
                            "(default: autonomous.max_parallel from "
                            ".cairn/config.json, itself 3)")
    batch.add_argument("--cycle", type=int, default=None, metavar="K",
                       help="which cycle of an autonomous run this is; "
                            "past autonomous.max_cycles nothing is selected "
                            "(omit it and the cycle ceiling never applies)")
    batch.set_defaults(func=cmd_batch)

    prepare = sub.add_parser("prepare", help="create phase N's named "
                                             "worktree and take its lease "
                                             "pointing at it")
    prepare.add_argument("phase", type=int, help="phase number")
    prepare.set_defaults(func=cmd_prepare)

    prepare_bead = sub.add_parser("prepare-bead",
                                  help="create bead <id>'s named worktree "
                                       "(<root>-bead-<short>, branch "
                                       "bead/<short>-<slug>) from --base and "
                                       "take its lease pointing at it")
    prepare_bead.add_argument("bead", help="bead id, e.g. CairnGo-o1vm")
    prepare_bead.add_argument("--base", metavar="REF",
                              help="branch or commit to branch from "
                                   "(default: HEAD — the PR branch)")
    prepare_bead.set_defaults(func=cmd_prepare_bead)
    reconcile = sub.add_parser("reconcile",
                               help="read-only report over the phase/* "
                                    "branches: what each phase produced, the "
                                    "merge conflicts, and the convergent "
                                    "edits git resolves in silence")
    reconcile.add_argument("--phases", metavar="LIST",
                           help="comma-separated phase numbers to restrict "
                                "to (default: every phase/* branch)")
    reconcile.add_argument("--beads", action="store_true",
                           help="the bead unit: every bead/* branch against "
                                "--base (default HEAD), one pair each")
    reconcile.add_argument("--base", metavar="REF",
                           help="with --beads: the branch the merger folds "
                                "the beads into (default HEAD)")
    reconcile.set_defaults(func=cmd_reconcile)

    cleanup = sub.add_parser("cleanup",
                             help="what a dead run left behind: worktree "
                                  "registrations whose directory is gone and "
                                  "leases whose holder is not a worktree of "
                                  "this repo")
    cleanup.add_argument("--apply", action="store_true",
                         help="write: prune orphaned registrations, release "
                              "orphaned leases, and remove worktrees that "
                              "are clean AND wholly merged (default: report "
                              "only)")
    cleanup.add_argument("--phase", type=int, metavar="N",
                         help="narrow the sweep to phase N's CANONICAL "
                              "worktree (<root>-phase-N, exactly what "
                              "prepare builds) and its own lease")
    cleanup.set_defaults(func=cmd_cleanup)

    for p in (batch, prepare, prepare_bead, reconcile, cleanup):
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
