# Executor isolation dispatch (ADR-1239 / #2584 Phase 3)

Read and follow this fragment from `execute-phase.md` step 3 when dispatching a wave.
It owns the per-host dispatch detail so the host workflow stays inside its
ADR-857 Phase 6 byte budget (#1168) — the host step keeps only the `ISOLATION`
resolution and its fail-closed guard.

## Resolve ISOLATION

Run this in the config-gate step, right after `RUNTIME`/`USE_WORKTREES` are read.

```bash
CAIRN_GSD="${CAIRN_GSD:-}"; if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; for _cg_root in "${CLAUDE_PROJECT_DIR:-}" "$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do [ -n "$_cg_root" ] || continue; _cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; if [ ! -x "${CAIRN_GSD:-}" ]; then echo "ERROR: cairn-gsd.sh not found (last path tried: ${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that lives in the repo. Run it from inside the CairnGo checkout, or export CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }
# Isolation is a NEGOTIATED CAPABILITY, not a runtime id (#2584). Fail-closed to none.
# #3045 CORE REDESIGN: `dispatch-isolation` PERSISTS this resolution to the
# run-scoped sentinel the isolation guard hooks read, as an unconditional
# side effect of resolving it — this call is the ONLY way the workflow learns
# ISOLATION at all, so the recording cannot be skipped the way a separate
# "and now also run this to record it" prose instruction could be. `--phase`
# threads the phase identifier into that same atomic write (mode + harnessFlag
# + phase together — see hooks/lib/isolation-sentinel.js for how the guards
# consume it).
ISOLATION=$(gsd_run query dispatch-isolation --raw --phase "${PHASE_NUMBER:-}" 2>/dev/null || echo "none")
case "$ISOLATION" in
  harness-worktree|orchestrator-worktree|none) ;;
  *) ISOLATION=none ;;
esac

# Project-level opt-out wins on every host; a host with no primitive fails closed.
[ "$USE_WORKTREES" = "false" ] && ISOLATION=none
if [ "$ISOLATION" = "none" ] && [ "$USE_WORKTREES" != "false" ]; then
  echo "FATAL: runtime '$RUNTIME' declares no executor-isolation primitive (dispatch.isolation=none) — executors would run unisolated against the main checkout. Set workflow.use_worktrees=false." >&2
  exit 1
fi

# Sweep orphaned locked worktrees from prior crashed sessions (#3707).
[ "$ISOLATION" != "none" ] && gsd_run query worktree.reap-orphans 2>/dev/null || true
# Auto-degrade if HEAD diverged from the fork base (#683) — both isolation models.
if [ "$ISOLATION" != "none" ]; then
  _SHOULD_DEGRADE=$(gsd_run query worktree.base-check --pick shouldDegrade 2>/dev/null || true)
  if [ "$_SHOULD_DEGRADE" = "true" ]; then
    _DEGRADE_MSG=$(gsd_run query worktree.base-check --pick message 2>/dev/null || true)
    [ -n "$_DEGRADE_MSG" ] && printf '%s\n' "$_DEGRADE_MSG" >&2
    USE_WORKTREES=false
    ISOLATION=none
  fi
fi

# Re-resolve (and, as a side effect, re-persist) now that the base-check
# auto-degrade above may have changed $ISOLATION since the first
# `dispatch-isolation` call. `--force-isolation` pushes the FINAL,
# shell-computed value (which the resolver itself cannot see — the #683
# base-check degrade is decided here, not inside cairn-gsd.sh) through the
# SAME single write path (`--force-isolation none` also clears the stored
# harnessFlag, since none applies to sequential dispatch). The isolation
# guard hooks (hooks/gsd-agent-isolation-guard.js,
# hooks/gsd-cursor-subagent-start.js) read this sentinel instead of
# re-deriving a host CAPABILITY from the registry — the registry's
# harness-worktree entry means "this host CAN isolate", not "this dispatch
# SHOULD be isolated", and every degrade above (project opt-out, the #683
# base-check auto-degrade) is a legitimate ISOLATION=none outcome the guards
# must not treat as a bypass. Best-effort: a write failure here must never
# fail the wave — the guards' own sentinel-absent fallback is safe, just less
# precise.
gsd_run query dispatch-isolation --raw --phase "${PHASE_NUMBER:-}" --force-isolation "$ISOLATION" >/dev/null 2>&1 || true
```

`ISOLATION` — not `RUNTIME` — selects how the wave fans out. These three values are the only
branch points; **never add a `RUNTIME = "codex"` test to the scheduler.** The per-host
invocation detail is descriptor data, surfaced by `dispatch-isolation --json` as
`harnessFlag` / `exec`.

| `ISOLATION` | Fan-out | What the scheduler does |
|---|---|---|
| `harness-worktree` | host-driven | Pass the host's own declared isolation flag (`harnessFlag`) on each executor dispatch and let the harness create + bind the worktree. GSD runs no git. |
| `orchestrator-worktree` | GSD-driven | GSD creates the worktree (`worktree create`), then process-spawns the executor bound to it via the resolved `exec` argv/cwd. GSD performs all git operations. |
| `none` | none | Plans run inline, sequentially (unchanged). |

Fail-closed is the invariant: an undeclared, unknown, or unresolvable isolation declaration
degrades to `none`, never to an unsafe parallel path. A `harness-worktree` host with no
declared flag, and an `orchestrator-worktree` host whose exec descriptor does not resolve,
both degrade to `none` rather than dispatching executors that only believe they are isolated.

## harness-worktree — pass the host flag

Read the flag once before dispatching; it is descriptor data, never hardcoded per runtime:

```bash
# #3045 CORE REDESIGN: `dispatch-isolation --json` already resolves and
# atomically records `harnessFlag` together with `isolation` and `phase` in
# ONE write, as a side effect of this same call (routeDispatchIsolation,
# cairn/scripts/cairn-gsd.sh) — there is no separate "now also record the
# flag" step, and therefore no flagless window between recording the mode and
# recording the flag.
# This parses the DISPATCHER's answer, not the wave manifest — same engine as every
# other bundle read in this workflow. Empty for an absent, null or empty flag and for
# an unparseable payload alike; the fail-closed check on the next line is what turns
# any of those into a refusal.
HARNESS_FLAG=$(gsd_run query dispatch-isolation --json --phase "${PHASE_NUMBER:-}" 2>/dev/null \
  | jq -r '.harnessFlag // empty' 2>/dev/null || true)
[ -n "$HARNESS_FLAG" ] || { echo "FATAL: runtime declares dispatch.isolation=harness-worktree but no harnessIsolationFlag — refusing to dispatch executors that would believe they are isolated." >&2; exit 1; }
```

Substitute `$HARNESS_FLAG`'s value for the `{harnessFlag}` placeholder in the `Agent()` dispatch
in `execute-phase.md` step 3 (on Claude Code it is literally `isolation="worktree"`).

## orchestrator-worktree — GSD creates the worktree and spawns the executor

The host has no harness-native isolation primitive, so **GSD** creates each worktree and process-spawns the executor into it. Fan-out is OS-level (N processes), not the host's subagent tool. Per the Codex `workspace-write` sandbox constraint, **the orchestrator performs every git operation** — create, merge, cleanup; the spawned executor only edits files and commits inside its own worktree.

Run the loop below once per runnable plan in the wave, **one plan at a time** (`git worktree add` races on `.git/config.lock`).

**Before running the bash block, substitute the plan's identifiers into it** exactly as you do for the `Agent()` prompt on the harness path: replace `{plan_number}` and `{phase_number}` with this plan's values. They are template placeholders, not shell variables. `$ORCH_ROOT` and `$EXPECTED_BASE` are real shell variables, already assigned earlier in this step; `$WAVE_WORKTREE_MANIFEST` was initialized above.

First build the executor prompt. It is the **same prompt text the harness path's `Agent()` call uses**, with the harness-only framing removed — drop the `<worktree_branch_check>` build-time embed note and the `<parallel_execution>` harness block, keep `<objective>`, the execution context, and `<success_criteria>` verbatim. Assign it to a shell variable so it can be passed as one argument:

```bash
# Compose the executor prompt for THIS plan. Single-quoted multi-line
# assignment (NOT a heredoc): these blocks are indented inside the workflow,
# and a heredoc terminator must sit at column 0 — `<<-` strips only tabs, not
# the leading spaces, so a heredoc here would never terminate. Single quotes
# also stop the shell expanding anything in the prompt body.
EXECUTOR_PROMPT='<objective>
Execute plan {plan_number} of phase {phase_number}-{phase_name}.
Commit each task atomically. Create SUMMARY.md.
Do NOT record the wave's tracking facts and do NOT update ROADMAP.md — the orchestrator is the single registrar, once, after all worktree agents in the wave complete.
</objective>

<execution_context>
You are running as an executor in a git worktree GSD created for you. Your
working directory IS that worktree. Do not cd elsewhere, and do not run any
git command that targets the main checkout. Use normal git commits WITH hooks.
Do NOT use --no-verify.
REQUIRED ORDER: Write SUMMARY.md, commit, then any narration.
</execution_context>

<success_criteria>
- [ ] All tasks executed
- [ ] Each task committed individually
- [ ] SUMMARY.md created AND committed in the plan directory
</success_criteria>'
[ -n "$EXECUTOR_PROMPT" ] || { echo "FATAL: executor prompt is empty for plan {plan_number}." >&2; exit 1; }
```

The prompt body must contain no single-quote character, since the assignment above is single-quoted; keep apostrophes out of it when editing.

Then create the worktree and resolve the spawn:

```bash
# 1. Create the worktree. Bounded, manifest-recorded, fail-closed, and
#    root-confined by the verb itself — never hand-roll `git worktree add`.
AGENT_ID="agent-p{plan_number}-$(date -u +%s)"
WT_BRANCH="worktree-${AGENT_ID}"
WT_PATH="${ORCH_ROOT}/.claude/worktrees/${AGENT_ID}"
CREATE_JSON=$(gsd_run query worktree.create \
  --manifest "$WAVE_WORKTREE_MANIFEST" \
  --agent-id "$AGENT_ID" \
  --path "$WT_PATH" \
  --branch "$WT_BRANCH" \
  --base "$EXPECTED_BASE" \
  --root "$ORCH_ROOT" 2>&1) || {
    echo "FATAL: worktree create failed for plan {plan_number}: $CREATE_JSON" >&2
    exit 1
  }

# 2. Resolve the host's headless-exec argv for that worktree. Descriptor
#    data — command, args, cwd flag and prompt flag all come from the
#    capability descriptor, so no host is named here.
EXEC_JSON=$(gsd_run query dispatch-isolation --json \
  --cwd-target "$WT_PATH" \
  --prompt "$EXECUTOR_PROMPT")

# 3. MANDATORY fail-closed check. `dispatch-isolation` degrades to
#    isolation:"none" / exec:null rather than exiting non-zero, so the
#    command substitution above ALWAYS "succeeds" — the exit code proves
#    nothing. A worktree already exists at this point (step 1 is a real side
#    effect), so an unusable exec must NOT be spawned and must NOT be left
#    behind as an orphan: tear it down through the manifest-scoped cleanup
#    and halt rather than silently running the wave unisolated.
EXEC_OK=$(printf '%s' "$EXEC_JSON" | jq -r 'if .isolation == "orchestrator-worktree" and ((.exec.command // "") != "") then "true" else "false" end' 2>/dev/null)
# Empty output means the payload did not parse at all — treat it as the same "no" the
# parser used to return, so the check below stays fail-CLOSED for every shape.
[ -n "$EXEC_OK" ] || EXEC_OK=false
if [ "$EXEC_OK" != "true" ]; then
  echo "FATAL: could not resolve an orchestrator-exec invocation for plan {plan_number} after its worktree was created. The wave is halted rather than run unisolated. Retained for inspection: $WT_PATH (branch $WT_BRANCH, recorded in $WAVE_WORKTREE_MANIFEST) — run 'gsd_run query worktree.cleanup-wave --manifest \"$WAVE_WORKTREE_MANIFEST\"' to merge/clean it." >&2
  exit 1
fi
```

`worktree create` records the entry in `$WAVE_WORKTREE_MANIFEST` itself, so **do not** call `worktree.record-agent` for these plans — that verb is the harness-path counterpart, used because the harness creates the worktree behind GSD's back. Double-recording is deduped by path+branch, but the create verb is the single writer here.

Spawn `EXEC_JSON`'s `command` + `args` as a background process with its working directory set to `EXEC_JSON.cwd`. The `cwd` is returned for **every** host, including those whose descriptor has no cwd flag (`cwdFlag: null`) and therefore bind through the process's own working directory — always set it, never assume the flag did the job. Wait for all spawned executors in the wave before merging.

The executor never records the tracking facts and never touches `ROADMAP.md`, and that guard needs no new code — `execute-plan` auto-detects worktree mode via the `IS_WORKTREE` (`.git`-is-a-file) primitive, which a GSD-created worktree trips identically to a harness-created one. The prohibition is on REGISTERING, not on writing: the state fact lives in the bd, where two agents registering the same wave register it twice instead of overwriting each other. Same wording, same force, as the single-registrar block in `execute-phase.md`.

Merge-back, validation, and cleanup are the **existing** gauntlet, unchanged: the serialized `worktree.cleanup-wave` merge loop that stops the wave and retains the worktree on conflict, and manifest-only cleanup (never glob-inferred). Because the manifest shape is identical, the orchestrator path reuses it verbatim.

> **Declared-scope conformance (#2596):** ADR-1239 specifies that *both* isolation adapters route their merge through a check that each plan branch's committed diff stayed inside its declared `files_modified` scope. That check does not exist yet for either adapter (it is tracked as #2596). When it lands it must be wired into this path **and** the harness path together.

