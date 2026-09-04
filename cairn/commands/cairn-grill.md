---
description: Interview until the spec is sharp, write it on a spec bead, stop
argument-hint: "[ref]"
---

Grill only. Do **not** implement code. Do **not** create tickets. Do **not** skip the interview because the idea looks obvious.

Read `${PLUGIN_ROOT}/skills/cairn/SKILL.md` and `${PLUGIN_ROOT}/references/matt-on-beads.md`. Then run the **grilling** skill (rounds: frontier questions, recommended answer on each, wait). Domain terms go on the spec `design`, never on `CONTEXT.md` or `docs/adr/`.

`PLUGIN_ROOT` = `$CAIRN_PLUGIN_ROOT` or `$GROK_PLUGIN_ROOT` or `$CLAUDE_PLUGIN_ROOT` or `head -1 .cairn/plugin-root`.

`$ARGUMENTS` is optional `ref` (bd id, spoke key, `m-vX.Y`, title).

## Resolve ref

Empty → new spec. Else the same order as `/cairn-implement`: `bd show`, spoke key, `m-*`, title search.

## Do

| what you resolved | action |
|---|---|
| nothing / idea | create a spec bead (`--type=epic`, `--metadata '{"cairn":{"kind":"spec"}}'`). Interview. Write `--description` and `--design` (`## GLOSSARY`, `## ADR`). Stop. |
| spec with empty or thin description | interview on that bead; `bd update --description` / `--design`. Stop. |
| spec that already has a body | show the body. Ask whether to reopen the interview or run `/cairn-implement <id>`. Do not start coding. |
| ticket | this is the wrong door. Name `/cairn-implement <id>`. |

Use the harness question UI when it exists. One round can hold several independent questions; do not implement between rounds.

When the frontier is empty, print the spec id and:

```
Spec is on bd. Next: /cairn-implement <id>
```

After each `bd create` / `bd update`, PUSH if sync is enabled:

```bash
bash "${PLUGIN_ROOT}/scripts/gbsync.sh" create|update <id>
```
