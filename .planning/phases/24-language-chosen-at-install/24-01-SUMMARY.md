---
phase: 24-language-chosen-at-install
plan: "01"
subsystem: config
tags: [lang, subagent, config, parallel]
requires:
  - "cairn-config.py (fase 29): schema fechado com leitor nomeado por chave"
  - "cairn-parallel.py prepare (fase 18): o payload que monta o prompt"
provides:
  - "agents.response_language: a chave, com precedência escrita e testada"
  - "response_language + response_language_source no payload de prepare"
  - "o sexto item do bloco SUBAGENT-PROMPT"
affects:
  - "cairn-config.py effective(): ganha um passo antes do arquivo, só para chave com planning_key"
  - "cairn-parallel.py cmd_prepare: dois campos novos no payload e uma linha no render humano"
tech-stack:
  added: []
  patterns:
    - "precedência entre dois donos, com `source` dizendo quem venceu — em vez de dois arquivos que se contradizem em silêncio"
    - "fallback para null em vez de repetir o default: um default tem um lugar só"
key-files:
  created: []
  modified:
    - cairn/scripts/cairn-config.py
    - cairn/scripts/cairn-parallel.py
    - cairn/commands/autonomous.md
    - cairn/docs/commands/autonomous.md
    - tests/cairn-config.bats
    - tests/cairn-parallel.bats
    - tests/cairn-parallel-autonomous.bats
decisions:
  - "A chave do GSD vence a do cairn quando setada (D-03 do CONTEXT): honrar a mais estreita faria os subagentes do cairn e os do GSD divergirem na mesma execução"
  - "O fallback do prepare é `(None, \"unavailable\")` e não `(\"English\", …)`: repetir o default criaria o segundo lugar onde ele mora"
  - "Nada foi acrescentado ao ELSEWHERE do `list`: a relação com o `.planning/config.json` já aparece em `keys[]` via `planning_key` + `source`, e uma segunda entrada com o mesmo path duplicaria a lista"
metrics:
  duration: "~50min"
  completed: 2026-08-05
status: complete
---

# Phase 24 Plan 01: A língua no ponto de entrega — Summary

A língua de resposta atravessa mecanicamente da config até a saída do script que
monta o prompt do subagente, e o teste a lê lá — não no `.json` de config.

## O que mudou

**`cairn-config.py`** ganhou o tipo `str` (não-vazio, uma linha, ≤ 40 caracteres —
limites com razão escrita: o valor é colado dentro de um prompt, então uma quebra de
linha encerraria a instrução ao redor) e a chave `agents.response_language`, default
`"English"`, leitor `cairn-parallel.py prepare`.

A parte que não é só "mais uma chave" é a **precedência**. O spec carrega
`planning_key`, e `effective()` lê a chave do GSD primeiro:

```
.planning/config.json : response_language        -> source "planning"
.cairn/config.json    : agents.response_language -> source "file"
"English"                                        -> source "default"
```

`planning_value()` nunca morre: arquivo ausente, ilegível, JSON inválido ou raiz
que não é objeto leem todos como "não setado". O arquivo é do GSD, e um `get` que
morresse por causa dele derrubaria `cairn-parallel.py batch` e `prepare`, que fazem
shell-out para este script a cada execução — o que é teste, não intenção.

**`cairn-parallel.py`**: `cmd_prepare` acrescenta `response_language` e
`response_language_source` ao payload, resolvidos por `config_language(top)` — mesma
forma defensiva do `config_value()` que já existia. A leitura é feita do **main
checkout**, nunca da worktree recém-criada: a config que o operador configurou é a
que governa, e uma worktree é cópia de um commit, não um lugar que alguém
configurou. O render humano ganhou a linha correspondente, porque o operador lê
aquela saída antes de spawnar.

**`autonomous.md`**: o bloco delimitado passou de cinco para seis itens, e o texto
que declarava "all five of these" passou a dizer seis — com um teste que compara a
contagem declarada com os itens que o bloco realmente carrega.

## O defeito que isto fecha, e por que o critério era literal

O LANG-02 exige teste "no ponto de entrega, não na config". Não é preciosismo:
**o defeito aconteceu com a chave certa, presente e correta.** No ciclo v1.4 todo
subagente que o loop spawnou respondeu em inglês contra um planejamento inteiro em
PT-BR, e `.planning/config.json:69` já dizia `"response_language": "pt-BR"`. Um
teste afirmando "a chave está no arquivo" estaria **verde no dia em que quebrou**.

Medido, e é a causa: em ~30 workflows do `gsd-core` a diretiva padrão diz
literalmente *"Technical terms, code, file paths, **and subagent prompts stay in
English**"*. Um único arquivo — `references/execute-phase-response-language.md`
(#2402) — manda repassar. Na maioria dos pontos de spawn a regra escrita era não
repassar.

## Deviations from Plan

Nenhuma. O plano foi executado como escrito.

Uma decisão de escopo que o plano deixara em aberto e ficou registrada como escolha:
o array `elsewhere` do `list` **não** ganhou entrada nova. A relação entre os dois
arquivos já aparece em `keys[]` (campo `planning_key` mais `source: "planning"`), e
uma segunda entrada com o mesmo `path` duplicaria a lista que
`tests/cairn-config.bats:198` afirma por caminho ordenado.

## Verificação

`bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-config.bats` — anunciou
`1..22`, executou 22, 22 ok. Log inteiro lido.

`bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-parallel.bats` — anunciou
`1..41`, executou 41, 41 ok. Log inteiro lido. (A primeira execução deste arquivo
saiu por um `| tail -40` meu e veio truncada; foi refeita sem pipe e é a segunda
que está reportada aqui.)

`bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-parallel-autonomous.bats` —
anunciou `1..13`, executou 13, 13 ok.

### Controle negativo

Removida a chave `agents.response_language` do SCHEMA (cópia por `cp`, restaurada da
cópia — nunca `git checkout`), `bats -f "response language|reports English by
default" tests/cairn-parallel.bats` ficou **vermelho nos dois**:

- `prepare reports the response language from .cairn/config.json …` falhou no
  `set` (`unknown key`, status 2);
- `prepare reports English by default …` falhou **no ponto de entrega**:
  `jq '.response_language' returned 'null', expected 'English'`.

O segundo é o que importa: sem a feature, o payload não carrega a língua. O teste
não passaria com a feature removida.

## O que NÃO está provado

Que o modelo cola o item no prompt do Task tool. `bats` não spawna o Task tool — a
mesma fronteira que `cairn/commands/reconcile.md:29-31` já registra por escrito para
o próprio gate dele. O que está provado é (a) o valor sai do script que monta o
prompt, e (b) o bloco delimitado do prompt manda copiá-lo de lá. A ponte entre as
duas é o modelo, e nenhum teste deste plano afirma o contrário.

## Self-Check: PASSED

Arquivos afirmados existem; commits `95d68d0` e `5af12c9` existem em `git log`.
