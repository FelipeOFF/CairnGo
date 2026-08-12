---
phase: 27-disagreement-trend-across-cycles
subsystem: cli
tags: [trend, milestones, verification, not-applicable, intersection, ambiguity, derivation]

plans: 3
requirements: [TREND-01, TREND-02]
beads: [CairnGo-s56, CairnGo-tsv]

provides:
  - "cairn-trend.py / cairn-trend.sh: a série da discordância entre ciclos, com os vãos declarados"
  - "quatro estados de ciclo, herdando o vocabulário que a fase 23 entregou"
  - "eixos derivados da interseção computada do disco, e o `score` reprovado com a unidade medida"
  - "a regra dos três pontos (exit 4) e a contiguidade reportada à parte"
  - "a declaração de ambiguidade qualidade×escrutínio, derivada do namespace `verifier_*`"
  - "duas guardas mecânicas contra o quarto precedente de número escrito à mão"
affects: [ship, milestone]

actuals:
  plans: 3
  tasks: 6
  commits: 7
  tests: 34

status: complete
---

# Phase 27: Disagreement trend across cycles Summary

A série existe, tem três pontos e dois vãos declarados, e **sai com a ambiguidade
declarada ao lado dela** — porque uma taxa de primeira aprovação que cai é
indistinguível, a partir do próprio número, entre a qualidade caindo e o escrutínio
subindo.

## O que a fase entrega

`cairn-trend.py` e o par `.sh`, com `tests/cairn-trend.bats` (34 testes). Contra a
árvore real:

```
[cairn-trend] · v1.1  veredito em 6/6 fases    gaps_found 2 · passed 4
[cairn-trend] ⊘ v1.2  not-applicable / no-frontmatter
[cairn-trend]         3 arquivos de verificação, nenhum com frontmatter —
                      o insumo existe, o formato não
[cairn-trend] ⊘ v1.3  not-applicable / no-frontmatter
[cairn-trend] · v1.4  veredito em 6/7 fases    gaps_found 2 · human_needed 1 · passed 3
[cairn-trend] · v1.5  veredito em 7/10 fases   gaps_found 3 · human_needed 1 · passed 3

[cairn-trend] ! v1.5 está em andamento: a cobertura dele conta fases que ainda não
                começaram, então não se compara com a de um ciclo fechado.

[cairn-trend] ▸ série: 3 pontos comparáveis em 5 ciclos, 2 vãos — não contígua
[cairn-trend] ▸ primeira aprovação   67% → 50% → 43%       desce
[cairn-trend] ▸ lacunas registradas  2 → 2 → 4             sobe
[cairn-trend] ▸ lacunas por fase     0.33 → 0.33 → 0.57    sobe
[cairn-trend] ▸ overrides aplicados  0 → 0 → 0             constante
[cairn-trend] ⊘ score não vira série: as unidades do denominador diferem entre os
                ciclos comparáveis — as frações não se comparam

[cairn-trend] ! a direção de `primeira aprovação` é ambígua na raiz, e este comando
                não a resolve. […] Leia a linha como "o par qualidade×escrutínio
                mudou", nunca como "a qualidade caiu".
```

## Os critérios de sucesso do roadmap

**1. Um comando de leitura mostra a evolução ao longo dos milestones arquivados.**
Cumprido. Os ciclos são descobertos do disco — o `vN-ROADMAP.md` arquivado e o
marcador `🚧` — e a série carrega quatro eixos.

**2. Todo número vem de artefato arquivado; nenhum é digitado à mão.** Cumprido, e
**provado por mecanismo, não afirmado**: um teste extrai todo token numérico da saída
humana e exige que cada um exista como valor no `--json`, em dois alvos, com controle
negativo. Isso só é possível porque o render não computa nada — toda porcentagem
nasce formatada no modelo.

**3. Com dado insuficiente o comando diz isso e não desenha uma linha.** Cumprido com
exit próprio (4) e sem direção nenhuma na saída. Provado nas duas direções: remover o
terceiro ponto mata a direção, acrescentá-lo a faz nascer, sem prosa editada.

## O trabalho real: a linha é verdadeira e ambígua

`67% → 50% → 43%` é uma queda real. Ela move por duas causas opostas que o número não
distingue: a qualidade caindo, ou o escrutínio subindo. **Um comando que desenha essa
linha sem dizer isso mente com número verdadeiro** — não é aprovar sem checar, é medir
certo e concluir errado.

A declaração não é uma frase impressa. O comando pergunta ao disco se existe chave do
namespace `verifier_*` comum a todo ciclo comparável, não acha nenhuma, e é dessa
ausência que a declaração nasce. Acrescentar a chave a todos os ciclos vira o veredito
para `resolvable` e a declaração desaparece — o que é teste. Um aviso que sai sempre
seria ruído que ninguém lê, e continuaria mentindo no dia em que o dado desambiguasse.

## Quatro correções ao contexto

**1. A varredura de milestones não está no `cairn-bookkeep.py`.** O `<code_context>`
a atribui a ele; ela vive em `cairn-doctor.py:649`, e o bookkeep não menciona
`milestones` uma vez sequer (`grep -c` = 0). Como o doctor está fora do escopo e a
casa não tem lib compartilhada, o asset é reusável como **forma**, não por import.

**2. `deferred` não é um campo do v1.1 — o esquema oscilou.** O D-02 o atribui ao
v1.1. Medido, e agora reportado pelo próprio comando em `fields.missing_from`:
`deferred` está no v1.1 **e no v1.5**, e falta no v1.4. Só `has_blocking_gaps` é
exclusivo de um ciclo. O esquema não derivou em linha reta: um campo sumiu e voltou,
o mesmo padrão do frontmatter inteiro, um andar abaixo.

**3. `score` é o candidato que precisa ser reprovado.** O contexto o lista entre os
candidatos a eixo por estar na interseção. Ele está — na interseção de **presença**.
A unidade do denominador muda: v1.1 conta `must-haves`, v1.5 conta `critérios`, e o
v1.4 usa **as duas réguas dentro de si**. Ligar `15/15 must-haves` a `4/4 critérios`
seria uma linha entre réguas diferentes: o mesmo defeito que a fase existe para
nomear, um andar abaixo do lugar onde ela o esperava.

**4. A cobertura do v1.4 não é 6 de 6.** O `19-ship-v1-4` tem diretório de fase e
nenhum `VERIFICATION.md` — o ciclo fechou com uma fase sem veredito. A série do
contexto não mostra isso porque conta arquivos, não fases; a cobertura é dado
separado e o comando a exibe.

## O que a fase se recusou a fazer

- **Retro-preencher o v1.2 e o v1.3.** Inventar veredito sobre trabalho que ninguém
  verificou daquele jeito é o que o TREND-02 proíbe. Os vãos ficam, com escopo
  nomeado e motivo escrito.
- **Desambiguar automaticamente.** Requer registrar a versão do verificador junto do
  veredito, e o contexto já o difere por escrito. O que a fase entrega é o comando
  dizendo que não sabe, e dizendo exatamente o que faria com que soubesse.
- **Classificar gaps por "mecanismo versus registro".** É julgamento humano lido em
  prosa livre; um classificador aqui inventaria o dado que a fase declara ausente.
- **Página em `cairn/docs/commands/`.** Sem comando slash, uma página ali seria
  reportada como órfã pelo `cairn-wrap.py docs`. O contrato mora no docstring, que a
  casa declara canônico.
- **Tocar `cairn-status.py` ou `cairn-doctor.py`.** Nenhuma linha em nenhum dos dois.

## A guarda que pegou o próprio autor

A segunda guarda proíbe contagem viva sobre o repositório fora do bloco de medição
datado, no `.py` e no `.sh`. Na primeira execução ela reprovou **duas linhas do meu
próprio docstring** — `"v1.2 and v1.3 have three verification files each"` e
`"vanished for two cycles"`. Era o quarto precedente desta casa nascendo dentro do
commit que existe para impedi-lo. Corrigido: a prosa descreve o mecanismo, as
contagens ficaram onde a data as protege.

## Verificação

`bash cairn/scripts/cairn-test.sh --jobs 4 tests/cairn-trend.bats` — **34/34**, lido
do log inteiro com a marca de fim conferida no arquivo.

Quatorze quebras aplicadas ao fonte ao longo dos três planos, cada uma com o vermelho
atribuído ao seu teste e o restauro feito por cópia (`cp`), nunca por
`git checkout --`. Duas guardas ficaram cegas na primeira versão e foram consertadas
por causa dessa medição: o teste-âncora do denominador (que somava um agregado imune à
contaminação) e a guarda de docstring (que marcava definição como contagem).

`git diff --quiet HEAD -- .planning/ROADMAP.md .planning/REQUIREMENTS.md
.planning/STATE.md` — limpo. Nenhum commit desta fase tocou os três.

## Achado de processo

Outra sessão commitou nesta mesma árvore durante a execução do 27-03 e arrastou meus
arquivos para dentro de dois commits sobre `PROJECT.md` (`2c618d3`, `3b04940`). O
conteúdo está íntegro e a suíte roda verde depois do fato; o que se perdeu foi a
atribuição. Não reescrevi histórico — isso exige autorização explícita, e com outra
sessão ativa na mesma árvore um force-push destruiria trabalho concorrente. Detalhes
e hashes no `27-03-SUMMARY.md`.

## Known Stubs

Nenhum. Nada foi entregue com valor fixo, lista escrita à mão ou caminho não
implementado.
