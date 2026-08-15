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

Every network call MUST carry an explicit timeout (30s in all five bundled
adapters) and MUST turn every transport failure — HTTP status, DNS/refused,
timeout, unparseable body — into a nonzero exit with a one-line reason on
stderr. A traceback is a contract violation, and a request with no timeout
hangs the whole dispatcher (and the prose command that called it) on one dead
socket. An adapter that shells out to a CLI (github: `gh`) is bound the same
way: the CLI reaches the network on the adapter's behalf, so an unbounded
`subprocess.run` is an unbounded network call.

The bundled adapters expose the value through a `CAIRN_<TOOL>_TIMEOUT` env
var (`CAIRN_JIRA_TIMEOUT`, `CAIRN_GITLAB_TIMEOUT`, …) — a test seam first,
and an escape hatch for a slow self-hosted instance second. `tests/gbsync.bats`
proves the bound against a socket that really hangs, and an AST scan there
fails if any call site loses its `timeout=`.

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

### IMPORT — `import`  (tool → bd, one-shot adoption) — *optional*

Adopts items that already existed in the tool before sync was wired (PULL only
covers ids already in `id-map.json`, which PUSH populates — so pre-existing
cards are otherwise unreachable). Currently implemented by `jira.py` only;
adapters that don't support it simply fail the action (nonzero exit), which
the dispatcher reports.

stdin:
```json
{
  "action": "import",
  "config": { /* backend config */ },
  "query": "native query string (e.g. JQL) or null",
  "project": "project key or null"
}
```
`query` wins when set; otherwise the adapter derives its default query from
`project` (falling back to the config's project key). `project` is
interpolated into a native query, so an adapter MUST validate it against the
tool's own key shape (jira: `^[A-Z][A-Z0-9_]{1,30}$`) and fail loud on
anything else — arbitrary query syntax belongs in `query`, where it is the
declared input.

stdout: a **JSON array** of the matched items, normalized exactly like PULL
but **without** `bd_id` (none exists yet):
```json
[
  { "external_id": "CHN-101", "title": "…", "body": "…",
    "status": "open|in_progress|closed",
    "updated_at": "2026-06-18T05:31:34Z" }
]
```
The dispatcher mints one bd issue per item (`bd create` + status), records
the pair in `.cairn/id-map.json`, and skips already-mapped external ids, so
re-running an import is idempotent. Adapters MUST paginate and MUST cap the
result at a documented ceiling (jira: 200 per run) — a larger backlog is
imported in slices by refining the query.

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
