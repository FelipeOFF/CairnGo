# Contributing to cairn

## Ground rules

- **Thin glue.** cairn never forks, vendors or patches GSD, beads or
  context-mode. Integration goes through their sanctioned surfaces only:
  the GSD capability manifest, the `bd` CLI (`--json`), the `ctx_*` tools.
- **Scripts over prose.** Anything deterministic (validation, generation,
  gating, sync) is a CLI script in `cairn/scripts/`, invoked by the prose
  commands. If a SKILL.md sentence can be a script check, make it one.
- **Generated artifacts stay generated.** `NN-BEADS-MAP.md` content between
  the `<!-- cairn:generated:start -->` / `<!-- cairn:generated:end -->` markers
  is written only by `cairn-map.sh`.

## Repo layout

| Path | What |
|---|---|
| `cairn/commands/*.md` | `/cairn:*` slash commands (prose, thin wrappers) |
| `cairn/skills/*/SKILL.md` | conventions the agent follows |
| `cairn/hooks/` | Claude Code hooks (SessionStart, PostToolUse, Stop) |
| `cairn/scripts/` | deterministic CLI scripts — the tested surface |
| `cairn/adapters/*.py` | sync adapters (stdin/stdout contract: `adapters/_contract.md`) |
| `tests/` | bats suite + fixture helpers |

## Tests

```bash
bats tests/
```

- Requires [bats-core](https://github.com/bats-core/bats-core) and, for the
  integration tests, a real `bd` binary (`brew install beads`). Tests that
  need `bd` skip cleanly when it is missing.
- The seam: tests invoke scripts by their CLI against disposable fixture
  repos (see `tests/helpers.bash` — `make_gsd_fixture`, `make_bd_fixture`)
  and assert on files, exit codes and `bd list --json`. Never test script
  internals; never reach into `.beads/` storage.
- Every new script ships with a `.bats` file. Every bug fix in a script
  ships with the test that would have caught it.

## Style

- Shell: bash, `set -euo pipefail`, shellcheck-clean.
- Python: stdlib only (the sync layer must run anywhere Claude Code runs).
- Prose commands/docs: English, match the surrounding voice.
- Commits: Conventional Commits (`feat(cairn): …`, `fix(sync): …`).

## Releasing

1. Bump `version` in `cairn/.claude-plugin/plugin.json`.
2. Update `CHANGELOG.md`.
3. Tag `vX.Y.Z` on `main`.
