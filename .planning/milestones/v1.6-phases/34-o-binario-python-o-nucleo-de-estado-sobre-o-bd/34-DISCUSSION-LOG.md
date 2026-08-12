# Phase 34: O binário python, o núcleo de estado sobre o bd - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-10
**Phase:** 34-o-binario-python-o-nucleo-de-estado-sobre-o-bd
**Areas discussed:** Arquivos do binário, Dimensões set-state

---

## Onde as famílias de estado vivem

| Option | Description | Selected |
|--------|-------------|----------|
| Scripts irmãos por grupo | dispatcher roteia; cairn-gsd-state.py e cairn-gsd-init.py; teto ~1.5k linhas por arquivo | ✓ |
| Tudo dentro do cairn-gsd.py | Um arquivo (~3k ao fim da 35); segundo maior script da casa | |

**User's choice:** Scripts irmãos por grupo (Recommended)

---

## Vocabulário das dimensões set-state (CORE-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Dimensões semânticas mínimas | phase, phase_status, plan, verification, session; labels legíveis; verbos mapeiam pra elas | ✓ |
| Espelhar os verbos gsd | 1 dimensão por verbo de escrita; herda vocabulário do upstream | |

**User's choice:** Dimensões semânticas mínimas (Recommended) — marcada one-way (schema de consulta permanente)

---

## Claude's Discretion

- Partição do misc entre os irmãos; forma da tabela verbo→dimensão (fonte única); cenários de golden.

## Deferred Ideas

Nenhuma.
