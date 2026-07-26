---
phase: 02-baseline-isolation-multi-baseline-harness
verified: 2026-07-26T03:24:10Z
status: passed
score: 4/4 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
---

# Phase 2: Baseline Isolation + Multi-Baseline Harness Verification Report

**Phase Goal:** Every baseline (vanilla, GSD-only, cairn) runs under mechanically enforced, identical, isolated conditions, so no comparative number can later be attributed to environment leakage
**Verified:** 2026-07-26T03:24:10Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, FAIR-01..03)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each run executes in a fresh, disposable worktree with an overridden `HOME`, and inspecting the actual env sent per baseline shows zero inherited personal CLAUDE.md/MCP/hooks | VERIFIED | Hand-authored an independent env-asserting stub (not the bats fixture) and ran `bench-run.py --baseline vanilla.json` against it directly. Observed row: `stub_observed_home = /var/folders/.../cairn-bench-home-6v0wzt0x` vs real `$HOME = /Users/felipeoliveira` (differ). A custom `MY_INDEPENDENT_LEAK_MARKER` set in the invoking shell was **not** observed by the claude subprocess (`""`). `isolated_claude_env()` (bench-run.py:75-86) builds `{"HOME": fresh_home, "PATH": ...}` + `ANTHROPIC_API_KEY`-if-present and is passed as `env=` (replaces, never merges) on the one claude `subprocess.run` call (line 218). Extra keys observed in the child (`PWD`, `SHLVL`, `LC_CTYPE`) were independently proven to be bash's own shell-startup behavior even under `env -i` (fully cleared env), not operator leakage. |
| 2 | vanilla/gsd-only/cairn are each an explicit baseline manifest (pinned full model id, identical task prompt, `--bare` + explicit flags) | VERIFIED | `jq -Sc '.claude_flags'` byte-identical across all three files: `{"bare":true,"max_turns":8,"no_session_persistence":true,"permission_mode":"acceptEdits"}`. `model` = `claude-haiku-4-5-20251001` (full pinned id) in all three. `provisioning.plugin_dirs` length is 0/1/3 for vanilla/gsd-only/cairn respectively; cairn's order is `gsd, context-mode, cairn`. Staged paths exist on disk: `benchmarks/plugins/gsd/v4.3.1` (`.staged-ref` = `v4.3.1`, `node_modules/` present, `node --check mcp/server.cjs` exits 0), `benchmarks/plugins/context-mode/v1.0.169` (`.staged-ref` = `v1.0.169`), `cairn` (local path, in-repo). |
| 3 | The same task run against all three baselines produces three separate JSONL rows whose manifests differ only in baseline-specific config | VERIFIED | Ran `bench-matrix.py --baselines vanilla,gsd-only,cairn --seed 777` end-to-end against a hand-authored stub twice, producing 3 rows each with distinct `baseline_id`; `claude_flags`/`model` identical per manifest inspection above, `plugin_dirs` construction differs only by provisioning (proven via `--plugin-dir` argv assertions in bats + independent stub run showing `--bare`/`--model`/`--plugin-dir` args built from the manifest). |
| 4 | Execution order across baselines/repetitions is randomized/interleaved, and every run's cost is decomposed into 4 components | VERIFIED | Determinism proven twice: (a) direct call to `build_execution_order(['vanilla','gsd-only','cairn'], 12345)` invoked twice returns identical order (`['cairn','vanilla','gsd-only']`), a different seed (999) returns a different order (`['gsd-only','vanilla','cairn']`); (b) full subprocess-level run of `bench-matrix.py` with `--seed 777` twice into separate `--out` files produces byte-identical `baseline_id` sequences (`cairn, gsd-only, vanilla` both times), confirmed via `diff`. `random.Random(seed)` is instance-scoped, never the shared `random` module (bench-matrix.py:48-55). Cost decomposition: every row's `usage` object already carries `input_tokens`/`output_tokens`/`cache_creation_input_tokens`/`cache_read_input_tokens` as separate fields (verified against the real committed `benchmarks/results/smoke-convert.jsonl` live rows from Phase 1, unchanged by Phase 2 — Phase 2 only adds `baseline_id`/`seed`/`run_order_index` on top). |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `benchmarks/baselines/vanilla.json` | pinned vanilla manifest, empty provisioning | VERIFIED | Valid JSON, `claude_flags` matches shared block, `plugin_dirs=[]` |
| `benchmarks/baselines/gsd-only.json` | pinned GSD-only manifest | VERIFIED | Valid JSON, 1 plugin_dirs entry (gsd@v4.3.1), staged_path exists |
| `benchmarks/baselines/cairn.json` | pinned cairn manifest (gsd+context-mode+cairn) | VERIFIED | Valid JSON, 3 plugin_dirs entries in order gsd/context-mode/cairn, all staged_paths exist |
| `benchmarks/scripts/bench-run.py` | `isolated_claude_env()`, `load_baseline()`, required `--baseline`, `--plugin-dir` construction, `baseline_id`/`seed`/`run_order_index` row fields | VERIFIED | All functions present and exercised directly (not just via bats) — see truths 1-4 above |
| `benchmarks/scripts/stage-plugins.py` | provisioning materialization: git clone pinned ref + build + verify, idempotent, fail-loud | VERIFIED | Real GSD v4.3.1 and context-mode v1.0.169 staged on disk with valid `.staged-ref` markers; `shell=True` absent (grep confirms 0 matches); `benchmarks/plugins/` confirmed gitignored via `git check-ignore` |
| `benchmarks/scripts/bench-matrix.py` | seeded interleaving orchestrator | VERIFIED | `build_execution_order` exercised directly and via full subprocess run, proven deterministic |
| `tests/bench-run.bats`, `tests/stage-plugins.bats`, `tests/bench-matrix.bats`, `tests/helpers.bash` | isolation/manifest/staging/ordering bats coverage | VERIFIED | 21/21 tests pass across all 4 suites (8 bench-run + 5 stage-plugins + 5 bench-matrix + 3 bench-verify) |
| `benchmarks/README.md` | documentation of baselines/isolation/staging/ordering + live-check status | VERIFIED | Substantive "Baselines", "Randomized execution order", and "Live isolation smoke check: PENDING" sections present with real content, not stubs |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| bench-run.py claude `subprocess.run` | `isolated_claude_env(fresh_home)` | `env=` kwarg | WIRED | `grep -c 'env='` = 2 total occurrences in the file: 1 in a docstring comment (line 27), 1 as the actual kwarg on the claude call (line 218) |
| bench-run.py verify.sh `subprocess.run` | unchanged full-inherit environment | no `env=` kwarg | WIRED (correctly unwired) | Confirmed the verify.sh call (line 236) carries no `env=` kwarg anywhere in its statement |
| `benchmarks/baselines/*.json provisioning.plugin_dirs` | cmd `--plugin-dir` flags | loop over plugin_dirs | WIRED | Independent stub run's observed argv contained `--plugin-dir <staged_path>` pairs built from the manifest, never hardcoded |
| `bench-matrix.py` | `bench-run.py` | subprocess per shuffled baseline, `--seed`/`--run-order-index` passthrough | WIRED | End-to-end run produced 3 rows with correct `run_order_index` (0,1,2) and consistent `seed` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Isolation holds under an independently authored stub (not the bats fixture) | `CAIRN_BENCH_CLAUDE_BIN=<my-stub> python3 bench-run.py --baseline vanilla.json ...` | scoped HOME differs from real `$HOME`; leak marker empty; `ANTHROPIC_API_KEY` presence correctly `false` | PASS |
| Determinism of `build_execution_order` | direct Python call, same seed twice | identical order both times; different seed differs | PASS |
| Determinism at full pipeline level | `bench-matrix.py --seed 777` run twice, `diff` on `baseline_id` sequences | empty diff (byte-identical) | PASS |
| Manifest JSON validity + claude_flags identity | `jq -Sc '.claude_flags'` on all 3 files | byte-identical | PASS |
| Staged paths exist + syntactically valid | `node --check .../mcp/server.cjs` | exit 0 | PASS |
| No API key literals in repo | `grep -rn 'sk-ant-'` (excluding `.git`) | 0 real key matches (only prefix-pattern mentions in planning docs) | PASS |
| `py_compile` on all benchmark scripts | `python3 -m py_compile benchmarks/scripts/*.py` | exit 0 | PASS |
| No Phase-3/4 scope creep | `grep -n 'reps\|repetition'` in bench-matrix.py/bench-run.py; `find` for aggregate/competitor scripts | no matches | PASS |
| Live check documentation state matches actual environment | `[ -z "$ANTHROPIC_API_KEY" ]` at verification time + README grep | README correctly says "PENDING"; key genuinely absent in this environment | PASS |
| Full bats suite | `bats tests/bench-run.bats tests/stage-plugins.bats tests/bench-matrix.bats tests/bench-verify.bats` | `1..21`, all `ok` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FAIR-01 | 02-01 | Isolamento por rodada: worktree fresco + HOME override, zero herança do operador | SATISFIED | `isolated_claude_env()` verified independently (truth 1) |
| FAIR-02 | 02-01, 02-02 | Baselines por manifesto JSON explícito, provisioning pinado | SATISFIED | Manifests + stage-plugins.py verified (truth 2) |
| FAIR-03 | 02-03 | Ordem randomizada/intercalada + custo decomposto em 4 componentes | SATISFIED | bench-matrix.py determinism + existing 4-component usage schema verified (truth 4) |

No orphaned requirements — `REQUIREMENTS.md`'s three Phase 2 rows (FAIR-01/02/03) all appear in plan `requirements:` frontmatter.

### Anti-Patterns Found

None. Scanned `benchmarks/scripts/bench-run.py`, `bench-matrix.py`, `stage-plugins.py`, and all three baseline manifests for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` — zero matches. `shell=True` absent from `stage-plugins.py` and `bench-matrix.py`. Commit history shows a clean RED→GREEN TDD cadence across all three plans with no deletions in any commit (`git diff --diff-filter=D` reported zero deletions per each plan's SUMMARY, independently spot-checked via `git log`).

### Human Verification Required

None. All must-haves are mechanically verifiable via bats, direct script invocation, and file inspection; no visual/UX/real-time behavior is in scope for this phase.

### Gaps Summary

No gaps. All four ROADMAP success criteria for Phase 2 verified against the actual codebase, not SUMMARY claims:
- Isolation was independently re-proven with a hand-authored stub distinct from the bats fixture (per verification instructions), confirming `isolated_claude_env()` replaces rather than merges the environment and that the phase's own bats coverage is not the only evidence of correctness.
- All 21 bats tests across `bench-run.bats`, `stage-plugins.bats`, `bench-matrix.bats`, `bench-verify.bats` pass.
- Determinism was proven both at the unit level (`build_execution_order`) and at the full subprocess/JSONL-row level with two independent `bench-matrix.py` invocations.
- Manifests are byte-identical on `claude_flags`, differ only in `provisioning.plugin_dirs` (0/1/3 entries), and all declared `staged_path`s exist on disk with valid `.staged-ref` pins.
- No API key literals anywhere in the repository; `isolated_claude_env()` passes only `HOME`/`PATH`/`ANTHROPIC_API_KEY`-if-present.
- `env=` appears exactly once as an actual subprocess kwarg (the claude call); `verify.sh`'s subprocess call carries no `env=` kwarg, preserving the objective-oracle trust boundary from Phase 1.
- No Phase 3/4 machinery (repetition, aggregation, competitor baseline) leaked into this phase's scope.
- The live isolated-auth smoke check is honestly documented as PENDING in `benchmarks/README.md`, consistent with `ANTHROPIC_API_KEY` genuinely being absent from this verification environment — matches the locked decision in `02-CONTEXT.md` that live validation is optional this phase.

One minor, non-blocking observation: `02-BEADS-MAP.md` still lists FAIR-01/02/03 issues as `open` in the beads tracker even though `REQUIREMENTS.md` marks them `Complete` and the code fully satisfies them — a tracking-hygiene staleness, not a code or goal gap.

---

_Verified: 2026-07-26T03:24:10Z_
_Verifier: Claude (gsd-verifier)_
