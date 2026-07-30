# Roadmap: CairnGo

## Milestones

- ✅ **v1.1 Metrics & Benchmarks** — Phases 1-6, shipped 2026-07-27 · [archive](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 GSD Core** — Phases 7-9, shipped 2026-07-28 · [archive](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Status Panel** — Phases 10-12, shipped 2026-07-28 · [archive](./milestones/v1.3-ROADMAP.md)
- 🚧 **v1.4 Honest State** — Phases 13-17, em andamento

## Milestone: v1.4 Honest State 🚧

**Um estado que prova o que afirma**

Hoje o cairn decide em que pé está uma fase perguntando se quatro nomes de arquivo
existem. Nunca abre o arquivo, nunca pergunta ao bd, nunca pergunta ao git. Trabalho
feito na mão, por outro agente ou por outra ferramenta é invisível — e o inverso
também: uma fase pode estar marcada como pronta sem nada construído. Este milestone
troca essa leitura única e frágil por uma corroborada, torna visível quando dois
agentes estão na mesma fase, e guarda o histórico do que de fato aconteceu.

O padrão para qualquer critério aqui é o nome do próprio milestone: um sinal que
reporta sucesso sem provar sucesso não conta como pronto.

## Phases

### 🚧 v1.4 Honest State — um estado que prova o que afirma (Phases 13-17)

- [ ] Phase 13: State corroboration (CORR-01, CORR-02, CORR-03, CORR-04, CORR-05, CORR-06, CORR-07, CORR-08)
- [ ] Phase 14: Phase card (CARD-01, CARD-02, CARD-03, CARD-04)
- [ ] Phase 15: Phase lease (LEASE-01, LEASE-02, LEASE-03, LEASE-04, LEASE-05)
- [ ] Phase 16: Transition journal (JOUR-01, JOUR-02, JOUR-03, JOUR-04, JOUR-05)
- [ ] Phase 17: Semantic escalation (ESC-01, ESC-02, ESC-03, ESC-04)

## Detalhe das fases

### Phase 13: State corroboration

**Goal:** o estado de uma fase deixa de ser um palpite do sistema de arquivos e passa
a ser um veredito em que quatro fontes independentes votaram, onde a discordância é
nomeada e uma fonte que não deu para ler diz isso em vez de concordar.

**Requirements**: CORR-01, CORR-02, CORR-03, CORR-04, CORR-05, CORR-06, CORR-07, CORR-08

**Success criteria:**

1. `/cairn:status --json` carrega, por fase, a alegação de cada fonte mais um
   veredito `ok` / `conflict` / `unknown` — enquanto `disk_state` mantém seus quatro
   valores, seu tipo e seu significado para quem já consome o JSON hoje.
2. Uma fase cujo SUMMARY.md existe mas cujas issues no bd seguem abertas renderiza
   `conflict` nas três superfícies (terminal, `--json`, HTML), nomeando as duas
   alegações — não uma das duas escolhida em silêncio.
3. Com o bd inalcançável, toda fase afetada reporta `unknown` e nenhuma reporta
   concordância. Provado por teste que força a falha, não por leitura do código.
4. `/cairn:ship` recusa um milestone que contenha fase em `conflict`, e
   `/cairn:autonomous` não a seleciona como próxima.
5. O corpus de diferenças sabidamente inócuas (mapa regenerado, mtime, reordenação de
   chaves em JSON) produz zero conflitos, cada entrada com sua justificativa escrita;
   e uma issue fechada passa a registrar o PR que a fechou, com backfill que recupera
   o vínculo na história já publicada sem reescrever commit.

**Research durante o planejamento:** não precisa. Estende `phase_model()`, função já
existente e bem entendida, com um padrão (condições no estilo Kubernetes) que dois
métodos de pesquisa independentes validaram.

**Depende de:** nada. É a raiz do milestone.

---

### Phase 14: Phase card

**Goal:** toda superfície passa a dizer o que a fase É e por onde ela passou, nas
mesmas palavras — hoje o card mostra número, título e estado, e o terminal mostra
menos que o HTML.

**Requirements**: CARD-01, CARD-02, CARD-03, CARD-04

**Success criteria:**

1. Cada card nomeia o propósito da fase, se houve research, planos feitos/total,
   issues fechadas/total e o veredito da verificação.
2. Board no terminal e página HTML renderizam os mesmos campos a partir da mesma
   leitura — provado por um teste que renderiza os dois e compara, não por inspeção.
3. Uma fase à qual falta um artefato diz qual falta, em vez de omitir a linha e
   deixar a ausência parecer ausência de informação.
4. O card nomeia o que a fase espera e o próximo comando, com a razão de estar
   naquela posição na ordem.

**Research durante o planejamento:** não precisa. Os dados já estão todos no disco
(`RESEARCH.md`, `CONTEXT.md`, `SUMMARY.md`, `VERIFICATION.md`, ROADMAP, bd) — falta
lê-los.

**Depende de:** Phase 13 — o card renderiza, entre outras coisas, o que a corroboração
computa.

---

### Phase 15: Phase lease

**Goal:** dois agentes na mesma fase vira fato visível antes do trabalho começar, em
vez de descoberta reativa no meio da execução, id por id.

**Requirements**: LEASE-01, LEASE-02, LEASE-03, LEASE-04, LEASE-05

**Success criteria:**

1. `/cairn:work N` numa fase segurada por outro actor vivo reporta quem segura e desde
   quando, em vez de seguir em silêncio.
2. Um lease tomado numa worktree é visível a partir de uma segunda worktree do mesmo
   repositório — o cenário exato para o qual a feature existe.
3. Um lease cuja sessão morreu é reportado como obsoleto pelo doctor e pode ser
   liberado; ele nunca vira bloqueio permanente.
4. A liberação acontece uma vez por fase, tenha a verificação passado ou falhado, e
   uma sessão morta à força não deixa lease que ninguém consiga limpar.

**Research durante o planejamento:** precisa de um item. Foi medido nesta sessão que
`bd list` a partir de uma worktree devolve as issues do repositório principal sem
criar banco local, sem daemon e sem registry global. Falta confirmar o caminho de
**escrita**: um `bd update` feito de uma segunda worktree cai no mesmo banco? Se não
cair, o lease herda o problema de invisibilidade e o desenho precisa de um gatilho de
sync explícito.

**Depende de:** Phase 13 — um lease sem sinal visível no board falha o próprio
requisito.

---

### Phase 16: Transition journal

**Goal:** o histórico do que realmente aconteceu sobrevive a uma queda e consegue
explicar um conflito, sem nunca virar autoridade sobre o estado corrente.

**Requirements**: JOUR-01, JOUR-02, JOUR-03, JOUR-04, JOUR-05

**Success criteria:**

1. Toda transição registra actor, instante, fase e evento; uma queda no meio da
   escrita deixa uma linha isolada, reportada com sua posição, e tudo antes dela ainda
   é lido.
2. O relatório de conflito cita quando cada lado se moveu pela última vez, extraído do
   journal.
3. Apagar o journal não muda veredito nenhum — a corroboração continua detectando uma
   edição feita fora dos comandos do cairn, que o journal nunca viu.
4. A compactação produz um estado comprovadamente idêntico ao replay completo.

**Research durante o planejamento:** não precisa. O idioma JSONL append-only já tem
precedente neste código, no journal resumível do `cairn-migrate.py`, e as perguntas de
armazenamento e autoridade foram fechadas na pesquisa.

**Depende de:** Phase 15 — os primeiros eventos de verdade a registrar são aquisição e
liberação de lease.

---

### Phase 17: Semantic escalation

**Goal:** quando as fontes discordam, uma investigação lê código, história e memória e
**propõe** uma reconciliação; aplicar é ato humano, e a investigação é incapaz de
gravar estado por construção, não por instrução.

**Requirements**: ESC-01, ESC-02, ESC-03, ESC-04

**Success criteria:**

1. Um `grep` sobre o caminho de análise não encontra nenhum verbo de escrita do bd, e
   um teste roda esse caminho contra um fixture e afirma que nada mutou.
2. A investigação roda apenas sobre conflito detectado — um teste afirma zero
   invocações numa passada em repositório onde tudo concorda.
3. A proposta nomeia, para cada alegação, o arquivo e a linha em que ela se apoia, e
   uma checagem confirma que o texto citado está mesmo lá.
4. Aplicar é comando separado, invocado por humano, que enumera cada mudança antes de
   fazer qualquer uma.

**Research durante o planejamento:** precisa. O esquema de verificação de citação
(confirmar mecanicamente que a evidência citada existe no arquivo apontado) não tem
precedente neste código.

**Depende de:** Phase 13 (precisa de conflito real para disparar) e Phase 16
(idealmente cita histórico ao propor).

---

## Cobertura

26 requisitos v1, 26 mapeados, 0 sem fase. Cada requisito pertence a exatamente uma
fase — ver a tabela de rastreabilidade em `REQUIREMENTS.md`.

## Ordem de dependência

```
13 ──┬──> 14
     ├──> 15 ──> 16 ──┐
     └────────────────┴──> 17
```

13 primeiro porque não exige I/O novo (a lista de issues do bd já é buscada antes de
`phase_model()` rodar) e porque tudo o mais depende dela. 14 e 15 podem correr lado a
lado depois de 13. 17 por último por construção: precisa de um conflito real sobre o
que operar.

Trabalho aberto e sem fase vive no beads (`bd ready`), não aqui.
