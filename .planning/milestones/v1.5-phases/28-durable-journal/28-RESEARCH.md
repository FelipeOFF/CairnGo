# Fase 28: Durable journal — Pesquisa

**Pesquisado:** 2026-08-05
**Domínio:** merge de arquivos append-only sob git; ordenação de eventos entre máquinas sem relógio comum
**Confiança:** ALTA nas medições, ALTA na recomendação, MÉDIA no dimensionamento do desenho alternativo
**Natureza:** esta fase é um **portão**. O `DJOUR-01` exige a decisão antes de qualquer código, e o `ROADMAP.md` registra que esta é a única fase cujo escopo a própria pesquisa pode redefinir. Este documento exerce essa permissão.

---

## Veredito, primeiro

**A premissa do requisito está parcialmente errada, e a alternativa que ele nomeia é pior do que aquilo que ele quer substituir.**

Medido nesta sessão, num repositório temporário, com o `git 2.42.1` e o `cairn-journal.py` de produção:

| Afirmação do `DJOUR-01` | Medido | Evidência |
|---|---|---|
| `merge=union` **reordena** registros | **Verdadeiro** | E2 — a ordem física vira "bloco de A, depois bloco de B", nunca cronológica |
| `merge=union` **deduplica** registros | **Verdadeiro, mas só para linhas byte-idênticas** | E3 — 2 eventos escritos, 1 sobreviveu |
| ...e isso ameaça o journal do cairn | **Falso hoje** | E4 — o `nonce` uuid4 que o `cairn-journal.py` já escreve em toda linha torna a colisão byte-idêntica impossível. Essa defesa foi construída na fase 16 e está em produção |
| `merge=union` **perde registro** | **Falso para append puro** (8 de 8 sobreviveram, E2); **verdadeiro quando há compactação** (E5, E13) | E13 — duas máquinas compactando concorrentemente: a história inteira de uma delas some, sem erro, sem conflito, com um arquivo JSONL perfeitamente válido no fim |
| hash-chain resolve isso | **Falso** | E6 — a cadeia quebra na primeira linha da outra máquina; o resultado tem 2 cabeças, não 1 |

**O que realmente quebra não é o `union`. São duas outras coisas, e uma delas está no código de produção agora:**

1. `_last_known()` dobra os registros **em ordem de arquivo**, e o docstring dele afirma isso explicitamente como invariante (*"file order IS chronological order; no re-sort needed here, unlike a hypothetically git-merged file"*). Sobre um journal mesclado, o `last-moved` de produção devolveu `complete` quando a verdade era `archived` (E2 + medição direta abaixo). Não é hipótese: rodei o script real sobre o arquivo mesclado real.
2. `compact()` é estruturalmente incompatível com um arquivo compartilhado e mesclado. O `union` **ressuscita** os registros que a compactação dobrou (E5: um snapshot mais os 4 registros que ele substituía, todos no mesmo arquivo), e duas compactações concorrentes descartam silenciosamente a história de uma das máquinas (E13).

**Recomendação: não versionar o journal.** A fase 28 entrega a decisão registrada, mais um guarda-corpo que impede a decisão de apodrecer em silêncio. O `DJOUR-02` como está escrito não sobrevive a esta pesquisa e precisa ser reescrito — está nomeado abaixo, com o motivo, como item de grooming.

---

## Restrições do usuário

**Não existe `CONTEXT.md` para a fase 28.** O diretório `.planning/phases/28-durable-journal/` foi criado por esta pesquisa. As restrições vinculantes vêm, então, de três fontes já travadas, e esta pesquisa as trata com a mesma autoridade que trataria decisões de um `/cairn:discuss-phase`:

### Travado pelo ROADMAP.md § Phase 28

- A pesquisa vem **antes** de qualquer implementação, com o que foi medido escrito.
- *"se a conclusão for que não vale, isso também é resultado e a fase entrega a decisão em vez de código"* — permissão explícita para o veredito acima.
- *"Se a hash-chain não resolver reordenação sob merge sem custo desproporcional, o resultado honesto é a decisão registrada de manter o journal local."* — o ROADMAP já antecipou este desfecho e o autorizou.
- A fase fica por último por ser a de maior risco.

### Travado pelo REQUIREMENTS.md § DJOUR

| ID | Texto | Situação após esta pesquisa |
|----|-------|------------------------------|
| DJOUR-01 | A alternativa de hash-chain é pesquisada e decidida **antes** de qualquer código: um `merge=union` cru reordena e deduplica registros, e isso precisa estar resolvido | **Atendido por este documento.** A hash-chain foi medida e rejeitada; a premissa do "deduplica" foi medida e mostrou-se já resolvida pelo `nonce` |
| DJOUR-02 | O journal sobrevive entre máquinas sem que merge reordene ou perca registro, provado por teste que mescla dois journals divergentes | **Não sobrevive à recomendação.** Precisa ser reescrito — ver "Perguntas abertas" |
| DJOUR-03 | O journal versionado continua sem ser autoridade sobre o estado corrente — apagá-lo não muda veredito nenhum | **Trivialmente atendido pela recomendação**, e é o requisito que mais pesa contra a hash-chain |

### Fora de escopo, por instrução direta

`.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` e `.planning/STATE.md` **não foram tocados** por esta pesquisa. Quatro fases executam em paralelo e esses três arquivos são o ponto de conflito. Tudo que esta pesquisa quer mudar neles está registrado abaixo como item de grooming, não aplicado.

---

## Restrições do projeto (de CLAUDE.md e CONVENTIONS.md)

O planejador precisa verificar conformidade com estes pontos:

| Origem | Diretiva | Consequência para esta fase |
|--------|----------|------------------------------|
| `CLAUDE.md` | Rastreamento de tarefas **só** por `bd` (beads). Nada de TodoWrite, TaskCreate ou TODO em markdown | Qualquer trabalho remanescente vira issue `bd`, não lista solta |
| `CLAUDE.md` | Perfil **conservador** por padrão: não commitar, não empurrar, não sincronizar Dolt sem pedido explícito | O plano não pode assumir commit automático |
| `CLAUDE.md` | Conhecimento persistente via `bd remember`, nunca `MEMORY.md` | A decisão desta pesquisa deve ir para `bd remember` além do documento |
| `CONVENTIONS.md` | **Só stdlib.** `pip install filelock`/`fasteners`/`GitPython` é violação dura | Nenhuma alternativa aqui pode depender de biblioteca de terceiro. Isso elimina CRDT de prateleira |
| `CONVENTIONS.md` | Sem type hints, sem dataclasses | O código da fase, se houver, segue |
| `CONVENTIONS.md` | Todo `cairn-X.py` tem um par `cairn-X.sh` | Um script novo custa dois arquivos |
| `CONVENTIONS.md` | `EXIT_*` nomeados; helper `die(msg, code)` duplicado por script, sem lib compartilhada | O padrão do `cairn-journal.py` já segue isso |
| `CONVENTIONS.md` | Um `.bats` por script, em `tests/` | O teste do `DJOUR-02` vai para `tests/cairn-journal.bats` (16 testes hoje) |

---

## Ponto de partida medido

A fase **não parte do zero**. Isto é o que existe hoje, medido, não presumido.

### `cairn-journal.py` — 47.001 bytes, 1.128 linhas, escritor único

| Propriedade | Valor medido |
|---|---|
| Caminho do arquivo | `<project-dir>/.cairn/journal.jsonl` (dentro do worktree, deliberadamente **não** em `--git-common-dir`, ao contrário do lease) |
| Formato | JSONL. Uma linha física por registro, `json.dumps(record, sort_keys=True)` |
| Envelope comum | `ts` (ISO-8601 UTC, resolução de microssegundo), `nonce` (uuid4 hex), `actor`, `phase`, `event` |
| Eventos | `state_changed`, `verdict_changed`, `lease_changed`, `snapshot` |
| Atomicidade de append | `os.open(O_WRONLY\|O_CREAT\|O_APPEND)` + **um** `os.write()` por registro, com verificação do byte count. Não é `open(path,"a")`, por decisão registrada |
| Compactação | `compact()` dobra a história de cada fase num `snapshot`, escreve num irmão e faz `os.rename`. Auto-disparo em `JOURNAL_COMPACT_THRESHOLD_BYTES = 200 KiB` |
| Guardas de concorrência | `fcntl.flock(LOCK_EX\|LOCK_NB)` entre compactações; revalidação de `st_size` antes do `rename` contra append concorrente |
| Códigos de saída | `EXIT_OK=0`, `EXIT_USAGE=2`, `EXIT_WRITE_FAILED=4` |
| Testes | `tests/cairn-journal.bats`, **16** testes, incluindo torn-tail, Pitfall 14 e equivalência de replay pós-compactação |

### Estado git do journal, medido agora

```
$ git ls-files ".cairn/"
(vazio — nada de .cairn/ é rastreado)

$ git check-ignore -v .cairn/journal.jsonl
.gitignore:8:.cairn/journal.jsonl*	.cairn/journal.jsonl

$ find . -name ".gitattributes" -not -path "./node_modules/*"
./benchmarks/plugins/context-mode/v1.0.169/.gitattributes
./benchmarks/plugins/context-mode/v1.0.169/node_modules/fast-uri/.gitattributes
./benchmarks/plugins/gsd/v4.3.1/node_modules/fast-uri/.gitattributes

$ git ls-files "*.gitattributes"
(vazio — nenhum dos três é rastreado)
```

**Confirmando o que o pedido já media:** não há merge driver configurado. Os três `.gitattributes` encontrados são de dependências vendorizadas dentro de `benchmarks/plugins/`, todos não rastreados, e todos contêm apenas `* text=auto eol=lf` — nenhum menciona `merge=` nem `*.jsonl`. **O `merge=union` do requisito é hipótese a avaliar, e continua sendo.** [VERIFICADO: comandos acima, este repositório]

### O journal real deste projeto, agora

```
registros: 141
eventos: {'state_changed': 104, 'verdict_changed': 27, 'lease_changed': 10}
fases: [13..30]
atores: {'FelipeOFF': 141}   ← uma máquina, um ator
tem nonce em todos? True
janela: 2026-07-31T19:36:56 -> 2026-08-05T15:27:09  (5 dias)
tamanho: 27.992 bytes
```

**Número que importa para a decisão:** 27.992 bytes em 5 dias ≈ **5,6 KB/dia**. O gatilho de compactação é 200 KiB. Nesse ritmo, `compact()` dispara pela primeira vez em **≈ 36 dias**. Ou seja: a compactação nunca rodou na vida real deste projeto ainda, mas vai rodar dentro de mais ou menos um mês — e é exatamente ela que colide com o merge. Não é um risco distante. [VERIFICADO: `.cairn/journal.jsonl` deste worktree]

### Quem escreve e quem lê

| Script | Papel | Mecanismo |
|--------|-------|-----------|
| `cairn-journal.py` | **Escritor único** (D-02) | dono do arquivo |
| `cairn-lease.py` | Escreve `lease_changed` | shell-out via seam `CAIRN_JOURNAL`, best-effort, degrada em silêncio |
| `cairn-doctor.py` | Lê `last-moved` | `journal_last_moved()` — **puramente aditivo**: enriquece o texto de um item de conflito. Falha degrada a cláusula para nada, nunca a severidade nem o exit code |
| `cairn-reconcile.py` | Lê `last-moved` **e** `history` | monta o bundle de evidência e calcula `evidence_hash` sobre ele |
| `cairn-status.py` | 26 menções | superfície de leitura |
| `cairn-parallel.py` | 13 menções | classifica `observe`/`lease` como verbos de escrita para invalidação de cache |
| `cairn-config.py` | 1 menção | registra `journal.jsonl` na tabela de "um dono por arquivo" |
| `cairn-migrate.py` | 32 menções | **journal PRÓPRIO, outra coisa.** É o journal resumível por execução do migrate (`migrate-state.json`), não o `cairn-journal.py`. Não confundir: ele é o precedente do *idioma* JSONL nesta casa, não um consumidor deste arquivo |

**Achado com consequência:** o `cairn-reconcile.py` calcula `evidence_hash = sha256(bundle)` e o docstring afirma que *"two immediate, unchanged re-runs produce an identical hash"*. O bundle inclui `journal.history`. Mas `cmd_history` **já ordena** por `(ts, nonce)` antes de imprimir — então `history` já é determinístico sob merge. É o `last-moved` que não é. A superfície quebrada é menor e mais precisa do que parece à primeira vista. [VERIFICADO: `cairn-journal.py:853`, `cairn-reconcile.py:517-531`]

---

## A demonstração

Tudo abaixo foi construído e executado nesta sessão, em repositórios temporários descartáveis, fora do CairnGo. `git 2.42.1`, `Python 3.12.1`, `Darwin 25.4.0`. Saídas reproduzidas literalmente.

### E1 — Sem `.gitattributes` (o estado real do CairnGo hoje)

Dois ramos, cada um com 3 appends sobre uma base comum de 2 registros:

```
git: Auto-merging .cairn/journal.jsonl
git: CONFLICT (content): Merge conflict in .cairn/journal.jsonl
git: Automatic merge failed; fix conflicts and then commit the result.
  status: UU .cairn/journal.jsonl
  linhas: 11
```

**Leitura:** versionar o journal *sem fazer nada* é a pior opção de todas. Todo pull divergente vira conflito manual, e o arquivo fica com marcadores `<<<<<<<` dentro — que são, eles mesmos, linhas JSONL inválidas. Isso não é um cenário candidato; é o piso contra o qual todos os outros são medidos.

### E2 — Com `*.jsonl merge=union`, a mesma divergência

A máquina B tem o relógio 0,5 s atrasado, então seus `ts` ficam **intercalados** com os de A. É de propósito.

```
git: Merge made by the 'ort' strategy.
git:  .cairn/journal.jsonl | 3 +++

--- ORDEM FÍSICA no arquivo após o merge ---
  linha 1  nonce=n0000001  ts=10:00:00.000001  null->planned
  linha 2  nonce=n0000002  ts=10:00:01.000002  planned->executing
  linha 3  nonce=a0000001  ts=10:00:10.000001  executing->complete
  linha 4  nonce=a0000002  ts=10:00:11.000002  complete->verified
  linha 5  nonce=a0000003  ts=10:00:12.000003  verified->archived
  linha 6  nonce=b0000001  ts=10:00:09.500001  executing->blocked
  linha 7  nonce=b0000002  ts=10:00:10.500002  blocked->executing
  linha 8  nonce=b0000003  ts=10:00:11.500003  executing->complete
  total de linhas: 8   (esperado 8: 2 base + 3 A + 3 B)

--- a mesma lista ORDENADA por (ts, nonce) ---
  #1 n0000001  10:00:00.000001
  #2 n0000002  10:00:01.000002
  #3 b0000001  10:00:09.500001
  #4 a0000001  10:00:10.000001
  #5 b0000002  10:00:10.500002
  #6 a0000002  10:00:11.000002
  #7 b0000003  10:00:11.500003
  #8 a0000003  10:00:12.000003
```

**Duas leituras, e a segunda é a que interessa:**

1. **Reordenação: confirmada.** A ordem física é "todo o A, depois todo o B". A linha 6 (`10:00:09.5`) vem depois da linha 5 (`10:00:12.0`). Posição no arquivo não significa mais nada.
2. **Perda: zero.** 8 de 8. E ordenar por `(ts, nonce)` — que é exatamente o que `cmd_history` **já faz hoje** — recupera a ordem cronológica completa e correta.

Ou seja: para append puro, o `union` não é o problema que o requisito diz que é. A defesa já está no código.

### O `last-moved` de produção, sobre o arquivo mesclado do E2

Copiei o `journal.jsonl` mesclado do E2 para um diretório de projeto e rodei o script real:

```
$ python3 cairn-journal.py last-moved --phase 28 --json --project-dir <tmp>
{"disk": {"value": "complete", "ts": "2026-08-05T10:00:11.500003+00:00"}, ...}

$ # a MESMA dobra (_last_known), sobre os registros ordenados por (ts, nonce)
{"disk": {"value": "archived", "ts": "2026-08-05T10:00:12.000003+00:00"}}
```

**O código de produção devolve `complete`. A verdade é `archived`.** Não é uma hipótese sobre o que aconteceria: é a saída do `cairn-journal.py` que está no disco deste repositório, rodando sobre um arquivo que o git produziu. O motivo está escrito no próprio docstring de `_last_known()`: a dobra é em ordem de arquivo, e o comentário diz, literalmente, *"no re-sort needed here, unlike a hypothetically git-merged file"*. O "hipotético" deixa de ser hipotético no instante em que o arquivo é versionado. [VERIFICADO: execução direta]

### E3 — Linhas byte-idênticas em ramos diferentes

Duas máquinas gravam, independentemente, exatamente a mesma linha (sem `nonce`, timestamp com resolução de segundo):

```
  escritos: 2 eventos 'claimed' (um por máquina)
  sobreviveram: 1
```

**A dedup é real.** Um evento verdadeiro some sem erro, sem conflito, sem aviso.

### E4 — As mesmas duas linhas, com o `nonce` que o `cairn-journal.py` já escreve

```
  escritos: 2 eventos 'claimed'
  sobreviveram: 2
```

**A dedup já está resolvida.** O `nonce` uuid4 por registro, adicionado na fase 16 exatamente por causa do achado do `STACK.md`, torna duas linhas semanticamente iguais byte-diferentes. Metade da premissa do `DJOUR-01` descreve um bug que este projeto já corrigiu há um ciclo.

### E5 — Compactação de um lado, append do outro

`maqA` compacta 4 registros num snapshot. `maqB`, do outro ramo, appenda 1 registro. Merge:

```
  1 {"nonce":"snap1", "event":"snapshot", "compacted_through":4}
  2 {"nonce":"n1", "event":"state_changed", "seq":1}
  3 {"nonce":"n2", "event":"state_changed", "seq":2}
  4 {"nonce":"n3", "event":"state_changed", "seq":3}
  5 {"nonce":"n4", "event":"state_changed", "seq":4}
  6 {"nonce":"n5", "event":"state_changed", "seq":5}
  linhas: 6
```

Um humano esperaria 2 linhas (o snapshot mais o `n5`). O `union` devolveu 6: **ele ressuscitou os quatro registros que a compactação tinha dobrado**, e agora o mesmo fato está contado duas vezes — uma dentro do snapshot, uma como evento solto. O `union` não sabe que uma reescrita aconteceu; para ele, o lado que compactou "deletou linhas", e deletar é a única coisa que um driver de união não faz.

### E7 e E9 — o mesmo, com `compact()` de verdade

Usando o `cairn-journal.py` real, com `observe` real e `compact` real.

**E7 (ordem sortuda — o snapshot tem `ts` anterior ao append da outra máquina):** as duas dobras acertam, `complete`.

**E9 (ordem perigosa — a `maqB` grava antes, a `maqA` compacta depois):**

```
  maqB gravou disk=complete em ts=15:22:21.160286
  maqA gravou o snapshot em ts=15:22:22.571434  (POSTERIOR)
  linhas após o merge: 10  (o registro da maqB ESTÁ no arquivo)
  'disk=complete' da maqB sobreviveu ao merge? 1 ocorrência

  VERDADE: disk == 'complete'
  A) ordem de arquivo (código de hoje):     complete   ts=15:22:21.160286
  B) ordenado por (ts, nonce):              executing  ts=15:22:20.750047
```

**Este é o resultado que decide a fase.** Ordenar por `ts` — a correção óbvia, a de uma linha, aquela que qualquer um proporia — dá a resposta **errada**. O snapshot carrega o `ts` do momento da compactação, que é posterior a tudo que ele dobrou, então ele acaba dobrado por último e sobrescreve um evento real que veio da outra máquina. A linha está fisicamente presente no arquivo e não tem efeito nenhum.

### E12 — Existe conserto? O `compacted_through_ts`

O snapshot já grava `compacted_through_ts`, e o docstring diz que é *"provenance only; `_last_known()` never reads it"*. Testei uma dobra que **lê** esse campo: snapshots primeiro (ordenados por `compacted_through_ts`), depois apenas os eventos cujo `ts` é posterior ao ponto já dobrado.

```
  snapshot: ts=15:23:25.349  compacted_through_ts=15:23:23.611
  registro da maqB:  ts=15:23:23.911
  VERDADE: disk == 'complete'
  A) ordem de arquivo:                complete   ✔
  B) ordenado por ts:                 executing  ✘
  C) ciente de compacted_through_ts:  complete   ✔
```

**Funciona.** Um campo que hoje é decorativo vira carga estrutural. Isso é um conserto real e barato — e ainda assim não é suficiente, pelos dois motivos seguintes.

### E13 — As duas máquinas compactam

`maqA` viu `disk=executing` e compactou. `maqB` viu `disk=blocked` e compactou. Merge:

```
  linhas após o merge: 2
    snapshot  ts=15:23:26.650  through=15:23:26.585  disk=executing
    snapshot  ts=15:23:28.091  through=15:23:28.033  disk=blocked
  C) ciente de compacted_through_ts:  blocked
```

**A história inteira da `maqA` desapareceu.** Não um registro: tudo que ela tinha observado, dobrado dentro de um snapshot que o snapshot mais novo sobrescreve por inteiro. Nenhum conflito do git, nenhum erro, um JSONL válido de duas linhas no fim. Nenhum teste comum pegaria isso.

Isto **não** é conserto de leitura. Um snapshot é uma afirmação totalizante ("este é o estado da fase X até T"), e duas afirmações totalizantes concorrentes sobre o mesmo objeto não se compõem. Só há três saídas: matar a compactação, particionar quem pode compactar o quê, ou trocar snapshot por algo comutativo — e "algo comutativo" é a definição de CRDT, o que nos leva de volta ao custo.

### E14 — Desvio de relógio

Snapshot cobre até `10:00:20`. A `maqB`, com relógio 10 s atrasado, grava `complete` com `ts=10:00:15` — no tempo real, **depois**.

```
  C) ciente de compacted_through_ts:  executing
  ^^ o registro está no arquivo e não tem efeito nenhum
```

O conserto do E12 depende de os `ts` de máquinas diferentes serem comparáveis. Eles não são.

**Quanto isso importa, medido:** rodei quatro `observe` reais e medi o espaçamento entre registros consecutivos, e medi o desvio NTP desta máquina.

```
registros: 8
janela total: 284,1 ms
delta entre registros consecutivos (ms): 12.26 17.68 12.82 10.83 70.04 82.97 77.49
delta MÍNIMO:  10,832 ms
delta MEDIANO: 17,682 ms

$ sntp -d time.apple.com
-0.016695 +/- 0.007931   →  desvio desta máquina: -16,7 ms ± 7,9 ms
```

**O desvio de relógio de uma única máquina bem sincronizada (16,7 ms) é maior que o intervalo mínimo entre dois registros do journal (10,8 ms) e praticamente igual ao mediano (17,7 ms).** Duas máquinas, cada uma com seu próprio desvio, podem divergir por ~33 ms — o equivalente a duas ou três posições na ordenação.

Isto é uma medição, não uma extrapolação de cenário catastrófico: a resolução de ordenação de que o journal precisa é **mais fina do que o acordo de relógio que ele pode assumir entre máquinas**. Qualquer desenho que ordene eventos cross-máquina por `ts` está construindo uma linha do tempo que parece autoritativa e não é.

**Ressalva honesta:** isso só morde quando duas máquinas escrevem o **mesmo eixo da mesma fase** dentro da janela de desvio. Para transições de estado de fase, separadas por horas, é irrelevante. E é justamente esse cenário concorrente que o `cairn-lease.py` existe para impedir. O risco é real e estreito. Não é o argumento principal contra versionar; é o que impede a linha do tempo mesclada de ser confiável quando alguém mais precisa dela.

### E6 — Hash-chain sob `merge=union`

Duas máquinas, cada uma estendendo a mesma ponta (`prev` = o mesmo hash), com dois registros cada:

```
  seq=1 ev=state_changed prev=000000000000 hash=f52b0c255bda
  seq=2 ev=state_changed prev=f52b0c255bda hash=d9d8d95cca9c
  seq=3 ev=A3     prev=d9d8d95cca9c hash=839385a08167
  seq=4 ev=A4     prev=839385a08167 hash=e071d7950bee
  seq=3 ev=B3     prev=d9d8d95cca9c hash=572b1d2f0e5c
  seq=4 ev=B4     prev=572b1d2f0e5c hash=54e78fd346b9

  --- validação linear da cadeia ---
  QUEBRA na linha 5: esperava prev=e071d7950bee, achou prev=d9d8d95cca9c
  cadeia linear válida: False
  pontas (hashes que ninguém aponta): ['e071d7950bee', '54e78fd346b9'] -> 2 cabeças, não 1
```

**A hash-chain não sobrevive ao merge, e o motivo é conceitual, não de implementação.** Uma cadeia de hash codifica uma **ordem total de escrita**. Duas máquinas escrevendo offline não têm ordem total de escrita — é a definição de trabalho concorrente. O resultado do merge não é uma cadeia quebrada por bug: é um **DAG de Merkle com duas cabeças**, que é a estrutura correta para o que aconteceu e a estrutura errada para o verificador linear que qualquer um escreveria.

Fazer isso direito significa: detectar as cabeças, achar o ancestral comum, ordenar os ramos por algum critério de desempate determinístico, e materializar. Isso é reimplementar o modelo de objetos do git dentro de um JSONL — dentro de um repositório git. Em stdlib pura, sem dependência de terceiro, conforme o `CONVENTIONS.md` exige.

**E ainda tem o problema de fundo, que é o que realmente mata:** uma hash-chain existe para dar **evidência de adulteração**. Ela responde "alguém mexeu no que já estava escrito?". O `DJOUR-03` diz que o journal **não é autoridade sobre nada** e que **apagá-lo não muda veredito nenhum**. Um artefato que não decide nada não tem o que ser adulterado com proveito. A hash-chain resolve um problema que este projeto não tem, ao custo de quebrar sob a única operação que a fase existe para suportar. **Rejeitada.**

### E15 — O `union` vale para `rebase`, `cherry-pick` e `pull`?

Isto importa porque o fluxo desta casa é `git pull --rebase` (está no `CLAUDE.md` da sessão de fechamento). Um driver que só valesse no `merge` explícito seria inútil.

```
E15a  git rebase main            → 3 linhas, 0 conflitos, 0 marcadores
E15b  git cherry-pick maqA       → 3 linhas, 0 conflitos
E15c  git pull --rebase (remoto) → 3 linhas, 0 conflitos
E15d  git pull (merge)           → 4 linhas, 0 conflitos
```

**O `union` vale em todos os quatro caminhos.** [VERIFICADO: repositórios bare + dois clones reais]

### E16 e E17 — De quem é o driver: do repositório ou da cópia?

```
E16: .gitattributes presente no clone? sim
     merge.union.driver em algum config? (nenhum — union é built-in)

E17: *.jsonl merge=cairnjournal, SEM merge.cairnjournal.driver no config
     git: CONFLICT (content): Merge conflict in .cairn/journal.jsonl
     linhas: 6   marcadores: 1
```

**Achado decisivo contra o driver próprio.** `.gitattributes` é um arquivo rastreado, então ele viaja com o clone — e `union` é built-in, não precisa de config nenhuma em lugar nenhum. Um driver **próprio**, ao contrário, exige uma entrada `merge.<nome>.driver` no `.git/config`, e **git nunca clona config**. Numa máquina sem esse passo de setup, o driver simplesmente não existe e o git cai no merge padrão: conflito, com marcadores, exatamente o E1. A correção do arquivo passaria a depender de configuração fora de banda, por clone, que ninguém lembra de fazer.

### E10 e E11 — Particionar

```
E11 caso 1 (duas máquinas, arquivos diferentes):
     Merge made by the 'ort' strategy. → 3 registros, 0 conflitos
E11 caso 2 (mesma máquina, dois worktrees, MESMO arquivo, com union):
     Auto-merging alice.jsonl → 3 registros, 0 conflitos

E8b  (mesma máquina, mesmo arquivo, SEM union):
     CONFLICT (add/add): Merge conflict in .cairn/journal/alice-macbook.jsonl

E10  (compactação que APAGA arquivos de partição, com append do outro lado):
     CONFLICT (modify/delete): .cairn/journal/bob.jsonl deleted in HEAD
                               and modified in appendou
```

**Particionar por máquina funciona, e funciona bem** — mas só quando composto com `union` em cada partição (E8b mostra que sozinho não basta: a mesma máquina em dois worktrees conflita). E `E10` mostra que apagar partições na compactação reintroduz conflito, agora do tipo `modify/delete`, que é pior de resolver que o de conteúdo.

---

## Mapa de responsabilidade arquitetural

| Capacidade | Camada dona | Camada secundária | Por quê |
|---|---|---|---|
| Unicidade global de registro | Escritor (`cairn-journal.py`) | — | O `nonce` uuid4 é gerado no append. Nenhuma camada posterior pode inventá-lo. **Já resolvido** |
| Atomicidade do append | Kernel (POSIX `O_APPEND`) | Escritor | Uma `os.write()` por registro. **Já resolvido** |
| Preservação de registro no merge | Git (`merge=union`) | `.gitattributes` (rastreado) | Só o git vê os dois lados. E17 prova que só o `union` built-in funciona sem setup por clone |
| Ordenação cronológica | **Leitor** | — | Posição no arquivo é destruída pelo merge (E2). Ordenação **tem** que ser derivada de campo interno, na leitura. `cmd_history` já faz; `_last_known` não |
| Ordem causal entre máquinas | **Ninguém** | — | Não existe fonte. `ts` não serve (E14, desvio 16,7 ms vs. gap mínimo 10,8 ms). Exigiria relógio lógico (Lamport/vetorial), que o cairn não tem |
| Limite de crescimento | `compact()` | — | **Incompatível com um arquivo mesclado** (E5, E13). É aqui que o desenho quebra |
| Autoridade sobre o estado | `cairn-status.py` `corroborate()` | — | Por `DJOUR-03`, **nunca** o journal |

A linha que decide tudo é a penúltima: **a compactação é a única capacidade cuja camada dona é incompatível com a camada que o requisito quer introduzir.**

---

## As alternativas, e o que cada uma custa

Filtro obrigatório em toda linha: o `DJOUR-03` diz que o journal versionado **continua sem ser autoridade sobre o estado corrente, e apagá-lo não muda veredito nenhum**.

### 1. Hash-chain linear (`prev_hash`) — a alternativa que o requisito nomeia

| | |
|---|---|
| **Resolve** | Nada do que a fase precisa. Detecta adulteração retroativa, que ninguém pediu |
| **Não resolve** | Reordenação (a cadeia nem sobrevive: E6, 2 cabeças). Perda por compactação. Desvio de relógio |
| **Custa** | Ou um verificador linear que falha em todo merge, ou um resolvedor de DAG de Merkle escrito à mão em stdlib |
| **Sobrevive ao DJOUR-03?** | **Não.** Uma cadeia verificável convida a ser tratada como fonte de verdade. É a estrutura de dados da autoridade. O `DJOUR-03` proíbe exatamente essa gravidade |
| **Veredito** | **REJEITADA**, medida (E6) |

### 2. `merge=union` cru, sem mais nada

| | |
|---|---|
| **Resolve** | Conflito no merge (E1 → E2). Zero perda em append puro. Vale em rebase/cherry-pick/pull (E15). Zero config por clone (E16) |
| **Não resolve** | `_last_known()` passa a mentir (medido: `complete` em vez de `archived`). `compact()` corrompe (E5, E13) |
| **Custa** | Uma linha no `.gitattributes`. Uma linha no `.gitignore` (removida) |
| **Sobrevive ao DJOUR-03?** | **Sim.** Um arquivo mesclado não ganha autoridade nenhuma por ser mesclado |
| **Veredito** | **INSUFICIENTE SOZINHA.** É condição necessária de qualquer desenho versionado, nunca o desenho inteiro |

### 3. Ordenação total por chave determinística `(ts, nonce)` na leitura

| | |
|---|---|
| **Resolve** | Reordenação, completamente, para append puro (E2: os 8 registros voltam à ordem certa) |
| **Não resolve** | Compactação — dá a resposta **errada** (E9: `executing` em vez de `complete`). Desvio de relógio (E14) |
| **Custa** | Um `sort` em `_last_known()`, mais reescrever um docstring que hoje afirma o contrário |
| **Sobrevive ao DJOUR-03?** | **Sim** |
| **Veredito** | **NECESSÁRIA, INSUFICIENTE.** E a variante ciente de `compacted_through_ts` (E12) conserta o E9 mas não conserta o E13 |

### 4. CRDT de conjunto append-only (G-Set)

| | |
|---|---|
| **Observação** | **O cairn já implementa um G-Set, por acidente.** Elemento = registro; id do elemento = `nonce`; merge = união de conjuntos = `merge=union`; materialização = dobra ordenada. As três peças já existem |
| **Resolve** | Tudo que o `union` + ordenação resolve, com a garantia formal por trás: união de conjuntos é comutativa, associativa e idempotente |
| **Não resolve** | **A compactação, porque compactar é remover, e um G-Set não tem remoção.** Essa é a definição, não uma limitação de implementação. Trocar por 2P-Set ou OR-Set adiciona tombstones, que crescem para sempre — o oposto do que a compactação quer |
| **Custa** | Zero para adotar o vocabulário. **Alto** para adicionar remoção corretamente, e nenhuma biblioteca é permitida (`CONVENTIONS.md`) |
| **Sobrevive ao DJOUR-03?** | **Sim**, e é a alternativa que se encaixa mais naturalmente nele: um G-Set não afirma "o estado é X", só "estes fatos foram observados" |
| **Veredito** | **É a moldura correta para entender o desenho atual**, e ela diz claramente por que a compactação é o ponto de ruptura. Não é uma quinta opção; é o nome do que já existe |

### 5. Merge driver próprio (`merge=cairn-journal`)

| | |
|---|---|
| **Resolve** | Poderia ordenar e dobrar snapshots no momento do merge |
| **Não resolve** | Rebase interativo, edição manual, `git checkout --theirs`, ou qualquer caminho onde o driver não roda. **O leitor tem que ordenar de qualquer jeito**, então o driver é trabalho duplicado |
| **Custa** | **Alto, e o custo é do tipo errado.** E17, medido: sem `merge.cairn-journal.driver` no `.git/config`, o git cai no merge padrão e conflita. Config não é clonada. Toda máquina precisa de um passo de setup manual; o `cairn-doctor` precisaria de um check novo só para detectar a ausência; e a máquina não configurada falha **em silêncio-conflito**, o pior modo |
| **Sobrevive ao DJOUR-03?** | Sim |
| **Veredito** | **REJEITADA.** Move a correção para a camada errada e faz a corretude depender de setup fora de banda, por clone |

### 6. Particionar: um arquivo por máquina/ator

| | |
|---|---|
| **Resolve** | Máquinas diferentes nunca tocam o mesmo arquivo (E11 caso 1: zero conflito, sem driver nenhum). Composto com `union`, a mesma máquina em dois worktrees também mescla limpo (E11 caso 2). **E torna o E13 impossível por construção**: duas máquinas nunca compactam os mesmos bytes |
| **Não resolve** | Sozinho, a mesma máquina em dois ramos conflita (E8b). Apagar partições ao compactar dá `modify/delete` (E10). Desvio de relógio continua |
| **Custa** | Layout novo de caminhos, leitor que varre diretório, migração do journal local existente, atualização dos 5 consumidores, `.gitattributes`, testes |
| **Sobrevive ao DJOUR-03?** | **Sim** |
| **Veredito** | **É a única alternativa estruturalmente correta se a decisão for versionar.** Detalhada abaixo |

### 7. Não versionar — manter local e gitignorado

| | |
|---|---|
| **Resolve** | Todos os problemas medidos, por não os ter. O invariante de escritor único vale, então ordem de arquivo **é** ordem cronológica e o `_last_known()` está certo hoje |
| **Não resolve** | Forense entre máquinas. A máquina A nunca sabe quando o eixo `bd` se moveu na máquina B |
| **Custa** | Zero em código. O custo é o valor abandonado |
| **Sobrevive ao DJOUR-03?** | **Trivialmente** |
| **Veredito** | **RECOMENDADA** |

---

## Recomendação

**Manter o journal local e gitignorado. Entregar a decisão, não o código.**

Três razões, em ordem de peso.

### 1. O que se ganha é pequeno e já degrada bem

Todo consumidor cross-máquina do journal é **aditivo por desenho**, e cada um já tem um caminho de degradação testado:

- `cairn-doctor.py` → `journal_last_moved()` enriquece o texto de um item de conflito. O docstring: *"a broken or missing journal degrades that one item's trailing clause to nothing (no clause at all), never the item's severity, never this check's own status/exit code."*
- `cairn-reconcile.py` → `journal_history()` devolve `[]` em qualquer falha, e o bundle segue.

O `DJOUR-03` não é uma restrição incômoda que o desenho precisa contornar: é a declaração de que **este artefato não decide nada**. Um artefato que não decide nada não justifica um redesenho distribuído. Se o journal sumir inteiro, o `corroborate()` continua dando o mesmo veredito para todas as 18 fases.

### 2. O que se perde é maior do que parece, e o custo é assimétrico

Versionar direito significa a opção 6 completa: partições, segmentos selados, leitor novo, compactação redesenhada, cinco consumidores atualizados, migração do journal local de 141 registros, `.gitattributes`, e testes para cada um dos modos de falha medidos aqui. Sobre a fase que o próprio `ROADMAP.md` marca como *"a de maior risco"*.

E o modo de falha do desenho versionado **não é ruidoso**. O E13 produz um JSONL válido, sem conflito, sem erro, com a história de uma máquina inteira faltando. Contra isso, o modo de falha de não versionar é: a máquina A não tem o dado da máquina B, o que é óbvio, imediato e inofensivo.

**Trocar "não tenho o dado" por "tenho um dado silenciosamente errado" é um mau negócio numa superfície forense** — que é, por definição, onde alguém vai olhar justamente quando já está confuso.

### 3. A alternativa que o requisito nomeia foi medida e é a pior das sete

O `DJOUR-01` enquadra a escolha como "hash-chain versus `merge=union` cru". A medição diz que o enquadramento está errado nas duas pontas: o `union` **não** perde registro com o formato atual (E2, E4 — a metade "deduplica" da premissa descreve um bug que a fase 16 já corrigiu com o `nonce`), e a hash-chain **não sobrevive** ao merge (E6) enquanto colide de frente com o `DJOUR-03`. O que quebra é a compactação, que não aparece em nenhuma das duas pontas do requisito.

### Por que as outras perderam

| Alternativa | Motivo da derrota |
|---|---|
| Hash-chain | Quebra sob merge (medido, E6); é a estrutura de dados da autoridade, que o `DJOUR-03` proíbe |
| `union` cru | Necessária, nunca suficiente: `_last_known()` passa a mentir e `compact()` corrompe |
| Ordenação por `(ts, nonce)` | Conserta o E2, erra o E9. Não é desenho, é uma peça |
| CRDT G-Set | Já é o que existe. Não tem remoção, e compactar é remover |
| Driver próprio | Corretude dependente de config não clonada (medido, E17); falha em conflito silencioso na máquina não configurada |
| Particionar | Estruturalmente correto, e o único caminho se a decisão for versionar. Perde por **custo desproporcional ao valor**, exatamente o critério que o `ROADMAP.md` escreveu |

### O que a fase 28 entrega, então

1. **A decisão, registrada onde ela é lida.** Este documento, mais uma atualização do docstring do `cairn-journal.py`. Hoje ele diz que o journal é local *"not because a `merge=union` flat-file strategy was tried here and then fixed, but because this file was never meant to be shared"* e que manter local *"sidesteps that question instead of solving it"*. Depois desta pesquisa, a questão foi resolvida: passa a ser uma decisão medida, com os números, e não mais um desvio. Além disso, um `bd remember` com o veredito, conforme o `CLAUDE.md`.

2. **Um guarda-corpo, porque hoje não existe nenhum.** O `.gitignore:8` tem `.cairn/journal.jsonl*`, e **nada testa isso**. Nenhum dos 16 testes do `cairn-journal.bats` afirma que o journal é ignorado. Um `git add -f` casual, ou uma reescrita futura do `.gitignore`, versiona o arquivo em silêncio — e a partir daí o `last-moved` começa a mentir no primeiro merge divergente, sem nenhum sinal. O guarda-corpo é: um teste que afirma que o caminho está ignorado e não rastreado, e um achado de `cairn-doctor` com severidade `fail` se o journal aparecer rastreado. Custo baixo, e é o que impede esta decisão de apodrecer.

3. **Opcional, e barato: o conserto do E12.** Fazer `_last_known()` ler o `compacted_through_ts` em vez de confiar em ordem de arquivo. Não é necessário enquanto o journal for local e de escritor único — a ordem de arquivo é cronológica por construção. É seguro contra o dia em que alguém versionar assim mesmo. **Recomendo apresentar como opção ao humano, não decidir sozinho:** é código especulativo contra um cenário que a decisão acima diz que não vai acontecer, e a casa não gosta de código especulativo.

---

## Se a decisão humana for versionar assim mesmo: o desenho correto

Registrado aqui para que essa escolha seja uma linha de decisão, e não outro ciclo de pesquisa. **Não é a recomendação.**

```
.cairn/journal/
  <ator>-<host>-0001.jsonl     ← selado, imutável, nunca reescrito
  <ator>-<host>-0002.jsonl     ← ativo; primeira linha é um snapshot
.gitattributes:  .cairn/journal/*.jsonl merge=union
```

| Regra | Motivo medido |
|---|---|
| Uma partição por `(ator, host)` | E11 caso 1: máquinas diferentes nunca tocam o mesmo arquivo |
| `merge=union` em cada partição | E11 caso 2 / E8b: a mesma máquina em dois worktrees precisa disso |
| **Nunca reescrever um segmento.** Compactar = selar o atual e abrir um novo cuja primeira linha é um `snapshot` com `compacted_through_ts` | E5: reescrever faz o `union` ressuscitar o que foi dobrado. E10: apagar dá `modify/delete` |
| **Nunca apagar um segmento selado** | E10 |
| Leitor: varre o diretório, dobra os snapshots por `compacted_through_ts`, depois os eventos posteriores, ordenados por `(ts, nonce)` | E12 |
| Compactação restrita à própria partição | E13 vira impossível por construção |
| A cláusula de forense do doctor **nomeia o ator/host de cada eixo** e nunca ordena eventos de máquinas diferentes entre si | E14: 16,7 ms de desvio contra 10,8 ms de gap mínimo |

**Contrapartida honesta que este desenho aceita:** compactar um arquivo versionado não economiza nada durável. **Toda versão fica no histórico do git para sempre.** A compactação só encurta o arquivo de trabalho, isto é, o tempo de leitura. Segmentos selados dão o mesmo ganho de leitura sem reescrever nada. Se este caminho for escolhido, `JOURNAL_COMPACT_THRESHOLD_BYTES` passa a significar "sele o segmento", não "reescreva o arquivo".

**Esforço estimado: 4 a 6 planos.** [SUPOSTO — extrapolado do tamanho dos consumidores (5 scripts, 47 KB no escritor, 16 testes existentes), não medido contra fases comparáveis deste projeto.]

---

## O teste do `DJOUR-02`

O requisito exige *"provado por teste que mescla dois journals divergentes"*. Sob a recomendação, esse teste muda de alvo, mas **não** desaparece — e a regra da casa continua valendo: **um teste que passaria com a feature removida não é prova.**

### Teste A — o invariante, o que a decisão realmente promete

`tests/cairn-journal.bats`, no estilo dos 16 já lá.

```
@test "o journal e' e continua local: ignorado pelo git e nunca rastreado" {
```

**Constrói:** um repositório git de fixture com o `.gitignore` do projeto; roda um `observe` real para criar `.cairn/journal.jsonl`.

**Afirma:**
1. `git check-ignore -q .cairn/journal.jsonl` sai 0.
2. `git ls-files --error-unmatch .cairn/journal.jsonl` sai **não-zero** (não rastreado).
3. `git status --porcelain` **não** menciona o journal (nem como não rastreado — o ignore cobre).
4. O glob cobre os irmãos: `journal.jsonl.tmp-*` e `journal.jsonl.compact.lock` também ignorados.

**O que o deixa vermelho:** remover a linha 8 do `.gitignore`; estreitar o glob para `journal.jsonl` sem o `*` (quebra 4); um `git add -f` deixado num fixture. Nenhuma dessas quebras é detectável hoje.

### Teste B — a divergência, o que o `DJOUR-02` literalmente pede

Este é o teste que **mede o motivo da decisão** e o mantém verdadeiro. Ele constrói a divergência exatamente como o requisito manda, e afirma que o resultado é a falha documentada — de modo que, se algum dia deixar de falhar, alguém vá reler esta pesquisa.

```
@test "por que o journal nao e' versionado: um journal mesclado faz last-moved mentir" {
```

**Constrói:**
1. Repositório temporário com `*.jsonl merge=union` no `.gitattributes` (a configuração hipotética, montada só dentro do teste).
2. Base comum: dois `observe` reais para a fase 28.
3. Ramo `maqA`: três `observe` levando `disk` até `archived`, timestamps crescentes.
4. Ramo `maqB`: três `observe` com timestamps **intercalados** com os de A, terminando em `complete`, mais cedo que o último de A.
5. `git merge maqB`.

**Afirma, nesta ordem:**
1. O merge sai 0 e **sem** marcadores de conflito. *(Fixa o E2: o `union` funciona.)*
2. O arquivo tem **8** registros: nenhum perdido. *(Fixa o E2 e o E4: o `nonce` impede a dedup.)*
3. `cairn-journal.py history --phase 28 --json` devolve os 8 **em ordem cronológica** — porque `cmd_history` já ordena por `(ts, nonce)`. *(Fixa a metade que já está certa.)*
4. **A afirmação carregada:** `cairn-journal.py last-moved --phase 28 --json` devolve `disk == "complete"`, enquanto a dobra sobre os mesmos registros ordenados devolve `disk == "archived"`. **O teste afirma que os dois discordam**, e o comentário diz por quê: `_last_known()` dobra em ordem de arquivo.

**O que o deixa vermelho, e por que isso é a prova:**

| Quebra | Qual asserção cai |
|---|---|
| Alguém "conserta" `_last_known()` com um `sort` sem entender o E9 | 4 — os dois passam a concordar, e o teste força a leitura desta pesquisa antes do merge do PR |
| O `nonce` é removido do envelope | 2 — cai de 8 para menos |
| `cmd_history` perde o `sort` | 3 |
| `.gitattributes` é removido do fixture | 1 — vira conflito |
| A feature é "removida" (nada muda no código) | O teste **não** passa vazio: as asserções 2, 3 e 4 medem comportamento real do script sobre um arquivo real que o git produziu |

Este segundo teste é o que impede o `DJOUR-02` de virar folclore ao contrário. Ele mescla dois journals divergentes de verdade, como o requisito manda, e o que ele prova é a **razão da decisão**, não a decisão.

### Teste C — o achado do doctor

```
@test "doctor: journal rastreado pelo git e' um achado fail" {
```

**Constrói:** fixture com o journal **rastreado** (`git add -f`). **Afirma:** `cairn-doctor.py` reporta um achado nomeado, severidade `fail`, e sai com `EXIT_FAILED`. **Vermelho quando:** o check não existe, ou é `warn`. Severidade `fail` e não `warn` porque um journal rastreado não é atrito: é uma condição sob a qual uma superfície do cairn começa a dar resposta errada em silêncio.

---

## Não faça à mão

| Problema | Não construa | Use | Por quê |
|---|---|---|---|
| Mesclar appends concorrentes | Um driver de merge próprio | `merge=union` built-in, **se algum dia versionar** | E17 medido: driver próprio precisa de config que o git não clona; a máquina sem setup falha em conflito silencioso |
| Ordem total entre máquinas | Comparar `ts` de máquinas diferentes | Nada — não afirme ordem cross-máquina | E14 medido: 16,7 ms de desvio contra 10,8 ms de gap mínimo. A resolução necessária é mais fina que o acordo disponível |
| Detectar reordenação | Um verificador de hash-chain | Ordenar por `(ts, nonce)` na leitura | E6: a cadeia quebra sob merge por definição, não por bug |
| Unicidade de registro | Timestamp de alta resolução como desempate | O `nonce` uuid4 que já existe | E3 vs. E4, medidos |
| Limitar crescimento de um arquivo **versionado** | `compact()` reescrevendo o arquivo | Segmentos selados, se versionar | E5, E13. E o histórico do git guarda tudo de qualquer jeito: compactar um arquivo versionado não economiza nada durável |
| Confiar na posição da linha | Qualquer leitura que dependa de ordem de arquivo | Campo de ordenação interno, sempre | É o que `_last_known()` faz hoje, e o que o torna correto localmente e errado sob merge |

**A ideia central:** este domínio parece um problema de formato de arquivo e é um problema de sistemas distribuídos. Toda solução caseira que trata "ordenar linhas" como a dificuldade erra o alvo — a dificuldade é que não existe uma ordem para descobrir.

---

## Armadilhas

### 1. Consertar `_last_known()` com um `sort` e achar que acabou

**O que dá errado:** ordenar por `(ts, nonce)` conserta o E2 e **quebra** o E9 — devolve `executing` onde a verdade é `complete`, porque o `ts` do snapshot é posterior a tudo que ele dobrou.
**Por que acontece:** é a correção óbvia, ela passa no teste óbvio, e o caso que ela quebra exige compactação e divergência ao mesmo tempo.
**Como evitar:** o Teste B acima afirma explicitamente que a dobra em ordem de arquivo e a dobra ordenada **discordam**, então esse "conserto" fica vermelho.
**Sinal de alerta:** um PR que adiciona `records.sort(...)` em `_last_known()` sem tocar em `compacted_through_ts`.

### 2. Achar que o `union` perde registros

**O que dá errado:** o desenho se defende de um problema que não existe (E2: 8 de 8) e ignora o que existe (E13).
**Por que acontece:** o `DJOUR-01` afirma "reordena e deduplica" numa frase só, e a dedup foi retirada de cena pelo `nonce` na fase 16.
**Como evitar:** ler o E4.

### 3. Achar que a compactação é um detalhe de performance

**O que dá errado:** o desenho versionado é planejado como se `compact()` fosse ortogonal, e o E13 aparece em produção — silenciosamente.
**Por que acontece:** a compactação é hoje uma otimização local e invisível, com 200 KiB de gatilho e 28 KB de arquivo real. Parece longe.
**Como evitar:** 5,6 KB/dia medidos → o gatilho dispara em ≈ 36 dias.
**Sinal de alerta:** qualquer plano de versionamento que não tenha uma tarefa nomeada sobre `compact()`.

### 4. Confiar num driver próprio sem checar a config

**O que dá errado:** funciona na máquina de quem construiu e conflita em todas as outras.
**Como evitar:** E17. `.gitattributes` é rastreado; `.git/config` não é clonado.
**Sinal de alerta:** um `.gitattributes` com `merge=<qualquer coisa que não seja union, binary, text ou ours>`.

### 5. Deixar a decisão sem guarda-corpo

**O que dá errado:** a decisão vive num markdown que ninguém relê, e o `.gitignore` muda um ano depois.
**Por que acontece:** nada testa a linha 8 do `.gitignore` hoje. Os 16 testes de `cairn-journal.bats` não a mencionam.
**Como evitar:** Testes A e C.

### 6. Confundir o journal do `cairn-migrate.py` com este

**O que dá errado:** o `cairn-migrate.py` tem 32 menções a "journal" e **nenhuma** delas é sobre o `cairn-journal.py` — é o journal resumível por execução do próprio migrate. Um grep ingênuo trata os dois como o mesmo sistema.
**Como evitar:** o consumidor real do `cairn-journal.py` é quem usa o seam `CAIRN_JOURNAL`: `cairn-lease.py` (escrita), `cairn-doctor.py` e `cairn-reconcile.py` (leitura).

---

## Escopo redefinido

O `ROADMAP.md` diz que esta é *"a única cujo escopo a própria pesquisa pode redefinir"*. Redefinindo:

| Como o ROADMAP descreve | O que a pesquisa conclui |
|---|---|
| *"o journal atravessa máquinas sem que o merge reordene ou perca registro"* | **Não vai atravessar máquinas.** O card muda para: *"a decisão sobre versionar o journal é tomada com números, e trancada contra regressão silenciosa"* |
| Critério 1: hash-chain decidida antes de qualquer implementação | **Atendido.** Rejeitada, medida (E6) |
| Critério 2: dois journals divergentes mesclados sem reordenar e sem perder registro | **Não sobrevive.** Vira: dois journals divergentes são mesclados **num teste**, e o teste prova que o resultado faz o `last-moved` mentir — que é a razão de não versionar (Teste B) |
| Critério 3: apagar o journal continua não mudando veredito nenhum | **Preservado e reforçado.** Não versionar é a forma mais forte desse critério |
| *"é a única cujo escopo a própria pesquisa pode redefinir"* | Exercido |

**Tamanho da fase depois disso: 1 a 2 planos** (docstring + `bd remember` + três testes + um check de doctor), contra 4 a 6 do caminho versionado. [SUPOSTO — estimativa, não medida contra fases comparáveis.]

---

## Auditoria de legitimidade de pacotes

**Não aplicável, com motivo:** nenhuma alternativa recomendada aqui instala pacote externo. O `CONVENTIONS.md` proíbe dependência de terceiro (`filelock`, `fasteners`, `portalocker`, `GitPython`, `pygit2`, `dulwich` estão todos na tabela "What NOT to Use" do `STACK.md`), e cada primitiva usada nesta pesquisa é stdlib do Python 3 (`os`, `fcntl`, `json`, `uuid`, `hashlib`, `datetime`, `subprocess`) ou o binário `git` já exigido. **Pacotes removidos por veredito SLOP: nenhum. Pacotes marcados SUS: nenhum.**

Bibliotecas de CRDT foram consideradas conceitualmente e **descartadas antes de qualquer busca em registro**, pela restrição stdlib-only — nenhum nome de pacote foi pesquisado, e nenhum é recomendado.

---

## Disponibilidade do ambiente

| Dependência | Necessária para | Disponível | Versão | Alternativa |
|---|---|---|---|---|
| `git` | `merge=union`, `check-ignore`, `ls-files` | Sim | 2.42.1 | — |
| `python3` | os scripts | Sim | 3.12.1 | — |
| `bd` (beads) | rastreio de trabalho remanescente | Sim | 1.1.0 (Homebrew) | — |
| `bats-core` | os três testes | Assumido presente (39 arquivos `.bats` em `tests/`) | não medido | — |
| `fcntl` | lock de compactação | Sim (POSIX; Darwin 25.4.0) | stdlib | — |
| Sincronização NTP | ordenação cross-máquina | Parcial: desvio de −16,7 ms ± 7,9 ms medido nesta máquina contra `time.apple.com` | — | **Nenhuma.** É por isso que a ordenação cross-máquina não é oferecida |

**Sem dependência faltando que bloqueie.** A única "faltando" é o relógio comum, e ela é premissa do problema, não item de instalação.

---

## Domínio de segurança

Superfície mínima: nenhuma entrada de rede, nenhuma autenticação, nenhum dado de usuário. Um ponto merece registro porque é o único lugar onde uma decisão de segurança foi tomada:

| Categoria ASVS | Aplica | Nota |
|---|---|---|
| V5 Validação de entrada | Sim | `_parse_records()` já põe em quarentena linha malformada por offset de byte, sem abortar a leitura. Coberto por 3 testes de torn-tail |
| V6 Criptografia | **Deliberadamente não** | A hash-chain foi rejeitada. Registrar o motivo: SHA-256 encadeado dá **evidência de adulteração**, e o `DJOUR-03` diz que este artefato não é autoridade e pode ser apagado sem consequência. Adicionar integridade criptográfica a um artefato descartável é teatro de segurança, e pior: cria a impressão de autoridade que o requisito proíbe |
| V7 Log e monitoramento | Parcial | O journal é forense, não trilha de auditoria. Não é adequado para auditoria de conformidade e **não deve ser apresentado como tal** — não é resistente a adulteração, e por decisão não vai ser |

**Padrão de ameaça mais próximo:** "trilha de auditoria falsa" — um artefato que parece autoritativo e não é. O E13 é a versão mecânica disso (uma história inteira somindo em silêncio). A recomendação evita a classe inteira.

---

## Registro de suposições

| # | Afirmação | Seção | Risco se errada |
|---|---|---|---|
| A1 | Esforço de 4–6 planos para o desenho particionado | Se a decisão for versionar | Se for muito menor, o custo/benefício muda e versionar pode valer. **Um humano deveria contestar este número se discordar** |
| A2 | Esforço de 1–2 planos para a fase redefinida | Escopo redefinido | Baixo |
| A3 | `bats-core` está instalado e funcional | Ambiente | Baixo — 39 `.bats` existem, mas não rodei a suíte nesta sessão |
| A4 | O desvio NTP medido (−16,7 ms) é representativo de máquinas típicas | E14 | Médio. É **uma** medição, de **uma** máquina, contra **um** servidor. Máquinas em rede pior desviam mais (o argumento fica mais forte); em datacenter com PTP, muito menos (mais fraco). Não medi uma segunda máquina |
| A5 | O ritmo de 5,6 KB/dia continua, então a compactação dispara em ~36 dias | Ponto de partida | Médio. Extrapolação linear de 5 dias de 1 ator. Mais fases em paralelo aceleram |
| A6 | O comportamento do `merge=union` é o mesmo em Linux e em versões mais novas do git | Demonstração | Baixo. É driver built-in, documentado no `man gitattributes`, mas medi só em `git 2.42.1`/Darwin |
| A7 | Nenhum consumidor não descoberto trata o journal como autoridade | Recomendação | Médio-baixo. Li as chamadas de `cairn-doctor.py` e `cairn-reconcile.py` direto; `cairn-status.py` (161 KB, 26 menções) e `cairn-parallel.py` (94 KB, 13 menções) foram inspecionados por grep, **não** lidos por inteiro. **O planejador deve confirmar** |

---

## Perguntas abertas, e o que precisa de decisão humana

### 1. O `DJOUR-02` precisa ser reescrito. Não posso reescrevê-lo.

**O que se sabe:** como está escrito — *"O journal sobrevive entre máquinas sem que merge reordene ou perca registro, provado por teste que mescla dois journals divergentes"* — o requisito **não sobrevive** à recomendação, porque o journal não vai atravessar máquinas.

**O que está travando:** foi instruído explicitamente não tocar em `.planning/REQUIREMENTS.md` (quatro fases em paralelo).

**Recomendação:** vira item de grooming. Texto sugerido:

> **DJOUR-02**: A decisão de manter o journal local é provada por teste que mescla dois journals divergentes e demonstra que a leitura de `last-moved` sobre o resultado mesclado discorda da verdade cronológica — e por teste que afirma que o journal é e continua ignorado pelo git.

**Motivo, para o registro do grooming:** o requisito original presume um desfecho que a pesquisa que ele mesmo exigiu descartou.

### 2. Vale pagar o desenho particionado assim mesmo?

**O que se sabe:** ele funciona (E11), custa 4–6 planos [SUPOSTO], e entrega forense cross-máquina que hoje não existe.
**O que não se sabe:** se o Felipe realmente opera o CairnGo de mais de uma máquina hoje. **Medido: o journal real tem 141 registros e exatamente um ator (`FelipeOFF`).** Zero evidência de uso multi-máquina até agora.
**Recomendação:** não pagar. **Mas esta é a pergunta que decide, e ela depende de um fato sobre o fluxo de trabalho do Felipe que a pesquisa não pode medir.** Se a resposta for "sim, opero de duas máquinas e quero a forense", a seção "o desenho correto" acima é o plano, e a recomendação inverte.

### 3. Vale fazer o conserto do E12 preventivamente?

**O que se sabe:** ler `compacted_through_ts` em `_last_known()` conserta o E9 e é pequeno. Não é necessário enquanto o journal for local.
**O que não se sabe:** se a casa aceita código defensivo contra um cenário que a decisão diz que não vai acontecer.
**Recomendação:** **não** fazer, e em vez disso registrar no docstring que o `compacted_through_ts` **passaria a ser carga estrutural** se o arquivo virasse versionado. Documentação é mais barata que código especulativo, e o Teste B guarda a fronteira. **Decisão do humano.**

### 4. Severidade do achado de doctor: `fail` ou `warn`?

**O que se sabe:** o precedente da fase 30 é *"trabalho não empurrado é atrito, não inconsistência"* → `warn`.
**Argumento para `fail`:** um journal rastreado não é atrito. É uma condição sob a qual o `last-moved` começa a devolver resposta errada em silêncio (medido).
**Recomendação:** `fail`. **Decisão do humano**, porque mexe na política de severidade do doctor, que é transversal.

---

## Fontes

### Primárias (confiança ALTA — reproduzidas nesta sessão)

- Repositórios git temporários construídos e mesclados agora, em `/private/tmp/.../scratchpad/j`, `j2`, `j3`, `j4`, `j5`, `j6`, `j7`, `j8`: experimentos E1–E17. Toda saída citada é literal.
- `cairn-journal.py` de produção deste repositório, executado diretamente sobre arquivos mesclados (`last-moved`, `observe`, `compact`) — não simulado.
- `.cairn/journal.jsonl` real deste worktree: 141 registros, 18 fases, 1 ator, 27.992 bytes.
- `git 2.42.1`, `Python 3.12.1`, `bd 1.1.0`, `Darwin 25.4.0` — todos via `--version`.
- `sntp -d time.apple.com`: desvio de −0,016695 s ± 0,007931 s.
- Leitura direta do código: `cairn-journal.py` (docstring completo, `_last_known`, `_parse_records`, `cmd_history`, `compact`), `cairn-doctor.py` (`journal_last_moved`), `cairn-reconcile.py` (`journal_history`, `evidence_hash`), `cairn-lease.py` (seam `CAIRN_JOURNAL`).

### Secundárias (confiança ALTA — pesquisa anterior deste projeto, reconfirmada)

- `.planning/research/STACK.md` § "`.gitattributes merge=union`" (2026-07-29): registrou a reordenação, a dedup byte-idêntica e a ausência de conflito do driver. **Reconfirmado independentemente aqui** (E2, E3). O aviso da linha 227 — *"Never rewrite the `merge=union` file in place"* — antecipou o E5/E13 e não tinha sido medido; agora está.
- `man gitattributes` (git 2.42.1, local), citado no `STACK.md`: *"This tends to leave the added lines in the resulting file in random order and the user should verify the result."*

### Terciárias

Nenhuma. **Nenhuma busca na web foi feita para esta pesquisa.** Toda afirmação vem de execução local ou de leitura de código deste repositório. Não há afirmação `[ASSUMIDO]` sobre comportamento de ferramenta — as únicas `[SUPOSTO]` são as estimativas de esforço (A1, A2) e a generalização da medição de relógio (A4), todas marcadas.

---

## Metadados

**Confiança por área:**

| Área | Nível | Motivo |
|---|---|---|
| Comportamento do `merge=union` | **ALTA** | 17 experimentos reproduzidos com saída literal; concorda com pesquisa independente anterior e com o `man` |
| Rejeição da hash-chain | **ALTA** | Medida (E6), e reforçada por um argumento de requisito (`DJOUR-03`) que independe da medição |
| Estado do código atual | **ALTA** | Script de produção executado diretamente; nenhuma afirmação de comportamento vem de leitura sozinha |
| Incompatibilidade da compactação | **ALTA** | E5, E9, E13, com `compact()` real |
| Argumento do desvio de relógio | **MÉDIA** | Medição de uma única máquina (A4). A direção é sólida; a magnitude varia por ambiente |
| Custo do desenho particionado | **MÉDIA** | O desenho é verificado (E11); a estimativa de esforço é suposta (A1) |
| Cobertura de consumidores | **MÉDIA-ALTA** | Chamadas de doctor e reconcile lidas direto; status e parallel por grep (A7) |

**Data da pesquisa:** 2026-08-05
**Válido até:** 2026-11-05 (90 dias). O comportamento do `merge=union` é built-in e estável; o que expira antes é o ponto de partida — o journal cresce ~5,6 KB/dia e a compactação dispara em ≈ 36 dias, o que torna o E13 uma preocupação viva em vez de teórica.
**Arquivos não tocados, por instrução:** `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`.
