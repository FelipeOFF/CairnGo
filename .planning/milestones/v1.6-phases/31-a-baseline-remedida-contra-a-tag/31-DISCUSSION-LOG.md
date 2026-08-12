# Phase 31: A baseline remedida contra a tag - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-10
**Phase:** 31-a-baseline-remedida-contra-a-tag
**Areas discussed:** Corpus alvo, Contratos, Forma do inventário, Verbos órfãos

---

## Corpus alvo

| Option | Description | Selected |
|--------|-------------|----------|
| Clone on-demand em cache | Clona --depth 1 --branch v1.10.0 para cache local, verifica o commit da tag; zero peso no repo, rede na primeira execução | ✓ |
| Git submodule pinado | Reproduzível offline, mas +54MB no clone e atrito de submodule | |
| Vendorizar já na 31 | Antecipa a 32; mistura fases e perde a visão do corpus completo | |
| Fixture parcial no repo | Circular: a lista de arquivos vem do próprio inventário | |

**User's choice:** Clone on-demand em cache (Recommended)

---

## Contratos

| Option | Description | Selected |
|--------|-------------|----------|
| JSON em cairn/gsd/contracts/ | Um por família + agregado; insumo direto das fases 33-35 e do harness; bats valida schema | ✓ |
| Markdown em .planning/research/ | Legível mas vira segunda fonte a parsear | |
| JSON dentro de tests/ | Contrato é artefato de produção, não fixture | |

**User's choice:** JSON em cairn/gsd/contracts/ (Recommended)

---

## Forma do inventário

| Option | Description | Selected |
|--------|-------------|----------|
| Script novo cairn-inventory | py + sh + bats, padrão da casa; doctor intocado (CHECK-04 exige baseline fixa dele) | ✓ |
| Subcomando do doctor | Engorda o maior script da casa antes da baseline congelar | |

**User's choice:** Script novo cairn-inventory (Recommended)

---

## Verbos órfãos

| Option | Description | Selected |
|--------|-------------|----------|
| Mesmo contrato JSON, com proveniência | Uniforme; harness sem caso especial; campo de proveniência com referência de linha | ✓ |
| Spec markdown por verbo | Mais espaço, mas dois leitores no harness | |

**User's choice:** Mesmo contrato JSON, com proveniência (Recommended)

---

## Claude's Discretion

- Layout interno de cairn/gsd/contracts/ (nomes por família, shape do schema).
- Local exato e política de invalidação do cache do clone.
- Formato da saída humana do cairn-inventory (com --json obrigatório).

## Deferred Ideas

Nenhuma — a discussão ficou dentro do escopo da fase.
