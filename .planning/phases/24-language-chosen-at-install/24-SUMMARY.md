---
phase: 24-language-chosen-at-install
subsystem: config
tags: [lang, install, subagent, doctor]
requirements: [LANG-01, LANG-02]
beads: [CairnGo-0rk, CairnGo-4ia]
plans: 3
status: complete
metrics:
  duration: "~3h"
  completed: 2026-08-05
  plans_completed: 3
  commits: 12
requirements_status:
  LANG-01: complete
  LANG-02: partial
---

# Phase 24: Language chosen at install — Summary

A linguagem de resposta deixou de ser algo que alguém descobre no meio de um ciclo:
é perguntada na instalação, antes do primeiro subagente, e chega até o prompt de
cada subagente que o lifecycle spawna por mecanismo, não por lembrança.

## O defeito, e por que o critério do LANG-02 era literal

Não é hipotético e não é antigo. No ciclo v1.4 todo subagente que o lifecycle
spawnou respondeu **em inglês** contra um planejamento inteiro em PT-BR. E o que
torna o critério duro: **isso aconteceu com a chave presente e correta**.
`.planning/config.json:69` já dizia `"response_language": "pt-BR"`. Um teste
afirmando "a chave está no `.json`" estaria **verde no dia exato em que quebrou**.

A causa, medida em ~30 arquivos de `~/.claude/gsd-core/workflows/`: a diretiva
padrão do GSD diz literalmente *"Technical terms, code, file paths, **and subagent
prompts stay in English** — only user-facing output is translated"*. Um único
arquivo — `references/execute-phase-response-language.md` (#2402) — manda repassar.
Na maioria dos pontos de spawn, a regra escrita era **não** repassar. O valor
existia; o repasse não.

## O que a fase entregou

**A escolha, na instalação (LANG-01).** `/cairn:init` ganhou o passo 3.5, **antes**
do hand-off para `/gsd:new-project` — porque aquele comando spawna os próprios
subagentes, e perguntar depois dele é perguntar depois de os primeiros subagentes do
projeto já terem errado. Inglês é o default, pré-selecionado e nomeado como tal.
Re-executar o init num projeto que já respondeu não pergunta e não escreve: a
decisão sai do `source` do `get --json`, não de heurística.

**O caminho até o subagente (LANG-02).** O inventário de quem spawna é fechado e
medido — mas o número mudou por causa desta fase, e vale dizer como. Hoje
`grep -rln "subagent\|[Ss]pawn"` sobre `cairn/commands/`, `cairn/skills/` e
`cairn/capability/fragments/` responde **quatro** arquivos: `autonomous.md`,
`reconcile.md`, `init.md` e `config.md`. Os dois últimos entraram na lista porque
**esta fase escreveu a palavra neles** — medido em `git show 6545a5c:` (o commit
anterior à fase), os dois contavam **zero** ocorrências. Nenhum deles spawna: só
descrevem a chave em prosa. Quem spawna continuam sendo dois:

| ponto de spawn | como a língua chega | provado por |
|---|---|---|
| `autonomous.md` passo 3 | campo do payload de `cairn-parallel.py prepare --json` | `tests/cairn-parallel.bats`, lendo a saída do script |
| `reconcile.md` passo 3 | leitura do `cairn-config.sh` antes do spawn | `tests/cairn-reconcile-agent.bats`, ordem de linhas |
| workflows do GSD | `.planning/config.json:response_language` | propagação do `set` + check do doctor |

Os demais comandos do cairn não spawnam nada: delegam a `/gsd:*`.

**Onde a resposta mora, e por que ali.** `.cairn/config.json`, chave
`agents.response_language`, default `"English"`, leitor nomeado
`cairn-parallel.py prepare`. Isto **corrige uma decisão registrada** —
`bd show CairnGo-0rk` traz "DECIDIDO (Felipe, 2026-07-30): reusar
`response_language` do config do GSD, não criar chave de lingua em
`.cairn/config.json`" — e a correção fica escrita em vez de a frase antiga sumir.
Três medições, todas posteriores àquela data:

- **M-1** `gsd-tools query config-set response_language X` **cria** `.planning/`
  quando ela não existe (exit 0, diretório aparece com só `config.json` dentro).
- **M-2** um `.planning/` com só `config.json` faz `cairn-migrate.py classify()`
  (que decide por `planning.is_dir()`) responder **A** em vez de **D** — e
  `init.md:20-22` manda o estado A **parar o init** e desviar para `/cairn:migrate`.
- **M-3** `init.md:153` proíbe por escrito: *".planning/ is created by GSD, not by
  cairn — do NOT create it yourself."*

No instante em que o init pergunta, `.planning/` não existe e não pode ser criado.
A intenção da decisão original — uma pergunta, um dono — é honrada de outro jeito:
a chave do cairn é **subordinada**, não paralela. `.planning/config.json` vence
sempre que estiver setada, e `get --json` devolve `source` (`planning` | `file` |
`default`), então qual das duas governa nunca é adivinhação.

**A ponte, mecânica.** `cairn-config.sh set agents.response_language` escreve também
`.planning/config.json:response_language` — e **só se aquele arquivo já existir**,
nunca o criando. Medido: `json.loads` + `json.dumps(indent=2)` + `\n`, sem
`sort_keys`, faz round-trip byte a byte no `config.json` real de 2096 bytes deste
repositório, então a ordem das chaves do GSD não se mexe.

**A rede.** `cairn-doctor` ganhou o check `response-language`: `warn` quando a
resposta da instalação nunca chegou na chave do GSD, ou quando os dois arquivos
discordam, sempre nomeando o comando exato que fecha. `warn` e nunca `fail` —
divergir não quebra nada mecanicamente, e gastar exit 7 em atrito ensina todo mundo
a ignorar exit 7.

## Deviations from Plan

Todas registradas nos SUMMARYs de plano; as duas que mudaram uma afirmação minha:

1. **O diff da propagação não é de uma linha** (24-02). Acrescentar chave ao fim de
   um objeto JSON põe vírgula na linha que era a última: 1 removida, 2 adicionadas.
   O plano dizia uma. O teste ficou com a forma exata **mais** a metade forte —
   remover a chave nova e comparar `list(items())` com o original, provando que
   nenhuma outra mudou de valor ou de posição.
2. **`context_excerpt` faltava** na minha asserção do conjunto de chaves do bundle
   (24-03). A asserção pegou na primeira execução, que é o trabalho dela.

E uma remoção: o seam `CAIRN_CONFIG` que escrevi no doctor por hábito e **apaguei**,
porque nada o lia. Um seam declarado e lido por nada é o defeito que
`cairn.sync_push` documenta; escrevê-lo "por consistência" criaria o segundo caso.

## Verificação

Refeita ao fechar a fase, uma invocação por arquivo, `--jobs 2`, log inteiro lido em
cada caso — o anunciado **e** o executado, contados sobre o arquivo completo:

| invocação | anunciado | executado | falhas | exit |
|---|---|---|---|---|
| `tests/cairn-config.bats` | `1..29` | 29 | 0 | 0 |
| `tests/cairn-parallel.bats` | `1..41` | 41 | 0 | 0 |
| `tests/cairn-parallel-autonomous.bats` | `1..13` | 13 | 0 | 0 |
| `tests/cairn-init.bats` | `1..11` | 11 | 0 | 0 |
| `tests/cairn-reconcile.bats` | `1..13` | 13 | 0 | 0 |
| `tests/cairn-reconcile-agent.bats` | `1..9` | 9 | 0 | 0 |
| `bats -f "response-language" tests/cairn-doctor.bats` | `1..5` | 5 | 0 | 0 |

Duas coisas que essa tabela corrige de uma versão anterior deste arquivo, e que só
apareceram porque ela foi refeita:

- `tests/cairn-config.bats` anuncia **29**, não 28. O número antigo estava errado.
- **`tests/cairn-doctor.bats` inteiro não tem resultado.** Ele anuncia `1..87`, e
  hoje foi tentado duas vezes — junto com os outros seis e depois sozinho. Nas duas
  o processo foi morto **antes de escrever um único `ok`**, e nas duas o `EXIT=` do
  wrapper nunca chegou ao log. Os 5 da linha filtrada são os que esta fase
  acrescentou e são os que estou reportando; os outros 82 daquele arquivo eu **não
  medi**, e não os estou chamando de verdes. Eles são do escopo da suíte no merge.

### Controles negativos, um por plano

- **24-01:** removida a chave do SCHEMA (cópia por `cp`, restaurada da cópia — nunca
  `git checkout`). Os testes do payload ficaram **vermelhos**, e o que importa é o
  segundo: `jq '.response_language' returned 'null', expected 'English'` — sem a
  feature, o ponto de entrega não carrega a língua.
- **24-02:** removido o bloco de propagação. `.propagated returned 'false', expected
  'true'`. Removido o passo 3.5 do `init.md`: âncora vazia e frase do default
  ausente.
- **24-03:** neutralizadas as duas comparações do check. `status returned 'ok',
  expected 'warn'` nos dois estados defeituosos.

Nenhum destes testes passaria com a feature removida.

### A suíte inteira não foi rodada aqui, e isso é a política

`tests/` inteiro **não roda nesta worktree**. Ele roda uma vez, na árvore principal,
no merge. A tentativa anterior de rodá-lo aqui **não terminou**: anunciou `1..713` e
executou 204 antes de o processo ser encerrado, com o aviso do próprio bats
(`Executed 204 instead of expected 713 tests`). Nunca chamei aquilo de verde, e a
tabela acima não contém nenhum número vindo dele.

E a mesma morte se repetiu hoje, o que vale registrar porque é a medição que fixa o
método: rodar os **sete** arquivos numa invocação só anunciou `1..203` e parou em
**116 ok, 0 falhas**, sem chegar a escrever o `EXIT=` do meu próprio wrapper — o
shell inteiro foi morto, com `load average` em 13,8 numa máquina de 8 núcleos (três
fases desta rodada dividindo a máquina). Os 116 são exatamente a soma dos seis
primeiros arquivos; ela morreu ao entrar no sétimo, `cairn-doctor.bats`, que sozinho
anuncia 87. Um arquivo por invocação é o que sobrevive, e é como a tabela acima foi
medida.

Também corrigi um erro meu de método no meio do caminho: a primeira execução do
`tests/cairn-parallel.bats` foi lida através de um `| tail -40`, o que trunca o log
e é precisamente o jeito de declarar verde o que não se viu. Toda contagem da tabela
acima vem de log inteiro, contado com `grep -c '^ok '` sobre o arquivo completo.

## O que NÃO está provado

**Que o modelo cola o valor no prompt do Task tool.** `bats` não spawna o Task tool
— a fronteira que `cairn/commands/reconcile.md:29-31` e o cabeçalho de
`tests/cairn-reconcile-agent.bats` já registravam antes desta fase. Provado está:
(a) o valor sai do script que monta o prompt, e (b) o bloco delimitado do prompt
manda copiá-lo de lá. A ponte entre as duas é o modelo, e nenhum teste desta fase
afirma o contrário.

**Que o passo 6 do init é de fato re-executado numa instalação real.** É prosa de
comando; a rede contra isso é o check do doctor, que é por que ele existe.

## Requisitos

- **LANG-01** — completo. `/cairn:init` pergunta, com inglês default explícito,
  grava na config local, e não sobrescreve escolha existente. Issue `CairnGo-0rk`
  fechada.

- **LANG-02 — parcial, e a issue `CairnGo-4ia` fica aberta.** O critério é literal:
  *a escolha alcança **todo** subagente spawnado pelo lifecycle, provado por teste
  que lê o valor **no ponto de entrega**, não na config*. Medido contra os testes que
  existem, ele se parte em três, e só o primeiro terço satisfaz a frase inteira.

  **Provado no ponto de entrega — `autonomous.md`.** O ponto de entrega é a saída de
  `cairn-parallel.py prepare --json`, o payload que o passo 3 lê imediatamente antes
  de montar o prompt. `tests/cairn-parallel.bats:231-305` **executa o script** contra
  fixture real e assere sobre o stdout do processo — nunca sobre um arquivo de
  config — em quatro estados: só cairn → `Portuguese`/`file`; GSD setado por cima →
  `Japanese`/`planning`; nenhum dos dois → `English`/`default`; config ilegível →
  `null`/`unavailable`. Mais a render humana, `response language: Portuguese`. Um
  teste que afirmasse "a chave está no `.json`" ficaria verde nos quatro, inclusive
  no dia da quebra do v1.4; estes não ficam.

  **Provado só estruturalmente — `reconcile.md`.** `tests/cairn-reconcile-agent.bats:180`
  assere **ordem de linhas**: o `get agents.response_language` aparece antes do
  spawn do investigador. É forma de comando, não valor entregue. Nenhum teste lê a
  língua na saída daquele caminho.

  **Não provado — os ~30 workflows do GSD.** Que são precisamente os que responderam
  em inglês no v1.4. Toda a cobertura deles é: `set` propaga para
  `.planning/config.json:response_language`, e `cairn-doctor` compara os **dois
  arquivos de config** (`cairn-doctor.py:2022-2116`). Os dois operam sobre config —
  a forma exata que o critério recusa. E a fase mediu por que isso não basta: a
  diretiva padrão do GSD manda literalmente *não* repassar (*"subagent prompts stay
  in English"*), então a chave estar certa não implica que ela chega ao prompt. Foi
  assim que quebrou, com a chave certa.

  O que falta para fechar é um teste que leia o valor na saída do caminho do GSD, ou
  a decisão explícita de que aquele caminho está fora do escopo deste repo — o que
  seria uma mudança de critério, não uma prova dele.

## Commits

| commit | o quê |
|---|---|
| `c2cf776` | contexto da fase, e as três medições |
| `d9544f2` | três planos |
| `95d68d0` | a chave, a precedência e o payload de `prepare` |
| `5af12c9` | o sexto item do prompt do subagente |
| `c6e5e94` | SUMMARY 24-01 |
| `3c630b6` | a propagação para a chave do GSD |
| `a122b41` | a pergunta na instalação, antes do hand-off |
| `4dd84d3` | SUMMARY 24-02 |
| `cf121af` | o investigador recebe a língua; o bundle não é tocado |
| `8744a55` | o check do doctor e o CHANGELOG |
| `2402e18` | SUMMARY 24-03 |
| _este_ | SUMMARY da fase, com a verificação refeita por arquivo |

## Self-Check: PASSED

- Os 11 hashes da tabela acima resolvem por `git cat-file -e <h>^{commit}` nesta
  worktree (`phase/24`, git-dir `…/worktrees/CairnGo-phase-24`).
- Os arquivos citados como prova existem e contêm o que a prosa afirma:
  `tests/cairn-parallel.bats:231-305`, `tests/cairn-reconcile-agent.bats:180`,
  `cairn/scripts/cairn-doctor.py:2022-2116`.
- Toda contagem da tabela de verificação vem de log inteiro em disco, contado com
  `grep -c '^ok '` / `grep -c '^not ok '`, mais o `EXIT=` do wrapper.
- `tests/cairn-doctor.bats` inteiro está declarado **não medido**, não verde.
