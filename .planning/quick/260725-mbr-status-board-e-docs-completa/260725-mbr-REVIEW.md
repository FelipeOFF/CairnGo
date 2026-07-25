# Code Review — cairn-status (260725-mbr)

## 1. [critical] cairn/scripts/cairn-status.py:392

Titulos/ids/assignees do bd sao impressos sem sanitizacao de caracteres de controle. clean() so colapsa \s+; ESC (\x1b) e outros C0/C1 passam intactos em TODOS os modos — inclusive --plain, cujo contrato (docstring linhas 35-46, e o teste 'refute_in_output \x1b') promete 'zero escape bytes'. Confirmado: `bd create "Evil \033[2J\033[31m title"` produz `READY\tinj-a6z\t2\tEvil ^[[2J^[[31m title` no --plain e bytes ESC crus no board (que tambem quebram o display_width/alinhamento, pois char_width conta ESC como 1 celula). Como issues podem vir de trackers remotos via sync-pull, titulos sao dados de origem externa injetando sequencias no terminal do usuario (clear screen, reposicionamento de cursor, OSC).

**Fix:** Sanitizar em clean(): remover/substituir C0+C1+DEL antes do colapso de whitespace, ex. `re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '', str(text))`, e garantir que todo texto vindo do bd/STATE.md passe por clean() antes de qualquer render (ver tambem o finding do synthesize_next).

## 2. [major] cairn/scripts/cairn-status.py:332

synthesize_next embute o titulo CRU (sem clean()) em next.text: f"continue {id} — {title}". Um titulo com \n ou \t forja linhas nos formatos maquina: confirmado que `bd create "top prio\nDOING\tfake-doing\t0\tInjected doing row" -p 0` faz o --plain emitir `NEXT\tstart inj-kk9 — top prio` seguido de uma linha `DOING\tfake-doing\t0\tInjected doing row` indistinguivel de uma linha de lane real (forja de linhas no formato que agentes/CI parseiam), faz o --brief imprimir 4 linhas (contrato e o teste dizem exatamente 3), e injeta uma linha extra apos o footer do board (truncate() nao protege: \n conta como 1 celula mas quebra a linha).

**Fix:** Aplicar clean() (ja com strip de controles) ao montar text em synthesize_next (linhas 332, 344, 349, 355) — ou no ponto de render (render_plain linha 622, render_brief linha 645, footer_lines linha 562). O next_action de STATE.md deve receber o mesmo tratamento.

## 3. [major] cairn/scripts/cairn-status.py:666

Nao ha guarda de existencia de .beads/ antes de consultar o bd (cairn-gate.py:198-201 tem: 'no .beads/ — gate not applicable, exit 0'). O bd auto-descobre .beads subindo diretorios (confirmado: `bd ready` num subdir acha o .beads do pai e lista as issues dele). Resultado: rodar cairn-status num checkout sem .beads aninhado sob um repo rastreado renderiza silenciosamente o board do repo ERRADO e sintetiza um next action apontando para uma issue estrangeira — pior que falhar, pois apresenta dados errados como estado do repo.

**Fix:** Antes de fetch_lanes, checar `(root / '.beads').is_dir()`; se ausente, ou sair 5 com mensagem clara ('no .beads at <root>'), ou degradar para board GSD-only com nota — espelhando a decisao de aplicabilidade do cairn-gate. Alternativa: passar `--db root/.beads/...` explicito ao bd para matar o walk-up.

## 4. [major] cairn/scripts/cairn-status.py:298

sync_status so trata OSError/JSONDecodeError; JSON valido com shape errado crasha com traceback. Confirmado: `.cairn/state.json` contendo `[]` -> AttributeError ('list' object has no attribute 'get') na linha 298; `{"last_pull": "corrupt"}` -> AttributeError ('str' has no .items) na linha 303. A linha de sync e best-effort por contrato (staleness informativa) e um state.json corrompido nao pode derrubar o board inteiro.

**Fix:** Validar shapes: `if not isinstance(state, dict): state = {}` apos o json.loads, e `if not isinstance(last_pull, dict): last_pull = {}` — degradando para 'never pulled', como ja acontece com timestamps invalidos.

## 5. [minor] cairn/scripts/cairn-status.py:477

make_cell nunca trunca o id: com prefixo bd longo (confirmado com `--prefix an-extremely-long-project-prefix-name`) o card fica mais largo que a lane, pad fica negativo (silenciosamente pulado) e a grade desalinha. Relacionado: truncate() com 0 < width < display_width(ell) retorna a elipse inteira (mais larga que width) porque o budget negativo quebra o loop no primeiro char — um id que consome quase todo o inner faz o title_t estourar a celula em 1-2 colunas.

**Fix:** Em make_cell, truncar o iid a um teto (ex. inner - 8) antes de computar used, e em truncate() retornar '' (ou ell cortado) quando width < display_width(ell). Cobrir com um teste bats de prefixo longo verificando que toda linha do board tem a mesma largura.

## 6. [minor] cairn/scripts/cairn-status.py:703

--color=always e silenciosamente ignorado quando stdout nao e TTY e --width nao foi dado: a selecao de formato roteia para render_plain antes da decisao de cor (confirmado: `cairn-status.py --color=always | od` emite zero bytes ESC). Isso contradiz a precedencia documentada ('--color > CAIRN_NO_COLOR > NO_COLOR > TERM=dumb > isatty' — o flag deveria vencer tudo). O mesmo vale para --ascii piped. A cadeia de precedencia em si (_color_enabled, linhas 427-440) esta correta e na ordem documentada, incluindo NO_COLOR nao-vazio; o furo e so o roteamento de formato.

**Fix:** Ou documentar explicitamente que --color/--ascii nao contam como 'output flag' e nao forcam o renderer, ou tratar --color=always como opt-in do renderer de board (como faz --width). Adicionar teste bats: `--color=always` piped sem --width define o comportamento escolhido.

## 7. [minor] cairn/scripts/cairn-status.py:723

O docstring promete render 'pipe-safe', mas um consumidor que fecha o pipe cedo (`cairn-status | head -1`) gera BrokenPipeError — traceback ou 'Exception ignored in <_io.TextIOWrapper...>' no stderr e exit != 0 (observado durante os testes empiricos). cairn-gate tem o mesmo padrao, mas nao anuncia pipe-safety.

**Fix:** Envolver o print final em try/except BrokenPipeError fazendo `os._exit(0)` apos fechar stderr, ou instalar `signal.signal(signal.SIGPIPE, signal.SIG_DFL)` no inicio do main.

## 8. [minor] cairn/scripts/cairn-status.py:100

TABLE_PHASE_ANY (`^\s*\|\s*0*(\d+)[.)\s][^|]*\|`) e mais frouxo que qualquer padrao do cairn-gate (que so tem TABLE_PHASE exigindo `| Complete |`), apesar do docstring dizer 'same patterns as cairn-gate'. Qualquer tabela markdown no ROADMAP.md cuja primeira coluna comece com numero (ex. tabela de success criteria `| 1 | User can sign up |`) conta como fase, inflando o total do `phase X/Y` do footer/JSON.

**Fix:** Restringir a linhas de tabela de progresso reais (ex. exigir um token vN na linha, como o agrupamento por milestone do gate implica) ou limitar o parse de tabela a secao de progresso; no minimo documentar a divergencia em vez de afirmar paridade com o gate.

## 9. [minor] cairn/scripts/cairn-status.py:610

Furos defensivos residuais no shape do JSON do bd (nao reproduzidos com o bd atual, mas o parsing se pretende defensivo): (1) render_plain `",".join(iss.get("blocked_by") or [])` -> TypeError se os itens nao forem strings (objetos {id:...}) e itera char-a-char se blocked_by vier como string; (2) trim_issue repassa labels/blocked_by nao-lista sem normalizar, mudando o shape do --json; (3) a sort key `i.get("id", "")` retorna None quando id e null explicito -> TypeError no sorted() de fetch_lanes (linha 202). Nota positiva: metadata-como-string nao afeta este script (trim_issue nunca le metadata, ao contrario do gsd_req do cairn-map que ja trata o caso).

**Fix:** Normalizar em trim_issue/fetch_lanes: `[str(x) for x in (iss.get("blocked_by") or []) if x is not None]` (idem labels, com isinstance(list) guard) e `str(i.get("id") or "")` na sort key; reutilizar os valores normalizados em make_cell/render_plain.

## 10. [minor] cairn/scripts/cairn-status.py:337

active_phase vem cru do frontmatter de STATE.md; um STATE.md com `active_phase: "02"` gera o label procurado `phase-02`, que nunca casa com o label real `phase-2` — synthesize_next pula as issues ready da fase e cai no next_action/fallback. cairn-gate tolera zeros a esquerda em todos os regexes (`0*(\d+)`) e consulta por numero canonico; cairn-status nao normaliza.

**Fix:** Normalizar: `active_phase = active_phase.lstrip("0") or "0"` quando for numerico (ou `str(int(active_phase))` com try/except) antes de montar `phase-{active_phase}`; usar o mesmo valor normalizado no display `phase X/Y`.

## 11. [minor] tests/cairn-status.bats:44

O contrato 'repo bd-only — missing .planning degrada para issues-only board' (docstring passos 3, foco explicito da revisao) nao tem NENHUM teste: todos os testes de render chamam make_gsd_fixture antes. Uma regressao que crashe sem .planning/ (ou o caminho '(no roadmap position)' + next fallback 'nothing tracked') passaria a suite inteira. O caminho funciona hoje (verificado manualmente), mas esta descoberto.

**Fix:** Adicionar teste: make_tmp_repo + bd init + issues SEM make_gsd_fixture; assert exit 0, presenca de '(no roadmap position)' no board/--brief, ausencia de linha PHASE no --plain, e `.phase.total == null` no --json.

## 12. [minor] tests/cairn-status.bats:140

O teste non-TTY afirma `refute_in_output "\x1b"` (zero escapes) apenas com titulos benignos da fixture — assercao vacuamente verdadeira para o contrato que pretende cobrir: um titulo contendo ESC ou \n viola o contrato HOJE (bugs confirmados nas linhas 392/332 do script) e nenhum teste detecta. Fora isso, a suite segue corretamente a propria 'Assertion style note' (grep -qF simples + refute_in_output com return 1; nenhum `[[ ]]`/`! cmd` inline vacuo encontrado) — mas a nota vive no header do .bats, nao em tests/README.md como o README sugere ser o lugar das convencoes.

**Fix:** Adicionar teste adversarial: `bd create "$(printf 'x\033[31my\nREADY\tfake\t0\tz')"`; assert no --plain refute ESC e numero exato de linhas/linhas comecando com lane validos, e no --brief exatamente 3 linhas. Documentar a Assertion style note no tests/README.md.

## 13. [minor] tests/cairn-status.bats:210

A cadeia de precedencia de cor e testada so em 2 dos 5 degraus: --color=always emite SGR, NO_COLOR=1 suprime, flag vence NO_COLOR. Faltam: CAIRN_NO_COLOR (o degrau proprio da ferramenta, acima de NO_COLOR), TERM=dumb, --color=never num contexto colorido, e NO_COLOR="" vazio (que por no-color.org NAO deve desabilitar — o codigo acerta, mas nada trava isso).

**Fix:** Estender o teste: `env CAIRN_NO_COLOR=1 ... --width 100` sem escapes; `env TERM=dumb NO_COLOR= ... --width 100 --color=always` com escapes (flag vence); `env NO_COLOR="" ... --width 100 --color=always` com escapes; e `--color=never` apos `--color=always`-style board garantindo zero ESC.
