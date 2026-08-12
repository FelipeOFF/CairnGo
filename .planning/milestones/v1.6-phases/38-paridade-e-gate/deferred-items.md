# Fase 38 — itens fora de escopo, encontrados durante a execução

Achados que a fase NÃO consertou, cada um com a medição que o sustenta e com o
lugar onde a decisão está escrita.

## 1. A partição de `cairn_gsd_render.py` (D-07)

**Decidida** aqui — saída (a), partir em envelope + substrato — e **não executada**:
refatorar 1536 linhas do binário na hora de fechar o milestone é o oposto de
consolidar. Rastreada por `CairnGo-2fyg` (backlog), com a decisão e o porquê no
corpo da issue.

O que ficou de pé no lugar: o gate de teto que nunca existiu (dois testes em
`tests/cairn-gsd.bats` — pino por arquivo que só desce, e a lista fechada dos três
arquivos acima de 1500). A cegueira está fechada; a partição, aberta.

## 2. Os 8 verbos GSD fora do ciclo continuam não vendorizados (D-01)

Não é dívida acidental — é a decisão desta fase, com custo medido e registrada em
`cairn/gsd-parity.json`. Fica aqui porque o efeito é visível ao usuário: quem roda
`/cairn:new`, `/cairn:milestone`, `/cairn:ship` ou `/cairn:migrate` sem um plugin
GSD instalado ao lado faz a parte de criação/arquivamento à mão. Os comandos dizem
isso na cara; nenhum deles finge.

Reabrir a decisão é trabalho de milestone próprio (dobraria a árvore vendorizada),
e o dado para reabrir está no registro.

## 3. A remoção física de `cairn/capability/` (herdada da fase 37, item 2)

Continua candidata a fase posterior. A fase 38 fecha a condição que a 37 pediu —
"depois que a fase 38 provar que nada mais lê o bundle em runtime": o scan de
paridade varre `cairn/gsd/` inteiro e nenhuma chamada `gsd_run` resolve para lá, e
o doctor do repositório novo sai limpo sem tocar no bundle. Quem executar a remoção
já tem a prova; o que falta é a cascata medida na 37 (4 frentes).

## 4. Profundidade dos 12 contratos inline (herdada da fase 37, item 3)

O gate de paridade desta fase mede **resolução**, não profundidade: prova que todo
caminho aponta para algo que existe e responde, não que o texto seja tão fundo
quanto o workflow upstream que substituiu. Aprofundar segue sendo trabalho com
dado — e o dado que faltava (quais comandos resolvem inteiramente dentro do
plugin) agora existe, no registro e no guard.

## 5. Dois testes de `cairn-gsd.bats` seguem skip-gated no clone

`cadeia do manifest (b)` e `reproducao (corpus real)` continuam pulando mesmo com
o clone `v1.10.0` presente — a condição deles é outra, não a que esta fase religou.
Fora de escopo aqui, registrado para que ninguém leia o skip como verde.
