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

Codex normalizes shell calls to `tool_name: "Bash"` and `tool_input.command`
for `PostToolUse`; the shared hook handles these writes automatically when
sync is configured. If hooks are inactive, run the documented sync action
explicitly after an authorized successful bd write. Avoid duplicating an
action already performed by a hook.
Plugin installation does not grant permission to commit, push or sync; use
the repository's active profile and the user's authorization.


## Hook context and output

The three registered hooks use `scripts/cairn-hook-context.py`. Detection
prefers the current payload over inherited environment variables, in order:

1. Grok's `hookEventName` (`session_start`, `post_tool_use`, `stop`).
2. Codex's `turn_id` (Stop and PostToolUse).
3. Grok's `GROK_HOOK_EVENT`, `GROK_SESSION_ID`, `GROK_WORKSPACE_ROOT` or
   `GROK_PLUGIN_ROOT`.
4. Codex's `PLUGIN_ROOT` or `CODEX_THREAD_ID`.
5. Claude Code's `CLAUDECODE`; otherwise `unknown`.

`CLAUDE_PLUGIN_ROOT` is a compatibility alias injected by all three runtimes,
so it locates the hook in the shared manifest but does not identify the agent.
No per-run setup is needed. Grok's camelCase tool fields override snake_case
aliases; its terminal tool names join `Bash` in the PostToolUse matcher.

The payload's `cwd` selects the project. Without it, Grok uses
`GROK_WORKSPACE_ROOT`, `GROK_PROJECT_DIR`, then `CLAUDE_PROJECT_DIR`; Claude
and unknown use `CLAUDE_PROJECT_DIR`; Codex uses the working directory.
The working directory is the final fallback. From there, the nearest ancestor
with `.beads/` or `.git` (file or directory) selects the project root. A nested
repository without beads stops the search, so it never inherits its parent's
tracker. If no marker exists, the selected directory stays unchanged.
Background sync jobs retain that resolved project.
Native `PLUGIN_DATA` / `GROK_PLUGIN_DATA` take priority
over `CLAUDE_PLUGIN_DATA` for the matching runtime.

Stop is silent when clean and otherwise emits one JSON `systemMessage`,
combining issue and lease warnings without blocking or closing issues. This
is also the safe fallback for an unknown agent. SessionStart emits one
`hookSpecificOutput` with `hookEventName: "SessionStart"` and
`additionalContext` for Codex, Claude Code and unknown. Grok's SessionStart
Observe gate extracts only `systemMessage`, so it receives the same reminder
in that field. PostToolUse queues emit one `systemMessage`. Plain text
beginning with `[cairn]` would be treated as malformed JSON by Codex.

The Stop schema was checked against [Codex 0.153.3](https://github.com/openai/codex/blob/rust-v0.153.3/codex-rs/hooks/src/schema.rs),
[Claude Code's JSON contract](https://code.claude.com/docs/en/hooks#json-output),
and [Grok's hook runner](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-hooks/src/runner/command.rs).
Stop must not emit `hookSpecificOutput` or a blocking `decision`.
