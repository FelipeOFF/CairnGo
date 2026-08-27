# /cairn:board

> The local live board — one stdlib server per repo on 127.0.0.1, the status board refreshed as the tracker moves, plus what is running now, what needs attention, the Jira links, and the bd command to copy

## Usage

```text
/cairn:board start [--port N]
/cairn:board stop
/cairn:board open
/cairn:board status
```

## What it does

`cairn-board.sh start` launches a stdlib HTTP server for this repo — bound
to `127.0.0.1`, on `--port` or a free port — and records `{port, pid, url,
plugin_root, started_at}` in `.cairn/board.json` (gitignored, one server per
checkout). `stop` ends it, `open` opens the URL, `status` says whether it is
alive. An already-running server is reused, never doubled; a busy `--port`
is exit 4.

The page is the **same board** `cairn-status.sh --html` renders: every
refresh is one `cairn-status.py --json --html` call, cached for a few seconds,
whose JSON is served at `/api/status` and whose generated region is served
at `/api/fragment`. The page polls — 5 s while a lease is held or something
is in DOING, 15 s idle, 30 s after five quiet minutes, paused while the tab
is hidden — and swaps the fragment only when it changed. On top of the
board, the live blocks: **now** (held leases, the last journal moves across
the repo's worktrees), **attention** (open `gh:run` gates, blocked work,
the next action), **Jira** (the cycle's story and epic, one sub-task per
phase), and a **copy** button per row with the exact `bd` command.

Read only in this phase: nothing on the page writes; `POST` is 405. Actions
arrive in phase 49, the trend and CI blocks in phase 51. No CDN, no
external font, no new dependency; the process never reaches the network.

## Related

- [`/cairn:status`](status.md) — the snapshot, `--html` and `--json`
- [`/cairn:jira`](jira.md) — the links the Jira block shows
