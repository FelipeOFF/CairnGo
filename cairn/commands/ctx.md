---
description: Run a context-mode operation directly — raw passthrough to the ctx_* tools
argument-hint: <search|stats|index|fetch|insight|doctor|upgrade|purge> [args…]
---

Raw context-mode passthrough — no cairn scoping. The `ctx_*` MCP tools ship with
cairn (context-mode is a dependency). Map the first token of `$ARGUMENTS` to the
tool and run it, passing the rest as arguments:

```text
search <query>   -> ctx_search(queries: [<query>])
stats            -> ctx_stats
index <text>     -> ctx_index(content: <text>)
fetch <url>      -> ctx_fetch_and_index(url: <url>)
insight          -> ctx_insight
doctor           -> ctx_doctor
upgrade          -> ctx_upgrade
purge <scope>    -> ctx_purge(scope: <session|project>)   ⚠ DESTRUCTIVE — confirm with the user first
```

For intent-scoped memory tied to the active issue + phase, prefer the curated
verbs `/cairn:recall` and `/cairn:remember` instead.
