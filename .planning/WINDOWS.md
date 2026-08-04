---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-08-04T01:44:05.715Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 29 | todo | cairn/scripts/cairn-config.py |  | Tres chaves entraram no schema com leitor NOMEADO mas ainda nao implementado (bookkeep.auto_commit, ship.pr_scope -> 29-02; test.jobs -> 29-06). Se o ciclo fechar com alguma delas nao lida, a chave deve ser apagada — e o estado exato do cairn.sync_push. | open |  | 2026-08-04T01:44:05.715Z |  |

````json
[
  {
    "id": 1,
    "kind": "todo",
    "phase": "29",
    "file": "cairn/scripts/cairn-config.py",
    "line": null,
    "description": "Tres chaves entraram no schema com leitor NOMEADO mas ainda nao implementado (bookkeep.auto_commit, ship.pr_scope -> 29-02; test.jobs -> 29-06). Se o ciclo fechar com alguma delas nao lida, a chave deve ser apagada — e o estado exato do cairn.sync_push.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-04T01:44:05.715Z",
    "resolved_at": null
  }
]
````
