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
items[]}, plus `scope` when and only when the status is not-applicable):

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
                        version output -> WARN. Runs first — eighteen
                        checks in total.
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
    10. gsd-capability  which GSD lineage is installed and whether the
                        cairn capability actually registered against it
                        (see check_gsd_capability()'s own docstring for
                        the full routing — an unloadable manifest, two
                        lineages at once, the 4.x lineage, or an
                        unregistered/partly-staged bundle -> FAIL; no GSD
                        binary found at all -> WARN, not evidence either
                        way).
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

--apply-reconciliation N  (ESC-03, Phase 17 Plan 3) the human-invoked,
                    separate command that APPLIES a verified semantic-
                    escalation reconciliation proposal for phase N. Not one
                    of the 19 checks above — a fixer, the same category as
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
CAIRN_TEST = os.environ.get(
    "CAIRN_TEST", str(SCRIPTS_DIR / "cairn-test.py"))

# Test/override seam for check_req_ledger()'s single read of the requirement
# ledger (AUTO-07) — same CAIRN_* convention as the three seams above. The
# doctor never re-parses the ledger: cairn-bookkeep.py owns that reading, and
# a second parser is how a repo ends up with a fifth number for the same
# quantity (T-29-31).
CAIRN_BOOKKEEP = os.environ.get(
    "CAIRN_BOOKKEEP", str(SCRIPTS_DIR / "cairn-bookkeep.py"))

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
NO_PHASE_EXEMPT = {"migrated-todo", "backlog", "quick", "lease"}


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
    """{'milestone': str|None, 'active_phase': int|None} from STATE.md."""
    out = {"milestone": None, "active_phase": None}
    lines = read_lines(planning_dir / "STATE.md")
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^(milestone|active_phase)\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        val = m.group(2).split("#", 1)[0].strip().strip("'\"").strip()
        if m.group(1) == "milestone" and val:
            out["milestone"] = val
        elif m.group(1) == "active_phase":
            digits = re.search(r"\d+", val)
            if digits:
                out["active_phase"] = int(digits.group(0))
    return out


def roadmap_milestone(planning_dir):
    """Milestone marked in progress in ROADMAP.md (🚧 / '(in progress)'
    line carrying a vN[.N...] token), or None."""
    for line in read_lines(planning_dir / "ROADMAP.md"):
        if "🚧" in line or re.search(r"\(in progress\)", line, re.IGNORECASE):
            m = VERSION_TOKEN.search(line)
            if m:
                return m.group(0)
    return None


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


def roadmap_phases_and_reqs(planning_dir):
    """(set of phase numbers, {phase: [req ids]}) parsed leniently from
    ROADMAP.md: 'Phase N' headings and checkbox lines enumerate phases;
    a '**Requirements**:' line inside a phase heading's section maps it."""
    phases, reqs = set(), {}
    current = None
    for line in read_lines(planning_dir / "ROADMAP.md"):
        m = PHASE_HEAD.match(line)
        if m:
            current = int(m.group(1))
            phases.add(current)
            continue
        if ANY_HEAD.match(line):
            current = None
        m = CHECKBOX_PHASE.match(line)
        if m:
            phases.add(int(m.group(2)))
        if current is not None:
            m = REQ_LINE.match(line.strip())
            if m:
                reqs[current] = REQ_ID.findall(m.group(1))
    return phases, reqs


def roadmap_completed_phases(planning_dir):
    """Phase numbers ROADMAP.md marks COMPLETE, with the same lenient
    semantics as cairn-gate: checked '- [x] ... Phase N' checkbox lines
    plus milestone progress-table rows ending '| Complete |'."""
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
def check_req_issue(issues, reqs_by_phase, milestone):
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
    if not total:
        # Phase 23 / VOID-02 (CairnGo-ca3). This used to read `ok` with the
        # detail "no '**Requirements**:' lists found" — a check announcing
        # success over a comparison it never made. `no-input`, not
        # `out-of-scope`: the mapping requirement -> issue is a guarantee this
        # project WANTS, it has simply never been verified here, and writing
        # the line in ROADMAP.md is a concrete thing the operator can do.
        return {"id": "req-issue", "status": NOT_APPLICABLE,
                "scope": NA_NO_INPUT,
                "detail": "nothing to compare — ROADMAP.md lists no phase "
                          "with a '**Requirements**:' line, so no requirement "
                          "was ever checked against an issue here; add the "
                          "line to a phase's section in ROADMAP.md",
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
        if not live_plans:
            detail = ("nothing to compare — no non-superseded PLAN.md on "
                      "disk, so no plan bead id has ever been checked here")
        else:
            detail = (f"nothing to compare — none of the {live_plans} "
                      "non-superseded PLAN.md file(s) carries a 'beads:' "
                      "frontmatter id, so no plan is stamped with the issues "
                      "it delivers — run cairn-map.sh <N> after stamping")
        return {"id": "frontmatter-ids", "status": NOT_APPLICABLE,
                "scope": NA_NO_INPUT, "detail": detail, "items": []}
    detail = (f"{len(items)} of {checked} plan bead id(s) broken" if items
              else f"{checked} plan bead id(s) verified")
    return {"id": "frontmatter-ids", "status": "fail" if items else "ok",
            "detail": detail, "items": items}


def check_maps_fresh(root, planning_dir, issues):
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
        return {"id": "maps-fresh", "status": NOT_APPLICABLE,
                "scope": NA_NO_INPUT,
                "detail": "nothing to compare — no phase directory under "
                          f"{planning_dir.name}/phases/ carries either an "
                          "issue or a generated map, so no map's freshness "
                          "was ever checked here",
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
        return {"id": "superseded-released", "status": NOT_APPLICABLE,
                "scope": NA_NO_INPUT,
                "detail": "nothing to compare — no PLAN.md on disk, so no "
                          "superseded plan's beads have ever been checked "
                          "here",
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
        blind = ("the phase-label axis could not run — ROADMAP.md lists no "
                 "phase to compare labels against")
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


def check_label_pairs(issues, milestone, fixed, fix_error):
    items = []
    for iss in unpaired_issues(issues):
        labels = ", ".join(lb for lb in iss["labels"]
                           if PHASE_LABEL.match(lb))
        hint = (f"cairn-relabel.sh pair --milestone {milestone}"
                if milestone else "cairn-relabel.sh pair --milestone <m>")
        items.append(f"{iss.get('id', '?')}: {labels} but no m-* label "
                     f"— {hint}")
    if fix_error:
        items.insert(0, f"--fix-labels failed: {fix_error}")
        status = "fail"
        detail = "--fix-labels could not repair the pairing"
    else:
        status = "warn" if items else "ok"
        detail = (f"{len(items)} issue(s) missing the m-* pair" if items
                  else "every phase-labeled issue carries an m-* label")
        if fixed:
            detail += f" (fixed {fixed} via cairn-relabel pair)"
    # Phase 23 evaluated and KEPT `ok` for the zero counts here, both of them.
    # An empty tracker is already reported by other checks, so saying it again
    # from this one adds a second voice for one fact; and issues present with
    # every pair intact is the check having swept and approved. Neither is an
    # absent input.
    return {"id": "label-pairs", "status": status,
            "detail": detail, "items": items}


# Every cairn surface that READS STATE.md's active_phase, measured
# 2026-08-04 (`grep -rln active_phase cairn/`, docstring-only mentions
# excluded): naming them is what makes the no-input verdict below routable
# instead of a shrug.
ACTIVE_PHASE_READERS = ("cairn-status.py", "cairn-doctor.py",
                        "cairn-lease.py", "cairn-migrate.py",
                        "hooks/session-start.sh")

# Where the decision this check is waiting on actually lives. A non-ok state
# with no address becomes noise in two weeks.
ACTIVE_PHASE_ISSUE = "CairnGo-rq0"


def check_claims_stale(issues, milestone, active_phase):
    """Check 8, id "claims-stale" — in_progress issues assigned outside the
    active phase.

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
        return {"id": "claims-stale", "status": NOT_APPLICABLE,
                "scope": NA_NO_INPUT,
                "detail": "cannot check — STATE.md's frontmatter carries no "
                          "'active_phase', so there is nothing to compare "
                          "in_progress claims against (this check has never "
                          "run here). "
                          f"{len(ACTIVE_PHASE_READERS)} cairn surfaces read "
                          f"that key ({', '.join(ACTIVE_PHASE_READERS)}); "
                          f"which key STATE.md should carry is open in "
                          f"{ACTIVE_PHASE_ISSUE}. Not a failure: a check "
                          "with no input is friction, not a state "
                          "inconsistency",
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


def check_gsd_capability(root):
    """Check 10 — which GSD lineage is installed, and whether the cairn
    capability actually registered against it.

    This is the check that would have caught the plugin's longest-lived bug:
    the wrappers worked, the fusion did not, and nothing said so. It is a
    FAIL, not a warn, whenever a repo with .planning/ has no registered
    capability — a soft signal here is exactly how the failure stayed
    invisible.

    Delegates to cairn-capability.py so the lineage rules and the two
    registration checks live in one place. Its exit codes: 0 registered,
    5 no GSD binary found, 7 not registered.
    """
    script = Path(__file__).resolve().parent / "cairn-capability.py"
    if not script.is_file():
        return {"id": "gsd-capability", "status": "warn",
                "detail": "cairn-capability.py not found beside this script",
                "items": []}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "detect",
             "--project-dir", str(root), "--json"],
            capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"id": "gsd-capability", "status": "warn",
                "detail": f"could not run cairn-capability.py: {exc}",
                "items": []}

    try:
        info = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"id": "gsd-capability", "status": "warn",
                "detail": "cairn-capability.py did not return JSON "
                          f"(exit {proc.returncode})", "items": []}

    lineage = info.get("lineage", "unknown")
    if lineage == "absent":
        # No GSD binary is discoverable. That is not proof the capability is
        # missing, so it does not carry the same verdict as a registry that
        # answered and did not list cairn.
        return {"id": "gsd-capability", "status": "warn",
                "detail": "no GSD binary found — cannot tell whether the "
                          "cairn capability is registered", "items": []}

    # Checked before registration, because it outranks it: a plugin Claude Code
    # refuses to load exposes no /gsd:* commands at all, so a perfectly
    # registered capability has nothing to attach to. It is also invisible from
    # inside the capability checks — the gsd-tools CLI keeps working, which is
    # why the install succeeds while the plugin is dead.
    if info.get("manifest_loadable") is False:
        return {"id": "gsd-capability", "status": "fail",
                "detail": "the installed gsd-core will NOT load — "
                          f"{info.get('manifest_detail', 'manifest defect')}",
                "items": [
                    "Fix: bash \"${CLAUDE_PLUGIN_ROOT}/scripts/"
                    "cairn-capability.sh\" repair-manifest, then /reload-plugins",
                    "Upstream: open-gsd/gsd-core#2077 has the one-line fix; a "
                    "plugin update re-introduces the defect until it lands",
                ]}

    # Two GSD lineages at once. cairn's discovery prefers gsd-core, so the
    # capability can be registered and complete while the operator's /gsd:*
    # commands are answered by the 4.x plugin that cannot host it — the fusion
    # absent with every other signal green. The likeliest way to land here is
    # having had GSD before meeting cairn.
    if info.get("both_lineages"):
        inst = info.get("installed_gsd") or {}
        legacy = inst.get("legacy") or []
        return {"id": "gsd-capability", "status": "fail",
                "detail": "two GSD lineages installed — "
                          f"{', '.join(legacy + (inst.get('core') or []))}. "
                          "/gsd:* may be answered by the 4.x plugin, which "
                          "cannot host the capability",
                "items": [
                    f"Fix: claude plugin uninstall {legacy[0]}"
                    if legacy else "Fix: remove the 4.x gsd plugin",
                    "then /reload-plugins",
                ]}

    if info.get("ok"):
        cap = info.get("capability") or {}
        return {"id": "gsd-capability", "status": "ok",
                "detail": f"gsd-core lineage; cairn v{cap.get('version', '?')} "
                          f"registered ({cap.get('scope', '?')} scope)",
                "items": []}

    remedy = (info.get("remedy") or "").splitlines()
    detail = {
        "legacy": "GSD 4.x lineage — it has no 'capability' subcommand, so "
                  "plain /gsd:* does NOT touch bd issues. Install the official "
                  "core: claude plugin install gsd-core@cairngo",
    }.get(lineage)
    if detail is None:
        detail = (remedy[0] if remedy
                  else f"capability not registered (lineage {lineage})")
    return {"id": "gsd-capability", "status": "fail", "detail": detail,
            "items": [ln.strip() for ln in remedy[1:] if ln.strip()]}


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
    completely untouched in that case."""
    if last_moved is None:
        return ""
    clauses = []
    for source in sources:
        entry = last_moved.get(source)
        if entry:
            clauses.append(f"{source} last moved {entry.get('ts')}")
        else:
            clauses.append(f"{source} last moved never observed")
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
            items.append(
                f"phase {phase}: held by {entry.get('holder')} (actor: "
                f"{entry.get('actor')}) since {entry.get('acquired_at')}, "
                f"last renewed {entry.get('heartbeat_at')} — reclaimable "
                f"— the next /cairn:work {phase} takes it automatically, "
                f"or run cairn-lease.sh release {phase} to clear it now")
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

# Named by reconcile, outside this check's remit: STATE.md's own views. They
# are still SURFACED — an unexplained absence is the exact defect this phase
# removes — but they never spend exit 7 on a check called `req-ledger`, and
# `state-narrative-stale` is free text reconcile itself declines to rewrite,
# so failing on it would be a red that the routed command cannot clear.
REQ_LEDGER_OUT_OF_REMIT_KINDS = (
    "state-counter-stale",
    "state-narrative-stale",
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
        return {"id": "req-ledger", "status": NOT_APPLICABLE,
                "scope": NA_OUT_OF_SCOPE,
                "detail": f"{planning_dir.name}/ carries no "
                          f"{', '.join(absent)}, so there is no requirement "
                          f"ledger to cross-check",
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
    if has_planning != has_beads:
        present = ".planning/" if has_planning else ".beads/"
        absent = ".beads/" if has_planning else ".planning/"
        summary["note"] = (f"{present} exists but {absent} is absent — "
                           "doctor not applicable (it checks wired repos); "
                           "run /cairn:migrate to bootstrap the missing side")
        emit(args.json, summary, [f"[cairn-doctor] note: {summary['note']}"])
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

    roadmap_phases, reqs_by_phase = roadmap_phases_and_reqs(planning_dir)
    completed_set = roadmap_completed_phases(planning_dir)
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
