# cairn adapter contract

An **adapter** is an executable in this directory that connects one external
work-management tool to bd, the hub. The dispatcher (`scripts/gbsync.py`) calls
it; the adapter does the HTTP. Adapters may be written in any language
(`.py` and `.sh` are auto-detected; an extensionless executable also works).

bd is the **source of truth**. Sync is hub-and-spoke: every tool talks to bd,
never to another tool.

## Invocation

The dispatcher passes one JSON object on **stdin** and reads the result from
**stdout**. Exit `0` on success; any nonzero exit is logged by the dispatcher,
which then continues with the other backends.

Both directions accept `--dry-run` at the dispatcher level: the would-be
operations are printed as `DRY-RUN:` lines and the adapter is **never
invoked** (nothing is written to id-map/state/conflicts either).

### PUSH — `create` | `update` | `close`  (bd → tool)

stdin:
```json
{
  "action": "create",
  "bd_id": "proj-7hp",
  "title": "…",
  "body": "…",
  "status": "open|in_progress|closed",
  "labels": ["phase-3"],
  "external_id": "42 or null",
  "config": { /* this backend's config block from sync.json */ }
}
```
stdout: the **external id** as a bare string (e.g. `42`, `CHN-101`, `1209…`).
On `create`, mint the item and return its id. On `update`/`close`, act on
`external_id` (if it is null, treat as `create`). The dispatcher stores the
returned id in `.cairn/id-map.json` — per-machine state that `/cairn:init`
gitignores (along with `state.json` and `conflicts.json`); `sync.json` is the
only committed `.cairn/` file.

### PULL — `pull`  (tool → bd)

stdin:
```json
{
  "action": "pull",
  "config": { /* backend config */ },
  "items": [ { "bd_id": "proj-7hp", "external_id": "42" }, … ]
}
```
stdout: a **JSON array** of the current external state of those items:
```json
[
  { "bd_id": "proj-7hp", "external_id": "42",
    "title": "…", "body": "…",
    "status": "open|in_progress|closed",
    "updated_at": "2026-06-18T05:31:34Z" }
]
```
- `status` MUST be normalized to `open` / `in_progress` / `closed` (map the
  tool's native states using the config's state/transition map).
- `updated_at` MUST be ISO-8601 UTC. The dispatcher uses it for
  last-writer-wins reconciliation against bd's `updated_at`.
- Omit items you cannot fetch (e.g. deleted remotely); do not fail the whole
  pull for one missing id.

## Secrets

Never read or write secrets to disk. Each adapter reads its API token from an
**environment variable named in its config** (e.g. `"token_env": "JIRA_API_TOKEN"`).
`sync.json` is committed to the repo and contains only the variable *names*.

## Status normalization

| normalized   | meaning                          |
|--------------|----------------------------------|
| `open`       | not started / backlog / to-do    |
| `in_progress`| claimed / active / doing         |
| `closed`     | done / completed / resolved      |

Tools without a native "in progress" (e.g. GitHub Issues, Asana) map only
`open`/`closed`; that is fine.
