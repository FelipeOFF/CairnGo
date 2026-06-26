---
description: Index current work into context-mode under the active bd issue + phase label
argument-hint: "[what to remember]"
---

Persist reference material into context-mode under the intent-scoped source
label, per the `cairn-context` conventions.

context-mode is a cairn dependency, so the `ctx_*` tools are present by default;
no opt-in needed. (`.cairn/context.json` only tunes the source template — the
default below applies without it. If the user disabled context-mode and the
`ctx_*` tools are absent, say so and stop.)

1. Resolve the active label from `scoping.source_template` (default
   `gb/{bd_id}/{phase}`) using the in-progress bd issue and its phase.
2. Index under it:
   `ctx_index(content: <the material, or $ARGUMENTS>, source: "gb/<bd_id>/<phase>")`.
3. Index **reference-grade** material only — docs, specs, decisions you'll cite
   later. Do **not** index logs / test / build output; stream those via
   `ctx_execute_file` and keep only the conclusion.

Never deletes — this layer is scope-by-label only.
