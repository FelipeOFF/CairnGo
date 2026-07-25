# Stack Research

**Domain:** Automated benchmarking of Claude Code agent workflows — token/cost/time measurement + reproducible, commitable chart generation
**Researched:** 2026-07-25
**Confidence:** HIGH (core measurement APIs verified against current `code.claude.com` docs); MEDIUM/LOW flagged inline where docs were incomplete or the feature is undocumented/beta

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|------------------|
| `claude -p --output-format json` (Claude Code CLI, headless/"print" mode) | Pin an exact CLI version for the whole benchmark run (e.g. record `claude --version` in results) | Executes one benchmark task non‑interactively and returns a single authoritative JSON object with cost, tokens, timing and turn count | This is Anthropic's own documented measurement surface, not a reverse‑engineered one. The final `result` object carries `total_cost_usd`, `usage` (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`), `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`, `session_id`. One JSON blob per run = trivial to parse with `jq`/`python3 json`, no format drift to chase. **HIGH confidence** — verified verbatim against `code.claude.com/docs/en/headless` and the Agent SDK TypeScript type reference. |
| `claude -p --output-format stream-json --verbose` (same CLI, streaming variant) | Same pinned version | Gives the same final `result` message **plus** a live event stream (`assistant`/`tool_use`/`tool_result`/`system` events) for the same run | Needed to count *tool calls* (Bash, Edit, Read, …) per task — a metric the plain `json` format does not expose (it only gives `num_turns`, which is coarser than tool-call count). Using the documented stream events avoids a second, undocumented parse of `~/.claude/projects/*.jsonl` just to count tool uses. **HIGH confidence** — message types (`system/init`, `stream_event`, final `result`) are documented in `docs/en/headless` and `docs/en/agent-sdk/typescript`. |
| Python 3, stdlib only | Any modern 3.x (matches repo's existing "any modern 3.x, stdlib-only" rule) | Harness orchestration: fixture setup, subprocess invocation of `claude`, JSON/NDJSON parsing, aggregation across repetitions/baselines, CSV/JSON result files, chart data prep | Matches the repo's explicit house style (`cairn/scripts/*.py`, stdlib-only) and the milestone's own constraint ("benchmark harness segue o molde de `cairn/scripts/`"). `json` module handles both the `--output-format json` result and the NDJSON `stream-json` lines with zero extra dependencies. |
| Bash wrappers (`set -euo pipefail`) | POSIX-ish bash, portable to macOS's bash 3.2 | Thin CLI entry points (`benchmarks/run-benchmark.sh`, `benchmarks/plot-results.sh`) that call the Python logic, matching every other script in `cairn/scripts/` | Consistency with the rest of the repo; keeps the benchmark suite runnable the same way (`bash script.sh`) as everything else, no new invocation convention to learn. |
| gnuplot (external CLI binary, `set terminal svg`) | Any gnuplot ≥ 5.x (clustered-histogram + errorbars styles are stable since the 4.2/4.6 era, so any recent Homebrew/apt build works) | Renders the final grouped bar charts (baseline × metric, with error bars across repetitions) to static `.svg` files committed to the repo | Fits the *existing* dependency pattern of this repo exactly: `bd`, `gh`, `git` are all "critical external CLI binaries, not language packages" (per `.planning/codebase/STACK.md`). gnuplot is the same category — one `brew install gnuplot` / `apt install gnuplot`, zero Python packages, zero `requirements.txt`, zero venv. Its `histogram cluster` + `errorbars` styles are exactly what's needed for "3 baselines × N metrics, with variance across repetitions" charts, and are far more mature than hand-rolling the same statistics in raw SVG. **HIGH confidence** on the feature set (long-standing, stable gnuplot functionality); **MEDIUM confidence** on "best choice for this repo" (a value judgement, not a doc fact). |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `jq` | already a repo dependency (used by `.bats` tests) | Extract fields from `claude -p --output-format json` output directly in bash wrappers before handing off to Python (`claude -p ... --output-format json \| jq '{cost: .total_cost_usd, usage}'`) | Quick shell-level sanity checks, or as the extraction step inside a bash wrapper. Prefer Python's `json` module for anything that needs aggregation across many runs (statistics, CSV writing) — `jq` alone gets unwieldy past simple field extraction. |
| OpenTelemetry console/OTLP exporter (`CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER=console\|otlp`) | N/A (env-var driven, no package to install for the console exporter) | Optional, advanced: attribute cost/tokens to specific tools/agents/skills/plugins within a run (`claude_code.token.usage` and `claude_code.cost.usage` carry `agent.name`, `skill.name`, `plugin.name`, `mcp_tool.name` attributes) or cross-check the CLI's own `total_cost_usd`/`usage` against an independent export path | Only if the roadmap needs *per-tool or per-agent* attribution across a whole benchmark batch (e.g. "how many tokens did cairn's `/cairn:status` skill invocation cost vs the rest of the turn"). For the headline vanilla/GSD/cairn/competitor comparison, the `result` JSON from each `-p` call is sufficient and much simpler to wire up. **HIGH confidence** on the metric names/attributes (verified against `code.claude.com/docs/en/monitoring-usage`); note the default export interval is 60s and events 5s — lower `OTEL_METRIC_EXPORT_INTERVAL` for short benchmark tasks or metrics may not flush before the process exits. |
| `ccusage` (`npx ccusage@latest`) | latest | Human-facing, ad-hoc spot-check of Claude Code usage/cost history (`session`, `daily`, `blocks` subcommands, `--json` output) | Use manually, outside the automated harness, to sanity-check a suspicious run or explore historical usage. **Do not** wire it into the automated pipeline (see "What NOT to Use"). |
| bats-core (already a repo dependency) | already pinned in `tests/README.md` | Test the harness itself: fixture setup/teardown, JSON-schema assertions on the `result` object shape, chart-script smoke tests (SVG file produced, well-formed) | Extend the existing `tests/*.bats` convention into `tests/benchmark-*.bats` rather than introducing a second test framework. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Dev Container / Docker sandbox | Safe execution environment for `--dangerously-skip-permissions` runs | Anthropic's own devcontainer docs state the pattern explicitly: "Because the container runs Claude Code as a non-root user and confines command execution to the container, you can pass `--dangerously-skip-permissions` for unattended operation" (`code.claude.com/docs/en/devcontainer`, **HIGH confidence**, official). The Best Practices guidance is that this flag should only be used in a sandbox **without internet access beyond the API endpoint** — running it unsandboxed on a developer's real machine or a CI runner with full network access is explicitly discouraged upstream, independent of this project's own concerns. |
| Disposable fixture directories (`mktemp -d` + copy of a committed fixture repo, or `git worktree add`) | Isolate each benchmark task/repetition so no run's file-system state leaks into the next | Claude Code's session transcript path is derived from the working directory (`~/.claude/projects/<hashed-cwd>/...`), so a fresh directory per run already gives clean transcript separation even before touching `HOME`. |
| `HOME=<tmp-dir>` override per run | Isolate `~/.claude` (global CLAUDE.md, hooks, MCP servers, settings) between runs and between baselines | `CLAUDE_CONFIG_DIR` exists but is **undocumented and has multiple open bugs** (inconsistent behavior between CLI and VS Code, "still creates local `.claude/` directories" — see anthropics/claude-code#3833, #28808, #33430). Overriding `HOME` for the subprocess is the standard, verifiable CI isolation technique and doesn't depend on an unstable flag. Combine with `--bare` (skips hook/skill/plugin/MCP/CLAUDE.md auto-discovery) when the goal is "measure Claude Code itself," and *without* `--bare` when the goal is "measure the cairn plugin's effect" (since `--bare` would also skip cairn's own hooks). |
| `--model <pinned-id>` | Pin the exact model for every run in the suite | Model version changes token/behavior distributions between releases; without pinning, a rerun weeks later is not comparable. Record the resolved model string in the results file. |
| `--max-turns <N>` | Prevent a runaway task from inflating one run's cost/time and skewing the comparison | Print-mode-only flag, exits with an error at the limit — treat that as a task failure in the harness, not a crash. |
| `python3 -c "import time; print(time.time())"` (or equivalent) for external wall-clock | Measure wall time around the whole `claude` invocation, independent of Claude's own internal timers | macOS ships bash 3.2 (already a documented constraint of this repo) which lacks `$EPOCHREALTIME` (bash 5+) and BSD `date` lacks `%N`. Python's `time.time()` is portable across the same macOS/Linux matrix the rest of the repo already targets. Report **three** time numbers per run, not one: external wall-clock (process start→exit), `duration_ms` (Claude's own total), and `duration_api_ms` (API-only time, excluding local tool execution) — the gap between `duration_ms` and `duration_api_ms` is a decent proxy for "time spent running Bash/tools locally." |

## Installation

```bash
# Core measurement primitive — already present if Claude Code CLI is installed
claude --version   # pin and record this in every benchmark results file

# Chart rendering (external CLI binary, same category as bd/gh)
brew install gnuplot        # macOS
# apt-get install gnuplot   # CI (ubuntu-latest, matches existing CI target)

# Everything else (harness, parsing, aggregation) is python3 stdlib + bash — no installs.
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `claude -p --output-format json` `result` object as the primary cost/token source | Parsing `~/.claude/projects/*.jsonl` transcripts directly | Only for supplementary detail the `result` object doesn't carry (e.g. per-message content, exact tool inputs). The JSONL format is not officially schema'd/versioned by Anthropic — treat it as best-effort, cross-checked against the `result` totals, never as the sole source of truth for headline numbers. |
| gnuplot → static `.svg` committed to repo, embedded via standard markdown image syntax | Pure-Python stdlib hand-rolled SVG generator | If the team wants **zero external binaries at all**, not just zero pip packages (i.e. gnuplot itself is unavailable in some target CI image). A ~150-200 line stdlib script covering grouped bars + simple error whiskers is enough for 3-4 baselines × 2-3 metrics; more chart variety becomes a maintenance burden fast. |
| gnuplot | matplotlib (`pip install matplotlib`) | Only if the project explicitly decides to relax the zero-pip-dependency constraint for the *benchmarks/ subtree specifically* (isolated `requirements.txt` + venv, never touching the plugin runtime). Matplotlib is more capable for complex statistical plots (box plots, violin plots, multi-panel figures) if the benchmark analysis grows beyond simple grouped bar charts — but it is a real, non-trivial dependency (pulls in numpy) and would be the **first pip dependency this repo has ever had**. |
| Static `.svg`/`.png` committed and embedded with `![]()` | Mermaid `xychart-beta` code block embedded directly in `README.md` | Only for a lightweight, no-build-step supplementary chart (e.g. a single trend line), and only after **manually verifying it renders** on the actual GitHub instance being targeted — see "What NOT to Use." |
| `--output-format json`/`stream-json` `result`/`usage` fields | OpenTelemetry metrics (`claude_code.token.usage`, `claude_code.cost.usage`) | When per-tool/per-agent/per-skill cost attribution *within* a single task is needed (OTel attributes include `agent.name`, `skill.name`, `plugin.name`, `mcp_tool.name`) — useful if a later milestone wants to show "cairn's hooks add only X% overhead," not just aggregate task cost. |
| `HOME` override per subprocess | `CLAUDE_CONFIG_DIR` | Never, until Anthropic documents and stabilizes it (see "What NOT to Use"). |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| matplotlib/numpy as the *default* charting stack | Introduces this repo's first-ever pip/venv dependency; contradicts the explicit house style ("python3 zero-dependências") and the milestone's own stated constraint that the harness "segue o molde de `cairn/scripts/`" | gnuplot (external CLI binary, same category as `bd`/`gh`) for anything beyond trivial charts; pure stdlib SVG for teams wanting zero external binaries too |
| Mermaid `xychart-beta` as the *primary/only* chart source | It is an explicitly "beta" Mermaid diagram type (added in Mermaid v10.5). GitHub's own diagram docs (`docs.github.com/.../creating-diagrams`) list only **mermaid, geoJSON, topoJSON, and ASCII STL** as supported, without confirming which Mermaid diagram *types* are enabled at GitHub's pinned Mermaid version — the docs explicitly tell you to run an `info` command inside a Mermaid block to check. Relying on an unverified, versioned, "beta" feature for the project's flagship credibility artifact is a fragile bet | Static `.svg`/`.png` files committed to the repo and embedded via standard markdown image syntax — GitHub sanitizes but always renders committed SVG/PNG images, independent of any Mermaid version pinning |
| `ccusage` wired into the automated harness | It's a Node/npm tool (introduces a second language runtime dependency into a Python/Bash-only repo) and it reads globally from `~/.claude/projects/` across *all* Claude Code usage ever recorded on the machine — scoping it cleanly to one benchmark invocation requires extra filtering hacks on top of what it already does. The CLI's own `--output-format json` per invocation is self-contained and authoritative | `claude -p --output-format json`, parsed per-run; keep `ccusage` as an optional manual/human debugging tool only |
| `CLAUDE_CONFIG_DIR` for run isolation | Undocumented (does not appear in official `env-vars` docs) with multiple open upstream bugs reporting inconsistent behavior (anthropics/claude-code#3833, #28808, #33430) | `HOME=<tmp-dir>` override per subprocess, combined with `--bare` when the intent is to exclude local hooks/skills/MCP/CLAUDE.md |
| Running `--dangerously-skip-permissions` directly on a developer machine or an internet-connected CI runner | Anthropic's own guidance restricts this flag to a sandbox without broader internet access, because it bypasses every permission prompt including destructive Bash commands and file writes outside the intended scope | Dev Container / Docker sandbox per the official `code.claude.com/docs/en/devcontainer` pattern (non-root user, confined to container, network egress restricted to the API endpoint) |
| Collapsing `input_tokens`/`output_tokens`/`cache_creation_input_tokens`/`cache_read_input_tokens` into a single "tokens used" number for cost comparisons | `cache_read_input_tokens` costs roughly 10% of a base input token; `cache_creation_input_tokens` costs roughly 25% more (5-minute TTL). A baseline that happens to get more cache hits (e.g. because it ran second in a batch, right after a structurally similar prompt) will look artificially cheaper/faster if the four token types are merged into one figure | Report all four token types as separate columns/series; when comparing baselines, either randomize run order across baselines (don't run all-vanilla-then-all-cairn back to back) or explicitly note and control for cache-order effects in the methodology |
| Trusting `/cost` (interactive slash command) for automated measurement | It's designed for the interactive terminal UI, not `-p`/headless scripting — several built-in slash commands are documented as terminal-interface-only | `--output-format json`'s `total_cost_usd` field, returned on every single headless invocation with no extra command needed |

## Stack Patterns by Variant

**If the goal is "measure Claude Code itself" (vanilla baseline):**
- Use `--bare` to skip hooks/skills/plugins/MCP/CLAUDE.md auto-discovery
- Because `--bare` guarantees the same minimal context on every machine, which is exactly what a "vanilla" baseline should mean

**If the goal is "measure cairn's (or GSD's) effect":**
- Do **not** use `--bare` (it would also suppress cairn's/GSD's own hooks and capability contributions) — instead use `--settings <pinned-json>` and/or `--setting-sources project` to load only the plugin under test, plus `HOME=<tmp-dir>` to keep everything else (personal `~/.claude`) out of the run
- Because the whole point of this baseline is to measure the plugin's real hook/skill/command overhead and savings, not to strip it out

**If gnuplot is unavailable in a target CI image:**
- Fall back to the bundled pure-stdlib SVG generator
- Because it has zero install step and the chart requirements (grouped bars, simple error whiskers) are well within reach of ~150-200 lines of hand-rolled SVG

**If a later milestone needs per-tool/per-hook cost attribution (not just per-task totals):**
- Add the OpenTelemetry console exporter (`CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER=console`, short `OTEL_METRIC_EXPORT_INTERVAL`) alongside the `result` JSON, and cross-check the two
- Because OTel is the only documented source that attributes tokens/cost to `agent.name`/`skill.name`/`plugin.name`/`mcp_tool.name`, which `--output-format json` does not expose

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `claude` CLI | Pin one specific version for the entire benchmark suite run (record `claude --version` output alongside results) | Several relevant behaviors are version-gated: `--max-turns` handling of queued stream-json messages (min 2.1.205), `--forward-subagent-text` for full subagent transcripts (min 2.1.211), stream drain wait on exit extended to 30s (min 2.1.214), background-task exit grace period fix (min 2.1.163/2.1.182). A benchmark comparing "before/after" cairn changes must pin the same CLI version across both arms, or the CLI version itself becomes a confound. |
| gnuplot ≥ 5.x | `set style histogram cluster` + `set style histogram errorbars` | Both styles have been stable since gnuplot 4.2/4.6-era docs; any current Homebrew/apt gnuplot build satisfies this. |
| Python 3.x (any) | stdlib `json`, `subprocess`, `statistics` modules | No version-specific behavior needed; matches the existing repo-wide "any modern 3.x" policy. |

## Sources

- `code.claude.com/docs/en/headless` — verified `--output-format json`/`stream-json` fields, `--bare`, examples for `total_cost_usd`/`.result` extraction, stream event structure (HIGH confidence, fetched directly)
- `code.claude.com/docs/en/cli-reference` — verified exact flags/values for `--model`, `--max-turns`, `--session-id`, `--dangerously-skip-permissions`, `--permission-mode` (values: `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`, `manual`), `--bare`, `--output-format`, `--settings`, `--add-dir` (HIGH confidence, fetched directly, quoted verbatim)
- `code.claude.com/docs/en/monitoring-usage` — verified OpenTelemetry metric names (`claude_code.token.usage`, `claude_code.cost.usage`, `claude_code.session.count`, `claude_code.lines_of_code.count`, `claude_code.active_time.total`), attributes, and exporter env vars (HIGH confidence, fetched directly)
- `code.claude.com/docs/en/devcontainer` — verified official guidance that `--dangerously-skip-permissions` is intended for sandboxed, non-root, network-restricted execution (HIGH confidence, quoted)
- `code.claude.com/docs/en/env-vars` — checked for `CLAUDE_CONFIG_DIR`/telemetry/cache env vars; confirmed `ANTHROPIC_API_KEY` headless behavior and `CLAUDE_CODE_ATTRIBUTION_HEADER`; did **not** find `CLAUDE_CONFIG_DIR` documented here (MEDIUM confidence — page fetch may have been partial, but corroborated by community reports that it's undocumented)
- `github.com/anthropics/claude-code` issues #3833, #28808, #33430 — corroborate `CLAUDE_CONFIG_DIR` is real but undocumented/buggy (MEDIUM confidence, community/issue-tracker source, not official docs)
- `docs.github.com/.../creating-diagrams` — verified GitHub natively supports exactly four fenced-code diagram types: mermaid, geoJSON, topoJSON, ASCII STL; does **not** confirm Mermaid `xychart-beta` specifically, tells users to check via an `info` command (HIGH confidence on the four-type list, fetched directly; LOW confidence on xychart-beta support specifically — unresolved)
- WebSearch, multiple queries, cross-referenced against the official-docs fetches above — used for `ccusage` feature summary (Node/npm tool, `session`/`daily`/`monthly`/`blocks` subcommands, `--json`, `--project` filter) and gnuplot histogram/errorbars syntax (MEDIUM confidence — not fetched from a single canonical doc page, but consistent across multiple independent sources and matches long-standing, stable gnuplot behavior)
- Community source on JSONL transcript format (`~/.claude/projects/<project>/<session-id>.jsonl`, fields `message.usage.{input_tokens,output_tokens,cache_creation_input_tokens,cache_read_input_tokens}`) — MEDIUM confidence, not an official schema, consistent with the officially-documented SDK message types but should be treated as best-effort/reverse-engineered

---
*Stack research for: automated Claude Code benchmark harness (tokens/cost/time measurement + reproducible charts)*
*Researched: 2026-07-25*
