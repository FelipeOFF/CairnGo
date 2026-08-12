# Phase 13: State corroboration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-30
**Phase:** 13-State corroboration
**Areas discussed:** Exibição do conflito, Quórum e fontes ilegíveis, Severidade, Vínculo git, Template do terminal

---

## Exibição do conflito

### Onde mora o detalhe do conflito?

| Option | Description | Selected |
|--------|-------------|----------|
| Linha no board, detalhe no `--json`/doctor | Marcador e linha curta na fase; itemizado atrás de outro comando | ✓ |
| Bloco itemizado no próprio board | Cada fonte listada ali mesmo; board cresce com o número de conflitos | |
| Inline compacto na linha | `disk=executed bd=2open`; denso, exige saber ler a notação | |

**User's choice:** Linha no board, detalhe no `--json`/doctor.
**Notes:** Board segue escaneável; nada essencial fica escondido porque o rodapé
sempre diz quantos conflitos existem e por onde ver o detalhe.

### Uma fase em conflito ainda sugere próximo comando?

| Option | Description | Selected |
|--------|-------------|----------|
| Não sugere — manda resolver o conflito | Coerente com conflito bloquear o ship; interrompe quem sabe o que faz | |
| Sugere, com a ressalva anexada | Não interrompe; risco de a ressalva virar ruído | |
| Depende de qual fonte discorda | Mais preciso; exige a tabela de severidade | ✓ |

**User's choice:** Depende de qual fonte discorda.
**Notes (literal, do usuário):** *"dependendo vai precisar de uma escolha do
usuário com o Claude Answer to User (mesma ferramenta usada aqui) para o usuário
escolher qual é a saída. Mas tentar ao máximo deixar automático caso o conflito
seja algo simplório."* — este pedido criou uma tensão aparente com a decisão já
travada de que nenhuma fonte vence em silêncio; a tensão foi levada para a área
de Severidade e resolvida lá.

### O HTML pode mostrar mais que o terminal?

| Option | Description | Selected |
|--------|-------------|----------|
| Idêntico nas duas superfícies | Um teste renderiza os dois e compara | ✓ |
| HTML mais verboso | Aproveita o desktop; cria duas verdades para manter | |

**User's choice:** Idêntico nas duas superfícies.

---

## Quórum e fontes ilegíveis

### bd fora do ar: o que acontece com o veredito?

| Option | Description | Selected |
|--------|-------------|----------|
| Só o eixo do bd vira `unknown` | Demais fontes seguem corroborando e podem dizer ok | |
| Toda fase vira `unknown` | Falha alto; board fica quase mudo quando o bd tosse | |

**User's choice:** nenhuma das duas — resposta livre.
**Notes (literal):** *"Ao ficar fora do ar, manda alerta e solicita para o usuário
como ele deve fazer o fix."* Vira D-07: nem veredito inventado, nem board mudo;
o fato é dito e as opções de conserto são oferecidas.

### Quantas fontes legíveis precisam concordar?

| Option | Description | Selected |
|--------|-------------|----------|
| Todas as legíveis, sem exceção | Simples de explicar e testar; produz mais conflitos | ✓ |
| Maioria das legíveis | Menos ruído, mas elege vencedor em silêncio | |
| Todas, com pares que não contam | Compara só o comparável | |

**User's choice:** Todas as legíveis, sem exceção.

### A corroboração roda no CI?

| Option | Description | Selected |
|--------|-------------|----------|
| Não — local e interativo apenas | Clone raso faz o eixo do git mentir | ✓ |
| Sim, com `fetch-depth: 0` | Rede de segurança contra estado desonesto na main | |
| Sim, detectando clone raso e recusando | Falha alto em vez de corroborar sobre dado corrompido | |

**User's choice:** Não — local e interativo apenas.

---

## Severidade

### O que "resolver automaticamente" pode fazer?

| Option | Description | Selected |
|--------|-------------|----------|
| Nunca escreve — só deixa de bloquear | Preserva CORR-02; arquivo continua errado | |
| Escreve a classe de conserto provável | Allowlist curta de consertos seguros; abre a porta que CORR-02 fechou | |
| Pergunta sempre, com a resposta pré-selecionada | Zero silêncio, quase zero atrito; um enter resolve o óbvio | ✓ |

**User's choice:** Pergunta sempre, com a resposta já pré-selecionada.
**Notes:** É a resolução da tensão levantada na área de Exibição. Vira D-01, e
acabou sendo o princípio que atravessa a fase inteira.

### Severidade entra na fase 13 ou fica para o v2?

| Option | Description | Selected |
|--------|-------------|----------|
| Entra agora, mínima: 2 níveis | O mínimo que as respostas anteriores exigem | ✓ |
| Fica no v2, como o research recomendou | Evita inventar níveis sobre zero dado | |
| Entra agora, só como rótulo sem efeito | Junta dado real para o v2 decidir | |

**User's choice:** Entra agora, mínima — bloqueia e informa.

### O ship gate barra qual conjunto?

| Option | Description | Selected |
|--------|-------------|----------|
| Só os de severidade bloqueante | Ponteiro velho não impede publicar | ✓ |
| Qualquer conflito, sem exceção | CORR-05 ao pé da letra | |

**User's choice:** Só os de severidade bloqueante.

---

## Vínculo git

### Como roda o backfill das ~31 issues fechadas?

| Option | Description | Selected |
|--------|-------------|----------|
| Flag do doctor (`--link-refs`) | Padrão provado de `--fix-labels` / `--close-completed` | ✓ |
| Comando próprio de uma vez só | Claro que é operação única; cria script órfão depois | |
| Não faz backfill | História antiga sem eixo de git para sempre | |

**User's choice:** Flag do doctor.
**Notes (literal):** *"mas deixe o mais automático possível para o usuário […] o
cairn dá as opções e o projeto segue, sem precisar ficar 'parando' o processo."*

### Quem grava o vínculo daqui pra frente?

| Option | Description | Selected |
|--------|-------------|----------|
| Hook `post-bd-write`, no fechamento | Já existe e já observa comandos bd | ✓ |
| O próprio `/cairn:work` ao fechar | Falha visível; perde fechamentos feitos na mão | |
| Os dois | Redundante de propósito | |

**User's choice:** Hook `post-bd-write`.
**Notes:** Ressalva registrada em D-12 — o contrato "nunca falha o chamador"
significa que uma falha de gravação some em silêncio; o plano precisa de um teste
que prove que a falha aparece em algum lugar observável.

### Quem escreve o trailer `Bd-Issue:`?

| Option | Description | Selected |
|--------|-------------|----------|
| Não usa trailer — só `--external-ref` | Menos uma coisa que pode faltar sem ninguém ver | |
| `prepare-commit-msg` do beads | Granularidade por commit; some no squash | ✓ |
| Trailer na mensagem do squash | A única que sobrevive ao merge | |

**User's choice:** `prepare-commit-msg` do beads.
**Notes:** Limitação apontada antes da escolha e aceita: este repo faz
squash-merge, então o trailer é descartado no merge — é literalmente por isso que
zero de 239 commits carregam id de bd hoje. Registrada em D-13 como limitação
conhecida, não como surpresa futura.

---

## Template do terminal

Quatro variantes foram renderizadas no terminal para comparação direta, a pedido
do usuário, em vez de descritas em prosa.

| Option | Description | Selected |
|--------|-------------|----------|
| A — fontes na própria linha | Uma fase, uma linha, sempre; trunca motivo longo | ✓ |
| B — nota indentada sob a fase | Nada trunca; board cresce com os conflitos | |
| C — coluna de corroboração | Varredura vertical; exige largura fixa, repete "ok" | |
| D — conflitos agrupados no fim | Lista limpa; fase sai da ordem e aparece duas vezes | |

**User's choice:** A.

---

## Claude's Discretion

- Nomes exatos das chaves aditivas no `--json`.
- Estrutura interna do itemizado no `/cairn:doctor`.
- Onde exatamente a comparação vive dentro de `phase_model()`.
- Conteúdo inicial do corpus de diferenças inócuas (CORR-07).

## Deferred Ideas

- Severidade com mais de dois níveis e allowlist configurável (CORR-09, v2).
- Corroboração no CI com `fetch-depth: 0` (descartada agora por causa do clone raso).
- Visão de tendência de conflitos entre milestones (CORR-10, v2).
- Defeitos registrados no bd durante esta conversa, fora do escopo desta fase:
  `CairnGo-ca3`, `CairnGo-xhy`, `CairnGo-13t`, `CairnGo-0rk`.
