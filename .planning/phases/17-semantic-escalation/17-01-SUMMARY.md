---
phase: 17-semantic-escalation
plan: 01
subsystem: infra
tags: [python, bats, bd, git, subprocess, hashing]

# Dependency graph
requires:
  - phase: 13-state-corroboration
    provides: "cairn-status.py's phase_model()/corroborate() — the evidence/corroboration/conflicts keys collect() reads verbatim"
  - phase: 16-transition-journal
    provides: "cairn-journal.py's last-moved/history read subcommands — the journal evidence collect() gathers"
provides:
  - "cairn-reconcile.py collect <N> — gated (ESC-04), write-free evidence collector, hashed bundle (D-04) at .cairn/reconcile-evidence.json"
  - "cairn-reconcile.py verify <N> — mechanical citation re-check (D-03), whole-proposal invalidation on any single bad citation"
  - "the fixed evidence-bundle and proposal JSON schemas both Plan 17-02 (subagent) and Plan 17-03 (--apply-reconciliation) build on"
affects: [17-02-semantic-escalation, 17-03-semantic-escalation]

# Actuals (#2632)
actuals:
  tokens: 7500
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "shell-out-and-degrade to cairn-status.py/cairn-journal.py, mirroring cairn-doctor.py's check_phase_corroboration()/journal_last_moved() shape exactly"
    - "D-04 evidence hash computed over the bundle dict BEFORE generated_at/evidence_hash are added, so it never hashes its own non-deterministic fields"
    - "whole-input invalidation (D-03): a single bad citation fails the entire proposal, no per-claim partial credit"

key-files:
  created:
    - cairn/scripts/cairn-reconcile.py
    - cairn/scripts/cairn-reconcile.sh
    - tests/cairn-reconcile.bats
  modified:
    - .gitignore

key-decisions:
  - "Empty proposal (no claims, or claims with zero citations) is treated as INVALID (exit 4), never vacuously valid — an absence of citations is not evidence of agreement"
  - "Stale-bundle cleanup on refusal is scoped strictly to 'different phase number' — a same-phase bundle or an unreadable/unparsable file is left untouched, never blindly deleted"
  - "Project-directory-does-not-exist is checked explicitly, before any subprocess call, rather than letting subprocess.run's cwd=<missing dir> raise an uncaught FileNotFoundError"

patterns-established:
  - "cairn-reconcile.py: a third example (after cairn-doctor.py, cairn-status.py) of shelling to cairn-status.py --json and reading phases[] rows client-side, rather than re-deriving corroboration logic"

requirements-completed: [ESC-01, ESC-02, ESC-04]

coverage:
  - id: D1
    description: "collect gathers evidence into a hashed bundle only when the target phase's corroboration verdict is exactly 'conflict', refusing (exit 3, nothing written) otherwise — ESC-04"
    requirement: "ESC-04"
    verification:
      - kind: unit
        ref: "tests/cairn-reconcile.bats#collect: an all-agree fixture reports 'ok' and collect refuses — exit 3, nothing written"
        status: pass
      - kind: unit
        ref: "tests/cairn-reconcile.bats#collect: refusing on a non-conflicted phase deletes a stale bundle left over for a DIFFERENT phase"
        status: pass
    human_judgment: false
  - id: D2
    description: "collect's source carries zero bd write verbs and zero journal-append calls, AND a real run against a conflicted fixture mutates neither bd state nor the tracked working tree — ESC-02"
    requirement: "ESC-02"
    verification:
      - kind: unit
        ref: "tests/cairn-reconcile.bats#static: cairn-reconcile.py's source carries zero bd write verbs and zero journal-append calls"
        status: pass
      - kind: unit
        ref: "tests/cairn-reconcile.bats#collect: THE LOAD-BEARING TEST -- a real collect run against a conflicted fixture mutates neither bd state nor the working tree"
        status: pass
    human_judgment: false
  - id: D3
    description: "the evidence bundle's hash (D-04) is stable across two consecutive collect runs against the same unchanged conflicted fixture"
    verification:
      - kind: unit
        ref: "tests/cairn-reconcile.bats#collect: two consecutive runs against an unchanged conflicted fixture produce the identical evidence_hash (D-04)"
        status: pass
    human_judgment: false
  - id: D4
    description: "verify rejects a proposal whole-cloth when even one citation's file+line does not contain the claimed literal text (D-03), even when every other citation in the same proposal is correct"
    requirement: "ESC-01"
    verification:
      - kind: unit
        ref: "tests/cairn-reconcile.bats#verify: THE CITATION TRAP -- one bad citation invalidates the WHOLE proposal, even with a correct citation present"
        status: pass
      - kind: unit
        ref: "tests/cairn-reconcile.bats#verify: a proposal with every citation correct verifies as valid, exit 0"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-07-31
status: complete
---

# Phase 17 Plan 1: Semantic escalation collector + citation checker Summary

**cairn-reconcile.py: a write-free evidence collector gated on cairn-status.py's "conflict" verdict, plus a mechanical citation checker that rejects a proposal wholesale on any single mismatched line.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-31
- **Tasks:** 3
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments
- `cairn-reconcile.py collect <N>` gathers corroboration evidence, journal last-moved/history, up to 50 capped git commits, and the phase's ROADMAP.md section + NN-CONTEXT.md into one bundle at `.cairn/reconcile-evidence.json`, but only when `cairn-status.py --json`'s phases[] row for N reads exactly `"conflict"` — otherwise it refuses (exit 3), writes nothing, and cleans up any bundle left over for a different phase.
- The bundle's `evidence_hash` (D-04) is computed over only the sources that specific conflict's bundle actually gathered, excluding its own `generated_at`/`evidence_hash` fields — proven stable across two consecutive, unchanged re-runs.
- `cairn-reconcile.py verify <N>` re-opens every citation's own file at its own 1-indexed line and compares the literal text exactly (D-03); a single bad citation invalidates the entire proposal, never a per-claim partial result.
- A grep over the committed source finds zero bd write verbs (`create`/`update`/`close`/`reopen`) and zero journal-append-family calls (`observe`/`lease`/`append`) — and a bats test *runs* `collect` against a real, genuinely conflicted bd+GSD fixture and proves neither `bd list --all --json` nor the tracked working tree (excluding `.git/` and `.cairn/`) changed, before vs. after.
- Every one of the three load-bearing guarantees (ESC-04's gate, ESC-02's mutation-proof invariant, and D-03's whole-proposal citation invalidation) was verified by temporarily breaking the corresponding code path, confirming its bats test went red, then restoring the implementation — not just asserted by inspection.

## Task Commits

Each task was committed atomically:

1. **Task 1: cairn-reconcile.py collect — gated evidence gathering, zero bd writes** - `4e16806` (feat)
2. **Task 2: cairn-reconcile.py verify — citation re-check, whole-proposal invalidation** - `614799a` (feat)
3. **Task 3: tests/cairn-reconcile.bats — mutation-proof, gating-proof, and citation-trap coverage** - `e956db8` (test)

_Note: Task 1 and Task 2 both touch `cairn-reconcile.py`; the file was built as one complete, fully-tested implementation and then reconstructed into two faithful, individually-compiling commits along the plan's own task boundary (collect-only, then the verify addition), matching the plan's per-task atomic-commit contract without discarding any verification already done against the final file._

## Files Created/Modified
- `cairn/scripts/cairn-reconcile.py` - `collect`/`verify` subcommands, argparse subparsers, evidence-bundle + proposal schemas documented in the module docstring
- `cairn/scripts/cairn-reconcile.sh` - thin wrapper, `exec python3 ... "$@"`, header restates the exit-code contract
- `tests/cairn-reconcile.bats` - 12 scenarios: static grep, gating (ESC-04), the mutation-proof load-bearing test, D-04 hash determinism, an evidence-content spot-check, and four `verify` scenarios including the citation trap
- `.gitignore` - added `.cairn/reconcile-evidence.json` alongside the existing `.cairn/conflicts.json` entry

## Decisions Made
- **Empty-proposal rejection:** a proposal with no `claims`, an empty `claims` list, or claims carrying zero citations across the whole proposal is treated as `valid: false` (exit 4), not vacuously valid. Absence of anything to check is not evidence of agreement — an empty/malformed proposal auto-accepting by default would be a dangerous silent-pass path. This surfaced directly from Task 2's own `<verify>` smoke test (`{"phase": 1, "citations_test": true}` — no real `claims` key — asserts exit 4), which made the "vacuously valid" alternative explicitly wrong per the plan itself.
- **Stale-bundle cleanup scope:** `_clean_stale_bundle()` only deletes an existing bundle when its own `phase` field differs from the phase just checked; an unreadable/unparsable existing file is left in place rather than blindly deleted, since a parse failure doesn't tell us whether it's actually stale.
- **Project-directory existence guard:** both `collect` and `verify` check `root.is_dir()` before doing anything else (including before shelling out), rather than letting a missing `--project-dir` surface as an uncaught `FileNotFoundError` from `subprocess.run(..., cwd=<missing>)`. This was necessary to satisfy Task 1's own smoke test literally (`grep -q "error\|does not exist"` is case-sensitive and would not match a raw `FileNotFoundError` traceback's `Error` with a capital E).
- **Git log field delimiter:** used the plan's literal `--format=%H|%ai|%an|%s`, but parse with `split("|", 3)` (not a bare split) so a `|` inside a commit subject can never corrupt the hash/date/author fields around it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `find` command in the mutation-proof test needed an explicit `.cairn/` exclusion**
- **Found during:** Task 3 (writing the mutation-proof bats scenario)
- **Issue:** The plan's own prose for the mutation-proof test says the working-tree manifest excludes `.cairn/` ("excluding `.cairn/` itself, since collect's OWN evidence-bundle write is expected there"), but the literal `find` command quoted in the same paragraph only excludes `./.git/*`. Using the command as literally quoted would make the test fail on collect's own expected, carved-out evidence-bundle write — a false failure on legitimate behavior, not a real mutation.
- **Fix:** Added `! -path './.cairn/*'` to the `find` invocation, matching the paragraph's own stated intent (and cairn-journal.py's parallel side effect of writing `.cairn/journal.jsonl` as part of cairn-status.py's existing, already-accepted `journal_observe_phases()` behavior, also correctly carved out by the same exclusion).
- **Files modified:** tests/cairn-reconcile.bats
- **Verification:** Manually confirmed the `.cairn/` exclusion is necessary — a run without it shows `reconcile-evidence.json` (and `journal.jsonl`) as expected new files, which the test would otherwise misreport as a mutation.
- **Committed in:** e956db8 (Task 3 commit)

**2. [Rule 1 - Bug] Task 2's own `<verify>` smoke test implied empty-proposal rejection, not the vacuous-accept my first draft would have produced**
- **Found during:** Task 2, running the plan's own smoke test (`verify 1 --file <proposal with no real claims>`, asserting exit 4)
- **Issue:** A straightforward reading of "flatten every citation and check it" against a proposal with zero citations naturally computes zero failures, which would report `valid: true` (exit 0) — directly contradicting the plan's own smoke-test assertion of exit 4.
- **Fix:** Added an explicit "no claims, or zero citations across every claim" check ahead of the per-citation loop, treating that case as its own failure rather than an empty (therefore vacuously passing) failure list.
- **Files modified:** cairn/scripts/cairn-reconcile.py
- **Verification:** Ran the plan's literal smoke-test command; exit 4 confirmed. Also covered by a dedicated bats scenario ("a proposal with no claims (or zero citations) is rejected, never vacuously valid").
- **Committed in:** 614799a (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking test-tooling fix, 1 bug relative to the plan's own stated behavior)
**Impact on plan:** Both fixes make the implementation match the plan's own explicit smoke tests and stated intent exactly; no scope creep, no architectural change.

## Issues Encountered
None beyond the two deviations above, both resolved during implementation.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The evidence-bundle schema (`.cairn/reconcile-evidence.json`) and the proposal schema (`.cairn/conflicts.json`) are both fixed in `cairn-reconcile.py`'s own module docstring, so Plan 17-02's tool-restricted subagent and Plan 17-03's `--apply-reconciliation` flag can build against one agreed shape without re-deriving it.
- `collect`'s pathspec-narrowed git log evidence returned empty (`[]`) against the test fixtures used here, since those fixtures' `.planning/` files are never committed to git — this is expected, correct degrade behavior (never an error), not a gap; a real repo's phase files are committed and will populate `git_log` normally.
- No blockers for Plan 17-02 (the subagent) or Plan 17-03 (`cairn-doctor.py --apply-reconciliation`) — both consume this plan's collector/checker as read-only inputs.

---
*Phase: 17-semantic-escalation*
*Completed: 2026-07-31*

## Self-Check: PASSED

All created files found on disk (`cairn/scripts/cairn-reconcile.py`, `cairn/scripts/cairn-reconcile.sh`, `tests/cairn-reconcile.bats`, this SUMMARY). All three task commits (`4e16806`, `614799a`, `e956db8`) confirmed present in `git log`.
