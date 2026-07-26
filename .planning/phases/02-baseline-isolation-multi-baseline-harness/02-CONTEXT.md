# Phase 2: Baseline Isolation + Multi-Baseline Harness - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning
**Source:** Autonomous run — decisions locked from project research + **Phase 1 live findings**. Gray areas are Claude's Discretion.

<domain>
## Phase Boundary

Every benchmark run executes in a fresh, disposable, mechanically-isolated environment with explicit pinned configuration, across three baselines: vanilla Claude Code, GSD-only, and cairn. Requirements: FAIR-01 (isolation), FAIR-02 (baseline manifests), FAIR-03 (order randomization + 4-way cost decomposition). bd issues: CairnGo-60i, CairnGo-gc1, CairnGo-9bb — see `02-BEADS-MAP.md`.

</domain>

<decisions>
## Implementation Decisions (locked)

### Phase 1 live findings that BIND this phase
- **`--bare` requires API-key auth**: verified live — `--bare` skips claude.ai OAuth and reports "Not logged in". Isolated baselines therefore authenticate via `ANTHROPIC_API_KEY` (env), never the operator's OAuth keychain. The key is read from the environment at run time, NEVER stored in any file this repo commits.
- **Home-field overhead is real and measured**: the operator's global environment injected 45-62k cache-creation tokens into Phase 1's non-isolated runs. Isolation (fresh `HOME`, `--bare`, explicit flags) is what removes it — this number is the baseline motivation, cite it.
- **Model comes from manifests as a full pinned id** (already enforced by bench-run.py + task.json).
- **Parse stdout regardless of exit code**; `is_error` ⊥ `verify_passed` (both proven live).

### Isolation mechanics (FAIR-01)
- Fresh disposable workdir per run (already exists) PLUS scoped `HOME` override (empty temp HOME per run) so no global CLAUDE.md/MCP/hooks/settings leak into any baseline.
- The cairn/GSD baselines get their plugins provisioned EXPLICITLY inside the isolated environment (that is the baseline's payload), never inherited from the operator.

### Baseline manifests (FAIR-02)
- `benchmarks/baselines/<name>.json`: pinned model id, claude flags (`--bare`, `--max-turns`, `--no-session-persistence`, permission mode), and the baseline's provisioning recipe (what gets installed into the isolated HOME). Vanilla = empty provisioning.
- Same task prompt, same fixture, same flags across all baselines — only the provisioning differs.

### Randomization + cost decomposition (FAIR-03)
- Run order across baselines randomized/interleaved (seeded, seed recorded in the row for reproducibility — stdlib `random.Random(seed)`).
- Every row already carries the 4 usage components; the aggregation stays Phase 3 — this phase only guarantees the fields are captured per-baseline and the execution order is recorded.

### Test strategy (stub-first — CI stays $0)
- ALL mechanics (HOME override, provisioning staging, manifest parsing, order randomization, seed recording) proven via the `CAIRN_BENCH_CLAUDE_BIN` stub in bats. The stub can ASSERT on its inherited env (e.g. print `$HOME` and env leakage markers into its canned output) — that's how isolation is tested at $0.
- **Live validation of isolated auth is OPTIONAL in this phase**: it requires `ANTHROPIC_API_KEY` in the operator's env. If the key is absent at execution time, deliver the mechanism + stub proofs, document the single pending live check in the SUMMARY (pending key, not a mechanism gap), and do NOT block the phase. If the key IS present, run at most ONE cheap live isolated run (haiku, smoke task) to prove the auth path, and record its cost.

### Research open questions — resolved by the autonomous run (2026-07-25)
- **The cairn arm INCLUDES context-mode.** Rationale: cairn's plugin.json declares it a hard dependency and `/cairn:init` installs it — the benchmark measures the product as it actually ships. Excluding it would be an artificial arm (and would rightly draw "rigged baseline" criticism). The manifest documents this composition explicitly.
- **Plugin dependencies are enumerated explicitly** in each manifest's provisioning recipe (one `--plugin-dir` entry per plugin) — never rely on auto-resolution (unverified behavior).
- **GSD source pinned to the identifier that resolves today** (`buildomator/buildomator`, verified live 2026-07-25; formerly `jnuyens/gsd-plugin`) — record both in the manifest comment.

### Claude's Discretion
- Exact manifest schema fields, HOME staging layout, how provisioning recipes are expressed, randomization CLI surface (flag vs manifest), whether bench-run grows `--baseline` flag vs a new orchestrating script (respect ARCHITECTURE.md's component split).

</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/01-verification-core-first-real-run/01-VERIFICATION.md` + `01-03-SUMMARY.md` — what Phase 1 proved, live findings
- `benchmarks/README.md` — methodology + observed schema/costs (extend, don't contradict)
- `benchmarks/scripts/bench-run.py` — the runner this phase extends
- `.planning/research/ARCHITECTURE.md` — component split (runner vs orchestrator), build order steps 3
- `.planning/research/PITFALLS.md` — pitfalls 3-5 (home-field, misconfigured arm, contamination)
- `tests/bench-run.bats`, `tests/helpers.bash` — stub patterns to extend

</canonical_refs>

<specifics>
## Specific Ideas

- The stub-asserts-its-environment trick: canned stub prints its `$HOME` and selected env vars into the fake JSON payload → bats asserts the harness passed a scoped HOME and a clean env. Isolation becomes a black-box-testable contract.

</specifics>

<deferred>
## Deferred Ideas

- N repetitions/aggregation/statistics — Phase 3. Competitor baseline — Phase 4. Corpus growth — Phase 5.

</deferred>

---
*Phase: 02-baseline-isolation-multi-baseline-harness*
*Context gathered: 2026-07-25 via autonomous run*
