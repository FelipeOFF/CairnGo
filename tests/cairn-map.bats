#!/usr/bin/env bats
# cairn-map.bats — o contrato do cairn-map, que na v1.7 deixou de GERAR e
# passou a IMPRIMIR.
#
# O QUE MUDOU, E POR QUE O ARQUIVO DE TESTE ENCOLHEU. Até a v1.6 este script
# escrevia `.planning/phases/NN-*/NN-BEADS-MAP.md`: markdown gerado, com um
# par de marcadores, splice do miolo preservando as notas manuais em volta,
# recusa quando o par vinha danificado, `--check` de frescor (exit 3 + diff) e
# uma checagem no doctor para o caso de a cópia envelhecer entre duas
# execuções.
#
# Todo esse aparato existia por causa da CÓPIA, e a cópia existia porque não
# havia outro jeito de olhar o bd. Há: é o próprio comando. Com a vista
# impressa a cada chamada, "estar velha" deixa de ser um estado possível — e
# com ela saem os testes de marcador, de nota manual sobrevivente, de append
# num arquivo sem marcadores e de `--check`, que mediam propriedades de um
# artefato que não é mais produzido.
#
# O que PERMANECE é o que era sobre a vista, não sobre o arquivo: as linhas,
# as duas listas de lacuna, a desambiguação de milestone, os códigos de saída
# e o pino do bd na raiz certa.
#
# Estilo de asserção: um `[[ ]]` ou `! cmd` no meio do teste NÃO reprova neste
# bash, então substring usa `grep -qF` e negativa usa `refute_out`.

load 'helpers'

refute_out() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# Issues da fase 1 com o par de labels e o carimbo {"gsd": {...}}.
# MAP_AUTH2 é fechada; MAP_NOREQ não tem gsd.req e tem de cair na lista de
# lacunas "issues without a requirement", nunca na tabela.
make_map_fixture() {
  bd init -q --prefix map --non-interactive >/dev/null 2>&1
  MAP_AUTH1="$(bd create "Signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"
  MAP_AUTH2="$(bd create "Login flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-02","phase":1,"milestone":"v1.0"}}' --silent)"
  MAP_EXTRA="$(bd create "Password reset" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-03","phase":1,"milestone":"v1.0"}}' --silent)"
  MAP_NOREQ="$(bd create "Stray chore" -t chore -l phase-1,m-v1.0 --silent)"
  bd close "$MAP_AUTH2" >/dev/null
}

@test "a vista sai no stdout, com a fechada inclusa e a sem-requisito na lacuna" {
  require_bd
  make_tmp_repo
  make_map_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1
  [ "$status" -eq 0 ]
  grep -qF "| AUTH-01 | $MAP_AUTH1 | open | Signup flow |" <<<"$output"
  grep -qF "| AUTH-02 | $MAP_AUTH2 | closed | Login flow |" <<<"$output"
  grep -qF "| AUTH-03 | $MAP_EXTRA | open | Password reset |" <<<"$output"
  grep -qF "## Gaps — issues without a requirement" <<<"$output"
  grep -qF "$MAP_NOREQ" <<<"$output"
}

@test "NADA e escrito em disco — a arvore nao ganha um arquivo sequer" {
  require_bd
  make_tmp_repo
  make_map_fixture
  local before after
  before="$(find . -type f | wc -l | tr -d ' ')"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1
  [ "$status" -eq 0 ]

  after="$(find . -type f | wc -l | tr -d ' ')"
  [ "$before" = "$after" ]
  # e o nome do artefato aposentado nao existe em lugar nenhum
  [ -z "$(find . -name '*BEADS-MAP.md' 2>/dev/null)" ]
}

@test "controle negativo: a contagem de arquivos SOBE quando algo escreve" {
  make_tmp_repo
  local before after
  before="$(find . -type f | wc -l | tr -d ' ')"
  echo "forjado" > forjado.md
  after="$(find . -type f | wc -l | tr -d ' ')"
  [ "$before" != "$after" ]
}

@test "a fase nao precisa de diretorio: um label basta" {
  require_bd
  make_tmp_repo
  make_map_fixture
  # Nenhum .planning/, nenhuma pasta de fase — só o bd.
  [ ! -d .planning ]

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1
  [ "$status" -eq 0 ]
  grep -qF "$MAP_AUTH1" <<<"$output"
}

@test "--check e recusado por nome: nao ha copia cujo frescor medir" {
  require_bd
  make_tmp_repo
  make_map_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 --check
  [ "$status" -eq 2 ]
  grep -qF "v1.7" <<<"$output"
  grep -qF "stale" <<<"$output"
}

@test "o argumento de fase aceita '1' e '01' como a mesma fase" {
  require_bd
  make_tmp_repo
  make_map_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 01
  [ "$status" -eq 0 ]
  grep -qF "$MAP_AUTH1" <<<"$output"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1
  [ "$status" -eq 0 ]
  grep -qF "$MAP_AUTH1" <<<"$output"
}

@test "m-* misturados sem --milestone saem 2; --milestone desambigua" {
  require_bd
  make_tmp_repo
  bd init -q --prefix map --non-interactive >/dev/null 2>&1
  local a b
  a="$(bd create "Signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"
  b="$(bd create "Login flow v2" -t task -l phase-1,m-v2.0 \
    --metadata '{"gsd":{"req":"AUTH-02","phase":1,"milestone":"v2.0"}}' --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1
  [ "$status" -eq 2 ]
  grep -qF -- "--milestone" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 --milestone v1.0
  [ "$status" -eq 0 ]
  grep -qF "| AUTH-01 | $a | open |" <<<"$output"
  refute_out "$b"
}

@test "issues legadas sem m-* funcionam, e a lacuna de requisito vem do BD" {
  require_bd
  make_tmp_repo
  bd init -q --prefix map --non-interactive >/dev/null 2>&1
  local c
  c="$(bd create "Rate limiter spike" -t task -l phase-2 \
    --metadata '{"gsd":{"req":"API-99","phase":2,"milestone":"v1.0"}}' --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2
  [ "$status" -eq 0 ]
  grep -qF "| API-99 | $c | open | Rate limiter spike |" <<<"$output"
  # A lista de requisitos da fase saía da linha `**Requirements**:` do
  # ROADMAP.md; agora sai da metadata gsd.req dos próprios beads. Com um só
  # requisito estampado e ele tendo issue, não há lacuna a declarar.
  grep -qF "## Gaps — requirements without an issue" <<<"$output"
  grep -qF "every phase requirement is mapped" <<<"$output"
}

# O NUMERO DE FASE COLIDE ENTRE CICLOS POR CONSTRUCAO — v1.0 e v1.1 tem cada
# uma a sua fase 1 — e ate a v3.0.0 a coluna de requisitos ignorava isso: o
# comando resolvia o ciclo (por --milestone, ou inferindo do rotulo das
# issues) e entao descartava a resposta ao pedir os requisitos ao bd. Uma
# tabela da fase 1 listava os requisitos da fase 1 de TODOS os ciclos que o
# repositorio ja viu.
@test "os requisitos sao os do ciclo pedido, nao os da fase 1 de todos os ciclos" {
  require_bd
  make_tmp_repo
  bd init -q --prefix map --non-interactive >/dev/null 2>&1
  local velho novo
  velho="$(bd create "Signup antigo" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"OLD-01","phase":1,"milestone":"v1.0"}}' --silent)"
  novo="$(bd create "Signup novo" -t task -l phase-1,m-v2.0 \
    --metadata '{"gsd":{"req":"NEW-01","phase":1,"milestone":"v2.0"}}' --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 --milestone v2.0
  [ "$status" -eq 0 ]
  grep -qF "NEW-01" <<<"$output"
  # O requisito do ciclo ENCERRADO nao entra — nem na tabela, nem na lista de
  # lacunas, que e' onde ele apareceria como "requisito sem issue".
  refute_out "OLD-01"
}

# A outra metade: num repo LEGADO, onde issue nenhuma carrega m-*, nao ha
# ciclo a recortar e todo requisito estampado continua valendo. A correcao
# nao pode transformar "sem rotulo de ciclo" em "sem requisito nenhum".
@test "repo legado sem m-*: os requisitos continuam aparecendo" {
  require_bd
  make_tmp_repo
  bd init -q --prefix map --non-interactive >/dev/null 2>&1
  bd create "Rate limiter" -t task -l phase-2 \
    --metadata '{"gsd":{"req":"API-99","phase":2,"milestone":"v1.0"}}' --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2
  [ "$status" -eq 0 ]
  grep -qF "API-99" <<<"$output"
}

@test "--json traz o resumo de maquina, e sem 'file' nem 'changed'" {
  require_bd
  make_tmp_repo
  make_map_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.phase' '1'
  assert_json_eq "$output" '.milestone' 'v1.0'
  assert_json_eq "$output" '.rows' '3'
  assert_json_eq "$output" '.gaps.issues_without_requirement' '1'
  # As duas chaves que descreviam o ARQUIVO saíram junto com ele. Um
  # consumidor que ainda as leia tem de quebrar aqui, não em produção.
  assert_json_eq "$output" 'has("file")' 'false'
  assert_json_eq "$output" 'has("changed")' 'false'
}

@test "erros de uso saem 2" {
  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh"
  [ "$status" -eq 2 ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" not-a-number
  [ "$status" -eq 2 ]
}

@test "bd fora do PATH sai 5" {
  make_tmp_repo
  local stub="$BATS_TEST_TMPDIR/nobd-bin"
  mkdir -p "$stub"
  # Link do interpretador real (não um shim de version-manager que precisa do PATH).
  ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$stub/python3"
  ln -s "$(command -v bash)" "$stub/bash"
  ln -s "$(command -v dirname)" "$stub/dirname"

  run env PATH="$stub" "$stub/bash" "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1
  [ "$status" -eq 5 ]
}

@test "--planning-dir aponta o bd para AQUELE checkout, nao para o cwd" {
  require_bd
  make_tmp_repo
  make_map_fixture
  local target_repo="$CAIRN_TMP_REPO"

  # Um segundo repo bd vira o cwd; suas issues não podem vazar para a vista
  # do repo alvo (o gerador pina o bd na raiz do --planning-dir).
  make_tmp_repo
  bd init -q --prefix other --non-interactive >/dev/null 2>&1
  local stray
  stray="$(bd create "Stray issue from the wrong repo" -t task \
    -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 \
    --planning-dir "$target_repo/.planning"
  [ "$status" -eq 0 ]
  grep -qF "$MAP_AUTH1" <<<"$output"
  refute_out "$stray"
}
