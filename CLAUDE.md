# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->


## Build & Test

**A suíte completa roda na CI, não bloqueando a sessão.** São 1161 testes em 51
arquivos; em série passa de uma hora e a execução inteira para junto. A CI já
existe para isso: `.github/workflows/ci.yml` roda a suíte em toda
`pull_request`, com `--jobs 4`, mais o lint de python e o validador de
capability.

A regra, então:

1. **Sempre exista uma PR aberta para o trabalho corrente** — a da fase contra
   a branch de milestone, ou a de milestone contra `main`. Todo push nela
   dispara a suíte.
2. **Empurre e siga trabalhando.** Não espere o verde parado. Depois do push,
   deixe um monitoramento da CI rodando em background e vá para a próxima
   tarefa (ou continue a atual).
3. **O vermelho interrompe, o verde não precisa ser esperado.** Quando a CI
   falhar, pare o que estiver fazendo e conserte antes de empilhar mais
   trabalho por cima de uma base que não se sabe verde.

```bash
# Empurrar e monitorar sem bloquear
git push -u origin <branch>
gh pr create --base <branch-alvo> --fill   # uma vez por frente de trabalho
gh run watch "$(gh run list --branch <branch> --limit 1 --json databaseId -q '.[0].databaseId')"
```

**Localmente, use a porta da casa, nunca `bats` cru:**

```bash
bash cairn/scripts/cairn-test.sh --jobs 8 tests/           # a suíte inteira
bash cairn/scripts/cairn-test.sh --jobs 8 tests/<arquivo>.bats   # um arquivo
```

`cairn-test.sh` resolve a contagem de jobs, confere o que `bats -j` precisa
ANTES de compor o comando, e repassa o exit code do bats sem traduzir. Chamar
`bats` direto perde as três coisas — e sem GNU parallel no PATH o `bats -j`
executa ZERO testes e sai 1, que é uma suíte que não rodou se passando por
suíte que rodou.

Rodar arquivos avulsos localmente durante o desenvolvimento é certo e barato
(os 4 arquivos de uma onda levam ~16s a `-j 8`). O que não se faz é gastar a
sessão esperando a suíte completa em série.

## Architecture Overview

_Add a brief overview of your project architecture_

## Conventions & Patterns

_Add your project-specific conventions here_
