# /cairn:config

> Configure cairn — auto-commit, PR scope, the ceilings on an autonomous run,
> and test jobs (writes `.cairn/config.json`, the file you can also edit by
> hand)

## Usage

```text
/cairn:config
```

No arguments. The command reads the current values, asks once, and writes only
what changed.

## Two doors into the same place

This command asks; `.cairn/config.json` is a plain JSON file anyone can edit by
hand. **Both write the same bytes.** The questions are a convenience, never a
second source of truth, and the file is committed like `sync.json` and
`context.json` — it is team config, not machine state.

## What it does

1. **Reads the current values from the script, not from memory:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" list --json
   ```
   Each key carries `value`, `default`, `source` (`file` or `default`),
   `reader` (the executable that reads it) and `effect`. The `elsewhere` array
   names the config cairn keeps in *other* files.
2. **Asks once — one batch, three named sections, current value
   pre-selected.** This mirrors `/gsd:config`, which is also one batch rather
   than a question-at-a-time wizard.
3. **Applies one `set` per changed answer** (`cairn-config.sh set <key>
   <value>`), then reprints the result.
4. **Names both doors and everything else** — where the rest of cairn's config
   lives, read from the `elsewhere` array rather than typed from memory.

## The keys

| Section | Key | Effect |
| --- | --- | --- |
| Bookkeeping | `bookkeep.auto_commit` | After `cairn-bookkeep.sh --apply` updates the roadmap and requirements, does cairn make the commit or leave the staged change for you? |
| Bookkeeping | `ship.pr_scope` | When a pull request comes due: `phase` · `milestone` · `none` |
| Autonomous run | `autonomous.max_parallel` | Ceiling on how many phases `cairn-parallel.sh batch` runs at once. It is a ceiling on **human attention**: each phase gets its own worktree and agent, and three is about what one person can review before the review becomes a rubber stamp. |
| Autonomous run | `autonomous.max_cycles` | How many cycles an autonomous run may take before `batch` stops selecting. `0` means no ceiling. |
| Tests | `test.jobs` | The `-j` the composed test command runs with. Unset uses as many jobs as there are CPUs. |
| Delivery | `git.control_branches` | Which branch(es) work has to reach before it counts as delivered — comma-separated, because gitflow really does keep two at once (`develop` **and** `main`). Empty means the question was never answered, and `cairn-land.sh` falls back to detecting it while saying so. |

Enum keys refuse anything outside their vocabulary with exit `3` — the command
never invents a fourth option.

## Where the rest of cairn's config lives

| File | Command |
| --- | --- |
| `.cairn/sync.json` | [`/cairn:sync-config`](./sync-config.md) |
| `.cairn/context.json` | [`/cairn:context-config`](./context-config.md) |
| `cairn.enabled` in `.planning/config.json` | the capability's activation switch, read by `cairn-loop-gate.py` |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Read or written |
| `2` | A key that is not in the schema (a bug in the prompt, not in your answer) |
| `3` | `list`: the config file on disk is not readable JSON — the named error is relayed and nothing is overwritten. `set`: an invalid value; nothing was written and the previous value stands. |

A wizard that overwrites an unreadable file destroys whatever was in it, which
is why exit `3` on read stops the flow rather than starting fresh.

## What is deliberately not here: the sync push

There is no question for `cairn.sync_push`, and that is a decision rather than
an oversight. **Measured:** the key is declared in `capability.json:43`,
documented in three prompt fragments and asserted in `tests/capability.bats`,
and it is read by **no executable code** — the push after a bd write is decided
solely by the existence of `.cairn/sync.json` with an enabled backend
(`cairn/hooks/post-bd-write.sh:126-152`).

A knob here would write a value the hook ignores; wiring the hook to honor it
would silently **stop** pushes that happen today for everyone who already has a
`sync.json`. That changes what the software decides, not how it does it. The
decision has an address instead of being left as silence: `bd show CairnGo-gbu`
carries the measurement and the three possible outs.

## Files it touches

- `.cairn/config.json` — written (committed, not machine state)

## See also

- [Command reference](../commands.md) — every `/cairn:` command
