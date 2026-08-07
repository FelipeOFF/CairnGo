---
phase: 25-measured-cleanup
plan: "10"
requirement: FIX-01, FIX-03
beads: [CairnGo-tuh, CairnGo-gbu, CairnGo-13t]
status: complete
---

# Fase 25 Plano 10 — resumo

## O que mudou

| Issue | Mudança |
|---|---|
| `CairnGo-tuh` (FIX-03, critério 2) | o `--json` do `cairn-release` para de embutir uma comparação dentro de `status`: o campo passa a ser fato sobre o portador sozinho, a comparação ganha `agrees_with_reference`, e a régua é nomeada em `reference` |
| `CairnGo-gbu` (critério 7) | a declaração de `cairn.sync_push` sai do `capability.json`, dos três fragmentos e do `tests/capability.bats`; as duas páginas do `/cairn:config` passam a descrever a remoção |
| `CairnGo-13t` (FIX-01) | `/cairn:milestone new` e o `SKILL.md` param de mandar gerar mapa num momento em que ele não pode rodar |

Seis testes novos ou reescritos; cinco quebras guardadas.

## `CairnGo-tuh` — o campo passou a dizer o que mede

Medido, reproduzido no teste: com o CHANGELOG em 1.5.0 e os manifestos em
1.4.2, o `marketplace` levava `status: ok` **carregando a versão velha**, e o
`changelog`, o único certo, levava `mismatch`.

**A maioria foi recusada por medição, não por gosto:** dois portadores em 1.4.2
contra um em 1.5.0 fazem a maioria acusar o changelog também. Maioria não é
correção — é um segundo palpite com nome melhor. Qual versão era a pretendida
não é fato que este repositório tenha.

Então:

| Campo | O que responde |
|---|---|
| `status` | fato sobre o portador **sozinho**: `ok`, `missing`, `invalid json`, `invalid semver` (e no `tag` também `pending`/`skipped`). `mismatch` **saiu** daqui — "não bate" é afirmação sobre um par |
| `agrees_with_reference` | `true`/`false` para os portadores realmente comparados; `null` quando não houve comparação (ilegível, eixo próprio, tag não consultada) |
| `reference` (topo) | o portador que serviu de régua, **por nome** — uma régua, nunca um veredito |

`null` em vez de `false` para o não comparado é a mesma regra que os leitores
já seguiam com `None` em vez de `""`: comparação que não aconteceu não é
discordância. O teste afirma que a **chave existe** e vale `null`, porque um
`jq` sobre chave ausente também devolve `null` — a asserção passaria contra um
payload que nunca aprendeu o campo.

**Critério 3 verificado:** texto humano e códigos de saída idênticos, e o único
consumidor do JSON fora dos testes — o `check_release_versions` do
`cairn-doctor.py`, que lê `findings`, `version` e o `status` da entrada `tag` —
devolve o **mesmo objeto** antes e depois:
`{"id": "release-versions", "status": "ok", "detail": "every version carrier agrees on 1.5.0, git tag v1.5.0 present", "items": []}`.

## `CairnGo-gbu` — a declaração saiu, o comportamento não mudou

D-04, decidido pelo Felipe em 2026-08-06 e não rediscutido. A chave saiu de
`capability.json`, dos três fragmentos (`plan-post`, `execute-wave-pre`,
`execute-wave-post`) e do `tests/capability.bats`.

Os três fragmentos diziam "se o `.cairn/sync.json` tem backend habilitado **e a
config `cairn.sync_push` não é false**". A segunda cláusula nunca foi legível
por nada — a instrução descrevia uma condição que ninguém conseguia avaliar. A
primeira, que é a que decide de verdade, ficou.

O teste substituto é o **inverso** do que ele era, de propósito: declaração é
promessa, e a forma de essa promessa voltar é alguém redeclarar a chave. Além
disso o conjunto de chaves declaradas passou a ser afirmado **inteiro**
(`cairn.enabled`), e um segundo teste varre os fragmentos.

## `CairnGo-13t` — a prosa mandava o impossível, nos dois sítios

Medido na abertura do v1.4 (5 de 5) e confirmado na do v1.5. Reproduzido no
teste: `cairn-map.sh 20` numa fixture sem o diretório da fase responde
`no phase directory matching phase 20` e sai `4`.

O script não mente — falha alto e com código próprio. O defeito estava na prosa
e ela estava em **dois** lugares: `cairn/commands/milestone.md` passo 3 e
`cairn/skills/cairn/SKILL.md` no bloco do `/gsd:new-milestone`. Consertar um só
deixaria o outro dando a mesma ordem impossível — a quebra guardada G é
exatamente esse cenário, e ele fica vermelho.

Os dois agora dizem onde o mapa nasce (no plano da fase, que é onde o diretório
nasce), então o passo foi **movido**, não apagado — e o teste afirma as duas
metades.

## As quebras guardadas

| # | Quebra | Asserção derrubada |
|---|---|---|
| D | `reference` volta a não ser emitido | `the reference carrier is named…` → `jq '.reference' returned 'null'` |
| D2 | `mismatch` volta a ser valor de `status` | `…disagree: exit 6 naming both paths…` → `status returned 'mismatch', expected 'ok'`; e `[.carriers[] \| select(.status=="mismatch")] \| length` → `1`, esperado `0` |
| E | a declaração de `cairn.sync_push` volta ao `capability.json` | `config slice declares cairn.enabled, and NOT a key nothing reads` |
| F | a cláusula morta volta a um fragmento | `no prompt fragment gates the mirror push on a key nothing reads` → nomeia arquivo e linha |
| G | só o comando é consertado; o `SKILL.md` volta ao estado anterior | `no surface orders a map generation at milestone-new time` → `SKILL.md:98` |

Todas restauradas de cópia `cp` — nunca `git checkout <arquivo>`.

## Suítes rodadas

| Suíte | Resultado |
|---|---|
| `tests/cairn-release.bats` (23) | verde |
| `tests/capability.bats` (21) | verde |
| `tests/cairn-config.bats` (29) | verde — inclusive o que exige `cairn.sync_push`, `post-bd-write.sh:126-152` e `CairnGo-gbu` literais no prompt do `/cairn:config` |
| `tests/hooks.bats` (33) | verde — o hook que decide o push não mudou |
| `tests/cairn-command-surfaces.bats` (14) | verde |
| `tests/cairn-bookkeep.bats -f "hand edit"` e `tests/cairn-reconcile-agent.bats` (9) | verdes — as duas varreduras sobre `cairn/commands` e `cairn/skills` |

## Premissas que a medição contradisse

1. **A issue do `gbu` diz que a chave vive em três lugares** (`capability.json`,
   três fragmentos, `tests/capability.bats`). Vive em **nove**: mais
   `cairn/commands/config.md`, `cairn/docs/commands/config.md`, a docstring do
   `cairn/scripts/cairn-config.py` (duas vezes), `tests/cairn-config.bats` (três
   sítios, um deles **exigindo** a string no prompt), `tests/cairn-test.bats:217`
   e `.planning/codebase/STRUCTURE.md:197`.
2. **"Apagar a declaração" não podia ser apagar todas as menções.**
   `tests/cairn-config.bats:726` exige `cairn.sync_push`,
   `post-bd-write.sh:126-152` e `CairnGo-gbu` **literalmente** dentro de
   `cairn/commands/config.md`. Apagar a seção deixaria um teste de outra frente
   vermelho — e ela não devia sumir mesmo: explicar por que o botão não existe
   é mais útil depois da remoção do que antes.
3. **A issue do `13t` fala de "o passo 3 do skill".** O passo 3 está no
   **comando** (`cairn/commands/milestone.md`); o `SKILL.md` carrega a mesma
   ordem noutra forma, num bullet. São duas superfícies, e a issue nomeia uma.
4. **`cairn-map.sh` não aceita `--project-dir`.** A primeira escrita do teste
   usou essa flag por analogia com os outros scripts e recebeu exit `2`
   (`unknown option`), não o `4` do defeito. A flag é `--planning-dir`, e a
   medição correta precisa dela.
5. **`status: mismatch` no portador de referência.** O código antigo também
   marcava a **régua** como `mismatch` (linhas 338-339), não só o discordante —
   detalhe que a issue não registra e que reforça o achado: dois portadores
   errados levavam rótulos diferentes por acidente de ordem.

## Registrado, não consertado

A docstring de `cairn/scripts/cairn-config.py` cita a declaração do
`sync_push` como exemplo canônico da regra "nenhuma chave sem leitor". O
argumento continua válido; o tempo verbal e os endereços de linha
envelheceram. O arquivo é da outra frente nesta fase, então virou issue de
backlog **`CairnGo-b5f`**, que nomeia também os outros quatro sítios de
comentário (`tests/cairn-config.bats`, `tests/cairn-test.bats:217`,
`.planning/codebase/STRUCTURE.md:197`).
