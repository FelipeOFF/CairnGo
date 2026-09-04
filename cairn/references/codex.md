# Cairn on Codex

The Codex plugin includes a native skill for every Cairn command, plus the
general `cairn` and `cairn-sync` skills. All reuse the scripts, templates and
command bodies shared with Claude Code and Grok. Codex prefixes each skill
name with `cairn:`. Use these native entries even if Codex also imports legacy
commands as `source-command-*` skills.

## Dispatch

For a command skill such as `$cairn:grill`, the verb is already selected:
treat the following text as its arguments. Read the matching command below
and follow it with this page's adaptations.

The general `$cairn:cairn <verb> [arguments]` entry still works. Without a
verb, route by the user's intent and the pipeline in the general skill.

| Codex invocation | Command (relative to this page) |
|---|---|
| `$cairn:init [target-dir]` | [cairn-init.md](../commands/cairn-init.md) |
| `$cairn:grill [ref]` | [cairn-grill.md](../commands/cairn-grill.md) |
| `$cairn:implement [ref]` | [cairn-implement.md](../commands/cairn-implement.md) |
| `$cairn:status [flags]` | [cairn-status.md](../commands/cairn-status.md) |
| `$cairn:doctor [flags]` | [cairn-doctor.md](../commands/cairn-doctor.md) |
| `$cairn:sync-config` | [cairn-sync-config.md](../commands/cairn-sync-config.md) |
| `$cairn:sync-pull [flags]` | [cairn-sync-pull.md](../commands/cairn-sync-pull.md) |

Translate suggested `/cairn-<verb>` commands back to `$cairn:<verb>` when
replying. `init` is the bootstrap exception to the `.beads/` gate.

## Paths and shell calls

Resolve the plugin directory from the **loaded** `skills/<name>/SKILL.md`:
two parent directories above its skill folder.
It contains `scripts/`, `commands/`, `templates/` and this `references/` folder.
Resolve symlinks first. Do not assume the user's current directory is CairnGo.

Use this absolute directory as `PLUGIN_ROOT` and set `CAIRN_PLUGIN_ROOT` to it
in **each** shell tool call that follows a command body. This keeps the loaded
version ahead of a stale `.cairn/plugin-root` from another harness. Shell
exports do not persist across calls. Replace `$ARGUMENTS` with the user's
actual arguments, individually shell-quoted; Codex does not interpolate it.
Run project commands in the target repository, without a login shell.

## Tools and lifecycle

- `Bash` → the available shell tool (`exec_command` / `shell_command`).
- `Read` / `Write` / `Edit` → file reads and `apply_patch`.
- `AskUserQuestion` / `ask_user_question` → `request_user_input_async` when
  available; otherwise `request_user_input` only in a mode that permits it.
  An async call is not an answer: wait for the user's reply before advancing
  a dependent interview round or writing the spec. If neither is available,
  ask one question in prose and wait, as the grill command specifies.
- `Agent` / `Task` → available collaboration tools, only when delegation is
  authorized. Otherwise implement the frontier sequentially. Track work on
  `bd`, including when a referenced skill suggests a local task list.

Use the Matt skills when installed. If absent, follow the bundled command
and [matt-on-beads.md](matt-on-beads.md); do not invent a missing tool or skill.
For ticketing, create small end-to-end slices with acceptance criteria and
explicit blockers, then implement the unblocked frontier.

Do not depend on Claude's `PostToolUse` matcher for Codex shell calls. Run the
documented sync action after a successful bd write when sync is enabled and
authorized. Avoid duplicating an action already performed by an active hook.
Plugin installation does not grant permission to commit, push or sync; use
the repository's active profile and the user's authorization.
