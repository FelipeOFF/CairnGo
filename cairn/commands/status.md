---
description: One combined view driven by bd ready — actionable, in-flight, blocked, GSD position, one next action
---

Show a single status view. `bd ready` drives it — everything else is context.

1. **Actionable** — `bd ready --json` (a JSON array: id, title, priority,
   labels, `metadata.gsd`). This is the truly claimable list: dependencies,
   gates, and `defer_until` are all respected, and in_progress/blocked issues
   are excluded — say that in one line so the user trusts it.
2. **In flight** — `bd list --status in_progress` (note assignees).
3. **Blocked** — `bd blocked`; for anything listed, show the chain with
   `bd dep tree <id>` (who is waiting on whom).
4. **Roadmap position** — `/gsd:progress`.
5. **Synthesize: ONE suggested next action.** In order:
   - an in_progress issue exists → continue it;
   - else the highest-priority ready issue of the **active phase** — filter
     the ready list by the pair label `m-<milestone>,phase-<active>` (active
     phase from STATE.md, milestone from ROADMAP.md's current header);
   - else the next GSD step from STATE.md's position/next action (e.g. "plan
     phase 3").
   When the bd-ready pick and STATE.md's next action disagree, say so: **bd
   wins for work items, STATE.md wins for workflow steps** — "issue X is
   ready" doesn't override "phase 3 still needs planning", and vice versa.
6. When `.cairn/sync.json` exists, add a one-liner on sync staleness from the
   last-pull watermark in `.cairn/state.json` (stale or missing → suggest
   `/cairn:sync-pull`).

Keep the whole thing tight: a few lines per section, one clear next action.
