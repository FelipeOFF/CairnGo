# Contributing to cairn

## Ground rules

- **Thin glue.** Specs and tickets live on `bd`. Optional spokes (Jira,
  GitHub, GitLab, Asana, Azure Boards) go through `cairn/adapters/`
  (`adapters/_contract.md`). Matt's grill / to-spec / to-tickets skills are
  orchestrated, not vendored.
- **Scripts over prose.** Anything deterministic (validation, generation,
  gating, sync) is a CLI script in `cairn/scripts/`, invoked by the prose
  commands. If a SKILL.md sentence can be a script check, make it one.

## Repo layout

| Path | What |
|---|---|
| `cairn/commands/cairn-*.md` | hyphenated slash commands (`/cairn-implement`, …) |
| `cairn/skills/*/SKILL.md` | conventions the agent follows |
| `cairn/references/` | addenda (Matt-on-beads, …) |
| `cairn/templates/` | tracker docs copied into a project by init |
| `cairn/hooks/` | Claude Code / Grok hooks (SessionStart, …) |
| `cairn/scripts/` | deterministic CLI scripts — the tested surface |
| `cairn/adapters/*.py` | sync adapters (stdin/stdout contract: `adapters/_contract.md`) |
| `cairn/docs/` | full guides |
| `tests/` | bats suite + fixture helpers |

## Tests

```bash
bash cairn/scripts/cairn-test.sh          # the runner
bats tests/                               # still works, always will
```

The runner does two things `bats tests/` does not: it picks the job count
(`--jobs N`, else `test.jobs` in `.cairn/config.json`, else your core count),
and it checks what `bats -j` actually needs *before* composing the command —
dropping `-j` and telling you why when a prerequisite is missing. It is
convenience, never a gate: `bats tests/` is the same suite and stays
supported. `cairn-test.sh --print-command` prints the exact command it would
run, and runs nothing.

- Requires [bats-core](https://github.com/bats-core/bats-core), `jq`, and,
  for the integration tests, a real `bd` binary (`brew install beads`).
  Tests that need `bd` skip cleanly when it is missing.
- **Optional:** GNU `parallel` (`brew install parallel` /
  `apt-get install parallel`). Without it, `bats -j` does **not** fall back
  to serial; it runs zero tests and exits 1, which is why the runner removes
  the flag rather than passing it
  through. `cairn-doctor.sh` reports its absence as a warning, never a
  failure.
- The seam: tests invoke scripts by their CLI against disposable fixture
  repos (see `tests/helpers.bash` — `make_gsd_fixture`, `make_bd_fixture`)
  and assert on files, exit codes and `bd list --json`. Never test script
  internals; never reach into `.beads/` storage.
- Every new script ships with a `.bats` file. Every bug fix in a script
  ships with the test that would have caught it.
- Prose commands delegate to scripts: new deterministic behavior ships as a
  script in `cairn/scripts/` plus its bats file, never as prose only.

## Style

- Shell: bash, `set -euo pipefail`, shellcheck-clean.
- Python: stdlib only (the sync layer must run anywhere Claude Code runs).
- Prose commands/docs: English, match the surrounding voice.
- Commits: Conventional Commits (`feat(cairn): …`, `fix(sync): …`).

## Releasing

1. Bump `version` in `cairn/.claude-plugin/plugin.json`.
2. Update `CHANGELOG.md`.
3. Tag `vX.Y.Z` on `main`.
