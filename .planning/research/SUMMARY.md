# Project Research Summary

**Project:** CairnGo v1.1 — "Metrics & Benchmarks"
**Domain:** Reproducible LLM-agent benchmark suite (tokens/cost/time), publicly comparing vanilla Claude Code vs GSD-only vs cairn vs a competing workflow plugin
**Researched:** 2026-07-25
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a benchmark-harness build, not a product feature — the standard reference points are SWE-bench, Terminal-Bench, and Aider's leaderboard, and the bar they set is high: a fixed, versioned task corpus; external, agent-unwritable pass/fail verification; per-turn token breakdown (input/output/cache-write/cache-read, never a single blended number); N>=3 repetitions with reported variance; and a fully in-repo, one-command reproduction with a documented dollar cost. Claude Code's own headless mode (`claude -p --output-format json`/`stream-json`) is the correct and sufficient measurement primitive — it returns `total_cost_usd`, full `usage`, `num_turns`, and both wall and API duration in one authoritative JSON payload per run, so no scraping of undocumented session-log files is needed for the core metrics. The whole harness should be built stdlib-Python + bash + gnuplot, matching this repo's existing zero-pip-dependency house style exactly, with `benchmarks/` living at repo root (not under `cairn/`) since it is development/credibility tooling, not something shipped to plugin users.

The recommended approach is a five-stage pipeline (runner+collector -> aggregator -> reporter -> publisher, plus a results archive) built around two hard architectural disciplines: a **fresh isolated worktree per single run** (never reused across repetitions or baselines) and **`--bare` + fully explicit flags** for every invocation (never ambient `~/.claude` config), so "same conditions across baselines" is mechanically enforced rather than aspirational. Build order should front-load the two highest-uncertainty pieces — an objective `verify.sh` proven without any agent involved, and one real (non-stubbed) `claude -p` call against a single baseline/task — before any statistics or chart layer is built on top of unverified assumptions.

The dominant risk in this domain is not technical but methodological and reputational: because CairnGo is both the tool under test and the publisher of the comparison, the community will read any result through a conflict-of-interest lens by default ("the vendor who publishes the benchmark wins the benchmark" is a well-documented pattern). The single highest-leverage mitigations, all of which must be designed into the harness from day one rather than retrofitted, are: environment isolation per baseline (no leaked personal `~/.claude` config — this is the single most likely source of both accidental bias and a public credibility hit), success-gated cost reporting (cost-per-verified-completion, never raw tokens/time blended with failed runs), minimum 5 repetitions with published variance, and publishing full raw per-run data alongside every aggregate claim. Skipping any of these turns the benchmark into exactly the kind of self-serving marketing claim (see the buildomator "~92% lower overhead" anti-pattern, confirmed to have zero supporting data) that this project is explicitly trying to out-credential.

## Key Findings

### Recommended Stack

The core measurement primitive is Anthropic's own documented surface: `claude -p --output-format json` (single authoritative result object) and `--output-format stream-json --verbose` (adds a live event stream needed to count tool calls, a metric `num_turns` alone doesn't capture). Everything else is orchestration around that primitive, deliberately kept inside the repo's existing dependency category ("critical external CLI binaries, not language packages," same class as `bd`/`gh`/`git`).

**Core technologies:**
- `claude -p --output-format json/stream-json` (pinned CLI version): the authoritative per-run source of `total_cost_usd`, four-way token `usage`, `num_turns`, `duration_ms`/`duration_api_ms` — HIGH confidence, verified against current official docs
- Python 3, stdlib only: harness orchestration (subprocess invocation, JSON/NDJSON parsing, aggregation, CSV/JSON output) — matches the repo's existing zero-dependency house style exactly
- Bash wrappers (`set -euo pipefail`): thin CLI entry points, consistent with every other script in `cairn/scripts/`
- gnuplot (external CLI binary, `histogram cluster` + `errorbars` styles): renders grouped bar charts to static committed `.svg` — fits the existing "critical binary, not pip package" dependency pattern; MEDIUM confidence this is the *best* choice vs. a hand-rolled stdlib SVG fallback, which is the documented fallback if gnuplot is unavailable in a target CI image
- `HOME=<tmp-dir>` override per subprocess (not `CLAUDE_CONFIG_DIR`, which is undocumented and has multiple open upstream bugs) combined with `--bare`: the standard, verifiable isolation technique for run-to-run and baseline-to-baseline environment cleanliness

Explicitly rejected: matplotlib/numpy as the default charting stack (would be this repo's first-ever pip dependency), Mermaid `xychart-beta` as the primary chart source (unverified "beta" GitHub rendering support), `ccusage` wired into the automated pipeline (second-language dependency, reads global machine-wide history), and trusting the interactive `/cost` slash command for automated measurement.

### Expected Features

**Must have (table stakes) — what makes a reader trust this is a benchmark, not a marketing claim:**
- Fixed, hand-verified, versioned task corpus committed in-repo
- External, agent-unwritable task-completion verification (pass/fail) — the single highest-risk item to skip
- Token breakdown into input/output/cache-write/cache-read (never one aggregate number), cost from official pricing with model/version/date recorded
- N>=3 repetitions per (task, baseline) with mean+spread reported, never a single-run point estimate
- Reproduction instructions + raw data committed, runnable by a third party with a documented expected cost
- Explicit methodology/limitations section

**Should have (differentiators vs. every comparable competitor — GSD, spec-kit, BMAD, buildomator):**
- Cost-vs-completion scatter chart (log-x), script-generated from `results.json`, never hand-drawn
- A true 3-4-way baseline matrix (vanilla / GSD-only / cairn / competitor) on identical tasks — nearly everything found in this space is only a two-way comparison
- Token composition breakdown chart, showing *where* savings come from (cache hit rate) rather than a bare percentage
- Turns/tool-calls count as its own reported column (correlates with agent "flailing" in a way raw tokens can hide)

**Defer (v2+):** additional competitor baselines, larger/harder task corpus, historical trend chart across cairn releases, CI regression gate on benchmark metrics, hosted dashboard/leaderboard website (explicitly out of scope per PROJECT.md), continuous session telemetry (explicitly ruled out).

**Anti-features to actively avoid:** bare percentage claims with no methodology (the buildomator failure mode, confirmed to have zero supporting data), single-run "conclusive" comparisons, an opaque single composite score replacing the raw metric breakdown, apples-to-oranges task variants per baseline, and tuning the harness/prompts to make cairn win its own benchmark.

### Architecture Approach

A 5-component pipeline — runner+collector, aggregator, reporter, publisher, plus an append-only results archive — sits in a new top-level `benchmarks/` directory (sibling to `cairn/` and `tests/`, explicitly *not* shipped inside the plugin). Task definitions (`task.json`+`prompt.md`+`fixture/`+`verify.sh`) and baseline definitions (`baseline.json`+`settings.json`) are kept as two flat, orthogonal directories — never nested — so every baseline is structurally forced to run the identical prompt against the identical task, closing off the "apples-to-oranges" anti-feature at the directory-structure level. Two disciplines apply to every single run without exception: a fresh isolated worktree (never reused across repetitions), and `--bare` plus fully explicit re-added flags (never ambient `~/.claude` config). Harness tests are stub-based (a recorder script on `CAIRN_BENCH_CLAUDE_BIN`, mirroring the existing `CAIRN_GBSYNC`/`CAIRN_MAP`/`CAIRN_GATE` seam pattern) so the deterministic pipeline logic is exercised in the normal bats CI suite at zero live API cost, while real, costed `claude -p` runs are a separate, deliberately-triggered job.

**Major components:**
1. Task + baseline definitions — fixed, versioned unit of work (fixture + prompt + verify script) and exactly which Claude Code configuration is under test
2. Runner + collector (`bench-run.py`) — executes N repetitions of (task x baseline) in fresh isolated worktrees, invokes `claude -p`, runs `verify.sh`, appends one raw JSONL row per run
3. Aggregator (`bench-aggregate.py`) — groups raw rows by (task, baseline) into geometric-mean cost/tokens, pass-rate, mean turns/wall-clock, with dispersion
4. Reporter (`bench-report.py`) — pure function of `aggregated.json` -> markdown comparison table + hand-rolled SVG charts (no matplotlib)
5. Publisher (`bench-publish.py`) — regenerates only the generated-marker block in root `README.md`, reusing the exact pattern `cairn-map.py` already uses

Recommended build order deliberately front-loads the riskiest pieces: prove `verify.sh` against hand-crafted solved/unsolved fixtures first (fully bats-testable, zero agent involvement), then validate the real JSON schema with one live `claude -p` call before building baselines, repetition, aggregation, or charts on top of untested assumptions.

### Critical Pitfalls

1. **Single-run results presented as fact** — minimum 5 repetitions per (task, baseline) as a hard floor; report median/IQR or mean+-stdev, never a point estimate; LLM agent runs are non-deterministic at the trajectory level even at temperature=0.
2. **Home-field advantage / environment leakage** — every arm must run in a clean, scoped environment (fresh `$HOME`/container), with no personal global CLAUDE.md, MCP servers, or hooks leaking in from the operator's real machine. Identified as the single highest-risk shortcut in the entire effort and the most likely source of both accidental bias and a public credibility hit.
3. **Fewer tokens because the task wasn't actually finished** — every task needs an automated, agent-unwritable pass/fail check; the only trustworthy headline metric is cost-per-verified-completion, never raw tokens/time averaged across all runs regardless of outcome. Called out as the single most important pitfall in the whole research set.
4. **Prompt caching creates order- and warm-up-dependent cost swings** — randomize/interleave execution order across arms rather than running all of one baseline's repetitions consecutively; report all four token/cost components separately, never a single blended figure.
5. **Self-published benchmark treated as marketing, not evidence** — publish full raw per-run data, a one-command reproduction with documented cost, explicit methodology/limitations, and at least one honest result where cairn does not win. This can't be retrofitted onto a suite that never recorded raw data or environment manifests from the start.

## Implications for Roadmap

Based on combined research, suggested phase structure:

### Phase 1: Verification core + single real run
**Rationale:** Architecture research explicitly recommends front-loading the two highest-uncertainty, hardest-to-fake pieces — the objective verify contract and a real (non-stubbed) `claude -p` invocation — before any statistics or presentation layer exists. Pitfall 6 (fewer tokens because the task wasn't finished) is rated the single most important pitfall in the whole set, and it is only preventable if verification is designed in from the start, not bolted on.
**Delivers:** One task's `verify.sh` proven against hand-crafted solved/unsolved fixtures (bats-tested, no agent involved); `bench-run.py` executing a single (task=1, baseline=vanilla, rep=1) run first via a stub seam, then once against the live CLI to validate the real JSON schema.
**Addresses:** "Fixed, hand-verified task corpus" and "external, agent-unwritable verification" table stakes from FEATURES.md.
**Avoids:** Pitfall 6 (success not verified) and Pitfall 5 in the technical-debt table (ad hoc per-task verification without a plan to generalize it).

### Phase 2: Baseline isolation + multi-baseline harness
**Rationale:** PITFALLS.md names environment leakage as the single highest-risk shortcut in the whole project and recommends it be a dedicated phase with its own verification step (inspecting the actual system prompt sent per arm, not just config files). ARCHITECTURE.md's Pattern 2 (`--bare` + explicit flags) is the mechanism that makes this enforceable, and it needs to be exercised for real across vanilla/GSD-only/cairn before repetition or aggregation is built on top.
**Delivers:** `--bare`-based invocation with per-baseline `settings.json`/`--plugin-dir`, a scoped `HOME` per run, and an explicit environment manifest per baseline; harness extended from one baseline to vanilla/GSD-only/cairn against the same single task.
**Uses:** `HOME=<tmp-dir>` override, `--bare` + explicit re-added flags, pinned full model id (STACK.md).
**Implements:** Runner + collector component, fresh-isolated-worktree-per-run discipline (ARCHITECTURE.md Pattern 1).

### Phase 3: Repetition, aggregation, and cost decomposition
**Rationale:** PITFALLS.md Pitfall 1 (single-run results) and Pitfall 7 (prompt-caching order effects) both require the repetition count, execution-order randomization, and four-way token/cost decomposition to be harness parameters from day one — retrofitting them onto an already-run suite invalidates the numbers. FEATURES.md rates N>=3 trials as the #1 credibility gap found across comparable community benchmarks.
**Delivers:** `bench-aggregate.py` (geometric mean for cost/tokens, dispersion, pass-rate, N>=5 repetitions per cell), execution-order randomization/interleaving across arms and reps, raw JSONL preserving all four token components per run.
**Uses:** Python stdlib `statistics` module; append-only `results/<run-id>/` archive.
**Implements:** Aggregator component; Anti-Pattern 4 prevention (never publish a mean with no visible spread).

### Phase 4: Competitor baseline
**Rationale:** PITFALLS.md flags a misconfigured competitor baseline as reputationally the single worst outcome available to the project — worse than not benchmarking at all — because it reads as sabotage even when it's negligence. This must be its own phase with a dedicated re-verification checkpoint, not folded into the general multi-baseline work.
**Delivers:** A fourth baseline (competitor plugin) configured against its own current official quickstart/defaults, version/commit pinned, run through the same isolated-worktree + `--bare` pipeline as the other three arms.
**Addresses:** "Multi-baseline comparison" differentiator from FEATURES.md (3-4-way matrix, rare in this space).
**Avoids:** Pitfall 5 (misconfigured competitor baseline / public flame-war risk).

### Phase 5: Task corpus expansion + task-design bias controls
**Rationale:** PITFALLS.md Pitfall 3 (cherry-picked tasks favoring cairn) requires the task suite's scope to be defined and diverse *before* seeing results, and to explicitly include at least one category unfavorable to cairn's overhead. This is cheaper and lower-risk to do once the pipeline (phases 1-4) is proven on a single task, per ARCHITECTURE.md's recommended build order (step 8: "scale the task set — only after the full pipeline is proven on one task").
**Delivers:** 2-4 additional representative dev-workflow tasks (bugfix, feature, refactor, and at least one trivial single-turn task where planning overhead is pure loss), task-selection criteria documented before any results exist.
**Addresses:** "Larger/more diverse task corpus" from FEATURES.md's Add-After-Validation list, pulled earlier because Pitfall 3/2 make task-design bias and sample-size-insufficiency structural risks, not polish items.
**Avoids:** Pitfall 3 (cherry-picked tasks) and Pitfall 2 (sample size too small to distinguish baselines from noise).

### Phase 6: Reporting, charts, and publication
**Rationale:** Architecture's build order places the markdown table and SVG charts last precisely because they are pure functions of already-validated `aggregated.json` — no new design risk once phases 1-5 are done. Pitfalls 8 and 10 (undated results, self-published-as-marketing) are publication-phase concerns that can only be executed correctly if raw data and methodology were captured all along (phases 1-5), so this phase is presentation + credibility packaging, not new data collection.
**Delivers:** `bench-report.py` (comparison table + cost-vs-completion scatter chart + token composition breakdown chart, all committed SVG), `bench-publish.py` README embed via generated markers, `BENCHMARKS.md` methodology doc (task corpus, pricing source/date, model versions, reproduction command, expected $ cost, caveats/limitations), every graph captioned with model snapshot + date + N reps.
**Implements:** Reporter + Publisher components (ARCHITECTURE.md); FEATURES.md's "script-generated charts" and "BENCHMARKS.md methodology doc" P1 items.
**Avoids:** Pitfall 8 (undated/stale results), Pitfall 10 (self-published credibility gap) — via raw data, one-command reproduction, and at least one honest non-win shown.

### Phase Ordering Rationale

- Verification and a live schema check come first because every other number in the system is meaningless (or worse, silently wrong) if success isn't objectively gated or the JSON payload assumptions are wrong — this is the architecture research's explicit "de-risk hardest pieces first" recommendation.
- Baseline isolation is its own phase, ahead of repetition/aggregation, because environment leakage is rated the single highest-risk shortcut across all pitfalls research, and it must be provably fixed before any comparative number is trusted, let alone repeated N times.
- Repetition/aggregation/cost-decomposition come together as one phase because they share the same root cause in pitfalls research (harness-design-time decisions that can't be retrofitted) and the same architecture component (the aggregator).
- The competitor baseline is deliberately isolated into its own phase, after the vanilla/GSD/cairn matrix is proven, because it carries a distinct, higher-severity reputational risk (public flame-war) that warrants its own re-verification checkpoint rather than being absorbed into general "multi-baseline" work.
- Task corpus expansion is sequenced after the pipeline is proven on one task (matching architecture's explicit build-order step 8), but pulled ahead of "add more competitors" (which FEATURES.md defers to v1.x) because task-design bias (Pitfall 3) and sample-size sufficiency (Pitfall 2) are structural credibility risks, not polish.
- Reporting/publication is last because it is a pure function of already-collected, already-validated data — building charts before the data pipeline is trustworthy would mean re-deriving them anyway.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Competitor baseline):** ARCHITECTURE.md explicitly flags this as an open question requiring phase-specific research — not all third-party Claude Code plugins are guaranteed to have documented headless-mode support or a pinnable version reference; verify per-competitor before committing to it as a baseline.
- **Phase 5 (Task corpus expansion):** Task design/selection-bias mitigation (Pitfall 3) and statistical-sufficiency sizing (Pitfall 2) both note "no universal N tasks is enough rule" — the right corpus size/diversity for this specific project needs its own investigation rather than a generic answer.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Verification core):** Directly mirrors the well-documented SWE-bench/Terminal-Bench `verify.sh`/`tests/` pattern, already adapted in ARCHITECTURE.md with concrete code examples.
- **Phase 2 (Baseline isolation):** `--bare` + `HOME` override + explicit flags are HIGH-confidence, officially documented CLI behaviors with worked examples already in STACK.md/ARCHITECTURE.md.
- **Phase 3 (Repetition/aggregation):** Geometric-mean-for-cost aggregation and N>=5 repetitions are both concretely specified with worked JSONL/JSON schema examples in ARCHITECTURE.md.
- **Phase 6 (Reporting/publication):** Reuses this repo's own already-proven `cairn-map.py` generated-marker pattern; gnuplot histogram/errorbars styles are long-stable, well-documented features.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core measurement APIs (`--output-format json/stream-json`, `usage` fields) verified verbatim against current official `code.claude.com` docs; only the gnuplot-vs-alternatives judgment and `CLAUDE_CONFIG_DIR` status are MEDIUM/community-sourced |
| Features | MEDIUM-HIGH | Verified against multiple credible sources (SWE-bench/Terminal-Bench, Aider's official leaderboard docs, Anthropic's cache-pricing docs) plus direct inspection of two real competitors in this exact space; some competitor-claim sources (buildomator, BMAD) are MEDIUM/LOW confidence self-reported claims used only as anti-pattern illustrations |
| Architecture | MEDIUM-HIGH | Claude Code headless flags/JSON schema are HIGH confidence, official docs; the component decomposition itself is a synthesis of two analogous public repos adapted to this repo's constraints — explicitly flagged as needing validation once task #1 is actually built |
| Pitfalls | MEDIUM-HIGH | Triangulated from peer-reviewed/arXiv agent-benchmarking literature, documented public benchmark controversies (Devin, AI code-review vendors), and Anthropic's own pricing docs; CairnGo-specific numbers are necessarily LOW confidence since no benchmark exists yet to observe failure modes on directly |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Competitor plugin headless-mode support is unverified per-plugin** — ARCHITECTURE.md explicitly flags this as unresolved; must be checked against the specific competitor(s) chosen before Phase 4 is planned in detail.
- **gnuplot vs. hand-rolled stdlib SVG is a value judgment, not a doc fact (MEDIUM confidence)** — decide during Phase 6 planning whether gnuplot's availability across target CI images is acceptable, or whether to default to the zero-external-binary stdlib fallback from the start.
- **Task count/diversity sufficient to distinguish baselines from noise has no universal rule** (Pitfall 2) — the specific number of tasks/categories for CairnGo's suite needs a deliberate decision during Phase 5 planning, informed by the affordability constraint (PROJECT.md: "custo previsível e documentado"), not resolved by this research.
- **`CLAUDE_CONFIG_DIR` is real but undocumented with open upstream bugs** — confirmed only via community issue-tracker reports (#3833, #28808, #33430), not official docs; the `HOME`-override workaround is well-reasoned but should be re-validated against the actual pinned CLI version at implementation time in case upstream stabilizes it.
- **Mermaid `xychart-beta` GitHub rendering support is unresolved (LOW confidence)** — irrelevant if the static-SVG recommendation is followed as planned, but flagged in case a future phase reconsiders lightweight in-README charts.

## Sources

### Primary (HIGH confidence)
- `code.claude.com/docs/en/headless` — `--output-format json/stream-json` fields, `--bare`, stream event structure
- `code.claude.com/docs/en/cli-reference` — full flag table (`--model`, `--max-turns`, `--plugin-dir`, `--settings`, `--permission-mode`, `--bare`)
- `code.claude.com/docs/en/agent-sdk/typescript` — `SDKResultMessage` schema (`usage`, `total_cost_usd`, `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`)
- `code.claude.com/docs/en/monitoring-usage` — OpenTelemetry metric names/attributes for optional per-tool/per-agent cost attribution
- `code.claude.com/docs/en/devcontainer` — official sandboxing guidance for `--dangerously-skip-permissions`
- `platform.claude.com/docs/en/about-claude/pricing` and `.../prompt-caching` — cache-read/cache-write pricing multipliers and TTL behavior
- [Aider LLM Leaderboards (official docs)](https://aider.chat/docs/leaderboards/)
- [Holistic Agent Leaderboard (arXiv 2510.11977)](https://arxiv.org/pdf/2510.11977)
- [Token Reduction Is Not Cost Reduction (arXiv 2607.12161)](https://arxiv.org/html/2607.12161)
- [How Many Tasks Are Enough for Agent Benchmark Decisions? (arXiv 2607.12338)](https://arxiv.org/html/2607.12338v1)
- This repo's own `.planning/codebase/TESTING.md` and `.planning/codebase/ARCHITECTURE.md`

### Secondary (MEDIUM confidence)
- [SWE-bench harness reference](https://www.swebench.com/SWE-bench/reference/harness/) / [SWE-bench GitHub](https://github.com/swe-bench/SWE-bench)
- [Terminal-Bench GitHub repo](https://github.com/laude-institute/terminal-bench) / [Harbor framework docs](https://www.harborframework.com/docs/tutorials/running-terminal-bench)
- [testing-claude-agent (GitHub, adam-s)](https://github.com/adam-s/testing-claude-agent) — closest direct architectural analogue found
- [Token-Harness Optimizer Leaderboard (THOL)](https://pi-infected.github.io/token-harness-optimizer-leaderboard/) — geometric-mean aggregation precedent
- [How We Broke Top AI Agent Benchmarks (Berkeley RDI)](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/) — agent-writable verification anti-pattern
- [Finding Widespread Cheating on Popular Agent Benchmarks (DebugML)](https://debugml.github.io/cheating-agents/)
- [Everyone Wins Their Own Benchmark (Endor Labs)](https://www.endorlabs.com/learn/everyone-wins-their-own-benchmark) — "vendor who publishes wins" pattern
- [buildomator (jnuyens/gsd-plugin) GitHub repo](https://github.com/jnuyens/gsd-plugin) — confirmed bare-percentage-claim anti-pattern, direct GSD-ecosystem competitor
- [Tura-AI/tura GitHub repo](https://github.com/Tura-AI/tura) — verified example of a credible embedded-chart methodology
- `github.com/anthropics/claude-code` issues #3833, #28808, #33430 — `CLAUDE_CONFIG_DIR` undocumented/buggy status

### Tertiary (LOW confidence)
- ["Spec Driven Development Is Wasting Tokens" (Medium)](https://medium.com/it-chronicles/is-your-safe-choice-burning-your-budget-1cfddf8782e4) — single-run N=2 anti-pattern example only
- [BMAD-METHOD token efficiency claims discussion (Medium)](https://medium.com/@hieutrantrung.it/from-token-hell-to-90-savings-how-bmad-v6-revolutionized-ai-assisted-development-09c175013085) — self-reported claims, used only to illustrate weak-backing anti-pattern
- [Model version drift best practices](https://futureagi.com/blog/model-vs-data-drift-how-to-identify-and-handle-it/) — general, not benchmark-specific
- [Debunking Devin AI benchmark criticism](https://gist.github.com/cedrickchee/588a55cbcaeb2d0faba694ae1fa560dd) — public backlash case study, needs no direct application, illustrative only

---
*Research completed: 2026-07-25*
*Ready for roadmap: yes*
