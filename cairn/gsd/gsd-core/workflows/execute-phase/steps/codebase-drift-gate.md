# Step: codebase_drift_gate

Post-execution structural drift detection (#2003). Runs after the last wave
commits, before verification. **Non-blocking by contract:** any internal
error here MUST fall through and continue to `verify_phase_goal`. The phase
is never failed by this gate.

```bash
CAIRN_GSD="${CAIRN_GSD:-}"; if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; for _cg_root in "${CLAUDE_PROJECT_DIR:-}" "$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do [ -n "$_cg_root" ] || continue; _cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; if [ ! -x "${CAIRN_GSD:-}" ]; then echo "ERROR: cairn-gsd.sh not found (last path tried: ${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that lives in the repo. Run it from inside the CairnGo checkout, or export CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }
# Resolve the dispatcher through the launcher preamble above, NOT a bare PATH binary: on
# this install it lives in the repo (cairn/scripts/cairn-gsd.sh) and nothing answers on
# PATH, so a bare call exits 127, `2>/dev/null` hides it, and this non-blocking gate
# would silently skip drift detection forever (#619). The canonical launcher preamble is
# defined once here — the
# always-run drift check, the file's first launcher block — and the conditional auto-remap
# block below reuses the launcher function from this shared shell scope (the single-preamble
# pattern established by discuss-phase #614, enforced by tests/runtime-launcher-parity.test.cjs).
# Non-blocking is preserved: an internal drift-command failure still falls through to the
# skip JSON via the `|| echo` below.
DRIFT=$(gsd_run verify codebase-drift 2>/dev/null || echo '{"skipped":true,"reason":"sdk-failed"}')
```

Parse JSON for: `skipped`, `reason`, `action_required`, `directive`,
`spawn_mapper`, `affected_paths`, `elements`, `threshold`, `action`,
`last_mapped_commit`, `message`.

**If `skipped` is true (no STRUCTURE.md, missing git, or any internal error):**
Log one line — `Codebase drift check skipped: {reason}` — and continue to
`verify_phase_goal`. Do NOT prompt the user. Do NOT block.

**If `action_required` is false:** Continue silently to `verify_phase_goal`.

**If `action_required` is true AND `directive` is `warn`:**
Print the `message` field verbatim. The format is:

```text
Codebase drift detected: {N} structural element(s) since last mapping.

New directories:
  - {path}
New barrel exports:
  - {path}
New migrations:
  - {path}
New route modules:
  - {path}

Run /gsd:map-codebase --paths {affected_paths} to refresh planning context.
```

Then continue to `verify_phase_goal`. Do NOT block. Do NOT spawn anything.

**If `action_required` is true AND `directive` is `auto-remap`:**

First load the mapper agent's skill bundle (the executor's `AGENT_SKILLS`
from step `init_context` is for `gsd-executor`, not the mapper):

```bash
# gsd_run is defined by the canonical preamble in the drift-check block above and reused
# here via the workflow's shared shell scope — defining it once keeps the file compliant
# with the single-canonical-preamble parity invariant (#619). This block only runs on the
# `auto-remap` directive, which is always reached after the drift check above has run.
AGENT_SKILLS_MAPPER=$(gsd_run query agent-skills gsd-codebase-mapper)
```

Then spawn `gsd-codebase-mapper` agents with the `--paths` hint (runs in a subagent — no output until it returns, ~1–5 min; expected, not a freeze):

<!-- #2508 runtime-aware-dispatch -->

> **Runtime-aware dispatch (#2508 Phase 4).** GSD workflows dispatch specialized subagents by role. Before dispatching on a built-in-only runtime (kimi-code — three built-ins only), resolve the role to a built-in via `gsd_run query resolve-dispatch-type --requested <role> --raw`. On named-dispatch runtimes (Claude/OpenCode/…) the role is returned unchanged; on kimi-code it maps to `coder`/`explore`/`plan` by role-suffix. The persona rides `${AGENT_SKILLS_<ROLE>}` (Phase 3) regardless. See @gsd-core/references/runtime-aware-dispatch.md.

```text
Agent(
  subagent_type="gsd-codebase-mapper",
  description="Incremental codebase remap (drift)",
  prompt="Focus: arch
Today's date: {date}
--paths {affected_paths joined by comma}

Refresh STRUCTURE.md and ARCHITECTURE.md scoped to the listed paths only.
Stamp last_mapped_commit in each document's frontmatter.
${AGENT_SKILLS_MAPPER}"
)
```

> **ORCHESTRATOR RULE — CODEX RUNTIME**: After calling Agent() above, stop working on this task immediately. Do not read more files, edit code, or run tests related to this task while the subagent is active. Wait for the subagent to return its result. This prevents duplicate work, conflicting edits, and wasted context. Only resume when the subagent result is available.

If the spawn fails or the agent reports an error: log `Codebase drift
auto-remap failed: {reason}` and continue to `verify_phase_goal`. The phase
is NOT failed by a remap failure.

If the remap succeeds: log `Codebase drift auto-remap completed for paths:
{affected_paths}` and continue to `verify_phase_goal`.

The two relevant config keys (continue on error / failure if either is invalid):
- `workflow.drift_threshold` (integer, default 3) — minimum drift elements before action
- `workflow.drift_action` — `warn` (default) or `auto-remap`

This step is fully non-blocking — it never fails the phase, and any
exception path returns control to `verify_phase_goal`.
