---
description: Recall context-mode memory scoped to the active bd issue + phase (intent-aware search)
argument-hint: <query>
---

Search context-mode memory scoped to the work at hand, per the `cairn-context`
conventions — not the whole session's noise.

context-mode is a cairn dependency, so the `ctx_*` tools are present by default;
no opt-in needed. (`.cairn/context.json` only tunes the scope template — defaults
apply without it. If the user disabled context-mode and the `ctx_*` tools are
absent, say so and stop.)

1. Resolve the active scope: the in-progress bd issue id
   (`bd list --status in_progress`) and its `phase-N` label.
2. Search scoped to it:
   `ctx_search(queries: ["$ARGUMENTS"], source: "<bd_id>")` — widen to the whole
   phase with `source: "phase-N"`, or narrow with the full `gb/<bd_id>/<phase>`
   prefix (the `source` filter is a partial match).
3. Return the matched sections only.

For unscoped search, use `/cairn:ctx search <query>`.
