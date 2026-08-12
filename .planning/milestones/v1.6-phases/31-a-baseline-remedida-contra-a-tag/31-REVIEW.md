---
phase: 31
phase_dir: 31-a-baseline-remedida-contra-a-tag
reviewed: 2026-08-10T00:00:00Z
depth: standard
status: issues-found
files_reviewed: 18
files_reviewed_list:
  - cairn/scripts/cairn-inventory.py
  - cairn/scripts/cairn-inventory.sh
  - cairn/gsd/contracts/contracts.json
  - cairn/gsd/contracts/checagem.json
  - cairn/gsd/contracts/commit.json
  - cairn/gsd/contracts/config.json
  - cairn/gsd/contracts/dispatch-model.json
  - cairn/gsd/contracts/estado.json
  - cairn/gsd/contracts/init.json
  - cairn/gsd/contracts/loop-hooks.json
  - cairn/gsd/contracts/misc.json
  - cairn/gsd/contracts/roadmap-phase.json
  - cairn/gsd/contracts/skills.json
  - cairn/gsd/contracts/worktree.json
  - tests/cairn-inventory.bats
  - tests/gsd-contracts.bats
  - tests/cairn-command-surfaces.bats
  - .gitignore
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
---

# Fase 31: Relatório de Code Review

**Revisado:** 2026-08-10
**Profundidade:** standard
**Arquivos revisados:** 18
**Status:** issues-found

## Sumário

Revisão do cairn-inventory (script Python + wrapper), dos 12 JSONs de
contrato e das duas suítes bats novas, sobre a base `21b76ed..HEAD`.

Verificação executada além da leitura:

- As duas suítes rodaram por inteiro contra o cache real da tag: **48/48
  testes passam**, incluindo os skip-gated (cache presente).
- Cross-check mecânico independente: `call_sites.{workflows8,agents}` de
  **todas** as 87 entradas de contrato conferem com a recontagem por escopo
  sobre o `--json` do inventário (0 divergências); soma dos verbos por
  família (11+2+2+4+10+9+1+29+12+1+6) == 87 == índice do agregado ==
  `universe.verbs_total`; nenhum verbo duplicado dentro de família.
- Risco de truncamento da BROAD_RE medido contra o corpus pinado: 0 matches
  cortados no meio de token, 0 ocorrências de `gsd_run` com prefixo
  alfanumérico, nenhum verbo bare `query` no universo.
- `installer_cut`: os dois comandos gravados não contam arquivo em dobro
  (interseção vazia entre os quatro `find`).

Nenhum problema de segurança real (subprocess sempre com argv em lista,
rede declarada e restrita ao clone, HEAD validado em toda execução). Os
achados são de robustez do script e de fidelidade de um teste ao próprio
título.

## Críticos

Nenhum.

## Avisos

### WR-01: `--refresh` faz `rmtree` de qualquer diretório passado em `--cache-dir` que contenha `.git`

**Arquivo:** `cairn/scripts/cairn-inventory.py:239-241`
**Problema:** `ensure_corpus` apaga `cache_dir` inteiro quando `--refresh`
é passado e existe `cache_dir/.git` — sem validar que o diretório é de fato
o cache da tag. `cairn-inventory.sh --cache-dir . --refresh` na raiz de um
repositório apagaria o repositório. O custo de uma guarda é baixo e o dano
do engano é perda de dados irreversível.
**Fix:**
```python
if refresh and is_clone:
    code, out, _ = run_git(["-C", str(cache_dir), "rev-parse", "HEAD"])
    if code != 0 or out.strip() not in (expected_commit, TAG_COMMIT):
        # só apaga o que é reconhecível como o cache desta tag;
        # qualquer outra coisa: recusar e mandar o humano apagar à mão
        die(f"refusing to --refresh {cache_dir}: HEAD is not the pinned "
            f"tag commit — delete it manually if it really is the cache",
            EXIT_BAD_CORPUS)
    shutil.rmtree(cache_dir)
```
(Alternativa equivalente: aceitar o rmtree apenas quando o basename do
diretório é `gsd-core-{TAG}`.)

### WR-02: cache degenerado (diretório sem `.git`) é irrecuperável por `--refresh` e morre com o exit errado

**Arquivo:** `cairn/scripts/cairn-inventory.py:238-254`
**Problema:** `is_clone = (cache_dir / ".git").exists()`; com `--refresh`,
o `rmtree` só acontece `if refresh and is_clone`. Se o diretório do cache
existe mas não tem `.git` (rmtree interrompido, mkdir manual, clone
abortado que deixou resto), o fluxo tenta `git clone` para diretório
não-vazio, o git falha ("destination path ... not an empty directory") e o
script sai **5** ("dependência indisponível") — código que o docstring
reserva para git ausente/clone sem cache. Pior: `--refresh`, que a
documentação promete como o remédio ("um --refresh o refaz",
linha 183-184), não limpa esse estado — o usuário fica preso num exit 5
sem saída documentada.
**Fix:** apagar sob `--refresh` independentemente de `.git` (combinado com
a guarda do WR-01):
```python
if refresh and cache_dir.exists():
    shutil.rmtree(cache_dir)
```
e/ou detectar diretório não-vazio sem `.git` antes do clone e morrer com
exit 6 nomeando o estado ("cache dir exists but is not a git clone —
delete it or pass --refresh").

### WR-03: título do teste de spellings promete um invariante que não é checado — e que é falso nos dados

**Arquivo:** `tests/gsd-contracts.bats:104-126`
**Problema:** o teste chama-se "every verb entry has spellings[]
**containing the verb itself** and call_sites counts", mas o jq só valida
que `spellings` é array não-vazio e que `call_sites.*` são números. O
invariante do título nunca é assertado — e de fato **nenhuma** das 87
entradas o satisfaz: os spellings gravados são a forma de invocação medida
(`"query config-get"`, `"query state.load"`), nunca o verbo bare. O dado é
internamente consistente com o campo `spelling` do inventário; o problema é
o teste documentar (e aparentar garantir) uma propriedade inexistente —
quem ler a suíte como especificação do schema sai com o modelo errado, e
uma regressão real em spellings (ex.: spelling que não menciona o verbo)
passaria verde.
**Fix:** ou renomear o título para o que é checado ("has a non-empty
spellings[] and numeric call_sites counts"), ou assertar a relação real:
```bash
run jq -r '[.verbs[] | select([.spellings[] | contains(.verb)] | any | not) | .verb] | .[]' "$f"
```
(cada spelling contém o verbo — vale para as duas grafias de
`verification.status`, cujo spelling espaçado é "query verification
status").

## Informativos

### IN-01: BROAD_RE tem alfabeto mais estreito que a CALIBRATION_RE e nenhuma fronteira de palavra à esquerda

**Arquivo:** `cairn/scripts/cairn-inventory.py:137,140`
**Problema:** `BROAD_RE` não admite dígitos no verbo nem mais de um
segmento pontuado (`[a-z][a-z-]*(\.[a-z-]+)?`), enquanto a
`CALIBRATION_RE` admite `[a-z0-9._-]+`; e nenhuma das duas exige fronteira
antes de `gsd_run` (um `old_gsd_run query x` em prosa contaria como call).
Medido contra o corpus pinado: efeito zero (0 truncamentos, 0 prefixos, o
verbo-fallback bare `query` não ocorre). Como o corpus é imutável por
commit pinado, isto é risco latente apenas se a métrica for reutilizada
noutro corpus — vale um comentário ao lado da constante registrando o
limite.
**Fix:** anotar no comentário da BROAD_RE que o alfabeto diverge da
calibração de propósito e que a completude foi provada pelo balde `other`
(== 2) do corpus pinado, não pela regex.

### IN-02: `verbs_index(sites)` é computado duas vezes em `build_model`

**Arquivo:** `cairn/scripts/cairn-inventory.py:481,497`
**Problema:** o índice de verbos é construído para a chave `"verbs"` e
reconstruído dentro de `top_verbs`. Duplicação simples — um leitor pode
alterar um e esquecer o outro.
**Fix:** `vi = verbs_index(sites)` uma vez; usar `vi` nas duas posições.

### IN-03: `eval` de comando lido de arquivo de dados no teste do installer_cut

**Arquivo:** `tests/gsd-contracts.bats:461,469`
**Problema:** o teste re-executa via `eval` o comando gravado em
`contracts.json`. É desenho intencional (re-medir o comando gravado, REM-05)
e o JSON é versionado no mesmo repo que a suíte — quem pode envenenar o
dado pode editar o teste —, então não há escalada real. Fica registrado
como superfície consciente: qualquer futura geração automática desse campo
muda o cálculo de risco.
**Fix:** nenhum necessário agora; se o campo passar a ser gerado, trocar o
`eval` por um executor restrito (whitelist de `find|xargs|cat|wc`).

### IN-04: `--source`/`--expect-commit` customizados mantêm `tag: v1.10.0` na proveniência do artefato

**Arquivo:** `cairn/scripts/cairn-inventory.py:267-273`
**Problema:** `src_info` sempre reporta `tag: TAG`, mesmo medindo um
fixture local com commit arbitrário — o `--json` de um fixture alega
`"tag": "v1.10.0"`. O `commit` e o `repo` reais acompanham no mesmo bloco,
então a proveniência é auditável; ainda assim, um consumidor que leia só
`.source.tag` pode ser enganado.
**Fix:** quando `--expect-commit` difere de `TAG_COMMIT`, emitir também
`"pinned_tag_commit": TAG_COMMIT` ou um campo `"overridden": true` no
bloco `source`.

---

_Revisado: 2026-08-10_
_Revisor: Claude (gsd-code-reviewer)_
_Profundidade: standard_
