---
phase: 04-competitor-baseline
plan: "01"
subsystem: benchmarks
tags: [python, bats, competitor, fair-02, comp-01, provisioning]
requires:
  - "benchmarks/scripts/stage-plugins.py (02-02: git+tag staging, no changes needed)"
  - "benchmarks/scripts/bench-run.py (02-01/02-03: load_baseline + --plugin-dir argv construction)"
  - "benchmarks/baselines/cairn.json (the byte-identical claude_flags/model reference)"
  - "tests/helpers.bash make_env_asserting_claude_stub (unchanged, reused)"
provides:
  - "benchmarks/baselines/competitor-ralph-specum.json — 4th arm, pinned tzachbon/smart-ralph@v4.0.0, defaults_source audit trail, plugin_dir_subpath: plugins/ralph-specum"
  - "bench-run.py nested --plugin-dir resolution: Path(staged_path) / entry.get('plugin_dir_subpath', '') at both call sites, backward-compatible no-op for manifests omitting the key"
  - "benchmarks/plugins/ralph-specum/v4.0.0 staged for real (nested .claude-plugin/plugin.json confirmed at declared path; gitignored)"
  - "3 new bats tests: subpath argv resolution, missing-target fail-loud pre-spend, FAIR-02 mechanical jq -S proof"
affects:
  - "04-02+ (competitor arm now provisionable through the identical isolated pipeline)"
  - "Phase 5/6 live matrix (4th baseline name: competitor-ralph-specum)"
tech-stack:
  added: []
  patterns:
    - "plugin_dir_subpath: optional manifest key joined onto staged_path; Path(x) / '' pathlib no-op keeps every existing manifest byte-identical in behavior"
    - "fairness proven mechanically: jq -S '{model, claude_flags}' diff against cairn.json inside the $0 suite, not by inspection"
key-files:
  created:
    - benchmarks/baselines/competitor-ralph-specum.json
  modified:
    - benchmarks/scripts/bench-run.py
    - tests/bench-run.bats
    - benchmarks/README.md
key-decisions:
  - "die message reworded to name the JOINED target while keeping the literal word staged_path (pre-existing grep contract in the unstaged-plugin bats test)"
  - "stage-plugins.py untouched by design: it stages the full repo at staged_path; subpath resolution is exclusively the runner's concern"
  - "live load-check recorded as PENDING (ANTHROPIC_API_KEY absent, re-checked 2026-07-26) with the exact reproduction command — never silently skipped"
duration: 6min
completed: 2026-07-26
---

# Phase 4 Plan 01: Competitor Baseline (ralph-specum) Summary

**Fourth benchmark arm `competitor-ralph-specum` pinned to the live-reconfirmed tag tzachbon/smart-ralph@v4.0.0 with a `defaults_source` audit trail and FAIR-02 byte-identical `claude_flags`/`model` (proven mechanically by `jq -S` diff in bats), plus backward-compatible `plugin_dir_subpath` resolution in bench-run.py so `--plugin-dir` targets the nested `plugins/ralph-specum/` plugin.json — real repo staged and structurally confirmed, 32/32 bats at $0, live load-check explicitly PENDING.**

## Accomplishments

- **Task 1** (`a3fccbf`): `git ls-remote --tags https://github.com/tzachbon/smart-ralph.git` re-run live — tags v2.0.0, v3.1.1, v4.0.0; **v4.0.0 confirmed newest** (annotated `5012c8f` → commit `d6fba6a`), matching 04-RESEARCH's same-day finding. Manifest written verbatim from the plan's Interfaces block (full description + defaults_source unabridged). Real staging executed: `stage-plugins.py --baseline benchmarks/baselines/competitor-ralph-specum.json` cloned the pinned tag (`Note: switching to 'd6fba6a...'`), zero build commands, atomic rename → `[stage-plugins] ralph-specum staged at v4.0.0 -> benchmarks/plugins/ralph-specum/v4.0.0`.
- **Task 2 RED** (`84ef582`): 3 new bats tests appended in house style. Genuine RED observed: subpath test failed exactly on the bare-vs-joined argv assertion (`returned '.../fake-repo', expected '.../fake-repo/plugins/fake-plugin'`); missing-target test failed on `[ "$status" -eq 2 ]` (current code exited 0 and launched the stub). The FAIR-02 structural test was green from birth by design — it validates Task 1's committed manifest, not Task 2's code (see TDD Gate Compliance).
- **Task 2 GREEN** (`a90d8db`): both call sites in `bench-run.py` changed exactly per the Interfaces block — `load_baseline()` joins `Path(entry["staged_path"]) / entry.get("plugin_dir_subpath", "")` before the `is_dir()` check and dies `EXIT_USAGE` naming the joined target (literal `staged_path` kept in the message for the pre-existing grep contract); `main()` mirrors the join for `--plugin-dir` argv. Docstring Behavior steps 2 and 5 updated. 11/11 bench-run.bats green.
- **Task 3** (`4114eae`): README opening + Baselines intro now say four manifests; 4th table row documents the arm and the selection rationale (spec-kit/BMAD structurally disqualified — no `--plugin-dir`-loadable manifest; superpowers larger but no non-interactive escape hatch; ralph-specum's `--quick` PreToolUse hook denies `AskUserQuestion`); Staging section documents the optional backward-compatible `plugin_dir_subpath` extension (stage-plugins.py unchanged); new "## Competitor plugin load-check" section names the three $0 bats proofs and records "### Live load-check: PENDING" with the verbatim `claude -p "/help" --plugin-dir ...` reproduction command and expected `ralph-specum:*` list.

## Verification Evidence (all commands actually run, observed output)

- `bats tests/bench-run.bats` → `1..11`, 11 ok, 0 not ok (post-GREEN; pre-GREEN tests 9 and 10 `not ok` for the exact right reasons)
- `bats tests/bench-run.bats tests/bench-verify.bats tests/stage-plugins.bats tests/bench-matrix.bats tests/bench-aggregate.bats` → `1..32`, ok=32, not_ok=0 — zero regression, all three existing manifests untouched
- Task 1 verify one-liner → `manifest OK` (model + claude_flags equality vs cairn.json, subpath, ref, repo, defaults_source all asserted)
- `test -f benchmarks/plugins/ralph-specum/v4.0.0/plugins/ralph-specum/.claude-plugin/plugin.json` → exit 0; `cat .../v4.0.0/.staged-ref` → `v4.0.0`; `git check-ignore benchmarks/plugins/ralph-specum/v4.0.0` → exit 0 (staged tree never committed)
- `grep -v '^#' benchmarks/scripts/bench-run.py | grep -c 'plugin_dir_subpath'` → 5 (≥ 2); `grep -c 'staged_path' benchmarks/scripts/bench-run.py` → 6 (die message retains the literal — additionally proven by the missing-target test's own `grep -qF "staged_path"` passing); `grep -v '^#' tests/bench-run.bats | grep -c 'plugin_dir_subpath'` → 5 (≥ 3)
- `python3 -m py_compile benchmarks/scripts/bench-run.py` → exit 0
- Task 3 greps: `competitor-ralph-specum` / `plugin_dir_subpath` / `Competitor plugin load-check` / `ralph-specum` all present in README; `PENDING` at the new section (line 153) alongside the pre-existing isolation one (line 223)
- `git diff --diff-filter=D` on all 4 commits → zero deletions
- API spend: **$0** — zero live claude calls (key absent, tripwire stubs proven never invoked)

## Live load-check status: PENDING (explicit, not skipped)

`ANTHROPIC_API_KEY` was absent (`[ -n "$ANTHROPIC_API_KEY" ]` → KEY_ABSENT, checked 2026-07-26) — the expected case. The wiring is proven at $0 by the three new bats tests; the exact live reproduction command (`claude -p "/help" --plugin-dir benchmarks/plugins/ralph-specum/v4.0.0/plugins/ralph-specum ... | grep -o 'ralph-specum:[a-z-]*' | sort -u`) is embedded verbatim in `benchmarks/README.md` § "Live load-check: PENDING", to be replaced with the observed `ralph-specum:*` list the moment a key exists. What remains unproven live is only that claude enumerates the plugin's commands in the isolated env; the argv path it will receive is stub-proven correct.

## Deviations from Plan

### Auto-fixed Issues

**1. [Minor] Docstring Behavior step 2 also updated (plan named only step 5)**
- **Found during:** Task 2 GREEN
- **Issue:** Step 2 stated "every plugin_dirs[].staged_path must already exist on disk" — literally false once the existence check validates the joined target
- **Fix:** Step 2 now reads "staged_path (joined with the entry's optional plugin_dir_subpath, when declared) must already exist on disk"
- **Files modified:** benchmarks/scripts/bench-run.py
- **Commit:** a90d8db

No other deviations — plan executed as written (network available, v4.0.0 reconfirmed, key absent as expected).

## TDD Gate Compliance

- RED gate: `84ef582` `test(04-01): ...` — tests 9/10 observed genuinely failing on the target assertions before any implementation
- GREEN gate: `a90d8db` `feat(04-01): ...` after it — full suite green
- REFACTOR: not needed (both call sites landed clean on first pass)
- Expected-pass note: the third new test (FAIR-02 manifest structural) passed during RED by construction — it asserts Task 1's already-committed artifact and involves no Task 2 code path. Investigated per the fail-fast rule and confirmed intentional (the plan itself specifies it as "no staging, no claude invocation — pure jq").

## Known Stubs

None in product code. The bats fixtures (env-asserting claude stub, tripwire stub, synthetic inline manifests) are the suite's deliberate $0 seams, per house convention.

## Threat Flags

No new surface beyond the plan's threat model. Mitigations implemented: T-04-01 (pin reconfirmed via live `git ls-remote --tags` before writing the manifest; `.staged-ref` records `v4.0.0`), T-04-04 (`defaults_source` cites exact vendor docs; FAIR-02 proven by a committed `jq -S` diff bats test), T-04-05 (subpath argv + fail-loud proven at $0; live `/help` check documented as explicit PENDING). T-04-02/T-04-03/T-04-SC accepted per plan (Phase 2 precedent, no registry install anywhere).

## Runtime artifacts out of scope (not committed)

Same pre-existing set recorded since 02-01 (`.beads/interactions.jsonl`, `01-BEADS-MAP.md`, `.beads/hooks/pre-push.old`, `.planning/.pending-auth-captures.jsonl`, `.pr-autopilot/`) — untouched (scope boundary). Per orchestrator constraints, bd issues, ROADMAP.md, and STATE.md were deliberately not modified by this executor.

## Self-Check: PASSED

- Files: competitor-ralph-specum.json, bench-run.py, bench-run.bats, README.md, staged `plugin.json` + `.staged-ref` — all present
- Commits: a3fccbf, 84ef582, a90d8db, 4114eae — all in `git log`
