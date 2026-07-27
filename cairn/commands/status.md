---
description: Render the status board — READY / DOING / BLOCKED lanes from bd, GSD position, one next action
argument-hint: "[--brief] [--json] [--plain] [--width N] [--max-rows N] [--ascii] [--color=always|never] [--planning-dir <dir>]"
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
- Full contract (degradation thresholds, `--max-rows`, `--ascii`, `--color`,
  `NO_COLOR`): see the docstring in `scripts/cairn-status.py`.
