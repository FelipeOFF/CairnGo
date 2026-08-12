# Phase 35: O binário python, checagem e verbos órfãos - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 35-o-binario-python-checagem-e-verbos-orfaos
**Areas discussed:** Moradia da checagem e dos órfãos

---

## Onde vivem a família de checagem e os 5 órfãos

| Option | Description | Selected |
|--------|-------------|----------|
| Terceiro irmão com tudo | cairn-gsd-check.py nasce com checagem + órfãos, molde exec do D-01/34, teto 1.5k próprio; state e init intocados | ✓ |
| Checagem no irmão, órfãos no init | órfãos na folga de 175 linhas do init; aperta e mistura proveniência | |
| Tudo no dispatcher | sem arquivo novo; dispatcher caminha pro precedente doctor (3.9k) | |

**User's choice:** Terceiro irmão com tudo (Recommended)

---

## Claude's Discretion

- Partição interna do arquivo; uso de cairn_gsd_render se o teto apertar.
- Forma do diferencial do predicate ADR-2008; fixação da baseline do doctor.
- Semântica dos órfãos fiel ao REM-04; divergência consciente em divergences.json.

## Deferred Ideas

Nenhuma.
