---
phase: 25-measured-cleanup
plan: "08"
beads: [CairnGo-q9l]
status: complete
---

# Fase 25 Plano 08 — resumo

## O que mudou

Os 25 comandos próprios do cairn declaram, no próprio frontmatter, o grupo em
que aparecem (`group:`), do mesmo jeito que os 13 wrappers já declaravam
`wraps:` e `wrap-family:`. `cairn/commands/help.md` perdeu o bloco ASCII e
passou a montar o mapa inteiro em runtime: nomes de `cairn-wrap.sh list
--json`, linha de cada comando do `description:` do próprio arquivo, cabeçalho
do `group:`.

## O defeito, e a asserção que o fecha

| Defeito | Medição | Teste |
|---|---|---|
| Metade do mapa era lista à mão, e já tinha perdido um comando | 2026-08-06: `grep -c 'cairn:reconcile' cairn/commands/help.md` → `0`, com o comando existindo, documentado e com linha na referência. Remedido contra `b9fdfb3`: **17** nomes transcritos | `the help map names no command by hand, beyond the six prose names` |
| A página não dizia de onde vinha a metade própria | o `list --json` era citado só para os wrappers | `the help map says where BOTH halves come from` |
| Nada provava que um comando novo aparece sozinho | o teste 23 da suíte do wrap só reprova a direção oposta | `a command added to the disk appears in the map with no prose edited` |
| Um comando sem grupo poderia sumir | — | mesmo teste (sonda **sem** `group:` continua listada) + `every command cairn owns declares the group it prints under` |

Quatro testes novos; os dois primeiros vermelhos contra o `b9fdfb3`.

## A decisão de projeto: o comando declara onde entra

`cairn-wrap.py list --json` já dá os **nomes** (`.commands` menos
`.wrappers[].command`), mas descarta a descrição dos comandos próprios — o
`collect()` a lê e o `do_list()` não a emite. E `cairn-wrap.py` é da outra
frente nesta fase.

Então a derivação foi montada sobre o contrato que o script já publica, mais o
frontmatter do próprio arquivo de comando — que é onde a descrição já morava.
`group:` é a chave nova, e ela é o análogo exato do `wrap-family:` que já
agrupa os wrappers. Precedente medido de que uma chave própria no frontmatter
de comando é segura: `wraps:` e `wrap-family:` já vivem lá, e o Claude Code
carrega esses comandos hoje.

Duas regras impedem que a derivação perca alguém:

- arquivo **sem** `group:` imprime sob `OTHER`;
- `group:` com valor sem cabeçalho definido imprime sob um cabeçalho com o
  próprio nome, no fim.

Um comando pode aparecer no lugar errado. Não pode sumir — que é exatamente o
que aconteceu com o `reconcile`.

## A prosa que sobrou nomeando comando, e por quê

Seis nomes, nenhum deles listagem, e o teste tem uma allowlist com essas seis
razões escritas:

- `config`, `sync-config`, `context-config` — a seção dos três arquivos de
  configuração, exigida **por nome** pelo `tests/cairn-config.bats` ("the three
  config commands are told apart in one place");
- `new`, `migrate`, `status` — a regra de próximo passo do parágrafo de
  abertura, que é comportamento, não mapa.

Qualquer sétimo nome derruba o teste.

## A quebra guardada

| Quebra | Onde | Asserção vermelha |
|---|---|---|
| Restaurar o `help.md` anterior ao conserto | `cairn/commands/help.md`, restaurado de cópia `cp` | `the help map names no command by hand…` → `transcribes command name(s): autonomous bd ctx doctor gsd init issues milestone plan progress quick recall remember ship sync-pull verify work` (17), e `the help map says where BOTH halves come from` → falha em `.wrappers[].command` |

Restauração por `cp` de uma cópia feita antes da quebra — nunca
`git checkout <arquivo>`.

## Suítes de quem consome o `help.md`, rodadas depois

| Suíte | Resultado |
|---|---|
| `tests/cairn-wrap.bats` (24 testes) | verde — inclusive o 22 (`the real command reference is current`) e o 23 (`/cairn:help derives its wrapper list`) |
| `tests/cairn-config.bats -f "declares what it leaves out"` | verde |
| `tests/cairn-bookkeep.bats -f "help.md registers the command"` | vermelho na primeira passada, verde depois |

## Premissas que a medição contradisse

1. **`cairn-wrap.sh list` bastaria para derivar o mapa inteiro.** Não basta: o
   payload não carrega a descrição dos comandos próprios. A descrição existe no
   `collect()` e morre no `do_list()`. A derivação precisou de uma segunda
   fonte — o frontmatter — que por sorte é a mesma fonte de onde o script tira
   a dele.
2. **O `help.md` podia ser reescrito sem tocar em contrato de outra suíte.**
   Dois testes de outras frentes exigem literais dentro dele:
   `tests/cairn-config.bats` pede os três nomes de configuração, e
   `tests/cairn-bookkeep.bats` pede a string `cairn-bookkeep.sh close`. A
   primeira escrita do bloco em estilo da casa
   (`"${CLAUDE_PLUGIN_ROOT}/scripts/cairn-bookkeep.sh" close`) pôs uma aspa no
   meio da string exigida e deixou o teste vermelho — corrigido para
   `"${CLAUDE_PLUGIN_ROOT}"/scripts/cairn-bookkeep.sh close`.
3. **Citar o defeito na própria página é inofensivo.** Não é: escrever
   `/cairn:reconcile` na prosa que explica o achado derrubou a asserção de "não
   transcreva". A citação foi reescrita para nomear o comando sem o prefixo, e
   a guarda ficou estrita — o que é o comportamento certo, já que era
   justamente esse nome que faltava.
