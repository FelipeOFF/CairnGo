# Feature Research

**Domain:** Public benchmark suite for coding-agent workflow efficiency (tokens/cost/time), published in a GitHub repo
**Researched:** 2026-07-25
**Confidence:** MEDIUM-HIGH (methodology patterns verified against multiple credible sources: SWE-bench/Terminal-Bench aggregators, Aider's official leaderboard docs, Anthropic's official API docs for cache tokens, and several real GitHub repos that publish token/cost benchmarks — including two competitors in CairnGo's exact space)

## Feature Landscape

### Table Stakes (Users Expect These)

A reader who has seen SWE-bench, Terminal-Bench, or Aider's leaderboard will not take a benchmark seriously without these. Missing any of them reads as "marketing claim," not "benchmark."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Fixed, hand-verified task corpus (task list committed to repo, not generated ad hoc) | Every credible benchmark (SWE-bench 1,865 real-commit tasks, Terminal-Bench 89 hand-crafted Docker tasks, Aider's 225 Exercism exercises) is built on a versioned, inspectable task set. Readers check "what exactly did you run?" first. | MEDIUM | Tasks should be small dev workflows representative of what cairn actually does (plan a feature, fix a bug, add a test) — not toy prompts. Version the corpus (`v0.1`) so future changes are traceable. |
| Task-completion / success verification, external to the agent | SWE-bench and Terminal-Bench are both criticized ("How We Broke Top AI Agent Benchmarks," Berkeley RDI) exactly where verification is agent-writable or agent-influenceable. A token/cost number is meaningless if the task wasn't actually finished, or if "finished" was self-graded by the agent under test. | MEDIUM | Verification script must run outside the agent's tool-call surface (e.g. a checked-out clean test harness that inspects the final repo state / runs a fixed test suite), never trust output the agent itself wrote to a shared file. |
| Cost/tokens reported *conditioned on* task completion, never in isolation | The single most repeated rule across sources: "a token comparison only counts if the task was completed equivalently." SWE-bench Pro explicitly reports Resolve Rate as the primary metric with cost as a secondary, derived number — never cost alone. | LOW | Pair every cost/token/time row with a pass/fail column in the same table. A baseline that "used fewer tokens" but failed the task must be flagged, not celebrated. |
| Token breakdown: input / output / cache-write / cache-read, not one aggregate number | Anthropic's API `usage` object exposes `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` as distinct, separately-priced fields (cache read ≈0.1x input price, 5-min cache write ≈1.25x, 1-hour ≈2x). Aggregating them into one "total tokens" number hides where the real cost sits. | LOW-MEDIUM | This is exactly the metric PROJECT.md already calls out ("input/output/cache, custo estimado"). Harness must log the raw `usage` block per turn, not just a token count. |
| Cost computed from official provider pricing, stated explicitly, with date | Artificial Analysis's methodology explicitly notes cost reflects "provider token pricing rather than consumer plans." A dollar figure with no pricing source/date is unverifiable the moment prices change. | LOW | State model name + pricing table version + date of run next to every $ figure. |
| Model + version pinning, and run date | Aider's leaderboard records model identifier and date per row for exactly this reason — model behavior drifts between versions. | LOW | Log Claude Code CLI version, model ID/snapshot, and cairn/GSD/competitor plugin version+commit for every run. |
| Reproduction instructions and raw data committed (not just claimed) | jcodemunch-mcp ships `tasks.json`, `results.md`, and the scripts that regenerate them; Tura-AI links a separate methodology repo with manifest JSONs and round contracts. Absence of this is the #1 anti-pattern (see buildomator below). | MEDIUM | `--reproduce` or `make benchmark` should be runnable by a third party with documented expected cost (already a named PROJECT.md constraint). |
| Methodology section stating what's *not* covered / known limitations | Every credible source (Aider, Artificial Analysis, jcodemunch) includes an explicit caveats/limitations section (e.g. "baseline is a lower bound," "missing values excluded rather than zeroed"). Its absence reads as either naive or evasive. | LOW | One paragraph per baseline: what it's good at, what it isn't measuring, known confounds (e.g. cache warm/cold state). |
| Multiple trials per task, variance disclosed (even if small N) | Artificial Analysis runs 3 attempts per task and averages; Holistic Agent Leaderboard explicitly argues single-run comparisons are "comparing noise." A single-shot run presented as definitive is the most common credibility failure found (see the Spec-Kit vs OpenSpec anti-pattern below). | MEDIUM-HIGH | At minimum N=3 repetitions per (task, baseline) pair; report mean + range/stdev, not just a point estimate. This is the single highest-leverage table-stakes item to get right — most amateur benchmarks skip it. |

### Differentiators (Competitive Advantage)

Where CairnGo can visibly out-credential the closest comparable projects (GSD, spec-kit, BMAD, buildomator, ralph-style loops), none of which currently publish anything close to a rigorous benchmark.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Cost-vs-completion scatter chart, log-scale x-axis, committed as an image/SVG generated by script | This is *the* recognizable "serious benchmark" visual — Aider's own leaderboard is built around exactly this plot (cost $ on log x-axis, pass-rate on y-axis). No workflow-plugin competitor (GSD, spec-kit, BMAD, buildomator) has one. Doing this first, in this specific space, is a genuine gap. | MEDIUM | Script-generated (matplotlib or similar) from the same `results.json` that feeds the tables — never hand-drawn, so it can't drift from the data. |
| Multi-baseline comparison in one run: vanilla Claude Code / GSD alone / cairn / ≥1 competitor plugin, same task set, same conditions | Nearly everything found is a two-way comparison (OpenSpec vs Spec-Kit, Tura vs Codex CLI). A clean 3-4-way baseline matrix on identical tasks is rare and directly isolates "does cairn's layer on top of GSD actually help," which is the exact claim in PROJECT.md's Core Value. | HIGH | Needs one harness abstraction that can run "vanilla," "GSD only," "cairn," and "competitor X" as swappable configs against the identical task corpus — this is the crux of the benchmark suite itself. |
| Token composition breakdown per baseline (stacked bar: input/output/cache-read/cache-write) alongside the $ total | Nobody in the workflow-plugin space breaks this down publicly; most competitor claims (buildomator's "92% lower per-turn overhead") are bare percentages with zero backing. Showing *where* the savings come from (e.g. cache hit rate from reused context) is both more convincing and harder to fake. | MEDIUM | Requires the harness to persist the raw Anthropic API `usage` object per turn, not just a rolled-up total — build this into the harness from day one since it's expensive to retrofit. |
| Turns / tool-calls count reported alongside tokens and time | The one non-token metric that recurring credible sources (OpenSpec-vs-Spec-Kit article, Tura-AI) both independently chose to add beyond raw tokens, because it correlates with agent "flailing" (many turns, low progress) in a way raw token count can hide. | LOW | Already implied by PROJECT.md's "nº de tool calls/turnos" requirement — just make sure it ships as its own column, not folded into a composite score. |
| Fully in-repo reproduction: fixed corpus + harness + chart-generation script, runnable by a third party with a documented expected $ cost before they run it | PROJECT.md already sets "custo previsível e documentado" as a constraint. Doing this makes cairn's benchmark strictly more reproducible than Terminal-Bench itself, which keeps results on an external website rather than in-repo (a real, verified gap: terminal-bench's own README has no embedded results or trial-count statement). | MEDIUM | `BENCHMARKS.md` should open with "running this suite costs approximately $X–Y at current pricing" before anything else. |
| Historical trend line across cairn releases (does token/time efficiency regress or improve version over version) | None of the reviewed competitors track this over time; it turns the benchmark from a one-off marketing artifact into an ongoing regression signal, which is a stronger, longer-lived credibility asset. | MEDIUM-HIGH | Natural v1.x follow-on once the harness exists — store `results/<version>/results.json` and let the chart script plot a series. Explicitly deferred to "Add After Validation" below; do not attempt in the first ship. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Bare percentage claim with no methodology, table, or raw data ("cairn uses 92% fewer tokens") | Fastest to write, feels punchy for a README hero line — exactly what buildomator (a direct GSD-ecosystem competitor) shipped: "~92% lower per-turn token overhead" appears only as an assertion, with zero benchmark comparison, methodology, or data anywhere in the repo. | Reads as marketing the instant a skeptical reader looks for the source; actively damages credibility once someone notices there's nothing behind it — and this is a documented, current failure mode from a direct competitor, not a hypothetical. | Every number in the README must be a hyperlink to the exact table/row in `BENCHMARKS.md` that produced it. If a claim can't cite its row, don't publish the claim yet. |
| Single-run, no-variance comparison presented as conclusive | Cheapest to produce — run the task once per baseline, report the delta. This is literally what the Spec-Kit-vs-OpenSpec community benchmark did (ran twice, no confidence interval, no statistical treatment, source "available on GitHub" but minimal rigor). | LLM agent runs are stochastic; a single run can differ by a wide margin from the mean purely by chance (temperature, tool-call path taken, retries). Presenting N=1 as fact invites exactly the "comparing noise" critique leveled at major benchmarks. | Minimum N=3 per (task, baseline), report mean and spread. If cost makes N=3 infeasible for all tasks, run N=1 for the full corpus and N≥3 for a small "headline" subset, and say so explicitly. |
| A single opaque composite "score" (one number blending pass-rate + cost + speed) as the *only* thing shown | Feels convenient for a leaderboard-style headline (Artificial Analysis's Coding Agent Index does this). | An opaque index can hide a cost regression behind a pass-rate gain, and readers can't audit it without the raw components. It's the layer most exposed to "gaming" critique. | Show raw metrics (pass rate, tokens, cost, time, turns) side by side, always. A derived index is fine as an *additional* summary column, never as a replacement for the breakdown. |
| Externally-verifiable but agent-writable pass/fail check (agent's own tool output decides success) | Simplest harness to build — just check what the agent's last message or its own test run said. | Directly the vulnerability named in "How We Broke Top AI Agent Benchmarks" (Berkeley RDI): SWE-bench trusts pytest output from inside a container the agent controls; Terminal-Bench trusts reward files scripts the agent can tamper with. A benchmark whose own verification can be gamed by the thing being measured is not credible, and it's a well-documented failure class. | Verification must run in a separate process/step the agent cannot write to — clone the result to a clean checkout, run the acceptance test suite there, independent of anything the agent claimed. |
| Comparing baselines on non-identical task variants or difficulty levels ("apples-to-oranges") | Tempting shortcut when one baseline (e.g. vanilla Claude Code) can't use cairn's structured task decomposition, so it's easy to let each baseline solve "an equivalent but not identical" version of the task. | Breaks the core validity rule found repeatedly in research: a comparison is only meaningful if the task and success bar are identical across baselines. Any difference becomes an unfalsifiable excuse for the result. | Same literal task prompt/spec and same acceptance test for every baseline; only the *workflow* (vanilla vs GSD vs cairn vs competitor) varies. |
| Continuous telemetry from real user sessions as the source of comparison numbers | Feels more "real-world" than synthetic tasks, and PROJECT.md flags this was actively considered. | Already explicitly ruled out in PROJECT.md ("Telemetria contínua... não escolhida") — and research confirms why: telemetry from different real sessions is never apples-to-apples (different tasks, different repos, different users), so it can't produce a defensible baseline-vs-baseline comparison the way a fixed reproducible suite can. | Fixed task corpus + harness, run by anyone, any time — this is exactly what CairnGo already decided, and the research validates it as the right call. |
| A hosted dashboard/leaderboard website as the primary presentation surface | Feels more "professional" — it's literally what Terminal-Bench does (results live at tbench.ai, not in the repo README). | Already explicitly out of scope for this milestone (PROJECT.md), and it adds infrastructure/maintenance burden without which the repo-embedded chart pattern (Aider, Tura-AI) already reads as credible. Building it now would also violate the "zero infra" rationale already logged in Key Decisions. | Commit generated charts (PNG/SVG) + `BENCHMARKS.md` + `results.json` directly to the repo, exactly as decided. Revisit a hosted site only if/when the static approach becomes a real bottleneck. |
| Tuning the harness or prompts specifically to make cairn win the benchmark it publishes | Obvious temptation once the suite exists and the numbers are public. | This is precisely the "gaming/contamination" failure mode documented across multiple sources (training on benchmark-adjacent data, scaffolding tuned to the eval, cherry-picked runs inflating scores by up to 100 points in one cited case). It would be self-defeating for a project whose whole differentiator is "honesty stands up to scrutiny" (PROJECT.md's explicit constraint). | Freeze the task corpus and harness config before running any baseline; treat any post-hoc tuning of cairn's prompts/behavior specifically to improve benchmark numbers as a methodology violation to disclose, not hide. |

## Feature Dependencies

```
Fixed, hand-verified task corpus
    └──requires──> Multi-baseline harness abstraction (vanilla/GSD/cairn/competitor, same tasks)
                       └──requires──> External, agent-unwritable task verification (pass/fail)
                                          └──requires──> Token/cost/time logging per turn (input/output/cache-read/cache-write)
                                                             └──requires──> Cost computation from official pricing table
                                                                                └──enhances──> Cost-vs-completion scatter chart (script-generated, committed)
                                                                                └──enhances──> Token composition breakdown chart

Multiple trials per (task, baseline) [N>=3]
    └──enhances──> Variance/spread reporting in BENCHMARKS.md
    └──conflicts──> Documented, bounded suite cost (more trials = higher $ cost; must trade off corpus size vs N)

Reproduction script + methodology doc
    └──requires──> Fixed task corpus + harness + raw results.json committed to repo
    └──enhances──> Third-party credibility (README claims can hyperlink to the exact producing row)

Hosted dashboard/leaderboard website [OUT OF SCOPE]
    └──conflicts──> "Zero infra, repo-embedded charts" decision already logged in PROJECT.md

Continuous session telemetry [OUT OF SCOPE]
    └──conflicts──> Apples-to-apples baseline comparison (different real sessions are never equivalent tasks)

Opaque single composite score
    └──conflicts──> Raw metric transparency (must show pass-rate/cost/tokens/time separately, not just blended)
```

### Dependency Notes

- **Multi-baseline harness requires external verification:** without a verification step the agent under test cannot influence, none of the cost/token numbers downstream are trustworthy — this must be built and tested before any baseline is run "for real," not bolted on after.
- **Cost/token charts require per-turn `usage` logging:** the four-way token breakdown (input/output/cache-write/cache-read) cannot be reconstructed after the fact from a rolled-up total — the harness must capture the raw API `usage` object at the point each baseline calls Claude, so this is a day-one harness requirement, not a v1.x add-on.
- **N>=3 trials conflicts with bounded suite cost:** PROJECT.md's constraint that the suite be "rodável por terceiros com custo previsível" pushes toward a *small* task corpus so that N>=3 repetitions per baseline stay affordable; a large corpus with N=1 is cheaper but fails the variance table-stakes item. Resolve by keeping the headline corpus small (handful of representative tasks) and explicit about the $ budget, rather than compromising on repetition count.
- **Hosted dashboard conflicts with the already-made decision:** flagged here only so the roadmap doesn't accidentally reintroduce it as a "nice differentiator" — research confirms the repo-embedded pattern (Aider, Tura-AI) is already sufficient for credibility; a website is not required to compete on rigor.
- **Opaque composite score conflicts with the transparency table-stakes:** if a future phase adds a single "cairn efficiency score" for headline purposes, it must be additive to (never a replacement for) the raw per-metric breakdown, or it reintroduces the exact criticism leveled at less transparent leaderboards.

## MVP Definition

### Launch With (v1.1, matches PROJECT.md Active requirements)

- [ ] Fixed, small, hand-verified task corpus (representative dev workflows: e.g. add a feature, fix a bug, add tests) — versioned in-repo — *why essential:* nothing downstream is credible without it
- [ ] Multi-baseline harness: vanilla Claude Code, GSD alone, cairn, ≥1 competitor plugin, run against identical tasks — *why essential:* this is the actual comparison PROJECT.md's Core Value depends on
- [ ] External, agent-unwritable task-completion verification (pass/fail) — *why essential:* makes every other number meaningful; the single highest-risk item to skip
- [ ] Per-turn token logging broken into input/output/cache-write/cache-read + $ cost from official pricing, with model/version/date recorded — *why essential:* directly the PROJECT.md requirement, and the differentiator vs every competitor's bare-percentage claims
- [ ] Wall-clock time + turn count/tool-call count per run — *why essential:* directly the PROJECT.md requirement; also the signal that catches "fewer tokens but flailing more"
- [ ] N>=3 repetitions per (task, baseline) with mean+spread reported — *why essential:* the #1 credibility gap found across community benchmarks in this exact space (Spec-Kit vs OpenSpec ran once)
- [ ] `BENCHMARKS.md` methodology doc: task corpus description, pricing source/date, model versions, reproduction command, expected $ cost to reproduce, explicit caveats/limitations section
- [ ] Script-generated charts committed to repo and embedded in README: cost-vs-completion scatter (log-x) + token composition breakdown — regenerable from `results.json`, never hand-edited

### Add After Validation (v1.x)

- [ ] Additional competitor baselines beyond the first one — *trigger:* once the harness abstraction proves stable across 2+ baselines, adding more is low-marginal-cost
- [ ] Larger/more diverse task corpus (multi-file refactors, debugging, cross-cutting changes) — *trigger:* once the small headline corpus has validated the harness and readers ask "does this hold on harder tasks"
- [ ] Historical trend chart across cairn releases — *trigger:* once there are at least 2-3 tagged cairn versions with stored `results.json` to plot
- [ ] CI regression gate that flags a token/cost/time regression beyond a threshold on PRs — *trigger:* once the suite is cheap/fast enough to run routinely, not just for milestone releases

### Future Consideration (v2+)

- [ ] Hosted leaderboard/dashboard website — *why defer:* explicitly out of scope per PROJECT.md; repo-embedded charts already meet the credibility bar set by comparable projects (Aider, Tura-AI)
- [ ] Continuous real-session telemetry as a supplementary data source — *why defer:* explicitly ruled out; would need a fundamentally different (and much harder to defend) methodology than the fixed-suite approach already chosen
- [ ] Community-submitted baseline configs (other plugins beyond the initial competitor) — *why defer:* needs a stable, documented harness contract first; premature before v1.1 ships

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Fixed task corpus + external verification | HIGH | MEDIUM | P1 |
| Multi-baseline harness (vanilla/GSD/cairn/competitor) | HIGH | HIGH | P1 |
| Per-turn token breakdown (input/output/cache) + $ cost | HIGH | LOW-MEDIUM | P1 |
| Time + turns/tool-calls per run | MEDIUM | LOW | P1 |
| N>=3 trials with variance reporting | HIGH | MEDIUM-HIGH | P1 |
| BENCHMARKS.md methodology + reproduction doc | HIGH | LOW | P1 |
| Cost-vs-completion scatter chart (script-generated) | HIGH | MEDIUM | P1 |
| Token composition breakdown chart | MEDIUM | LOW-MEDIUM | P2 |
| Additional competitor baselines | MEDIUM | LOW (once harness exists) | P2 |
| Larger/harder task corpus | MEDIUM | MEDIUM | P2 |
| Historical trend chart across releases | MEDIUM | MEDIUM | P3 |
| CI regression gate on benchmark metrics | LOW-MEDIUM | MEDIUM | P3 |
| Hosted dashboard/leaderboard site | LOW (given repo-embedded already sufficient) | HIGH | P3 (deferred, out of scope) |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Aider Leaderboard | SWE-bench / Terminal-Bench | GSD-ecosystem competitors (buildomator, OpenSpec-vs-Spec-Kit article) | Tura-AI | Our Approach |
|---------|--------------------|------------------------------|--------------------------------------------------------------------|---------|--------------|
| Task corpus | 225 versioned Exercism exercises, public | 1,865 real-commit tasks (SWE-bench Pro) / 89 hand-crafted Docker tasks (Terminal-Bench) | Ad hoc: one MVP chat-app task, run twice | 25 DeepSWE + 5 rewrite + 2 design tasks, versioned manifest | Small, versioned, hand-verified dev-workflow corpus in-repo |
| Verification | Unit-test pass/fail, second attempt on failure | External test suite, but flagged as agent-tamperable in places | Not clearly external/independent | External, documented in a separate methodology repo | External, agent-unwritable pass/fail per task |
| Cost reporting | $ per full benchmark run, per model, on leaderboard table | $ per task (Resolve Rate paired w/ Average Cost) | Token counts only, no $ | Tokens + turns, cost inferred | $ from official pricing + input/output/cache breakdown, paired with pass/fail |
| Trials/variance | Not clearly multi-trial per exercise | 3 attempts/task averaged (Artificial Analysis aggregator) | Single run x2 (no variance treatment) | Not fully disclosed per-task | N>=3 per (task, baseline), mean+spread reported |
| Visual presentation | Interactive scatter (cost log-x vs pass-rate y), on leaderboard site | External leaderboard site, no embedded repo charts | None (bare README claim) | SVG chart embedded directly in README | Script-generated charts committed to repo + embedded in README |
| Reproducibility | Public exercises + aider CLI commands per row | Public repo/tasks, external submission process | Source "available on GitHub," minimal rigor | Public methodology repo, manifest JSONs linked | `BENCHMARKS.md` + `results.json` + regen script, in-repo, documented $ cost |
| Multi-baseline (workflow-level, not just model-level) | No (compares LLMs, not workflows) | No | Two-way only (Spec-Kit vs OpenSpec) | Two-way (Tura vs Codex CLI) | Three-to-four-way: vanilla / GSD / cairn / competitor, same tasks |

## Sources

- [Aider LLM Leaderboards (official docs)](https://aider.chat/docs/leaderboards/) — HIGH confidence, official source
- [Aider Benchmarks Scatter Plot (VizHub)](https://vizhub.com/curran/aider-benchmarks-scatter-plot) — MEDIUM confidence, community visualization of official data
- [SWE-bench Pro Leaderboard (Morph)](https://www.morphllm.com/swe-bench-pro) — MEDIUM confidence, third-party aggregator
- [Holistic Agent Leaderboard (arXiv 2510.11977)](https://arxiv.org/pdf/2510.11977) — HIGH confidence, peer-reviewed methodology paper; source of "cost-adjusted comparison" and multi-rollout argument
- [Artificial Analysis: Coding Agent Index Methodology](https://artificialanalysis.ai/methodology/coding-agents-benchmarking) — MEDIUM-HIGH confidence, published methodology
- [Terminal-Bench GitHub repo](https://github.com/laude-institute/terminal-bench) — MEDIUM confidence, verified README does not embed results/trial-count in-repo
- [How We Broke Top AI Agent Benchmarks (Berkeley RDI)](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/) — HIGH confidence, source of the agent-writable-verification anti-pattern
- ["Spec Driven Development Is Wasting Tokens" (Medium/IT Chronicles)](https://medium.com/it-chronicles/is-your-safe-choice-burning-your-budget-1cfddf8782e4) — LOW-MEDIUM confidence (single community benchmark, N=2 runs, no variance treatment) — used as an anti-pattern example, not as a factual claim about Spec-Kit/OpenSpec
- [buildomator (jnuyens/gsd-plugin) GitHub repo](https://github.com/jnuyens/gsd-plugin) — MEDIUM confidence, direct verification that the "~92% lower per-turn token overhead" claim has no supporting data in-repo (verified anti-pattern, current direct GSD-ecosystem competitor)
- [Tura-AI/tura GitHub repo](https://github.com/Tura-AI/tura) — MEDIUM confidence, verified example of embedded chart + linked methodology repo + disclosed evidence gaps
- [jcodemunch-mcp benchmarks/README.md](https://github.com/jgravelle/jcodemunch-mcp/blob/main/benchmarks/README.md) — MEDIUM confidence, verified example of a well-structured in-repo BENCHMARKS.md (methodology, task corpus table, caveats section)
- [Anthropic Prompt Caching official docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — HIGH confidence, official documentation of `cache_creation_input_tokens`/`cache_read_input_tokens`/`input_tokens` fields and pricing multipliers
- [BMAD-METHOD token efficiency claims discussion (Medium)](https://medium.com/@hieutrantrung.it/from-token-hell-to-90-savings-how-bmad-v6-revolutionized-ai-assisted-development-09c175013085) — LOW confidence, self-reported claims with contradicting caveats found in the same search (31,667 tokens/run, ~$847/month reported by users) — used to illustrate the "big % claim, weak backing" anti-pattern
- CairnGo project context: `/Users/felipeoliveira/Projects/CairnGo/.planning/PROJECT.md`

---
*Feature research for: public benchmark suite for coding-agent workflow efficiency*
*Researched: 2026-07-25*
