---
phase: 32-o-vendoring-bruto-da-camada-prompt
plan: "01"
subsystem: tooling
tags: [gsd-core, vendoring, manifest, transitive-closure, filecmp, python-stdlib]

# Dependency graph
requires:
  - phase: 31-a-baseline-remedida-contra-a-tag
    provides: "cairn-inventory com ensure_corpus (clone pinado 68a04cc validado por HEAD), workflows8_files, agents_files e a serialização da casa"
provides:
  - "Subcomando `closure`: fecho transitivo dos 8 workflows sobre o corpus pinado, determinístico, gravável como manifest byte-idêntico ao --json (--write)"
  - "Subcomando `vendor`: cópia por lista (nunca copytree) do cache verificado para cairn/gsd/, reconferida por filecmp shallow=False, exit 2/6 nos erros"
  - "cairn/gsd/MANIFEST.json — lista de inclusão versionada e derivada (171 arquivos / 29.957 linhas medidos; schema_version, source, derived_from, files[], totals, summary.shim_matches)"
  - "cairn/gsd/** — árvore vendorizada byte-idêntica espelhando os caminhos relativos do clone v1.10.0, com LICENSE MIT intacto"
  - "README §License & credits com o crédito open-gsd/gsd-core tag v1.10.0 commit 68a04cc"
affects: [32-02, fase-36-adaptacao, fase-37-saida-do-marketplace]

# Actuals (#2632)
actuals:
  tokens: 399563
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dispatch de subcomando rota (b): testar sys.argv[1] antes do parser flat — preserva o contrato flat byte a byte onde add_subparsers exigiria duplicar flags"
    - "Manifest derivado: --json e --write passam pelo MESMO serializer (closure_payload) — a igualdade byte a byte é por construção, não por disciplina"
    - "derived_from.date date-only (sem hora) como critério de determinismo: duas execuções no mesmo dia emitem bytes idênticos"

key-files:
  created:
    - cairn/gsd/MANIFEST.json
    - cairn/gsd/LICENSE
    - "cairn/gsd/** (169 arquivos vendorizados além do LICENSE)"
  modified:
    - cairn/scripts/cairn-inventory.py
    - cairn/scripts/cairn-inventory.sh
    - README.md

key-decisions:
  - "O medido vence o research: 171/29.957 contra 160/28.071 — 16 agents (research 13, trio ui-*), 16 shims 1:1 (research contou só os 8 SKILL.md), LICENSE como entrada da lista, e contexts/ FORA porque nenhum arquivo do corpus referencia caminho contexts/*.md (a inclusão dos 3/66 no research era fiat, não fecho)"
  - "Layout real dos shims descoberto por ls no cache: commands/gsd/<w>.md e skills/gsd-<w>/SKILL.md — todos os 8 pares existem (shim_matches sem lista vazia)"
  - "requires: no clone real vive no frontmatter dos COMMANDS; nenhum SKILL.md dos 8 declara — a guarda check_skill_requires (escopo SKILL.md, por decisão de plano) passa no corpus real e morde se um SKILL.md prometer command fora da lista (die 6)"
  - "REF_RE com lookbehind (?<![A-Za-z0-9_-]) para nunca casar no meio de palavra (ex.: preferences/ contém references/)"

patterns-established:
  - "Guarda derivada de rejeição de research: a decisão de NÃO seguir o research §3 (fecho via requires:) vira código executável que reprova a premissa rejeitada se ela reaparecer"

requirements-completed: [VEND-01, VEND-02]

coverage:
  - id: D1
    description: "closure --json emite o fecho transitivo determinístico dos 8 workflows sobre o corpus pinado, e --write grava MANIFEST.json byte-idêntico (VEND-01)"
    requirement: VEND-01
    verification:
      - kind: other
        ref: "diff <(cairn/scripts/cairn-inventory.sh closure --json) <(cairn/scripts/cairn-inventory.sh closure --json) && diff <(cairn/scripts/cairn-inventory.sh closure --json) cairn/gsd/MANIFEST.json"
        status: pass
  - id: D2
    description: "vendor copia exatamente files[] do manifest do cache verificado para cairn/gsd/ espelhando caminhos relativos; fidelidade provada nos dois sentidos (VEND-01)"
    requirement: VEND-01
    verification:
      - kind: other
        ref: "sweep python3 (filecmp shallow=False sobre files[] + comm dos dois sentidos excluindo MANIFEST.json e contracts/**) — exit 0"
        status: pass
  - id: D3
    description: "LICENSE MIT do upstream byte-idêntico em cairn/gsd/LICENSE, entrando pela própria lista; README credita open-gsd/gsd-core com tag v1.10.0 e commit 68a04cc (VEND-02)"
    requirement: VEND-02
    verification:
      - kind: other
        ref: "cmp cairn/gsd/LICENSE .cairn/cache/gsd-core-v1.10.0/LICENSE && awk '/## License & credits/,0' README.md | grep 68a04cc"
        status: pass
  - id: D4
    description: "Contrato flat do inventário intacto: suítes existentes verdes sem edição"
    requirement: VEND-01
    verification:
      - kind: integration
        ref: "bats tests/cairn-inventory.bats tests/gsd-contracts.bats (48 testes)"
        status: pass
---

# Phase 32 Plan 01: Vendoring bruto da camada prompt — Summary

**closure → MANIFEST.json → vendor → diff provados de ponta a ponta no corpus real: cairn/gsd/ nasce da lista derivada (171 arquivos / 29.957 linhas), byte-idêntico ao clone da tag v1.10.0, com LICENSE MIT intacto e crédito no README.**

## Accomplishments

- `cairn-inventory.sh closure --json`: fecho transitivo (sementes: workflows8 + AGENTS_SCOPE + shims 1:1 + LICENSE; passadas de REF_RE até ponto fixo, só caminhos existentes no cache), determinístico entre execuções, `.files` ordenado, source.commit == 68a04cc.
- `closure --write cairn/gsd/MANIFEST.json` grava os MESMOS bytes do `--json` (serializer único `closure_payload`, indent 2, sort_keys, newline final).
- `vendor` valida o corpus primeiro (ensure_corpus), exige manifest presente (die 2) com source.commit correto (die 6), copia arquivo a arquivo com shutil.copy2 + mkdir parents (nunca copytree, nunca rmtree — contracts/** da fase 31 intocado) e reconfere cada cópia com filecmp shallow=False (die 6 em divergência).
- Fidelidade provada nos DOIS sentidos: todo files[] byte-idêntico ao cache, e nada sob cairn/gsd/ além de files[] + MANIFEST.json + contracts/**.
- Números medidos registrados no bloco datado MEASURED VERSUS ASSUMED com comando ao lado e a divergência contra o research §2.1 anotada; ASSUMED nomeia layout dos shims e exaustividade da REF_RE.
- README §License & credits credita open-gsd/gsd-core (MIT, tag v1.10.0, commit 68a04cc) apontando cairn/gsd/LICENSE intacto; crédito ao fork original preservado.

## Deviations

- Nenhuma de comportamento; registro de realidade: o research §2.1 lista 3 contexts/66 linhas no fecho, mas nenhum arquivo do corpus referencia `contexts/*.md` — o fecho mecânico os exclui e a divergência está anotada no bloco datado (o medido vence, CONTEXT).
- `requires:` existe no clone apenas no frontmatter dos commands (ex.: commands/gsd/plan-phase.md `requires: [discuss-phase, phase, review, update]`); a guarda do plano cobre SKILL.md por decisão registrada no próprio plano (rejeição do fecho via requires) e o 32-02 prova em fixture que ela morde.

## Commits

| hash | título |
|---|---|
| 324f5ed | feat(32-01): closure e vendor no inventário — cairn/gsd/ nasce do manifest |
| e19dc02 | docs(32-01): números medidos do fecho no bloco datado e usage dos subcomandos |
| 1bfb1bc | docs(32-01): credita open-gsd/gsd-core no README com tag e commit do pin |
