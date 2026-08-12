# Phase 32: O vendoring bruto da camada prompt - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-10
**Phase:** 32-o-vendoring-bruto-da-camada-prompt
**Areas discussed:** Estrutura interna, Lista de inclusão

---

## Estrutura interna de cairn/gsd/

| Option | Description | Selected |
|--------|-------------|----------|
| Espelhar a árvore upstream | Mesmos caminhos relativos do clone; diff byte a byte trivial; fase 36 mede contra base idêntica | ✓ |
| Achatar numa estrutura própria | Mais "cairn", mas exige mapa de renomes e perde a base limpa | |

**User's choice:** Espelhar a árvore upstream (Recommended)

---

## Lista de inclusão (VEND-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Subcomando do inventário + manifest versionado | Comando emite o fecho; manifest é o artefato; teste compara os dois | ✓ |
| Arquivo estático escrito uma vez | Rápido, mas ninguém prova que é o fecho | |

**User's choice:** Subcomando do inventário + manifest versionado (Recommended)

---

## Claude's Discretion

- Nome/formato do manifest; mecânica da cópia; local do crédito no README.

## Deferred Ideas

Nenhuma.
