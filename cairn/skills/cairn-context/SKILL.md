---
name: cairn-context
description: Use when a repo has .cairn/context.json AND the context-mode ctx_* MCP tools are available — makes context-mode's knowledge base GSD/beads-aware. Scopes indexed memory by the active bd issue + GSD phase (source-label convention), recalls only the active task's context, and watches ctx_stats to advise task-splitting before the window degrades. Scope-by-label only — never deletes. Complements the cairn skill.
---

# cairn context (intent-aware memory for context-mode)

context-mode is excellent at compressing raw runtime data inside a session, but
it is *architecturally blind* — it compresses by recency/size, not by what the
work actually needs. This skill gives it intent: it ties context-mode's
knowledge base to the **active bd issue** and **GSD phase**, so retrieval is
scoped to the task at hand instead of the whole session's noise.

bd is the source of truth for *what the work is*; GSD owns *what phase it's in*;
context-mode holds *the compressed memory of doing it*. This skill is the wiring.

## Activation gate

context-mode is a **hard dependency** of cairn, so its `ctx_*` MCP tools are
present by default. Apply this skill whenever:
- `.planning/` (GSD) and `.beads/` (beads) both exist — the `cairn` skill is active, **and**
- The `ctx_*` MCP tools are available in the session.

This layer is **on by default** — it does not require opt-in. `.cairn/context.json`
is **optional tuning**: if present it overrides the defaults below (source
template, capacity threshold, capacity-guard on/off); if absent, the defaults
apply. `/cairn:context-config` writes that file to customize them. The only
case where the skill is inert is the rare one where the `ctx_*` tools are
genuinely unavailable (context-mode disabled by the user).

**Defaults (when `.cairn/context.json` is absent):** `source_template` =
`gb/{bd_id}/{phase}`, `capacity_guard.enabled` = true, `token_threshold` =
`150000`, `reset.mode` = `scope-by-label`.

## Capability boundaries (do not exceed)

context-mode is a set of **passive MCP tools**. It cannot signal, pause, or
delete on its own. This skill works strictly within what the tools support:

| Want | Real mechanism | Not available |
|---|---|---|
| Isolate a task's memory | Label on index (`source`), filter on search (`ctx_search(source:…)`) | per-task delete |
| "Clear" a phase | Switch the active source scope; stop searching the old label | per-phase purge |
| Free the window | Advise `bd` to split the active issue (agent acts) | context-mode auto-pausing |
| Real wipe | `ctx_purge(session\|project)` — **manual, user-confirmed only** | per-task/phase purge |

**This skill NEVER calls `ctx_purge`.** Deletion is whole-session or
whole-project only, so it stays an explicit user action. Memory is isolated by
*scoping*, not by deleting (`reset.mode: "scope-by-label"`).

## The source-label convention

Every time you index during execution, set the `source` label from
`scoping.source_template` in `.cairn/context.json` (default
`gb/{bd_id}/{phase}`):

- `{bd_id}` = the active bd issue (e.g. `proj-7hp`)
- `{phase}` = its phase label (e.g. `phase-3`)

```
ctx_index(content: <docs>,   source: "gb/proj-7hp/phase-3")
ctx_batch_execute(commands: [...], )   # label its commands "gb/proj-7hp/phase-3 — <what>"
```

Recall is then **scoped to intent**, not the whole session:

```
ctx_search(queries: [...], source: "proj-7hp")   # just this task
ctx_search(queries: [...], source: "phase-3")    # the whole phase
```

Because `ctx_search`'s `source` filter is a partial match, the `gb/<id>/<phase>`
prefix lets you widen or narrow the lens by how much of the path you pass.

### What to index vs. what to stream

Follow context-mode's own contract, scoped by the active label:
- **Index** (persisted, queryable): API docs, framework guides, skill prompts,
  spec sections, MCP `tools/list` — anything you'll reference precisely later,
  under `source: gb/<bd_id>/<phase>`.
- **Stream, don't persist**: logs, test output, build output, CSV — run through
  `ctx_execute_file` so the bytes process in-sandbox and never bloat the base.
  Keep only the derived conclusion, tagged to the active task in your notes.

## Lifecycle — hook into the cairn flow

Run these alongside the `cairn` lifecycle (claim → in_progress → close):

| cairn event | context action |
|---|---|
| **issue claimed / phase work starts** | Set active scope = `gb/<bd_id>/<phase>`. Index the task's spec/docs under it. |
| **during execution** | Index reference material under the active label; recall with `ctx_search(source: "<bd_id>")`. Stream logs via `ctx_execute_file`. |
| **phase transition** (e.g. Execute → Verify) | `ctx_stats` checkpoint. Switch active scope to the new phase's issue label(s). Index verify artifacts (scripts, error logs to keep) under the new label. Recall scoped to the new label — the prior phase's noise simply isn't searched. **No deletion.** |
| **issue closed** (`bd close`) | Its labeled chunks fall out of active scope automatically (you only search active labels). They persist for later cross-phase recall. |
| **session/milestone end** | If — and only if — the user explicitly asks to reset, surface `ctx_purge(scope: "session")` or `(scope: "project")`. Never auto-run it. |

## Capacity guard (proactive token budgeting)

When the capacity guard is enabled (the default; override in `.cairn/context.json`):

1. Call `ctx_stats` at each phase transition, and periodically during long
   execution runs.
2. If the reported cumulative tool-output token estimate exceeds
   `capacity_guard.token_threshold` (default `150000`, tuned for medium
   multi-phase loops), do **not** plow on. Instead advise splitting the active
   bd issue into smaller sub-tasks:
   ```bash
   bd create --title "<subtask>" --type task   # one per bite-sized slice
   bd dep add <new-id> <active-id>              # wire the dependency
   ```
   Carry the source label onto the new ids (`gb/<new-id>/<phase>`) so their
   memory stays scoped. This forces a natural context reset by *narrowing the
   active task*, before the window degrades.
3. `action` is advisory: context-mode cannot pause the loop itself — you (the
   agent) act on the signal. Surface the recommendation; let the user/flow proceed.

## Precedence & safety

- This layer is **read-mostly** on context-mode: it indexes and searches. The
  only destructive op (`ctx_purge`) is never automatic.
- On any conflict between a bd issue and GSD phase docs, **GSD docs win** —
  identical to the `cairn` skill.
- `.cairn/context.json` is optional tuning, not a gate — defaults apply when it
  is absent. The skill is inert only if the user has disabled context-mode so
  the `ctx_*` tools are unavailable.
