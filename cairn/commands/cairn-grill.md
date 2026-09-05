---
description: Interview until the spec is sharp, write it on a spec bead, stop
argument-hint: "[ref]"
---

Grill only. Do **not** implement code. Do **not** create tickets. Do **not** skip the interview because the idea looks obvious.

Read `${PLUGIN_ROOT}/skills/cairn/SKILL.md` and `${PLUGIN_ROOT}/references/matt-on-beads.md`. Then run the **grilling** skill (rounds: frontier questions, recommended answer on each, wait). Domain terms go on the spec `design`, never on `CONTEXT.md` or `docs/adr/`.

`PLUGIN_ROOT` = `$CAIRN_PLUGIN_ROOT` or `$GROK_PLUGIN_ROOT` or `$CLAUDE_PLUGIN_ROOT` or `head -1 .cairn/plugin-root`.

`$ARGUMENTS` is optional `ref` (bd id, spoke key, `m-vX.Y`, title).

## Ask through the harness — not in chat prose

Every interview question goes through the harness question tool. A `❓ Q1` markdown block in the assistant message is an **error** for this command.

| Harness | Tool |
|---|---|
| Claude Code | `AskUserQuestion` |
| Grok | `ask_user_question` (the Ask tool) |
| Codex | `request_user_input_async`, or `request_user_input` when the current mode allows it |

Put the recommended option first and append `(Recommended)` to its label. Independent frontier questions may share one tool call. A question that depends on an unanswered one waits for the next round.

On Codex, follow `references/codex.md`. An async question remains pending
until the user replies; sending it or waiting for a while is not an answer.

Do **not** write `--description` / `--design` (and do **not** say the spec is done) until the frontier is empty and the user has answered through that tool.

If the tool is missing from this session, say which harness you are on and that the Ask tool is unavailable, then ask **one** question in prose and wait. That fallback is last resort, not the default.

## Resolve ref

Empty → new spec. Else the same order as `/cairn-implement`: `bd show`, spoke key, `m-*`, title search.

## Do

| what you resolved | action |
|---|---|
| nothing / idea | create a spec bead (`--type=epic`, `--metadata '{"cairn":{"kind":"spec"}}'`). Interview via the Ask tool. Write `--description` and `--design` (`## GLOSSARY`, `## ADR`). Stop. |
| spec with empty or thin description | interview on that bead via the Ask tool; `bd update --description` / `--design`. Stop. |
| spec that already has a body | show the body. Ask via the Ask tool whether to reopen the interview or run `/cairn-implement <id>`. Do not start coding. |
| ticket | this is the wrong door. Name `/cairn-implement <id>`. |

When the frontier is empty, print the spec id and:

```
Spec is on bd. Next: /cairn-implement <id>
```

After each `bd create` / `bd update`, PUSH if sync is enabled:

```bash
bash "${PLUGIN_ROOT}/scripts/gbsync.sh" create|update <id>
```
