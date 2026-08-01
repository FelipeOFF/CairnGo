---
phase: 15-phase-lease
plan: "02"
subsystem: infra
tags: [bd, beads, git-worktree, cairn-capability, bash, bats]

# Dependency graph
requires:
  - phase: 15-phase-lease (Plan 15-01)
    provides: "cairn-lease.py/.sh acquire/release/renew/status subcommands, the single TTL/staleness authority"
provides:
  - "cairn/capability/scripts/cairn-lease.sh: a locator/delegator shim (mirrors cairn-map.sh) that resolves cairn-lease.py in the capability-bundle context, where ${CLAUDE_PLUGIN_ROOT} cannot be trusted"
  - "the phase lease wired into its two entry points: work.md (session-start acquire) and execute-wave-pre.md (per-wave heartbeat acquire)"
  - "the phase lease wired into its one exit point: verify-post.md (unconditional, once-per-phase release)"
affects: [15-03, 15-04, 15-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "capability-fragment CAP-locator pattern (\"CAP=.gsd/capabilities/cairn; [ -d \\\"$CAP\\\" ] || CAP=...\") applied to a third script (cairn-lease.sh), keeping ${CLAUDE_PLUGIN_ROOT} exclusively for genuine cairn commands like work.md"
    - "self-contained CAP= recomputation at each insertion point in a fragment, rather than reusing a variable set earlier in the same file, so paragraph order can never silently break resolution"

key-files:
  created:
    - cairn/capability/scripts/cairn-lease.sh
  modified:
    - cairn/commands/work.md
    - cairn/capability/fragments/execute-wave-pre.md
    - cairn/capability/fragments/verify-post.md
    - tests/capability.bats

key-decisions:
  - "cairn-lease.sh (bundle shim) is a pure locator/delegator, structurally identical to cairn-map.sh, with zero lease/TTL/metadata logic of its own — that logic has exactly one implementation, cairn-lease.py (Plan 15-01)"
  - "work.md keeps ${CLAUDE_PLUGIN_ROOT} (it is a genuine cairn command); execute-wave-pre.md and verify-post.md use the CAP-locator pattern (they are capability fragments injected into GSD's own executor/orchestrator, where ${CLAUDE_PLUGIN_ROOT} would resolve to gsd-core's root during a bare /gsd:* run)"
  - "verify-post.md recomputes its own CAP= block at the lease-release insertion point rather than reusing the block already computed earlier in the file for cairn-loop-gate.sh — two identical two-line blocks, deliberately, so neither paragraph depends on file ordering"
  - "acquisition happens twice by design: once in work.md (session start) and again in execute-wave-pre.md (every wave), the latter existing specifically to keep the lease's heartbeat fresh across a long multi-wave execution that outlives a single session-start renewal"
  - "release happens exactly once, in verify-post.md, unconditionally — it does not check who holds the lease first, because verification reaching that point at all means the phase's cycle is over regardless of which worktree ran it"

requirements-completed: [LEASE-01, LEASE-02, LEASE-04]

coverage:
  - id: D1
    description: "cairn-lease.sh (capability bundle) locates and delegates to the real cairn-lease.py using the same four-tier resolution as cairn-map.sh, proven with both CAIRN_PLUGIN_ROOT and CLAUDE_PLUGIN_ROOT absent (the literal outside-a-/cairn:*-session scenario)"
    requirement: "LEASE-01"
    verification:
      - kind: integration
        ref: "tests/capability.bats#bundle lease shim resolves the dev-checkout generator and delegates identically to the direct script"
        status: pass
      - kind: integration
        ref: "tests/capability.bats#bundle lease shim honors the .cairn/plugin-root pointer from an installed layout, outside a /cairn:*-initiated session"
        status: pass
      - kind: integration
        ref: "tests/capability.bats#bundle lease shim warns and exits 0 when no resolution tier finds cairn-lease.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "the shim contains zero lease/TTL/metadata logic of its own — grep for heartbeat or LEASE_TTL in the file finds nothing"
    verification:
      - kind: other
        ref: "grep -c 'heartbeat\\|LEASE_TTL' cairn/capability/scripts/cairn-lease.sh -> 0 matches"
        status: pass
    human_judgment: false
  - id: D3
    description: "work.md acquires the phase lease as its new first step via ${CLAUDE_PLUGIN_ROOT}, surfaces a held-elsewhere report (exit 3) verbatim, and continues regardless into the per-plan claim loop"
    requirement: "LEASE-01"
    verification:
      - kind: manual_procedural
        ref: "cairn/commands/work.md step 1 (read-through) + grep -n cairn-lease/CLAUDE_PLUGIN_ROOT"
        status: pass
    human_judgment: false
  - id: D4
    description: "execute-wave-pre.md re-acquires the lease before every wave (the heartbeat rationale is stated verbatim as reasoning, not just an instruction), and verify-post.md releases it exactly once, unconditionally, pass or fail, via a self-contained CAP= block distinct from the one already used for cairn-loop-gate.sh"
    requirement: "LEASE-02"
    verification:
      - kind: other
        ref: "grep -cF 'CAP=\".gsd/capabilities/cairn\"; [ -d \"$CAP\" ] || CAP=\"${GSD_HOME:-$HOME}/.gsd/capabilities/cairn\"' cairn/capability/fragments/verify-post.md -> 2"
        status: pass
      - kind: manual_procedural
        ref: "cairn/capability/fragments/execute-wave-pre.md + verify-post.md (read-through)"
        status: pass
    human_judgment: false

# Metrics
duration: 14min
completed: 2026-07-31
status: complete
---

# Phase 15 Plan 02: Phase lease Summary

**The phase lease built in Plan 15-01 is now reachable from both invocation contexts — a vendored `cairn-lease.sh` bundle shim (mirroring `cairn-map.sh`'s locator pattern) lets `execute-wave-pre.md` and `verify-post.md` resolve it correctly even when `${CLAUDE_PLUGIN_ROOT}` points at gsd-core during a bare `/gsd:*` run, while `work.md` keeps `${CLAUDE_PLUGIN_ROOT}` as a genuine cairn command.**

## Performance

- **Duration:** ~14 min
- **Completed:** 2026-07-31T00:11:32-03:00
- **Tasks:** 2 (Task 1: tracer/TDD, Task 2: tracer)
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments
- `cairn/capability/scripts/cairn-lease.sh`: a locator/delegator shim, structurally identical to `cairn-map.sh` — same four-tier resolution order, same `.beads/`/`cairn.enabled` guards (copied verbatim), same "warn to stderr, exit 0" degrade. Contains zero lease/TTL/metadata logic of its own.
- Three new `tests/capability.bats` cases prove the shim actually works outside a `/cairn:*`-initiated session: dev-checkout delegation is byte-identical to the direct script, the `.cairn/plugin-root` pointer resolves with both `CAIRN_PLUGIN_ROOT` and `CLAUDE_PLUGIN_ROOT` neutralized (with a follow-up `status` call proving the underlying `bd` write actually landed, not just "exit 0"), and the no-tier-resolves path degrades correctly.
- `work.md` gained a new first step: acquire the phase lease via `${CLAUDE_PLUGIN_ROOT}` (correct there — it's a genuine cairn command) before the per-plan claim loop, surfacing a held-elsewhere report (exit 3) verbatim and continuing regardless (D-04).
- `execute-wave-pre.md` gained a per-wave re-acquire via the CAP-locator pattern, with the heartbeat rationale stated explicitly: session-start renews once, but a long multi-wave execution needs the lease refreshed at every wave or it would read as stale mid-execution even while the same worktree is actively working it.
- `verify-post.md` gained the phase's single, unconditional release point — pass or fail — using a self-contained `CAP=` block recomputed at the release insertion point rather than reused from the earlier `cairn-loop-gate.sh` call, so the two paragraphs' correctness never depends on file ordering.

## Task Commits

Each task was committed atomically:

1. **Task 1: vendor the capability-bundle lease shim** - `165ce94` (feat) — shim + 3 new bats tests, all 20 `tests/capability.bats` cases pass.
2. **Task 2: wire acquire/release into work.md, execute-wave-pre.md, verify-post.md** - `4b1a603` (feat) — prose-only wiring across the three files.

## Files Created/Modified
- `cairn/capability/scripts/cairn-lease.sh` (created) - locator/delegator shim, mirrors `cairn-map.sh`
- `cairn/commands/work.md` (modified) - new step 1: acquire the phase lease via `${CLAUDE_PLUGIN_ROOT}`; existing steps 1-5 renumbered to 2-6
- `cairn/capability/fragments/execute-wave-pre.md` (modified) - new paragraph: per-wave re-acquire via the CAP-locator pattern, before the existing beads-claim step
- `cairn/capability/fragments/verify-post.md` (modified) - new section: unconditional, once-per-phase release via a self-contained `CAP=` block
- `tests/capability.bats` (modified) - `LEASE_SHIM`/`LEASE_DIRECT` declarations + 3 new tests mirroring the existing `MAP_SHIM` dev-checkout and plugin-root-pointer tests

## Decisions Made
- Followed the plan's explicit instruction to recompute `CAP=` at `verify-post.md`'s own release insertion point rather than reuse the variable already set earlier in the file for `cairn-loop-gate.sh`, even though both resolve identically today — verified via `grep -cF` returning 2, not 1.
- Kept `work.md` on `${CLAUDE_PLUGIN_ROOT}` unchanged, per the plan's explicit warning not to "fix" it to match the fragments — it is a genuine cairn command, not a fragment injected into another plugin's context.
- Reworded two "never a stop condition" / "never a hard stop" phrases in `work.md` to "never a reason to block" / "degrades the same non-blocking way" after noticing the literal word "stop" would otherwise appear near the acquire step — the plan's own acceptance criterion greps for "stop"/"abort" near acquire/release and expects zero matches, even though the original phrasing was semantically a negation (documenting the *absence* of blocking behavior). Reworded to satisfy the literal grep-able criterion without changing the meaning.
- The three new bats tests exceed the plan action text's literal "two sibling tests" in favor of covering all three behaviors the task's own `acceptance_criteria` enumerate (dev-checkout equivalence, plugin-root-pointer with a proven real `bd` write, and the no-tier-resolves degrade path) — the `acceptance_criteria` list is more specific than the summarizing prose and was treated as the actual bar.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - missing acceptance-criteria coverage] Added a third bats test for the shim's degrade path**
- **Found during:** Task 1
- **Issue:** The task's `<action>` prose describes "two sibling tests," but its own `<acceptance_criteria>` list enumerates three distinct provable behaviors, the third being the no-tier-resolves warn-and-exit-0 degrade path (mirroring `cairn-map.sh`'s own accepted T-15-09 disposition). Two tests alone would not exercise that third criterion.
- **Fix:** Added `"bundle lease shim warns and exits 0 when no resolution tier finds cairn-lease.py"` as a third test, reusing the same fake-install fixture minus the `.cairn/plugin-root` pointer.
- **Files modified:** `tests/capability.bats`
- **Commit:** `165ce94`

**2. [Rule 1 - literal criterion not satisfied] Removed the literal substring "stop" from work.md's acquire step**
- **Found during:** Task 2
- **Issue:** The plan's Task 2 `<acceptance_criteria>` states "grep for the word 'stop' or 'abort' near any acquire/release step finds nothing." My first draft of `work.md`'s new step used "never a stop condition" / "never a hard stop" to describe the exit-3 and exit-5 non-blocking behavior — semantically correct (a negation), but it would fail the literal grep.
- **Fix:** Reworded to "never a reason to block" and "degrades the same non-blocking way," preserving the exact same meaning without the literal substring.
- **Files modified:** `cairn/commands/work.md`
- **Commit:** `4b1a603`

## Issues Encountered

None beyond the two items documented above as deviations. Both `bd` and `git worktree` behaved as expected throughout; no auth gates, no blocked commands.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The phase lease is now reachable through both entry points and its one exit point, in both invocation contexts (`/cairn:work` and a bare `/gsd:execute-phase`). Plans 15-03 (doctor check for a stale/orphaned lease) and 15-05 (status-panel footer line) can build directly on `cairn-lease.py status --all --json`, unaffected by this plan's changes (Plan 15-01's contract, untouched here). No blockers.

---
*Phase: 15-phase-lease*
*Completed: 2026-07-31*

## Self-Check: PASSED

All 5 referenced files found on disk; both task commits (`165ce94`, `4b1a603`) found in git history.
