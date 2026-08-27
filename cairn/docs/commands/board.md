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
phase), and per row a **copy** button with the exact `bd` command and an
**action** button that runs it.

**Actions** (`POST /api/action`, `{action, id, reason?}`): `claim`,
`close` (reason required), `reopen`, `gate-check`, `gate-resolve` (reason
required), `lease-release` (`N` or `bead:<id>`), `stop` (`N`, `bead:<id>`,
or nothing for everything — writes `.cairn/stop` through `cairn-stop.py
request` and releases that lease; a running loop reads the flag at its next
boundary and stops clean, never by kill) and `stop-clear`.

**Trend and CI** (phase 51): `GET /api/trend` serves cairn-trend's
first-pass verdict per cycle plus closed-per-day per phase of the open
cycle (from bd `closed_at`; time in DOING is not measured, and the block
says so), drawn as inline SVG. `GET /api/ci` runs `gh run list` for the
current branch and lists the open `gh:run` gates — from this process only,
never from cairn-status or cairn-land, and only when `git.review_state` is
`gh` (cached 60 s in `.cairn/ci-cache.json` with `fetched_at`); off, the
block reads `CI desligada · /cairn:config git.review_state gh`. Each runs the
deterministic CLI as an argv list with `BEADS_ACTOR=board`, mirrors itself
through gbsync when `.cairn/sync.json` exists (the post-bd-write hook only
sees the session's own `bd` commands), appends one line to
`.cairn/board.log`, and invalidates the snapshot so the next poll shows the
write. No token, by decision: the server binds the loopback and refuses
(403) a `POST` whose `Origin`/`Host` are not this board's own port; a local
`curl` without `Origin` passes. The trend and CI blocks arrive in phase 51.
No CDN, no external font, no new dependency.

## Related

- [`/cairn:status`](status.md) — the snapshot, `--html` and `--json`
- [`/cairn:jira`](jira.md) — the links the Jira block shows
