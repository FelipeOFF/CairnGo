---
phase: 17-semantic-escalation
plan: 02
subsystem: infra
tags: [claude-agent, subagent, tool-restriction, bats, markdown-command]

# Dependency graph
requires:
  - phase: 17-semantic-escalation
    provides: "Plan 17-01's cairn-reconcile.py collect/verify — the evidence bundle and proposal schemas this plan builds the subagent and command against"
provides:
  - "cairn/agents/reconcile-investigator.md — a Read/Grep/Glob-only subagent that proposes a cited reconciliation as text, holding zero write-capable tools"
  - "cairn/commands/reconcile.md — the /cairn:reconcile N command: gate -> cache-check -> collect -> spawn -> write-proposal -> verify -> present"
  - "the harness-level half of ESC-02 (the subagent cannot write ANY file, structurally, not merely 'no Bash, no Edit')"
affects: [17-03-semantic-escalation]

# Actuals
actuals:
  tokens: 5200
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "agent tools: frontmatter as the write-incapacity boundary — no path-scoping syntax exists in this repo, so the guarantee is 'tool absent from the list', never 'tool present but constrained in prose'"
    - "the deterministic command layer (not the subagent) performs the one file write in a code+prose pipeline, mirroring how cairn-doctor.py's flags gate writes behind a deterministic check rather than an LLM's own judgment"

key-files:
  created:
    - cairn/agents/reconcile-investigator.md
    - cairn/commands/reconcile.md
    - tests/cairn-reconcile-agent.bats

key-decisions:
  - "ctx_search (context-mode memory) is deliberately NOT granted in this revision — no established convention exists anywhere in this codebase for naming an MCP tool inside an agent's tools: frontmatter, and the plan's own instruction is to omit rather than guess a name that might not hold. Documented in the agent body as a known gap, not a silently cut corner."
  - "The write-capable-tools bats check scopes its grep to the extracted tools: line specifically, never the whole file — the agent's own body text discusses 'Write' at length to explain why it's excluded, so a whole-file grep for the word would always false-fail"
  - "All assertions in the new bats file use plain [ ] against a run-captured $status/$output, never [[ ]] or a bare negated command, per the house note (inherited from tests/cairn-reconcile.bats) that a failing [[ ]] or ! cmd does not reliably fail a test on this bash"

requirements-completed: [ESC-01, ESC-02, ESC-04]

coverage:
  - id: D1
    description: "reconcile-investigator's tools: frontmatter grants exactly Read, Grep, Glob and contains NONE of the full write-capable set (Write, Edit, Bash, NotebookEdit) — proven by a bats check that actually failed against a reintroduced unscoped Write grant before being restored and reconfirmed green"
    requirement: "ESC-02"
    verification:
      - kind: unit
        ref: "tests/cairn-reconcile-agent.bats#agent: tools: grant contains NONE of the full write-capable set"
        status: pass
      - kind: unit
        ref: "tests/cairn-reconcile-agent.bats#agent: tools: grant is a non-empty subset of {Read, Grep, Glob, ctx_search}"
        status: pass
    human_judgment: false
  - id: D2
    description: "the agent's own body text states in prose it never writes any file and names /cairn:reconcile as the sole writer of .cairn/conflicts.json — catching a leftover-prose bug the frontmatter check alone would miss"
    verification:
      - kind: unit
        ref: "tests/cairn-reconcile-agent.bats#agent: body states it never writes any file, naming /cairn:reconcile as the sole writer of conflicts.json"
        status: pass
    human_judgment: false
  - id: D3
    description: "/cairn:reconcile's committed prose gates on corroboration before collect before the subagent spawn before its own conflicts.json write before verify before presenting — a proxy for ESC-04's 'runs only on a detected conflict', since bats cannot invoke the Task tool to prove a live run"
    requirement: "ESC-04"
    verification:
      - kind: unit
        ref: "tests/cairn-reconcile-agent.bats#command: corroboration gate precedes collect, precedes the subagent spawn, precedes the command's own conflicts.json write, precedes verify, precedes apply-reconciliation"
        status: pass
    human_judgment: false
  - id: D4
    description: "the command names /cairn:doctor --apply-reconciliation as the only path to an actual bd write and its own committed prose never instructs a direct bd create/update/close/reopen invocation, mirroring Plan 17-01's script-level static check one layer up"
    verification:
      - kind: unit
        ref: "tests/cairn-reconcile-agent.bats#static: neither reconcile.md nor reconcile-investigator.md instructs a direct bd write"
        status: pass
    human_judgment: true
    rationale: "The proposal schema, claim wording, and recommended_action vocabulary are authored prose read by a human reviewing the command's design intent, not something a unit test can fully validate — ESC-01's 'the investigation proposes a cited reconciliation a human can actually evaluate' is a readability/design judgment call, even though the mechanical citation re-check (D-03) is already proven by Plan 17-01's own verify tests."

duration: ~25min
completed: 2026-07-31
status: complete
---

# Phase 17 Plan 2: Semantic escalation investigator + orchestrating command Summary

**A Read/Grep/Glob-only subagent (zero write-capable tools) that proposes a cited reconciliation as text, and the `/cairn:reconcile` command that gates on a detected conflict, spawns it, and performs the one file write itself.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-31
- **Tasks:** 3
- **Files modified:** 3 (all created)

## Accomplishments
- `cairn/agents/reconcile-investigator.md` declares `tools: Read, Grep, Glob` — no `Write`, `Edit`, `Bash`, or `NotebookEdit` — and its body documents, in prose, exactly why this is the fix for the plan-check blocker on this plan's first draft (an unscoped `Write` "scoped in prose only" would have let the subagent write any file in the repo, since this codebase has no path-scoping syntax for an agent's `tools:` list).
- The agent's body states plainly it never writes `.cairn/conflicts.json` or any other file, names `/cairn:reconcile` as the sole writer, defines the closed `bd_close`/`bd_reopen`/`manual_review` recommended-action vocabulary mapped from `corroborate()`'s own conflict `sources` pairs, and states its final message is a single JSON object `{"claims": [...]}` and nothing else.
- `cairn/commands/reconcile.md` is a six-step numbered prose command: gate on `corroboration` (step 1) → cache-check a hash-matching prior proposal (step 2, D-04) → real `collect` + spawn the subagent (step 3) → parse its returned text and write the full envelope to `.cairn/conflicts.json` itself, stamping `phase`/`generated_at`/`evidence_hash` from its own deterministic state (step 4) → `verify` before ever showing a human anything (step 5) → present, naming `/cairn:doctor --apply-reconciliation` as the only path to an actual `bd` write (step 6).
- `tests/cairn-reconcile-agent.bats` (7 scenarios): the frontmatter's `tools:` line is checked in isolation for absence of the *full* write-capable set and for being an exact subset of `{Read, Grep, Glob, ctx_search}`; the body's write-incapacity framing is grepped for directly; the command's own anchor terms (`corroboration`, `collect`, `reconcile-investigator`, `conflicts.json`, `verify`, `apply-reconciliation`) are asserted strictly increasing by first line number; both files are scanned for a direct `bd create`/`update`/`close`/`reopen` invocation (zero matches).
- The write-capable-tools check was proven non-vacuous per this repo's "a test that would pass either way is not proof" discipline: an unscoped `Write` was temporarily reintroduced into the frontmatter, the check went red (2 of 7 tests failed), the file was restored, and the suite was re-confirmed green — see the transcript of this session for the actual red/green cycle.

## Task Commits

Each task was committed atomically:

1. **Task 1: reconcile-investigator subagent — restricted tool grants** - `a99225c` (feat)
2. **Task 2: /cairn:reconcile command — gate, cache, spawn, verify, present** - `5af3036` (feat)
3. **Task 3: tests/cairn-reconcile-agent.bats — structural proof the write-incapacity is real, not narrated** - `c87faab` (test)

## Files Created/Modified
- `cairn/agents/reconcile-investigator.md` - the restricted subagent, `tools: Read, Grep, Glob`, prose covering the write-incapacity rationale, citation rules (D-03), and the closed recommended-action vocabulary
- `cairn/commands/reconcile.md` - the orchestrating command, six numbered steps, `argument-hint: "<phase-number>"`
- `tests/cairn-reconcile-agent.bats` - 7 scenarios: tool-grant absence/subset checks, body-prose check, command step-order proxy check, direct-bd-write static scan

## Decisions Made
- **`ctx_search` omitted, not guessed.** The plan explicitly allowed granting `ctx_search` "only if this session's context-mode MCP tool name is confirmed available — otherwise omit rather than guess a name that doesn't exist." No agent anywhere in this codebase (cairn's own, or the vendored GSD agents) declares an MCP tool by name in a `tools:` frontmatter line, so there is no established convention to follow, and the exact string that would be required (a bare `ctx_search` vs. a fully-qualified `mcp__...__ctx_search`) is unconfirmed. Omitting it keeps the agent's grant unambiguous and still satisfies every `must_haves` truth in the plan (`Read, Grep, Glob` alone already carries zero write-capable tools); the agent's body documents this as a known, deliberate gap for a future plan to close once a real convention exists, not a silently cut corner.
- **The bats step-ordering check's anchor terms were chosen and placed by iterating the actual command prose, then verified with real `grep -n` runs before the bats file was written** (not assumed) — `corroboration` (line 19) < `collect` (36) < `reconcile-investigator` (56) < `conflicts.json` (61) < `verify` (90) < `apply-reconciliation` (101) in the committed `reconcile.md`. This is documented directly in this plan's `<objective>` as a proxy, not a runtime proof: bats cannot spawn the Task tool, so it can only assert the command's own text is in the right order, never that a live invocation actually respected it. The load-bearing, mechanically-proven half of ESC-04's gate remains Plan 17-01's `collect` refusal (exit 3), tested with a real fixture in `tests/cairn-reconcile.bats`.

## Deviations from Plan

None — plan executed exactly as written, including its own explicit fallback instruction for the `ctx_search` grant (see Decisions Made above, which is a plan-anticipated branch, not a deviation from it).

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Plan 17-03 (`cairn-doctor.py --apply-reconciliation`) can now build against a real, committed proposal schema producer: `.cairn/conflicts.json` is written by `/cairn:reconcile`'s own step 4, and `cairn-reconcile.py verify` (Plan 17-01) already mechanically re-checks every citation in it before a human ever sees it.
- The closed `recommended_action.type` vocabulary (`bd_close`/`bd_reopen`/`manual_review`) is fixed in both the agent's own instructions and this summary — Plan 17-03's applier should treat any other value as a schema violation, never attempt to interpret a fourth type.
- No blockers. The one open, explicitly-documented gap (context-mode memory not granted to the investigator) does not block Plan 17-03, since it only affects how thorough the investigator's own reasoning can be, not the schema or the write-incapacity guarantee Plan 17-03 depends on.

---
*Phase: 17-semantic-escalation*
*Completed: 2026-07-31*

## Self-Check: PASSED

All three created files found on disk (`cairn/agents/reconcile-investigator.md`, `cairn/commands/reconcile.md`, `tests/cairn-reconcile-agent.bats`), plus this SUMMARY. All three task commits (`a99225c`, `5af3036`, `c87faab`) confirmed present in `git log`.
