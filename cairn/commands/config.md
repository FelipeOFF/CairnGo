---
description: Configure cairn — auto-commit, PR scope, the ceilings on an autonomous run, and test jobs (writes .cairn/config.json, the file you can also edit by hand)
group: config
---

Set cairn's own knobs. There are **two doors into the same place**: this
command asks, and `.cairn/config.json` is a plain JSON file anyone can edit by
hand. Both write the same bytes — the questions here are a convenience, never
a separate source of truth.

## 1. Read the current values

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" list --json
```

Everything you pre-select below comes from that output — from the script, not
from memory. Each key carries `value`, `default`, `source` (`file` or
`default`), `reader` (the executable that reads it) and `effect`. The
`elsewhere` array names the config cairn keeps in other files; show it in
step 4.

Exit codes: `0` ok; `3` the config file on disk is not readable JSON — relay
the named error and stop, because a wizard that overwrites an unreadable file
destroys whatever was in it.

## 2. Ask once, not one question at a time

**One** `AskUserQuestion` batch, grouped into three named sections, with the
current value **pre-selected** in each. This mirrors `/gsd:config`, which is
also one batch with the current value pre-selected — the user already knows
the shape, and mirroring costs less than inventing.

Sections and questions (the `header` field carries the section name on the
first question of each group):

### Bookkeeping
- **Auto-commit** (`bookkeep.auto_commit`) — after `cairn-bookkeep.sh
  --apply` updates the roadmap and the requirements, does cairn make the
  commit, or does it leave the staged change for you?
  Options: *Leave it to me* (`false`) · *Commit it* (`true`).
- **Auto-merge** (`ship.auto_merge`) — does `/cairn:implement` merge the
  pull request itself once the last CI gate closes green (`true`), or stop
  at ready for review and leave the merge to you (`false`, the default)?
- **PR scope** (`ship.pr_scope`) — when does a pull request come due?
  Options: *Once per phase* (`phase`) · *Once per milestone* (`milestone`) ·
  *Never* (`none`).

### Autonomous run
- **Phases at once** (`autonomous.max_parallel`) — the ceiling on how many
  phases `cairn-parallel.sh batch` selects to run at the same time. It is a
  ceiling on human attention: each selected phase gets its own worktree and
  its own agent, and three is about what one person can review before the
  review becomes a rubber stamp.
  Options: *1 (sequential)* · *3 (default)* · *5* · *8*.
- **Cycle ceiling** (`autonomous.max_cycles`) — how many cycles an autonomous
  run may take before `batch` stops selecting anything. `0` means no ceiling.
  Options: *No ceiling* (`0`) · *5* · *10* · *20*.

### Tests
- **Parallel jobs** (`test.jobs`) — the `-j` the composed test command runs
  with. Leave it unset and it uses as many jobs as there are CPUs.
  Options: *As many as there are CPUs* (`null`) · *2* · *4* · *8*.

### Language
- **Response language** (`agents.response_language`) — the language every
  subagent the cairn lifecycle spawns writes its user-facing output in: its
  report back, the SUMMARY it produces, the questions it asks. Code,
  identifiers, file paths and commands are unaffected. Any language name is
  accepted; the default is English.
  Options: *English* (the default) · *Portuguese* · *Spanish* · *Other* (ask
  for the name).

  **Read `source` from step 1 before offering this one.** If it reads
  `planning`, `.planning/config.json:response_language` already carries a
  value and **that value governs** — GSD's key outranks this one, because it
  is read by GSD's own workflows as well as by cairn, and honoring the
  narrower key would make cairn's subagents answer in one language while
  GSD's answer in another in the same run. Say so instead of offering a
  choice that will not take effect, and point at `/cairn:config` for changing
  it.

Describe each option by its **effect**, in one line, rather than by the key
name alone. Never invent a fourth option for a key whose type is an enum: the
script refuses anything outside `phase|milestone|none` with exit 3.

## 3. Apply, one `set` per changed answer

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" set <key> <value>
```

Only for the answers that actually changed. Exit codes: `0` written; `2` a key
that is not in the schema (a bug in this prompt, not in the user's answer);
`3` an invalid value — nothing was written and the previous value stands.

Then reprint the result so the user sees what the file now says:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" list
```

## 4. Close by naming both doors, and everything else

Tell the user, in one line each:

- `.cairn/config.json` is the file that was just written, it is **committed**
  like `sync.json` and `context.json` (it is team config, not machine state),
  and editing it by hand reaches exactly the same place this command does;
- where the rest of cairn's config lives — read the `elsewhere` array from
  step 1 rather than typing the list from memory: `.cairn/sync.json`
  (`/cairn:sync-config`), `.cairn/context.json` (`/cairn:context-config`), and
  `cairn.enabled` inside `.planning/config.json`, the capability's activation
  switch, which stays with GSD's config and is read by `cairn-loop-gate.py`;
- and, if the language was among the answers: setting it here also wrote
  `.planning/config.json:response_language`, when that file exists — one
  answer reaching both the cairn side and the GSD side, rather than two
  places to keep in agreement by hand. The `set` output says whether the
  propagation happened and why not, when it did not.

## What is deliberately NOT here: the sync push

There is no question for `cairn.sync_push`, and there is no such key anywhere
any more. Measured before it was removed: the key was declared in
`capability.json`, documented in three prompt fragments and asserted in
`tests/capability.bats`, and read by **no executable code**. The push after a
bd write is decided solely by the existence of `.cairn/sync.json` with an
enabled backend (`cairn/hooks/post-bd-write.sh:126-152`).

A button here would have written a value the hook ignores, and wiring the hook
to honor it would silently **stop** pushes that happen today for everyone who
already has a `sync.json`. No default rescues that: `true` makes the key mean
nothing, `false` breaks pushes in silence. That is a change to what the
software decides, not to how it does it.

**Decided (bd issue `CairnGo-gbu`): the declaration was deleted rather than
implemented.** Behaviour after the removal is byte for byte what it was
before — the hook still decides the push by the existence of the sync file —
and a promise nothing kept is gone. If the user asks how to turn the mirror
push on or off, the answer is `/cairn:sync-config` and the backends in
`.cairn/sync.json`, not a knob here.
