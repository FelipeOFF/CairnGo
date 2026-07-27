---
description: Render the status board — READY / DOING / BLOCKED lanes from bd, GSD position, one next action
argument-hint: "[--brief] [--json] [--plain] [--html <path>] [--width N] [--max-rows N] [--ascii] [--color=always|never] [--planning-dir <dir>]"
---

Show the status board. A deterministic script renders it — `bd ready` drives
the lanes, GSD files supply the position, and the output is the answer.

## 1. Render the board

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-status.sh" --width 100 $ARGUMENTS
```

(`--width 100` forces the board renderer at a fixed width — without it a
non-TTY run degrades to the machine-readable `--plain` format. Flags the user
typed are in $ARGUMENTS and pass straight through to `cairn-status.sh`,
overriding the default render.) Present the
board **verbatim** in a fenced code block. Do not paraphrase it, reflow it,
or re-list the issues in prose — the render IS the view. After the fence, add
at most one or two sentences of commentary when something needs explaining
(a blocked chain, a stale claim, a disagreement — see step 3).

What the board shows:

- **READY** — `bd ready`: the truly claimable list. Dependencies, gates, and
  `defer_until` are all respected; in_progress and blocked issues are
  excluded. Say that in one line so the user trusts it.
- **DOING** — in_progress issues (`◆ assignee` when claimed).
- **BLOCKED** — blocked issues (`⧗ id` names the blocking issue; for a deep
  chain the user can ask and you run `bd dep tree <id>`).
- **Footer** — `phase X/Y · milestone · done: N`, then `▶ next:` with ONE
  suggested action, plus a sync-staleness line when `.cairn/sync.json`
  exists and the last pull is missing or older than 24h (offer
  `/cairn:sync-pull`).

## 2. Exit codes

- `0` — board rendered.
- `2` — usage error (bad flag); fix the invocation.
- `5` — **bd unavailable** (not on PATH, or a bd query failed). Never treat
  this as fatal for the user: fall back to a minimal prose view — run
  `/gsd:progress` for the roadmap position and say tracked-issue lanes are
  unavailable until beads is installed
  (https://github.com/gastownhall/beads).

## 3. The next action

The script synthesizes ONE next action (in order: continue an in_progress
issue → highest-priority ready issue labeled `m-<milestone>,phase-<active>` →
STATE.md's `next_action` → highest-priority ready issue overall). When the
bd-ready pick and STATE.md's next action disagree, say so: **bd wins for work
items, STATE.md wins for workflow steps** — "issue X is ready" doesn't
override "phase 3 still needs planning", and vice versa. The `--json` output
carries both (`next` and `next.state_next`) if you need to compare.

## 4. Variants

- User wants the one-glance version → `--brief` (three lines: position,
  counts, next action).
- Scripting / parsing → `--json` (one machine line) or `--plain`
  (tab-separated rows; also the automatic non-TTY default — pipes never
  receive box-drawing or ANSI escapes).
- User wants to *look* at it — a second monitor, a shared page, a browser tab
  they leave open → `--html <path>` (see step 5).
- Full contract (degradation thresholds, `--max-rows`, `--ascii`, `--color`,
  `NO_COLOR`): see the docstring in `scripts/cairn-status.py`.

## 5. The HTML board

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-status.sh" --html status.html
```

Writes a standalone page — the same lanes, position and next action, plus a
topographic profile of the roadmap (one terrain segment per phase, its height
the number of issues that phase carries, ground filled up to where you stand,
a cairn marking it). The page loads nothing from the network, so it works
offline and from a file:// URL.

Report the path, not the markup — never paste the HTML into the conversation.
Say what changed in one line and stop.

Two things to tell the user once, when they first ask for it:

- **The file is theirs outside the markers.** Everything between
  `<!-- cairn:generated:board:start -->` and `<!-- cairn:generated:board:end -->`
  is regenerated; every byte outside it — their CSS edits, their notes, their
  wrapper markup — survives untouched. So re-running the command on the same
  path is safe, and restyling the page is expected. Same contract as
  `NN-BEADS-MAP.md`.
- **Re-run it to refresh.** Nothing watches the repo; the page is a snapshot
  and carries the timestamp it was generated at.

`--html` composes with `--planning-dir` and with `--json` (which reports the
write under an `html` key instead of the confirmation line). It is refused
with `--plain` / `--brief` (exit 2) — those render to stdout, `--html` renders
to a file, and combining them would silently drop one.
