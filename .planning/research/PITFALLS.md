# Pitfalls Research

**Domain:** Publishing a self-authored LLM-agent token/time efficiency benchmark (cairn vs. Claude Code vanilla vs. GSD-only vs. a competing workflow plugin), embedded as public marketing/credibility evidence in the CairnGo README.
**Researched:** 2026-07-25
**Confidence:** MEDIUM-HIGH (triangulated from peer-reviewed/arXiv agent-benchmarking literature, documented public benchmark controversies — Devin, AI code-review vendors — and Anthropic's own prompt-caching pricing docs; LOW confidence only where noted for CairnGo-specific numbers, since no benchmark exists yet to observe failure modes on)

This is a dual-domain problem: (1) **agent benchmarking methodology** (variance, task design, success verification) and (2) **publishing your own comparison as one of the parties being compared** (conflict of interest, public scrutiny, flame-war risk). Both literatures agree on the same root cause: benchmarks that look rigorous but are not independently reproducible get treated as marketing, not evidence — and self-published vendor benchmarks face the harshest scrutiny of all ("the vendor who publishes the benchmark wins the benchmark" is a documented pattern, not paranoia).

## Critical Pitfalls

### Pitfall 1: Single-run results presented as fact

**What goes wrong:**
One run per task/baseline is reported as "cairn uses 40% fewer tokens than X," with no repetition. A single run of an LLM agent is a sample of size 1 from a noisy distribution — the number is real but not representative.

**Why it happens:**
Repetition costs real API money and wall-clock time (N repetitions × M baselines × K tasks multiplies fast), so it's tempting to run once and call it done, especially under time pressure to ship the README graphs.

**How to avoid:**
- Minimum 5 repetitions per (task, baseline) cell before publishing any number; treat this as a hard floor, not a target.
- Report median and IQR (or mean ± stdev) per cell, never a single value, in both the graphs and the raw data.
- Even with temperature=0 / fixed sampling params, leading coding-agent models do not reproduce identical token counts or tool-call sequences run-to-run — tool outputs (file listings, timestamps, git diffs) and the agent's own exploration path vary. Determinism at the API level does not imply determinism at the trajectory level.

**Warning signs:**
- Any README claim ("40% fewer tokens") traceable to exactly one JSON result file.
- No `stdev`/`iqr` column in the raw results CSV.
- Graphs with no error bars.

**Phase to address:**
Metrics collection / harness design phase — repetition count and aggregation method must be a harness parameter from day one, not a post-hoc fix.

---

### Pitfall 2: Sample size too small to distinguish baselines from noise

**What goes wrong:**
Even with repetitions, too few *tasks* (not just too few runs per task) makes it impossible to tell whether cairn is actually cheaper than a competitor or the difference is within noise. Research replaying public agent benchmarks found the number of tasks needed to reliably detect even a 5-percentage-point difference between two systems varies wildly by benchmark (15% of tasks sufficient for one benchmark, 90%+ for another, some benchmarks never reaching sufficiency at 95% coverage) — there is no universal "N tasks is enough" rule.

**Why it happens:**
A benchmark suite that's "reproducible by one command" pressures toward a small, fast task set; a comprehensive one is expensive to run and slow to develop. Nobody wants to compute statistical power before publishing a comparison chart.

**How to avoid:**
- Pick a task count large enough, and diverse enough across task *types* (not just repeated variations of one task shape), to plausibly separate a real effect from noise — err toward more, smaller tasks over few, large ones.
- Report a per-task breakdown, not just an aggregate bar chart — aggregates hide the cases where cairn loses.
- If a difference between two baselines is smaller than the observed run-to-run variance for either one, do not present it as a win in the README; call it "no significant difference" explicitly.

**Warning signs:**
- Fewer than ~10 distinct task types informing a headline percentage.
- Aggregate numbers with no per-task table available for scrutiny.

**Phase to address:**
Task design phase — decide task count/diversity and the statistical bar for "significant" before building the harness around a fixed small set.

---

### Pitfall 3: Cherry-picked tasks that favor cairn's structure

**What goes wrong:**
Choosing benchmark tasks that happen to play to cairn's strengths (e.g., multi-phase feature work where GSD-style planning saves re-reads) while omitting task shapes where a lighter-weight competitor would win (e.g., a single quick bugfix where any planning overhead is pure loss) produces a technically-true, systematically-misleading result — the exact "cherry-picked evaluation runs" failure documented across coding-agent benchmark controversies.

**Why it happens:**
The task author (you) is also the tool author, and every task written is unconsciously shaped by familiarity with how cairn is supposed to shine.

**How to avoid:**
- Define the task suite's scope (bugfix, feature, refactor, multi-file, exploration-heavy) *before* running cairn on any of them, ideally derived from real historical CairnGo issues/PRs rather than authored fresh.
- Include at least one task category explicitly expected to be unfavorable to cairn's overhead (trivial one-shot tasks) — showing where you lose is what makes the rest credible.
- Have someone other than the tool's author sanity-check the task list for selection bias, or publish the task-selection criteria openly so readers can judge for themselves.

**Warning signs:**
- Every task in the suite is a "multi-phase feature," none are trivial single-turn fixes.
- Task list was written after seeing early results ("let's add one more task like the one where we won big").

**Phase to address:**
Task design phase.

---

### Pitfall 4: Home-field advantage — the cairn arm gets help the baselines don't

**What goes wrong:**
The cairn run includes cairn's own CLAUDE.md, skills, and MCP context-mode integration; the "vanilla" and "GSD-only" baselines are run with residual global config (the operator's personal `~/.claude/CLAUDE.md`, unrelated MCP servers, memory hooks) still active, or with a stripped-down setup that isn't actually equivalent to how a real user would run them. Either direction — over-helping cairn or under-configuring the competitor — invalidates the comparison.

**Why it happens:**
It is much easier to notice and control your own tool's environment than to notice everything ambient in someone else's. The person running the benchmark already has a fully customized global Claude Code environment (as this very session demonstrates: a large personal CLAUDE.md, code-review-graph, supermemory, multiple MCP servers) that will silently leak into any baseline run from the same machine/user profile.

**How to avoid:**
- Run every arm (vanilla, GSD-only, competitor, cairn) in a clean, isolated environment: a fresh container/VM or a scoped `$HOME`/`$CLAUDE_CONFIG_DIR` with only that arm's intended config present — no personal global CLAUDE.md, no unrelated MCP servers, no leftover session state.
- Explicitly enumerate what's active for each arm (system prompt, CLAUDE.md, MCP servers, skills, hooks) in the published methodology, so it's auditable.
- Give the competing plugin its documented, intended setup — not a deliberately minimal or misconfigured install. If unsure how the competitor is meant to be configured, follow its own README/quickstart exactly and note the version used.

**Warning signs:**
- Benchmark harness reuses the operator's normal `$HOME`/dotfiles instead of a scoped environment.
- No explicit "environment manifest" per arm in the methodology doc.
- Competitor's config was written from memory instead of copied from its own docs.

**Phase to address:**
Baseline isolation phase — this is the single most likely source of both accidental bias and a public credibility hit, and should be a dedicated phase with its own verification step (e.g., inspect the actual system prompt/context sent per arm, not just the config files).

---

### Pitfall 5: Misconfigured competitor baseline — the public flame-war risk

**What goes wrong:**
The competing plugin is run with an outdated version, wrong flags, or a setup that doesn't match how its own maintainers intend it to be used, producing an artificially bad result for them. When published, the competitor (or their community) points this out publicly — this is reputationally the single worst outcome available to this project, worse than not benchmarking at all, because it looks like deliberate sabotage even when it's negligence.

**Why it happens:**
Nobody on the CairnGo side uses the competitor tool daily; its docs may be skimmed rather than followed precisely; version pinning is easy to forget.

**How to avoid:**
- Pin and record the exact version/commit of every competing tool used, and re-verify against its current README/quickstart before each publish cycle.
- Where feasible, before publishing, let a maintainer or an active user of the competing tool review the configuration used for their arm (even an informal "does this look right?" DM) — this is standard practice for independent benchmarks that survive scrutiny (e.g., the Martian AI-code-review benchmark explicitly positioned itself as neutral precisely because it wasn't vendor-run).
- If direct review isn't possible, err toward the competitor's officially documented defaults, not a hand-tuned or minimal config, and say so explicitly in the methodology.
- Keep transcripts/logs for the competitor's runs available in the raw data so anyone can verify it actually ran as claimed.

**Warning signs:**
- Competitor's setup instructions were written from a skim of their README weeks ago, not re-checked against current docs at benchmark time.
- No changelog entry recording which competitor version/commit was benchmarked.

**Phase to address:**
Baseline isolation phase, with a re-verification checkpoint immediately before each publish/re-run.

---

### Pitfall 6: Fewer tokens because the task wasn't actually finished

**What goes wrong:**
An arm reports a lower token count or faster completion because the agent stopped early, produced a shallower/incorrect solution, or silently skipped steps — not because it was genuinely more efficient at the *same* task. Token/time efficiency without a task-success gate is not a benchmark, it's a race to give up first. This is a well-documented failure mode: agents that "finish early" or take shortcuts can look efficient while doing less work, and independent audits of popular agent benchmarks found dozens of confirmed cases of tasks gamed via shortcuts rather than solved.

**Why it happens:**
Token/time are cheap to measure automatically; correctness requires a real verification step (tests passing, diff matching intent, output review) that's easy to skip when the point of the exercise is "make the efficiency graph."

**How to avoid:**
- Every task needs an objective, automated pass/fail check (test suite green, specific file/diff assertions, output matching a spec) that runs identically against every arm's output — not a subjective "looks done."
- Compute and publish **cost-per-successful-completion**, not raw token/time averaged across all runs regardless of outcome. A recent empirical study of API-based coding agents found token reduction and dollar cost can move in *opposite* directions once success rate and follow-up turns are accounted for — the only trustworthy metric is end-to-end cost divided by verified successes.
- Any run that fails its success check is excluded from the "efficiency win" headline number, but must still be reported (failure rate is itself a critical metric — a tool that's cheap because it fails often is not a win).

**Warning signs:**
- Task definitions have no automated success criteria, only a token/time budget.
- Aggregate cost numbers include failed/incomplete runs blended in with successful ones.
- One arm's average token count is suspiciously low with no corresponding success-rate figure published alongside it.

**Phase to address:**
Task design phase (define success criteria) and Metrics collection phase (compute cost-per-success, not raw averages) — this is the most important pitfall in the whole set; a headline number that doesn't gate on correctness is worse than no benchmark.

---

### Pitfall 7: Prompt caching creates order- and warm-up-dependent cost swings

**What goes wrong:**
Anthropic's prompt caching makes cache *reads* ~10% of full input price after a cache write, with a default ~5-minute TTL reset on each hit. If the harness runs all of one arm's repetitions back-to-back with shared/overlapping context (e.g., the same repo checkout, same CLAUDE.md prefix), later runs get artificially cheap cache hits that earlier runs or a different arm running cold do not — making the recorded cost a function of *execution order and timing*, not of the tool's real efficiency. Compression/optimization that removes cached-context tokens can also *increase* real dollar cost (removing early-context tokens forfeits the ~90%-off cache-read discount on all their future reads), the inverse of what a naive token count would suggest.

**Why it happens:**
Token counts are easy to reason about; the cache-read/cache-write cost split is not, and it depends on request timing/ordering that a simple "run task, record tokens" harness doesn't control for.

**How to avoid:**
- Randomize execution order across arms/repetitions rather than running all repetitions of one arm consecutively, so caching effects are distributed rather than systematically favoring whichever arm happens to run second.
- Record and report the four cost components separately (uncached input, cache-creation, cache-read, output tokens) per run, not just a single blended token count — this is necessary to explain why costs might not track token counts.
- Use the API's own billed cost fields (actual `usage`/cost reporting) as the source of truth for dollar figures, cross-checked against the published pricing table, rather than reconstructing cost from raw token counts by hand.
- Decide and document a fixed cache posture per arm (e.g., always cold cache per run, or always warm with an explicit warm-up run excluded from measurement) and apply it identically to every arm.

**Warning signs:**
- Harness runs `for rep in 1..N: run(arm)` sequentially per arm instead of interleaving/randomizing.
- Reported cost is derived only from `input_tokens + output_tokens × price`, with no cache-read/cache-write breakdown.
- Cost per run trends downward across repetitions within a single arm (classic warm-cache artifact).

**Phase to address:**
Metrics collection phase — this needs to be designed into the harness (execution order + cost decomposition), not patched after the fact.

---

### Pitfall 8: Undated results silently invalidated by model updates

**What goes wrong:**
A README graph published today claims "cairn uses N% fewer tokens than X" with no model version or date attached. Three months later the underlying model (or the competitor's own tool) has changed behavior enough that the comparison no longer holds, but the graph still sits in the README as if timeless, quietly becoming false advertising.

**Why it happens:**
Model identifiers behind convenience aliases (e.g., "latest") change without notice; a one-time benchmark effort doesn't naturally include a maintenance plan, and re-running is exactly the expensive, unglamorous work that gets deprioritized once the initial README graphs ship.

**How to avoid:**
- Pin and record the exact model snapshot/version used for every arm (not a moving alias), plus the date of the run and the versions of cairn/GSD/competitor benchmarked, directly on the published graph or its caption — not just buried in a separate methodology doc.
- Establish an explicit re-run cadence (e.g., on every cairn minor release, or quarterly, or whenever the pinned model version changes) as a recurring maintenance task, not a one-off.
- Prefer a script-generated graph committed to the repo (already the chosen approach per PROJECT.md) with the generation date embedded in the image/caption, so staleness is visible at a glance rather than silently assumed current.

**Warning signs:**
- README graph has no date or model-version caption.
- No CI/reminder mechanism tied to re-running the benchmark after a dependency (model, competitor version) changes.
- "Last benchmarked" date, if present, is more than one model-generation old.

**Phase to address:**
Publication phase (dating/captioning is part of shipping the graph) and an ongoing maintenance phase (re-run cadence) that should be explicitly scoped in the roadmap, not left implicit.

---

### Pitfall 9: Setup/session overhead conflated with task-execution cost

**What goes wrong:**
Time or tokens spent on one-time setup (installing the plugin, running `cairn init`, indexing the codebase for context-mode, initial `/gsd:new-project` scaffolding) get lumped into the per-task numbers, unfairly penalizing whichever arm has heavier one-time setup even if its steady-state task cost is lower — or conversely, amortizing cairn's setup cost across so many trivial tasks that its real per-task overhead is hidden.

**Why it happens:**
It's simpler to measure "everything that happened between start and finish" than to instrument the harness to separate one-time setup from repeatable task execution.

**How to avoid:**
- Measure and report setup cost (install + first-run indexing/scaffolding) as its own separate line item, amortized transparently (e.g., "setup cost: X tokens one-time; steady-state per-task: Y tokens") rather than folded into every task's number.
- Warm up each arm once (run and discard a throwaway task) before measured repetitions begin, so first-run-only costs (cold context-mode index, first `cairn-map` run, etc.) don't bleed into comparative task numbers unless setup cost itself is the thing being measured.
- If the roadmap wants to make a claim about setup cost specifically (a legitimate and honest thing to measure), do it as its own explicit metric/graph, not mixed into the per-task efficiency chart.

**Warning signs:**
- Task 1's numbers are a clear outlier (much higher) relative to tasks 2-N for the same arm within a run.
- No separate "setup" row/column in the raw results.

**Phase to address:**
Metrics collection phase.

---

### Pitfall 10: Self-published benchmark treated as marketing, not evidence

**What goes wrong:**
Because CairnGo is one of the compared tools, any published comparison is read by the community through a conflict-of-interest lens by default — "the vendor who publishes the benchmark wins the benchmark" is such a well-established pattern (documented across AI code-review vendors, and generally in tech benchmarking) that a benchmark with no counter-measures for this will simply be dismissed, regardless of how careful the methodology actually was.

**Why it happens:**
There's no way to *not* have a conflict of interest when you're both the subject and the publisher; the only lever available is transparency and falsifiability, and it's easy to under-invest in exactly the parts (raw data, one-command reproduction, showing where you lose) that don't make the marketing copy shinier.

**How to avoid:**
- Publish the full raw results (per-run JSON/CSV, not just aggregates) alongside the graphs, in the repo, from day one — this is the single highest-leverage credibility move and costs little beyond discipline to keep the harness output structured.
- Make the entire suite runnable by a third party with one command (documented cost estimate up front, since it burns real API credits) — "reproducible by anyone" is the explicit bar the community holds vendor benchmarks to, and CairnGo's constraints section already commits to this ("suite precisa ser rodável por terceiros com custo previsível e documentado").
- Explicitly publish the methodology (task selection criteria, environment isolation, statistical treatment, known limitations) in the same place as the results, not as an afterthought — and include at least one result where cairn does *not* win, if one exists honestly. A benchmark that shows only wins reads as cherry-picked even if it isn't.
- Consider inviting or crediting review from someone outside the project (a user of the competing tool, or just a careful outside reader) before the first publish, given this is exactly the kind of comparison most likely to be picked apart publicly.

**Warning signs:**
- README shows only summary graphs with no link to raw data or a reproduction script.
- No "limitations" or "how to reproduce this yourself" section near the benchmark claims.
- Every single comparison in the published results favors cairn (statistically implausible if the methodology were truly neutral across a large task suite).

**Phase to address:**
Publication phase — but methodology transparency has to be designed in from the harness/task-design phase onward, since it can't be retrofitted onto a suite that never recorded the raw data or environment manifests in the first place.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|--------------------|-----------------|------------------|
| Running only 1-2 reps per task to ship the first README graphs faster | Faster time-to-publish | Numbers get challenged/retracted once someone reproduces with proper repetition and gets different results | Never for published claims; fine only for internal dev-loop iteration on the harness itself |
| Hardcoding task success checks per-task instead of a shared verification framework | Faster to add first few tasks | Each new task needs bespoke, easy-to-get-wrong verification code; inconsistent rigor across tasks | Acceptable for the first 3-5 tasks while the harness shape is still being figured out; must be refactored into a shared framework before the suite is called "done" |
| Skipping environment isolation (running baselines from the operator's normal `$HOME`) to save harness-engineering time | Ships sooner | Silent home-field-advantage bias (Pitfall 4); undermines the entire credibility premise of the project | Never — this is the single highest-risk shortcut in the whole effort |
| Publishing aggregate-only graphs without raw per-run data in the repo | Cleaner, simpler README | Reads as unverifiable marketing (Pitfall 10); blocks anyone from catching a methodology bug before a competitor does it publicly | Never for the public README; fine for a private/internal draft pass |
| Reusing the same model alias ("claude latest") instead of pinning a snapshot | Avoids version-tracking overhead | Comparison silently invalidated by future model updates (Pitfall 8); no way to explain a discrepancy later | Never once results are published; acceptable only during harness development before any number is recorded |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|------------------|--------------------|
| Anthropic Claude API billing/usage | Reconstructing dollar cost by hand from token counts × list price, ignoring cache-read/cache-write split | Use the API's own reported usage/cost fields per request as source of truth; cross-check against the published pricing page, decomposed into uncached-input, cache-creation, cache-read, output |
| Competing plugin CLI/config | Configuring the competitor from memory or a stale README skim | Follow the competitor's current official quickstart exactly, pin the version/commit used, and (where feasible) get an outside sanity check before publishing |
| CI running the benchmark (if automated) | API keys for multiple provider accounts sitting in CI logs/artifacts, or benchmark runs triggered on every PR (uncontrolled cost) | Gate benchmark CI runs behind manual trigger/label, use scoped secrets not printed to logs, cap spend with a budget check before each run |
| GSD-only baseline vs. cairn | Running "GSD-only" with cairn's plugin still installed/active (dormant hooks, leftover skills) instead of a genuinely clean GSD install | Use a separate, verified-clean environment per arm (container or scoped config dir) and enumerate exactly what's installed for each |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Full matrix re-run (N reps × M baselines × K tasks) on every benchmark iteration during harness development | API cost balloons before the suite is even finalized | Iterate the harness itself against 1 task/1 baseline/1 rep; only run the full matrix once the harness is stable | Breaks budget almost immediately once K (tasks) or M (baselines) grows past a handful — cost is multiplicative, not additive |
| Growing the task suite indefinitely to "cover everything" | Each benchmark run becomes slower and more expensive to reproduce, discouraging the "one command, documented cost" promise | Cap the suite to a deliberately curated, diverse-but-bounded set; add tasks only when they cover a genuinely new dimension, not for volume | Breaks the "cheap to reproduce" credibility promise once a third-party run costs more than they're willing to spend to verify a README claim |
| Sequential (non-parallel) execution of all arms/reps | Full benchmark run takes hours/days, discouraging frequent re-runs (worsening Pitfall 8, staleness) | Parallelize across independent task/arm combinations where the API/rate limits allow, while still respecting execution-order randomization for cache fairness (Pitfall 7) | Breaks maintainability once re-running "before every release" becomes too slow to actually happen in practice |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing raw benchmark transcripts/logs that include API keys, local file paths, or other environment leakage from the operator's machine | Credential/PII leak in a public repo | Scrub/redact transcripts before committing; run the harness in a scoped environment (Pitfall 4) so there's nothing sensitive to leak in the first place |
| Storing provider API keys for multiple accounts (needed to run competitor tools too) in a shared `.env` committed or logged by the harness | Key leak, unexpected spend if leaked key is reused elsewhere | Use per-arm scoped credentials (1Password/secret manager, not a repo-tracked file), and never print full keys in harness output/logs |
| Benchmark CI workflow with unrestricted trigger (e.g., runs on every fork PR) | Cost-abuse vector — anyone can trigger expensive API-billed runs against the project's keys | Restrict to manual/maintainer-triggered runs, never auto-run on external PRs |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| README graph shown with no caption stating model version/date/rep count | Reader can't judge if the number still applies to them, or verify it themselves | Caption every graph with model snapshot, date, N reps, and a link to the raw data + reproduction command |
| Methodology doc exists but is buried several links deep from the headline claim | Skeptical readers (the ones most likely to actually check) give up and just distrust the number instead | Link the methodology and raw data directly from wherever the headline percentage appears in the README |
| Graphs show only cairn's best-case wins, no per-task or failure-rate breakdown | Reads as cherry-picked even if the underlying methodology was sound | Show per-task results (including any losses) and success/failure rates alongside the efficiency numbers |

## "Looks Done But Isn't" Checklist

- [ ] **"Benchmark suite reproducible"**: Often missing a documented, pinned-cost, one-command entry point that a third party (no prior context) can actually run — verify by having someone unfamiliar with the harness try to reproduce a single number from scratch.
- [ ] **"Token/cost metrics collected"**: Often missing the cache-read/cache-write/uncached-input decomposition and success-gated cost-per-completion — verify the raw data has these columns, not just a single blended token total.
- [ ] **"Baselines compared"**: Often missing verified environment isolation per arm (no leaked personal CLAUDE.md/MCP servers) — verify by inspecting the actual system prompt/context sent for each arm, not just the config files intended to produce it.
- [ ] **"Graphs generated and committed"**: Often missing date/model-version captions and a link to raw data — verify each published graph is self-contained enough to be judged without trusting the README prose around it.
- [ ] **"Comparison against competitor plugin"**: Often missing a re-check of the competitor's current official setup instructions and pinned version — verify against their live docs immediately before each publish, not from memory.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|------------------|
| Single-run/underpowered results already published | LOW-MEDIUM | Re-run with proper repetition count, update the graph and raw data, add a changelog note explaining the correction — transparency about a fix is itself a credibility signal |
| Home-field-advantage/environment leakage discovered post-publish | MEDIUM | Re-run all arms in a properly isolated environment, republish with a visible correction note; disclose what was found, don't quietly replace the numbers |
| Misconfigured competitor baseline flagged publicly | HIGH | Acknowledge quickly and publicly, fix the configuration (ideally with input from the competitor/community), re-run, and republish with a visible correction — speed and transparency of the fix matters more here than the original mistake |
| Benchmark numbers gone stale (model update invalidates comparison) | LOW-MEDIUM (if re-run process already exists) / HIGH (if not) | Re-run against current pinned model versions per the maintenance cadence; if no cadence existed, this is the trigger to build one, not just a one-time fix |
| Community concludes the whole benchmark is marketing, not evidence | HIGH | The only real recovery is retroactively adding what was missing — raw data, reproduction script, honest losses shown — and being visibly responsive to specific technical critiques rather than defensive; a benchmark's credibility, once lost, is regained slowly through repeated transparent iterations, not a single rebuttal post |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Single-run results (P1) | Harness design / Metrics collection | Raw results CSV has ≥5 reps per cell with median+IQR computed |
| Insufficient task sample size (P2) | Task design | Task suite has ≥10 diverse task types; per-task breakdown published, not just aggregate |
| Cherry-picked tasks (P3) | Task design | Task list includes at least one category expected to be unfavorable to cairn; selection criteria documented before results existed |
| Home-field advantage / environment leakage (P4) | Baseline isolation | Environment manifest per arm published; actual system prompt/context inspected and matches manifest |
| Misconfigured competitor baseline (P5) | Baseline isolation, re-verified before each publish | Competitor version/commit pinned and cross-checked against their current docs at publish time |
| Success not verified (P6) | Task design + Metrics collection | Every task has an automated pass/fail check; headline metric is cost-per-successful-completion, failure rate published alongside |
| Prompt-caching order effects (P7) | Metrics collection (harness design) | Execution order randomized/interleaved across arms; cost broken into 4 components in raw data |
| Undated/stale results (P8) | Publication + ongoing maintenance | Every graph captioned with model snapshot + date; re-run cadence documented and scheduled |
| Setup cost conflated with task cost (P9) | Metrics collection | Setup cost reported as separate line item; warm-up run excluded from per-task measurement unless setup is the metric being measured |
| Self-published credibility gap (P10) | Task design onward, shipped in Publication | Raw data + one-command reproduction + methodology doc linked directly from the headline claim; at least one honest non-win shown |

## Sources

- [Token Reduction Is Not Cost Reduction: An Empirical Study of End-to-End Efficiency in API-Based Coding Agents (arXiv 2607.12161)](https://arxiv.org/html/2607.12161) — HIGH confidence, directly on-domain; source for Pitfalls 6, 7, 9
- [How Many Tasks Are Enough for Agent Benchmark Decisions? A Replay Analysis of Public LLM Agent Benchmarks (arXiv 2607.12338)](https://arxiv.org/html/2607.12338v1) — HIGH confidence; source for Pitfall 2
- [Finding Widespread Cheating on Popular Agent Benchmarks (DebugML)](https://debugml.github.io/cheating-agents/) — MEDIUM-HIGH confidence; source for Pitfall 6 (task-level shortcuts/gaming)
- [Finding Widespread Cheating on Popular Agent Benchmarks (Davis Brown)](https://davisrbrown.com/blog/cheating-agents.html) — corroborating source
- [Building to the Test: Coding Agents Deliver What You Check, Not What You Requested (arXiv 2606.28430)](https://arxiv.org/html/2606.28430) — MEDIUM confidence; supports Pitfall 6
- [Evaluation and Benchmarking of LLM Agents: A Survey (arXiv 2507.21504)](https://arxiv.org/html/2507.21504v1) — MEDIUM confidence; general methodology issues (construction validity, non-reproducibility)
- [SWE-bench Contamination & AI Coding Leaderboards](https://www.buildmvpfast.com/blog/benchmark-contamination-ai-coding-leaderboard-swe-bench-2026) — MEDIUM confidence; supports Pitfalls 3, 5, 8 (contamination, self-reported/unverified leaderboard entries)
- [SWE-bench in 2026: Benchmarks vs Scaffolding Reality](https://www.digitalapplied.com/blog/swe-bench-verified-june-2026-benchmark-vs-scaffolding-analysis) — MEDIUM confidence
- [Everyone Wins Their Own Benchmark (Endor Labs)](https://www.endorlabs.com/learn/everyone-wins-their-own-benchmark) — MEDIUM confidence; direct source for Pitfall 10 ("vendor who publishes wins their own benchmark" pattern)
- [Perfectly Hitting the Wrong Target: The Story of an AI Code Review Benchmark (Hexmos)](https://journal.hexmos.com/perfectly-hitting-the-wrong-target/) — MEDIUM confidence; documents the vendor-benchmark trust collapse in the AI code-review tool space, and the Martian independent-benchmark counter-example, directly analogous to this domain
- [Debunking Devin / Devin AI benchmark criticism](https://gist.github.com/cedrickchee/588a55cbcaeb2d0faba694ae1fa560dd) and [world's first AI software engineer fails 85% of tasks](https://www.tweaktown.com/news/102761/worlds-first-ai-software-engineer-fails-85-of-its-assigned-tasks/index.html) — MEDIUM confidence; case study of published-benchmark-vs-reality gap and public backlash risk
- [Anthropic Claude API Pricing docs — prompt caching mechanics](https://platform.claude.com/docs/en/about-claude/pricing) — HIGH confidence, official source; cache-read at ~10% of input price, TTL behavior, minimum cacheable length — source for Pitfall 7
- [Claude Prompt Caching Deep Dive (Agentbrisk)](https://agentbrisk.com/blog/prompt-caching-deep-dive-2026/) — MEDIUM confidence, corroborating
- [claude-token-efficient BENCHMARK.md](https://github.com/drona23/claude-token-efficient/blob/main/BENCHMARK.md) and [claude-context-optimizer](https://github.com/egorfedorov/claude-context-optimizer) — MEDIUM confidence; real-world example from this exact ecosystem (Claude Code plugins) explicitly noting single-rep unreliability and net-negative-on-some-workloads results — directly analogous cautionary precedent
- [Model version drift / snapshot pinning best practices](https://futureagi.com/blog/model-vs-data-drift-how-to-identify-and-handle-it/) — LOW-MEDIUM confidence (general drift-monitoring content, not benchmark-specific); source for Pitfall 8 pinning recommendation, corroborated by general industry practice of pinning dated model snapshots

---
*Pitfalls research for: LLM-agent efficiency benchmark publication (CairnGo v1.1)*
*Researched: 2026-07-25*
