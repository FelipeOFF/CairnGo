# Phase 4: Competitor Baseline - Research

**Researched:** 2026-07-26
**Domain:** Selecting and provisioning a non-GSD Claude Code workflow plugin as a fair, headless-viable competitor baseline arm
**Confidence:** HIGH (candidate structure/licensing/pinning verified live via `gh api`/`git ls-remote`/official docs; MEDIUM on runtime behavior — no ANTHROPIC_API_KEY available this session to observe a live trigger/completion rate, flagged explicitly below)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Must NOT be GSD-family**: `buildomator/buildomator` IS upstream GSD (renamed; verified live in Phase 2) — the `gsd-only` arm already covers it. Candidates: GitHub spec-kit, BMAD-method, ralph-specum, or another non-GSD Claude Code workflow plugin with real adoption.
- **Decisive criterion: headless viability** — the plugin must work under `claude -p` + `--plugin-dir` provisioning in an isolated HOME with API-key auth (the pipeline shipped in Phase 2). A competitor that can't run headless can't be benchmarked fairly; research must VERIFY this per candidate (not assume), and pick the strongest candidate that passes.
- **Pin exactly** like the others: repo + tag/commit, recorded in the manifest with a dated comment.
- Fairness discipline (non-negotiable — Pitfall 5): the competitor runs on **its own documented defaults** — its README/quickstart is the configuration authority, mirrored into the manifest. No tuning it down, no tuning cairn up.
- Same task prompt, same fixture, same pinned model, same `claude_flags` as every other arm; only provisioning differs.
- The manifest carries a `defaults_source` field: URL/path of the competitor doc the configuration was taken from, so any reader can audit the arm's setup against the vendor's own instructions.
- Re-verification checkpoint is part of the phase (the roadmap demands it): after staging, an explicit check that the competitor plugin actually LOADS and its commands are visible to claude in the isolated env — a silently-broken arm measuring "vanilla with dead weight" is the misconfiguration disaster this phase exists to prevent.
- Mechanics (reuse, don't invent): `stage-plugins.py` gets the competitor entry (git+tag provisioning, same shape as GSD's). New `benchmarks/baselines/competitor-<name>.json` manifest (name carries the plugin, e.g. `competitor-spec-kit`). Stub-first tests as always; CI $0. Live validation conditional on ANTHROPIC_API_KEY exactly like Phase 2's pending check.

### Claude's Discretion

- Which candidate wins (per criteria above), manifest naming details, how the load-check is implemented (e.g. `claude -p "/help" --plugin-dir ...` expecting the plugin's commands listed — via stub in CI, documented live procedure).

### Deferred Ideas (OUT OF SCOPE)

- Corpus growth — Phase 5. Charts/publication — Phase 6. Running the full N=5 live matrix — data collection happens when the corpus exists (Phase 5/6 boundary).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|--------------------|
| COMP-01 | Baseline de ao menos um plugin de workflow concorrente rodando headless, com configuração documentada e validada (invocação justa — risco público de arm mal configurado é o maior risco reputacional) | This document DECIDES the competitor (`tzachbon/smart-ralph`'s `ralph-specum`, pinned `v4.0.0`), documents its `defaults_source` (README Quick Start + `quick-mode.md`), specifies the exact manifest and small backward-compatible schema extension needed to provision it, and defines the load-check mechanism (Pattern 2) that satisfies the "validated... risco de arm mal configurado" half of the requirement. Runner-up (`obra/superpowers`) is fully documented as a low-cost fallback/second-arm option. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

`./CLAUDE.md` at the project root contains only the standard Beads issue-tracker integration block (profile: minimal/conservative) plus empty placeholder sections ("Build & Test," "Architecture Overview," "Conventions & Patterns" — none filled in). Extracted actionable directives relevant to this phase:

- Use `bd` for task tracking, not TodoWrite/TaskCreate/markdown TODOs (orchestration concern, not a research-content constraint).
- Conservative git profile: do not commit/push without explicit authority from the active profile or the current user request — relevant to this phase's own `gsd-sdk query commit` step, not to any recommendation made here.
- No project-specific coding conventions, required tools, or security requirements are declared beyond the Beads block — nothing in `CLAUDE.md` constrains or contradicts any recommendation in this document.

## Summary

This research surveyed the four named candidates plus a broader adoption sweep and **DECIDES** the competitor per CONTEXT.md's delegation. Two of the four named candidates are structurally disqualified before headless viability even matters: **github/spec-kit has no Claude Code plugin manifest anywhere in its repository** — it is `specify-cli`, a Python/`uv` project-scaffolding tool that writes command *templates* into a target project's `.claude/commands/`, never installable via `--plugin-dir`. **bmad-code-org/BMAD-METHOD** ships only `.claude-plugin/marketplace.json` (no root `.claude-plugin/plugin.json`, which official docs confirm `--plugin-dir` requires), and every one of its skills hard-depends on a `_bmad/` project scaffold created by a separate `npx bmad-method install` step (Node ≥20.12, Python ≥3.10, `uv`) — a fundamentally different, heavier provisioning model than this repo's git-clone-tag pipeline. "ralph-specum" does not exist as an independently-adopted repo (only a 7-star unrelated reference was found); the real project is `tzachbon/smart-ralph`, which ships a plugin literally named `ralph-specum`.

That leaves two real, structurally-valid, headless-provisionable candidates: **`obra/superpowers`** (261,180 stars — the largest Claude Code plugin found in this entire survey, larger even than spec-kit) and **`tzachbon/smart-ralph`**'s `ralph-specum` plugin (431 stars — modest, but real, active, and MIT-licensed). Both load cleanly via `--plugin-dir`, both have SessionStart/context-injection mechanisms proven to fire under headless `-p` (per official Claude Code docs). They diverge sharply on the **decisive criterion**: superpowers' own README and skill source explicitly, proudly describe an interactive-by-design workflow ("asks you what you're really trying to do... after you've signed off on the design... once you say 'go'") with a hard-coded approval gate and **zero documented non-interactive escape hatch**. `ralph-specum`, by contrast, ships a first-party `--quick` mode — documented in its own README's Quick Start section, not a hidden flag — backed by a **verified, code-level `PreToolUse` hook that programmatically denies the `AskUserQuestion` tool** whenever quick mode is active, forcing the model to "make opinionated decisions autonomously" instead of blocking on a human. This is the only mechanism found across all four candidates purpose-built for exactly the "no human in the loop" scenario this benchmark requires.

**Primary recommendation: `tzachbon/smart-ralph`, plugin `ralph-specum`, pinned to git tag `v4.0.0`, provisioned via a small backward-compatible `staged_path`+subpath extension to the existing manifest schema.** Runner-up: `obra/superpowers` — zero code changes required and vastly larger adoption, but structurally weaker against the decisive headless criterion. Both carry the same open risk, flagged prominently below: this harness's `FAIR-02` design (one literal prompt string, identical across every arm) means neither candidate's non-interactive mode can be *forced* into the prompt without either violating "same prompt across arms" or relying on model judgment to auto-invoke it. This is not a reason to disqualify either candidate — it is a first-order finding for the plan to address explicitly (see Common Pitfalls #1 and Open Questions).

## Architectural Responsibility Map

This phase has no browser/frontend/backend split — it extends a Python CLI benchmarking harness. Tiers are reframed for that context.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Competitor selection + fairness verification | Research (this doc) | — | One-time decision; not re-derived at run time |
| Plugin provisioning (clone pinned tag, optional build) | `stage-plugins.py` (Harness/Staging) | — | Reuses existing idempotent, fail-loud staging mechanics unchanged |
| `--plugin-dir` target resolution (repo root vs. nested subpath) | `bench-run.py` (Harness/Orchestration) | `stage-plugins.py` | New: `ralph-specum`'s manifest lives at `plugins/ralph-specum/`, not repo root — needs a small schema field, not new staging logic |
| Plugin runtime behavior (skills, commands, hooks, AskUserQuestion guard) | Claude Code process (`claude -p`) | Competitor plugin's own hooks/skills | Entirely owned by the competitor's code; harness only provisions and measures |
| Load/visibility verification ("is the arm alive") | New load-check step (Harness/Orchestration) | Phase SUMMARY (audit trail) | Must be a distinct, cheap check independent of full task-completion risk |
| Task-completion measurement | `bench-run.py` + `verify.sh` (existing, unchanged) | `bench-aggregate.py` | Success-gating already built (Phase 3); this phase adds a new baseline row, no new measurement logic |

## Standard Stack

### Core

No new external packages are installed by this phase. The winning candidate needs no build step at all.

| Dependency | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tzachbon/smart-ralph` (git) | tag `v4.0.0` [VERIFIED: git ls-remote] | Competitor plugin source (`ralph-specum`) | Only real, structurally-valid, headless-capable candidate with a purpose-built non-interactive mode; verified live |
| `jq` | any recent (1.6+) | Runtime dependency of `ralph-specum`'s hook scripts (`quick-mode-guard.sh`, `stop-watcher.sh`, `load-spec-context.sh`) | Already present in this dev environment (`jq-1.8.1`); hooks `exit 0` gracefully if `jq` is absent, so missing `jq` degrades to "guard silently no-ops," not a hard failure — still worth confirming present wherever live runs execute |

### Supporting (runner-up, documented for completeness / future consideration)

| Dependency | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `obra/superpowers` (git) | tag `v6.2.0` [VERIFIED: git ls-remote via `gh api repos/obra/superpowers/tags`] | Alternative competitor plugin (skills-only, no commands) | If the plan decides adoption/simplicity outweighs the headless-safety-mechanism gap, or as a **second** competitor baseline in a later phase (COMP-01 only requires "at least one") |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ralph-specum`'s nested-plugin-dir schema extension | Sparse-checkout the subtree only, so `staged_path` IS `plugins/ralph-specum` directly | Avoids touching `bench-run.py`, but `git clone --branch --depth 1` (current `stage-plugins.py` mechanism) does not do sparse checkouts; would require a second, divergent staging code path — more invasive than a one-field schema addition |
| `ralph-specum` pinned to `v4.0.0` | Pin to `main`@`b26bb23` (current HEAD, where `plugin.json` self-reports version `4.10.1`) | `stage-plugins.py` clones via `git clone --branch <ref> --depth 1`, which resolves tags and branches, not arbitrary commit SHAs under `--depth 1` in this exact form; `main` also isn't a stable, re-fetchable pin (drifts every time the upstream repo advances) — `v4.0.0` is the only real, immutable, clonable ref, at the cost of being ~5 months / 9+ commits stale |
| `obra/superpowers` as sole competitor | Both `ralph-specum` and `superpowers` as two `competitor-*.json` manifests | CONTEXT.md and COMP-01 only require one competitor arm for this phase; running two doubles staging/verification/live-cost surface for no requirement gain — defer a second competitor to "Add After Validation" per FEATURES.md's own MVP scoping |

**Installation:**
```bash
# No package-manager install needed for the plugin itself (no package.json in
# ralph-specum). Staging is purely: pinned git clone, zero build commands —
# even simpler than GSD (npm ci) or context-mode (npm install).
python3 benchmarks/scripts/stage-plugins.py \
  --baseline benchmarks/baselines/competitor-ralph-specum.json
```

**Version verification (performed live this session):**
```bash
git ls-remote --tags https://github.com/tzachbon/smart-ralph.git
# 84f6cb1... refs/tags/v2.0.0
# 56dbd46... refs/tags/v3.1.1  (+ ^{} deref)
# 5012c8f... refs/tags/v4.0.0  (+ ^{} deref)   <- last real tag, 2026-02-20
# (no tag newer than v4.0.0; plugin.json at HEAD self-reports "4.10.1" untagged)

git ls-remote --tags https://github.com/obra/superpowers.git | tail -3
# v6.2.0 present and current as of 2026-07-24 (matches HEAD)
```

## Package Legitimacy Audit

> Adapted for this phase: neither candidate is an npm/PyPI/crates registry package — both are git-cloned Claude Code plugin repositories, staged by `stage-plugins.py`'s existing `git clone --branch <ref> --depth 1` mechanism (identical to how GSD and context-mode are already staged). `slopcheck` targets package registries and does not apply here; the equivalent diligence performed is documented per-row below (repo age, activity, stars, license, maintainer signal, absence of suspicious install/build scripts).

| Plugin | Registry | Repo Age / Last Push | Stars | Source Repo | Build/postinstall scripts | Verdict | Disposition |
|--------|----------|-----------------------|-------|--------------|---------------------------|---------|-------------|
| `ralph-specum` (in `tzachbon/smart-ralph`) | git (GitHub) | Active; pushed 2026-07-23 [VERIFIED: `gh api repos/tzachbon/smart-ralph`] | 431 [VERIFIED: GitHub API] | `github.com/tzachbon/smart-ralph`, MIT `LICENSE` present at `v4.0.0` [VERIFIED] | None — no `package.json` anywhere in the repo at `v4.0.0`; hooks are plain bash + `jq`, no `postinstall` | Legitimate, real, actively maintained; adoption is modest but the repo is coherent, documented, and self-consistent (README examples match actual command/skill source) | Approved |
| `superpowers` (`obra/superpowers`) | git (GitHub) | Active; pushed 2026-07-24, weekly release cadence back to at least `v5.0.5` [VERIFIED: `gh api .../tags`] | 261,180 [VERIFIED: GitHub API — larger than `github/spec-kit`'s 123,823] | `github.com/obra/superpowers`, MIT `LICENSE`, `plugin.json` declares `"license": "MIT"` [VERIFIED] | None — no MCP server (`mcpServers` key absent from `plugin.json`), no `dependencies`/`devDependencies` in `package.json` (only a `pi`-platform extension field, irrelevant to Claude Code) | Legitimate, very large real-world adoption, clean structure, no suspicious scripts | Approved |
| `github/spec-kit` | N/A (not a Claude Code plugin) | Active; 123,823 stars, MIT | — | No `.claude-plugin/` anywhere in repo (confirmed via `gh api repos/github/spec-kit/contents/` and a repo-scoped `filename:plugin.json` code search returning zero results) | N/A | Legitimate project, wrong category — a `specify-cli` project-scaffolding tool, not a plugin | REMOVED (structural disqualification, not a legitimacy concern) |
| `bmad-code-org/BMAD-METHOD` | N/A (not `--plugin-dir`-loadable) | Active; 51,121 stars | — | `.claude-plugin/marketplace.json` present but no root `.claude-plugin/plugin.json`; official docs confirm `--plugin-dir` requires the latter | Every skill depends on `_bmad/bmm/config.yaml` from a separate `npx bmad-method install` (Node ≥20.12, Python ≥3.10, `uv`) | Legitimate, well-adopted project, wrong provisioning shape for this harness | REMOVED (structural disqualification, not a legitimacy concern) |

**Packages removed due to structural disqualification:** `github/spec-kit`, `bmad-code-org/BMAD-METHOD` — neither is a `[SLOP]` verdict; both are legitimate, well-adopted projects that simply do not fit the `--plugin-dir` provisioning contract this harness requires. See Common Pitfalls #2 for the mechanism that would falsely "prove" BMAD provisioned successfully if this distinction were missed.
**Packages flagged as suspicious:** none.

## Architecture Patterns

### System Architecture Diagram

```
task.json + prompt.md (IDENTICAL across every arm — FAIR-02, locked)
        |
        v
  bench-run.py --baseline competitor-ralph-specum.json
        |
        |-- load_baseline(): validates name/model/claude_flags/provisioning
        |                      + NEW: resolves --plugin-dir target as
        |                        staged_path (+ optional subpath, see
        |                        Code Examples)
        |
        v
  fresh disposable HOME + workdir (copytree of fixture/)
        |
        v
  claude -p "<prompt_text>" --plugin-dir <staged>/plugins/ralph-specum \
           --model <pinned> --max-turns 8 --permission-mode acceptEdits \
           --bare --no-session-persistence --output-format json
        |
        |-- SessionStart hook (load-spec-context.sh) fires -- proven to
        |     fire under -p per official docs -- injects spec-state context
        |     (no-op on a fresh workdir with no ./specs/)
        |
        |-- model reads system context incl. `spec-workflow` skill
        |     description ("build a feature", "implement spec", ...) and
        |     MAY auto-invoke /ralph-specum:start (command has no
        |     disable-model-invocation:true, so Claude CAN auto-trigger it
        |     per official docs) -- but whether it also supplies --quick is
        |     model judgment, NOT harness-controlled (see Pitfall #1)
        |
        |-- IF --quick path is taken: PreToolUse hook (quick-mode-guard.sh)
        |     denies any AskUserQuestion call, forcing autonomous decisions;
        |     Stop hook (stop-watcher.sh) continues execution until
        |     ALL_TASKS_COMPLETE
        |-- IF plain/no-quick path is taken: Goal Interview / brainstorming-
        |     style dialogue, explicit STOP-and-wait -- same interactive risk
        |     profile as superpowers' brainstorming HARD-GATE
        |
        v
  subprocess.run(..., timeout=task_s)  <- existing backstop, unchanged;
        |                                  protects against ANY hang,
        |                                  including a theoretical
        |                                  AskUserQuestion block outside
        |                                  quick mode (askUserQuestionTimeout
        |                                  defaults to "never" in a fresh,
        |                                  unconfigured HOME)
        v
  verify.sh <workdir>  (external, agent-unwritable pass/fail — unchanged)
        |
        v
  JSONL row: task_id, baseline_id="competitor-ralph-specum", usage,
             total_cost_usd, verify_passed, is_error, ...
```

### Recommended Project Structure
```
benchmarks/
├── baselines/
│   └── competitor-ralph-specum.json   # NEW manifest (this phase)
├── plugins/
│   └── ralph-specum/
│       └── v4.0.0/                    # full smart-ralph repo clone;
│                                        # --plugin-dir target is the
│                                        # plugins/ralph-specum/ subpath
│                                        # inside it, not the clone root
└── scripts/
    ├── stage-plugins.py                # UNCHANGED — already handles empty
    │                                    # build[] and mcpServers-less plugins
    └── bench-run.py                    # SMALL, backward-compatible change:
                                         # resolve an optional per-entry
                                         # subpath when building --plugin-dir
```

### Pattern 1: Nested-plugin `--plugin-dir` resolution (new)
**What:** `ralph-specum`'s `.claude-plugin/plugin.json` lives at `plugins/ralph-specum/` inside the `smart-ralph` repo, not at the repo root (unlike GSD, context-mode, cairn, and superpowers, which all have it at root). The vendor's own README documents the exact local-dev invocation: `claude --plugin-dir ./smart-ralph/plugins/ralph-specum`.
**When to use:** Any competitor/dependency whose marketplace bundles multiple plugins from one repo via distinct subdirectories (as opposed to BMAD's pattern of one shared root with no per-plugin manifest, which is NOT provisionable this way at all).
**Example (schema addition, backward-compatible):**
```json
// Source: official docs (code.claude.com/docs/en/plugins) confirm --plugin-dir
// targets a directory containing .claude-plugin/plugin.json; the vendor's own
// README (github.com/tzachbon/smart-ralph, v4.0.0) documents the exact subpath.
{
  "plugin": "ralph-specum",
  "source": { "type": "git", "repo": "tzachbon/smart-ralph", "ref": "v4.0.0" },
  "staged_path": "benchmarks/plugins/ralph-specum/v4.0.0",
  "plugin_dir_subpath": "plugins/ralph-specum",
  "build": []
}
```
```python
# bench-run.py — the ONLY two spots that need to change, both additive:
# 1) load_baseline()'s existing per-entry existence check:
for entry in manifest["provisioning"]["plugin_dirs"]:
    target = Path(entry["staged_path"]) / entry.get("plugin_dir_subpath", "")
    if not target.is_dir():
        die(f"plugin '{entry['plugin']}' --plugin-dir target not found: "
            f"{target} (stage and build it before running)", EXIT_USAGE)

# 2) the --plugin-dir flag construction in main():
for entry in manifest["provisioning"]["plugin_dirs"]:
    target = Path(entry["staged_path"]) / entry.get("plugin_dir_subpath", "")
    cmd += ["--plugin-dir", str(target)]
```
`Path("/a/b") / ""` is a documented no-op in `pathlib` (returns `/a/b` unchanged), so every existing manifest (`vanilla`, `gsd-only`, `cairn`) — none of which set `plugin_dir_subpath` — is unaffected. `stage-plugins.py` itself needs **zero changes**: it stages the full repo at `staged_path` regardless of where inside it the eventual `--plugin-dir` target sits.

### Pattern 2: Load-check without provoking task-completion risk
**What:** CONTEXT.md's own suggested mechanism (`claude -p "/help" --plugin-dir ...`) is the right shape, but must target the correct namespace strings and stay a single cheap call, independent of whether any task run actually completes.
**When to use:** The phase's required re-verification checkpoint ("does the plugin actually LOAD and its commands are visible").
**Stub version ($0, CI):** extend the existing `CAIRN_BENCH_CLAUDE_BIN`-stub pattern (identical to `tests/bench-matrix.bats`'s env-observing stub) to assert the constructed `argv` contains `--plugin-dir <staged>/plugins/ralph-specum` — proves the harness *wires up* provisioning correctly without any live call.
**Documented live version:**
```bash
# Source: CONTEXT.md's own suggested mechanism, refined with verified
# namespace strings from this session's live source inspection.
claude -p "/help" \
  --plugin-dir benchmarks/plugins/ralph-specum/v4.0.0/plugins/ralph-specum \
  --model claude-haiku-4-5-20251001 --bare --no-session-persistence \
  --permission-mode acceptEdits --output-format json \
  | grep -o 'ralph-specum:[a-z-]*' | sort -u
# Expected (non-exhaustive): ralph-specum:start, ralph-specum:new,
# ralph-specum:research, ralph-specum:requirements, ralph-specum:design,
# ralph-specum:tasks, ralph-specum:implement, ralph-specum:status,
# ralph-specum:help
```
This is a single short call (no task fixture, no file edits, no exploration — `/help` resolves from static command metadata), so it is cheap even against the live API, and — per CONTEXT.md's own "Specific Ideas" note — its captured output is the audit-trail artifact that belongs in the phase SUMMARY.

### Anti-Patterns to Avoid
- **Hard-coding `/ralph-specum:start ... --quick` into the shared `prompt.md`:** would violate FAIR-02 ("mesmo prompt de tarefa" — same task prompt across every arm, already locked and shipped in Phase 2). The competitor must earn its own invocation the same way GSD/cairn already do — from a plain natural-language task description — or the run honestly records that it didn't trigger. Do not special-case the prompt per arm.
- **Tuning `askUserQuestionTimeout` to force completion:** this repo's `bench-run.py` already has a hard per-run `subprocess.run(timeout=task_s)` backstop (proven, unchanged by this phase). Reaching for a `--settings` override to make the competitor "finish" would be exactly the "tuning it down / tuning it up" fairness violation CONTEXT.md forbids. If a live run times out because the model got stuck on a blocked/never-answered dialogue, that is a legitimate, accurately-labeled `is_error`/timeout row — report it, don't engineer around it.
- **Treating "plugin loads" and "task completes" as the same verification:** they are architecturally distinct (see Architectural Responsibility Map). Conflating them either over-trusts a broken arm (loads fine, never actually attempts the task) or under-trusts a working one (task fails for a legitimate, honestly-measured reason unrelated to provisioning).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Verifying a plugin repo isn't malicious/hallucinated | A custom trust-scoring script | The diligence already performed in this research (stars, license, tag history via `gh api`/`git ls-remote`, absence of postinstall scripts) — re-run only the specific `gh api`/`git ls-remote` commands shown above before publish, per Pitfall 5's re-verification-checkpoint guidance | `slopcheck` doesn't cover git-cloned plugins; hand-rolling a scorer for a one-time decision is overkill — the manual checks are already fast, cheap, and reproducible |
| Nested `--plugin-dir` resolution | A new staging code path (e.g., sparse checkout, symlink farm) | The one-field `plugin_dir_subpath` schema addition (Pattern 1) | Every other structural option (sparse checkout, sub-clone, symlink) adds a second, divergent code path to `stage-plugins.py` for a problem a single `Path` join already solves |
| Detecting whether the competitor actually engaged with the task | A custom transcript-parsing heuristic | `verify.sh`'s existing external, agent-unwritable pass/fail (already built, Phase 1) plus the raw `usage`/`num_turns`/`is_error` fields already captured per row (Phase 1-3) | The harness already answers "did it work" cleanly; a bespoke "did it try" heuristic on top would be exactly the kind of self-graded, gameable signal Pitfall 6 (research/PITFALLS.md) warns against |

**Key insight:** every piece of new mechanism this phase needs (nested-plugin resolution, load-check, staleness disclosure) is a small, additive extension of infrastructure Phase 1-3 already built and proved at $0. Nothing here calls for new invention.

## Common Pitfalls

### Pitfall 1: The shared-prompt constraint can silently neuter either candidate's non-interactive mode
**What goes wrong:** FAIR-02 locks one literal prompt string across every arm. Neither `ralph-specum`'s `--quick` flag nor a workaround for superpowers' brainstorming gate can be forced into that shared string without either violating "same prompt across arms" or depending entirely on the model's own judgment to auto-invoke the plugin's entry point *with* the right flag. If the model auto-invokes `/ralph-specum:start <name> <goal>` **without** `--quick` (a live possibility — the flag is optional and nothing in a generic task prompt like "Implement `celsius_to_fahrenheit(c)`..." says "quick" or "non-interactive"), the run falls into the exact same interactive Goal-Interview/STOP-and-wait pattern that afflicts superpowers, and the `AskUserQuestion`-denial guard never activates (it only reads `quickMode` from `.ralph-state.json`, which is only set `true` via the `--quick` code path).
**Why it happens:** Slash commands and skills in Claude Code plugins are model-auto-invoked based on the model's own judgment of task fit (confirmed via official docs: commands without `disable-model-invocation:true` — `ralph-specum:start` has none — can be auto-triggered), not by a harness-controlled dispatch table.
**How to avoid:** Do not attempt to guarantee `--quick` from the harness side. Instead: (1) run the load-check (Pattern 2) to confirm the plugin is *visible*, independent of task-triggering; (2) when the live smoke run becomes possible (ANTHROPIC_API_KEY), capture and honestly report whatever triggering behavior is observed — including "the competitor never engaged its own workflow at all" as a legitimate, informative result; (3) flag this explicitly in `BENCHMARKS.md`'s methodology/limitations section (already an REPT-01 requirement) rather than silently normalizing it away.
**Warning signs:** A live competitor row shows `num_turns` far below the vanilla arm's with `verify_passed: false` and no corresponding `.ralph-state.json`/spec artifacts in the captured transcript — evidence the plugin never engaged at all, not evidence it "lost fairly."
**Phase to address:** This phase's plan should explicitly decide how to report/handle this (not silently accept whichever outcome occurs); Phase 5/6 (corpus growth, report) inherit whatever decision is made here.

### Pitfall 2: A structurally-invalid `--plugin-dir` target can appear to "work" without actually loading anything
**What goes wrong:** `claude --plugin-dir <dir-with-no-plugin.json>` does not necessarily hard-crash the whole CLI process — it can start a session with that directory's plugin simply absent/unregistered, silently degrading to "vanilla with dead weight" (Pitfall 5 in `.planning/research/PITFALLS.md` — the exact failure this phase exists to prevent). This is precisely the trap `bmad-code-org/BMAD-METHOD`'s repo root (`.claude-plugin/marketplace.json` only, no `plugin.json`) would spring if someone pointed `--plugin-dir` at it directly, assuming the presence of *some* `.claude-plugin/` file was sufficient.
**Why it happens:** `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json` look similar at a glance (both JSON manifests under the same hidden directory name) but serve entirely different provisioning paths (marketplace registration+install vs. direct dev-mode dir loading).
**How to avoid:** The load-check (Pattern 2) is not optional polish — it is the only thing that distinguishes "loaded and its commands are visible in `/help`" from "process started, nothing registered." Always confirm the specific `plugin-name:command` strings appear in `/help` output for the exact `--plugin-dir` path used, not just that the `claude` process exited 0.
**Warning signs:** `/help` output contains zero occurrences of the plugin's namespace prefix even though the process exited cleanly.
**Phase to address:** Baseline isolation / this phase's re-verification checkpoint.

### Pitfall 3: Assuming a repo's newest `plugin.json`-declared version is git-tagged
**What goes wrong:** `ralph-specum`'s `plugin.json` at `main` HEAD self-reports `"version": "4.10.1"`, but `git ls-remote --tags` shows the newest real tag is `v4.0.0` (2026-02-20) — a ~5-month, 9+-commit gap with no corresponding tag. Pinning to a string that isn't a real, clonable git ref (e.g., trusting the marketplace-declared version number as if it were a tag name) would make `stage-plugins.py`'s `git clone --branch 4.10.1 --depth 1` fail loudly at staging time — which is the safe failure mode, but wastes a staging attempt and could be mistaken for a broader provisioning bug if not anticipated.
**Why it happens:** Not every plugin author tags every version bump; marketplace.json/plugin.json version fields are updated far more casually than release tags.
**How to avoid:** Always resolve the pin via `git ls-remote --tags` (or `gh api .../tags`) directly against the actual repo, never by reading the version field out of a JSON manifest and assuming it maps to a tag of the same name.
**Warning signs:** `gh api repos/<owner>/<repo>/tags` returns fewer/older entries than the `version` field visible in the repo's current default-branch content.
**Phase to address:** Staging/pinning step of this phase; document the staleness explicitly in the manifest's description field (mirroring `gsd-only.json`'s own existing precedent of noting "verified live" + date).

## Code Examples

### Full competitor manifest (verified schema-compatible with existing `load_baseline()`/`stage_entry()`)
```json
// Source: this session's live verification (gh api, git ls-remote, official
// docs at code.claude.com/docs/en/plugins) — see Sources below for each claim.
{
  "name": "competitor-ralph-specum",
  "description": "tzachbon/smart-ralph's ralph-specum plugin: spec-driven, task-by-task autonomous execution. Chosen over github/spec-kit (no Claude Code plugin manifest anywhere in repo -- a specify-cli project scaffolder, not --plugin-dir-provisionable), bmad-code-org/BMAD-METHOD (no root .claude-plugin/plugin.json -- only marketplace.json -- and every skill requires a separate `npx bmad-method install` scaffold incompatible with this harness's provisioning model), and obra/superpowers (261k stars vs. 431 -- vastly larger adoption, but its documented default workflow has a hard design-approval gate with zero non-interactive escape hatch, unlike ralph-specum's --quick mode). Pinned to v4.0.0 (verified live via `git ls-remote --tags` 2026-07-26 -- the newest real git tag; plugin.json at HEAD self-reports 4.10.1, untagged -- disclosed staleness, not a provisioning error). --plugin-dir target is the plugins/ralph-specum/ subpath inside the cloned repo, per the vendor's own documented local-dev instructions (README.md, v4.0.0, 'Installation' section).",
  "model": "claude-haiku-4-5-20251001",
  "defaults_source": "https://github.com/tzachbon/smart-ralph/blob/v4.0.0/README.md#quick-start (documents /ralph-specum:start ... and the --quick mode as the two first-party default entry points) and https://github.com/tzachbon/smart-ralph/blob/v4.0.0/plugins/ralph-specum/references/quick-mode.md (full non-interactive execution contract, including the explicit 'non-interactive -- do not block or prompt user' directive)",
  "claude_flags": {
    "bare": true,
    "max_turns": 8,
    "no_session_persistence": true,
    "permission_mode": "acceptEdits"
  },
  "provisioning": {
    "plugin_dirs": [
      {
        "plugin": "ralph-specum",
        "source": { "type": "git", "repo": "tzachbon/smart-ralph", "ref": "v4.0.0" },
        "staged_path": "benchmarks/plugins/ralph-specum/v4.0.0",
        "plugin_dir_subpath": "plugins/ralph-specum",
        "build": []
      }
    ]
  }
}
```
Note: `claude_flags` is byte-identical to `vanilla.json`/`gsd-only.json`/`cairn.json` (FAIR-02) — only `provisioning` differs, exactly as the existing three manifests already establish.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Assume "biggest GitHub stars = best competitor" | Weight structural `--plugin-dir` compatibility and a purpose-built non-interactive mode above raw adoption when the phase's own decisive criterion is headless viability | This research, 2026-07-26 | `superpowers` (261k stars) is demoted to runner-up behind `ralph-specum` (431 stars) specifically because only the latter has a code-verified mechanism (the `AskUserQuestion`-denying `PreToolUse` hook) matching the phase's stated decisive criterion |
| Trust a marketplace.json's presence as proof of `--plugin-dir` loadability | Require a root `.claude-plugin/plugin.json` specifically, per official docs | Verified this session against `code.claude.com/docs/en/plugins` | Directly disqualifies BMAD's repo-root as a `--plugin-dir` target, and is the exact mechanism Pitfall 2 above warns against |

**Deprecated/outdated:**
- Nothing plugin-ecosystem-wide is deprecated here; this is a first-time competitor selection for this project, not a migration.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | Given a plain natural-language task prompt (no literal slash syntax), Claude will sometimes — but not reliably — auto-invoke `/ralph-specum:start` with the `--quick` flag specifically (as opposed to without it, or not invoking the plugin's commands at all) | Common Pitfalls #1, Architecture Patterns diagram | If the model reliably omits `--quick` (or never engages the plugin at all) across the actual task corpus, the "purpose-built non-interactive mode" advantage over superpowers evaporates in practice even though it exists on paper — the plan should verify this empirically via the live smoke run before treating it as settled |
| A2 | `askUserQuestionTimeout` defaults to `"never"` in a fresh, unconfigured `HOME` (no user/managed settings present) — read from official docs, not observed live in this harness's isolated env | Architecture Patterns diagram, Anti-Patterns | If some other default/managed-settings layer overrides this in the actual isolated `HOME`, the existing 120s process-level timeout backstop still fully protects the harness either way — low risk even if this specific claim is imprecise |
| A3 | The `spec-workflow` skill's presence (no `user-invocable: false`, description matching "build a feature"/"implement spec") is sufficient for Claude to discover and consider invoking `ralph-specum:start`, mirroring how `disable-model-invocation` (absent) permits command auto-invocation — both mechanisms confirmed independently via official docs and live source inspection, but never jointly observed in an actual live call this session | Architecture Patterns, Pattern 1 | If wrong, the plugin might never be discoverable from a plain prompt at all (not just risk of missing `--quick`) — same mitigation as A1: the live smoke run is the actual proof, this research establishes plausibility with strong but indirect evidence |

## Open Questions

1. **Will `ralph-specum` (or superpowers) ever meaningfully engage with the existing, deliberately tiny `smoke-convert` fixture ("implement one function so tests pass")?**
   - What we know: both plugins' entry points are explicitly designed for "build a feature"-scale work; `brainstorming`'s own anti-pattern section explicitly rejects "too simple to need a design" as a rationalization, suggesting superpowers WILL still try to engage even trivial tasks — no equivalent explicit statement exists for `ralph-specum`.
   - What's unclear: whether a one-function task is large enough for the model to judge `spec-workflow`/`start` relevant at all, versus just fixing the file directly and never touching either plugin's mechanism.
   - Recommendation: treat this as an empirical question for the live smoke run (Phase 4's own re-verification checkpoint), and consider whether Phase 5's corpus (out of this phase's scope per CONTEXT.md's Deferred Ideas) should include at least one task explicitly feature-shaped enough to plausibly trigger a spec-driven workflow, so the competitor arm isn't structurally starved of a fair chance to show its intended behavior.

2. **Should a second competitor arm (`competitor-superpowers.json`) be added now or deferred?**
   - What we know: COMP-01 requires only "at least one" competitor; `provisioning.plugin_dirs` schema and `stage-plugins.py` already handle superpowers with zero code changes (root-level `plugin.json`, no build step).
   - What's unclear: whether the phase's remaining budget/scope favors shipping both now (maximizing data even before Phase 5's corpus exists) vs. keeping this phase minimal and adding superpowers as a fast follow once the harness proves out on one competitor.
   - Recommendation: ship `ralph-specum` only for this phase (matches COMP-01's literal requirement and CONTEXT.md's "pick the strongest candidate" framing); leave `superpowers` staged-ready in this research as a documented, low-cost next step.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `git` | Staging (`stage-plugins.py`, unchanged) | ✓ | 2.42.1 | — |
| `node` / `npm` | Not required by the winning candidate (no build step) | ✓ | v24.13.1 / 11.8.0 | N/A — `ralph-specum` needs neither |
| `jq` | Runtime dependency of `ralph-specum`'s hooks (`quick-mode-guard.sh` et al.) | ✓ | jq-1.8.1 | Hooks `exit 0` gracefully (no-op) if `jq` is missing — degrades to "guard silently absent," not a crash; still worth confirming present in whatever environment executes live runs |
| `python3` | Harness scripts (unchanged) | ✓ | 3.12.1 | — |
| `bats` | `$0` test suite (unchanged) | ✓ | 1.14.0 | — |
| `claude` CLI | All live runs | ✓ (on PATH) | not queried this session | — |
| `ANTHROPIC_API_KEY` | Live smoke run / live load-check | ✗ (absent, re-checked live 2026-07-26) | — | Same PENDING pattern already established and documented in Phase 2/3 (`benchmarks/README.md`'s "Live isolation smoke check: PENDING" section) — the $0 stub-based mechanism (Pattern 2's stub version) proves the wiring without it; the live load-check and live smoke run remain blocked until a key is available |

**Missing dependencies with no fallback:**
- None — `ANTHROPIC_API_KEY` absence blocks only the live-verification artifacts, not the $0-provable mechanism (staging, schema extension, stub-based load-check), exactly mirroring the precedent already accepted for Phase 2/3.

**Missing dependencies with fallback:**
- `jq` (if ever absent in a future execution environment) degrades gracefully per the hook script's own `command -v jq >/dev/null 2>&1 || exit 0` guard — confirmed by direct source inspection at `v4.0.0`.

## Security Domain

> `security_enforcement` config key not found in `.planning/config.json` — treated as enabled per instructions. This phase's "security" surface is narrow: staging an additional untrusted third-party code source and running it with edit permissions in an isolated environment.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | No new auth surface — reuses the existing `--bare` + `ANTHROPIC_API_KEY`-in-scoped-env pattern, unchanged |
| V4 Access Control | yes | Reuses `--permission-mode acceptEdits` (already gates Bash execution, per `benchmarks/README.md`'s "Observed behavior" — `permission_denials` recorded for arbitrary command attempts even under `acceptEdits`), unchanged by this phase |
| V5 Input Validation | yes | `bench-run.py`'s existing `load_baseline()` fail-loud validation, extended (Pattern 1) to also validate the new `plugin_dir_subpath`-resolved target exists before any spend — same "validate before spend" contract as every other check in this file |
| V6 Cryptography | no | Not applicable |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Untrusted third-party plugin code executes with the operator's real `PATH` inside an isolated-but-not-network-isolated `HOME` | Elevation of Privilege / Tampering | Already mitigated by the existing isolated-`HOME` + `--permission-mode acceptEdits` design (Phase 2, unchanged); this phase adds no new trust boundary beyond "one more pinned git tag, reviewed the same way GSD/context-mode already were" |
| A staged plugin's hook scripts run arbitrary shell (`quick-mode-guard.sh`, `stop-watcher.sh`, `load-spec-context.sh`) | Tampering | Same threat class already accepted for GSD's/context-mode's own hook/MCP-server code (Phase 2's threat model, T-02-06/T-02-07); mitigated by pinning to a reviewed tag + `.staged-ref` idempotency, not by sandboxing the hooks themselves (out of scope, matches existing precedent) |
| Stale pin (`v4.0.0` vs. untagged `4.10.1` HEAD) silently drifts out of sync with the vendor's actual current behavior | Tampering (of the comparison's validity, not the code) | Disclosed explicitly in the manifest's `description` field (already modeled in the Code Examples manifest above); re-verify against `git ls-remote --tags` before each publish cycle, per Pitfall 5 in `.planning/research/PITFALLS.md` |

## Sources

### Primary (HIGH confidence)
- `gh api repos/{github/spec-kit,bmad-code-org/BMAD-METHOD,obra/superpowers,tzachbon/smart-ralph}` — repo metadata, stars, license, tags, releases, directory contents (live, this session, 2026-07-26)
- `git ls-remote --tags https://github.com/tzachbon/smart-ralph.git` and `.../obra/superpowers.git` — authoritative tag verification (live, this session)
- `gh api repos/.../contents/<path>?ref=<tag>` — pinned-tag content verification for `plugin.json`, `hooks.json`, `quick-mode-guard.sh`, `start.md`, `LICENSE`, `agents/` at the exact `v4.0.0` ref actually being pinned (not just HEAD) — this session
- https://code.claude.com/docs/en/plugins — official confirmation that `--plugin-dir` requires `.claude-plugin/plugin.json` at the target directory (fetched live this session)
- https://code.claude.com/docs/en/hooks — official confirmation that `SessionStart` fires under headless `-p` and `additionalContext` is injected identically to interactive mode (fetched live this session)
- https://code.claude.com/docs/en/settings — official `askUserQuestionTimeout` documentation (default `"never"`, user/managed-settings scope only) (fetched live this session)
- https://raw.githubusercontent.com/tzachbon/smart-ralph/v4.0.0/README.md and .../obra/superpowers/v6.2.0/README.md — vendor-authored quickstart/default-workflow descriptions, fetched at the actual pinned tags (this session)

### Secondary (MEDIUM confidence)
- WebSearch results on Claude Code slash-command auto-invocation (`disable-model-invocation`, `user-invocable`) — cross-verified against the actual observed frontmatter of `ralph-specum:start` (no `disable-model-invocation: true` present) and superpowers' skills

### Tertiary (LOW confidence)
- None material to the final recommendation; all load-bearing claims were cross-checked against a primary source above.

## Metadata

**Confidence breakdown:**
- Standard stack (which repo/tag to pin): HIGH — every structural claim (plugin.json location, license, tag existence) verified live via `gh api`/`git ls-remote` at the actual pinned ref, not assumed from training data
- Architecture (provisioning mechanics, schema extension): HIGH — cross-checked against this repo's actual `stage-plugins.py`/`bench-run.py` source, not just general Claude Code plugin docs
- Pitfalls (prompt-trigger reliability, `AskUserQuestion` behavior under `-p`): MEDIUM — the mechanism (guard hook, timeout default) is code/docs-verified, but the actual triggering *rate* against this harness's real task prompts is unobserved (no ANTHROPIC_API_KEY this session) and explicitly flagged as an assumption (A1, A3) for the plan/live-verification step to resolve

**Research date:** 2026-07-26
**Valid until:** ~30 days for the structural/licensing findings (stable); re-verify the `git ls-remote --tags` pin immediately before any live publish cycle regardless of elapsed time, per Pitfall 5's re-verification-checkpoint requirement (fast-moving: both candidate repos push multiple times per month)
