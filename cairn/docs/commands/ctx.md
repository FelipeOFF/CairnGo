# /cairn:ctx

> Run a context-mode operation directly — raw passthrough to the ctx_* tools

## Usage

```text
/cairn:ctx <search|stats|index|fetch|insight|doctor|upgrade|purge> [args…]
```

The first token selects the operation; the rest are passed as its arguments.

## What it does

Raw context-mode passthrough — **no cairn scoping**. The command maps the
first token of the arguments to the matching `ctx_*` MCP tool and runs it:

| Operation | Tool call |
|---|---|
| `search <query>` | `ctx_search(queries: [<query>])` |
| `stats` | `ctx_stats` |
| `index <text>` | `ctx_index(content: <text>)` |
| `fetch <url>` | `ctx_fetch_and_index(url: <url>)` |
| `insight` | `ctx_insight` |
| `doctor` | `ctx_doctor` |
| `upgrade` | `ctx_upgrade` |
| `purge <session\|project>` | `ctx_purge(scope: <session\|project>)` — **destructive, confirmed first** |

The `ctx_*` tools ship with cairn (context-mode is a plugin dependency), so
they are present by default.

Because this is a passthrough, nothing here is labeled with the
`gb/<bd_id>/<phase>` convention: `index` writes unscoped chunks and `search`
looks across everything. For intent-scoped memory tied to the active issue +
phase, prefer the curated verbs [`/cairn:recall`](recall.md) and
[`/cairn:remember`](remember.md).

### The purge warning

`purge` is **destructive and coarse**: context-mode can only delete a whole
**session** or the whole **project** knowledge base — there is no per-issue or
per-phase delete. That is exactly why the cairn integration isolates memory by
label instead of by deletion. The command always asks for explicit user
confirmation before running `ctx_purge`, and no cairn flow ever triggers it
automatically.

## Flags & arguments

| Argument | Meaning |
|---|---|
| `<operation>` | Positional, required. One of `search`, `stats`, `index`, `fetch`, `insight`, `doctor`, `upgrade`, `purge`. |
| `[args…]` | Passed to the selected tool: the query for `search`, the text for `index`, the URL for `fetch`, the scope (`session` or `project`) for `purge`. |

## Examples

```text
/cairn:ctx search adapter contract
```

→ `ctx_search(queries: ["adapter contract"])` across the whole knowledge
base, no source filter — useful when a scoped `/cairn:recall` came back empty.

```text
/cairn:ctx stats
```

→ `ctx_stats`; reports cumulative tool-output token usage (the number the
capacity guard watches).

```text
/cairn:ctx purge session
```

→ asks for confirmation, then `ctx_purge(scope: "session")` — wipes the whole
session's memory. There is no smaller scope; make sure that is what you want.

## Files touched

- **Reads/writes:** the local context-mode knowledge base only, via the MCP
  tools. No files under `.planning/`, `.beads/`, or `.cairn/` are touched.
- `purge` deletes knowledge-base content (session- or project-wide).

## Related

- [`/cairn:recall`](recall.md) — issue+phase-scoped search (preferred)
- [`/cairn:remember`](remember.md) — issue+phase-scoped indexing (preferred)
- [`/cairn:context-config`](context-config.md) — tune the integration defaults
- [Cairn context guide](../context.md) — why isolation is scope-by-label, not purge
