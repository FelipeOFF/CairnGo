---
description: The local live board — one stdlib server per repo on 127.0.0.1, the status board refreshed as the tracker moves, plus what is running now, what needs attention, the Jira links, and the bd command to copy
argument-hint: <start [--port N] | stop | open | status>
group: view
---

Run the live board under the `cairn` conventions. `$ARGUMENTS` picks the
verb; with none, `status`.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-board.sh" start [--port N] [--open]
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-board.sh" stop
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-board.sh" open
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-board.sh" status
```

- **`start`** launches one server for this repo in the background, bound to
  `127.0.0.1` only, on `--port` or a free port, and records it in
  `.cairn/board.json` (gitignored). Print the URL it reports. A server that
  is already running is reused — say so and print its URL; do not start a
  second. Exit `4` names a busy port; exit `5` means bd or the status script
  is unavailable.
- **`stop`** ends it and removes the record. After a plugin upgrade the
  running server still executes the previous version's files: `stop` then
  `start`.
- **`open`** opens the URL in the browser; **`status`** says whether the
  pid in the record is alive.

The page is the same board `cairn-status.sh --html` renders — one renderer,
refreshed by polling (5 s while something runs, slower when idle, paused in
a hidden tab) — plus the blocks a snapshot cannot carry: what is running
now (leases, the journal's last moves across the repo's worktrees), what
needs attention (open `gh:run` gates, blocked work, the next action), the
cycle's Jira links, and per row both a copy button with the exact `bd`
command and an action button that runs it: claim, close (with a reason),
gate check and resolve, lease release, and **stop** — the request a running
`/cairn:autonomous` or `/cairn:implement` honours at its next boundary
(`.cairn/stop`, never a kill); the block says "stop requested" until the
lease goes. Two more blocks close the page: **trend** (cairn-trend's
first-pass verdict per cycle, and closed-per-day per phase of the open cycle,
drawn inline) and **CI** — `gh run list` for the current branch and the open
`gh:run` gates, fetched by this process only and only when
`git.review_state` is `gh`; off, the block says `CI desligada —
/cairn:config git.review_state gh`. Every action is the deterministic
CLI run by the server with `BEADS_ACTOR=board`, mirrored through gbsync
when `.cairn/sync.json` exists, and logged to `.cairn/board.log`; a `POST`
from any page that is not this board's own port is refused (403). `GET
/api/status` is `cairn-status --json` verbatim, for anything else that
wants the model.
