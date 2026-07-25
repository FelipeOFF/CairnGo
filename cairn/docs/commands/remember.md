# /cairn:remember

> Index current work into context-mode under the active bd issue + phase label

## Usage

```text
/cairn:remember [what to remember]
```

The argument is optional. With it, the given text becomes the material to
index; without it, the command indexes the reference material currently at
hand in the conversation (a spec just read, a decision just made).

## What it does

Persists reference material into context-mode under the intent-scoped source
label, per the `cairn-context` conventions:

1. Resolves the active label from `scoping.source_template` (default
   `gb/{bd_id}/{phase}`) using the in-progress bd issue
   (`bd list --status in_progress`) and its `phase-N` label.
2. Indexes under that label:
   `ctx_index(content: <the material, or $ARGUMENTS>, source: "gb/<bd_id>/<phase>")`.
3. Indexes **reference-grade** material only — docs, specs, decisions you will
   cite later. Logs, test output, and build output are **not** indexed; those
   are streamed via `ctx_execute_file` and only the conclusion is kept.

context-mode ships as a cairn plugin dependency, so the `ctx_*` MCP tools are
present by default — no opt-in needed. If the user disabled context-mode and
the tools are absent, the command says so and stops.

This layer **never deletes**. Isolation is scope-by-label: old memory simply
falls out of the search lens when the active issue or phase changes. The only
destructive operation (`ctx_purge`) lives in [`/cairn:ctx`](ctx.md) and is
always manual and user-confirmed.

## Flags & arguments

| Argument | Meaning |
|---|---|
| `[what to remember]` | Optional positional. The text to index. Omitted → the command indexes the reference material currently in hand. |

No flags. Tuning (source template, capacity guard) lives in
`.cairn/context.json` via [`/cairn:context-config`](context-config.md);
defaults apply without the file.

## Examples

```text
/cairn:remember The auth service rejects tokens older than 15 minutes; refresh must happen client-side
```

→ resolves the active issue (say `proj-7hp` in `phase-3`) and runs
`ctx_index(content: "...", source: "gb/proj-7hp/phase-3")`. Later,
`/cairn:recall token refresh` finds it scoped to that issue.

```text
/cairn:remember
```

→ indexes the reference material currently in the conversation (e.g. the API
spec you just fetched) under the active `gb/<bd_id>/<phase>` label.

## Files touched

- **Reads:** the bd database (`bd list --status in_progress`, to resolve the
  active issue) and `.cairn/context.json` if present (source-template
  override).
- **Writes:** the context-mode knowledge base (local, managed by the
  context-mode plugin). Nothing under `.planning/`, `.beads/`, or `.cairn/`
  is modified.

## Related

- [`/cairn:recall`](recall.md) — search memory scoped to the same label
- [`/cairn:ctx`](ctx.md) — raw context-mode passthrough (unscoped index/search)
- [`/cairn:context-config`](context-config.md) — override the source template and capacity guard
- [Cairn context guide](../context.md) — the full scope-by-label model
