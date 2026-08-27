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
   a branch de milestone (`/cairn:implement <N>` abre essa PR como draft, a
   partir da branch em que você está, quando `ship.pr_scope=phase`), ou a de
   milestone (`feat/vX.Y/<slug>`) contra `master`. Todo push nela
   dispara a suíte.
2. **Todo push prende o bead seguinte a um gate `gh:run`.** A espera pela CI é
   estado rastreado, não disciplina de memória: com o gate aberto, o bead
   bloqueado não aparece em `bd ready`, então ninguém empilha trabalho sobre
   base que não se sabe verde por esquecimento.
3. **Siga trabalhando no que já está aberto** — quem espera é o gate, não você.
   E o vermelho continua interrompendo: `bd gate check` só fecha o gate quando a
   run sai `completed` + `success`. CI vermelha deixa o gate aberto e o bead
   seguinte fora do `ready` até você consertar.

```bash
# empurrar (dispara a CI)
git push -u origin <branch>
gh pr create --base <branch-alvo> --fill   # uma vez por frente de trabalho

# prender o próximo bead à CI desta push
bd gate create --type=gh:run --blocks <bead-seguinte> --reason="CI de <branch>"
bd gate discover    # casa a run por branch+SHA; repita se a run ainda não subiu

# antes de pegar o próximo trabalho
bd gate check --type=gh:run   # verde fecha o gate, vermelho o mantém aberto
bd ready

bd gate list                            # gates abertos
bd gate resolve <gate-id> -r "<motivo>" # destravar à mão (run recriada, push refeito)
```

**Em `--await-id`, só ID numérico de run é seguro.** Um nome de workflow
(`--await-id=ci.yml`) é aceito, mas esse hint dispara `gh run list
--workflow=ci.yml` **sem filtro de branch** — medido em 2026-08-15 com bd 1.1.0:
o gate casou com a run de outra branch e teria fechado com o verde alheio. Não
passe `--await-id` na criação; deixe o `bd gate discover` casar por branch e SHA.

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

**O runner pina o `HOME`.** Cada `bd` enfileira um evento de métricas anônimas
em `~/.beads/eventsData` (medido 2026-08-27: 259.653 arquivos `.evtq`, 1,0 GB —
a fila do `bd metrics`, não histórico de issue; o bd a drena sozinho quando
alcança a rede). O único interruptor que o bd honra é
`~/.config/bd/config.yaml` (`metrics.disabled`), então `cairn-test.sh` roda o
bats com `HOME` num diretório próprio (`$TMPDIR/cairn-test-home-<uid>`, com o
`.tool-versions` copiado e as métricas desligadas) e exporta
`CAIRN_TEST_HOME`. Na sua máquina, `bd metrics off` desliga de vez, e
`rm -rf ~/.beads/eventsData` é seguro — é só a fila.

## Architecture Overview

_Add a brief overview of your project architecture_

## Conventions & Patterns

_Add your project-specific conventions here_
