---
description: One combined view — plan phases, tracker issue states, drift
---

Show project status:

1. `plan_status()` — phase table: number, name, artifacts present
   (C/R/P/V), issue count.
2. For the active phase (`context_get`), `issue_get` each referenced issue and
   show id · title · state · assignee.
3. `plan_drift()` — append flagged items, each with its one-line remedy
   (missing → recreate + `plan_issues_set`; closed-unverified → verify or reopen).
4. Keep it to one screen; end with the obvious next `/cairn:` step.
