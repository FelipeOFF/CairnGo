---
phase: 23-not-applicable-as-a-check-state
subsystem: infra
tags: [python, bats, cli, stdlib, doctor, false-green, not-applicable]
requirements: [VOID-01, VOID-02, VOID-03]
plans: 4
status: complete
---

# Phase 23: Not-applicable as a check state — Summary

**O doctor parou de dar verde sobre o que não checou.** Uma checagem que não teve o
que comparar agora diz isso, com o símbolo `⊘`, com a família do vazio e com a frase
que nomeia o insumo que faltou — em vez de reportar `✓ ok` e ser contada como
sucesso. E a contagem de órfãs históricas, que crescia a cada milestone, voltou a
zerar ao fim de um ciclo.

## O defeito, e por que ele era grave

Medido em 2026-08-03, logo depois de arquivar o v1.4: com o `ROADMAP.md` sem nenhuma
fase, o doctor reportava um board **perfeitamente verde**. Três checagens passavam
por não ter o que comparar. O `orphans` era o caso mais claro: dizia
`77 issue(s), no orphans` um minuto depois de ter reportado 26 órfãs, com o mesmo
número de issues, porque um `if roadmap_phases:` pulava a comparação inteira e caía
no ramo de sucesso.

Nenhuma das checagens estava errada isoladamente — de fato não havia o que comparar.
Juntas produziam a forma exata de sinal falso que o v1.4 existiu para eliminar: um
verde que não distingue "comparei e está consistente" de "não comparei nada".

**A medição do planejamento corrigiu o tamanho do problema:** o doctor tem **dezoito**
checagens desde a fase 29, não dezesseis, e **nove das dezoito** aprovavam sem ter
comparado nada — não três.

## Os quatro critérios do ROADMAP, e como cada um foi provado

**1. `not-applicable` é estado distinto de `ok`, e o rodapé conta os dois
separadamente.** Feito no plano 01, como fatia vertical. O rodapé passou a **contar**
os quatro baldes em vez de derivar o de sucesso por subtração — que era o lugar exato
onde um quarto estado nasceria já contado como verde. Os baldes são as chaves do
próprio mapa de símbolos, então um status sem símbolo não tem onde ser contado e
`die()` em vez de cair no balde de sucesso.

**2. Um roadmap vazio não lê como saudável.** Provado no plano 03, ponta a ponta: um
repositório cujo ROADMAP não lista fase nenhuma passou a produzir rodapé `INCOMPLETE`,
com `req-issue` e `orphans` dizendo que não compararam nada — e código de saída
continua `0`, de propósito.

**3. `orphans` para de sinalizar issue fechada de milestone arquivado, e um teste
arquiva um ciclo e afirma que a contagem zera.** Feito no plano 04. Neste repositório
a contagem caiu de **61 para 0**, e o veredito diz `+61 closed issue(s) of archived
milestone(s) exempted`. A prova é diferencial: o mesmo repositório, com as mesmas
issues, rodado duas vezes, com uma única variável entre as rodadas — se o ROADMAP
arquivado do ciclo está em `.planning/milestones/`.

**4. Cada checagem que ganha o estado novo diz o que faltou para ela poder checar.**
Feito nos planos 02 e 03, e fechado na varredura do 04. O `claims-stale`, que exibia
`✓ ok` desde sempre sem nunca ter rodado, hoje diz:
`cannot check — STATE.md's frontmatter carries no 'active_phase'`.

## O que a fase entregou, plano a plano

| plano | entrega |
|---|---|
| 23-01 | o quarto estado `not-applicable` (símbolo `⊘`), o campo `scope` com duas famílias, e o rodapé contando quatro baldes em vez de subtrair |
| 23-02 | os cinco ramos que já diziam "not applicable" em prosa passaram a dizê-lo no campo `status`, e as oito anotações que o arquivo carregava prometendo esta fase foram quitadas |
| 23-03 | o idioma da contagem zero decidido checagem a checagem — nove avaliadas, cinco convertidas, quatro mantidas `ok` com a razão escrita ao lado; `check_orphans` com os dois eixos separados no código |
| 23-04 | a isenção do `orphans` por milestone arquivado, o teste de invariante do vocabulário, e o fecho do contrato na página e no consumidor autônomo |

## As duas famílias do vazio, e por que a distinção existe

Uma contagem zero significava duas coisas diferentes, e tratá-las como uma só teria
trocado um defeito por outro:

- **`out-of-scope`** — o insumo nunca vai existir para esta classe de repositório e
  nada está errado (os manifestos do próprio cairn, num repositório que não é o
  cairn). Permanente, ordinário, e deixa o relatório completo.
- **`no-input`** — o insumo **deveria** existir dado o que o repositório já tem, então
  a ausência é um vão que alguém pode fechar (um `STATE.md` presente mas sem
  `active_phase`; um `ROADMAP.md` presente mas sem fase). Só esta limpa o `ok` de topo.

A razão da divisão foi **medida**: o fixture saudável da própria suíte é o repositório
de um usuário, sem os manifestos do cairn, e três checagens são ausentes ali por
construção. Fazer toda ausência significar "incompleto" teria entregado a todo
repositório de usuário um **falso vermelho permanente** — o mesmo defeito do falso
verde, espelhado.

## A varredura final das dezoito checagens

Oito das dezoito podem devolver o quarto estado: sete com `no-input`, uma
(`release-versions`) com `out-of-scope`, uma (`req-ledger`) com `out-of-scope`, e a
`test-parallel` é a única que usa as duas famílias, por razões diferentes em ramos
diferentes. A tabela completa, checagem a checagem, está no
[23-04-SUMMARY.md](23-04-SUMMARY.md).

## O que impede a fase de ser desfeita sem ninguém perceber

A fase pode ser revertida de um jeito silencioso: alguém acrescenta um quinto estado
sem passar por aqui. O plano 04 acrescentou um teste de invariante que não afirma nada
sobre nenhuma checagem em particular — afirma sobre o vocabulário. Subtrair os quatro
estados da lista de status deixa o conjunto vazio; todo `not-applicable` carrega
escopo de uma das duas famílias e nada mais carrega escopo; e a soma dos quatro
contadores é igual ao número de checagens registradas.

## O que a fase deliberadamente NÃO fez

- **Não alargou o código de saída 7.** Recusado por escrito na D-04 do CONTEXT. Uma
  entrada ausente é atrito, não inconsistência, e um `7` gasto com atrito para de
  significar alguma coisa. Um relatório `INCOMPLETE` sai `0`; quem quer saber "posso
  confiar neste verde" lê `.ok`, não o código de saída.
- **Não converteu as quatro checagens que a contagem zero deixa genuinamente
  verdadeiras** (nenhuma lease parada *porque nada está leaseado*, nenhum rótulo sem
  par *porque todo rótulo tem par*). Cada uma carrega, ao lado do retorno, o comentário
  que começa com *"Phase 23 evaluated and KEPT `ok`"* e diz por quê — sem ele, daqui a
  seis meses a decisão seria indistinguível de omissão.
- **Não tocou em render nem no `cairn-status.py`** — território da fase 21.
- **Não isentou trabalho vivo.** A isenção do `orphans` exige três condições ao mesmo
  tempo, e **todos** os rótulos de milestone arquivados, nunca algum. Issue aberta de
  ciclo fechado, issue fechada sem rótulo de milestone e issue carregada para o
  milestone ativo continuam avisando, cada uma provada por teste de contorno.

## Achados fora do escopo, medidos e não consertados aqui

**A falha de `phase-corroboration` na própria fase 23.** O relatório deste repositório
sai com exit 7 porque o disco reporta a fase como `executed` — existe SUMMARY — enquanto
as issues seguem abertas. É o defeito **FIX-05**, conserto da fase 25. Não foi tocado
nesta fase, e o exit 7 deste repositório não é resultado dela.

**`lease-stale` e `maps-fresh` se movem por efeito de relógio e de claim**, não de
código desta fase. Registrado nos SUMMARY dos planos 01 e 04 justamente para que a
mudança de contadores entre duas rodadas não seja creditada à fase por engano.

## Um defeito que a própria fase criou, e que a passada completa pegou

O plano 23-02 deu o quarto estado a `release-versions` e `test-parallel` — o estado
ordinário de um repositório que não é o cairn — e deixou vermelha uma asserção irmã do
`lease-stale`, escrita quando só havia três estados, que perguntava se alguma outra
checagem estava `!= "ok"`. `!= "ok"` é satisfeito por `warn` **e** por
`not-applicable`: era o idioma que esta fase existe para remover, sobrevivendo dentro
da suíte da própria fase.

Ele passou despercebido por dois planos e foi encontrado no 23-04, na primeira passada
completa de `tests/cairn-doctor.bats`. Medido contra o código do commit `9a9e0d7`, numa
worktree separada, para provar que era anterior ao plano 04 e não efeito dele. A
asserção foi consertada perguntando pelo valor exato (`warn` ou `fail`) e fixando os
dois `⊘` por id e por família — ficou mais forte do que era.

A lição fica registrada: uma fase que muda o vocabulário de status precisa varrer as
asserções que testam *outra* coisa e leem status de passagem.

## O que a fase deliberadamente deixou para o operador

A escrituração — `ROADMAP.md`, `REQUIREMENTS.md` e `STATE.md` — **não** foi tocada por
esta execução. O fechamento da fase é do operador, por `cairn-bookkeep close 23 --apply`.

## Verificação

`tests/cairn-doctor.bats` inteiro, pelo runner da casa: anunciado `1..96`, executado
96, **96 ok, 0 not ok, 0 skips, exit 0** — contado sobre o log inteiro. A suíte completa do
repositório roda uma vez, ao fim, sob responsabilidade do operador — decisão medida:
a suíte inteira em primeiro plano excede o limite do harness e é morta, e uma fase
irmã ficou 135 minutos num laço de morte-e-retentativa sem avançar um commit.

Efeito medido neste repositório, checagem a checagem:

```
antes   warn  orphans  ::  61 orphan issue(s)
depois  ok    orphans  ::  122 issue(s), no orphans (+61 closed issue(s) of archived milestone(s) exempted)

antes   ok    claims-stale  ::  (nunca havia rodado)
depois  ⊘     claims-stale  ::  cannot check — STATE.md's frontmatter carries no 'active_phase'
```
