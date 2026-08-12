# Phase 36: Workflows, steps e agentes falam bd - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 36-workflows-steps-e-agentes-falam-bd
**Areas discussed:** Escopo da camada prompt, tratamento de resolve-execution

---

## Escopo: quais superfícies a fase adapta

| Option | Description | Selected |
|--------|-------------|----------|
| Workflows + agentes | 8 workflows (189 chamadas, 50 arquivos) + 16 agentes (65 chamadas, 8 shims); references registrados como lacuna | ✓ |
| Tudo, incluindo os 40 references | Soma 18 chamadas e ~33 sítios de estado; fecha a superfície e adia o milestone | |
| Só os 8 workflows | A letra do roadmap; deixa 8 agentes quebrando quando a fase 37 remover o plugin | |

**User's choice:** Workflows + agentes (Recommended)

---

## resolve-execution (recuperação de quota, fora do universo de 87)

| Option | Description | Selected |
|--------|-------------|----------|
| Falha nomeada + cortar o sítio | Binário responde falha nomeada; o reference passa a descrever recuperação manual; zero código novo | ✓ |
| Implementar o verbo | Extrair semântica do bundle, golden diferencial; universo vai a 88; custa uma task | |
| Deixar quebrar e registrar | Exit 2 no meio de 5 jq; divergência consciente | |

**User's choice:** Falha nomeada + cortar o sítio (Recommended)

---

## Decidido por medição, sem ir ao usuário

- **ADAPT-01 (fragments):** preservar a composição. Achatar inlinaria 806 linhas para
  adaptar 10 das 38 chamadas dos fragments — o research fechou a questão com números,
  e o roadmap só exige que a decisão esteja escrita com motivo.
- **Onda zero:** o preâmbulo shim vem antes de tudo, porque nenhuma outra edição da fase
  tem efeito observável enquanto `gsd_run` resolver `gsd-tools.cjs`.

## Claude's Discretion

- Forma do preâmbulo novo (testada rodando); ordem das fatias; métrica de prova que não
  seja grep por nome de arquivo; tratamento de intel api-surface e graphify.

## Deferred Ideas

- Preencher o manifesto de verdade; os 40 references; os 193 caminhos `$HOME/.claude`;
  `--wave` como bool_flag.
