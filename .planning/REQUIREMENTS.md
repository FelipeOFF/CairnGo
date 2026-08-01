# Requirements: CairnGo — v1.4 Honest State

**Defined:** 2026-07-29
**Core Value:** Workflow unificado plan→work→ship cujo estado é verificável — nenhuma superfície afirma que uma fase está pronta sem ter com o que corroborar.

## v1 Requirements

Requisitos deste milestone. Cada um mapeia para exatamente uma fase do roadmap.

### Corroboração de estado (CORR)

- [ ] **CORR-01**: O estado de uma fase é derivado de fontes independentes — artefatos em disco, issues do bd, o checkbox do ROADMAP e o `active_phase` do STATE.md — em vez da existência de quatro nomes de arquivo
- [ ] **CORR-02**: Quando as fontes discordam, a fase lê `conflict` e cada fonte tem sua alegação mostrada nominalmente; nenhuma fonte vence em silêncio
- [ ] **CORR-03**: Uma fonte que não pôde ser lida reporta `unknown` e nunca "concorda" — bd fora do ar, clone raso ou comando que falhou jamais produzem verde falso
- [ ] **CORR-04**: `disk_state` e as chaves existentes do `--json` mantêm nome, tipo e significado; a corroboração chega em chaves aditivas
- [ ] **CORR-05**: Uma fase em `conflict` bloqueia o ship gate e sai da seleção de próxima fase do `/cairn:autonomous`
- [ ] **CORR-06**: `/cairn:doctor` ganha uma checagem de corroboração que reporta as fases em conflito e roteia cada achado para sua correção
- [ ] **CORR-07**: Diferenças sabidamente inócuas (mapa regenerado, mtime, reordenação de chaves em JSON) estão numa allowlist com justificativa escrita e comprovadamente produzem zero conflitos
- [ ] **CORR-08**: Uma issue fechada carrega o vínculo com o commit ou PR que a fechou, de modo que o git volte a ser fonte de corroboração — populado daqui pra frente e recuperável na história já existente

### Card de fase (CARD)

- [ ] **CARD-01**: Todo card de fase diz para que a fase serve, não apenas seu número e estado
- [ ] **CARD-02**: O card informa se houve research, planos feitos/total, issues fechadas/total e o veredito da verificação
- [ ] **CARD-03**: O board no terminal carrega a mesma informação da página HTML — uma leitura só, nenhuma superfície mais pobre que a outra
- [ ] **CARD-04**: O card nomeia o que a fase espera e qual o próximo comando, com a razão de estar naquela posição

### Lease de fase (LEASE)

- [ ] **LEASE-01**: É possível ver que outro agente está trabalhando dentro de uma fase antes de entrar nela
- [ ] **LEASE-02**: Entrar numa fase que outro actor vivo segura avisa quem segura e desde quando, em vez de sobrepor em silêncio
- [ ] **LEASE-03**: O lease atravessa worktrees — um agente numa segunda worktree do mesmo repositório enxerga o lease da primeira
- [ ] **LEASE-04**: Um lease deixado por sessão morta é detectável e liberável, nunca um bloqueio permanente
- [ ] **LEASE-05**: `/cairn:doctor` reporta lease obsoleto com a mesma disciplina com que já reporta claim obsoleto

### Journal de transições (JOUR)

- [ ] **JOUR-01**: Toda transição de estado de fase é registrada com actor, instante, fase e evento
- [ ] **JOUR-02**: O journal explica um conflito mostrando quando cada lado se moveu pela última vez
- [ ] **JOUR-03**: O journal nunca é autoridade única sobre o estado corrente — uma edição feita fora dos comandos do cairn continua sendo detectada
- [ ] **JOUR-04**: Um registro truncado por queda de processo é isolado e reportado com sua posição, nunca descartado em silêncio
- [ ] **JOUR-05**: O journal tem compactação projetada desde o início, com replay provado idêntico ao original

### Escalada semântica (ESC)

- [ ] **ESC-01**: Diante de um conflito, é possível pedir uma investigação que lê código, história e memória e **propõe** uma reconciliação
- [ ] **ESC-02**: A investigação é estruturalmente incapaz de gravar estado — a garantia é o programa não ter a capacidade, não uma instrução pedindo que não faça
- [ ] **ESC-03**: Aplicar uma proposta é um comando separado, invocado por humano, que enumera o que vai mudar antes de mudar
- [ ] **ESC-04**: A escalada roda apenas sobre conflito detectado, nunca numa passada rotineira de status ou doctor, e seu veredito é cacheado por hash da árvore

### Execução paralela de fases (PAR)

- [x] **PAR-01**: O `/cairn:autonomous` executa concorrentemente as fases que ele já identifica como independentes, em vez de anunciar o paralelismo e rodar em fila
- [x] **PAR-02**: Cada fase paralela roda numa worktree própria, e edições de uma não aparecem na árvore da outra antes da reconciliação
- [x] **PAR-03**: Duas execuções na mesma fase são impedidas pelo lease, com quem segura e desde quando — por mecanismo, não por convenção
- [x] **PAR-04**: A reconciliação relata o que cada fase produziu, e conflito de merge é reportado, nunca resolvido em silêncio
- [x] **PAR-05**: Falha ou interrupção de uma fase não corrompe as outras nem deixa lease órfão

### Release do milestone (REL)

- [x] **REL-01**: O CHANGELOG descreve o que o milestone entregou em termos do que mudou para quem usa o plugin, não como lista de commits ou de nomes de função
- [x] **REL-02**: A versão é bumpada em todo arquivo que a carrega, e um comando verifica que eles combinam em vez de alguém conferir de olho
- [x] **REL-03**: A tag é anotada e a release publicada com notas derivadas do CHANGELOG, nunca reescritas em paralelo
- [x] **REL-04**: A release diz o que quem já tem o plugin instalado precisa fazer, ou diz explicitamente que não precisa fazer nada

## v2 Requirements

Reconhecidos e adiados. Não entram neste roadmap.

### Corroboração

- **CORR-09**: Conflitos classificados por severidade, com allowlist configurável no estilo `.tfdriftignore` — adiado até existir corpus real de tipos de conflito; inventar níveis sobre zero dado é exatamente o erro que a pesquisa sobre alert fatigue descreve
- **CORR-10**: Visão de tendência de conflitos entre milestones ou entre repositórios

### Journal

- **JOUR-06**: Journal versionado em git e durável entre máquinas — exige antes a alternativa de hash-chain; um `merge=union` cru reordena e deduplica registros

## Out of Scope

Excluídos explicitamente.

| Feature | Reason |
|---------|--------|
| Os 13 wrappers `/cairn:*` (`CairnGo-9xy`) | Trabalho real, mas ortogonal a estado honesto — fica no backlog do bd |
| Remover o reparo de manifesto do gsd-core (`CairnGo-c8v`) | Auto-disparado pelo CI quando o upstream resolver; não precisa de fase |
| Reescrever a história do git para inserir ids de bd | Quebra clones e forks; o backfill via `--external-ref` recupera o vínculo sem tocar em commit já publicado |
| Lease baseado em arquivo como mecanismo primário | Medido: o bd resolve o workspace pelo git e atravessa worktree, então a issue de lease cobre o caso com menos superfície nova |
| Detecção de drift dentro do código-fonte (semântica do que foi implementado) | Corroboração compara declarações sobre a fase, não interpreta implementação; isso é o trabalho da escalada, sob pedido |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORR-01 | Phase 13 | Complete |
| CORR-02 | Phase 13 | Complete |
| CORR-03 | Phase 13 | Complete |
| CORR-04 | Phase 13 | Complete |
| CORR-05 | Phase 13 | Complete |
| CORR-06 | Phase 13 | Complete |
| CORR-07 | Phase 13 | Complete |
| CORR-08 | Phase 13 | Complete |
| CARD-01 | Phase 14 | Complete |
| CARD-02 | Phase 14 | Complete |
| CARD-03 | Phase 14 | Complete |
| CARD-04 | Phase 14 | Complete |
| LEASE-01 | Phase 15 | Complete |
| LEASE-02 | Phase 15 | Complete |
| LEASE-03 | Phase 15 | Complete |
| LEASE-04 | Phase 15 | Complete |
| LEASE-05 | Phase 15 | Complete |
| JOUR-01 | Phase 16 | Complete |
| JOUR-02 | Phase 16 | Complete |
| JOUR-03 | Phase 16 | Complete |
| JOUR-04 | Phase 16 | Complete |
| JOUR-05 | Phase 16 | Complete |
| ESC-01 | Phase 17 | Complete |
| ESC-02 | Phase 17 | Complete |
| ESC-03 | Phase 17 | Complete |
| ESC-04 | Phase 17 | Complete |
| PAR-01 | Phase 18 | Complete |
| PAR-02 | Phase 18 | Complete |
| PAR-03 | Phase 18 | Complete |
| PAR-04 | Phase 18 | Complete |
| PAR-05 | Phase 18 | Complete |
| REL-01 | Phase 19 | Complete |
| REL-02 | Phase 19 | Complete |
| REL-03 | Phase 19 | Complete |
| REL-04 | Phase 19 | Complete |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0 ✓

## Decisões travadas antes do roadmap

Registradas aqui porque a pesquisa pediu explicitamente que não ficassem para a implementação decidir.

| Decisão | Escolha | Por quê |
|---------|---------|---------|
| Fase em `conflict` bloqueia o ship gate | Sim | Conflito sem consequência degrada para ruído ignorado; `cairn-gate.py` e `cairn-loop-gate.py` recebem a mesma checagem aditiva, em lockstep |
| Sinal de git | `--external-ref` no fechamento **e** trailer `Bd-Issue:` | O backfill recupera história existente pelo `(#N)` do squash; o trailer impede a lacuna de voltar |
| Onde vive a corroboração | Estrutura paralela de condições, `disk_state` intocado | Alargar o enum quebra `phase_next_command()` com KeyError e faz o campo mentir sobre a própria definição |
| Mecanismo do lease | Issue de lease no bd | Medido nesta sessão: `bd list` de uma worktree devolveu as issues do repo principal sem criar banco local, sem daemon e sem registry global |
| Onde vive o journal | Local e gitignored | Nunca passa por merge do git, então a reordenação do `merge=union` deixa de ser um risco; visibilidade entre agentes é trabalho do bd |
| Ausência de sinal é `unknown` | Sempre | Fonte ilegível que "concorda" é exatamente o `|| echo "skipped"` que custou três releases |

---
*Requirements defined: 2026-07-29*
