---
phase: 25-measured-cleanup
plan: "03"
requirement: AUTO-10
beads: [CairnGo-ctr]
status: complete
---

# Fase 25 Plano 03 — resumo

## O que mudou

O `cairn-bookkeep close` passa a escrever `active_phase` junto com
`current_phase`, e o `cairn-doctor` ganha a vigésima segunda checagem, que
compara as duas. Aditivo: nenhum leitor mudou, nada foi migrado, e o GSD
continua achando a chave dele.

## A medição, antes e depois

```
antes                                   depois
current_phase: 29                       current_phase: 29
                    <- ausente          active_phase: 29
claims-stale ⊘ no-input                 claims-stale ✓ ok
                    <- nao existia      state-dialect ✓ ok
```

`grep -rn current_phase cairn/` continua devolvendo zero leitores, e é por isso
que a chave que o cairn lê passou a ser escrita ao lado — não no lugar.

## As duas metades do critério 5, e a asserção que fecha cada uma

| Metade | Teste |
|---|---|
| o `STATE.md` fala as duas, e a checagem que nunca rodou passa a rodar | `AUTO-10: close --apply lands active_phase, and claims-stale stops reporting no input` |
| a divergência entre as duas vira checagem do doctor | `state-dialect: two keys naming two different phases is a FAIL that routes` |

E as três metades negativas, sem as quais a afirmação seria vazia:
`state-dialect: two keys naming the same phase is ok` (senão "sempre falha"
passaria numa checagem que roda em toda invocação), `state-dialect: one key only
is out-of-scope, and never a gap` (asserção sobre o valor exato, nunca sobre a
negação de `ok`), e `close --apply: no current_phase in the file means no
active_phase either` (a âncora, sem a qual a exceção vira invenção).

## A escolha que precisou ser argumentada, não medida

Uma chave só é `⊘ out-of-scope`, nunca `no-input`. O arquivo com uma chave **não
tem divergência de dialeto para ter** — falar um dialeto só é o estado que o
AUTO-10 persegue. A ausência de `active_phase` já é `no-input` na `claims-stale`;
repetir aqui contaria um buraco duas vezes e derrubaria o `.ok` de todo
repositório GSD que nunca rodou o `cairn-bookkeep` — falso vermelho permanente,
que é o defeito da fase 23 espelhado (D-07). A atribuição está escrita no
docstring da checagem, como o próprio arquivo manda.

## A prova por quebra

Cinco quebras reais no fonte, cada uma numa **cópia da árvore fora do
repositório** (`cairn/` e `tests/` copiados para um diretório de trabalho, onde
o `helpers.bash` resolve a raiz sozinho), restauradas de cópia `cp` e conferidas
por `shasum` no fim. Nenhum `git checkout <arquivo>`.

| Guarda | O que foi removido | Asserção que ficou vermelha |
|---|---|---|
| G1 | `active_phase` sai de `STATE_KEYS_WRITTEN` | `an active_phase already in the file is updated` — `grep "active_phase: 29"` falhou |
| G2 | a condição de âncora `"current_phase" in items` | `no current_phase in the file means no active_phase either` — `unexpectedly found 'active_phase'` |
| G3 | `check_state_dialect` sai do registro do `main()` | `two keys naming two different phases` — `[ "$status" -eq 7 ]` falhou |
| G4 | a discordância devolve `warn` em vez de `fail` | a mesma — `[ "$status" -eq 7 ]` falhou |
| G5 | uma chave só devolve `no-input` | `one key only is out-of-scope` — `.scope returned 'no-input', expected 'out-of-scope'` |

**G1 saiu VERDE na primeira tentativa, e o verde é o achado.** Remover
`active_phase` de `STATE_KEYS_WRITTEN` não derrubou um único teste, porque o
ramo que **cria** a chave pergunta `"active_phase" in wanted` e nunca consulta a
tupla. Ou seja: a tupla governa apenas a **atualização** de um arquivo que já
carrega a chave — o estado de todo repositório a partir do segundo `close` — e
nada afirmava isso. Sem a descoberta, a fase teria entregue uma chave escrita
uma vez e depois envelhecendo, que é uma instância nova do exato defeito que a
`state-dialect` existe para pegar: ela começaria a **reprovar** o doctor na fase
seguinte. O teste
`close --apply: an active_phase already in the file is updated, not duplicated`
fecha o buraco, e G1 refeita ficou vermelha nele.

## O canário de contagem do doctor

De **21 para 22**, os quatro sítios na mesma edição: as duas asserções
`.checks | length` do `tests/cairn-doctor.bats`, a lista numerada do docstring do
`cairn-doctor.py` (mais o `twenty-one` → `twenty-two` da checagem 0 e o
`21 checks` do rodapé) e a página `cairn/docs/commands/doctor.md` (a entrada
nova, o `twenty-two checks in total` e o `22 checks`). **A última vaga da fase
está usada.**

O comentário do canário registra que as fases 23 e 24 rodaram em paralelo e o
git mesclou os dois arquivos sem conflito. A fase 25 rodou em duas worktrees
outra vez — e desta vez há **um escritor só**: a outra frente não toca
`cairn-doctor.py`, então não há merge sobre o qual ficar em silêncio. Isso está
escrito ao lado da asserção.

## Medido, e contrariou o que estava escrito

1. **A tupla não governa a criação da chave** (o G1 acima). Duas trilhas de
   código onde a leitura sugeria uma.
2. **O teste `claims-stale: the doctor never writes active_phase and never reads
   current_phase` tinha um título que a fase tornou falso.** O doctor agora LÊ
   `current_phase` — na checagem 21, para compará-la, jamais como sinônimo. O
   teste seguiu válido e verde; o título foi corrigido para dizer o que ele de
   fato guarda (`never takes current_phase as its synonym`), com a razão ao
   lado. Um título que mente é a mesma classe de defeito que um número em prosa
   que envelhece.
3. **Um teste da suíte do doctor afirmava o conjunto exato dos `⊘` e não é
   afrouxável.** `lease-stale: cairn-lease.py itself failing degrades to warn`
   fixa `phase-landed,release-versions,test-parallel`; a checagem nova entra
   como quarto `out-of-scope` na fixture. O literal foi **editado**, nunca
   trocado por um subconjunto — o comentário do próprio teste explica que um
   subconjunto é o que para de pegar uma regressão real para o quarto estado.
   Foi a única falha da suíte completa (116 de 117 na primeira rodada).
4. **O contrato de diff do `close` mudou de forma assimétrica.** Era
   `5 5 .planning/STATE.md`; passou a `6 5`, porque cinco valores são
   substituídos e **uma** chave é criada. É a primeira e única inserção que a
   metade do `STATE.md` já fez, e o teste passou a dizer isso com essas
   palavras.

## Suítes

`tests/cairn-bookkeep.bats` (53 testes, verde) e `tests/cairn-doctor.bats`
(117 testes, `--jobs 6`, verde depois do sítio corrigido).
