#!/usr/bin/env bats
# cairn-record.bats — a fronteira UNICA de escrita de registro (cairn-record.py
# / cairn-record.sh). Exercita o contrato de CLI contra repos de fixture
# descartaveis: exit codes, estado no bd via `bd show --json`, e a invariante
# que da nome ao milestone — este script NUNCA escreve markdown.
#
# POR QUE ESTE SCRIPT EXISTE. Medido na arvore pre-mudanca: 123 sitios em 42
# arquivos de cairn/gsd/ mandam o modelo escrever um <DOC>.md, e 209 literais
# de caminho .planning/ dizem onde. Converter sitio a sitio para prosa
# artesanal multiplicaria 123 formas de gravar a mesma coisa. Uma fronteira
# unica troca as 123 por UMA chamada, e o oraculo tests/cairn-zero-md.bats
# mede que a troca aconteceu.
#
# O DESENHO QUE A MEDICAO IMPOS (registrado em bd CairnGo-9c0h --design):
# context-mode NAO tem CLI — `command -v ctx ctx-mode context-mode` devolve
# vazio, os ctx_* sao tools MCP model-side. Logo um script python NAO indexa.
# A fronteira e' partida: o SCRIPT grava o FATO estruturado no bd
# (deterministico, testavel — e' o que esta suite mede); a CAMADA PROMPT chama
# ctx_index para a PROSA. Nao e' acidente, e' o desenho, e a alternativa
# (inventar um formato de arquivo) e' exatamente o que o milestone recusa.
#
# UM SUMMARY NAO E' ARQUIVO NOVO. E' o FECHO do mesmo registro que o PLAN
# abriu. Por isso `summary` fecha o bead do plano com o corpo em notes, em vez
# de criar um segundo registro — e ha caso de teste provando que a contagem de
# beads NAO sobe quando um summary e' gravado.
#
# Estilo de assercao: um `[[ ]]` ou `! cmd` no meio do teste NAO reprova neste
# bash, entao checagem de substring usa grep -qF e negativa usa refute_output.

load 'helpers'

refute_output_has() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

RECORD="$CAIRN_SCRIPTS_DIR/cairn-record.py"

# Fixture: um bead portador de fase (phase-1) e nada mais. O portador e' o
# alvo dos kinds que gravam na fase; os kinds de plano criam filhos dele.
make_record_fixture() {
  bd init -q --prefix rec --non-interactive >/dev/null 2>&1
  REC_PHASE="$(bd create "Phase 1 carrier" -t epic -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"phase":1,"milestone":"v1.0"}}' --silent 2>/dev/null)"
}

# Conta arquivos markdown na arvore inteira do repo de fixture. A invariante
# do milestone e' que este numero nao se mova por causa do cairn-record.
count_md() {
  find . -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' '
}

# Le um campo do bead pelo NOME DE CHAVE DO JSON do bd. MEDIDO (bd 1.1.0): os
# campos longos so aparecem no JSON quando nao-vazios, e `acceptance` na CLI e'
# `acceptance_criteria` no JSON — os testes usam a grafia do JSON.
bd_field() {
  bd show "$1" --json 2>/dev/null | python3 -c "
import json,sys
d = json.load(sys.stdin)
d = d[0] if isinstance(d, list) else d
print(d.get('$2') or '')
"
}

# --- uso e contratos de falha -------------------------------------------------

@test "record: sem kind e uso, exit 2" {
  run python3 "$RECORD"
  [ "$status" -eq 2 ]
  grep -qF "usage:" <<<"$output$stderr" || grep -qi "usage" <<<"$output"
}

@test "record: kind desconhecido nomeia o kind e sai 4" {
  run bash -c "echo corpo | python3 '$RECORD' banana --phase 1"
  [ "$status" -eq 4 ]
  grep -qF "banana" <<<"$output"
}

@test "record: kind valido lista os kinds conhecidos no erro de kind" {
  run bash -c "echo corpo | python3 '$RECORD' banana --phase 1"
  [ "$status" -eq 4 ]
  grep -qF "summary" <<<"$output"
  grep -qF "plan" <<<"$output"
}

@test "record: bd ausente do PATH e exit 5, nao stack trace" {
  require_bd
  make_tmp_repo
  make_record_fixture
  run env PATH="/usr/bin:/bin" bash -c "echo corpo | python3 '$RECORD' context --phase 1"
  [ "$status" -eq 5 ]
  refute_output_has "Traceback"
}

# --- os kinds, um a um --------------------------------------------------------

@test "record: plan cria bead filho do portador com o corpo em description" {
  require_bd
  make_tmp_repo
  make_record_fixture
  run bash -c "printf 'corpo do plano\nsegunda linha\n' | python3 '$RECORD' plan --phase 1 --plan 01 --title 'Onda 1'"
  [ "$status" -eq 0 ]
  local child
  child="$(bd list --parent "$REC_PHASE" --json 2>/dev/null | python3 -c "
import json,sys
d = json.load(sys.stdin)
print(d[0]['id'] if d else '')
")"
  [ -n "$child" ]
  run bd_field "$child" description
  grep -qF "corpo do plano" <<<"$output"
}

@test "record: summary FECHA o registro do plano, nao cria um segundo" {
  require_bd
  make_tmp_repo
  make_record_fixture
  echo "corpo do plano" | python3 "$RECORD" plan --phase 1 --plan 01 --title "Onda 1"
  local before
  before="$(bd list --all --json 2>/dev/null | python3 -c "import json,sys;print(len(json.load(sys.stdin)))")"
  run bash -c "echo 'o que a onda entregou' | python3 '$RECORD' summary --phase 1 --plan 01"
  [ "$status" -eq 0 ]
  local after
  after="$(bd list --all --json 2>/dev/null | python3 -c "import json,sys;print(len(json.load(sys.stdin)))")"
  [ "$before" -eq "$after" ]
}

@test "record: summary fecha o bead do plano com o corpo em notes" {
  require_bd
  make_tmp_repo
  make_record_fixture
  echo "corpo do plano" | python3 "$RECORD" plan --phase 1 --plan 01 --title "Onda 1"
  echo "o que a onda entregou" | python3 "$RECORD" summary --phase 1 --plan 01
  local child
  child="$(bd list --parent "$REC_PHASE" --all --json 2>/dev/null | python3 -c "
import json,sys
d = json.load(sys.stdin)
print(d[0]['id'] if d else '')
")"
  run bd_field "$child" notes
  grep -qF "o que a onda entregou" <<<"$output"
  run bd_field "$child" status
  grep -qi "closed" <<<"$output"
}

@test "record: context grava design no portador da fase" {
  require_bd
  make_tmp_repo
  make_record_fixture
  run bash -c "echo 'o contexto medido' | python3 '$RECORD' context --phase 1"
  [ "$status" -eq 0 ]
  run bd_field "$REC_PHASE" design
  grep -qF "o contexto medido" <<<"$output"
}

@test "record: verification grava acceptance no portador da fase" {
  require_bd
  make_tmp_repo
  make_record_fixture
  run bash -c "echo 'criterio verificado' | python3 '$RECORD' verification --phase 1"
  [ "$status" -eq 0 ]
  run bd_field "$REC_PHASE" acceptance_criteria
  grep -qF "criterio verificado" <<<"$output"
}

@test "record: log ANEXA em notes, nao substitui" {
  require_bd
  make_tmp_repo
  make_record_fixture
  echo "primeira entrada" | python3 "$RECORD" log --phase 1
  run bash -c "echo 'segunda entrada' | python3 '$RECORD' log --phase 1"
  [ "$status" -eq 0 ]
  run bd_field "$REC_PHASE" notes
  grep -qF "primeira entrada" <<<"$output"
  grep -qF "segunda entrada" <<<"$output"
}

# --- resolucao de alvo: fato ausente e' falha NOMEADA (doutrina CORE-04) -----

@test "record: fase sem portador NENHUM — cria o fato e nomeia o id criado" {
  require_bd
  make_tmp_repo
  bd init -q --prefix rec --non-interactive >/dev/null 2>&1
  # Este teste afirmava o contrato inverso ate 2026-08-12 (exit 1, "o FATO nao
  # existe"). A medicao no repositorio real o derrubou: das 38 fases daqui,
  # ZERO tem portador — a ausencia e' o estado NORMAL de um projeto com
  # historico, nao erro do usuario. CORE-04 proibe o fallback silencioso e o
  # fallback para markdown; criar o fato que falta e dizer o id em voz alta
  # nao e' nenhum dos dois.
  run bash -c "echo corpo | python3 '$RECORD' context --phase 9"
  [ "$status" -eq 0 ]
  grep -qF "fase 9 nao existia" <<<"$output"
}

@test "record: portador ambiguo lista os candidatos e pede --issue" {
  require_bd
  make_tmp_repo
  make_record_fixture
  bd create "Segundo portador" -t epic -l phase-1,m-v1.0 --silent >/dev/null 2>&1
  run bash -c "echo corpo | python3 '$RECORD' context --phase 1"
  [ "$status" -eq 1 ]
  grep -qF -- "--issue" <<<"$output"
}

@test "record: --issue explicito vence a resolucao por label" {
  require_bd
  make_tmp_repo
  make_record_fixture
  local other
  other="$(bd create "Outro" -t task -l phase-1,m-v1.0 --silent 2>/dev/null)"
  run bash -c "echo 'alvo explicito' | python3 '$RECORD' context --phase 1 --issue '$other'"
  [ "$status" -eq 0 ]
  run bd_field "$other" design
  grep -qF "alvo explicito" <<<"$output"
}

# --- a invariante do milestone ------------------------------------------------

@test "record: NENHUM kind escreve markdown em lugar nenhum" {
  require_bd
  make_tmp_repo
  make_record_fixture
  local before after
  before="$(count_md)"
  echo "corpo" | python3 "$RECORD" plan --phase 1 --plan 01 --title "Onda"
  echo "corpo" | python3 "$RECORD" context --phase 1
  echo "corpo" | python3 "$RECORD" verification --phase 1
  echo "corpo" | python3 "$RECORD" log --phase 1
  echo "corpo" | python3 "$RECORD" summary --phase 1 --plan 01
  after="$(count_md)"
  [ "$before" -eq "$after" ]
}

@test "record: controle negativo — a contagem de markdown SOBE quando algo escreve" {
  make_tmp_repo
  local before after
  before="$(count_md)"
  echo "sou um markdown" > INTRUSO.md
  after="$(count_md)"
  [ "$after" -gt "$before" ]
}

@test "record: --json emite resumo de maquina com kind, alvo e campo" {
  require_bd
  make_tmp_repo
  make_record_fixture
  run bash -c "echo corpo | python3 '$RECORD' context --phase 1 --json"
  [ "$status" -eq 0 ]
  run bash -c "echo corpo | python3 '$RECORD' log --phase 1 --json"
  [ "$status" -eq 0 ]
  python3 -c "
import json,sys
d = json.loads('''$output''')
assert d['kind'] == 'log', d
assert d['field'] == 'notes', d
assert d['issue'], d
"
}

@test "record: o wrapper .sh repassa o exit code do python sem traduzir" {
  run bash -c "echo corpo | '$CAIRN_SCRIPTS_DIR/cairn-record.sh' banana --phase 1"
  [ "$status" -eq 4 ]
}

# --- o portador da fase: quem e', e o que acontece quando nao ha -------------
#
# MEDIDO no repositorio real (2026-08-12) e por isso estes casos existem: das
# 38 fases deste repo, ZERO tem epico portador e quase nenhuma tem bead sem
# `gsd.req` — todo bead `phase-N` daqui e' um REQUISITO. O fixture de cima
# (um unico bead com o label) nunca encosta nessa forma, e por isso a versao
# anterior do resolvedor podia estar quebrada com a suite verde.

# Fixture do repo REAL: tres requisitos da fase 7, nenhum portador.
make_reqs_only_fixture() {
  bd init -q --prefix noc --non-interactive >/dev/null 2>&1
  bd create "REQ-01: alfa" -t task -l phase-7,m-v1.0 \
    --metadata '{"gsd":{"phase":7,"milestone":"v1.0","req":"REQ-01"}}' --silent >/dev/null 2>&1
  bd create "REQ-02: beta" -t task -l phase-7,m-v1.0 \
    --metadata '{"gsd":{"phase":7,"milestone":"v1.0","req":"REQ-02"}}' --silent >/dev/null 2>&1
  bd create "REQ-03: gama" -t task -l phase-7,m-v1.0 \
    --metadata '{"gsd":{"phase":7,"milestone":"v1.0","req":"REQ-03"}}' --silent >/dev/null 2>&1
}

@test "record: fase so com requisitos — o portador e criado e o id sai NOMEADO" {
  require_bd
  make_tmp_repo
  make_reqs_only_fixture
  local before
  before="$(count_md)"
  run bash -c "echo 'corpo do contexto' | python3 '$RECORD' context --phase 7 --milestone v1.0"
  [ "$status" -eq 0 ]
  grep -qF "portador da fase 7 nao existia" <<<"$output"
  # e continua sem escrever markdown nenhum
  [ "$(count_md)" = "$before" ]
}

@test "record: o portador criado NAO e um requisito, e o corpo nao cai num deles" {
  require_bd
  make_tmp_repo
  make_reqs_only_fixture
  echo "corpo do contexto" | python3 "$RECORD" context --phase 7 --milestone v1.0 >/dev/null
  # nenhum dos tres requisitos recebeu o corpo
  run bash -c "bd list -l phase-7 --all --json | python3 -c \"
import json,sys
d = json.load(sys.stdin)
reqs = [i for i in d if ((i.get('metadata') or {}).get('gsd') or {}).get('req')]
print(sum(1 for i in reqs if (i.get('design') or '')))
\""
  [ "$output" = "0" ]
  # e o portador criado tem o corpo, sem gsd.req
  run bash -c "bd list -l phase-7 --all --json | python3 -c \"
import json,sys
d = json.load(sys.stdin)
c = [i for i in d if not ((i.get('metadata') or {}).get('gsd') or {}).get('req')]
print(len(c), (c[0].get('issue_type') if c else ''), 'corpo' if c and (c[0].get('design') or '') else 'vazio')
\""
  [ "$output" = "1 epic corpo" ]
}

@test "record: a segunda gravacao REUSA o portador criado, nao cria outro" {
  require_bd
  make_tmp_repo
  make_reqs_only_fixture
  echo "primeiro" | python3 "$RECORD" context --phase 7 --milestone v1.0 >/dev/null
  run bash -c "echo segundo | python3 '$RECORD' research --phase 7 --milestone v1.0"
  [ "$status" -eq 0 ]
  refute_output_has "nao existia"
  run bash -c "bd list -l phase-7 --all --json | python3 -c \"
import json,sys
d = json.load(sys.stdin)
print(len([i for i in d if not ((i.get('metadata') or {}).get('gsd') or {}).get('req')]))
\""
  [ "$output" = "1" ]
}

@test "record: DOIS portadores continuam sendo ambiguidade NOMEADA, com os ids" {
  require_bd
  make_tmp_repo
  make_reqs_only_fixture
  bd create "Phase 7" -t epic -l phase-7,m-v1.0 \
    --metadata '{"gsd":{"phase":7,"milestone":"v1.0"}}' --silent >/dev/null 2>&1
  bd create "Phase 7 (duplicata)" -t epic -l phase-7,m-v1.0 \
    --metadata '{"gsd":{"phase":7,"milestone":"v1.0"}}' --silent >/dev/null 2>&1
  run bash -c "echo corpo | python3 '$RECORD' context --phase 7 --milestone v1.0"
  [ "$status" -eq 1 ]
  grep -qF "portador ambiguo" <<<"$output"
  grep -qF -- "--issue" <<<"$output"
}

@test "record: controle negativo — o filtro de portador NAO pode ser a chave 'parent'" {
  require_bd
  make_tmp_repo
  make_record_fixture
  # MEDIDO (bd 1.1.0): o JSON do bd nao emite `parent` em list, show nem no
  # export. Este teste FIXA a medicao: se um dia passar a emitir, quem
  # reescrever o resolvedor vera aqui que a versao antiga dependia dela.
  run bash -c "bd list -l phase-1 --all --json | python3 -c \"
import json,sys
d = json.load(sys.stdin)
print('parent' in (d[0] if d else {}))
\""
  [ "$output" = "False" ]
}

# --------------------------------------------------------------------------- #
# the record mirrors to the card as a comment (phase 45 / MIRROR-03)
# --------------------------------------------------------------------------- #

# A gbsync stand-in on the CAIRN_GBSYNC seam: logs its argv, exits 0.
make_gbsync_stub() {
  GBSYNC_STUB="$BATS_TEST_TMPDIR/gbsync.sh"
  GBSYNC_LOG="$BATS_TEST_TMPDIR/gbsync.log"
  cat > "$GBSYNC_STUB" <<EOS
#!/usr/bin/env bash
printf 'CALL: %s\n' "\$*" >> "$GBSYNC_LOG"
EOS
  chmod +x "$GBSYNC_STUB"
}

@test "record: plan e summary viram comentario no carrier via gbsync, so' com sync.json" {
  require_bd
  make_tmp_repo
  make_record_fixture
  make_gbsync_stub

  # Sem sync.json: nenhum espelho, nenhuma chamada.
  run bash -c "printf 'corpo do plano\n\nsegundo paragrafo\n' | CAIRN_GBSYNC='$GBSYNC_STUB' python3 '$RECORD' plan --phase 1 --plan 01 --title 'Onda 1' --json"
  [ "$status" -eq 0 ]
  grep -qF '"mirror": null' <<<"$output"
  [ ! -e "$GBSYNC_LOG" ]

  mkdir -p .cairn && echo '{"backends": []}' > .cairn/sync.json
  run bash -c "printf 'corpo do plano\n\nsegundo paragrafo\n' | CAIRN_GBSYNC='$GBSYNC_STUB' python3 '$RECORD' plan --phase 1 --plan 02 --title 'Onda 2' --json"
  [ "$status" -eq 0 ]
  grep -qF "\"carrier\": \"$REC_PHASE\"" <<<"$output"
  grep -qF "comment $REC_PHASE --text Plano 02 registrado: Onda 2" "$GBSYNC_LOG"
  grep -qF "corpo do plano" "$GBSYNC_LOG"
  ! grep -qF "segundo paragrafo" "$GBSYNC_LOG"

  run bash -c "echo 'o que a onda entregou' | CAIRN_GBSYNC='$GBSYNC_STUB' python3 '$RECORD' summary --phase 1 --plan 02"
  [ "$status" -eq 0 ]
  grep -qF "comment $REC_PHASE --text Fechado: o que a onda entregou" "$GBSYNC_LOG"
  grep -qF "registro completo no bead" "$GBSYNC_LOG"

  # Um contexto nao e' plano nem summary: nada e' espelhado.
  run bash -c "echo 'contexto' | CAIRN_GBSYNC='$GBSYNC_STUB' python3 '$RECORD' context --phase 1"
  [ "$status" -eq 0 ]
  [ "$(grep -c '^CALL: ' "$GBSYNC_LOG")" -eq 2 ]
}

@test "record: os kinds de desenho escrevem cada um a sua secao do design, sem apagar as outras" {
  require_bd
  make_tmp_repo
  make_record_fixture
  echo "o que se decidiu" | python3 "$RECORD" context --phase 1
  echo "o que se pesquisou" | python3 "$RECORD" research --phase 1
  echo "o que a fase entrega" | python3 "$RECORD" spec --phase 1
  run bd_field "$REC_PHASE" design
  grep -qF "## CONTEXT" <<<"$output"
  grep -qF "o que se decidiu" <<<"$output"
  grep -qF "## RESEARCH" <<<"$output"
  grep -qF "## SPEC" <<<"$output"
  grep -qF "o que a fase entrega" <<<"$output"

  # Regravar um kind substitui SO' a sua secao.
  echo "decisao revista" | python3 "$RECORD" context --phase 1
  run bd_field "$REC_PHASE" design
  grep -qF "decisao revista" <<<"$output"
  refute_output_has "o que se decidiu"
  grep -qF "o que se pesquisou" <<<"$output"
  [ "$(grep -c '^## CONTEXT' <<<"$output")" -eq 1 ]
}

@test "record: um design gravado antes das secoes vira '## LEGACY' e sobrevive ao primeiro kind" {
  require_bd
  make_tmp_repo
  make_record_fixture
  bd update "$REC_PHASE" --design "decisao antiga gravada com set" >/dev/null
  echo "o que a fase entrega" | python3 "$RECORD" spec --phase 1
  run bd_field "$REC_PHASE" design
  grep -qF "## LEGACY" <<<"$output"
  grep -qF "decisao antiga gravada com set" <<<"$output"
  grep -qF "## SPEC" <<<"$output"
  grep -qF "o que a fase entrega" <<<"$output"
}
