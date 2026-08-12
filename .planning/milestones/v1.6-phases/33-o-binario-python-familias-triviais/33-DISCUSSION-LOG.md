# Phase 33: O binário python, famílias triviais - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-10
**Phase:** 33-o-binario-python-familias-triviais
**Areas discussed:** Forma do binário, Harness diferencial

---

## Onde o binário vive e em que forma

| Option | Description | Selected |
|--------|-------------|----------|
| Dispatcher único em cairn/scripts/ | cairn-gsd.py + .sh + bats, padrão da casa; famílias futuras decididas na 34 com medida | ✓ |
| Módulos por família em cairn/gsd/bin/ | Mais modular, quebra o padrão um-script-uma-superfície | |

**User's choice:** Dispatcher único em cairn/scripts/ (Recommended)

---

## Harness diferencial (TRIV-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Goldens gravados da tag + --record skip-gated | Offline e determinístico; re-gravação roda o binário real do clone | ✓ |
| Executar o binário real em todo teste | Mais fiel, mas depende de node + build do upstream em toda suíte | |

**User's choice:** Goldens gravados da tag + re-gravação skip-gated (Recommended)

---

## Claude's Discretion

- Layout dos goldens e mecânica do --record; envelope conforme contrato; falha nomeada para verbo de outra fase.

## Deferred Ideas

- Distribuição das famílias 34-35 em arquivos (decisão na fase 34).
