---
description: Pull-request state for this project's phases — the one cairn surface that talks to the forge, behind a switch that is off by default
argument-hint: "[fetch [--pr N]] [show] [--json]"
group: view
---

Show what the forge says about the pull requests this project's history names.
This is **pull-request state, not code review** — nothing here reads a diff or
comments on one.

## 1. The switch is off by default, and `off` is an answer

`git.review_state` in `.cairn/config.json`: `off` (default), `gh`, or `glab`.
With `off` this command reads one config key, touches nothing else, and exits
`3` — no network, no file, no cache. That is the answer, not an error: say so
plainly and offer the switch rather than working around it.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" set git.review_state gh
```

Only turn it on when the user asks for it. This is the single place in cairn
that opens a socket, and every other surface — the status board included —
stays offline by construction.

## 2. Show what is already cached

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-review.sh" show $ARGUMENTS
```

Reads `.cairn/pr-cache.json`, which is per-machine state (gitignored, like
`.cairn/state.json`). **Every entry carries the age of the fetch that produced
it, and you always print that age.** A pull-request state with no age is worse
than no state at all, because it looks current.

## 3. Fetch, when the user wants it fresh

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-review.sh" fetch
```

The numbers come from `cairn-land.sh report --json` — the pull requests the
local history actually names. This command invents no number and re-reads no
git. `--pr N` asks about a number the history does not carry, for the case
where somebody knows it.

Exit `3` also covers "there is no pull request to ask about": the history names
none. Report that as the local history's silence — never as "the pull request
does not exist", which is a claim about the forge that an absent reference
cannot support.

Exit codes: `0` ok; `2` usage; `3` nothing to do (the switch is off, or there
is nothing to ask about); `5` a script or binary it depends on is unavailable
— `cairn-config.py`, `cairn-land.py`, or the `gh`/`glab` the switch names.

Related: `/cairn:land` answers the offline half — did the work reach the
control branch, and which pull request the history names.
