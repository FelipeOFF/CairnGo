#!/usr/bin/env python3
"""cairn-doctor — consistency doctor for a repo wired with GSD + beads.

Cross-checks the two sources of truth (.planning/ and the bd tracker) and
reports drift. Read-only except for --fix-labels, which delegates to
cairn-relabel.py pair, --close-completed, which bulk-closes via
'bd close', and --link-refs, which backfills bd's --external-ref field
via 'bd update'.

Usage:
    cairn-doctor.py [--project-dir <dir>] [--json] [--fix-labels]
                    [--close-completed] [--link-refs]
                    [--apply-reconciliation N]

Checks (each reported as {id, status: ok|not-applicable|warn|fail, detail,
items[]}, plus `scope` when and only when the status is not-applicable, plus
`state` when and only when the check is `gsd-unmigrated` — it carries the
state letter of cairn-migrate.py's classifier, which that check reuses rather
than re-deriving; see check_gsd_unmigrated for why the reuse is deliberate):

THE FOURTH STATUS, `not-applicable` (phase 23, VOID-01). It says the check had
nothing to check — as opposed to `ok`, which says it compared something and
found it consistent. The word is not new: four detail strings already wrote
"not applicable" in prose while wearing `ok`, and this only moves it into the
field tools read.

It carries a `scope`, because two very different absences were wearing one
word. MEASURED (2026-08-05), and the reason the split exists: the suite's own
healthy fixture is a USER's repo, with no cairn manifests, so three checks are
absent there by construction. Making every absence mean "incomplete" would
have handed every user repo a permanent false red — the same defect as the
false green, mirrored.

  out-of-scope  the input will never exist for this class of repo and nothing
                is wrong (cairn's own manifests in a repo that is not cairn).
                Permanent, ordinary, and it leaves the report complete.
  no-input      the input SHOULD exist given what the repo already has, so the
                absence is a gap someone can close (a STATE.md present but
                carrying no active_phase; a ROADMAP.md present but listing no
                phase). This one, and only this one, clears the top-level `ok`.

ASSIGNMENT IS A WRITTEN DECISION, NOT A MEASUREMENT: each branch's family is
chosen by the rule above and recorded at the branch. What WAS measured is the
symbol: `⊘` (U+2298) reports east_asian_width "N", one column even under a CJK
locale, checked with unicodedata and asserted by the suite — never eyeballed.
`◌` (U+25CC) was rejected on purpose: it is already a step symbol on the
status board, and reusing it would collide two vocabularies.

COUNTING. The footer counts one bucket per word of the vocabulary, and the
buckets are SYMBOL's own keys, so a status with no symbol has nowhere to be
counted and die()s instead of landing in the success bucket. Nothing is
derived by subtraction — that shape is exactly how a fourth status would have
arrived pre-approved. The four counters sum to the number of registered
checks, always.

The top-level keys that carry the verdict: `counts` (the four numbers),
`failed` (the exact mirror of the exit code) and `ok` (which also answers "did
every check inside the doctor's remit receive its input"). "Something failed"
and "something never ran" are different questions and get different keys.
    0. bd-version       the bd binary meets the minimum version cairn
                        relies on (--claim, --all, label add/remove,
                        nested --metadata). Older -> FAIL, unparsable
                        version output -> WARN. Runs first — twenty-two
                        checks in total. (This line read `eighteen` while
                        nineteen were registered, from phase 24 until
                        phase 30 measured it: a hand-maintained count in
                        prose is the fifth one this repository has caught
                        going stale. tests/cairn-doctor.bats asserts the
                        real number in two places, and both are edited
                        together or the canary there says why.)
    1. req-issue        every requirement id in ROADMAP.md's
                        '**Requirements**:' lists has >=1 issue whose
                        metadata.gsd.req matches, scoped to the phase's
                        phase-<N> label and to the active milestone
                        (issues from other milestones are ignored;
                        m-*-less legacy issues count, same semantics as
                        cairn-gate). Missing -> FAIL.
                        WHERE IT STOPS, measured 2026-08-04: it can only
                        count the ids it manages to READ off a phase's
                        '**Requirements**:' line, so in this repo it
                        reported `ok :: 29 requirement(s) mapped to
                        issues` against 35 active requirements —
                        ROADMAP.md:400 reads '**Requirements**: AUTO-01 …
                        AUTO-08' and an ellipsis is prose, not a
                        separator, so six ids never entered the count.
                        Not a mapping bug: the limit of the source it
                        reads, and exactly the limit check 17
                        (req-ledger) covers.
                        NO '**Requirements**:' LINE ANYWHERE (phase 23 /
                        VOID-02) -> NOT-APPLICABLE / no-input, never `ok`:
                        the mapping was never verified in this repo, and
                        writing the line is a concrete action.
    2. frontmatter-ids  every id in a non-superseded PLAN.md's 'beads:'
                        frontmatter exists in bd and carries the plan's
                        phase-<N> label. Dangling id or wrong label -> FAIL.
                        Nothing to verify (phase 23) -> NOT-APPLICABLE /
                        no-input, in BOTH its shapes: no non-superseded
                        PLAN.md at all, and plans on disk carrying no
                        'beads:' id — an unstamped plan is the very gap
                        cairn exists to prevent, so it is the loudest
                        no-input there is, not a vacuous pass.
    3. maps-fresh       cairn-map.py --check per phase dir that has issues
                        or a map (its exit codes reused: 3 stale -> WARN;
                        a missing map where issues exist -> WARN).
                        No phase dir carrying either (phase 23) ->
                        NOT-APPLICABLE / no-input. NOTE, measured: this
                        check's input is .planning/phases/ ON DISK — it
                        never reads ROADMAP.md, so an empty roadmap leaves
                        it running for real.
    4. superseded-released  PLAN.md with 'status: superseded' whose beads:
                        ids are still open/in_progress -> WARN (release or
                        move them). No PLAN.md at all (phase 23) ->
                        NOT-APPLICABLE / no-input, the same axis as check 2
                        and therefore the same verdict. Plans present with
                        none superseded stays `ok`: that is a real sweep of
                        every plan, not an absent input.
    5. phase-complete-open  non-closed issues whose phase-<N> labels ALL
                        point at phases ROADMAP.md marks COMPLETE -> WARN
                        (FAIL only when a --close-completed the operator
                        asked for was refused, see below), listing the
                        ids. ALL, not any: a
                        cross-phase issue stays live while any of its
                        phases is still open, the same predicate as
                        cairn-status's in_done_phase — otherwise the
                        doctor would flag (and --close-completed would
                        kill) the very issue the status board recommends
                        as the next action. 'Complete' is read with
                        the same lenient semantics as cairn-gate:
                        '- [x] ... Phase N' checkboxes plus milestone
                        progress-table rows ending '| Complete |'. When
                        the ROADMAP checkbox and the on-disk artifacts
                        (every non-superseded PLAN has its SUMMARY)
                        disagree about a flagged phase, a note item spells
                        out the divergence and names the concrete gap (no
                        phase directory / no PLAN in it / a PLAN lacking
                        its SUMMARY). --close-completed bulk-closes
                        the flagged issues via 'bd close <id> --reason
                        "doctor: phase N complete in ROADMAP"' BEFORE the
                        checks run (idempotent; the report shows post-fix
                        state). The divergence note is computed and
                        printed BEFORE those closes — after them the
                        issues leave check 5's scope, so the operator
                        would never see the warning in the one run that
                        needed it — and the note is carried into the
                        check's items too.
                        bd refuses to close an epic with an open child and
                        an issue whose blocker is still open, so the bulk
                        close runs as a FIXPOINT: repeated passes over the
                        target set, each closing whatever bd now accepts,
                        stopping when a whole pass closes nothing. That
                        drains any topology (epic<-epic<-epic chains,
                        blocks edges between phases) without modelling the
                        graph and without --force, which would bulldoze a
                        genuinely open child that is NOT in a complete
                        phase. Whatever survives the fixpoint is reported
                        with bd's own refusal reason and turns this check
                        FAIL (exit 7) — a close the operator asked for and
                        did not get is never silent.
    6. orphans          TWO INDEPENDENT AXES. Axis 1: issues labeled
                        phase-<N> where N is not a ROADMAP phase -> WARN;
                        needs the roadmap. Axis 2: non-closed issues with NO
                        phase-* label at all (excluding migrated-todo/
                        backlog/quick labels) -> WARN; never reads the
                        roadmap. With an EMPTY roadmap (phase 23 / VOID-02
                        + the first half of VOID-03) axis 1 cannot run, and
                        the verdict then depends on axis 2: a finding still
                        WARNs, and only a run with nothing from either axis
                        is NOT-APPLICABLE / no-input. Refusing the whole
                        check would swallow axis 2's findings — trading a
                        false green for a new silence. Axis 1 EXEMPTS an
                        issue that is closed AND carries at least one m-*
                        label AND has every one of them archived under
                        .planning/milestones/ (VOID-03's second half), so
                        the historical count falls to zero at the end of a
                        cycle instead of growing forever. All three
                        conditions, and ALL milestones not ANY: an open
                        issue, an issue with no m-* label, and an issue
                        carried into the active milestone all keep warning.
                        The detail always says how many were exempted — a
                        silent exemption is indistinguishable from a
                        switched-off axis.
    7. label-pairs      issues with a phase-* label but no m-* label ->
                        WARN. --fix-labels repairs them via
                        'cairn-relabel.py pair --milestone <active>' BEFORE
                        the checks run (the report shows post-fix state);
                        refused (exit 2) when the active milestone is
                        unresolvable.
    7c. jira-links      (LINK-05, phase 44) the cycle's Jira links, read off
                    the beads: ⊘ out-of-scope until .cairn/sync.json has
                    an enabled `jira` backend. With one: an open milestone
                    or open phase whose carrier has no external_ref ->
                    warn; two beads sharing one jira-<KEY> -> fail (one
                    card, one bead); a linked key the tracker does not
                    know -> fail, asked through the CAIRN_JIRA_FETCH seam
                    (a command printing the card JSON, exit non-zero when
                    absent) or, by default, REST with the backend's
                    email/token env vars — and `skipped`, said out loud,
                    when neither can ask; a story whose parent is not the
                    cached epic -> warn (epic drift). Writes nothing.

7d. planning-writes (RECORD-03, phase 46) a markdown file NEW or MODIFIED
                    under .planning/phases/ in a repo that has .beads/ —
                    a document written where the bead is the source. Warn,
                    naming the cairn-record kind that replaces it; ⊘
                    out-of-scope with no .planning/phases/ at all.

7b. milestone-carrier  (CARRY-02, phase 43) every OPEN cycle — an m-*
                    label with at least one non-closed issue — has exactly
                    one milestone carrier (label `milestone` + m-*, no
                    phase-*). None -> warn in 4.0, with the bd create that
                    resolves it (a failure from 4.1: the carrier is the
                    contract for cycles opened from 4.0 on, and a cycle
                    opened under 3.x deserves one release to catch up).
                    Two or more -> fail, always: two beads claiming to be
                    the same cycle is an inconsistency, not a gap. Closed
                    cycles are history and are never asked.

8. claims-stale     in_progress issues with an assignee whose phase-<N>
                        label differs from STATE.md's active_phase -> WARN
                        (possible stale claim). When active_phase is
                        unresolvable the check CANNOT RUN, and that is
                        reported as WARN naming the missing key, the five
                        cairn surfaces that read it, and CairnGo-rq0 where
                        the current_phase-vs-active_phase decision lives —
                        never `ok`. Measured 2026-08-04 before the change:
                        `claims-stale :: ok :: skipped — no active_phase in
                        STATE.md`, a check that had never run once in this
                        project's life while wearing the success marker
                        (AUTO-08). Still never FAIL: a check with no input
                        is friction, not a state inconsistency, and exit 7
                        spent on friction stops meaning anything.
    9. bd-doctor        run 'bd doctor'; first line captured as the
                        summary, pass/fail as bd reports it (exit 0 -> ok,
                        else FAIL).
    10. gsd-capability  is the VENDORED GSD runtime intact, and is any
                        external GSD lineage still installed beside it?
                        INVERTED in phase 37: it used to ask whether the
                        cairn capability had registered against an installed
                        gsd-core, and prescribed INSTALLING it. cairn now
                        vendors its runtime, so an installed gsd-core (or
                        gsd 4.x) is a FAIL prescribing `claude plugin
                        uninstall` — two lineages answering /gsd:* and
                        /cairn:* at once is the defect class the whole v1.5
                        cycle chased. Order of decision is load-bearing and
                        asserted: a broken vendored runtime FAILS first (a
                        defect of the install, not the environment), an
                        external lineage FAILS second, and leftover .gsd/
                        state from a pre-v1.6 /cairn:init WARNs last —
                        because a machine that migrated has both, and
                        evaluating residue first would report the actionable
                        finding as a warning. Residue never FAILs, for the
                        reason checks 8 and 14 already record (friction is
                        not a state inconsistency). See
                        check_gsd_capability()'s own docstring.
    11. phase-corroboration  reads Plan 13-01's phase_model() verdict for
                        every phase (shells to 'cairn-status.py --json',
                        the same subprocess pattern check 3 already uses
                        for cairn-map.py --check) and itemizes every
                        phase whose corroboration != "ok": a "conflict"
                        verdict lists each entry in that phase's
                        conflicts[] as '<n>: <detail> (<severity>) —
                        <recommendation> — <source> last moved <ts>, ...',
                        the recommendation being the FIRST, most-likely
                        fix (D-01) and differing by the conflict's source
                        pair (disk/bd -> close the bd issue or run
                        /cairn:work; roadmap/disk -> confirm before
                        leaving the checkbox ticked; state_md/disk -> the
                        pointer is merely stale, no action needed); the
                        trailing "last moved" clause (Phase 16, JOUR-02)
                        names when EACH of that conflict's cited sources
                        last moved, pulled from 'cairn-journal.py
                        last-moved --phase N --json' (called at most ONCE
                        per phase, cached, never once per conflict item),
                        "never observed" for a source the journal has
                        never seen — a broken/missing journal degrades
                        that one clause to nothing, never this check's
                        own status. An "unknown" verdict (bd unreadable
                        for that phase) gets one item saying so, no
                        last-moved clause. A "blocks"-severity conflict ->
                        FAIL (reuses EXIT_FAILED, no new exit code);
                        "informs"-only or "unknown" -> WARN, never fails
                        the run (D-10 applied to doctor's own exit code).
                        A subprocess/JSON failure degrades to WARN rather
                        than crashing the whole doctor run over this one
                        check.
    12. phase-artifacts CARD-02/D-04: names which artifact is missing for a
                        phase whose board row would otherwise be a bare
                        dash. Reuses main()'s already-computed
                        disk_incomplete_reasons() (no duplicate frontmatter
                        parser) plus 'cairn-status.py --json' (same
                        subprocess pattern as check 11) for disk_state /
                        verify_status. Two WARN-only shapes: a phase whose
                        disk_state has already reached "verified" (an
                        NN-VERIFICATION.md exists) while one of its
                        PLAN.md files still lacks its own SUMMARY.md,
                        named by filename; and a "verified" phase whose
                        NN-VERIFICATION.md carries no readable 'status:'
                        field. The missing-SUMMARY half is gated on
                        disk_state == "verified" ON PURPOSE — an ungated
                        version fired on every plans-without-summary gap,
                        which is the state of any phase mid-flight between
                        waves, and a plan-checker caught that as noise; a
                        phase someone ran /cairn:verify on despite an
                        unsummarized plan is a genuine anomaly, ordinary
                        in-progress work is not. Known accepted gap: a
                        phase stuck at "executed" that never reaches
                        "verified" — its SUMMARY-less plan never gets
                        flagged here either, the false negative the
                        narrowed gate trades for removing the mid-flight
                        false positive. NEVER fails the run (see
                        check_phase_artifacts()'s own docstring for why);
                        a subprocess/JSON failure against cairn-status.py
                        degrades to a single WARN item rather than falling
                        back to the ungated dump.
    13. external-ref    CORR-08/D-11 backfill: every CLOSED issue lacking
                        bd's own 'external_ref' field, resolved to its
                        phase and that phase's plan(s) 'files_modified:',
                        cross-referenced against 'git log' in a +/-2 day
                        window around the issue's closed_at for a commit
                        subject carrying a single, unambiguous '(#N)'
                        token (zero or multiple distinct numbers found ->
                        never a candidate, never guessed). Read-only by
                        default: reports each unambiguous candidate as
                        '<id> -> gh-N', writes nothing. --link-refs backs
                        it: runs 'bd update <id> --external-ref gh-N' for
                        each candidate, itemizes what it linked, and is
                        idempotent (an issue already carrying an
                        external_ref is excluded from consideration up
                        front). A shallow clone's git match can be
                        silently WRONG at the boundary commit, not merely
                        incomplete (D-08, reproduced in STACK.md) — a
                        single 'git rev-parse --is-shallow-repository'
                        check skips the whole check for the run rather
                        than trusting it. WARN only when an unambiguous,
                        actionable candidate is waiting (never merely
                        because history predates the convention — that is
                        the expected, unremarkable case per STACK.md).
    14. lease-stale     cairn-lease.py status --all --json (Plan 15-01)
                        itemized for every phase whose lease is currently
                        held AND stale (heartbeat older than the 4h TTL
                        cairn-lease.py enforces): phase, holder, actor,
                        acquired_at, heartbeat_at, and the reclaim path
                        ("reclaimable — the next /cairn:work N takes it
                        automatically, or run cairn-lease.sh release N to
                        clear it now") -> WARN, one item per stale lease;
                        no stale lease -> ok. Never FAIL — mirrors check 8
                        (claims-stale)'s own discipline one level up
                        (D-04/LEASE-05): a stale lease is reclaimable, not
                        itself a doctor failure. A non-zero cairn-lease.py
                        exit or unparsable JSON degrades to WARN with an
                        explanatory detail rather than crashing the whole
                        doctor run over this one check (same degrade
                        shape as check_phase_corroboration()).
    15. release-versions  cairn-release.py check --json (Plan 19-01,
                        REL-02) run through the CAIRN_RELEASE env seam:
                        the plugin version's carriers must agree —
                        cairn/.claude-plugin/plugin.json's `version`,
                        .claude-plugin/marketplace.json's NESTED
                        `metadata.version`, the first released CHANGELOG
                        heading, and the v<version> git tag — while
                        cairn/capability/capability.json keeps its own
                        axis and need only be valid semver (D-02). A
                        finding -> FAIL (exit 7): a version inconsistency
                        blocks a release, and the marketplace carrier went
                        unnoticed across three of them precisely because
                        nothing failed. APPLIES ONLY when
                        cairn/.claude-plugin/plugin.json exists under the
                        project root — the doctor runs in USERS' repos,
                        which carry none of these manifests, and a naive
                        version of this check would report `missing` and
                        drive every one of them to exit 7. Elsewhere it
                        reports not-applicable / out-of-scope: the carriers
                        are cairn's own and will never exist there, so
                        nothing is missing and the report stays complete.
                        Exit stays 0, the same "0 = ok, or not applicable"
                        semantics the exit-code table below documents. A
                        non-zero-and-not-6 cairn-release.py exit or
                        unparsable JSON degrades to WARN rather than
                        crashing the whole doctor run over this one check
                        (same degrade shape as check_lease_stale()).
    16. test-parallel   (AUTO-04) whether this machine can run the bats
                        suite in parallel, ROUTED from 'cairn-test.py
                        --check-env' through the CAIRN_TEST env seam rather
                        than recomputed here — that script owns the
                        measurement of what `bats -j` actually requires (the
                        parallel binary at bats-exec-suite:323 AND flock-or-
                        shlock at lib/bats-core/semaphore.bash:26-33; miss
                        either one and bats runs ZERO tests and exits 1
                        rather than degrading to serial). A missing
                        prerequisite -> WARN, itemizing each absence with
                        its install command plus the measured cost of
                        running serial (64s against 33s on
                        tests/cairn-map.bats at -j 6). No bats at all ->
                        NOT-APPLICABLE / no-input, a different sentence: the
                        suite cannot run here at all, so nothing about
                        parallelism was concluded. `no-input` because the
                        guard below already proved we are inside cairn's own
                        tree, where the suite exists — a missing tool is a
                        gap someone can close, so it makes the report read
                        INCOMPLETE.
                        NEVER fails the run: running the suite slowly is
                        friction, not a state inconsistency, and spending
                        exit 7 on friction is how exit 7 stops meaning
                        anything. APPLIES ONLY when
                        cairn/.claude-plugin/plugin.json exists under the
                        project root — same guard and same reason as check
                        15, and same verdict: not-applicable / out-of-scope,
                        since a wired repo has no cairn bats suite to
                        run. A non-zero exit or unparsable JSON from
                        cairn-test.py degrades to WARN.
    17. req-ledger      (AUTO-07) the requirement ledger's own chain, the
                        one nothing was validating: every ACTIVE
                        requirement has a row in the coverage table, the
                        table's row count is the number the coverage
                        footer claims, each phase's '**Requirements**:'
                        line actually yields the ids the ledger assigns
                        it, and a plan whose SUMMARY is on disk has its
                        ROADMAP checkbox ticked. Requirements under
                        `## Deferred` / `## Out of Scope` are outside the
                        table BY RULE and never counted as gaps — the
                        detail says how many were excluded that way,
                        because an unexplained absence is the same defect
                        pointing the other way. Read by shelling out to
                        cairn-bookkeep.py `reconcile --json` through the
                        CAIRN_BOOKKEEP seam (same pattern as checks 3, 15,
                        16); the ledger is NEVER re-parsed here, since a
                        second reader is a fifth number for one quantity.
                        WHERE IT STOPS vs check 1: check 1 goes
                        requirement -> bd issue and can only count the ids
                        it manages to read; this one goes active
                        requirement -> coverage row -> footer claim, and
                        covers the legibility of the very line check 1
                        reads. Measured 2026-08-04 in this repo: 35 active
                        requirements, 33 coverage rows (AUTO-05 and
                        AUTO-06 have none), a footer still claiming '29
                        requisitos, 29 mapeados.', and check 1 reporting
                        29 from an unrelated cause — three numbers for one
                        quantity, two wrong, meeting at 29 by accident,
                        both wearing a green check. A broken link -> FAIL
                        (exit 7), routed by name to `cairn-bookkeep.sh
                        reconcile --apply`. A disagreement reconcile names
                        OUTSIDE these links (STATE.md's counters and its
                        free-text narrative) is surfaced as WARN and never
                        spends exit 7 on a check called req-ledger. No
                        coverage view at all (no '## Cobertura' in
                        ROADMAP.md, no '## Traceability' in
                        REQUIREMENTS.md), and no REQUIREMENTS.md at all ->
                        NOT-APPLICABLE / out-of-scope, the same verdict
                        checks 15/16 use, since the doctor runs in USERS'
                        repos and keeping no coverage view is a method
                        choice, not a gap. The ledger being UNREADABLE
                        (script gone, exit outside the (0, 3) allowlist,
                        unparsable JSON) -> FAIL, never WARN: a warning
                        does not change the exit code, so degrading here
                        would leave the doctor exiting 0 over a ledger
                        nobody read. Writes nothing.
    18. response-language  (LANG-02) the two homes of the one answer still
                        agree. `/cairn:init` records the installation's
                        choice in `.cairn/config.json:agents.
                        response_language` — it must, since at the moment
                        it asks, `.planning/` does not exist and cairn is
                        forbidden from creating it — and `cairn-config.py
                        set` propagates it into `.planning/config.json:
                        response_language`, which is the key GSD's own ~30
                        workflows read when they spawn subagents. On a
                        greenfield install that propagation depends on one
                        re-run after the `/gsd:new-project` hand-off, and a
                        step in prose is exactly the thing that gets
                        skipped. WARN, never FAIL, and the reason is
                        written rather than assumed: a disagreement breaks
                        nothing mechanically, it makes half a run's
                        subagents answer in one language and half in
                        another — which is what nobody noticed in v1.4.
                        Spending exit 7 on it would train people to ignore
                        exit 7. It reads the two files RAW, the one place
                        this repository's usual "shell out to the script
                        that owns the rule" would be wrong: `cairn-config.
                        py get` returns the RESOLVED value, so asking it
                        would report a single agreeing answer in exactly
                        the situation this check exists to catch. Writes
                        nothing.
    19. phase-landed    (PR-04, Phase 30) a phase the roadmap calls
                        complete whose commits are not on the control
                        branch. The whole question — which branch, which
                        commits, did they arrive — is read ONCE from
                        cairn-land.py through the CAIRN_LAND seam, the
                        same shape checks 3 and 17 use for cairn-map.py
                        and cairn-bookkeep.py; no git is read here.
                        MEASURED 2026-08-06, and the reason it exists:
                        nine roadmap-complete phases of this repository
                        are not on origin/main (145 commits ahead) and
                        the doctor said nothing about any of them.
                        Complete phase of the OPEN cycle not yet on the
                        branch -> WARN: unpushed work is the normal state
                        of anybody mid-cycle, it is friction and not
                        inconsistency, and exit 7 spent on friction stops
                        meaning anything (same distinction as checks 8
                        and 14). Complete phase of an ARCHIVED milestone
                        that never arrived -> FAIL: a cycle was CLOSED
                        over work the control branch does not have, which
                        is a claim the repository cannot support. A phase
                        the local history cannot place -> named in items
                        with the word `unknown` and its reason, raising
                        NOTHING: measured, phases 7-12 here predate the
                        conventional-commit scope convention and are
                        attributable by neither source, and charging that
                        would hand every long-lived repo a permanent
                        finding about history nobody will rewrite. The
                        universe of "complete" is roadmap_completed_
                        phases() UNION the phase dirs under .planning/
                        milestones/<key>-phases/ — the current ROADMAP.md
                        lists only the open cycle, so reading it alone
                        would make the FAIL rung unreachable by
                        construction. No control branch, or nothing
                        complete anywhere -> NOT-APPLICABLE / out-of-
                        scope. A cairn-land.py that could not run or
                        answered unparsably -> WARN, never FAIL (same
                        degrade shape as check 11). Writes nothing; every
                        finding routes to /cairn:ship.
    20. plan-counters   (CairnGo-6bx, Phase 25 criterion 6) STATE.md
                        claiming more plans completed than it has.
                        MEASURED 2026-08-06, right after the close of
                        phase 22: `total_plans: 39` against
                        `completed_plans: 47`, because 47 = 39 plan
                        summaries + 8 PHASE summaries, and the glob that
                        produced it matched both while its `*-PLAN.md`
                        pair matched only plans. This check COMPARES and
                        never recomputes: writer and verifier derived that
                        number with the same rule and therefore agreed
                        while printing both contradictory values in one
                        JSON object, so a recount with the writer's rule
                        would reproduce the defect inside the check meant
                        to catch it. `completed > total` is impossible by
                        arithmetic, not by convention, and needs to know
                        nothing about either glob. Both numbers present
                        and possible -> OK; `completed > total` -> FAIL;
                        no .planning/, no STATE.md, or a `progress:` block
                        without both keys -> NOT-APPLICABLE / no-input,
                        because GSD owns that block and a repo that never
                        grew one is not inconsistent. Writes nothing; the
                        finding routes to `cairn-bookkeep.sh reconcile`,
                        which owns the recount. NO .planning/ AT ALL is
                        NOT-APPLICABLE / out-of-scope, never no-input —
                        a defensive branch the CLI never reaches, since
                        main() registers zero checks in that repo.
    22. issues-recoverable  whether the issue store survives this
                        machine. MEASURED 2026-08-07 on this repository:
                        `.beads/embeddeddolt` 27 MB in .gitignore,
                        `.beads/issues.jsonl` ABSENT, `.beads/backup/`
                        13 MB and also ignored, and 0 refs/dolt among the
                        42 refs on the remote — a clean clone recovered
                        NONE of the 176 issues. CLAUDE.md:25 had been
                        stating the opposite in writing for weeks; bd
                        ships `export.auto` disabled and commented, so
                        the file that sentence promises is never born
                        until somebody enables it. Twenty-two checks
                        cross-examined the sources against each other and
                        not one asked whether any of them survives the
                        laptop: corroboration between sources says
                        nothing about the durability of a source. It
                        reads what GIT TRACKS and compares the record
                        count against the live store, never the config —
                        `export.auto: true` proves an intent, not a file.
                        Tracked export covering the store -> OK; behind
                        the store -> WARN (a stale export still recovers
                        most of it, and spending exit 7 on lag is how
                        exit 7 stops meaning anything); NO tracked export
                        -> FAIL, because absence is not a degraded
                        recovery, it is none. Empty store ->
                        NOT-APPLICABLE / no-input; no `.beads/` ->
                        out-of-scope. Green here means the ISSUE RECORDS
                        have a way back, never the database: the JSONL
                        carries no Dolt branch, no commit history and no
                        working set. Writes nothing.

    21. state-dialect   (CairnGo-ctr, AUTO-10, Phase 25 criterion 5)
                        STATE.md's two phase keys naming two different
                        phases. MEASURED 2026-08-05: cairn-bookkeep wrote
                        `current_phase` and `grep -rn current_phase
                        cairn/` returned ZERO readers, while five surfaces
                        read `active_phase`. The owner's decision
                        (2026-08-06) is to write BOTH, additively, and
                        THIS CHECK IS THE STATED COUNTERPART of that
                        duplication: two keys that must agree and that
                        nobody compares is the defect this cycle measured
                        four times, so writing the pair without comparing
                        it would create the fifth case while fixing the
                        fourth. It COMPARES, never derives — a phase
                        recomputed from the roadmap would agree with
                        whichever key the same rule wrote. Both present
                        and equal -> OK; both present and different ->
                        FAIL; FEWER THAN TWO readable -> NOT-APPLICABLE /
                        out-of-scope, never no-input: one key is no
                        disagreement (it is the state AUTO-10 is named
                        after), check 8 already reports the missing
                        active_phase as no-input, and a second no-input
                        would drop `.ok` in every GSD repo that never ran
                        cairn-bookkeep — a permanent false red. Writes
                        nothing; the finding routes to `cairn-bookkeep.sh
                        close <N> --apply`, which writes both keys.

--apply-reconciliation N  (ESC-03, Phase 17 Plan 3) the human-invoked,
                    separate command that APPLIES a verified semantic-
                    escalation reconciliation proposal for phase N. Not a
                    check at all — a fixer, the same category as
                    --close-completed/--fix-labels/--link-refs, but the only
                    one of the four that always exits on its own rather
                    than falling through to the ordinary report, since its
                    own exit-code contract (below) does not track check
                    pass/fail. Reads .cairn/conflicts.json (written by
                    /cairn:reconcile's own deterministic step, Plan 17-02)
                    and refuses the WHOLE apply, fail-closed, on any of:
                    no proposal for phase N (or its own 'phase' field
                    doesn't match N); phase N's corroboration verdict is no
                    longer "conflict" at apply-time (a real 're-collect',
                    never the proposal's own stale self-claim) — not a
                    failure, nothing to apply; the freshly re-collected
                    evidence_hash no longer matches the proposal's own
                    stored one (the tree moved between proposal and apply,
                    D-04's cache key re-validated); any citation fails a
                    real re-verification run (D-03); any
                    recommended_action.type falls outside the closed
                    {bd_close, bd_reopen, manual_review} vocabulary; or any
                    bd_close/bd_reopen claim's recommended_action.issue
                    names a bd id that carries no phase-N label (the
                    issue-provenance check — correct citations elsewhere in
                    the same proposal never excuse a claim that targets an
                    unrelated issue). Only once every one of those passes
                    does anything print: EVERY claim is enumerated
                    (statement, recommended_action, what will happen —
                    manual_review claims listed as skipped) BEFORE the
                    first bd subprocess call ever runs, then bd_close/
                    bd_reopen claims are applied one at a time; manual_review
                    claims never touch bd. A close/reopen bd itself refuses
                    is reported by id and reason and fails the run — never
                    silent, the same "asked for it and did not get it"
                    discipline check_phase_complete_open's close_failures
                    already applies one level up.

Active milestone is resolved leniently like cairn-gate: STATE.md
frontmatter 'milestone:' first, else the ROADMAP.md milestone marked in
progress, else None (single-milestone / legacy repo — milestone scoping is
then a no-op).

Exit codes:
    0  all checks ok, or ok + warnings (warnings are printed but never
       change the exit code), or doctor NOT APPLICABLE: .planning/ or
       .beads/ absent — the doctor is for wired repos. When exactly one
       side exists the note suggests /cairn:migrate. ALSO:
       --apply-reconciliation's own "phase N is no longer in conflict"
       refusal — nothing left to apply is not a failure. ALSO: any number
       of checks reporting `not-applicable`, of EITHER family, including a
       run whose footer reads INCOMPLETE. That is deliberate, not an
       oversight: an absent input is friction, not a state inconsistency,
       and spending exit 7 on friction is how exit 7 stops meaning
       anything. The verdict of an incomplete report moved where it is
       READ (the footer word, the symbol, the top-level `ok` key), never
       where it decides to block.
    2  usage error, or --fix-labels refused (milestone unresolvable), or
       --apply-reconciliation found no proposal for phase N (missing
       .cairn/conflicts.json, or its own 'phase' field doesn't match N).
    5  bd unavailable (not on PATH, or bd list failed).
    7  at least one check FAILED — including --close-completed leaving a
       target unclosed (bd refused it and the fixpoint could not drain it),
       which fails check 5 rather than exiting silently 0, and including a
       "blocks"-severity phase-corroboration conflict (check 11). ALSO:
       --apply-reconciliation refusing a stale proposal, a bad citation, an
       unrecognized recommended_action.type, an issue-provenance mismatch,
       or bd itself refusing a close/reopen it was asked to apply.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cairn_source  # noqa: E402

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_BD = 5
EXIT_FAILED = 7

# Phase 23 / VOID-01. The fourth status: a check that had nothing to check.
# The word is not invented here — four `detail` strings already SAID "not
# applicable" in prose while wearing `ok`; this only moves it into the field
# tools read.
NOT_APPLICABLE = "not-applicable"

# ...and the two families of it, which are NOT the same sentence (T-04).
# The rule that assigns them:
#   out-of-scope  the input will never exist for this CLASS of repo and
#                 nothing is wrong — cairn's own manifests in a repo that is
#                 not cairn. Permanent, ordinary, and it does NOT make the
#                 report incomplete.
#   no-input      the input SHOULD exist given what the repo already has, so
#                 its absence is a gap someone can close — a STATE.md with no
#                 active_phase, a ROADMAP.md with no phase.
# Only `no-input` clears summary["ok"]. Without the split, every user repo
# would trade a permanent false green for a permanent false red, which is the
# same defect mirrored rather than progress.
NA_OUT_OF_SCOPE = "out-of-scope"
NA_NO_INPUT = "no-input"

# The single source of the status vocabulary: main() derives its counting
# buckets from these keys, so a status with no symbol has nowhere to be
# counted and cannot slip in unnoticed. Every glyph measures east_asian_width
# "N" (single column even under a CJK locale) — measured with unicodedata,
# never eyeballed, and asserted by the suite. ⊘ (U+2298) is the new one; ◌
# (U+25CC) was rejected on purpose, it is already a step symbol on the status
# board and reusing it would collide two vocabularies.
SYMBOL = {"ok": "✓", "not-applicable": "⊘", "warn": "⚠", "fail": "✗"}

SCRIPTS_DIR = Path(__file__).resolve().parent

# Test/override seam for check_phase_corroboration()'s journal_last_moved()
# call (Phase 16, D-01/D-02) — the SAME env var name cairn-lease.py and
# cairn-status.py already use for their own calls into this identical
# script (CONVENTIONS.md's "Environment variable seams" note: CAIRN_*
# prefix, upper case). Default: the sibling cairn-journal.py next to this
# script.
CAIRN_JOURNAL = os.environ.get(
    "CAIRN_JOURNAL", str(SCRIPTS_DIR / "cairn-journal.py"))

# Test/override seam for check_release_versions() (Phase 19, Plan 19-01) —
# the same CAIRN_* convention as CAIRN_JOURNAL above and CAIRN_GBSYNC/
# CAIRN_MAP/CAIRN_GATE elsewhere (CONVENTIONS.md's "Environment variable
# seams" note). Default: the sibling cairn-release.py next to this script.
# The doctor never reimplements the manifest reads; it calls the script that
# owns them.
CAIRN_RELEASE = os.environ.get(
    "CAIRN_RELEASE", str(SCRIPTS_DIR / "cairn-release.py"))
# jira-links' way of asking the tracker whether a key exists: a command
# that takes the key as its last argument and prints the card JSON (REST
# shape), exiting non-zero when the card is absent. Unset -> REST through
# the backend's own env var names, when both are in the shell.
CAIRN_JIRA_FETCH = os.environ.get("CAIRN_JIRA_FETCH")
JIRA_FETCH_TIMEOUT = 20
CAIRN_TEST = os.environ.get(
    "CAIRN_TEST", str(SCRIPTS_DIR / "cairn-test.py"))

# Test/override seam for check_req_ledger()'s single read of the requirement
# ledger (AUTO-07) — same CAIRN_* convention as the three seams above. The
# doctor never re-parses the ledger: cairn-bookkeep.py owns that reading, and
# a second parser is how a repo ends up with a fifth number for the same
# quantity (T-29-31).
CAIRN_BOOKKEEP = os.environ.get(
    "CAIRN_BOOKKEEP", str(SCRIPTS_DIR / "cairn-bookkeep.py"))

# Test/override seam for check_phase_landed() (Phase 30, PR-04) — same CAIRN_*
# convention as the seams above. The doctor reads NO git of its own: cairn-
# land.py owns "did this work enter the control branch", cairn-status.py's
# board renders from the same report, and a `git merge-base` written here would
# be the second reader of one fact — which is the defect this milestone has
# already paid for twice.
CAIRN_LAND = os.environ.get(
    "CAIRN_LAND", str(SCRIPTS_DIR / "cairn-land.py"))

# Test/override seam for check_gsd_capability() (Phase 37, PLUG-02) — same
# CAIRN_* convention as the seams above. Default: the plugin's own vendored
# GSD runtime, a sibling of scripts/. It is a seam and not a constant because
# the check's FAIL path is "this tree is incomplete", and a test cannot prove
# a refusal it has no way to trigger.
CAIRN_VENDORED_GSD = os.environ.get(
    "CAIRN_VENDORED_GSD", str(SCRIPTS_DIR.parent / "gsd"))

PHASE_LABEL = re.compile(r"^phase-(\d+)$")
PHASE_HEAD = re.compile(r"^#{1,6}\s+Phase\s+0*(\d+)\b")
ANY_HEAD = re.compile(r"^#{1,6}\s")
CHECKBOX_PHASE = re.compile(r"^\s*-\s*\[([ xX])\]\s.*?\bPhase\s+0*(\d+)\b")
TABLE_PHASE = re.compile(r"^\s*\|\s*0*(\d+)[.)\s][^|]*\|.*\|\s*Complete\s*\|",
                         re.IGNORECASE)
REQ_LINE = re.compile(r"^\*\*Requirements\*\*\s*:(.*)$")
REQ_ID = re.compile(r"[A-Za-z][A-Za-z0-9]*-\d+")
VERSION_TOKEN = re.compile(r"\bv\d+(?:\.\d+)*\b")
# The filename /gsd:complete-milestone leaves in .planning/milestones/ when it
# archives a cycle. Anchored on both ends: the archived ROADMAP is the
# evidence, and a REQUIREMENTS file or a phases/ directory is not (T-18).
ARCHIVED_ROADMAP = re.compile(r"^(v\d+(?:\.\d+)*)-ROADMAP\.md$")
DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")
PR_NUMBER = re.compile(r"\(#(\d+)\)")

# Labels that legitimately carry no phase-* label (migration parking lots,
# unphased /cairn:quick side-quests, plus the phase-lease bookkeeping issue
# — cairn-lease.py's module docstring explains why it never carries a
# phase-<N> label: it would make the lease look like real phase work to
# this doctor's own phase-complete-open check, phase-corroboration, and
# work.md's done-check).
# `milestone` is the milestone carrier (phase 43): the cycle's own bead,
# which by definition wears no phase-N — check_milestone_carrier is the
# check that audits it, and the orphans axis has no opinion about it.
NO_PHASE_EXEMPT = {"migrated-todo", "backlog", "quick", "lease", "milestone"}


def die(msg, code):
    print(f"[cairn-doctor] error: {msg}", file=sys.stderr)
    sys.exit(code)


def read_lines(path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


# --------------------------------------------------------------------------- #
# lenient .planning/ parsing (same shapes cairn-gate / cairn-map accept)
# --------------------------------------------------------------------------- #
def state_frontmatter(planning_dir):
    """{'milestone', 'active_phase'} DERIVADOS DO BD (v1.7).

    Vinham do frontmatter do STATE.md, e o defeito CairnGo-fp7 é exatamente
    o que essa fonte produz: a linha MILESTONE continuava anunciando o ciclo
    ARQUIVADO, porque ninguém tinha voltado ao documento para movê-la depois
    do arquivamento. O trabalho aberto sabe em que ciclo está e em que fase
    está; o documento só sabia o que a última pessoa escreveu nele.
    """
    root = planning_dir.parent
    return {"milestone": cairn_source.milestone(root),
            "active_phase": cairn_source.active_phase(root)}


def state_plan_counters(planning_dir):
    """{'total_plans': int|None, 'completed_plans': int|None} — the two numbers
    exactly AS WRITTEN under `progress:` in STATE.md.

    Nothing here counts a file. That is the whole point: the defect this feeds
    (CairnGo-6bx) is a writer and a verifier sharing one wrong rule and
    therefore agreeing, so recomputing either number with the writer's rule
    would reproduce the defect inside the check meant to catch it.
    """
    out = {"total_plans": None, "completed_plans": None}
    lines = read_lines(planning_dir / "STATE.md")
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^\s*(total_plans|completed_plans)\s*:\s*(.+?)\s*$",
                     line)
        if not m:
            continue
        digits = re.search(r"\d+", m.group(2).split("#", 1)[0])
        if digits:
            out[m.group(1)] = int(digits.group(0))
    return out


def state_phase_dialect(planning_dir):
    """{'current_phase': int|None, 'active_phase': int|None} — the two phase
    keys of STATE.md's frontmatter, each exactly AS WRITTEN.

    Nothing here derives a phase from the roadmap, from the phase tree, or
    from anything else. That is the whole point: the check this feeds exists
    because a writer and a verifier sharing one rule AGREE, so a phase
    recomputed here would agree with whichever key was written by the same
    rule and the disagreement between the two would stay invisible.

    A key whose value carries no digits (`current_phase: null`, an empty
    value) reads as absent: there is no number there to disagree with.
    """
    out = {"current_phase": None, "active_phase": None}
    lines = read_lines(planning_dir / "STATE.md")
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^(current_phase|active_phase)\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        digits = re.search(r"\d+", m.group(2).split("#", 1)[0])
        if digits:
            out[m.group(1)] = int(digits.group(0))
    return out


def roadmap_milestone(planning_dir):
    """O milestone corrente, DERIVADO DO BD (v1.7): o `m-*` com trabalho
    ainda aberto.

    Lia a linha 🚧 do ROADMAP.md. Duas coisas estavam erradas nisso, e a
    segunda é a que o mantra da v1.7 mata: um emoji num documento é um
    campo que alguém tem de lembrar de mover, e um repositório que não
    escreve markdown não tem esse documento para consultar. Um ciclo
    corrente é aquele que ainda tem issue aberta — isso o bd sabe sozinho.

    A assinatura fica: `planning_dir` é a raiz + `.planning`, e o que este
    leitor precisa é a raiz. Nenhum byte de `.planning/` é lido aqui.
    """
    return cairn_source.milestone(planning_dir.parent)


def archived_milestones(planning_dir):
    """Milestone keys ('v1.1', 'v1.2', ...) whose ROADMAP sits archived under
    .planning/milestones/ — the on-disk evidence that a cycle actually closed.

    /gsd:complete-milestone archives the ROADMAP, the REQUIREMENTS and the
    phase tree there when it closes a milestone (cairn/commands/milestone.md),
    so the archived roadmap is the most direct and the cheapest proof that the
    cycle is over. Nothing is inferred from position in a list, from recency,
    or from STATE.md — the same discipline cairn-status already holds by
    reading the milestone list off the roadmap itself (phase 23, T-18).

    Returns an empty set and never raises when the directory is absent, which
    is the ordinary case in a user's repo that has not closed a cycle yet.
    """
    keys = set()
    try:
        entries = list((planning_dir / "milestones").iterdir())
    except OSError:
        return keys
    for entry in entries:
        m = ARCHIVED_ROADMAP.match(entry.name)
        if m:
            keys.add(m.group(1))
    return keys


def disk_roadmap_phases(planning_dir):
    """As fases que o ROADMAP.md em disco enumera. Vazio quando nao ha
    arquivo — e' o sinal de que este repo nao tem GSD por importar."""
    phases = set()
    for line in read_lines(planning_dir / "ROADMAP.md"):
        m = PHASE_HEAD.match(line)
        if m:
            phases.add(int(m.group(1)))
            continue
        m = CHECKBOX_PHASE.match(line)
        if m:
            phases.add(int(m.group(2)))
    return phases


def disk_roadmap_completed(planning_dir):
    """As fases que o ROADMAP.md em disco marca como COMPLETAS, com a mesma
    leniencia do cairn-gate: checkbox `- [x] ... Phase N` e linha de tabela
    de progresso terminando em `| Complete |`."""
    done = set()
    for line in read_lines(planning_dir / "ROADMAP.md"):
        m = CHECKBOX_PHASE.match(line)
        if m:
            if m.group(1) in ("x", "X"):
                done.add(int(m.group(2)))
            continue
        m = TABLE_PHASE.match(line)
        if m:
            done.add(int(m.group(1)))
    return done


def unimported_roadmap_reqs(planning_dir):
    """{fase: [req ids]} lido do ROADMAP.md — a UNICA leitura de markdown que
    sobrevive no doctor, e ela existe para responder uma pergunta so: o que
    deste GSD ainda NAO foi importado?

    Ler `.planning/` para MIGRAR nao e' ler `.planning/` como VERDADE. Num
    repo por migrar o roteiro em disco e' a ENTRADA, e comparar seus
    requisitos contra os beads e' exatamente a cobertura que a migracao
    precisa provar. Num repo ja migrado o arquivo nao existe, e a pergunta
    passa a ser outra (todo requisito estampado tem fase?).

    Devolve {} quando nao ha ROADMAP.md — nao ha GSD por importar aqui.
    """
    path = planning_dir / "ROADMAP.md"
    if not path.is_file():
        return {}
    reqs, current = {}, None
    for line in read_lines(path):
        m = PHASE_HEAD.match(line)
        if m:
            current = int(m.group(1))
            continue
        if ANY_HEAD.match(line):
            current = None
        if current is not None:
            m = REQ_LINE.match(line.strip())
            if m:
                found = REQ_ID.findall(m.group(1))
                if found:
                    reqs[current] = found
    return reqs


def roadmap_phases_and_reqs(planning_dir, milestone_key=None):
    """(fases, {fase: [req ids]}) — do ROTEIRO EM DISCO quando ele existe, do
    BD quando não.

    A REGRA E' UMA SO, E VALE PARA AS TRES CHECAGENS DE DIVERGENCIA
    (req-issue, phase-complete-open, orphans):

        ha `.planning/ROADMAP.md`  ->  ele e' a ENTRADA, e comparar o que ele
                                       afirma contra o que o bd tem e' a
                                       cobertura da IMPORTACAO;
        nao ha                     ->  o bd e' tudo, e a comparacao vira uma
                                       pergunta de convencao interna.

    POR QUE ISTO NAO E' RECUAR DO MANTRA. Derivar tudo do bd num repo que
    AINDA TEM roteiro em disco nao "moderniza" a checagem: ela some. A
    divergencia que essas tres medem — o documento afirma uma coisa, o
    tracker tem outra — fica IMPOSSIVEL POR CONSTRUCAO quando as duas pontas
    passam a ser a mesma fonte, e uma checagem que nao pode reprovar nao
    protege ninguem. Foi exatamente o que a suite pegou: oito casos de
    `phase-complete-open` viraram verde sem que nada tivesse melhorado.

    O mantra diz que `.planning/` existe PARA MIGRAR. E' o que esta leitura
    faz, e ela morre sozinha no dia em que o diretorio nao existir.
    """
    root = planning_dir.parent
    disk_reqs = unimported_roadmap_reqs(planning_dir)
    disk_phases = disk_roadmap_phases(planning_dir)
    if disk_phases:
        return disk_phases, disk_reqs
    key = milestone_key if milestone_key is not None else \
        cairn_source.milestone(root)
    return (cairn_source.phases(root, key),
            cairn_source.phase_reqs(root, key))


def roadmap_completed_phases(planning_dir, milestone_key=None):
    """Fases terminadas, DERIVADAS DO BD (v1.7): toda issue da fase fechada,
    e ao menos uma issue existindo.

    O checkbox `- [x]` era uma AFIRMAÇÃO sobre o trabalho, digitada à mão e
    livre para discordar dele — a divergência que o próprio doctor mantinha
    uma segunda checagem para pegar. O status dos beads não discorda do
    trabalho: ele É o trabalho. E a fase vazia não conta como completa, que
    é o `all([])` que faria um relatório dizer "pronto" sobre o que nunca
    começou.
    """
    root = planning_dir.parent
    key = milestone_key if milestone_key is not None else \
        cairn_source.milestone(root)
    disk_done = disk_roadmap_completed(planning_dir)
    if disk_roadmap_phases(planning_dir):
        # Ha roteiro: o que ELE marca como completo e' a afirmacao a
        # confrontar com o tracker (ver roadmap_phases_and_reqs).
        return disk_done
    return cairn_source.completed_phases(root, key)


def disk_complete_phases(planning_dir):
    """Phase numbers that look complete ON DISK: the phase dir has >=1
    *-PLAN.md and every non-superseded plan has its sibling *-SUMMARY.md.
    The artifact-based notion of 'complete', held next to the ROADMAP
    checkbox one — phase-complete-open notes when the two diverge."""
    done = set()
    for n, d in phase_dirs(planning_dir):
        plans = sorted(d.glob("*-PLAN.md"))
        if not plans:
            continue
        complete = True
        for f in plans:
            status, _ = parse_plan_frontmatter(f)
            if status == "superseded":
                continue
            summary = f.with_name(f.name[:-len("-PLAN.md")] + "-SUMMARY.md")
            if not summary.is_file():
                complete = False
                break
        if complete:
            done.add(n)
    return done


def disk_incomplete_reasons(planning_dir):
    """{phase number: why it falls short of disk_complete_phases}, for the
    phases that HAVE a directory. The divergence note used to claim 'a
    non-superseded PLAN lacks its SUMMARY' for every gap, including a phase
    with no directory at all — this names the real case instead. A phase
    absent from the mapping has no directory on disk (the caller's
    default); a phase in disk_complete_phases is absent too."""
    reasons = {}
    for n, d in phase_dirs(planning_dir):
        plans = sorted(d.glob("*-PLAN.md"))
        if not plans:
            reasons[n] = f"{d.name}/ holds no PLAN"
            continue
        missing = []
        for f in plans:
            status, _ = parse_plan_frontmatter(f)
            if status == "superseded":
                continue
            summary = f.with_name(f.name[:-len("-PLAN.md")] + "-SUMMARY.md")
            if not summary.is_file():
                missing.append(f.name)
        if missing:
            extra = (f" (+{len(missing) - 1} more)" if len(missing) > 1
                     else "")
            reasons[n] = f"{missing[0]}{extra} lacks its SUMMARY"
    return reasons


def divergence_sentence(n, disk_reasons):
    """The one sentence both the pre-close warning and check 5's note item
    print, carrying the concrete on-disk gap for phase n."""
    why = (disk_reasons or {}).get(n, "no phase directory on disk")
    return (f"phase {n} is checked off in ROADMAP.md but its on-disk "
            f"artifacts disagree ({why}) — confirm the phase is really "
            f"done before closing")


def parse_plan_frontmatter(path):
    """(status, beads ids) from a PLAN.md's YAML frontmatter, leniently:
    'beads: [a, b]' flow style (trailing comment tolerated) or an indented
    '- id' block list."""
    lines = read_lines(path)
    if not lines or lines[0].strip() != "---":
        return None, []
    body = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    status, beads = None, []
    for i, line in enumerate(body):
        m = re.match(r"^status\s*:\s*(.+?)\s*$", line)
        if m:
            status = m.group(1).split("#", 1)[0].strip().strip("'\"")
            continue
        m = re.match(r"^beads\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1)
        if "[" in rest:
            inner = rest[rest.index("[") + 1:]
            if "]" in inner:
                inner = inner[:inner.index("]")]
            beads = [t.strip().strip("'\"") for t in inner.split(",")]
            beads = [b for b in beads if b]
        else:
            for cont in body[i + 1:]:
                mi = re.match(r"^\s*-\s*(.+?)\s*$", cont)
                if not mi:
                    break
                beads.append(mi.group(1).strip("'\""))
    return status, beads


def plan_inventory(planning_dir):
    """[{rel, phase, status, beads}] for every *-PLAN.md under phases/."""
    plans = []
    phases_root = planning_dir / "phases"
    if not phases_root.is_dir():
        return plans
    for d in sorted(p for p in phases_root.iterdir() if p.is_dir()):
        m = DIR_PREFIX.match(d.name)
        if not m:
            continue
        n = int(m.group(1))
        for f in sorted(d.glob("*-PLAN.md")):
            status, beads = parse_plan_frontmatter(f)
            plans.append({"rel": f"{d.name}/{f.name}", "phase": n,
                          "status": status, "beads": beads})
    return plans


def phase_dirs(planning_dir):
    """[(phase number, dir Path)] under <planning>/phases/."""
    out = []
    phases_root = planning_dir / "phases"
    if not phases_root.is_dir():
        return out
    for d in sorted(p for p in phases_root.iterdir() if p.is_dir()):
        m = DIR_PREFIX.match(d.name)
        if m:
            out.append((int(m.group(1)), d))
    return out


# --------------------------------------------------------------------------- #
# bd access
# --------------------------------------------------------------------------- #
def bd_all_issues(root):
    """Every issue (open and closed), labels normalized, exit 5 on failure."""
    cmd = ["bd", "-C", str(root), "list", "--all", "--limit", "0", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"bd list failed: {proc.stderr.strip()}", EXIT_NO_BD)
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        die(f"bd list returned invalid JSON: {e}", EXIT_NO_BD)
    if data is None:
        data = []
    issues = data if isinstance(data, list) else [data]
    for issue in issues:
        issue["labels"] = issue.get("labels") or []
    return sorted(issues, key=lambda i: i.get("id", ""))


def gsd_req(issue):
    """metadata.gsd.req of a bd issue, or None when absent."""
    md = issue.get("metadata")
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except json.JSONDecodeError:
            md = None
    gsd = md.get("gsd") if isinstance(md, dict) else None
    req = gsd.get("req") if isinstance(gsd, dict) else None
    return req.strip() if isinstance(req, str) and req.strip() else None


def phase_nums(issue):
    """Phase numbers from the issue's phase-<N> labels."""
    out = []
    for lb in issue["labels"]:
        m = PHASE_LABEL.match(lb)
        if m:
            out.append(int(m.group(1)))
    return out


def in_done_phase(issue, completed):
    """True when the issue is phase-labeled and EVERY phase label points at
    a ROADMAP-complete phase — an issue the roadmap says was already
    delivered. ALL, not any: a cross-phase issue stays live while any of
    its phases is still open, and an unlabeled issue is never stale. Same
    predicate as cairn-status's in_done_phase, so the board and the doctor
    never disagree about what is deliverable."""
    ns = set(phase_nums(issue))
    return bool(ns) and ns <= set(completed)


def in_milestone(issue, milestone):
    """Same scoping as cairn-gate: the issue counts when no milestone is
    resolved, when it carries m-<milestone>, or when it carries no m-*
    label at all (legacy stray)."""
    m_labels = [lb for lb in issue["labels"] if lb.startswith("m-")]
    return milestone is None or not m_labels or f"m-{milestone}" in m_labels


def milestone_keys(issue):
    """Milestone keys from the issue's m-<key> labels, read the same way
    phase_nums() reads phase-<N> — one shape for reading a label, not a
    third one invented here."""
    return {lb[2:] for lb in issue["labels"]
            if lb.startswith("m-") and lb[2:]}


def in_archived_milestone(issue, archived):
    """True when this issue belongs entirely to cycles that already closed —
    the exemption VOID-03's second half grants the orphans check, so the
    count of historical findings falls to zero at the end of a cycle instead
    of growing forever until the operator learns to ignore the check.

    THREE conditions, all at once (phase 23, T-19), and each exclusion is a
    finding somebody still wants:

      closed          work still live on a cycle that already closed is
                      exactly a finding worth reporting, not historical noise.
      has an m-* label
                      with no milestone label there is no evidence of
                      archiving at all, and exempting anyway is the same
                      reasoning as approving because nothing was compared —
                      the defect this whole phase removes.
      ALL of them archived, not ANY
                      the same ALL/ANY distinction in_done_phase and
                      --close-completed already hold. milestone.md documents
                      that an issue carried into the NEW cycle shows up as a
                      transient orphan until the new roadmap places it, and
                      says that warning is expected: one active-milestone
                      label is enough to keep it.
    """
    if issue.get("status") != "closed":
        return False
    keys = milestone_keys(issue)
    return bool(keys) and keys <= set(archived)


# --------------------------------------------------------------------------- #
# the checks
# --------------------------------------------------------------------------- #
def check_req_issue(issues, reqs_by_phase, milestone, unimported=None):
    """Dois modos, e o que decide entre eles e' a existencia do roteiro:

    A) HA um `.planning/ROADMAP.md` (repo por migrar) — a pergunta e' de
       COBERTURA DA IMPORTACAO: todo requisito que o roteiro declara tem bead
       estampado e rotulado? A prescricao e' `/cairn:migrate`.
    B) NAO ha (repo cairn) — a pergunta e' de CONVENCAO: todo bead que carrega
       `gsd.req` tem tambem `phase-N`? Um requisito sem fase e' invisivel a
       tudo que lista trabalho por fase.

    O modo A e' o que impede a v1.7 de perder a garantia junto com o arquivo:
    sem ele, um roteiro cheio de requisitos nao importados passaria calado.
    """
    if unimported:
        reqs_by_phase = unimported
    items = []
    total = 0
    scoped = [i for i in issues if in_milestone(i, milestone)]
    for n in sorted(reqs_by_phase):
        for req in reqs_by_phase[n]:
            total += 1
            matching = [i for i in scoped if gsd_req(i) == req]
            if any(n in phase_nums(i) for i in matching):
                continue
            if matching:
                ids = ", ".join(i.get("id", "?") for i in matching)
                items.append(f"{req} (phase {n}): {ids} carry the req but "
                             f"none is labeled phase-{n}")
            else:
                items.append(f"{req} (phase {n}): no issue with "
                             f"metadata.gsd.req == {req}")
    if not total and not unimported:
        # MODO B: sem roteiro e sem fase no ciclo, a convencao ainda e'
        # verificavel sobre os beads que existem — um `gsd.req` sem `phase-N`
        # e' um requisito que nenhuma listagem por fase alcanca.
        stray = [i for i in scoped
                 if gsd_req(i) and not phase_nums(i)]
        if stray:
            return {"id": "req-issue", "status": "fail",
                    "detail": f"{len(stray)} stamped requirement(s) carry no "
                              f"phase-* label",
                    "items": [f"{i.get('id', '?')}: gsd.req "
                              f"{gsd_req(i)} with no phase-* label"
                              for i in stray]}
        if any(gsd_req(i) for i in scoped):
            return {"id": "req-issue", "status": "ok",
                    "detail": f"{sum(1 for i in scoped if gsd_req(i))} "
                              f"stamped requirement(s), each labeled with its "
                              f"phase",
                    "items": []}
    if not total:
        # Phase 23 / VOID-02 (CairnGo-ca3). This used to read `ok` with the
        # detail "no '**Requirements**:' lists found" — a check announcing
        # success over a comparison it never made. `no-input`, not
        # `out-of-scope`: the mapping requirement -> issue is a guarantee this
        # project WANTS, it has simply never been verified here, and writing
        # the line in ROADMAP.md is a concrete thing the operator can do.
        # v1.7: a frase falava de uma linha `**Requirements**:` no
        # ROADMAP.md, e mandava o operador escreve-la. Num repo que nao gera
        # markdown esse conselho manda editar um arquivo que nao existe — pior
        # que nao dizer nada, porque parece acionavel. O insumo agora e' o
        # ciclo: sem fase no milestone corrente nao ha o que cruzar.
        return {"id": "req-issue", "status": NOT_APPLICABLE,
                "scope": NA_NO_INPUT,
                "detail": "nothing to compare — the current milestone carries "
                          "no phase-labeled issue, so no requirement was ever "
                          "checked against one here; open a phase with "
                          "/cairn:phase add (or /cairn:milestone new)",
                "items": []}
    if items:
        detail = f"{len(items)} of {total} requirement(s) unmapped"
    else:
        detail = f"{total} requirement(s) mapped to issues"
    return {"id": "req-issue", "status": "fail" if items else "ok",
            "detail": detail, "items": items}


def check_frontmatter_ids(plans, issues):
    by_id = {i.get("id"): i for i in issues}
    items = []
    checked = 0
    live_plans = 0
    for plan in plans:
        if plan["status"] == "superseded":
            continue
        live_plans += 1
        for bid in plan["beads"]:
            checked += 1
            iss = by_id.get(bid)
            if iss is None:
                items.append(f"{plan['rel']}: {bid} not found in bd")
            elif plan["phase"] not in phase_nums(iss):
                labels = ", ".join(iss["labels"]) or "none"
                items.append(f"{plan['rel']}: {bid} lacks label "
                             f"phase-{plan['phase']} (labels: {labels})")
    if not checked:
        # Phase 23 / VOID-02. `0 plan bead id(s) verified` was a count of
        # nothing wearing the success marker. Two ways to get here, one
        # sentence each, and BOTH are no-input:
        #   - no non-superseded PLAN.md at all: nothing was planned yet, so
        #     the stamp guarantee has never been verified in this repo;
        #   - plans on disk carrying no `beads:` id: an unstamped plan is
        #     precisely the gap cairn exists to prevent, so this is the
        #     loudest no-input there is, not a vacuous pass.
        # v1.7, E A FAMILIA MUDOU DE no-input PARA out-of-scope. Isto nao e'
        # um insumo que falta: e' um insumo que a v1.7 aposentou. O `beads:`
        # do frontmatter existia para AMARRAR um arquivo de plano aos ids que
        # ele entrega; o plano agora E' o bead, e nao ha arquivo do lado de
        # fora para amarrar. Um PLAN.md em disco so aparece num repo por
        # migrar, e ai a checagem volta a ter o que cruzar.
        if not live_plans:
            detail = ("out of scope — a plan is a record on a bead, not a "
                      "file with a 'beads:' frontmatter to be checked "
                      "against; nothing to bind")
            return {"id": "frontmatter-ids", "status": NOT_APPLICABLE,
                    "scope": NA_OUT_OF_SCOPE, "detail": detail, "items": []}
        detail = (f"nothing to compare — none of the {live_plans} "
                  "non-superseded PLAN.md file(s) left by an unmigrated GSD "
                  "carries a 'beads:' frontmatter id — run /cairn:migrate to "
                  "import them")
        return {"id": "frontmatter-ids", "status": NOT_APPLICABLE,
                "scope": NA_NO_INPUT, "detail": detail, "items": []}
    detail = (f"{len(items)} of {checked} plan bead id(s) broken" if items
              else f"{checked} plan bead id(s) verified")
    return {"id": "frontmatter-ids", "status": "fail" if items else "ok",
            "detail": detail, "items": items}


def check_maps_fresh(root, planning_dir, issues):
    # v1.7 — APOSENTADA, e nao so quando falta diretorio de fase.
    #
    # `NN-BEADS-MAP.md` era uma COPIA do bd em disco, e "fresco" media a
    # distancia entre a copia e o original. Com a vista impressa a cada
    # chamada (`cairn-map.sh <N>`), a copia nao existe e a distancia nao tem
    # como crescer: nao ha estado "velho" a detectar. A guarda sai inteira em
    # vez de virar uma que nunca reprova — uma checagem que so pode passar e'
    # pior que checagem nenhuma, porque ocupa a linha onde um leitor procura
    # a garantia.
    #
    # O que ela protegia — "a fase tem issues e ninguem regenerou o mapa" —
    # deixou de ser um risco: perguntar E' regenerar.
    return {"id": "maps-fresh", "status": NOT_APPLICABLE,
            "scope": NA_OUT_OF_SCOPE,
            "detail": "out of scope — the phase map is a view printed from "
                      "bd on demand (cairn-map.sh <N>), not a generated file "
                      "that can go stale",
            "items": []}
    items = []
    checked = 0
    for n, d in phase_dirs(planning_dir):
        map_path = d / f"{n:02d}-BEADS-MAP.md"
        n_issues = sum(1 for i in issues if n in phase_nums(i))
        if not map_path.is_file():
            if n_issues:
                items.append(f"phase {n}: {n_issues} issue(s) but no "
                             f"{map_path.name} — run cairn-map.sh {n}")
                checked += 1
            continue
        checked += 1
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "cairn-map.py"), str(n),
             "--check", "--planning-dir", str(planning_dir)],
            capture_output=True, text=True, cwd=str(root))
        if proc.returncode == 0:
            continue
        if proc.returncode == 3:
            items.append(f"phase {n}: stale map {map_path.name} — "
                         f"run cairn-map.sh {n}")
        elif proc.returncode == 5:
            die(f"cairn-map --check: bd unavailable: "
                f"{proc.stderr.strip()}", EXIT_NO_BD)
        else:
            text = proc.stderr.strip() or proc.stdout.strip()
            first = text.splitlines()[0] if text else ""
            items.append(f"phase {n}: cairn-map --check exit "
                         f"{proc.returncode}: {first}")
    if not checked:
        # Phase 23 / VOID-02. This used to read `ok :: 0 phase map(s)
        # current`, which is a count of nothing announced as a clean bill of
        # health. MEASURED CORRECTION to the plan that asked for this: the
        # insumo here is NOT the roadmap — this function never reads it — it
        # is `.planning/phases/` on disk. An empty roadmap leaves this check
        # running for real, and only an empty phases/ tree silences it.
        # `no-input`: a project with phases should have maps, and generating
        # them is one command away.
        # v1.7, out-of-scope E NAO no-input: `NN-BEADS-MAP.md` era markdown
        # GERADO — uma vista do bd escrita em disco — e cairn deixou de
        # gerar markdown. A vista continua existindo, impressa por
        # `cairn-map.sh <N>`; o que deixou de existir e' a copia em disco que
        # podia envelhecer, e uma checagem de frescor sem copia nao tem
        # objeto.
        return {"id": "maps-fresh", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": "out of scope — the phase map is a view printed "
                          "from bd on demand, not a generated file that can "
                          "go stale",
                "items": []}
    detail = (f"{len(items)} of {checked} phase map(s) need attention"
              if items else f"{checked} phase map(s) current")
    return {"id": "maps-fresh", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


def check_superseded_released(plans, issues):
    if not plans:
        # Phase 23 / VOID-02. Same axis as check_frontmatter_ids and
        # therefore the same verdict: with no PLAN.md on disk this guarantee
        # has never been verified here, and writing a plan is the action.
        # v1.7: mesmo eixo do frontmatter-ids e mesma reclassificacao. Um
        # plano superseded e' um bead que se fecha, e o bd ja responde por ele
        # — nao ha arquivo superseded para inspecionar.
        return {"id": "superseded-released", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": "out of scope — superseding a plan closes its "
                          "record; there is no superseded PLAN.md holding "
                          "ids open",
                "items": []}
    by_id = {i.get("id"): i for i in issues}
    items = []
    n_superseded = 0
    for plan in plans:
        if plan["status"] != "superseded":
            continue
        n_superseded += 1
        for bid in plan["beads"]:
            iss = by_id.get(bid)
            if iss and iss.get("status") in ("open", "in_progress"):
                items.append(f"{plan['rel']}: {bid} still "
                             f"{iss['status']} — release or move it")
    detail = (f"{len(items)} bead(s) still live under superseded plan(s)"
              if items else f"{n_superseded} superseded plan(s), "
                            "no live beads")
    # Phase 23 evaluated and KEPT `ok` here. `n_superseded == 0` with plans on
    # disk is not an absent input: the check swept EVERY plan, found none
    # superseded, and that is a real answer with nothing for the operator to
    # do. The no-input case is the empty inventory, handled at the top.
    return {"id": "superseded-released", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


def check_phase_complete_open(issues, completed, disk_done, milestone,
                              closed_n, closed_phases=(), disk_reasons=None,
                              close_failures=()):
    """Check 5 — non-closed issues whose phase-<N> labels ALL point at
    phases ROADMAP.md marks complete. WARN by default (the phase's checkbox
    and its tracker disagree; --close-completed bulk-closes, or re-open the
    phase), FAIL only when a --close-completed the operator asked for was
    refused by bd and the fixpoint could not drain it: close_failures
    carries [(id, bd's reason)] and each one replaces that issue's generic
    warn item. A cross-phase issue with one phase still open is NOT flagged
    (in_done_phase — cairn-status's semantics). Appends a note item per
    flagged phase where the ROADMAP checkbox and the on-disk artifacts
    diverge; closed_phases carries the phases --close-completed just
    emptied so their divergence note survives the close that removed the
    issues from scope."""
    items = []
    flagged = set(closed_phases)
    failures = dict(close_failures)
    reported = set()
    scoped = [i for i in issues
              if i.get("status") != "closed" and in_milestone(i, milestone)]
    for iss in scoped:
        if not in_done_phase(iss, completed):
            continue
        done = sorted(set(phase_nums(iss)))
        flagged.update(done)
        phases = ", ".join(str(n) for n in done)
        iid = iss.get("id", "?")
        if iid in failures:
            reported.add(iid)
            items.append(f"{iid}: --close-completed could not close it — "
                         f"{failures[iid]}")
        else:
            items.append(f"{iid}: {iss.get('status')} but phase "
                         f"{phases} is complete in ROADMAP.md — close it "
                         f"(--close-completed bulk-closes) or re-open the "
                         f"phase")
    # A refused close whose issue somehow left scope still gets reported —
    # the operator asked for it and did not get it.
    for iid, why in close_failures:
        if iid not in reported:
            items.append(f"{iid}: --close-completed could not close it — "
                         f"{why}")
    n_flagged = len(items)
    for n in sorted(flagged):
        if n not in disk_done:
            items.append(f"note: {divergence_sentence(n, disk_reasons)}")
    detail = (f"{n_flagged} non-closed issue(s) in completed phase(s)"
              if n_flagged
              else "no non-closed issues in completed phases")
    if closed_n:
        detail += f" (closed {closed_n} via --close-completed)"
    if close_failures:
        detail += (f" — {len(close_failures)} refused by bd, still open")
    status = ("fail" if close_failures
              else "warn" if n_flagged else "ok")
    # Phase 23 evaluated and KEPT `ok`. "ROADMAP marks no phase complete" is
    # the ordinary, correct state of a project in its first milestone, and
    # there is no action behind it: the check looked for non-closed issues in
    # completed phases, the set of completed phases is empty, so the set of
    # findings is genuinely empty too. Vacuous truth with nothing to fix is
    # not the same as an input that failed to arrive.
    return {"id": "phase-complete-open", "status": status,
            "detail": detail, "items": items}


def check_orphans(issues, roadmap_phases, archived=frozenset()):
    """Check 6, id "orphans" — TWO INDEPENDENT AXES in one loop, and keeping
    them distinguishable is the whole difficulty of this function.

      axis 1  an issue LABELED phase-<N> where N is not a ROADMAP phase.
              Needs the roadmap; with an empty one there is nothing to
              compare against and the axis cannot run. Exempts an issue whose
              cycles all closed (in_archived_milestone) — see below.
      axis 2  a non-closed issue with NO phase-* label at all (minus the
              NO_PHASE_EXEMPT labels). Never touches the roadmap, and works
              perfectly well with an empty one.

    Phase 23 / VOID-02 + VOID-03's first half. Before it, an empty roadmap
    made axis 1 silently skip and the whole check report `ok :: N issue(s),
    no orphans` — approval for a comparison that never happened. The naive
    promotion is to refuse the CHECK when the roadmap is empty; that would
    swallow every axis-2 finding, and a phase that exists to remove false
    green cannot go creating new silence. So the verdict depends on axis 2:
    an axis-2 finding still WARNs, and only a run with nothing from either
    axis reports not-applicable. Either way the detail SAYS axis 1 could not
    run, so that fact is never lost — not even when there is a warning to
    print on top of it.

    VOID-03's second half, the archived-milestone exemption on axis 1. Every
    closed cycle leaves its phases behind, so the population axis 1 sweeps
    grows at every milestone and never shrinks: measured in this repo on
    2026-08-05, all 61 findings were closed issues of the four archived
    milestones. A warning that only grows becomes noise and the operator
    learns to ignore the check — the same death by desensitization this phase
    fights from the other side. in_archived_milestone() holds the predicate
    and names the three cases deliberately left OUT of it.

    The exemption is never silent: `exempted` counts the issues that WOULD
    have been reported and the detail says so. A repo with sixty-one
    historical issues has to stay distinguishable from a repo with none,
    otherwise the phase would have traded a permanent noise for a permanent
    silence — and an exemption nobody can see is indistinguishable from an
    axis somebody switched off.
    """
    unplaced = []           # axis 1 findings
    unlabeled = []          # axis 2 findings
    exempted = 0            # axis 1 findings suppressed by archiving
    for iss in issues:
        nums = phase_nums(iss)
        if nums:
            if roadmap_phases:
                missing = [n for n in nums if n not in roadmap_phases]
                if not missing:
                    continue
                # Counted only for an issue axis 1 would otherwise have
                # reported, so the number the detail prints is the number of
                # warnings actually suppressed — not a tally of every closed
                # issue in the tracker.
                if in_archived_milestone(iss, archived):
                    exempted += 1
                    continue
                for n in missing:
                    unplaced.append(f"{iss.get('id', '?')}: labeled "
                                    f"phase-{n} but ROADMAP.md has no "
                                    f"phase {n}")
        elif (iss.get("status") != "closed"
                and not NO_PHASE_EXEMPT.intersection(iss["labels"])):
            unlabeled.append(f"{iss.get('id', '?')}: no phase-* label "
                             f"({iss.get('status')}: "
                             f"{iss.get('title', '')})")
    items = unplaced + unlabeled

    if not roadmap_phases:
        # v1.7: o eixo compara o label `phase-N` de uma issue contra as fases
        # do CICLO, e essas vem do bd. Cego aqui significa ciclo sem fase
        # nenhuma, nao documento sem secao.
        blind = ("the phase-label axis could not run — the current milestone "
                 "has no phase to compare labels against")
        if items:
            return {"id": "orphans", "status": "warn",
                    "detail": f"{len(items)} orphan issue(s), and {blind}",
                    "items": items}
        return {"id": "orphans", "status": NOT_APPLICABLE,
                "scope": NA_NO_INPUT,
                "detail": f"nothing to compare — {blind}; the unlabeled-issue "
                          f"axis ran and found nothing over "
                          f"{len(issues)} issue(s)",
                "items": []}

    # The exemption is stated wherever it applied, warning or not: the reader
    # of a count that just fell to zero has to be able to see WHY it fell.
    exempt_note = (f" (+{exempted} closed issue(s) of archived milestone(s) "
                   f"exempted)" if exempted else "")
    detail = (f"{len(items)} orphan issue(s)" if items
              else f"{len(issues)} issue(s), no orphans") + exempt_note
    return {"id": "orphans", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


def unpaired_issues(issues):
    return [i for i in issues
            if phase_nums(i)
            and not any(lb.startswith("m-") for lb in i["labels"])]


# Um label que É uma versão: `v1.6`, `v2`, `v1.10.0`. O prefixo `m-` é o que
# distingue "o ciclo desta issue" de qualquer outro label que por acaso
# pareça uma versão, e escrevê-lo sem o prefixo produz um label que NÃO é
# nada — não filtra, não agrupa, não aparece em `bd list -l m-<x>`.
BARE_VERSION_LABEL = re.compile(r"^v\d+(?:\.\d+)*$")


def malformed_milestone_issues(issues):
    """Issues com um label de versão CRU, sem o prefixo `m-`.

    MEDIDO NO PRÓPRIO REPOSITÓRIO (2026-08-13): o épico `CairnGo-dhl`
    carregava `v1.6` em vez de `m-v1.6` e, por isso, não aparecia em
    listagem nenhuma do ciclo. Sobreviveu ao fecho inteiro do milestone —
    72 issues fechadas, release publicada — e só foi encontrado meses
    depois, à mão.

    POR QUE `label-pairs` NÃO O PEGOU, e por que esta é uma checagem
    separada em vez de um `or` na outra: `unpaired_issues` procura issue com
    `phase-N` e sem `m-*`, e o `dhl` não tinha `phase-N` nenhum. As duas
    condições descrevem defeitos diferentes — par quebrado, e rótulo
    malformado — e um achado que as somasse diria ao usuário uma coisa
    quando a verdade é a outra.

    Backlog fica de fora por construção: trabalho sem ciclo não carrega
    label de versão nenhum, cru ou prefixado, e é a AUSÊNCIA que o marca
    como fora de ciclo (ver a convenção na skill `cairn`).
    """
    out = []
    for i in issues:
        bare = [lb for lb in i.get("labels") or [] if BARE_VERSION_LABEL.match(lb)]
        if bare:
            out.append((i, bare))
    return out


def check_label_pairs(issues, milestone, fixed, fix_error):
    items = []
    for iss in unpaired_issues(issues):
        labels = ", ".join(lb for lb in iss["labels"]
                           if PHASE_LABEL.match(lb))
        hint = (f"cairn-relabel.sh pair --milestone {milestone}"
                if milestone else "cairn-relabel.sh pair --milestone <m>")
        items.append(f"{iss.get('id', '?')}: {labels} but no m-* label "
                     f"— {hint}")
    # A SEGUNDA REGRA, como achado DISTINTO e não como mais um item da
    # primeira: um label de versão cru (`v1.6`) é um `m-*` malformado, e a
    # correção é renomear o label — não emparelhá-lo com um `phase-N` que a
    # issue talvez nem devesse ter. Dizer as duas coisas com a mesma frase
    # mandaria o usuário rodar o comando errado.
    for iss, bare in malformed_milestone_issues(issues):
        items.append(
            f"{iss.get('id', '?')}: label {', '.join(bare)} without the m- "
            f"prefix — invisible to `bd list -l m-{bare[0]}`; rename it "
            f"(bd update {iss.get('id', '?')} --add-label m-{bare[0]} "
            f"--remove-label {bare[0]})")
    if fix_error:
        items.insert(0, f"--fix-labels failed: {fix_error}")
        status = "fail"
        detail = "--fix-labels could not repair the pairing"
    else:
        status = "warn" if items else "ok"
        detail = (f"{len(items)} issue(s) with a broken milestone label"
                  if items
                  else "every phase-labeled issue carries an m-* label, "
                       "and no label is a bare version")
        if fixed:
            detail += f" (fixed {fixed} via cairn-relabel pair)"
    # Phase 23 evaluated and KEPT `ok` for the zero counts here, both of them.
    # An empty tracker is already reported by other checks, so saying it again
    # from this one adds a second voice for one fact; and issues present with
    # every pair intact is the check having swept and approved. Neither is an
    # absent input.
    return {"id": "label-pairs", "status": status,
            "detail": detail, "items": items}



def check_milestone_carrier(issues):
    """Check 7b, id "milestone-carrier" — one carrier per OPEN cycle.

    An open cycle is an m-* label with at least one non-closed issue: that is
    cairn_source.milestone()'s own definition of "current", applied to every
    label rather than to the most frequent one, so a straggler cycle with one
    open bead is asked the question too. Closed cycles are never asked —
    v1.1..v3.3 of this repository have no carrier and never will.

    The severity split is deliberate and dated. Zero carriers is a WARN in
    4.0 because the carrier is a 4.0 contract, and a repository that
    upgrades mid-cycle would otherwise go from green to exit 7 without
    having done anything wrong; the item carries the exact bd create that
    closes the gap. From 4.1 it becomes a failure. Two carriers is a FAIL
    already: that is two beads disagreeing about what the cycle is, and
    the doctor exists to refuse that out loud.
    """
    open_keys = set()
    for iss in issues:
        if iss.get("status") != "closed":
            open_keys.update(cairn_source.issue_milestones(iss))
    if not open_keys:
        return {"id": "milestone-carrier", "status": "ok",
                "detail": "no open cycle — nothing to require a carrier of",
                "items": []}
    missing, doubled = [], []
    for key in sorted(open_keys):
        carriers = [i for i in issues
                    if cairn_source.is_milestone_carrier(i)
                    and key in cairn_source.issue_milestones(i)]
        if not carriers:
            missing.append(
                f"m-{key}: open cycle with no milestone carrier — "
                f"bd create \"<cycle name>\" -t task -l m-{key},milestone "
                f"-d \"<what the cycle promises>\" (a warning in 4.0, a "
                f"failure from 4.1)")
        elif len(carriers) > 1:
            ids = ", ".join(i.get("id", "?") for i in carriers)
            doubled.append(f"m-{key}: {len(carriers)} milestone carriers "
                           f"({ids}) — one cycle, one bead; close or "
                           f"relabel the extra")
    items = doubled + missing
    if doubled:
        status = "fail"
    elif missing:
        status = "warn"
    else:
        status = "ok"
    n = len(open_keys)
    detail = (f"{n} open cycle(s), each with one milestone carrier"
              if status == "ok"
              else f"{len(items)} finding(s) over {n} open cycle(s)")
    return {"id": "milestone-carrier", "status": status,
            "detail": detail, "items": items}


def jira_backend(root):
    """The enabled `jira` backend of .cairn/sync.json, or None."""
    path = root / ".cairn" / "sync.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for b in (data.get("backends") or []) if isinstance(data, dict) else []:
        if isinstance(b, dict) and b.get("type") == "jira" and b.get("enabled"):
            return b
    return None


def jira_fetch(backend, key):
    """(card|None, how) — the card for `key` as REST-shaped JSON, or None
    when the tracker says it does not exist; `how` names the road taken:
    'seam', 'rest', or a 'skipped: …' reason when no road was open. Every
    call is bounded by JIRA_FETCH_TIMEOUT (GUARD-01)."""
    if CAIRN_JIRA_FETCH:
        try:
            proc = subprocess.run(CAIRN_JIRA_FETCH.split() + [key],
                                  capture_output=True, text=True,
                                  timeout=JIRA_FETCH_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as exc:
            return None, f"skipped: CAIRN_JIRA_FETCH failed ({exc})"
        if proc.returncode != 0:
            return None, "seam"
        try:
            return json.loads(proc.stdout or "{}"), "seam"
        except ValueError:
            return None, "skipped: CAIRN_JIRA_FETCH printed no JSON"
    cfg = backend.get("config") or {}
    email = os.environ.get(cfg.get("email_env") or "JIRA_EMAIL", "")
    token = os.environ.get(cfg.get("token_env") or "JIRA_API_TOKEN", "")
    base = str(cfg.get("base_url") or "").rstrip("/")
    if not (email and token and base):
        return None, (f"skipped: no token in the shell "
                      f"({cfg.get('email_env') or 'JIRA_EMAIL'} / "
                      f"{cfg.get('token_env') or 'JIRA_API_TOKEN'})")
    import base64
    import urllib.error
    import urllib.request
    req = urllib.request.Request(
        f"{base}/rest/api/3/issue/{key}?fields=summary,status,issuetype,parent")
    req.add_header("Authorization", "Basic " + base64.b64encode(
        f"{email}:{token}".encode()).decode())
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=JIRA_FETCH_TIMEOUT) as r:
            return json.loads(r.read().decode() or "{}"), "rest"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, "rest"
        return None, f"skipped: REST {exc.code} for {key}"
    except (OSError, ValueError) as exc:
        return None, f"skipped: REST unreachable ({exc})"


def check_jira_links(root, issues):
    """Check 7c, id "jira-links" — the cycle's links, audited off the beads.

    Out of scope, not silent, until .cairn/sync.json enables a `jira`
    backend: a repository that never chose Jira has nothing to compare and
    must not read "no links" as a finding. With a backend, four questions,
    none of which writes:
      gap        an open cycle's milestone carrier, or an open phase's
                 carrier, with no external_ref -> warn (the link is a
                 convention from 4.0 on; a missing one is friction).
      duplicate  two beads sharing one jira-<KEY> -> fail. One card, one
                 bead is the contract; /cairn:doctor puts the pair to the
                 user and offers to create another card.
      absent     a linked key the tracker does not know -> fail. Asked via
                 CAIRN_JIRA_FETCH or REST; when neither can ask, the item
                 says `skipped` and the verdict is not green over it.
      drift      the story's live parent differs from the epic cached on the
                 milestone carrier -> warn.
    """
    backend = jira_backend(root)
    if backend is None:
        return {"id": "jira-links", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": "out of scope — no enabled jira backend in "
                          ".cairn/sync.json (/cairn:sync-config)",
                "items": []}
    key = cairn_source.milestone(root)
    items, fails, warns = [], 0, 0
    linked = {}   # jira key -> [bead ids]
    for iss in issues:
        ref = str(iss.get("external_ref") or "").strip()
        if ref.startswith("jira-"):
            linked.setdefault(ref[len("jira-"):], []).append(iss.get("id", "?"))
    for jkey, ids in sorted(linked.items()):
        if len(ids) > 1:
            fails += 1
            items.append(f"duplicate: {jkey} is linked to "
                         f"{', '.join(sorted(ids))} — "
                         "one card, one bead; /cairn:jira decides which and "
                         "offers another card for the other")
    carriers = []   # (kind, display name, link target, bead)
    if key:
        ms = cairn_source.milestone_carriers(root, key)
        if len(ms) == 1:
            carriers.append(("milestone", f"m-{key}", key, ms[0]))
        done = cairn_source.completed_phases(root, key)
        for n in sorted(cairn_source.milestone_phases(root, key),
                        key=lambda x: (not isinstance(x, (int, float)), x)):
            if n in done:
                continue
            c = cairn_source.phase_carrier(root, n)
            if c is not None:
                carriers.append(("phase", f"phase {n}", n, c))
    for kind, name, target, c in carriers:
        if not str(c.get("external_ref") or "").startswith("jira-"):
            warns += 1
            what = "Story" if kind == "milestone" else "Sub-task"
            items.append(f"gap: {name} ({c.get('id')}) has no jira link — "
                         f"/cairn:jira link --{kind} {target} (a {what})")
    checked, skipped = 0, None
    for jkey, ids in sorted(linked.items()):
        card, how = jira_fetch(backend, jkey)
        if how.startswith("skipped"):
            skipped = how
            break
        checked += 1
        if card is None:
            fails += 1
            items.append(f"absent: {jkey} (on {', '.join(ids)}) does not "
                         f"exist in the tracker (asked via {how})")
            continue
        for kind, name, target, c in carriers:
            if kind != "milestone" or c.get("id") not in ids:
                continue
            cached = (cairn_source.gsd(c).get("jira") or {}).get("epic")
            live = ((card.get("fields") or {}).get("parent") or {}).get("key")
            if cached and live and cached != live:
                warns += 1
                items.append(f"epic drift: {jkey}'s parent is {live} now, "
                             f"and {c.get('id')} caches {cached} — re-link "
                             "to refresh the cache")
    # What the last pull saw (state.json seen.jira, written by gbsync pull
    # or cairn-jira.py seen): a card Done while its bead is open, or the
    # reverse, is named — never acted on (MIRROR-04).
    try:
        state = json.loads((root / ".cairn" / "state.json")
                           .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    seen = ((state.get("seen") or {}).get("jira") or {}) \
        if isinstance(state, dict) else {}
    by_id = {i.get("id"): i for i in issues}
    for jkey, ids in sorted(linked.items()):
        entry = seen.get(jkey) if isinstance(seen, dict) else None
        if not isinstance(entry, dict) or len(ids) != 1:
            continue
        bead = by_id.get(ids[0]) or {}
        card_closed = entry.get("status") == "closed"
        bead_closed = bead.get("status") == "closed"
        if card_closed != bead_closed:
            warns += 1
            items.append(f"status divergent: {jkey} is "
                         f"{'Done' if card_closed else 'open'} in Jira and "
                         f"{ids[0]} is {'closed' if bead_closed else 'open'} "
                         f"in bd (seen {entry.get('at') or '?'}) — the bead "
                         "is the source; close or reopen on the side that is "
                         "wrong")
    for iss in issues:
        mirror = cairn_source.gsd(iss).get("mirror") or {}
        pending = mirror.get("pending") if isinstance(mirror, dict) else None
        waiting = [e for e in (pending or []) if e.get("backend") == "jira"]
        if waiting:
            warns += 1
            what = ", ".join(f"{e.get('action')} {e.get('key') or ''}".strip()
                             for e in waiting[:3])
            items.append(f"pending: {iss.get('id')} has {len(waiting)} mirror "
                         f"write(s) waiting ({what}) — /cairn:jira flush "
                         "applies them in a session")
    if skipped:
        items.append(f"existence of {len(linked)} linked key(s) not checked — "
                     f"{skipped}; in a session, /cairn:jira audit asks the "
                     "MCP instead")
    status = "fail" if fails else ("warn" if warns else "ok")
    detail = (f"{len(linked)} linked key(s), {len(carriers)} open carrier(s)"
              f", {checked} existence check(s)"
              + (", existence skipped" if skipped else ""))
    return {"id": "jira-links", "status": status, "detail": detail,
            "items": items}


def check_planning_writes(root, planning_dir):
    """Check 7d, id "planning-writes" (RECORD-03, phase 46) — a document
    written where the bead is the source.

    In a repo that has `.beads/`, `.planning/phases/` is import material
    and history; every planning command records on beads through
    cairn-record. A file under it that git sees as NEW or MODIFIED in the
    working tree is therefore something written after the fact — a session
    that followed an old habit, or an old prompt — and the finding names the
    record that should have been made instead. Out of scope when there is
    no `.planning/phases/` at all; not a mtime comparison, because no import
    date is recorded and git already says what was born since the last
    commit. Never fails: the file is a symptom, and the cure is one
    cairn-record call and a `git rm`.
    """
    phases_dir = planning_dir / "phases"
    tracked = []
    if phases_dir.is_dir():
        try:
            proc = subprocess.run(["git", "-C", str(root), "ls-files", "--",
                                   str(phases_dir)],
                                  capture_output=True, text=True, timeout=30)
            tracked = (proc.stdout or "").split() if proc.returncode == 0 else []
        except (OSError, subprocess.SubprocessError):
            tracked = []
    if not tracked:
        # Either no directory, or one git never recorded: a GSD project
        # still being imported, not history somebody wrote over. The
        # gsd-unmigrated check owns that case.
        return {"id": "planning-writes", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": "out of scope — .planning/phases/ is not tracked "
                          "history here (nothing imported to guard; the "
                          "record is the bead)",
                "items": []}
    try:
        proc = subprocess.run(["git", "-C", str(root), "status",
                               "--porcelain", "--untracked-files=all", "--",
                               str(phases_dir)],
                              capture_output=True, text=True, timeout=30)
        lines = (proc.stdout or "").splitlines() if proc.returncode == 0 else []
    except (OSError, subprocess.SubprocessError):
        lines = []
    KINDS = {"SPEC": "spec", "CONTEXT": "context", "RESEARCH": "research",
             "PATTERNS": "patterns", "UI-SPEC": "ui-spec", "AI-SPEC": "ai-spec",
             "PLAN": "plan --plan NN", "SUMMARY": "summary --plan NN",
             "VERIFICATION": "verification", "VALIDATION": "verification",
             "SECURITY": "review", "REVIEW": "review"}
    items = []
    for line in lines:
        path = line[3:].strip()
        if not path.endswith(".md"):
            continue
        state = "new" if line[:2].strip() in ("??", "A") else "modified"
        stem = pathlib_name(path)
        kind = next((v for k, v in KINDS.items() if stem.upper().endswith(k)),
                    None)
        m = re.search(r"phases/0*(\d+)", path)
        phase = m.group(1) if m else "<N>"
        cure = (f"cairn-record.sh {kind} --phase {phase}" if kind
                else "the matching cairn-record.sh kind")
        items.append(f"{path} is {state} — a document written where the "
                     f"bead is the source; record it with {cure} and git rm "
                     "the file")
    return {"id": "planning-writes", "status": "warn" if items else "ok",
            "detail": (f"{len(items)} document(s) written under "
                       ".planning/phases/ since the last commit" if items
                       else ".planning/phases/ untouched since the last "
                            "commit — the record is the bead"),
            "items": items}


def pathlib_name(path):
    return path.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def check_claims_stale(issues, milestone, active_phase):
    """Check 8, id "claims-stale" — in_progress issues assigned outside the
    active phase.

    AS SUPERFICIES QUE LEEM `active_phase` do STATE.md, medidas 2026-08-04
    (`grep -rln active_phase cairn/`, menções só em docstring excluídas):
    cairn-status.py, cairn-doctor.py, cairn-lease.py, cairn-migrate.py e
    hooks/session-start.sh. A medição vivia numa constante que nenhuma
    mensagem chegou a consumir; ela informa quem lê, e é aqui que se lê.

    THE NO-INPUT BRANCH IS NOT `ok`, AND THAT IS THE POINT (AUTO-08).
    Measured before this change, in this very repository:

        ✓ claims-stale   skipped — no active_phase in STATE.md

    A check that has never run once in this project's life, wearing the
    success marker. STATE.md here carries `current_phase` (what GSD writes)
    and every cairn reader looks for `active_phase`, so the input has never
    arrived — and `ok` said everything was fine about a comparison that
    never happened. A phase about tools reporting false green cannot leave
    standing the purest specimen the repo owns.

    NOT `fail` EITHER, and the line is deliberate: this is a check with no
    INPUT, not a state inconsistency. Spending exit 7 on friction is how
    exit 7 stops meaning anything (the same line check 16 draws, and the
    same one check 14 draws for a reclaimable lease). So: `warn`, with the
    missing key named, the five readers named, and the open decision
    addressed by id — the shape check_external_ref() already uses for its
    shallow-clone branch, which likewise cannot check rather than having
    checked and found nothing.

    PHASE 23 ARRIVED, AND THIS BRANCH IS `not-applicable` / `no-input`.
    29-07 left `warn` as a placeholder with a note saying so; VOID-01 made
    `not-applicable` first-class and this is its verdict now. The family is
    `no-input`, not `out-of-scope`, and the rule that decides it is: STATE.md
    IS here, it simply lacks a key someone can add. That is a gap, not a repo
    this check has no business running in — so it DOES clear summary["ok"]
    (the report is incomplete) while leaving the exit code at 0.

    WHICH KEY STATE.md SHOULD CARRY IS NOT DECIDED HERE. `current_phase`
    versus `active_phase` changes what five surfaces read and what every
    repo with a STATE.md already on disk means; that is a business rule, it
    is grooming, and it is open in CairnGo-rq0. Not one line here takes a
    side: nothing is renamed, nothing is migrated, and no `active_phase` key
    is written anywhere.
    """
    if active_phase is None:
        # v1.7, E A DISCUSSAO SOBRE QUAL CHAVE O STATE.md DEVE CARREGAR
        # MORREU JUNTO COM A PERGUNTA. A fase ativa vinha de um campo escrito
        # a mao (`active_phase:` / `current_phase:`), e o desacordo entre as
        # duas grafias era o que CairnGo-rq0 discutia. Ela agora e' DERIVADA:
        # a menor fase com trabalho in_progress, senao a menor com trabalho
        # aberto. Nenhuma grafia a define, e nao ha campo para esquecer de
        # mover. Ausencia aqui quer dizer uma coisa so, e ela e' verdadeira:
        # nao ha fase com trabalho aberto.
        # v1.7 — E ESTA E' `ok`, NAO `no-input`, POR UM MOTIVO QUE A SUITE
        # ENSINOU. Com a fase ativa DERIVADA (a menor com trabalho aberto),
        # "nao ha fase ativa" deixou de significar "falta um campo no
        # STATE.md" e passou a significar "nao ha trabalho aberto". Isso
        # RESPONDE a pergunta desta checagem — nenhuma claim pode estar velha
        # quando nao ha claim — em vez de impedi-la.
        #
        # Classifica-la como no-input deixaria todo repositorio de trabalho
        # concluido permanentemente INCOMPLETE, que foi o que a suite pegou:
        # dois casos de phase-artifacts, que nao tem nada a ver com claims,
        # falharam so porque o rodape virou INCOMPLETE por baixo deles.
        return {"id": "claims-stale", "status": "ok",
                "detail": "no phase carries open work, so no claim can be "
                          "stale",
                "items": []}
    items = []
    for iss in issues:
        if iss.get("status") != "in_progress" or not iss.get("assignee"):
            continue
        if not in_milestone(iss, milestone):
            continue
        nums = phase_nums(iss)
        if nums and active_phase not in nums:
            phases = ", ".join(f"phase-{n}" for n in nums)
            items.append(f"{iss.get('id', '?')}: in_progress "
                         f"(assignee {iss['assignee']}) on {phases} but "
                         f"active phase is {active_phase} — stale claim?")
    detail = (f"{len(items)} possible stale claim(s)" if items
              else f"no assigned in_progress issues outside "
                   f"phase {active_phase}")
    return {"id": "claims-stale", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


BD_MIN_VERSION = (1, 1, 0)


def check_bd_version():
    """Check 0 — the bd binary meets the minimum version cairn relies on
    (--claim semantics, --all, label add/remove, nested --metadata)."""
    need = ".".join(map(str, BD_MIN_VERSION))
    proc = subprocess.run(["bd", "version"], capture_output=True, text=True)
    out = (proc.stdout or "").strip()
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    if proc.returncode != 0 or not m:
        return {"id": "bd-version", "status": "warn",
                "detail": "could not parse bd version output: "
                          f"{out or proc.stderr.strip() or '(empty)'}",
                "items": []}
    ver = tuple(int(x) for x in m.groups())
    got = ".".join(map(str, ver))
    if ver < BD_MIN_VERSION:
        return {"id": "bd-version", "status": "fail",
                "detail": f"bd {got} < required {need} — upgrade beads "
                          "(brew upgrade beads / npm update -g @beads/bd)",
                "items": []}
    return {"id": "bd-version", "status": "ok",
            "detail": f"bd {got} >= {need}", "items": []}


def check_bd_doctor(root):
    try:
        proc = subprocess.run(["bd", "doctor"], capture_output=True,
                              text=True, cwd=str(root), timeout=60)
    except subprocess.TimeoutExpired:
        return {"id": "bd-doctor", "status": "warn",
                "detail": "bd doctor timed out after 60s", "items": []}
    text = proc.stdout.strip() or proc.stderr.strip()
    summary = text.splitlines()[0].strip() if text else "(no output)"
    status = "ok" if proc.returncode == 0 else "fail"
    return {"id": "bd-doctor", "status": status,
            "detail": f"exit {proc.returncode}: {summary}", "items": []}


def vendored_runtime_report(runtime_dir):
    """(ok, detail) for the plugin's own vendored GSD runtime.

    MANIFEST.json is the derived list phase 32 wrote from
    `cairn-inventory.sh closure --json`; it is the only thing that knows which
    files the closure contains, and re-deriving that list here would make this
    the second reader of one fact — the defect this milestone has already paid
    for twice.

    Sampled, not exhaustive: the manifest lists 160+ files, and stat-ing every
    one on every doctor run buys nothing that a missing manifest or a missing
    entry-point file does not already catch. What is checked is the manifest
    itself plus its FIRST 25 entries, which span agents/, commands/ and
    gsd-core/ — a tree truncated by a failed install fails on one of them.
    """
    manifest = Path(runtime_dir) / "MANIFEST.json"
    if not manifest.is_file():
        return False, f"no MANIFEST.json under {runtime_dir}"
    try:
        files = json.loads(manifest.read_text(encoding="utf-8")).get("files")
    except (OSError, ValueError) as exc:
        return False, f"MANIFEST.json is unreadable ({exc})"
    if not files:
        return False, "MANIFEST.json lists no files"
    missing = [name for name in files[:25]
               if not (Path(runtime_dir) / name).is_file()]
    if missing:
        return False, (f"{len(missing)} of the first 25 manifest entries are "
                       f"absent (e.g. {missing[0]})")
    return True, f"{len(files)} files, manifest verified"


def external_gsd_lineages():
    """{'legacy': [ids], 'core': [ids]} — GSD plugins Claude Code has installed.

    Delegates to cairn-capability.py, which already owns this read and its
    lineage rules; the doctor never grows a second reader of
    installed_plugins.json. None on ANY failure, and the caller degrades to
    WARN rather than crashing the whole run over this one check — the shape
    check_lease_stale() established.
    """
    script = SCRIPTS_DIR / "cairn-capability.py"
    if not script.is_file():
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "detect", "--json"],
            capture_output=True, text=True, timeout=300)
        info = json.loads(proc.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None
    installed = info.get("installed_gsd") or {}
    return {"legacy": list(installed.get("legacy") or []),
            "core": list(installed.get("core") or [])}


def capability_residue(root):
    """Paths a pre-v1.6 /cairn:init left behind, or [] — never deleted here."""
    found = []
    for rel in (".gsd/capabilities/cairn", ".gsd-capabilities.json"):
        if (Path(root) / rel).exists():
            found.append(rel)
    return found


def check_gsd_capability(root):
    """Check 10 — is the VENDORED GSD runtime intact, and is any external GSD
    lineage still installed beside it?

    Phase 37 (PLUG-02) turned this check around, and the inversion is the point
    of it. It used to ask "is the cairn capability registered against the
    installed gsd-core?" and prescribed INSTALLING `gsd-core@cairngo` when it
    was not. cairn no longer installs, requires, or publishes gsd-core: the
    runtime is vendored under the plugin's own gsd/. So the questions became:

        1. Is the runtime this plugin carries actually complete?
        2. Is an external GSD lineage still installed, answering /gsd:* with
           markdown-era workflows while /cairn:* answers with bd?

    Question 2 is the defect class the whole v1.5 cycle chased, with the
    obsolete lineage now being gsd-core itself. An installed gsd-core is
    therefore a FAIL prescribing `claude plugin uninstall` — the exact opposite
    of the sentence this function used to print, and that reversal is asserted
    in both directions by tests/cairn-doctor-lineage.bats.

    ORDER OF DECISION, and it is load-bearing:

    1. A broken vendored runtime FAILS first. It is a defect of the INSTALL,
       not of the environment, and no statement about the environment is worth
       anything while the plugin itself is incomplete.
    2. An external lineage FAILS second, naming every id found.
    3. Residue under .gsd/ WARNs last. Checked after the failures on purpose:
       a machine that ran /cairn:init before v1.6 has BOTH the gsd-core install
       and the residue, and evaluating residue first would report the finding
       that needs action as a warning.

    Residue is WARN and never FAIL for the reason checks 8 and 14 already
    record: leftover files are friction, not a state inconsistency, and an
    exit 7 spent on friction stops meaning anything. The doctor NAMES the
    cleanup; it never deletes.
    """
    ok, detail = vendored_runtime_report(CAIRN_VENDORED_GSD)
    if not ok:
        return {"id": "gsd-capability", "status": "fail",
                "detail": f"the vendored GSD runtime is incomplete — {detail}",
                "items": [
                    "This is a defect of the cairn install, not of your "
                    "environment: no external plugin can supply it.",
                    "Fix: claude plugin install cairn@cairngo, then "
                    "/reload-plugins",
                ]}

    lineages = external_gsd_lineages()
    if lineages is None:
        return {"id": "gsd-capability", "status": "warn",
                "detail": f"vendored GSD runtime ok ({detail}); could not read "
                          "which plugins are installed, so a leftover external "
                          "GSD would not be reported", "items": []}

    external = lineages["core"] + lineages["legacy"]
    if external:
        items = [f"Fix: claude plugin uninstall {name}" for name in external]
        items.append("then /reload-plugins")
        items.append("cairn vendors its own GSD runtime since v1.6 — an "
                     "installed gsd-core answers /gsd:* with the pre-bd "
                     "workflows while /cairn:* answers with bd, and two "
                     "lineages at once is the window the vendoring closed.")
        return {"id": "gsd-capability", "status": "fail",
                "detail": "an external GSD plugin is still installed — "
                          f"{', '.join(external)}. cairn no longer requires "
                          "one, and two lineages must not answer at once",
                "items": items}

    residue = capability_residue(root)
    if residue:
        return {"id": "gsd-capability", "status": "warn",
                "detail": "vendored GSD runtime ok; leftover capability state "
                          f"from a pre-v1.6 /cairn:init — {', '.join(residue)}",
                "items": [
                    "The cairn GSD capability was archived in v1.6: there is "
                    "no external host for its contributions any more, and "
                    "nothing reads these files.",
                    "Fix: rm -rf " + " ".join(residue),
                ]}

    return {"id": "gsd-capability", "status": "ok",
            "detail": f"vendored GSD runtime ok ({detail}); no external GSD "
                      "lineage installed", "items": []}


# --------------------------------------------------------------------------- #
# check 11 — phase-corroboration (CORR-06)
# --------------------------------------------------------------------------- #
CORROBORATION_RECOMMENDATION = {
    ("disk", "bd"): "close the open bd issue(s) if the work is done, or "
                    "run /cairn:work N if it is not",
    ("roadmap", "disk"): "confirm the phase is really done before leaving "
                         "the checkbox ticked, or re-plan it",
    ("state_md", "disk"): "STATE.md's active_phase looks stale — no action "
                          "needed unless you are actually still working "
                          "phase N",
}


def corroboration_recommendation(sources):
    """The first, most-likely fix for a conflict's source pair (D-01: the
    likely-correct option presented first, never a bare list of options)."""
    return CORROBORATION_RECOMMENDATION.get(
        tuple(sources), "see /cairn:doctor for details")


def journal_last_moved(root, phase):
    """cairn-journal.py's `last-moved --phase N --json` for one PHASE, or
    None on ANY failure (missing/broken script, nonzero exit, unparsable
    JSON) — mirroring check_lease_stale()'s shell-out-and-degrade shape
    exactly, one level down: a failure HERE degrades only the calling
    conflict item's enrichment text (see _last_moved_clause()), never
    check_phase_corroboration()'s own status/severity computation (T-16-09
    — that verdict is already fully decided by corroborate()'s own
    "severity" field by the time this is ever called). Shells through the
    CAIRN_JOURNAL env seam (default: the sibling cairn-journal.py), the
    same test/override convention cairn-lease.py and cairn-status.py
    already use for this identical script."""
    try:
        proc = subprocess.run(
            [sys.executable, CAIRN_JOURNAL, "last-moved",
             "--phase", str(phase), "--json", "--project-dir", str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None


def _last_moved_clause(last_moved, sources):
    """'<source> last moved <ts>, ...' — one clause per SOURCES key
    (a conflict's own ["disk","bd"]-shaped list), pulled from
    journal_last_moved()'s per-axis {"value":..., "ts":...} dict. A
    source with no prior record (the axis key is None/missing) renders
    the literal phrase "never observed", per JOUR-02's own wording — never
    a blank, never a fabricated timestamp. Returns "" (append nothing)
    when LAST_MOVED itself is None — the journal call failed or was never
    attempted, and the item's EXISTING (pre-Plan-16-05) text is left
    completely untouched in that case.

    Phase 28 (DJOUR-02) adds one branch: the journal is now partitioned
    one file per checkout, so an axis can have been observed by SEVERAL
    checkouts. In that case cairn-journal.py reports no single `ts` — a
    single timestamp across machines would be an ordering claim, and E14
    measured that the clock agreement available (−16.7 ms NTP offset) is
    coarser than the resolution needed (10.8 ms minimum record gap). The
    clause then NAMES each machine and says outright that no order is
    claimed between them. Still purely additive: severity, status and
    exit code were all decided before this function was ever called."""
    if last_moved is None:
        return ""
    clauses = []
    for source in sources:
        entry = last_moved.get(source)
        if not entry:
            clauses.append(f"{source} last moved never observed")
            continue
        candidates = entry.get("candidates")
        if candidates:
            seen = ", ".join(
                f"{c.get('ts')} on {c.get('machine') or 'unknown machine'}"
                for c in candidates)
            clauses.append(f"{source} last moved {seen} (order between "
                           "machines not claimed)")
        else:
            clauses.append(f"{source} last moved {entry.get('ts')}")
    return ", ".join(clauses)


def check_phase_corroboration(root, planning_dir):
    """Check 11, id "phase-corroboration" (CORR-06) — reads Plan 13-01's
    phase_model() corroboration verdict for every phase (shells to
    'cairn-status.py --json', the same subprocess pattern check_maps_fresh()
    already uses for cairn-map.py --check) and routes each non-"ok" phase to
    a recommended fix.

    Two severities only (D-09), each carrying corroborate()'s own written
    justification (see cairn-status.py): a "blocks" conflict FAILS the
    doctor run (reuses EXIT_FAILED, no new exit code); an "informs"
    conflict or an "unknown" verdict (bd unreadable for that phase) WARNs
    without failing — D-10's "the ship gate bars only the blockers" posture,
    applied here to doctor's own exit code too. A subprocess/parse failure
    degrades to WARN rather than crashing the whole doctor run over one
    check — corroboration is additive, never a new way for doctor itself to
    become unusable.

    Each "conflict" item ALSO cites when each of that conflict's cited
    sources last moved (Phase 16, JOUR-02 — D-04's "dentro do relatório de
    conflito", the ONLY place this history surfaces by design), via
    journal_last_moved(): one cairn-journal.py `last-moved` call per phase
    that has at least one conflict — cached in last_moved_cache, never
    once per conflict item, even when a phase carries several (e.g. both
    a ["disk","bd"] and a ["roadmap","disk"] conflict at once). This is
    PURELY additive text appended to an item whose status/severity was
    already fully decided above — a broken or missing journal degrades
    that one item's trailing clause to nothing (no clause at all), never
    the item's severity, never this check's own status/exit code.
    """
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "cairn-status.py"), "--json",
         "--planning-dir", str(planning_dir)],
        capture_output=True, text=True, cwd=str(root))
    # 0 (every phase corroborated) and 5 (cairn-status.py's own bd probe
    # failed — a normal, documented degrade that still emits valid JSON
    # with every affected phase's bd axis reading "unknown") are the two
    # exit codes cairn-status.py --json is documented to pair with real
    # output; anything else is unexpected.
    if proc.returncode not in (0, 5):
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        return {"id": "phase-corroboration", "status": "warn",
                "detail": f"cairn-status.py --json exited "
                          f"{proc.returncode}, corroboration could not be "
                          f"computed: {first}",
                "items": []}
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        return {"id": "phase-corroboration", "status": "warn",
                "detail": "cairn-status.py --json returned invalid JSON, "
                          f"corroboration could not be computed: {e}",
                "items": []}

    items = []
    any_blocks = False
    n_phases = 0
    last_moved_cache = {}
    for p in data.get("phases") or []:
        verdict = p.get("corroboration")
        if verdict in (None, "ok"):
            continue
        n_phases += 1
        n = p.get("number")
        if verdict == "conflict":
            conflicts = p.get("conflicts") or []
            if conflicts and n not in last_moved_cache:
                last_moved_cache[n] = journal_last_moved(root, n)
            last_moved = last_moved_cache.get(n)
            for c in conflicts:
                sev = c.get("severity")
                sources = c.get("sources") or []
                rec = corroboration_recommendation(sources)
                line = f"{n}: {c.get('detail', '')} ({sev}) — {rec}"
                clause = _last_moved_clause(last_moved, sources)
                if clause:
                    line = f"{line} — {clause}"
                items.append(line)
                if sev == "blocks":
                    any_blocks = True
        elif verdict == "unknown":
            items.append(f"{n}: bd could not be read for this phase — "
                         f"re-run once bd is reachable")
    detail = (f"{len(items)} corroboration item(s) across {n_phases} "
              "phase(s)" if items else "every phase's corroboration is ok")
    status = "fail" if any_blocks else ("warn" if items else "ok")
    return {"id": "phase-corroboration", "status": status,
            "detail": detail, "items": items}


# --------------------------------------------------------------------------- #
# check 12 — phase-artifacts (CARD-02, D-04)
# --------------------------------------------------------------------------- #
def check_phase_artifacts(root, planning_dir, disk_reasons):
    """Check 12, id "phase-artifacts" (CARD-02/D-04) — names which artifact
    is missing when a phase's board row would otherwise show only a bare
    dash: a PLAN.md still lacking its own SUMMARY.md in a phase that has
    already reached disk_state "verified", or an NN-VERIFICATION.md with
    no readable 'status:' verdict in its frontmatter. This is the doctor
    half of D-04's narrowing of the phase card's missing-artifact story —
    the board says "not planned" or renders a dash; naming the concrete
    gap by filename is doctor's job, the same division of labor phase 13
    already established for per-source conflict detail (check 11, above).

    The missing-SUMMARY half is gated on disk_state == "verified"
    DELIBERATELY, not on every plans/summary gap
    disk_incomplete_reasons() (already computed once in main() as
    disk_reasons, reused here rather than recomputed — no duplicate
    frontmatter parser in this file) reports. An earlier draft fired on
    ANY phase with an unsummarized plan regardless of state; a
    plan-checker caught that this fires on completely ordinary mid-flight
    work (a phase between waves always has some plans without summaries
    yet) and is noise, not signal. A phase someone ran /cairn:verify on
    despite one of its plans never having been summarized is a genuine
    anomaly; a phase still being worked is not.

    Known, accepted residual gap — written down rather than left as a
    silent trap: a phase stuck at disk_state "executed" (its SUMMARY-less
    plan sits there, nobody ever runs /cairn:verify on it, so it never
    reaches "verified") never fires this check either. The narrowed gate
    trades that false negative for the mid-flight false positive it was
    built to remove; check 5 (phase-complete-open) independently covers
    the ROADMAP-checkbox-complete flavor of the same on-disk gap.

    Shells to 'cairn-status.py --json' exactly the way
    check_phase_corroboration() already does, reading phase_model()'s
    disk_state and verify_status for every phase in the same subprocess
    call. On a returncode outside (0, 5) or a JSON-decode failure, this
    check cannot determine disk_state for its gate, so it degrades to a
    single WARN item rather than falling back to the ungated disk_reasons
    dump — that fallback would silently reintroduce the exact mid-flight
    noise this check's narrowed gate exists to remove.

    Status is ALWAYS "warn" (items present) or "ok" (none), NEVER "fail" —
    a deliberate choice distinct from phase-corroboration's blocks/fail
    behavior, because a missing SUMMARY or an unreadable verdict is a
    record-hygiene gap, not contradictory evidence about what actually
    happened (D-01's "cairn never stops the flow", applied here to
    hygiene rather than correctness findings).
    """
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "cairn-status.py"), "--json",
         "--planning-dir", str(planning_dir)],
        capture_output=True, text=True, cwd=str(root))
    if proc.returncode not in (0, 5):
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        return {"id": "phase-artifacts", "status": "warn",
                "detail": f"cairn-status.py --json exited "
                          f"{proc.returncode}, phase-artifacts could not "
                          f"run: {first}",
                "items": []}
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        return {"id": "phase-artifacts", "status": "warn",
                "detail": "cairn-status.py --json returned invalid JSON, "
                          f"phase-artifacts could not run: {e}",
                "items": []}

    phases = data.get("phases") or []
    state_by_n = {p.get("number"): p.get("disk_state") for p in phases}
    verify_by_n = {p.get("number"): p.get("verify_status") for p in phases}

    items = []
    # First pass: a PLAN.md missing its SUMMARY.md, but ONLY for phases
    # that have already reached disk_state "verified" — the narrowed gate
    # this check exists to enforce (see docstring above).
    for n, reason in sorted((disk_reasons or {}).items()):
        if state_by_n.get(n) == "verified":
            items.append(f"phase {n}: {reason}")
    # Second pass: a "verified" phase whose NN-VERIFICATION.md carries no
    # readable 'status:' field.
    for n, ds in sorted(state_by_n.items()):
        if ds == "verified" and not verify_by_n.get(n):
            items.append(f"phase {n}: has a VERIFICATION.md but no "
                         f"readable 'status:' field in its frontmatter")

    detail = (f"{len(items)} phase(s) with an unexpected missing/unreadable "
              "artifact" if items
              else "every phase's artifacts are complete and readable")
    return {"id": "phase-artifacts", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


# --------------------------------------------------------------------------- #
# check 13 — external-ref backfill (CORR-08, D-11)
# --------------------------------------------------------------------------- #
def parse_plan_files_modified(path):
    """`files_modified:` paths from a PLAN.md's YAML frontmatter, the same
    lenient flow-list-or-block-list shape parse_plan_frontmatter() already
    reads for `beads:` — a sibling parser, so that function's (status,
    beads) return contract never changes."""
    lines = read_lines(path)
    if not lines or lines[0].strip() != "---":
        return []
    body = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    for i, line in enumerate(body):
        m = re.match(r"^files_modified\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1)
        if "[" in rest:
            inner = rest[rest.index("[") + 1:]
            if "]" in inner:
                inner = inner[:inner.index("]")]
            return [t.strip().strip("'\"") for t in inner.split(",")
                    if t.strip().strip("'\"")]
        files = []
        for cont in body[i + 1:]:
            mi = re.match(r"^\s*-\s*(.+?)\s*$", cont)
            if not mi:
                break
            files.append(mi.group(1).strip("'\""))
        return files
    return []


def phase_files_modified(planning_dir, n):
    """Every files_modified path across phase n's non-superseded plans,
    de-duplicated in first-seen order — the pathspec link_ref_candidate()
    narrows its git query to."""
    files = []
    for num, d in phase_dirs(planning_dir):
        if num != n:
            continue
        for f in sorted(d.glob("*-PLAN.md")):
            status, _ = parse_plan_frontmatter(f)
            if status == "superseded":
                continue
            files.extend(parse_plan_files_modified(f))
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def git_is_shallow(root):
    """True when root is a shallow git clone — verified live (STACK.md) to
    make -S/-G/--grep results silently WRONG at the boundary commit, not
    merely incomplete (D-08); check_external_ref must never trust a git
    match from one."""
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-shallow-repository"],
        capture_output=True, text=True)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def git_tracked_beads_exports(root):
    """Paths under .beads/ that git actually TRACKS and that look like an
    issue export, as repo-relative Path objects.

    `git ls-files` and not a directory listing, deliberately: the failure
    this feeds (check 22) was a 27 MB database sitting in .gitignore beside a
    13 MB backup directory that was ALSO ignored. Both exist on disk; neither
    survives a clone. Only what git carries can answer the question, so only
    git is asked.

    The suffix filter is JSONL because that is bd's export format
    (`bd export -o <path>`, default `.beads/issues.jsonl`), and the two
    names bd writes for other purposes are excluded by name rather than by
    pattern: `interactions.jsonl` is an audit trail of command invocations
    and `events.jsonl` is the event stream, and neither reconstructs an
    issue. Excluding them by name keeps a future export file included by
    default — the safer direction for a durability check.
    """
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--", ".beads"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    skip = {"interactions.jsonl", "events.jsonl"}
    out = []
    for line in proc.stdout.splitlines():
        p = line.strip()
        if not p or not p.endswith(".jsonl"):
            continue
        if Path(p).name in skip:
            continue
        out.append(Path(p))
    return out


def beads_export_promised(root):
    """True when bd's own config says an export is produced, None when it
    could not be asked.

    Read for ONE purpose: to catch a promise the artifact does not keep. It
    is never evidence of durability — `export.auto: true` proves an intent,
    and the file is what a clone actually gets. The check that uses it treats
    promise-without-artifact as a DISAGREEMENT BETWEEN TWO SOURCES, which is
    the thing this whole tool exists to name, and treats absence-without-
    promise as ordinary friction in a young repository.
    """
    proc = subprocess.run(["bd", "config", "get", "export.auto"],
                          cwd=str(root), capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    val = proc.stdout.strip().lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("false", "0", "no", "off"):
        return False
    return None


def beads_export_ids(root, paths):
    """(set of issue ids found across PATHS, list of paths with unreadable
    lines).

    A line that will not parse is REPORTED, never skipped in silence: a
    truncated export is exactly the shape of a recovery file that looks
    present and restores less than it claims, and this check exists because
    a file that was absent looked fine for weeks.
    """
    ids = set()
    unreadable = []
    for rel in paths:
        f = root / rel
        bad = False
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            unreadable.append(str(rel))
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                bad = True
                continue
            if isinstance(rec, dict) and rec.get("id"):
                ids.add(rec["id"])
        if bad:
            unreadable.append(str(rel))
    return ids, unreadable


def closed_window(closed_at, pad_days=2):
    """(since, until) ISO8601 strings +/-pad_days around a bd closed_at
    timestamp, or (None, None) when it is missing/unparsable."""
    if not closed_at:
        return None, None
    s = str(closed_at).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None, None
    delta = timedelta(days=pad_days)
    return (dt - delta).isoformat(), (dt + delta).isoformat()


def link_ref_candidate(root, planning_dir, iss):
    """The single unambiguous PR number for a closed issue, or None.

    Resolves the issue's phase from its phase-<N> label(s) (the lowest
    numbered one when it carries several), narrows a 'git log' query to
    that phase's files_modified (falling back to the phase directory path
    when no files_modified is known) within +/-2 days of the issue's
    closed_at, and scans matching commit subjects for a '(#N)' token.
    Exactly one distinct PR number among the matches is the candidate;
    zero or multiple distinct numbers is never a candidate — this never
    guesses (T-13-07: a crafted '(#N)' misattributing a PR is bounded to
    'nothing written', never a wrong link silently accepted).
    """
    nums = phase_nums(iss)
    if not nums:
        return None
    n = min(nums)
    since, until = closed_window(iss.get("closed_at"))
    if since is None:
        return None
    pathspec = phase_files_modified(planning_dir, n)
    if not pathspec:
        d = dict(phase_dirs(planning_dir)).get(n)
        if d is None:
            return None
        pathspec = [str(d.relative_to(root))]
    proc = subprocess.run(
        ["git", "-C", str(root), "log", f"--since={since}",
         f"--until={until}", "--format=%H|%s", "--", *pathspec],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    prs = set()
    for line in proc.stdout.splitlines():
        if "|" not in line:
            continue
        subject = line.split("|", 1)[1]
        m = PR_NUMBER.search(subject)
        if m:
            prs.add(int(m.group(1)))
    if len(prs) == 1:
        return next(iter(prs))
    return None


def check_external_ref(root, planning_dir, issues, do_write):
    """Check 12, id "external-ref" (CORR-08, D-11) — backfills the
    bd-issue-to-PR linkage on already-closed issues from this repo's own
    git history. See link_ref_candidate() for the exact match rule.

    Read-only by default: reports each unambiguous candidate as
    '<id> -> gh-N', writes nothing. do_write (--link-refs) writes 'bd
    update <id> --external-ref gh-N' for each candidate and itemizes what
    it linked — naturally idempotent, since an issue that already carries
    an external_ref is excluded from `lacking` up front, so a second run
    (a fresh process reading fresh bd state) has nothing left to
    (re)write.

    D-08: a shallow clone's git match can be silently WRONG at the
    boundary commit, not merely incomplete (verified live in STACK.md) —
    checked once before any query and reported as a single item rather
    than trusted.

    WARN only when an unambiguous, actionable candidate is waiting — never
    merely because closed issues predate the --external-ref convention.
    Per STACK.md, that is the expected, unremarkable state of this
    repo's entire history today; flagging it unconditionally would be
    exactly the vacuous-check failure mode this milestone exists to avoid.
    """
    if git_is_shallow(root):
        # PHASE 23 CONSIDERED PROMOTING THIS BRANCH TO not-applicable AND
        # REFUSED, on the record so nobody reopens it without the argument.
        # It reads like the new state ("cannot be trusted"), but the check
        # RAN — it still counts how many closed issues lack a ref, and only
        # the git evidence for PROPOSING a backfill is unavailable. And the
        # missing input has a one-line cure (git fetch --unshallow). Partial
        # execution plus a one-command fix is environment friction, which is
        # exactly the sentence `warn` exists to say.
        return {"id": "external-ref", "status": "warn",
                "detail": "shallow clone — git history cannot be trusted "
                          "for --link-refs (D-08); run against a full "
                          "clone (git fetch --unshallow)",
                "items": ["shallow clone: --link-refs skipped entirely "
                          "this run"]}

    closed = [i for i in issues if i.get("status") == "closed"]
    lacking = [i for i in closed
               if not str(i.get("external_ref") or "").strip()]
    candidates = []
    for iss in lacking:
        pr = link_ref_candidate(root, planning_dir, iss)
        if pr is not None:
            candidates.append((iss.get("id"), pr))

    linked = []
    if do_write:
        for iid, pr in candidates:
            proc = subprocess.run(
                ["bd", "-C", str(root), "update", iid, "--external-ref",
                 f"gh-{pr}"], capture_output=True, text=True)
            if proc.returncode == 0:
                linked.append(iid)

    remaining_lacking = len(lacking) - len(linked)
    remaining_candidates = len(candidates) - len(linked)
    items = [f"linked {iid} -> gh-{pr}" if iid in linked
             else f"{iid} -> gh-{pr}" for iid, pr in candidates]
    detail = (f"{remaining_lacking} closed issue(s) lack an external ref, "
              f"{remaining_candidates} have an unambiguous git match "
              f"(run --link-refs to backfill)")
    if linked:
        detail += f" — linked {len(linked)} via --link-refs"
    # Phase 23 evaluated and KEPT `ok`. Zero closed issues means the check
    # swept the closed set — which is empty — and there is nothing waiting to
    # be linked. It already refuses to warn merely because history predates
    # the convention, and the same reasoning covers the empty case.
    return {"id": "external-ref",
            "status": "warn" if remaining_candidates else "ok",
            "detail": detail, "items": items}


# --------------------------------------------------------------------------- #
# check 13 — lease-stale (LEASE-05)
# --------------------------------------------------------------------------- #
def check_lease_stale(root):
    """Check 13, id "lease-stale" (LEASE-05) — a stale phase lease reported
    with the same WARN-only discipline check 8 (claims-stale) already
    applies to a stale issue claim, one level up: shells to
    'cairn-lease.py status --all --json' (Plan 15-01), the same
    shell-out-to-a-sibling-script pattern check_maps_fresh() already uses
    for cairn-map.py --check and check_phase_corroboration() uses for
    cairn-status.py --json — no TTL/staleness math is re-derived here.

    Itemizes every phase whose lease is currently held AND stale (past the
    4h TTL cairn-lease.py enforces) by phase, holder, actor, acquired_at,
    heartbeat_at, and the reclaim path. Never FAILS: a stale lease is
    reclaimable — the next acquire takes it automatically, or a human runs
    'cairn-lease.sh release N' — exactly the "reclaimable, not a bug" case
    D-03/LEASE-04 describe, matching claims-stale's own never-fails
    posture exactly.

    A non-zero cairn-lease.py exit or unparsable JSON degrades to WARN
    with an explanatory detail rather than crashing the whole doctor run
    over this one check (same degrade shape as
    check_phase_corroboration()).
    """
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "cairn-lease.py"), "status",
             "--all", "--json", "--project-dir", str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"id": "lease-stale", "status": "warn",
                "detail": f"could not run cairn-lease.py: {exc}",
                "items": []}
    if proc.returncode != 0:
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        return {"id": "lease-stale", "status": "warn",
                "detail": f"cairn-lease.py status --all exited "
                          f"{proc.returncode}, lease staleness could not "
                          f"be computed: {first}",
                "items": []}
    try:
        entries = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        return {"id": "lease-stale", "status": "warn",
                "detail": "cairn-lease.py status --all returned invalid "
                          f"JSON, lease staleness could not be computed: "
                          f"{e}",
                "items": []}
    if not isinstance(entries, list):
        entries = []

    items = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("held") and entry.get("stale"):
            phase = entry.get("phase")
            # A bead lease (phase 47) has no phase: it is named by its bead.
            key = f"bead:{entry.get('bead')}" if phase is None else str(phase)
            what = f"bead {entry.get('bead')}" if phase is None else f"phase {phase}"
            taker = ("the next /cairn:implement takes it automatically"
                     if phase is None
                     else f"the next /cairn:work {phase} takes it automatically")
            items.append(
                f"{what}: held by {entry.get('holder')} (actor: "
                f"{entry.get('actor')}) since {entry.get('acquired_at')}, "
                f"last renewed {entry.get('heartbeat_at')} — reclaimable "
                f"— {taker}, or run cairn-lease.sh release {key} to clear "
                "it now")
    detail = (f"{len(items)} stale phase lease(s)" if items
              else "no stale phase leases")
    # Phase 23 evaluated and KEPT `ok`, and this is the cleanest example of
    # the line: the check looks for a STUCK lease. No lease registered means
    # it looked, there is none stuck, and there is nothing anyone would want
    # to do. Vacuously true with no action behind it is a real `ok`, not a
    # check that failed to run.
    return {"id": "lease-stale", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


# --------------------------------------------------------------------------- #
# check 15 — release-versions (REL-02)
# --------------------------------------------------------------------------- #
RELEASE_PLUGIN_MANIFEST = Path("cairn") / ".claude-plugin" / "plugin.json"


def check_release_versions(root):
    """Check 15, id "release-versions" (REL-02) — the plugin version's
    carriers must agree, verified by shelling out to cairn-release.py
    through the CAIRN_RELEASE env seam, the same
    shell-out-to-a-sibling-script pattern check_maps_fresh() uses for
    cairn-map.py --check and check_lease_stale() uses for cairn-lease.py.
    No manifest reading is re-derived here: cairn-release.py owns the three
    (different!) JSON key paths and the CHANGELOG heading, and this check
    only routes its verdict.

    A command nobody remembers to run would not have caught the third
    carrier. That is why this lives in the doctor at all:
    .claude-plugin/marketplace.json carries the version at
    `metadata.version` and drifted unnoticed across three releases while
    every human check said "the two files match".

    APPLICABILITY — the trap this check has to dodge. The doctor runs in
    USERS' repos, which have a .planning/ and a .beads/ but none of cairn's
    own plugin manifests. A naive version of this check would report
    `missing: cairn/.claude-plugin/plugin.json does not exist` and drive
    every user's doctor to exit 7 over a file that has no business being
    there. So it applies ONLY when cairn/.claude-plugin/plugin.json exists
    under the project root; everywhere else it reports `not-applicable` with
    scope `out-of-scope` (phase 23) — the word used to sit in the detail
    prose while the status said `ok`, and this is the same sentence in the
    field tools read. `out-of-scope`, not `no-input`: these manifests are
    cairn's own and will NEVER exist in a wired repo, so nothing is missing
    and the report stays complete. Still exit 0, for the reason the module
    docstring's exit-code table already gives: an absent input is friction,
    not a state inconsistency.

    Inside THIS repo a divergence is "fail", not "warn": it is an
    inconsistency that blocks a release, and only "fail" reaches exit 7.
    An unexpected cairn-release.py exit (anything but its documented 0/6)
    or unparsable JSON degrades to WARN rather than crashing the whole
    doctor run over this one check.
    """
    if not (root / RELEASE_PLUGIN_MANIFEST).is_file():
        return {"id": "release-versions", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": f"no {RELEASE_PLUGIN_MANIFEST} under this root "
                          "(the version carriers are cairn's own, not a "
                          "wired repo's)",
                "items": []}
    try:
        proc = subprocess.run(
            [sys.executable, CAIRN_RELEASE, "check", "--json",
             "--project-dir", str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"id": "release-versions", "status": "warn",
                "detail": f"could not run cairn-release.py: {exc}",
                "items": []}
    # 0 (every carrier agrees) and 6 (findings) are the two exit codes
    # cairn-release.py check --json is documented to pair with real output;
    # anything else is unexpected and degrades rather than failing.
    if proc.returncode not in (0, 6):
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        return {"id": "release-versions", "status": "warn",
                "detail": f"cairn-release.py check exited "
                          f"{proc.returncode}, version consistency could "
                          f"not be computed: {first}",
                "items": []}
    try:
        report = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        return {"id": "release-versions", "status": "warn",
                "detail": "cairn-release.py check returned invalid JSON, "
                          f"version consistency could not be computed: {e}",
                "items": []}

    findings = report.get("findings") or []
    if findings:
        return {"id": "release-versions", "status": "fail",
                "detail": f"{len(findings)} version carrier finding(s) — "
                          "run cairn-release.sh check",
                "items": list(findings)}
    version = report.get("version")
    tag = next((c for c in report.get("carriers") or []
                if c.get("name") == "tag"), {})
    tag_note = {"ok": f", git tag {tag.get('key')} present",
                "pending": f", git tag {tag.get('key')} pending"}.get(
                    tag.get("status"), "")
    return {"id": "release-versions", "status": "ok",
            "detail": f"every version carrier agrees on {version}"
                      f"{tag_note}",
            "items": []}


def check_test_parallel(root):
    """Check 16, id "test-parallel" (AUTO-04) — can this machine run the
    suite in parallel, and if not, what does that cost and what fixes it.

    The absence of GNU parallel is the kind of thing nobody discovers:
    nothing breaks, everything is slow. So it becomes a doctor check. But
    what it may NOT become is a doctor FAILURE — running the suite slowly is
    friction, not a state inconsistency, and spending exit 7 on friction
    trains everyone to ignore exit 7. This check never returns "fail".

    The verdict is ROUTED, not recomputed: cairn-test.py --check-env owns the
    knowledge of what `bats -j` actually requires (the parallel binary AND
    flock-or-shlock, both measured), and this check only turns its report
    into a status. Same shell-out-to-a-sibling-script shape check_maps_fresh
    uses for cairn-map.py, check_lease_stale for cairn-lease.py and
    check_release_versions for cairn-release.py — and the same reason: one
    file knows the rule, so the rule cannot drift into disagreeing with
    itself.

    APPLICABILITY, the same trap check_release_versions dodges. The doctor
    runs in USERS' repos, which have a .planning/ and a .beads/ and no reason
    on earth to run cairn's bats suite. Warning them about GNU parallel would
    be noise about a suite they do not have. So this check applies only where
    cairn's own plugin manifest is — the same marker, for the same reason.

    A machine with no bats at all says the suite cannot run here AT ALL, which
    is a different sentence from "it will run slowly" — and phase 23 gave that
    sentence its own status. 29-06 left it as `warn` with a note pointing here;
    it is now `not-applicable` / `no-input`. `no-input` and not `out-of-scope`,
    because the manifest guard below has ALREADY filtered: we are inside
    cairn's own tree, where the suite exists and should be runnable, so a
    missing tool is a gap someone can close, not a repo this check has no
    business running in. It therefore makes the report read INCOMPLETE — and
    still never touches the exit code.

    THE GUARD ITSELF is the other family: no cairn manifest means no cairn
    suite, permanently and correctly, so it is `out-of-scope` and leaves the
    report complete.
    """
    if not (root / RELEASE_PLUGIN_MANIFEST).is_file():
        return {"id": "test-parallel", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": f"no {RELEASE_PLUGIN_MANIFEST} under this root "
                          "(cairn's bats suite is cairn's own, not a wired "
                          "repo's)",
                "items": []}
    try:
        proc = subprocess.run(
            [sys.executable, CAIRN_TEST, "--check-env", "--project-dir",
             str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as e:
        return {"id": "test-parallel", "status": "warn",
                "detail": f"could not run cairn-test.py --check-env: {e}",
                "items": []}
    if proc.returncode != 0:
        return {"id": "test-parallel", "status": "warn",
                "detail": f"cairn-test.py --check-env exited "
                          f"{proc.returncode}: "
                          f"{proc.stderr.strip() or '(no stderr)'}",
                "items": []}
    try:
        data = json.loads(proc.stdout or "null")
    except json.JSONDecodeError as e:
        return {"id": "test-parallel", "status": "warn",
                "detail": f"cairn-test.py --check-env did not return valid "
                          f"JSON: {e}",
                "items": []}
    if not isinstance(data, dict):
        return {"id": "test-parallel", "status": "warn",
                "detail": "cairn-test.py --check-env returned no report",
                "items": []}

    if not data.get("bats"):
        return {"id": "test-parallel", "status": NOT_APPLICABLE,
                "scope": NA_NO_INPUT,
                "detail": "bats is not on PATH — the suite cannot run here "
                          "at all, so nothing about parallelism can be "
                          "concluded (brew install bats-core / "
                          "npm install -g bats)",
                "items": []}
    if data.get("can_parallelize"):
        return {"id": "test-parallel", "status": "ok",
                "detail": f"the suite can run in parallel "
                          f"(bats -j {data.get('jobs')}, from "
                          f"{data.get('jobs_source')})",
                "items": []}

    items = [f"{b.get('what')} — fix: {b.get('fix')}"
             for b in data.get("blockers") or []]
    items.append(f"cost of running serial: {data.get('measured_cost')}")
    return {"id": "test-parallel", "status": "warn",
            "detail": "the suite will run serial here — `bats -j` is missing "
                      "a prerequisite (never a doctor failure: this is "
                      "friction, not inconsistency)",
            "items": items}


# --------------------------------------------------------------------------- #
# check 17 — req-ledger (AUTO-07)
# --------------------------------------------------------------------------- #
# cairn-bookkeep.py reconcile's OWN exit-code contract, named rather than
# inlined. `reconcile` (read-only) exits 3 when it named at least one
# disagreement and 0 when it named none — cairn-bookkeep.py's own
# EXIT_DISAGREEMENT = 3, the same 3 cairn-reconcile.py:154 spends on a
# disagreement verdict and the same one cairn-map.py --check uses for "stale".
#
# THE ALLOWLIST IS (0, 3) AND NOT (0, 5), AND THE DIFFERENCE IS THE WHOLE
# CHECK. The neighbouring defensive shell-out, check_phase_corroboration(),
# allowlists (0, 5) because that is cairn-status.py's contract. Copied here
# unchanged, 3 — the ONLY verdict this check exists to report — would fall
# into the "tool unavailable" branch, that branch would return "warn", and
# the exit-code table above records that a warning never changes the exit
# code. The doctor would exit 0 against a ledger it had just been told
# disagrees, and a test asserting "the status is not ok" would stay green on
# the `warn`. Hence: every status assertion for this check is on the exact
# value, and every unavailability verdict below is "fail".
BOOKKEEP_EXIT_OK = 0
BOOKKEEP_EXIT_DISAGREEMENT = 3

# reconcile's disagreement vocabulary, split by what THIS check claims.
# Written out by name on purpose: a set built by exclusion ("everything that
# is not X") silently adopts whatever kind reconcile grows next, and this
# check would start failing repos over a rule nobody here reviewed.
#
# The requirement-ledger chain — AUTO-07's four links, plus the two siblings
# of the same derivation (a row that outlived its requirement; a requirement
# checkbox lagging its own complete phases). All are
# `cairn-bookkeep.sh reconcile --apply` territory, all FAIL.
REQ_LEDGER_CHAIN_KINDS = (
    "coverage-row-missing",          # link 1: active requirement -> table row
    "coverage-row-orphan",           # link 1, the other direction
    "footer-count-stale",            # link 2: the table -> the footer's claim
    "requirements-line-unreadable",  # link 3: the phase's Requirements line
    "plan-checkbox-stale",           # link 4: SUMMARY on disk -> plan checkbox
    "requirement-checkbox-stale",    # reconcile's derived 2, same chain
)

# "This repo has no coverage view at all" is not a broken ledger, it is no
# ledger. The doctor runs in USERS' repos, and a naive version of this check
# would drive every roadmap without a coverage table to exit 7 — the same
# trap check_release_versions() documents. Phase 23 landed, and this branch is
# `not-applicable` with scope `out-of-scope`.
#
# `out-of-scope`, not `no-input`, and the reason is right here in this
# comment: keeping no coverage view is a METHOD CHOICE a project is entitled
# to make, and most user repos make it. Calling it a gap would leave every one
# of them reading INCOMPLETE forever over a table they deliberately do not
# keep — a permanent false red where there used to be a permanent false green,
# which is the same defect mirrored rather than removed. The exit code does
# not move: the "0 = ok, or not applicable" semantics of the exit-code table
# stayed true through this phase; what changed is that "not applicable" now
# has a place of its own in the report instead of disguising itself as `ok`.
#
# ACCEPTED GAP, named rather than hidden: with no coverage view the plan
# checkbox link (link 4) goes unchecked too, because the check is refused as
# a whole. Splitting it per-link would let a repo with no ledger still be
# failed over unticked plan checkboxes, which is the user-repo trap again.
REQ_LEDGER_VOID_KIND = "coverage-view-missing"

# reconcile's own preconditions, checked here first so that its EXIT_USAGE
# (2) never arrives from this cause: it die()s when any of the three planning
# files is absent, and "this repo keeps no REQUIREMENTS.md" must read as "no
# ledger to check", not as "the ledger reader is broken".
REQ_LEDGER_SOURCES = ("ROADMAP.md", "REQUIREMENTS.md", "STATE.md")

# The command every finding routes to. A findings line that does not name
# the command that resolves it trains everyone to scroll past it.
REQ_LEDGER_FIX = "cairn-bookkeep.sh reconcile --apply"


def req_ledger_source(root, source):
    """A finding's file:line relative to the repo root when it sits under it
    — the report is read next to the repo, not next to /."""
    if not source:
        return ""
    text = str(source)
    prefix = f"{root}{os.sep}"
    return text[len(prefix):] if text.startswith(prefix) else text


def req_ledger_pair(value):
    """reconcile states the footer as TWO quantities ([active, mapped]).
    Rendered as 'A active requirement(s) / B coverage row(s)' when it is that
    pair, and verbatim otherwise — the shape belongs to cairn-bookkeep.py, so
    this reads it defensively instead of asserting it."""
    if isinstance(value, list) and len(value) == 2:
        return f"{value[0]} active requirement(s) / {value[1]} coverage row(s)"
    return repr(value)


def req_ledger_item(root, finding):
    """One reconcile disagreement rendered as one doctor item.

    Every line names its SUBJECT (the requirement id, the phase, the plan
    file, the footer) and the concrete values that disagree. "The ledger is
    inconsistent" routes nowhere; naming AUTO-05, or 29 against 35/33, is
    what makes the finding actionable — and an unknown kind still renders
    (found/expected verbatim) rather than vanishing.
    """
    kind = finding.get("kind") or "?"
    subject = finding.get("subject") or "?"
    found = finding.get("found")
    expected = finding.get("expected")
    extra = finding.get("detail")
    if not isinstance(extra, dict):
        extra = {}
    where = req_ledger_source(root, finding.get("source"))

    if kind == "coverage-row-missing":
        what = "active requirement with no row in the coverage table"
    elif kind == "coverage-row-orphan":
        what = ("a coverage table row for a requirement the requirements "
                "section no longer lists as active")
    elif kind == "footer-count-stale":
        what = (f"the footer reads {extra.get('raw')!r} — it claims "
                f"{req_ledger_pair(found)}, the ledger holds "
                f"{req_ledger_pair(expected)}")
    elif kind == "requirements-line-unreadable":
        what = (f"its '**Requirements**:' line does not yield the ids the "
                f"ledger assigns it — raw {extra.get('raw')!r}, parsed "
                f"{found}, signals {extra.get('signals')}")
    elif kind == "plan-checkbox-stale":
        what = (f"{extra.get('summary')} is on disk but the plan's ROADMAP "
                f"checkbox still reads {found!r}")
    elif kind == "requirement-checkbox-stale":
        what = (f"every phase carrying it ({extra.get('phases')}) is "
                f"complete but its checkbox still reads {found!r}")
    else:
        what = f"found {found!r}, expected {expected!r}"
    return f"{subject}: {what} [{kind}]" + (f" {where}" if where else "")


def req_ledger_unavailable(why):
    """The one verdict shape for "this check could not run".

    ALWAYS "fail", NEVER "warn" and never "ok". A doctor that approves
    because it could not check is the disease this whole milestone treats,
    and `warn` is a quiet way of approving: the exit-code table above states
    that a warning never changes the exit code, so a `warn` here leaves the
    doctor exiting 0 over a ledger nobody read (T-29-29 / T-29-29b).
    """
    return {"id": "req-ledger", "status": "fail",
            "detail": f"the requirement ledger could not be read: {why}",
            "items": []}


def check_response_language(root):
    """Check 18, id "response-language" (LANG-02) — the two homes of the one
    answer still agree.

    `/cairn:init` records the installation's answer in
    `.cairn/config.json:agents.response_language` (it must: at the moment it
    asks, `.planning/` does not exist and cairn is forbidden from creating
    it), and `cairn-config.py set` propagates it into
    `.planning/config.json:response_language` the moment that file exists —
    because THAT is the key GSD's own ~30 workflows read when they spawn their
    subagents. The propagation of a greenfield install therefore depends on
    one re-run of that command after the `/gsd:new-project` hand-off, and a
    step in prose is exactly the thing that gets skipped. This check is the
    net under it.

    WARN, never FAIL, and the reason is written rather than assumed: a
    disagreement breaks nothing mechanically. It makes half the subagents of a
    run answer in one language and half in another — which is precisely what
    nobody noticed last time, and precisely why it deserves a line in a health
    report instead of silence. Spending exit 7 on it would train people to
    ignore exit 7.

    Read-only. It never writes either file: the doctor reports, and
    `cairn-config.py set` is what writes.

    AND IT READS THE TWO FILES RAW, which is the one place this repository's
    usual "shell out to the script that owns the rule" would be wrong.
    `cairn-config.py get` returns the RESOLVED value — GSD's key when it is
    set, cairn's otherwise — so asking it would report a single, agreeing
    answer in exactly the situation this check exists to catch. The resolver
    hides the disagreement on purpose; the doctor's job is to see it. There is
    no second resolver here: nothing below decides which value wins, it only
    reports that two files say different things and which one governs.
    """
    cairn_path = root / ".cairn" / "config.json"
    planning_path = root / ".planning" / "config.json"

    def _read_json(path):
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    cairn_data = _read_json(cairn_path)
    cairn_value = None
    if isinstance(cairn_data, dict):
        agents = cairn_data.get("agents")
        if isinstance(agents, dict):
            candidate = agents.get("response_language")
            if isinstance(candidate, str) and candidate.strip():
                cairn_value = candidate

    if cairn_value is None:
        return {"id": "response-language", "status": "ok",
                "detail": "no installation answer recorded in "
                          ".cairn/config.json — nothing to keep in agreement",
                "items": []}

    planning_data = _read_json(planning_path)
    if planning_data is None:
        return {"id": "response-language", "status": "ok",
                "detail": f"'{cairn_value}' recorded; "
                          ".planning/config.json is absent or unreadable, so "
                          "there is nothing to propagate into yet",
                "items": []}

    planning_raw = planning_data.get("response_language")
    planning_value = (planning_raw
                      if isinstance(planning_raw, str) and planning_raw.strip()
                      else None)
    fix = (f"bash cairn/scripts/cairn-config.sh set "
           f"agents.response_language '{cairn_value}'")

    if planning_value is None:
        return {"id": "response-language", "status": "warn",
                "detail": f"'{cairn_value}' was chosen at install but never "
                          f"reached .planning/config.json:response_language, "
                          f"which is the key GSD's own workflows read when "
                          f"they spawn subagents",
                "items": [f"run: {fix}"]}

    if planning_value != cairn_value:
        return {"id": "response-language", "status": "warn",
                "detail": f"the two disagree: .planning/config.json says "
                          f"'{planning_value}', .cairn/config.json says "
                          f"'{cairn_value}'. GSD's key governs, so every "
                          f"subagent answers in '{planning_value}'",
                "items": [f"to make cairn's record agree: {fix}",
                          "to change the language for everything: "
                          "/gsd:config, which writes GSD's key"]}

    return {"id": "response-language", "status": "ok",
            "detail": f"'{cairn_value}' in both .cairn/config.json and "
                      f".planning/config.json — every spawned subagent "
                      f"answers in it",
            "items": []}


def archived_phase_numbers(planning_dir):
    """Phase numbers whose directory sits under .planning/milestones/<key>-
    phases/ — the on-disk evidence that the cycle that owned them closed.

    Same discipline as archived_milestones() one level up: nothing is inferred
    from position in a list, from recency, or from STATE.md. /gsd:complete-
    milestone moves the phase tree there when it closes a cycle, so the
    directory's location IS the fact.
    """
    out = set()
    try:
        entries = list((planning_dir / "milestones").iterdir())
    except OSError:
        return out
    for entry in entries:
        if not entry.is_dir() or not entry.name.endswith("-phases"):
            continue
        try:
            children = list(entry.iterdir())
        except OSError:
            continue
        for child in children:
            m = DIR_PREFIX.match(child.name)
            if child.is_dir() and m:
                out.add(int(m.group(1)))
    return out


def check_phase_landed(root, planning_dir, completed):
    """Check 19, id "phase-landed" (PR-04) — a phase the roadmap calls complete
    whose work never entered the control branch.

    Showing the information and not asking for it trains everybody not to look.
    MEASURED 2026-08-06, and it is why this check exists: this repository has
    ten roadmap-complete phases whose commits are not on `origin/main`
    (`git rev-list --count origin/main..HEAD` = 145), and the doctor exited 7
    without saying one word about any of them.

    THE LEDGER OF LANDING IS READ ONCE, BY INVOCATION, NEVER REIMPLEMENTED
    HERE. cairn-land.py owns every git read behind the question, through the
    CAIRN_LAND seam — the same shell-out-to-a-sibling shape check_maps_fresh()
    uses for cairn-map.py and check_req_ledger() for cairn-bookkeep.py. A
    second `git merge-base` in this file would be a second answer to one
    question, which is the family of defect that produced check 17.

    STATUS LADDER, and every rung is a deliberate value, never a negation:
      * a complete phase of an ARCHIVED milestone whose
        work never entered the control branch      -> "fail" (exit 7)
      * a complete phase of the OPEN cycle whose
        work has not entered it yet                -> "warn"
      * every complete phase has landed            -> "ok"
      * no control branch to compare against, or
        no complete phase at all                   -> "not-applicable",
                                                      scope "out-of-scope"
      * cairn-land.py could not be run or answered
        unparsably                                 -> "warn", never "fail"

    WHY THE OPEN CYCLE IS ONLY A WARN. Unpushed work is the normal state of
    anybody in the middle of a cycle — it is friction, not inconsistency — and
    spending exit 7 on friction is how 7 stops meaning anything. Same
    distinction plans 29-06 and 29-07 drew. The archived case is genuinely
    different: a cycle was CLOSED over work that is not on the control branch,
    and that is a claim the repository cannot support.

    WHY `unknown` RAISES NOTHING. A complete phase the local history cannot
    place (no commit touched its directory and no commit named it in a
    conventional-commit scope) is reported by name in `items`, prefixed with
    the word `unknown` and carrying its reason — and it does NOT move the
    status. MEASURED in this repository: phases 7 through 12 are archived from
    cycles that predate the scope convention and are attributable by neither
    source. Turning that into a warning would hand every long-lived repo a
    permanent finding about history nobody is going to rewrite, which is the
    false-red this doctor already refused once (phase 23). Silence about it
    would be the opposite defect, so it is named without being charged.

    WHERE THE COMPLETE PHASES COME FROM, AND WHY IT IS A UNION. `completed` is
    roadmap_completed_phases(), which reads the CURRENT .planning/ROADMAP.md —
    and MEASURED 2026-08-06, that file lists only the open cycle: nine phases
    here, none of the nineteen already archived. Reading it alone would make
    the `fail` rung unreachable by construction, because the phases it exists
    to catch are exactly the ones an archive removed from that file. So the
    universe is that set UNION the phase directories sitting under
    .planning/milestones/<key>-phases/, which are complete by construction —
    a cycle only archives when it closes.

    This check WRITES NOTHING. Every finding routes by name to /cairn:ship.
    """
    archived = archived_phase_numbers(planning_dir)
    delivered = set(completed) | archived
    if not delivered:
        return {"id": "phase-landed", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": "no phase is marked complete in ROADMAP.md and none "
                          "is archived under .planning/milestones/, so there "
                          "is no delivered work to look for on a control "
                          "branch",
                "items": []}
    try:
        proc = subprocess.run(
            [sys.executable, CAIRN_LAND, "report", "--json",
             "--project-dir", str(root), "--planning-dir", str(planning_dir)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as e:
        return {"id": "phase-landed", "status": "warn",
                "detail": f"could not run {Path(CAIRN_LAND).name}: {e} — "
                          "whether complete work reached the control branch "
                          "is unknown for this run",
                "items": []}
    if proc.returncode != 0:
        return {"id": "phase-landed", "status": "warn",
                "detail": f"{Path(CAIRN_LAND).name} report exited "
                          f"{proc.returncode}: "
                          f"{(proc.stderr or '').strip()[:200]}",
                "items": []}
    try:
        report = json.loads(proc.stdout or "null")
    except json.JSONDecodeError as e:
        report = None
        detail = str(e)
    if not isinstance(report, dict):
        return {"id": "phase-landed", "status": "warn",
                "detail": f"{Path(CAIRN_LAND).name} report --json did not "
                          "answer with an object — refusing to guess whether "
                          "complete work reached the control branch",
                "items": []}

    control = report.get("control") or {}
    branches = control.get("branches") or []
    if not branches:
        why = control.get("detail") or "no branch to compare against"
        return {"id": "phase-landed", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": f"no control branch could be resolved here ({why}),"
                          " so whether the work landed is a question this "
                          "repository cannot be asked",
                "items": []}

    rows = report.get("phases") or {}
    failures, warnings, unknowns = [], [], []
    for n in sorted(delivered):
        row = rows.get(str(n))
        if not isinstance(row, dict) or row.get("status") == "unknown":
            reason = ((row or {}).get("reason")
                      or report.get("reason") or "no-commits")
            unknowns.append(f"unknown :: phase {n} — {reason}: the local "
                            "history places no commit in this phase, so "
                            "whether its work landed cannot be answered here")
            continue
        if row.get("status") == "landed":
            continue
        missing = sorted(b for b, v in (row.get("branches") or {}).items()
                         if v != "landed")
        where = ", ".join(missing) or "the control branch"
        item = (f"phase {n} is complete and its {row.get('commits')} "
                f"commit(s) are not on {where}")
        if n in archived:
            failures.append(f"{item} — and its milestone is ARCHIVED: the "
                            "cycle closed over work the control branch does "
                            "not have")
        else:
            warnings.append(item)

    items = failures + warnings + unknowns
    census = (f"{len(delivered)} complete phase(s) ({len(archived)} archived),"
              f" control branch {', '.join(branches)} "
              f"({control.get('source')})")
    if failures:
        return {"id": "phase-landed", "status": "fail",
                "detail": f"{len(failures)} archived-milestone phase(s) never "
                          f"reached the control branch — {census}: run "
                          "/cairn:ship",
                "items": items}
    if warnings:
        return {"id": "phase-landed", "status": "warn",
                "detail": f"{len(warnings)} complete phase(s) have not "
                          f"reached the control branch yet — {census}: run "
                          "/cairn:ship",
                "items": items}
    return {"id": "phase-landed", "status": "ok",
            "detail": f"every complete phase the history can place is on the "
                      f"control branch — {census}",
            "items": items}


def check_plan_counters(planning_dir):
    """Check 20, id "plan-counters" (CairnGo-6bx, roadmap criterion 6) — a
    STATE.md claiming more plans done than it has.

    MEASURED 2026-08-06, right after the close of phase 22, and still true on
    2026-08-07 before the fix landed:

        .planning/STATE.md          on disk
        total_plans:     39         NN-MM-PLAN.md ...... 39
        completed_plans: 47   <---  NN-MM-SUMMARY.md ... 39
        percent:         91         NN-SUMMARY.md ....... 8     47 = 39 + 8

    WHY THIS CHECK COMPARES AND DOES NOT RECOMPUTE. The defect was never the
    arithmetic — it was that the writer (cairn-bookkeep.py's compute_counters)
    and the verifier (`cairn-bookkeep reconcile`) derive completed_plans with
    the SAME rule, so they agreed while printing 28 and 33 in one JSON object.
    A check that recounted the tree with that rule would agree too, in the very
    act of trying to catch it. So this one reads the two numbers exactly as
    written and asks a question neither glob can answer for itself: can more
    plans be finished than exist? `completed > total` is impossible by
    arithmetic, not by convention, and it needs to know nothing about how
    either number was produced.

    STATUS LADDER, every rung a deliberate value:
      * completed_plans > total_plans           -> "fail" (exit 7)
      * both readable and possible              -> "ok"
      * no .planning/ at all                    -> "not-applicable",
                                                   scope "out-of-scope"
      * .planning/ present but STATE.md missing
        the pair under `progress:`              -> "not-applicable",
                                                   scope "no-input"

    A missing key is NOT a failure: STATE.md's progress block is GSD's, and a
    repository that never grew one has nothing inconsistent about it. Saying
    `ok` over an absent input is the shape phase 23 removed from this file.

    THE TWO SCOPES ARE NOT INTERCHANGEABLE. A `.planning/` that IS here with
    the pair missing is a GAP — `no-input`, and `.ok` goes false. No
    `.planning/` at all means the question does not apply — `out-of-scope`.

    That first branch is DEFENSIVE, not reachable from the CLI, and it is
    written down here because a test asserting it would be vacuous: MEASURED
    2026-08-07, `cairn-doctor.sh --json` in a repo without `.planning/`
    returns `"checks": []` — main() short-circuits before the check list is
    built, so no check of any status is registered at all. The branch keeps
    the honest value for any future caller that reaches this function
    directly; nothing in the suite can prove it, and pretending otherwise
    would be a test that passes against every implementation.

    This check WRITES NOTHING. Its finding routes to `cairn-bookkeep.sh
    reconcile`, which owns the recount.
    """
    if planning_dir is None or not planning_dir.is_dir():
        return {"id": "plan-counters", "status": NOT_APPLICABLE,
                "scope": "out-of-scope",
                "detail": "no .planning/ directory — this repo has no plan "
                          "counters to be wrong about",
                "items": []}
    counters = state_plan_counters(planning_dir)
    total, done = counters["total_plans"], counters["completed_plans"]
    if total is None or done is None:
        missing = [k for k in ("total_plans", "completed_plans")
                   if counters[k] is None]
        return {"id": "plan-counters", "status": NOT_APPLICABLE,
                "scope": "no-input",
                "detail": ("STATE.md carries no " + " and no ".join(missing) +
                           " under progress:, so there is nothing to compare"),
                "items": []}
    if done > total:
        return {"id": "plan-counters", "status": "fail",
                "detail": (f"STATE.md claims {done} completed plans out of "
                           f"{total} — more plans finished than exist. Run "
                           f"cairn-bookkeep.sh reconcile --json to see which "
                           f"side of the pair the tree disagrees with"),
                "items": [f"progress.completed_plans {done} > "
                          f"progress.total_plans {total}"]}
    return {"id": "plan-counters", "status": "ok",
            "detail": f"STATE.md reports {done} of {total} plans completed",
            "items": []}


def check_issues_recoverable(root, issues):
    """Check 22, id "issues-recoverable" — whether the issue store has a way
    back that does not depend on this one machine.

    THE MEASUREMENT THAT OPENED THIS CHECK, 2026-08-07, on this repository:

        .beads/embeddeddolt   27 MB, in .gitignore, untracked
        .beads/issues.jsonl   DID NOT EXIST
        .beads/backup/        179 .darc files, 13 MB, ALSO in .gitignore
        refs/dolt on origin   0, out of 42 refs on the remote

    A clean clone received ZERO of the 176 issues. Every verdict, every
    `--reason` written on a close, the whole dependency graph and the
    milestone's requirements lived in one untracked directory on one laptop.

    AND THE REPOSITORY SAID OTHERWISE IN WRITING. CLAUDE.md:25 had been
    stating for weeks: "sync uses `refs/dolt/data` on your git remote;
    `.beads/issues.jsonl` is a passive export". Both mechanisms it names were
    absent. Nobody lied: bd ships `export.auto` disabled and commented out,
    so the file the sentence promises is never born until somebody enables
    it. That is the exact defect this project exists to remove — a surface
    answering with confidence about something it never checked — and it was
    living inside the surface that documents the project.

    WHY THE DOCTOR DID NOT CATCH IT, WHICH IS THE POINT. Twenty-two checks
    cross-examined the sources against each other: the roadmap against the
    issues, the coverage table against its footer, the two phase keys against
    one another. Not one asked whether the source itself survives the machine
    it sits on. Corroboration between sources says nothing about the
    durability of any of them.

    IT MEASURES THE ARTIFACT, NEVER THE CONFIGURATION. `export.auto` being
    true proves an intent, not a file; a tracked path proves a file, not its
    freshness. So the check reads what git actually carries and compares its
    record count against the live store. A config that claims to export and a
    file that is empty must not read as healthy, and reading the config would
    let it.

    STATUS LADDER, every rung a deliberate value:
      * store has issues, no tracked export         -> "fail" (exit 7)
      * tracked export missing ids the store has    -> "warn"
      * tracked export present and covering         -> "ok"
      * bd unavailable or store empty               -> "not-applicable",
                                                       scope "no-input"
      * no .beads/ at all                           -> "not-applicable",
                                                       scope "out-of-scope"

    WHY MISSING IDS ARE `warn` AND NOT `fail`. A stale export still recovers
    most of the history, and staleness is the ordinary state of a file
    written on an interval. Absence is different in kind: it is not a
    degraded recovery, it is none. Spending exit 7 on lag is how exit 7 stops
    meaning anything (phase 23's rule), and the failure this check was born
    from was absence.

    WHY `no-input` FOR AN EMPTY STORE AND `out-of-scope` FOR NO `.beads/`. A
    repository with beads wired and zero issues WILL have issues, and the
    export is a gap someone can close; a repository with no `.beads/` at all
    is a class of repo this question does not apply to.

    WHAT IT DOES NOT CLAIM, written here so no reader infers it: a green here
    means the ISSUE RECORDS have a way back, not the database. The JSONL is
    an issue export, not a Dolt backup — it carries no branches, no commit
    history, no working set. Full recovery still needs a Dolt remote, and on
    this repository that remote is configured and has produced zero refs.

    This check WRITES NOTHING.
    """
    beads = root / ".beads"
    if not beads.is_dir():
        return {"id": "issues-recoverable", "status": NOT_APPLICABLE,
                "scope": "out-of-scope",
                "detail": "no .beads/ directory — this repo has no issue "
                          "store to make recoverable",
                "items": []}
    if issues is None:
        return {"id": "issues-recoverable", "status": NOT_APPLICABLE,
                "scope": "no-input",
                "detail": "bd is unavailable, so the live store could not be "
                          "read and there is nothing to compare a tracked "
                          "export against",
                "items": []}
    live = {i.get("id") for i in issues if i.get("id")}
    if not live:
        return {"id": "issues-recoverable", "status": NOT_APPLICABLE,
                "scope": "no-input",
                "detail": "the issue store carries no issues yet, so there is "
                          "nothing whose recovery could be checked",
                "items": []}
    tracked = git_tracked_beads_exports(root)
    if not tracked:
        promised = beads_export_promised(root)
        common = (f"{len(live)} issue(s) live only on this machine — git "
                  f"tracks no export under .beads/, and the database itself "
                  f"is ignored, so a clean clone recovers NONE of them")
        if promised:
            return {"id": "issues-recoverable", "status": "fail",
                    "detail": (f"{common}. AND THE CONFIG SAYS OTHERWISE: "
                               f"export.auto is true, so bd is configured to "
                               f"produce the file a clone would restore from, "
                               f"and git carries none. Run `bd export --all "
                               f"-o .beads/issues.jsonl` and commit it; set "
                               f"git-add so it stays committed"),
                    "items": ["export.auto is true and no export is tracked"]}
        return {"id": "issues-recoverable", "status": "warn",
                "detail": (f"{common}. Enable bd's export (export.auto plus "
                           f"git-add in .beads/config.yaml), run `bd export "
                           f"--all -o .beads/issues.jsonl`, and commit the "
                           f"file"),
                "items": [f"{len(live)} issue(s) with no tracked export"]}
    exported, unreadable = beads_export_ids(root, tracked)
    missing = sorted(live - exported)
    if missing:
        shown = missing[:8]
        more = f" (+{len(missing) - len(shown)} more)" if len(missing) > len(shown) else ""
        return {"id": "issues-recoverable", "status": "warn",
                "detail": (f"the tracked export is behind the store by "
                           f"{len(missing)} issue(s) — a clone recovers "
                           f"{len(exported & live)} of {len(live)}. Re-run "
                           f"`bd export --all -o .beads/issues.jsonl` and "
                           f"commit it{more}"),
                "items": [f"absent from the export: {i}" for i in shown] +
                         ([f"unreadable line(s) in {p}" for p in unreadable]
                          if unreadable else [])}
    paths = ", ".join(sorted(str(p) for p in tracked))
    return {"id": "issues-recoverable", "status": "ok",
            "detail": (f"all {len(live)} issue(s) are recoverable from a "
                       f"clean clone via {paths} — issue records only, not a "
                       f"database backup"),
            "items": []}


EXPORT_SESSION = re.compile(
    r"claude\.ai/code|session_[A-Za-z0-9]{8,}|sess[\u00e3a]o\s+[a-f0-9]{8}"
    r"|\.claude/projects/")
EXPORT_HOME = re.compile(
    r"/(?:Users|home)/(?!x[/\"]|user[/\"]|you[/\"]|USERNAME|foo[/\"])"
    r"[A-Za-z0-9_.-]+/")
EXPORT_HOSTNAME = re.compile(r"\b[A-Za-z0-9][A-Za-z0-9-]{2,}\.local\b")
EXPORT_PROSE_FIELDS = ("title", "description", "notes", "close_reason",
                       "design", "acceptance")


def export_identity_findings(root, paths):
    """(prose, machine_written) — identity leaks in the TRACKED export.

    Split by WHO WROTE IT, because the two need different answers. `prose` is
    what a person or a tool typed into a title, description, note or close
    reason: it is scrubbable once, by editing the issue. `machine_written` is
    everything else in the record, and today that is one thing —
    `metadata.cairn.lease`, where cairn-lease.py records the holding
    worktree's absolute path and `socket.gethostname()` by design. Scrubbing
    that one is pointless: the next `lease acquire` writes it again.
    """
    prose, machine = [], []
    for rel in paths:
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            iid = rec.get("id") or "?"
            campos = {f: rec.get(f) for f in EXPORT_PROSE_FIELDS}
            texto = "\n".join(str(v) for v in campos.values() if v)
            resto = json.dumps({k: v for k, v in rec.items()
                                if k not in EXPORT_PROSE_FIELDS},
                               ensure_ascii=False)
            for rotulo, rx, alvo in (
                    ("session id", EXPORT_SESSION, texto),
                    ("home path", EXPORT_HOME, texto),
                    ("hostname", EXPORT_HOSTNAME, texto)):
                m = rx.search(alvo)
                if m:
                    prose.append(f"{iid}: {rotulo} in prose — {m.group(0)[:44]}")
            for rotulo, rx in (("session id", EXPORT_SESSION),
                               ("home path", EXPORT_HOME),
                               ("hostname", EXPORT_HOSTNAME)):
                m = rx.search(resto)
                if m:
                    machine.append(f"{iid}: {rotulo} written by a tool — "
                                   f"{m.group(0)[:44]}")
    return prose, machine


def check_export_identity(root, issues):
    """Check 23, id "export-identity" — whether the tracked export publishes
    the identity of a machine or a session.

    WHY IT EXISTS, and it is a consequence of check 22 rather than an
    independent idea. Before 2026-08-07 the bd store never left the laptop, so
    a hostname or an absolute path inside an issue was inert. Enabling the
    export to make the issues RECOVERABLE also made every issue field a
    published file, and the first record through the new door carried a
    session id — caught before the push, by hand. A door opened deliberately
    needs the guard built in the same move; this is that guard.

    SPLIT BY AUTHOR, because the two halves have different fixes:

      * PROSE (title, description, notes, close_reason, design, acceptance) is
        what somebody typed. It is scrubbable once, with `bd update`, and it
        stays scrubbed. -> "fail"
      * MACHINE-WRITTEN is the rest of the record, and today that means
        `metadata.cairn.lease`, where cairn-lease.py records the holder's
        absolute path and socket.gethostname() BY DESIGN. Scrubbing it is
        pointless: the next `lease acquire` writes it back. -> "warn", with
        the issue named, until the lease surface stores a derived id instead
        of a name (CairnGo-xclf). `holder` is read in ten places and
        asserted in five test files, so that is a contract change to a shipped
        surface, not a scrub, and it is tracked rather than done in passing.

    A session id is "fail" wherever it appears, including machine-written:
    the rule it breaks is absolute and no tool has a reason to write one.

    WHAT IS DELIBERATELY NOT A FINDING: `/Users/x/`, `/Users/user/`,
    `/Users/you/`, `/Users/foo/` and `$USERNAME`. Those are the placeholders
    this project already uses to make a point that REQUIRES an absolute path
    to make — the journal's partition key argues that the same path string on
    two machines collides, and rewriting it as `~` destroys the argument.

    This check WRITES NOTHING.
    """
    beads = root / ".beads"
    if not beads.is_dir():
        return {"id": "export-identity", "status": NOT_APPLICABLE,
                "scope": "out-of-scope",
                "detail": "no .beads/ directory — nothing is exported",
                "items": []}
    tracked = git_tracked_beads_exports(root)
    if not tracked:
        return {"id": "export-identity", "status": NOT_APPLICABLE,
                "scope": "no-input",
                "detail": ("git tracks no beads export, so nothing is "
                           "published — check 22 owns that gap"),
                "items": []}
    prose, machine = export_identity_findings(root, tracked)
    sessao_maquina = [m for m in machine if "session id" in m]
    duro = prose + sessao_maquina
    if duro:
        return {"id": "export-identity", "status": "fail",
                "detail": (f"the tracked export publishes identity in "
                           f"{len(duro)} place(s) — a clone, a fork and every "
                           f"mirror carry it. Scrub with `bd update <id> "
                           f"--description ...` and re-export"),
                "items": duro[:10]}
    if machine:
        return {"id": "export-identity", "status": "warn",
                "detail": (f"{len(machine)} identity value(s) in the export "
                           f"were written by a tool, not typed — scrubbing "
                           f"them is undone by the next run that writes them. "
                           f"The fix is at the source, in the surface that "
                           f"records the value"),
                "items": machine[:10]}
    return {"id": "export-identity", "status": "ok",
            "detail": "the tracked export names no machine and no session",
            "items": []}


def check_state_dialect(planning_dir):
    """Check 21, id "state-dialect" (CairnGo-ctr, AUTO-10, roadmap criterion
    5) — the two phase keys of STATE.md naming two different phases.

    WHY THIS CHECK IS PART OF THE DECISION AND NOT A NICE-TO-HAVE. MEASURED
    2026-08-05: cairn-bookkeep wrote `current_phase` and `grep -rn
    current_phase cairn/` found ZERO readers, while five surfaces read
    `active_phase` (cairn-status.py, cairn-doctor.py, cairn-lease.py,
    cairn-migrate.py, hooks/session-start.sh). The owner's decision
    (2026-08-06) is to write BOTH, additively — and its stated cost is a
    duplicated key. Two keys that must agree and that nobody compares is the
    defect this cycle measured FOUR separate times (the coverage footer
    against its table, req-issue against req-ledger, completed_plans against
    total_plans, two hand-written numbers inside one document). Writing the
    pair without comparing the pair would have created the fifth case in the
    act of fixing the fourth, so the comparison ships with the duplication.

    IT COMPARES AND NEVER DERIVES. Neither number is recomputed from the
    roadmap or the phase tree: the values are read exactly as written and
    asked the one question neither key can answer about itself — do the two
    name the same phase? Recomputing would reproduce this phase's underlying
    defect (a writer and a verifier sharing a rule and therefore agreeing)
    inside the check written to catch it.

    STATUS LADDER, every rung a deliberate value:
      * both keys present, different phases  -> "fail" (exit 7)
      * both keys present, same phase        -> "ok"
      * fewer than two keys readable         -> "not-applicable",
                                                scope "out-of-scope"
      * no .planning/ at all                 -> "not-applicable",
                                                scope "out-of-scope"

    WHY ONE KEY IS out-of-scope AND NOT no-input, which is the assignment
    that had to be argued rather than measured (the docstring's rule at the
    top of this file: family is a written decision). A file carrying one key
    HAS NO DIALECT DISAGREEMENT TO HAVE — speaking one dialect is literally
    the state AUTO-10 is named after. And the absence of `active_phase` is
    ALREADY named as `no-input` by check 8, claims-stale; naming it here too
    would count one gap twice and, worse, would drop `.ok` to false in every
    GSD repository that has never run cairn-bookkeep — a permanent false red,
    which is phase 23's defect mirrored (D-07: no fix changes the verdict of
    a path that is legitimately green today).

    This check WRITES NOTHING. Its finding routes to `cairn-bookkeep.sh close
    <N> --apply`, which owns both keys and writes them together.
    """
    if planning_dir is None or not planning_dir.is_dir():
        return {"id": "state-dialect", "status": NOT_APPLICABLE,
                "scope": "out-of-scope",
                "detail": "no .planning/ directory — this repo has no STATE.md "
                          "to speak two dialects in",
                "items": []}
    keys = state_phase_dialect(planning_dir)
    current, active = keys["current_phase"], keys["active_phase"]
    if current is None or active is None:
        present = [k for k in ("current_phase", "active_phase")
                   if keys[k] is not None]
        carries = ("carries only " + present[0]) if present else \
            "carries neither current_phase nor active_phase"
        return {"id": "state-dialect", "status": NOT_APPLICABLE,
                "scope": "out-of-scope",
                "detail": (f"STATE.md {carries}, so there is no second "
                           f"dialect for it to disagree with"),
                "items": []}
    if current != active:
        return {"id": "state-dialect", "status": "fail",
                "detail": (f"STATE.md's two phase keys name two different "
                           f"phases: current_phase {current}, active_phase "
                           f"{active}. Every cairn surface reads "
                           f"active_phase and GSD writes current_phase, so "
                           f"the lease, the board and this report are "
                           f"reading a different phase than GSD is. Run "
                           f"cairn-bookkeep.sh close <N> --apply, which "
                           f"writes both"),
                "items": [f"current_phase {current} != active_phase {active}"]}
    return {"id": "state-dialect", "status": "ok",
            "detail": f"STATE.md's two phase keys agree on phase {current}",
            "items": []}


def check_req_ledger(root, planning_dir):
    """Check 17, id "req-ledger" (AUTO-07) — the chain nobody was validating:
    an active requirement has a row in the coverage table, the table's row
    count is the number the footer claims, each phase's '**Requirements**:'
    line actually yields its ids, and a plan whose SUMMARY is on disk has its
    ROADMAP checkbox ticked.

    Measured 2026-08-04 in this repository, and it is why the check exists:
    35 active requirements, 33 coverage rows (AUTO-05 and AUTO-06 have none),
    a footer still claiming '29 requisitos, 29 mapeados.', and check 1
    (req-issue) reporting `ok :: 29 requirement(s) mapped to issues` because
    ROADMAP.md:400 reads '**Requirements**: AUTO-01 … AUTO-08' and an
    ellipsis is prose, not a separator. Three numbers for one quantity, two
    of them wrong from independent causes that happened to meet at 29, both
    wearing a green check, for days, with nothing to say so.

    WHERE THIS CHECK STOPS AND check_req_issue() STARTS. Check 1 goes
    requirement -> bd issue, and it can only count the ids it manages to READ
    off a phase's requirements line — that limit is precisely what produced
    its 29. This check covers that limit: requirement -> coverage row ->
    footer claim, plus the legibility of the line check 1 reads and the plan
    checkboxes of the phase.

    THE LEDGER IS READ ONCE, BY INVOCATION, NEVER REIMPLEMENTED HERE.
    cairn-bookkeep.py's `reconcile` owns that reading; a second parser in the
    doctor would be a fifth number for the same quantity, which is the defect
    with one more surface (T-29-31). Same shell-out-to-a-sibling-script shape
    check_maps_fresh() uses for cairn-map.py and check_release_versions() for
    cairn-release.py, through the CAIRN_BOOKKEEP seam.

    STATUS LADDER, and every rung is a deliberate value, never a negation:
      * a broken link in the requirement ledger    -> "fail" (exit 7)
      * only findings outside this check's remit
        (STATE.md's counters and narrative)        -> "warn", surfaced and
                                                      routed, never exit 7
      * no REQUIREMENTS.md, or no coverage view
        in this repo at all                        -> "not-applicable",
                                                      scope "out-of-scope"
                                                      (phase 23; it used to
                                                      be "ok" with the words
                                                      in the prose)
      * the ledger could not be READ (script gone,
        unexpected exit, unparsable JSON)          -> "fail", never "warn"

    This check WRITES NOTHING. Every finding routes by name to
    `cairn-bookkeep.sh reconcile --apply`, where the writing lives behind a
    flag that says so.
    """
    absent = [name for name in REQ_LEDGER_SOURCES
              if not (planning_dir / name).is_file()]
    if absent:
        # Same family and same reason as the coverage-view branch below: a
        # repo that keeps no REQUIREMENTS.md keeps no ledger, on purpose.
        # v1.7: a classificacao ja era out-of-scope e continua sendo — o que
        # muda e' a frase. Este check confere a consistencia INTERNA de um
        # ledger em markdown (a tabela de cobertura contra o rodape que diz
        # quantas linhas ela tem, a linha `**Requirements**:` contra os ids
        # que o ledger atribui). Sem documento nao ha inconsistencia interna
        # possivel: o requisito e' o bead, e um bead nao discorda de si mesmo.
        return {"id": "req-ledger", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": "out of scope — the requirement ledger was a "
                          "markdown cross-reference; the requirement is the "
                          "bead now, and a bead cannot disagree with itself "
                          f"(no {', '.join(absent)} to cross-check)",
                "items": []}
    try:
        proc = subprocess.run(
            [sys.executable, CAIRN_BOOKKEEP, "reconcile", "--json",
             "--planning-dir", str(planning_dir)],
            capture_output=True, text=True, cwd=str(root))
    except (OSError, subprocess.SubprocessError) as exc:
        return req_ledger_unavailable(f"could not run cairn-bookkeep.py: "
                                      f"{exc}")
    if proc.returncode not in (BOOKKEEP_EXIT_OK, BOOKKEEP_EXIT_DISAGREEMENT):
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        return req_ledger_unavailable(
            f"cairn-bookkeep.py reconcile --json exited {proc.returncode} "
            f"(expected {BOOKKEEP_EXIT_OK} or "
            f"{BOOKKEEP_EXIT_DISAGREEMENT}): {first}")
    try:
        report = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return req_ledger_unavailable(
            f"cairn-bookkeep.py reconcile --json returned invalid JSON: "
            f"{exc}")
    if not isinstance(report, dict):
        return req_ledger_unavailable(
            "cairn-bookkeep.py reconcile --json returned no report")

    findings = report.get("disagreements") or []
    if any(f.get("kind") == REQ_LEDGER_VOID_KIND for f in findings):
        return {"id": "req-ledger", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": "this roadmap has no coverage "
                          "view (no '## Cobertura' table in ROADMAP.md and "
                          "no '## Traceability' table in REQUIREMENTS.md), "
                          "so there is no requirement ledger to cross-check",
                "items": []}

    reqs = report.get("requirements") or {}
    active = reqs.get("active") or []
    excluded = (reqs.get("deferred") or []) + (reqs.get("out_of_scope") or [])
    rows = (report.get("coverage") or {}).get("rows")
    census = (f"{len(active)} active requirement(s) against {rows} coverage "
              f"row(s), {len(excluded)} excluded by rule (deferred / out of "
              f"scope)")

    broken = [f for f in findings if f.get("kind") in REQ_LEDGER_CHAIN_KINDS]
    aside = [f for f in findings if f.get("kind") not in REQ_LEDGER_CHAIN_KINDS]
    items = [req_ledger_item(root, f) for f in broken]
    items += [f"{req_ledger_item(root, f)} — outside req-ledger's own links, "
              f"reported not counted" for f in aside]

    if broken:
        return {"id": "req-ledger", "status": "fail",
                "detail": f"{len(broken)} broken link(s) in the requirement "
                          f"ledger — {census} — run {REQ_LEDGER_FIX}",
                "items": items}
    if aside:
        return {"id": "req-ledger", "status": "warn",
                "detail": f"every requirement-ledger link agrees — {census} "
                          f"— but reconcile names {len(aside)} disagreement(s"
                          f") outside this check's links: run "
                          f"{REQ_LEDGER_FIX}",
                "items": items}
    return {"id": "req-ledger", "status": "ok",
            "detail": f"every requirement-ledger link agrees — {census}",
            "items": []}


# --------------------------------------------------------------------------- #
# --apply-reconciliation (ESC-03, Phase 17 Plan 3) — the human-invoked,
# separate apply command for a verified semantic-escalation reconciliation
# proposal. See the module docstring's own --apply-reconciliation entry for
# the full refusal-path rationale.
# --------------------------------------------------------------------------- #
RECONCILE_SCRIPT = SCRIPTS_DIR / "cairn-reconcile.py"
RECONCILE_ACTION_VOCAB = ("bd_close", "bd_reopen", "manual_review")


def run_apply_reconciliation(root, n, issues, as_json):
    """--apply-reconciliation N — reads .cairn/conflicts.json (written by
    /cairn:reconcile's own deterministic step, Plan 17-02), re-verifies it
    is STILL trustworthy at apply-time (never trusting anything about the
    proposal's own self-description), enumerates every change it is about
    to make, and only then executes the closed bd_close/bd_reopen action
    vocabulary. This is the ONLY place in the whole phase 17 pipeline where
    a real bd write happens, and it always runs because a human explicitly
    asked it to — never automatically.

    Fail-closed refusal paths, each refusing the WHOLE apply (never a
    per-claim partial result) — a proposal is only ever as trustworthy as
    its LAST verification, and time may have passed since /cairn:reconcile
    wrote it:
      1. no .cairn/conflicts.json for phase N, or its own 'phase' field
         does not match N -> EXIT_USAGE, nothing written.
      2. phase N's corroboration verdict is no longer "conflict", re-read
         via a REAL 'cairn-reconcile.py collect N --json' run at
         apply-time -> EXIT_OK, nothing to apply, not a failure.
      3. the freshly re-collected evidence_hash no longer matches the
         proposal's own stored one (D-04's cache key re-validated) ->
         EXIT_FAILED.
      4. any citation fails a real 'cairn-reconcile.py verify N' run
         (D-03) -> EXIT_FAILED.
      5. any recommended_action.type falls outside the closed
         {bd_close, bd_reopen, manual_review} vocabulary -> EXIT_FAILED,
         checked over EVERY claim in one pre-flight pass, before anything
         is even enumerated.
      6. any bd_close/bd_reopen claim's recommended_action.issue names a bd
         id carrying no phase-N label (issue provenance — correct
         citations elsewhere in the same proposal never excuse a claim
         that targets an unrelated issue) -> EXIT_FAILED, checked in the
         SAME pre-flight pass as 5, also before any enumeration prints.

    Only once every one of those passes does anything print: EVERY claim
    is enumerated (statement, recommended_action, what will happen —
    manual_review claims listed as "skipped") BEFORE the first bd
    subprocess call ever runs — the operator sees the full plan while it
    can still be stopped. bd_close/bd_reopen claims are then applied one
    at a time; a close/reopen bd itself refuses is reported by id and
    reason and fails the run (EXIT_FAILED) — never silent, the same
    "asked for it and did not get it" discipline
    check_phase_complete_open's close_failures already applies one level
    up.
    """
    proposal_path = root / ".cairn" / "conflicts.json"
    proposal = None
    if proposal_path.is_file():
        try:
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            proposal = None
    if not isinstance(proposal, dict) or proposal.get("phase") != n:
        die(f"no proposal for phase {n} — run /cairn:reconcile {n} first",
            EXIT_USAGE)

    # Step 2 (freshness, re-validating D-04's cache key at apply-time): a
    # REAL, current 'collect' run — the tree may have moved between
    # proposal generation and this invocation, so the proposal's own
    # evidence_hash is never trusted on its own say-so.
    proc = subprocess.run(
        [sys.executable, str(RECONCILE_SCRIPT), "collect", str(n), "--json",
         "--project-dir", str(root)],
        capture_output=True, text=True, cwd=str(root))
    if proc.returncode == 3:  # cairn-reconcile.py's EXIT_NOT_CONFLICTED
        msg = f"phase {n} is no longer in conflict; this proposal is moot"
        if as_json:
            print(json.dumps({"phase": n, "applied": False,
                              "reason": "not_conflicted", "detail": msg}))
        else:
            print(f"[cairn-doctor] {msg}")
        sys.exit(EXIT_OK)
    if proc.returncode != 0:
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        die(f"could not re-collect evidence for phase {n}: {first}",
            EXIT_FAILED)
    try:
        fresh = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        die(f"could not re-collect evidence for phase {n}: cairn-reconcile "
            f"collect returned invalid JSON: {e}", EXIT_FAILED)
    if fresh.get("evidence_hash") != proposal.get("evidence_hash"):
        die("proposal is stale (evidence has changed since it was "
            f"generated) — re-run /cairn:reconcile {n}", EXIT_FAILED)

    # Step 3 (citation re-check, D-03): a single bad citation invalidates
    # the WHOLE proposal, never per-claim partial credit.
    vproc = subprocess.run(
        [sys.executable, str(RECONCILE_SCRIPT), "verify", str(n),
         "--project-dir", str(root)],
        capture_output=True, text=True, cwd=str(root))
    if vproc.returncode != 0:
        text = (vproc.stdout.strip() or vproc.stderr.strip()
                or "(no output)")
        die(f"proposal failed citation verification: {text}", EXIT_FAILED)

    claims = proposal.get("claims") or []

    # Step 4 (pre-flight, BEFORE any enumeration is even printed): the
    # closed action vocabulary AND issue provenance, checked over EVERY
    # claim. Either failure refuses the ENTIRE apply, fail-closed, the same
    # posture as a stale hash or a bad citation above — a rejected
    # proposal never gets as far as looking plausible on screen.
    phase_n_ids = {iss.get("id") for iss in issues if n in phase_nums(iss)}
    for claim in claims:
        action = claim.get("recommended_action") or {}
        atype = action.get("type")
        if atype not in RECONCILE_ACTION_VOCAB:
            die("proposal names an unrecognized recommended_action.type "
                f"{atype!r} — refusing the whole apply (closed vocabulary: "
                "bd_close, bd_reopen, manual_review)", EXIT_FAILED)
        if atype in ("bd_close", "bd_reopen"):
            iid = action.get("issue")
            if iid not in phase_n_ids:
                die(f"proposal's claim targets {iid!r}, which carries no "
                    f"phase-{n} label — refusing the whole apply "
                    "(issue-provenance check: correct citations elsewhere "
                    "in the proposal do not excuse a claim targeting an "
                    "unrelated issue)", EXIT_FAILED)

    # Step 5 (enumerate): the FULL plan, printed before anything executes.
    header = (f"[cairn-doctor] apply-reconciliation: phase {n} — "
              f"{len(claims)} claim(s)")
    enum_lines = [header]
    for i, claim in enumerate(claims, 1):
        action = claim.get("recommended_action") or {}
        atype = action.get("type")
        stmt = claim.get("statement", "")
        if atype == "manual_review":
            what = "skipped (manual review, no automated action)"
        elif atype == "bd_close":
            what = f"will close {action.get('issue')}"
        else:
            what = f"will reopen {action.get('issue')}"
        enum_lines.append(f"  {i}. {stmt} -> {what}")
    if not as_json:
        for line in enum_lines:
            print(line)

    # Step 6 (apply): only bd_close/bd_reopen ever touch bd — manual_review
    # was already enumerated above and is never executed.
    results = []
    any_refused = False
    for claim in claims:
        action = claim.get("recommended_action") or {}
        atype = action.get("type")
        iid = action.get("issue")
        stmt = claim.get("statement", "")
        if atype == "manual_review":
            results.append({"statement": stmt, "issue": iid, "type": atype,
                            "outcome": "skipped-manual-review"})
            continue
        if atype == "bd_close":
            reason = (action.get("reason") or action.get("note")
                      or f"cairn-doctor: apply-reconciliation phase {n}")
            cmd = ["bd", "-C", str(root), "close", iid, "--reason", reason]
        else:  # bd_reopen
            cmd = ["bd", "-C", str(root), "update", iid, "--status", "open",
                   "--assignee", ""]
        bproc = subprocess.run(cmd, capture_output=True, text=True)
        if bproc.returncode == 0:
            results.append({"statement": stmt, "issue": iid, "type": atype,
                            "outcome": "applied"})
            verb = "closed" if atype == "bd_close" else "reopened"
            if not as_json:
                print(f"[cairn-doctor] {verb} {iid} — applied via "
                      "--apply-reconciliation")
        else:
            any_refused = True
            why = (bproc.stderr.strip() or bproc.stdout.strip()
                   or f"bd exited {bproc.returncode}")
            results.append({"statement": stmt, "issue": iid, "type": atype,
                            "outcome": "refused-by-bd", "detail": why})
            if not as_json:
                print(f"[cairn-doctor] {iid}: {atype} refused by bd — {why}")

    n_applied = sum(1 for r in results if r["outcome"] == "applied")
    n_skipped = sum(1 for r in results
                    if r["outcome"] == "skipped-manual-review")
    n_refused = sum(1 for r in results if r["outcome"] == "refused-by-bd")
    if as_json:
        print(json.dumps({"phase": n, "applied": not any_refused,
                          "claims": len(claims), "applied_n": n_applied,
                          "skipped_n": n_skipped, "refused_n": n_refused,
                          "results": results}))
    else:
        print(f"[cairn-doctor] apply-reconciliation phase {n}: "
              f"{n_applied} applied, {n_skipped} skipped (manual review), "
              f"{n_refused} refused by bd")
    sys.exit(EXIT_FAILED if any_refused else EXIT_OK)


# --------------------------------------------------------------------------- #
# output + main
# --------------------------------------------------------------------------- #
def migrate_detect_state(root):
    """Estado do classificador de cairn-migrate.py, ou None quando indisponivel.

    REUSO DELIBERADO, e a alternativa foi medida antes de ser recusada:
    cairn-migrate.py `detect` JA classifica esta situacao como estado A
    (".planning present, .beads absent -> GSD-only backfill"). Escrever um
    segundo classificador aqui criaria duas definicoes de "projeto por
    migrar" que divergiriam no primeiro caso de borda. O doctor PERGUNTA a
    quem ja sabe responder.
    """
    script = Path(__file__).resolve().parent / "cairn-migrate.py"
    if not script.is_file():
        return None
    proc = subprocess.run([sys.executable, str(script), "detect",
                           "--project-dir", str(root), "--json"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout).get("state")
    except ValueError:
        return None


def check_gsd_unmigrated(root, planning_dir):
    """Um GSD que ainda nao foi migrado — ACHADO com rota, nao residuo.

    ESTA E' A LEITURA DE `.planning/` QUE O MILESTONE v1.7 PRESERVA, e a
    distincao que a preserva e' esta:

        ler .planning/ para MIGRAR  !=  ler .planning/ como VERDADE

    As duas frases terminais que governam o diretorio, e que ficam aqui no
    codigo de proposito — nao so num registro de sumario — porque e' o que
    separa "o doctor le markdown" (regressao) de "o doctor reconhece um
    projeto por migrar" (feature):

        (1) ANTES de migrar, .planning/ e' lido UMA vez, como ENTRADA da migracao.
            E' o que esta funcao faz, e o unico motivo pelo qual ela abre o
            diretorio.
        (2) DEPOIS de migrado, .planning/ nao e' lido nem escrito. Nenhuma
            checagem deste arquivo o consulta como fonte de estado, e o
            caminho para ca deixa de ser alcancado no instante em que
            `.beads/` existe.

    Um leitor futuro que encontre esta leitura sem a doutrina ao lado vai
    conclui-la residuo e apaga-la — e apagar isto deixa sem rota exatamente
    a pessoa que o cairn mais quer receber: a que chega vinda do GSD, com o
    `.planning/` cheio e nada mais.

    O INVENTARIO E' CONTAGEM, NAO INTERPRETACAO. Conta fases, planos e
    sumarios para dizer o TAMANHO do que ha para migrar. Nao le conteudo,
    nao infere progresso, nao decide o que esta completo — isso e' trabalho
    de `cairn-migrate.py plan`, que e' quem tem os parsers e o handshake de
    plano. Aqui a pergunta e' so "ha um GSD aqui, e quao grande e' ele".
    """
    phases = sorted(p for p in (planning_dir / "phases").glob("*")
                    if p.is_dir()) if (planning_dir / "phases").is_dir() else []
    plans = sorted(planning_dir.rglob("*PLAN.md"))
    summaries = sorted(planning_dir.rglob("*SUMMARY.md"))
    docs = [name for name in ("ROADMAP.md", "REQUIREMENTS.md", "STATE.md",
                              "PROJECT.md")
            if (planning_dir / name).is_file()]

    items = []
    if phases:
        items.append(f"{len(phases)} phase director"
                     f"{'y' if len(phases) == 1 else 'ies'} under "
                     f".planning/phases/")
    if plans:
        items.append(f"{len(plans)} PLAN document"
                     f"{'' if len(plans) == 1 else 's'}")
    if summaries:
        items.append(f"{len(summaries)} SUMMARY document"
                     f"{'' if len(summaries) == 1 else 's'}")
    if docs:
        items.append("planning documents: " + ", ".join(docs))
    if not items:
        items.append(".planning/ exists but carries no phase, plan or "
                     "planning document yet")

    state = migrate_detect_state(root)
    return {
        "id": "gsd-unmigrated",
        "status": "warn",
        "state": state,
        "detail": (
            "this repo carries a GSD that has not been migrated to cairn "
            "(.planning/ present, .beads/ absent"
            + (f"; cairn-migrate detect says state {state}" if state else "")
            + "). Nothing here is broken — the work simply has not moved into "
            "the tracker yet. Migrate it with `/cairn:migrate`, which reads "
            "these documents ONCE and turns phases, plans, requirements and "
            "summaries into bd records; after that .planning/ is neither read "
            "nor written."),
        "items": items,
    }


def emit(as_json, summary, human_lines):
    if as_json:
        print(json.dumps(summary))
    else:
        for line in human_lines:
            print(line)


def main():
    parser = argparse.ArgumentParser(
        prog="cairn-doctor",
        description="Consistency doctor for a repo wired with GSD + beads.")
    parser.add_argument("--project-dir", metavar="DIR",
                        help="repo root (default: $CLAUDE_PROJECT_DIR or cwd)")
    parser.add_argument("--json", action="store_true",
                        help="print a machine summary instead of the report")
    parser.add_argument("--fix-labels", action="store_true",
                        help="repair phase-* issues lacking an m-* label via "
                             "cairn-relabel pair --milestone <active>")
    parser.add_argument("--close-completed", action="store_true",
                        help="bulk-close non-closed issues whose phase-<N> "
                             "labels ALL point at phases ROADMAP.md marks "
                             "complete (bd close --reason), before the "
                             "checks run; a cross-phase issue with an open "
                             "phase is left alone")
    parser.add_argument("--link-refs", action="store_true",
                        help="backfill closed issues lacking bd's "
                             "external_ref field from an unambiguous git "
                             "match (bd update --external-ref), read-only "
                             "without this flag")
    parser.add_argument("--apply-reconciliation", metavar="N", type=int,
                        default=None,
                        help="apply a verified semantic-escalation "
                             "reconciliation proposal for phase N "
                             "(.cairn/conflicts.json): re-verifies "
                             "freshness and citations, enumerates every "
                             "change before making any of them, then "
                             "executes only the closed bd_close/bd_reopen "
                             "vocabulary — refuses the whole apply on any "
                             "staleness, bad citation, unrecognized action "
                             "type, or an issue lacking a phase-N label")
    args = parser.parse_args()

    root = Path(args.project_dir
                or os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    planning_dir = root / ".planning"
    has_planning = planning_dir.is_dir()
    has_beads = (root / ".beads").is_dir()

    # `counts` and `failed` are seeded here so the early not-applicable exits
    # below emit the same shape as a full run — a consumer should not have to
    # branch on which kind of repo it is pointed at.
    summary = {"applicable": False, "ok": True, "failed": False,
               "milestone": None, "active_phase": None, "checks": [],
               "counts": {status: 0 for status in SYMBOL}, "note": None}

    if not has_planning and not has_beads:
        summary["note"] = ("neither .planning/ nor .beads/ — doctor not "
                           "applicable (it checks wired repos)")
        emit(args.json, summary, [f"[cairn-doctor] note: {summary['note']}"])
        sys.exit(EXIT_OK)
    # `.beads/` E' O GATE, e `.planning/` deixou de ser exigido (v3.3).
    #
    # Ate aqui bastava a AUSENCIA do `.planning/` para o doctor recusar o
    # repositorio inteiro — e o repositorio sem `.planning/` e' o REPO
    # MIGRADO, que e' o destino da migracao e o que o cairn existe para
    # servir. Um repo tracker-owned nao tinha auditoria nenhuma: nem
    # cobertura requisito-issue, nem integridade do par de labels, nem
    # claims velhas, nem recuperabilidade do export. Todas essas perguntas
    # sao sobre o BD, e nenhuma precisa de um documento para ser respondida.
    #
    # MESMA FAMILIA DO SHIP GATE, corrigido uma release antes: cairn-gate
    # exigia `.planning/` e por isso saia 0 "not applicable" em todo repo
    # migrado — morto e verde ao mesmo tempo. O gate foi corrigido e este
    # ficou, com a mesma forma, no arquivo ao lado.
    #
    # As checagens que dependem de documento NAO precisaram mudar: cada uma
    # ja sabe se declarar `not-applicable` com scope `out-of-scope` (ver
    # check_plan_counters). O defeito era o gate GLOBAL, sobra de um tempo
    # em que o doctor so' sabia auditar documento.
    #
    # A DIRECAO INVERSA CONTINUA NAO-APLICAVEL, e por outra razao: sem
    # `.beads/` nao ha tracker para auditar, e esse caso ja tem achado
    # proprio desde a v1.7 (check_gsd_unmigrated, com a rota).
    if has_planning and not has_beads:
        summary["note"] = (".planning/ exists but .beads/ is absent — "
                           "doctor not applicable (there is no tracker to "
                           "audit); run /cairn:migrate to import this GSD "
                           "into bd")
        human = [f"[cairn-doctor] note: {summary['note']}"]
        # O ACHADO DO GSD POR MIGRAR, que e' o valor deste ramo: quem instala
        # o cairn quase sempre chega com um `.planning/` cheio, e dizer so'
        # "nao aplicavel" o deixaria sem rota nenhuma. O finding nomeia o que
        # ha para migrar e o comando que migra.
        #
        # O `if has_planning:` que envolvia isto saiu na v3.3: dentro deste
        # ramo ele e' sempre verdadeiro — a condicao acima ja exige
        # `has_planning` — e uma condicao sempre-verdadeira com forma de
        # teste e' a armadilha que este repositorio ja documentou duas vezes
        # (bd nao emite `parent`; o `or` do id fazendo o trabalho ao lado).
        finding = check_gsd_unmigrated(root, planning_dir)
        summary["checks"].append(finding)
        summary["counts"][finding["status"]] += 1
        human.append(f"{SYMBOL[finding['status']]} {finding['id']}: "
                     f"{finding['detail']}")
        for item in finding["items"]:
            human.append(f"    - {item}")
        emit(args.json, summary, human)
        sys.exit(EXIT_OK)

    if shutil.which("bd") is None:
        print("[cairn-doctor] warning: 'bd' not on PATH — doctor cannot "
              "run (exit 5)", file=sys.stderr)
        sys.exit(EXIT_NO_BD)

    summary["applicable"] = True
    issues = bd_all_issues(root)
    state = state_frontmatter(planning_dir)
    milestone = state["milestone"] or roadmap_milestone(planning_dir)
    active_phase = state["active_phase"]
    summary["milestone"] = milestone
    summary["active_phase"] = active_phase

    roadmap_phases, reqs_by_phase = roadmap_phases_and_reqs(planning_dir,
                                                            milestone)
    completed_set = roadmap_completed_phases(planning_dir, milestone)
    disk_done = disk_complete_phases(planning_dir)
    disk_reasons = disk_incomplete_reasons(planning_dir)
    plans = plan_inventory(planning_dir)

    # The fixer flags run BEFORE the checks so the report shows post-fix
    # state. --close-completed first: it shrinks the later fixers' inputs.
    closed_n = 0
    closed_phases = set()
    close_failures = []
    if args.close_completed:
        # in_done_phase (ALL, not any) is what keeps this from killing a
        # cross-phase issue that cairn-status still lists as ready.
        targets = [i for i in issues
                   if i.get("status") != "closed"
                   and i.get("id")
                   and in_milestone(i, milestone)
                   and in_done_phase(i, completed_set)]
        closed_phases = {n for i in targets for n in phase_nums(i)}
        # The checkbox<->artifacts divergence note is printed BEFORE the
        # bulk close: the closes empty check 5's scope, so the operator
        # must see "confirm the phase is really done" while it can still
        # change the decision. --json consumers read the same note off
        # check 5's items (closed_phases carries it there).
        if not args.json:
            for n in sorted(closed_phases - disk_done):
                print(f"[cairn-doctor] warning: "
                      f"{divergence_sentence(n, disk_reasons)}")
        # bd refuses to close an epic that still has an open child, and an
        # issue whose blocker is still open. targets is in bd list order,
        # which says nothing about that ordering, so close by FIXPOINT:
        # sweep the pending set, keep whatever bd refused, repeat while a
        # pass still closed something. Any topology drains (an
        # epic<-epic<-epic chain needs one pass per link) with no graph
        # model and no --force — forcing would bulldoze a genuinely open
        # child that is NOT itself in a completed phase.
        pending = list(targets)
        last_error = {}
        while pending:
            stuck, progressed = [], False
            for iss in pending:
                n = min(phase_nums(iss))
                proc = subprocess.run(
                    ["bd", "-C", str(root), "close", iss["id"], "--reason",
                     f"doctor: phase {n} complete in ROADMAP"],
                    capture_output=True, text=True)
                if proc.returncode != 0:
                    last_error[iss["id"]] = (
                        proc.stderr.strip() or proc.stdout.strip()
                        or f"bd close exited {proc.returncode}")
                    stuck.append(iss)
                    continue
                closed_n += 1
                progressed = True
                if not args.json:
                    print(f"[cairn-doctor] closed {iss['id']} — phase {n} "
                          f"complete in ROADMAP ({iss.get('title', '')})")
            pending = stuck
            if not progressed:
                break
        # Survivors are reported (check 5 turns FAIL -> exit 7), never
        # swallowed: an operator who asked for a close and got none of it
        # must not read exit 0.
        close_failures = [(i["id"], last_error.get(i["id"], "unknown error"))
                          for i in pending]
        if closed_n:
            issues = bd_all_issues(root)
            # These closes go through 'bd close' directly, so no
            # post-bd-write hook fires and external mirrors keep showing
            # them open — same reminder cairn-migrate apply prints.
            if not args.json and (root / ".cairn" / "sync.json").is_file():
                print(f"[cairn-doctor] reminder: .cairn/sync.json exists — "
                      f"run /cairn:sync-pull to reconcile external mirrors "
                      f"({closed_n} issue(s) closed here bypassed the push "
                      f"hook)")

    # --fix-labels runs BEFORE the checks so the report shows post-fix state.
    fixed, fix_error = 0, None
    if args.fix_labels:
        candidates = unpaired_issues(issues)
        if candidates:
            if milestone is None:
                die("cannot --fix-labels: active milestone unresolvable "
                    "(no 'milestone:' in STATE.md frontmatter and no "
                    "in-progress milestone in ROADMAP.md)", EXIT_USAGE)
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "cairn-relabel.py"),
                 "pair", "--milestone", milestone, "--dir", str(root)],
                capture_output=True, text=True)
            if proc.returncode == 5:
                die(f"cairn-relabel pair: bd unavailable: "
                    f"{proc.stderr.strip()}", EXIT_NO_BD)
            if proc.returncode != 0:
                fix_error = (proc.stderr.strip() or
                             f"exit {proc.returncode}")
            else:
                fixed = len(candidates)
            issues = bd_all_issues(root)

    # --apply-reconciliation (ESC-03) is mutually orthogonal to the two
    # fixers above (no shared state) — simple sequencing after them is
    # enough. Unlike them it is a distinct, human-invoked command whose own
    # exit-code contract does not track check pass/fail, so it always exits
    # on its own rather than falling through to the report below.
    if args.apply_reconciliation is not None:
        run_apply_reconciliation(root, args.apply_reconciliation, issues,
                                 args.json)

    checks = [
        check_bd_version(),
        check_req_issue(issues, reqs_by_phase, milestone),
        check_frontmatter_ids(plans, issues),
        check_maps_fresh(root, planning_dir, issues),
        check_superseded_released(plans, issues),
        check_phase_complete_open(issues, completed_set, disk_done,
                                  milestone, closed_n, closed_phases,
                                  disk_reasons, close_failures),
        check_orphans(issues, roadmap_phases,
                      archived_milestones(planning_dir)),
        check_label_pairs(issues, milestone, fixed, fix_error),
        check_milestone_carrier(issues),
        check_jira_links(root, issues),
        check_planning_writes(root, planning_dir),
        check_claims_stale(issues, milestone, active_phase),
        check_bd_doctor(root),
        check_gsd_capability(root),
        check_phase_corroboration(root, planning_dir),
        check_phase_artifacts(root, planning_dir, disk_reasons),
        check_external_ref(root, planning_dir, issues, args.link_refs),
        check_lease_stale(root),
        check_release_versions(root),
        check_test_parallel(root),
        check_req_ledger(root, planning_dir),
        check_response_language(root),
        check_phase_landed(root, planning_dir, completed_set),
        check_plan_counters(planning_dir),
        check_state_dialect(planning_dir),
        check_issues_recoverable(root, issues),
        check_export_identity(root, issues),
    ]
    summary["checks"] = checks
    # ONE BUCKET PER WORD OF THE VOCABULARY, COUNTED, NEVER SUBTRACTED.
    # This line used to read `n_ok = len(checks) - n_fail - n_warn`, and that
    # is precisely where a fourth status would have been born already counted
    # as success: the footer would have announced eighteen successes with
    # three checks that compared nothing. The buckets come from SYMBOL's own
    # keys, so the vocabulary has exactly one source.
    counts = {status: 0 for status in SYMBOL}
    for c in checks:
        if c["status"] not in counts:
            # Loudly, not quietly, and not approximated into a neighbouring
            # bucket: between approving in silence and refusing out loud,
            # this phase exists to pick the second. EXIT_USAGE would be a
            # lie — nobody misused the CLI, the report simply does not close.
            die(f"check {c['id']!r} returned unknown status "
                f"{c['status']!r} — the vocabulary is {sorted(counts)}; a "
                f"new status needs a symbol in SYMBOL before it can be "
                f"counted", EXIT_FAILED)
        counts[c["status"]] += 1
    n_ok = counts["ok"]
    n_na = counts[NOT_APPLICABLE]
    n_warn = counts["warn"]
    n_fail = counts["fail"]
    # Only the gap family clears the health key: an out-of-scope absence is
    # normal and permanent in a user's repo, and must not read as incomplete.
    n_no_input = sum(1 for c in checks
                     if c["status"] == NOT_APPLICABLE
                     and c.get("scope") == NA_NO_INPUT)
    summary["counts"] = counts
    # Two different questions, two keys. `failed` is the exact mirror of the
    # exit code, for the consumer that needs it; `ok` also answers "did every
    # check inside the doctor's remit actually receive its input".
    summary["failed"] = n_fail > 0
    summary["ok"] = n_fail == 0 and n_no_input == 0

    lines = [f"[cairn-doctor] {root} — milestone: "
             f"{milestone or 'unresolved'}, active phase: "
             f"{active_phase if active_phase is not None else '?'}"]
    for c in checks:
        lines.append(f" {SYMBOL[c['status']]} {c['id']:<20} {c['detail']}")
        lines += [f"     - {item}" for item in c["items"]]
    # INCOMPLETE never stands in for FAIL: a failure outranks it, because
    # "something is inconsistent" is the louder sentence.
    if n_fail:
        verdict = "FAIL"
    elif n_no_input:
        verdict = "INCOMPLETE"
    else:
        verdict = "ok"
    lines.append(f"[cairn-doctor] {verdict} — {n_ok} ok, {n_na} "
                 f"not-applicable, {n_warn} warning(s), {n_fail} failure(s)")

    emit(args.json, summary, lines)
    sys.exit(EXIT_OK if n_fail == 0 else EXIT_FAILED)


if __name__ == "__main__":
    main()
