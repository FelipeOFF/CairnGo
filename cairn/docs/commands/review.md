# /cairn:review

> Pull-request state for this project's phases — the one cairn surface that
> talks to the forge, behind a switch that is off by default

## Usage

```text
/cairn:review show          # what is cached, with its age
/cairn:review fetch         # ask the forge about the numbers the history names
/cairn:review fetch --pr N  # ask about a number the history does not carry
/cairn:review --json        # machine-readable
```

Wraps [`cairn-review.py`](../../scripts/cairn-review.py).

**Pull-request state, not code review.** Nothing here reads a diff, writes a
comment, or judges anything. It reports what `gh` / `glab` say about a pull
request's `state`, `title`, `url` and `mergedAt`.

## Why it is a separate command

The status board must stay offline, and that is proved structurally rather than
promised: `tests/cairn-land.bats` asserts the exact number of `subprocess.run`
sites in `cairn-land.py`, and `tests/cairn-tracker-card.bats` does the same for
`cairn-status.py`, none of them a network tool. Moving the fetch into either
file would have to delete those assertions to ship — which is exactly the
conversation that should happen out loud.

```text
cairn-status.py  ->  cairn-land.py  ->  git, and the local cache FILE
cairn-review.py  ->  gh / glab                       (never the reverse)
```

## The switch, and why `off` is an answer

`git.review_state` in `.cairn/config.json`: `off` (default), `gh`, or `glab`.

With `off`, this command reads one config key and touches nothing else — no
network, no file, no cache — and exits `3`. That is the answer, not an error.
Turn it on deliberately:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" set git.review_state gh
```

No token is read, written or printed anywhere in this path; `gh`/`glab` carry
their own auth and cairn never sees it.

## The cache carries its own age, always

`.cairn/pr-cache.json` is per-machine state (gitignored, like
`.cairn/state.json` and `.cairn/id-map.json`). Every entry sits under a
top-level `fetched_at` stamp in ISO 8601 UTC, the reader computes an age from
it, and every surface prints that age beside the state.

A pull-request state with no age is **worse** than no state at all, because it
looks current. So the stamp is not optional.

## Where the numbers come from

`cairn-land.py report --json`, whose `phases[].pr.numbers` is the set of pull
requests the local history actually names. This command invents no number and
re-reads no git: one fact, one owner. `--pr N` skips that read for the case
where somebody knows a number the history does not carry.

When the history names none, `fetch` exits `3`. Report that as the local
history's silence — never as "the pull request does not exist", which is a
claim about the forge that an absent reference cannot support (see
[`/cairn:land`](./land.md) for the measurement behind that rule).

## Exit codes

| Code | Meaning |
|---|---|
| `0` | ok |
| `2` | usage error |
| `3` | nothing to do: the switch is `off`, or there is no pull request to ask about. Not a failure — it is the answer |
| `5` | a script or binary this one depends on is unavailable: `cairn-config.py`, `cairn-land.py`, or the `gh`/`glab` the switch names |

## Files it touches

- `.cairn/pr-cache.json` — written by `fetch`, read by `show`. Per-machine
  state, gitignored.
- `.cairn/config.json` — `git.review_state`, read only.

## See also

- [`/cairn:land`](./land.md) — the offline half: did the work reach the control
  branch, and which pull request the history names
- [`/cairn:config`](./config.md) — where the switch lives
