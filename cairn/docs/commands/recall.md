# /cairn:recall

> Recall context-mode memory scoped to the active bd issue + phase (intent-aware search)

## Usage

```text
/cairn:recall <query>
```

The positional argument is the search text.

## What it does

Searches context-mode memory scoped to the work at hand, per the
`cairn-context` conventions — not the whole session's noise:

1. Resolves the active scope: the in-progress bd issue id
   (`bd list --status in_progress`) and its `phase-N` label.
2. Searches scoped to it:
   `ctx_search(queries: ["$ARGUMENTS"], source: "<bd_id>")`.
3. Returns only the sections that matched.

The `source` filter is a **partial match**, so the label prefix works as a
zoom control:

| Scope | `source` value | Sees |
|---|---|---|
| One task (default) | `<bd_id>` | just that issue's memory |
| A whole phase | `phase-N` | every issue in that phase |
| Exact task + phase | `gb/<bd_id>/<phase>` | the narrowest slice |

context-mode ships as a cairn plugin dependency, so the `ctx_*` MCP tools are
present by default — no opt-in needed. If the user disabled context-mode and
the tools are absent, the command says so and stops. `.cairn/context.json`
only tunes the scope template; the defaults apply without it.

For an **unscoped** search across everything context-mode holds, use
[`/cairn:ctx search <query>`](ctx.md) instead.

## Flags & arguments

| Argument | Meaning |
|---|---|
| `<query>` | Positional, required. The search text passed to `ctx_search`. |

No flags. Widening/narrowing is done through the `source` prefix as shown
above, not through options.

## Examples

```text
/cairn:recall token refresh policy
```

→ with issue `proj-7hp` in progress, runs
`ctx_search(queries: ["token refresh policy"], source: "proj-7hp")` and
returns the matched sections — e.g. the auth-service note indexed earlier via
[`/cairn:remember`](remember.md).

```text
/cairn:recall migration invariants        # then widen if it misses
```

→ if the issue-scoped search comes back empty, widen to the phase with
`source: "phase-3"` before falling back to an unscoped `/cairn:ctx search`.

A miss can also mean the material was **streamed, not indexed** — only
indexed content is queryable (see the guide's troubleshooting table).

## Files touched

- **Reads:** the bd database (`bd list --status in_progress`) and
  `.cairn/context.json` if present (scope-template override). The search
  itself reads the local context-mode knowledge base.
- **Writes:** nothing.

## Related

- [`/cairn:remember`](remember.md) — index material under the same scoped label
- [`/cairn:ctx`](ctx.md) — raw passthrough for unscoped search and other ops
- [`/cairn:context-config`](context-config.md) — tune the source template
- [Cairn context guide](../context.md) — the source-label convention in full
