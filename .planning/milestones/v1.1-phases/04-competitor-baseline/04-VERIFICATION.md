---
phase: 04-competitor-baseline
verified: 2026-07-26T06:01:38Z
status: gaps_found
score: 8/9 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
gaps:
  - truth: "The same task, run N≥5 times against the competitor baseline, appears in `aggregated.json` alongside the other three arms (ROADMAP Phase 4 Success Criterion 4)"
    status: failed
    severity: minor
    reason: "No aggregated.json exists anywhere in the repository (for any of the 4 arms, not just the competitor) — the N≥5 live matrix has genuinely never been run. This requires real ANTHROPIC_API_KEY spend, which is confirmed absent in this environment (re-checked independently, matches SUMMARY/README's own PENDING claim). 04-CONTEXT.md's own 'Deferred Ideas' section explicitly defers this: 'Running the full N=5 live matrix — data collection happens when the corpus exists (Phase 5/6 boundary).' The plan's own must_haves frontmatter (correctly, per this locked decision) never claimed this SC — it scoped only the manifest/wiring/load-check. All underlying capability needed to eventually satisfy this SC is independently proven correct (pipeline plumbing, aggregation logic, fairness) — what's missing is the live data itself, an operator-authorized-spend decision, not a code defect."
    artifacts:
      - path: "benchmarks/results/aggregated.json"
        issue: "Does not exist. Only benchmarks/results/smoke-convert.jsonl (2 rows, from Phase 1's live validation) is present."
    missing:
      - "Run `bench-matrix.py --baselines vanilla,gsd-only,cairn,competitor-ralph-specum --reps 5 --seed <N> --task benchmarks/tasks/smoke-convert --out <path>.jsonl` for real once ANTHROPIC_API_KEY is available, then `bench-aggregate.py --in <path>.jsonl --out benchmarks/results/aggregated.json`."
      - "Alternatively, accept an explicit override (see suggestion below) deferring this to Phase 5/6's data-collection step, consistent with 04-CONTEXT.md's own locked decision."
deferred: []
---

# Phase 4: Competitor Baseline Verification Report

**Phase Goal:** A competing workflow plugin is benchmarked as a legitimate fourth arm — configured strictly from its own official defaults, version-pinned, and run through the identical isolated pipeline — so the comparison cannot be dismissed as sabotaged or unfairly configured
**Verified:** 2026-07-26T06:01:38Z
**Status:** gaps_found (1 minor, non-blocking gap)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, COMP-01)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The competitor's baseline manifest is configured strictly from its own official quickstart/documented defaults, with plugin version or commit pinned and recorded | VERIFIED | `competitor-ralph-specum.json`'s `provisioning.plugin_dirs[0].source.ref == "v4.0.0"`, `.repo == "tzachbon/smart-ralph"`. Independently re-ran `git ls-remote --tags https://github.com/tzachbon/smart-ralph.git` — confirmed `v4.0.0` (`5012c8f`→`d6fba6a`) IS the newest real tag (v2.0.0, v3.1.1, v4.0.0 only). `defaults_source` field is non-empty and cites exact vendor doc sections (README Quick Start + `quick-mode.md`). |
| 2 | The competitor runs headless through the same isolated-worktree + `--bare` + fresh-`HOME` pipeline as vanilla/GSD-only/cairn, producing directly comparable JSONL rows | VERIFIED | Independently ran `bench-run.py --baseline competitor-ralph-specum.json` against my own hand-authored stub (distinct from the bats fixture). Produced a valid JSONL row with `baseline_id: "competitor-ralph-specum"` through the exact same `isolated_claude_env()`/argv-construction code path used by vanilla/gsd-only/cairn — no baseline-specific branching exists in the pipeline. |
| 3 | The competitor's configuration is reviewed against its own documentation as an explicit re-verification checkpoint before any comparative results are generated | VERIFIED | The pin was re-confirmed live via `git ls-remote --tags` before the manifest was written (Task 1, reproduced independently above); `defaults_source` is the auditable citation trail; 3 dedicated bats tests plus a documented live `/help` load-check constitute the checkpoint. No comparative results (aggregated.json) have been generated yet — the checkpoint precedes them as required. |
| 4 | The same task, run N≥5 times against the competitor baseline, appears in `aggregated.json` alongside the other three arms | **FAILED** | No `aggregated.json` exists anywhere in the repository (confirmed via `find . -iname aggregated.json` — zero results, git-tracked or gitignored). This is not solely a competitor-arm gap: no baseline has ever been run through the full N≥5 live matrix. Blocked on `ANTHROPIC_API_KEY` (confirmed absent independently). See Gaps Summary. |

**Score:** 3/4 ROADMAP truths verified (1 gap, see below)

### PLAN.md-Level Must-Haves (04-01 frontmatter)

| Must-have | Status | Evidence |
|-----------|--------|----------|
| Manifest pins exact immutable tag `v4.0.0` + `defaults_source` field | VERIFIED | Confirmed above (truth 1) |
| `model`/`claude_flags` byte-identical to vanilla/gsd-only/cairn | VERIFIED | `jq -S '{model,claude_flags}'` on all 4 manifests independently — byte-identical output across all 4: `{"bare":true,"max_turns":8,"no_session_persistence":true,"permission_mode":"acceptEdits"}`, `model: "claude-haiku-4-5-20251001"` |
| `bench-run.py` resolves nested `--plugin-dir` target (`staged_path` + `plugin_dir_subpath`) without changing behavior for manifests that omit it | VERIFIED | Independent stub run: observed argv contains `--plugin-dir benchmarks/plugins/ralph-specum/v4.0.0/plugins/ralph-specum` (joined, never bare `staged_path`). Full 32/32 bats green including all pre-existing vanilla/gsd-only/cairn tests, zero regression. |
| A `plugin_dir_subpath` target that does not exist dies EXIT_USAGE before any claude subprocess launches | VERIFIED | Independently reproduced with a broken manifest (existing `staged_path`, non-existent nested subpath) + a tripwire stub: exit code 2, error message names the joined path and retains literal `staged_path`, no JSONL row written, tripwire marker never created (stub never invoked). |
| Real `tzachbon/smart-ralph@v4.0.0` staged locally, nested `plugin.json` structurally exists at declared path | VERIFIED | `benchmarks/plugins/ralph-specum/v4.0.0/plugins/ralph-specum/.claude-plugin/plugin.json` exists on disk; `.staged-ref` reads `v4.0.0`; `git check-ignore` confirms the tree is gitignored and not committed (`git ls-files benchmarks/plugins/` returns empty). |
| Load-check provable at $0 via bats + documented live command; PENDING explicitly recorded, never silently skipped | VERIFIED | 3 dedicated bats tests pass (`ok 12`, `ok 13`, `ok 14` in the full suite run); README's "Competitor plugin load-check" section documents the exact `claude -p "/help" --plugin-dir ...` reproduction command verbatim, and "### Live load-check: PENDING" subsection is present. Independently confirmed `ANTHROPIC_API_KEY` is genuinely absent in this environment. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `benchmarks/baselines/competitor-ralph-specum.json` | pinned manifest, `plugin_dir_subpath`, `defaults_source` | VERIFIED | Valid JSON, all required fields present and correct, matches Interfaces block verbatim |
| `benchmarks/scripts/bench-run.py` | nested `--plugin-dir` resolution at both call sites | VERIFIED | `grep -c 'plugin_dir_subpath'` = 5 occurrences (≥2 required); die message retains literal `staged_path` (6 occurrences); independently exercised, produces correct joined argv |
| `tests/bench-run.bats` | subpath resolution, fail-loud, fairness coverage | VERIFIED | 14 tests total (11 pre-existing + 3 new), all pass; `grep -c 'plugin_dir_subpath'` = 5 (≥3 required) |
| `benchmarks/README.md` | 4th arm documented, schema extension, load-check status | VERIFIED | `competitor-ralph-specum`, `plugin_dir_subpath`, `Competitor plugin load-check`, `ralph-specum` all present; PENDING subsection with verbatim repro command present |
| `benchmarks/results/aggregated.json` | N≥5 competitor rows alongside other 3 arms (ROADMAP SC4) | **MISSING** | Does not exist — see gap above |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `competitor-ralph-specum.json provisioning.plugin_dirs[0].plugin_dir_subpath` | `bench-run.py load_baseline()` existence check | `Path(staged_path) / plugin_dir_subpath` | WIRED | Independently reproduced missing-target fail-loud (exit 2, correct message, no spend) |
| `competitor-ralph-specum.json provisioning.plugin_dirs[0].plugin_dir_subpath` | `bench-run.py main()` `--plugin-dir` argv construction | same join | WIRED | Independently reproduced correct joined argv via my own stub (not the bats fixture) |
| `benchmarks/README.md` live load-check command | `benchmarks/plugins/ralph-specum/v4.0.0/plugins/ralph-specum` | documented `claude -p "/help" --plugin-dir <path>` | WIRED (structurally) — LIVE EXECUTION PENDING | Path in the documented command matches the actual staged path on disk exactly; the live claude call itself has not been executed (key absent), consistent with the explicit PENDING status |

### Behavioral Spot-Checks (all independently re-executed, not taken from SUMMARY.md)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full bats suite (bench-verify, bench-run, bench-matrix, stage-plugins, bench-aggregate) | `bats tests/bench-verify.bats tests/bench-run.bats tests/bench-matrix.bats tests/stage-plugins.bats tests/bench-aggregate.bats` | `1..32`, 32 ok, 0 not ok | PASS |
| `jq -S '{model,claude_flags}'` on all 4 manifests | manual per-file jq | byte-identical across vanilla/gsd-only/cairn/competitor-ralph-specum | PASS |
| Live tag re-verification | `git ls-remote --tags https://github.com/tzachbon/smart-ralph.git` | v2.0.0, v3.1.1, v4.0.0 — v4.0.0 confirmed newest | PASS |
| Staged tree existence + pin marker | `test -f .../plugin.json`, `cat .../.staged-ref` | plugin.json exists; `.staged-ref` = `v4.0.0` | PASS |
| Staged tree gitignored | `git check-ignore -v`, `git ls-files benchmarks/plugins/` | ignored via `.gitignore:13`; zero tracked files | PASS |
| Independent stub run against competitor manifest (own stub, not bats fixture) | `bench-run.py --baseline competitor-ralph-specum.json` with custom stub | row written, `baseline_id: competitor-ralph-specum`, argv's `--plugin-dir` target = joined nested path | PASS |
| Fail-loud: missing `plugin_dir_subpath` target | broken manifest + tripwire stub | exit 2, no row written, tripwire never touched | PASS |
| `py_compile` all `benchmarks/scripts/*.py` | `python3 -m py_compile benchmarks/scripts/*.py` | exit 0 | PASS |
| README PENDING claim vs actual environment | `[ -n "$ANTHROPIC_API_KEY" ]` | key genuinely absent, matches README/SUMMARY | PASS |
| No leaked API key material | `grep -rn "sk-ant-api" benchmarks/` | zero matches | PASS |
| Anti-pattern scan (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) on all 4 phase-modified files | `grep -n -E ...` per file | zero matches in all 4 files | PASS |
| `aggregated.json` existence (repo-wide) | `find . -iname aggregated.json` | zero results | **CONFIRMS GAP** |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention exists in this repo and neither PLAN nor SUMMARY declares probes; skipped per Step 7c.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| COMP-01 | 04-01 | Baseline de ao menos um plugin de workflow concorrente rodando headless, com configuração documentada e validada | SATISFIED (configuration/wiring) — data-collection portion open | Manifest is pinned, `defaults_source`-documented, mechanically proven fair (FAIR-02), runs headless through the identical pipeline (independently proven above). `.planning/REQUIREMENTS.md` still shows COMP-01 unchecked/"Pending" — this matches reality more precisely than Phase 3's stale-bookkeeping note: the wiring/configuration is done, but no live headless run has actually occurred (0 API spend), so "rodando" (running, in the literal present tense) is not yet demonstrated with real data. |

No orphaned requirements — REQUIREMENTS.md's only Phase 4 row (COMP-01) appears in the plan's `requirements:` frontmatter.

### Anti-Patterns Found

None. Scanned all 4 phase-4-modified files (`competitor-ralph-specum.json`, `bench-run.py`, `tests/bench-run.bats`, `benchmarks/README.md`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` — zero matches. All 4 commits referenced in SUMMARY.md (`a3fccbf`, `84ef582`, `a90d8db`, `4114eae`) confirmed present in `git log`.

### Human Verification Required

None required for code correctness (this phase is a headless CLI/data-pipeline component with no UI). The one outstanding action — running the live `/help` load-check and the N≥5 competitor matrix — is an operator spend decision (requires `ANTHROPIC_API_KEY`), not a verification-by-a-human-tester item; it is captured as the gap above.

### Gaps Summary

**8/9 must-haves fully verified independently.** One gap, classified minor/non-blocking:

**ROADMAP Success Criterion 4** ("The same task, run N≥5 times against the competitor baseline, appears in `aggregated.json` alongside the other three arms") is **not met**. No `aggregated.json` exists anywhere in the repository — this is true for all 4 arms, not just the competitor; the full N≥5 live matrix has never been executed in this project. This is blocked on `ANTHROPIC_API_KEY`, which is genuinely absent (independently re-confirmed). `04-CONTEXT.md`'s own "Deferred Ideas" section explicitly anticipated this: *"Running the full N=5 live matrix — data collection happens when the corpus exists (Phase 5/6 boundary)."* The plan's own `must_haves` frontmatter correctly never claimed SC4 (it scoped only manifest/wiring/load-check), consistent with that locked decision — but per verification rules, PLAN-level scoping cannot silently subtract from the ROADMAP contract, so SC4 is reported here rather than silently passed.

Everything SC4 depends on is independently proven correct: the pipeline plumbing (isolated env, argv construction, `--plugin-dir` resolution) works identically for the competitor arm as for the other three; `bench-matrix.py`'s `--reps`/interleaving and `bench-aggregate.py`'s success-gated 4-way decomposition were already independently verified correct in Phase 3. What's missing is purely the live data itself — an operator-authorized-spend action, not a code defect. Classified **minor** (does not block the phase's stated goal of fair, auditable competitor configuration) rather than blocking.

**This looks intentional.** To accept this deviation and formally track it, add to this file's frontmatter:

```yaml
overrides:
  - must_have: "The same task, run N>=5 times against the competitor baseline, appears in aggregated.json alongside the other three arms"
    reason: "Deferred to Phase 5/6 data-collection boundary per 04-CONTEXT.md's own locked decision; blocked on ANTHROPIC_API_KEY which is genuinely absent from this environment. All pipeline plumbing needed to satisfy this is independently proven correct — only the live spend/data-collection step remains."
    accepted_by: "{your name}"
    accepted_at: "{current ISO timestamp}"
```

---

_Verified: 2026-07-26T06:01:38Z_
_Verifier: Claude (gsd-verifier)_
