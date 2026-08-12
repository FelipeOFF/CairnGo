# Cairn context — intent-aware memory for context-mode

Complete guide to the context-mode integration in the `cairn` plugin: what
it is, what it does, how it works, and how to set it up.

---

## 1. What it is

[context-mode](https://github.com/mksglu/context-mode) is a Claude Code plugin
that keeps raw runtime data (tool output, docs, logs) out of the conversation by
storing it in a searchable knowledge base (`ctx_*` MCP tools). It compresses
brilliantly — but **architecturally blind**: it decides what to keep by recency
and size, not by what the work actually needs. It can just as easily surface a
stale log as the one compiler error that explains the current failure.

`cairn context` gives that memory **intent**. It ties context-mode's
knowledge base to the **active bd issue** and the **GSD phase**, so retrieval is
scoped to the task at hand instead of the whole session's noise.

It is **thin glue**: a skill, a hook, and an optional tuning file. No
dispatcher, no runtime, no HTTP. It does not fork, vendor, or modify
context-mode, bd, or GSD — it only ships the convention that makes them aware
of each other.

It is also **on by default**: context-mode ships as a cairn plugin dependency,
so the `ctx_*` tools are present out of the box and the convention applies in
every repo where the cairn integration is active (both `.planning/` and
`.beads/` exist). `.cairn/context.json` is optional tuning, not a gate.

### Design in one line

> **bd says what the work is. GSD says what phase it's in. context-mode holds
> the memory of doing it. This layer labels that memory with the first two so
> the third can be searched by intent.**

The three tools nest — each narrows the one inside it:

```
┌─ GSD ─ phase isolation (Plan / Execute / Verify) ───────────┐
│  ┌─ bd ─ the active issue (the task boundary) ───────────┐  │
│  │  ┌─ context-mode ─ compressed tool-output memory ──┐  │  │
│  │  │   labeled  source: gb/<bd_id>/<phase>            │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Why scope-by-label (and not "purge old tasks")

The obvious design — *delete a task's memory when it closes* — is **not
available**. context-mode can only delete by whole session or whole project
(`ctx_purge`). There is no per-task or per-phase delete. So isolation is done by
**labeling on write and filtering on read**, never by deleting:

| Model | Why not |
|---|---|
| **Per-task purge on close** | context-mode has no such scope. Only session/project wipe exists. |
| **Auto-purge each phase** | Risks discarding cross-phase context (the root-cause error you still need in Verify). |
| **Scope-by-label** ✅ | Tag memory with `gb/<bd_id>/<phase>`; search the active label. Nothing is lost; old noise is simply not in the lens. Real wipe stays a manual, user-confirmed `ctx_purge`. |

---

## 2. What it does

Three behaviors, all driven by the active bd issue + phase:

```
   ┌──────────────────────────────────────────────────────────────┐
   │ 1. SCOPE  index under gb/<bd_id>/<phase>; recall by that label │
   │ 2. SWITCH on phase change, move the active label; old noise     │
   │           drops out of the lens (no delete)                     │
   │ 3. GUARD  ctx_stats over threshold -> advise splitting the      │
   │           active bd issue into sub-tasks (bd create + dep add)   │
   └──────────────────────────────────────────────────────────────┘
```

1. **Intent-scoped retention** — everything indexed while a bd issue is active
   carries that issue's label. Recall is filtered to it, so the model reads the
   active task's memory, not the session's.
2. **Phase-driven scope switch** — at a phase boundary (e.g. Execute → Verify),
   checkpoint `ctx_stats`, switch the active label to the new phase's issues, and
   index that phase's artifacts under it. The previous phase's chunks persist but
   fall out of the search scope.
3. **Capacity guard** — when `ctx_stats` reports token usage past a configurable
   threshold, the agent is told to split the active bd issue into smaller
   sub-tasks. Narrowing the task is the context reset — before the window degrades.

---

## 3. Architecture

```
cairn/
├── skills/
│   └── cairn-context/SKILL.md   # the convention + lifecycle + boundaries
├── commands/
│   └── context-config.md            # /cairn:context-config (optional tuning)
├── hooks/
│   └── session-start.sh             # emits the reminder when .planning/ + .beads/ exist
└── templates/
    └── context.json.example         # starter tuning config (optional)
```

There is **no dispatcher and no adapter** — unlike the sync layer, nothing here
makes a network call or runs a subprocess. context-mode is a set of passive MCP
tools; the *agent* calls them, and this layer is the set of conventions telling
the agent how, scoped by bd + GSD state.

| Piece | Role |
|---|---|
| `cairn-context` skill | The rules: label on index, filter on search, switch on phase, guard on stats. On by default — active whenever the cairn integration is (both dirs present) and the `ctx_*` tools exist. |
| `session-start.sh` | Injects a one-screen reminder of the convention whenever both `.planning/` and `.beads/` exist — **not** gated on `context.json`. |
| `context.json` | **Optional** tuning overrides (source template, capacity threshold); defaults apply without it. |

---

## 4. The source-label convention (the data model)

context-mode's only organizing handle is the free-text **`source`** label on
`ctx_index` / `ctx_batch_execute`, which `ctx_search` can filter by (partial
match). This layer standardizes that label:

```
source = gb/<bd_id>/<phase>
         │    │        └─ the issue's phase label, e.g. phase-3
         │    └────────── the active bd issue id, e.g. proj-7hp
         └─────────────── fixed prefix, namespaces all cairn memory
```

Because the filter is a **partial match**, the path prefix is a zoom control:

| Search scope | Call | Sees |
|---|---|---|
| One task | `ctx_search(source: "proj-7hp")` | just that issue's memory |
| A whole phase | `ctx_search(source: "phase-3")` | every issue in phase 3 |
| All cairn memory | `ctx_search(source: "gb/")` | everything this layer indexed |

The pattern defaults to `gb/{bd_id}/{phase}` and can be overridden via
`source_template` in `.cairn/context.json`; `{bd_id}` and `{phase}` are the
only interpolated fields.

### What to index vs. what to stream

The label only applies to things you **persist**. Follow context-mode's own
contract for what that is:

| Data | Action | Why |
|---|---|---|
| API docs, specs, framework guides, `tools/list` | `ctx_index(source: gb/<id>/<phase>)` | referenced precisely later; queryable |
| Logs, test output, build output, CSV | `ctx_execute_file` (no persist) | process in-sandbox; keep only the conclusion |
| One-off content that fits | keep inline | not worth a chunk |

---

## 5. How the three behaviors work

### Scope (index + recall)

```
while an issue is active:
    index docs/specs under  source = gb/<bd_id>/<phase>
    recall with             ctx_search(source: "<bd_id>")
    stream logs through      ctx_execute_file   (never persisted)
```

The "active label" is just the current bd issue + its `phase-N` label — both
already tracked by the `cairn` skill. No extra state file.

### Switch (phase boundary)

```
on Execute -> Verify (or any phase transition):
    ctx_stats                      # checkpoint usage
    active label := gb/<new_id>/<new_phase>
    index verify artifacts (scripts, kept error logs) under the new label
    recall scoped to the new label
    # the prior phase's chunks remain in storage but are out of the lens
```

No deletion happens. Isolation is the scope change, not a wipe.

### Guard (capacity)

```
periodically during long runs, and at each phase boundary:
    s := ctx_stats
    if s.tokens > capacity_guard.token_threshold:
        # narrow the task -> natural context reset
        bd create --title "<slice>" --type task     # one per bite-sized slice
        bd dep add <new-id> <active-id>
        carry the label onto the new ids: gb/<new-id>/<phase>
        surface the recommendation; let the flow proceed
```

`ctx_stats` reports cumulative tool-output token usage, **not** a database-full
signal — the threshold is a heuristic proxy, and the action is **advisory**:
context-mode cannot pause the loop, so the agent acts on the number.

---

## 6. Quick start

```text
# 1. Install cairn — context-mode comes with it as a plugin dependency, so the
#    ctx_* tools (and this integration) are on by default. Nothing to enable.

# 2. In a repo with both .planning/ and .beads/ (run /cairn:init if needed),
#    that's it. During execution:
#      - index docs under  source: gb/<bd_id>/<phase>
#      - recall with        ctx_search(source: "<bd_id>")
#      - the SessionStart hook reminds you of the convention each session.

# 3. Optional — override the defaults (scope template, capacity threshold):
/cairn:context-config      # interactive; writes .cairn/context.json
```

---

## 7. Configuration

All state lives under `<project>/.cairn/`:

| File | Committed? | Purpose |
|---|---|---|
| `context.json` | **yes** | Optional tuning overrides. Holds no secrets. |

`context.json` is **optional** — the integration is on by default and the
defaults below apply without it. When you do tune, commit the file so the whole
team shares the same settings.

```json
{
  "enabled": true,
  "scoping": {
    "source_template": "gb/{bd_id}/{phase}"
  },
  "capacity_guard": {
    "enabled": true,
    "token_threshold": 150000,
    "action": "advise_split"
  },
  "reset": {
    "mode": "scope-by-label"
  }
}
```

| Field | Meaning | Default |
|---|---|---|
| `enabled` | Master switch — set `false` to turn the conventions off in this repo. Absent file = `true`. | `true` |
| `scoping.source_template` | Label pattern; `{bd_id}` + `{phase}` interpolated. | `gb/{bd_id}/{phase}` |
| `capacity_guard.enabled` | Watch `ctx_stats` and advise splitting. | `true` |
| `capacity_guard.token_threshold` | Cumulative tool-output tokens that trigger the split advice. | `150000` |
| `capacity_guard.action` | What to do at threshold (only `advise_split` today). | `advise_split` |
| `reset.mode` | Isolation strategy. Only `scope-by-label` — never deletes. | `scope-by-label` |

### Tuning the threshold to your loop length

The default suits **medium, multi-phase** loops. Match it to how long your agent
runs unattended:

| Loop length | Suggested `token_threshold` |
|---|---|
| Short — single phase, frequent check-ins | `80000` |
| Medium — a few phases per run (default) | `150000` |
| Long — multi-hour autonomous (`/gsd:autonomous`) | `300000` |

Lower = splits sooner (more, smaller tasks); higher = lets a run accumulate more
before advising a split.

---

## 8. Lifecycle integration

Run these alongside the `cairn` lifecycle (claim → in_progress → close):

| cairn / GSD step | context action |
|---|---|
| issue claimed / phase work starts | active label := `gb/<bd_id>/<phase>`; index the task's spec/docs under it |
| during execution | index reference material under the label; recall `ctx_search(source: "<bd_id>")`; stream logs via `ctx_execute_file` |
| phase transition (Execute → Verify) | `ctx_stats` checkpoint; switch active label; index verify artifacts under it; recall scoped to the new label — **no delete** |
| issue closed (`bd close`) | its chunks fall out of active scope automatically (you only search active labels); they persist for cross-phase recall |
| session / milestone end | only if the user explicitly asks to reset, surface `ctx_purge(scope: session\|project)` — never auto-run |

---

## 9. Capability boundaries

context-mode is **passive MCP tools**. This integration works strictly within
what they support — anything beyond is deliberately *not* built:

| Want | Real mechanism here | Not available in context-mode |
|---|---|---|
| Isolate a task's memory | label on index + filter on search | per-task delete |
| "Clear" a phase | switch the active label; stop searching the old one | per-phase purge |
| Free the window | advise `bd` to split the active issue (agent acts) | context-mode pausing the loop |
| Real wipe | `ctx_purge(session\|project)` — **manual, user-confirmed** | per-task / per-phase purge |

**This layer never calls `ctx_purge`.** Deletion is whole-session or
whole-project only, so it stays an explicit user action. On any conflict between
a bd issue and GSD phase docs, **GSD docs win** — same precedence as the
`cairn` skill.

---

## 10. Security & privacy

- **Local only.** The integration runs entirely on your machine. context-mode's
  knowledge base is local; nothing is sent anywhere by this layer.
- **No secrets.** `context.json` holds only switches and a number — no tokens,
  no paths to anything sensitive. Safe to commit.
- **Non-destructive by design.** The only destructive context-mode op
  (`ctx_purge`) is never invoked automatically. A reset is always a deliberate,
  user-confirmed action.
- **On by default, tunable.** context-mode ships as a cairn dependency, so the
  convention applies with no setup; `.cairn/context.json` only tunes it. To
  switch the conventions off in a repo, set `enabled: false` there (or disable
  the context-mode plugin) — plain context-mode usage is unaffected either way.

---

## 11. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Skill never engages | The `ctx_*` tools aren't loaded (context-mode dependency unresolved or plugin disabled); `.planning/` or `.beads/` missing (cairn integration not active); or `.cairn/context.json` sets `enabled: false`. No config file is needed — defaults apply without it. |
| No SessionStart reminder | The hook emits whenever both `.planning/` and `.beads/` exist — it is not gated on `context.json`. Check both directories are present (run `/cairn:init` if not). |
| `ctx_search` returns other tasks' noise | You didn't pass `source:` — scope it: `ctx_search(source: "<bd_id>")`. |
| Recall misses something you expected | It was streamed (`ctx_execute_file`), not indexed — only indexed content is queryable. Index it under the active label if you need it later. |
| Capacity guard never fires | Usage below `token_threshold`, or `capacity_guard.enabled:false`. Lower the threshold for shorter loops. |
| Capacity guard fires constantly | Threshold too low for your loop length — raise it (see §7). |
| Want to actually wipe memory | That's a manual choice: `ctx_purge(scope: "session")` or `(scope: "project")`. This layer will not do it for you. |

---

## 12. Summary

- bd = the task; GSD = the phase; context-mode = the memory. This layer labels
  the memory with the first two so it can be searched by intent.
- Three behaviors: **scope** (label + filter), **switch** (move the label on
  phase change), **guard** (`ctx_stats` over threshold → advise a `bd` split).
- **Scope-by-label only** — never deletes. `ctx_purge` stays a manual user action.
- **On by default** — context-mode is a cairn dependency; `.cairn/context.json`
  is optional tuning (committed, no secrets), not a gate.
- No dispatcher, no adapter, no network — just a skill, a hook, and a convention.
