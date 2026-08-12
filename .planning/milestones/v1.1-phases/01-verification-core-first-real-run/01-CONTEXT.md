# Phase 1: Verification Core + First Real Run - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning
**Source:** Autonomous run (`/cairn:autonomous`) — decisions locked from committed project research (`.planning/research/`); no interactive discussion. Gray areas below are Claude's Discretion by design.

<domain>
## Phase Boundary

Prove the harness's two riskiest primitives before anything is built on top of them: (1) an objective, agent-unwritable pass/fail check per benchmark task (`verify.sh`, exit code is the verdict), and (2) one real `claude -p --output-format json` invocation validating the result-JSON schema assumptions. Deliverables map to HARN-01, HARN-02, HARN-03. bd issues: CairnGo-bur (HARN-01), CairnGo-9f5 (HARN-02), CairnGo-pgp (HARN-03) — see `01-BEADS-MAP.md`.

</domain>

<decisions>
## Implementation Decisions (locked — from research + approved roadmap)

### House style
- python3 **stdlib-only** + thin bash wrapper, exactly like `cairn/scripts/` (shebang, docstring-contract with Usage/Behavior/Exit codes, `die()` helper, `--json` flag convention).
- Manifests/config are **JSON, not YAML** (stdlib has no YAML parser — deliberate deviation from SWE-bench's task.yaml).

### Verification (HARN-01)
- Per-task `verify.sh`: exit code = pass/fail. Never LLM self-report. The agent under test must not be able to rewrite it (it lives outside the agent's working tree; staged in read-only or copied fresh per run).
- Task fixture = disposable repo tree + task prompt + `verify.sh`, bats-testable with zero API cost.

### Runner (HARN-02)
- `claude -p --output-format json` is the primary measurement source: `total_cost_usd`, `usage.{input,output,cache_creation,cache_read}_tokens`, `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`, `session_id` (verified against official docs in STACK.md).
- One raw JSONL row per run appended to a results file; external wall-clock measured by the runner itself (python `time.time()`).
- Exactly **one real `claude -p` call** happens in this phase, at the end, to validate the schema live — smallest possible task, cost documented in the SUMMARY. Everything else runs against the stub.

### Testability (HARN-03)
- `claude` binary reached through an env-var seam (e.g. `BENCH_CLAUDE_BIN`, mirroring the existing `CAIRN_GBSYNC`-style stub seams) — bats stubs it; CI never pays API.

### Layout
- New top-level `benchmarks/` directory (tasks/, harness scripts follow house naming `bench-*.py` + `.sh` wrappers); tests in `tests/` as `bench-*.bats` reusing `tests/helpers.bash`.

### Claude's Discretion
- Exact `benchmarks/` subtree layout, JSONL field order, the content of the first fixture task, stub output shape, and how the single live validation run is triggered (flag vs separate script).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research (project-level, committed)
- `.planning/research/ARCHITECTURE.md` — component boundaries, data flow, 8-step build order (this phase = steps 1-2)
- `.planning/research/STACK.md` — verified `claude -p` JSON schema, flags, isolation notes
- `.planning/research/PITFALLS.md` — success-gating (pitfall 6) is THE hard gate this phase establishes
- `.planning/research/SUMMARY.md` — synthesis

### House style
- `cairn/scripts/cairn-map.py`, `cairn/scripts/cairn-status.py` — script contract molds
- `tests/helpers.bash`, `tests/cairn-status.bats` — bats patterns, PATH-stub technique
- `.planning/codebase/TESTING.md`, `.planning/codebase/CONVENTIONS.md`

</canonical_refs>

<specifics>
## Specific Ideas

- Requirements text (REQUIREMENTS.md HARN-01..03) is the acceptance bar verbatim.
- The single live run doubles as the phase's proof artifact: its JSONL row gets committed as the first real data point.

</specifics>

<deferred>
## Deferred Ideas

- Multi-baseline manifests, isolation (HOME override, worktrees) — Phase 2.
- Repetition/aggregation — Phase 3. Never build ahead of the current phase.

</deferred>

---
*Phase: 01-verification-core-first-real-run*
*Context gathered: 2026-07-25 via autonomous run*
