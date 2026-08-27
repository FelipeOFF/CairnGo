#!/usr/bin/env bats
# cairn-gsd.bats — o diferencial do dispatcher das famílias triviais
# (cairn-gsd.py / cairn-gsd.sh) contra os goldens versionados de
# tests/fixtures/gsd-goldens/ (TRIV-04, D-02).
#
# What is under test here:
#   roteamento (D-01)  spellings derivados do contrato; exit 2 fora do
#                      universo; exit 4 nomeando família e fase quando a
#                      família ainda não é servida.
#   diferencial (D-02) o runner itera scenarios.json, monta o fixture
#                      declarativo, roda o wrapper no cwd do fixture e
#                      compara o envelope inteiro com o golden do cenário —
#                      byte-igualdade só para provenance `recorded`;
#                      `derived-from-contract` compara SEMPRE por forma
#                      (exit exato + stdout normalizado).
#
# Exit codes under test: 0/1 pelo contrato do verbo, 2 uso do dispatcher,
# 4 família não implementada.
#
# Assertion style notes (as of cairn-inventory.bats):
#   - every status assertion is on the EXACT value (`-eq 4`), never `-ne 0`:
#     a negation accepts the wrong code and hides a regression.
#   - a failing `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this
#     bash, so substring checks use grep -qF and negations use explicit `if`.
#   - no expectation is typed from the real corpus: fixture expectations come
#     from the manifest + goldens committed beside this suite.
#   - no test touches the network: fixtures are throwaway local dirs, and the
#     real-cache tests (recorder suite) skip when the cache is absent.
#
# MEASURED (2026-08-10, contra cairn/gsd/contratos da tag v1.10.0, HEAD
# 68a04ccf8ef74803bdb651e12c3b85b218bbccdf — cada número recomputável com o
# comando ao lado; o GUARD correspondente recomputa a cada execução):
#   - call_sites das 5 famílias triviais: 97 workflows8 + 12 agents (os ~96
#     sítios do 33-CONTEXT): jq -s '[.[].verbs[].call_sites]
#     | {w: ([.[].workflows8] | add), a: ([.[].agents] | add)}'
#     cairn/gsd/contracts/{config,commit,skills,loop-hooks,dispatch-model}.json
#   - universo trivial: 10 verbos nas 5 famílias (de 87 no agregado):
#     jq '[.verbs[] | select(.family == "config" or .family == "commit"
#     or .family == "skills" or .family == "loop-hooks"
#     or .family == "dispatch-model")] | length' contracts.json
#
# Como a fase 34 adiciona um verbo (o seam de reuso, provado por teste):
#   1. entrada nova em tests/fixtures/gsd-goldens/scenarios.json (id, argv,
#      fixture declarativo, compare, mask, expect_stderr, verb);
#   2. golden irmão <id>.golden.json (gravado por cairn-gsd-record.sh, ou
#      derived-from-contract com a provenance declarada);
#   3. handler novo em HANDLERS de cairn-gsd.py.
#   Nada mais: o runner itera o manifesto e não carrega lista própria de
#   verbos — cenário sem golden reprova, golden órfão reprova e o guard de
#   cobertura exige o handler. Os caminhos do manifesto e dos goldens
#   aceitam override por env (CAIRN_GSD_SCENARIOS / CAIRN_GSD_GOLDENS_DIR),
#   o seam pelo qual o teste de reuso injeta um cenário extra sem tocar
#   nem o manifesto commitado nem uma linha deste runner.

load 'helpers'

GSD="$CAIRN_SCRIPTS_DIR/cairn-gsd.sh"
GOLDENS_DIR="${CAIRN_GSD_GOLDENS_DIR:-$CAIRN_TESTS_DIR/fixtures/gsd-goldens}"
SCENARIOS="${CAIRN_GSD_SCENARIOS:-$GOLDENS_DIR/scenarios.json}"
TAG_COMMIT="68a04ccf8ef74803bdb651e12c3b85b218bbccdf"
CONTRACTS_JSON="$CAIRN_REPO_ROOT/cairn/gsd/contracts/contracts.json"
CONTRACTS_FAM_DIR="$CAIRN_REPO_ROOT/cairn/gsd/contracts"
INVENTORY="$CAIRN_SCRIPTS_DIR/cairn-inventory.sh"

# --- fixture builders, local to this file -----------------------------------
# helpers.bash is loaded by thirty suites and is not touched for one phase's
# shape; the precedent is the inventory suite's local builders.

scenario_spec() {
  jq -c --arg id "$1" '.scenarios[] | select(.id == $id)' "$SCENARIOS"
}

# Monta o fixture declarativo do cenário num diretório descartável.
# Exporta GSD_FIXTURE.
build_scenario_fixture() {
  local id="$1" spec path
  spec="$(scenario_spec "$id")"
  GSD_FIXTURE="$(mktemp -d "${BATS_TEST_TMPDIR:-${TMPDIR:-/tmp}}/gsdfx.XXXXXX")"
  if [ "$(printf '%s' "$spec" | jq -r '.fixture.git')" = "true" ]; then
    git init -q "$GSD_FIXTURE"
    git -C "$GSD_FIXTURE" config user.email "cairn-tests@example.com"
    git -C "$GSD_FIXTURE" config user.name "Cairn Tests"
  fi
  if [ "$(printf '%s' "$spec" | jq -r '.fixture.git_commit // false')" = "true" ]; then
    # cenários de worktree precisam de um commit base (plano 34-04)
    git -C "$GSD_FIXTURE" commit -q --allow-empty -m "fixture base"
  fi
  if [ "$(printf '%s' "$spec" | jq -r '.fixture.planning_config != null')" = "true" ]; then
    mkdir -p "$GSD_FIXTURE/.planning"
    printf '%s' "$spec" | jq '.fixture.planning_config' \
      > "$GSD_FIXTURE/.planning/config.json"
  fi
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    mkdir -p "$GSD_FIXTURE/$(dirname "$path")"
    printf '%s' "$spec" | jq -rj --arg p "$path" '.fixture.files[$p]' \
      > "$GSD_FIXTURE/$path"
  done < <(printf '%s' "$spec" | jq -r '.fixture.files | keys[]')
  # fixture.bd (plano 34-01): bd init + seeds declarativos — o cenário
  # descreve, o builder executa; nada de shell embutido no manifesto.
  # O token "@id" num argv de seed vira o id devolvido pelo seed anterior
  # (bd create --silent imprime só o id), o que deixa create+set-state
  # declaráveis em sequência.
  if [ "$(printf '%s' "$spec" | jq -r '.fixture.bd != null')" = "true" ]; then
    local prefix bd_id seed_count i arg out
    prefix="$(printf '%s' "$spec" | jq -r '.fixture.bd.prefix // "gfx"')"
    if [ "$(printf '%s' "$spec" | jq -r '.fixture.bd.init // true')" = "true" ]; then
      # bd -C exige projeto beads existente — o init roda com cd (molde
      # helpers.bash L353)
      ( cd "$GSD_FIXTURE" \
        && bd init -q --prefix "$prefix" --non-interactive ) \
        >/dev/null 2>&1
    fi
    bd_id=""
    seed_count="$(printf '%s' "$spec" | jq -r '.fixture.bd.seed // [] | length')"
    for ((i = 0; i < seed_count; i++)); do
      local -a seed_argv=()
      while IFS= read -r arg; do
        [ "$arg" = "@id" ] && arg="$bd_id"
        seed_argv+=("$arg")
      done < <(printf '%s' "$spec" | jq -r --argjson i "$i" '.fixture.bd.seed[$i][]')
      out="$(bd -C "$GSD_FIXTURE" "${seed_argv[@]}" 2>/dev/null)" || true
      # só um create alimenta o @id — a saída informativa de set-state e
      # afins não é id e não pode sobrescrever o token
      if [ "${seed_argv[0]}" = "create" ] && [ -n "$out" ]; then
        bd_id="$(printf '%s' "$out" | tail -n1 | awk '{print $1}')"
      fi
    done
  fi
}

# Roda o wrapper no cwd do fixture, capturando stdout/stderr SEPARADOS —
# o diferencial compara o envelope inteiro, então `run` (que os mistura)
# não serve aqui. Exporta GSD_STATUS, GSD_STDOUT, GSD_STDERR (arquivos).
# GSD_SCENARIO_MANIFEST, quando setado, entra pelo seam de env do resolver
# (CAIRN_GSD_CONFIG_MANIFEST); caso contrário o seam é explicitamente limpo
# para o ambiente externo não vazar para dentro do cenário.
gsd_in_fixture() {
  GSD_STDOUT="$BATS_TEST_TMPDIR/gsd-stdout"
  GSD_STDERR="$BATS_TEST_TMPDIR/gsd-stderr"
  GSD_STATUS=0
  if [ -n "${GSD_SCENARIO_MANIFEST:-}" ]; then
    ( cd "$GSD_FIXTURE" \
      && CAIRN_GSD_CONFIG_MANIFEST="$GSD_SCENARIO_MANIFEST" "$GSD" "$@" ) \
      >"$GSD_STDOUT" 2>"$GSD_STDERR" || GSD_STATUS=$?
  else
    ( cd "$GSD_FIXTURE" && env -u CAIRN_GSD_CONFIG_MANIFEST "$GSD" "$@" ) \
      >"$GSD_STDOUT" 2>"$GSD_STDERR" || GSD_STATUS=$?
  fi
}

# O clone em cache com HEAD verificado existe nesta máquina? (gate dos
# testes do caminho (b) da cadeia do manifest.)
real_cache_manifest() {
  local cache="$CAIRN_REPO_ROOT/.cairn/cache/gsd-core-v1.10.0"
  [ -d "$cache/.git" ] || return 1
  [ "$(git -C "$cache" rev-parse HEAD 2>/dev/null)" = "$TAG_COMMIT" ] \
    || return 1
  find "$cache" -name config-defaults.manifest.json -not -path '*/.git/*' \
    | grep -q .
}

# Aplica o mask do cenário a um arquivo JSON: valida o valor no jq_path
# contra o regex e o substitui pelo marcador. Falha quando o valor não casa.
# Um valor JÁ mascarado ("<masked>") passa — é o lado golden da comparação,
# que o recorder grava com o marcador no lugar do valor vivo.
apply_mask_file() {
  local spec="$1" file="$2" out p re
  out="$(cat "$file")"
  while IFS=$'\t' read -r p re; do
    [ -n "$p" ] || continue
    out="$(printf '%s' "$out" | jq --arg re "$re" \
      "if (${p} | type == \"string\" and (test(\$re) or . == \"<masked>\")) \
       then (${p}) = \"<masked>\" \
       else error(\"mask: valor em ${p} não casa o regex\") end")" || return 1
  done < <(printf '%s' "$spec" | jq -r \
    '.mask | to_entries[] | [.key, .value] | @tsv')
  printf '%s\n' "$out"
}

# Compara a última execução (gsd_in_fixture) com o golden do cenário.
# Uso: compare_with_golden <id> [<golden alternativo>]  — return 1 acumulável.
compare_with_golden() {
  local id="$1" golden="${2:-$GOLDENS_DIR/$id.golden.json}"
  local spec cmp prov exp_status
  spec="$(scenario_spec "$id")"
  if [ ! -f "$golden" ]; then
    echo "golden ausente: $golden" >&2
    return 1
  fi
  cmp="$(printf '%s' "$spec" | jq -r '.compare')"
  prov="$(jq -r '.provenance' "$golden")"
  exp_status="$(jq -r '.expect.exit_code' "$golden")"
  if [ "$GSD_STATUS" -ne "$exp_status" ]; then
    echo "cenário $id: exit $GSD_STATUS, golden espera $exp_status" >&2
    echo "cenário $id stderr: $(cat "$GSD_STDERR")" >&2
    return 1
  fi
  local exp_out="$BATS_TEST_TMPDIR/expected-stdout"
  jq -rj '.expect.stdout // ""' "$golden" > "$exp_out"
  local act="$GSD_STDOUT"
  if [ "$(printf '%s' "$spec" | jq -r '.mask != null')" = "true" ]; then
    local masked_act="$BATS_TEST_TMPDIR/masked-act"
    local masked_exp="$BATS_TEST_TMPDIR/masked-exp"
    if ! apply_mask_file "$spec" "$act" > "$masked_act"; then
      echo "cenário $id: mask não casa no stdout real" >&2
      return 1
    fi
    if ! apply_mask_file "$spec" "$exp_out" > "$masked_exp"; then
      echo "cenário $id: mask não casa no golden" >&2
      return 1
    fi
    act="$masked_act"
    exp_out="$masked_exp"
  fi
  if [ "$prov" = "recorded" ]; then
    # Golden gravado do binário real: a comparação é literal por compare.
    case "$cmp" in
      bytes)
        if ! cmp -s "$act" "$exp_out"; then
          echo "cenário $id: stdout diverge do golden (bytes)" >&2
          diff "$exp_out" "$act" >&2 || true
          return 1
        fi
        ;;
      json)
        if [ "$(jq -S . "$act" 2>/dev/null)" != \
             "$(jq -S . "$exp_out" 2>/dev/null)" ]; then
          echo "cenário $id: stdout diverge do golden (json)" >&2
          return 1
        fi
        ;;
      *)
        echo "cenário $id: compare desconhecido: $cmp" >&2
        return 1
        ;;
    esac
  else
    # derived-from-contract não promete os bytes do binário real: a
    # comparação é SEMPRE por forma — exit exato (acima) + stdout
    # normalizado (jq -S para json; newline final normalizado para texto).
    if [ "$cmp" = "json" ] && [ -s "$act" ]; then
      if [ "$(jq -S . "$act" 2>/dev/null)" != \
           "$(jq -S . "$exp_out" 2>/dev/null)" ]; then
        echo "cenário $id: stdout diverge do golden (forma json)" >&2
        return 1
      fi
    else
      if [ "$(cat "$act")" != "$(cat "$exp_out")" ]; then
        echo "cenário $id: stdout diverge do golden (forma texto)" >&2
        diff "$exp_out" "$act" >&2 || true
        return 1
      fi
    fi
  fi
  if [ "$(printf '%s' "$spec" | jq -r '.expect_stderr')" = "true" ]; then
    local exp_err
    exp_err="$(jq -r '.expect.stderr // ""' "$golden")"
    if [ "$(cat "$GSD_STDERR")" != "$exp_err" ]; then
      echo "cenário $id: stderr diverge do golden" >&2
      return 1
    fi
  fi
  return 0
}

# Roda um cenário do manifesto de ponta a ponta e compara com o golden.
# Cenários com requires "config-manifest" recebem o manifest fixture
# COMMITADO pelo seam de env — o diferencial roda verde offline; a cadeia
# real (caminho (b), clone em cache) tem testes próprios skip-gated abaixo.
run_scenario() {
  local id="$1" req
  build_scenario_fixture "$id"
  req="$(jq -r --arg id "$id" \
    '.scenarios[] | select(.id == $id) | .requires // empty' "$SCENARIOS")"
  if [ "$req" = "config-manifest" ]; then
    GSD_SCENARIO_MANIFEST="$GOLDENS_DIR/config-defaults.fixture.json"
  else
    GSD_SCENARIO_MANIFEST=""
  fi
  local -a argv=()
  local a
  while IFS= read -r a; do
    argv+=("$a")
  done < <(jq -r --arg id "$id" \
    '.scenarios[] | select(.id == $id) | .argv[]' "$SCENARIOS")
  gsd_in_fixture "${argv[@]}"
  GSD_SCENARIO_MANIFEST=""
  compare_with_golden "$id"
}

# --- o diferencial ----------------------------------------------------------

@test "diferencial: todo cenario do manifesto bate com o seu golden" {
  local id fails=0
  while IFS= read -r id; do
    [ -n "$id" ] || continue
    if ! run_scenario "$id"; then
      fails=$((fails + 1))
    fi
  done < <(jq -r '.scenarios[].id' "$SCENARIOS")
  [ "$fails" -eq 0 ]
}

@test "controle negativo: golden adulterado no stdout REPROVA o comparador" {
  local id="config-get-scope-hit"
  # linha de base: o cenário intacto passa
  run_scenario "$id"
  # o mesmo envelope contra um golden adulterado tem que reprovar
  local tampered="$BATS_TEST_TMPDIR/tampered.golden.json"
  jq '.expect.stdout = "ADULTERADO\n"' "$GOLDENS_DIR/$id.golden.json" \
    > "$tampered"
  if compare_with_golden "$id" "$tampered" 2>/dev/null; then
    echo "golden adulterado passou no comparador — o diferencial não morde" >&2
    return 1
  fi
}

@test "manifesto e goldens: schema minimo, provenance declarada e fonte pinada" {
  jq -e '.schema_version == 1' "$SCENARIOS"
  jq -e --arg c "$TAG_COMMIT" '.source.commit == $c' "$SCENARIOS"
  jq -e '.scenarios | length >= 5' "$SCENARIOS"
  jq -e '[.scenarios[] | select((.id | length) == 0
    or (.argv | type != "array" or length == 0)
    or ((.compare == "bytes" or .compare == "json") | not))] | length == 0' \
    "$SCENARIOS"
  local g fails=0
  for g in "$GOLDENS_DIR"/*.golden.json; do
    if ! jq -e --arg c "$TAG_COMMIT" '
        .schema_version == 1
        and (.provenance == "derived-from-contract"
             or .provenance == "recorded")
        and .source.commit == $c
        and (.scenario | type == "string" and length > 0)
        and (.expect | has("exit_code") and has("stdout"))
        and (.expect.exit_code | type == "number" and . == floor)
        and (.expect.stdout | type == "string")
      ' "$g" >/dev/null; then
      echo "golden com envelope inválido: $g" >&2
      fails=$((fails + 1))
    fi
    # doutrina de determinismo: NENHUM timestamp num golden — filtrado por
    # CHAVE (jq sobre os objetos), não por prosa no corpo dos valores
    if ! free_of_timestamp_keys "$g"; then
      echo "golden carrega chave de timestamp: $g" >&2
      fails=$((fails + 1))
    fi
    # todo golden pertence a um cenário do manifesto
    if ! jq -e --arg id "$(jq -r '.scenario' "$g")" \
        '.scenarios[] | select(.id == $id)' "$SCENARIOS" >/dev/null; then
      echo "golden órfão de cenário: $g" >&2
      fails=$((fails + 1))
    fi
  done
  [ "$fails" -eq 0 ]
}

# --- integridade manifesto<->goldens e serializacao (plano 03, Task 2) ------

# Ids dos goldens de um diretório (basename sem .golden.json), ordenados.
golden_ids_of() {
  local g
  for g in "$1"/*.golden.json; do
    [ -e "$g" ] || continue
    basename "$g" .golden.json
  done | sort
}

# Serialização da casa num arquivo JSON: indent 2 + sort_keys (o jq -S
# reserializado bate byte a byte com o arquivo) e newline final.
house_serialization_ok() {
  [ "$(cat "$1")" = "$(jq -S . "$1")" ] || return 1
  [ "$(tail -c1 "$1" | od -An -c | tr -d ' ')" = '\n' ] || return 1
}

# Guard de determinismo por CHAVE (não por prosa): nenhum objeto do golden
# carrega chave de timestamp em nenhum nível.
free_of_timestamp_keys() {
  jq -e '[.. | objects | keys[]]
    | map(select(. == "timestamp" or . == "recorded_at"
      or . == "generated_at" or . == "date" or . == "time"))
    | length == 0' "$1" >/dev/null
}

@test "integridade: todo cenario tem golden irmao e todo golden referencia cenario (comm vazio nos dois sentidos)" {
  local ids goldens d
  ids="$(jq -r '.scenarios[].id' "$SCENARIOS" | sort)"
  goldens="$(golden_ids_of "$GOLDENS_DIR")"
  d="$(comm -23 <(printf '%s\n' "$ids") <(printf '%s\n' "$goldens"))"
  if [ -n "$d" ]; then
    printf 'cenarios do manifesto SEM golden irmao:\n%s\n' "$d" >&2
    return 1
  fi
  d="$(comm -13 <(printf '%s\n' "$ids") <(printf '%s\n' "$goldens"))"
  if [ -n "$d" ]; then
    printf 'goldens SEM cenario no manifesto:\n%s\n' "$d" >&2
    return 1
  fi
  # e o campo .scenario de cada golden bate com o nome do arquivo — o comm
  # acima compara nomes; esta metade prende o conteúdo ao nome
  local g fails=0
  for g in "$GOLDENS_DIR"/*.golden.json; do
    if [ "$(jq -r '.scenario' "$g")" != "$(basename "$g" .golden.json)" ]; then
      echo "golden cujo .scenario nao bate com o nome do arquivo: $g" >&2
      fails=$((fails + 1))
    fi
  done
  [ "$fails" -eq 0 ]
}

@test "controle negativo: golden orfao num diretorio fixture VAZA pelo comm" {
  local dir="$BATS_TEST_TMPDIR/goldens-orfao"
  mkdir -p "$dir"
  cp "$GOLDENS_DIR/config-get-scope-hit.golden.json" "$dir/"
  jq -S '.scenario = "cenario-que-nao-existe"' \
    "$GOLDENS_DIR/config-get-scope-hit.golden.json" \
    > "$dir/cenario-que-nao-existe.golden.json"
  local ids goldens d
  ids="$(jq -r '.scenarios[].id' "$SCENARIOS" | sort)"
  goldens="$(golden_ids_of "$dir")"
  d="$(comm -13 <(printf '%s\n' "$ids") <(printf '%s\n' "$goldens"))"
  [ -n "$d" ]
  printf '%s\n' "$d" | grep -qF "cenario-que-nao-existe"
}

@test "serializacao da casa: scenarios.json, divergences.json e todo golden sao jq -S estaveis com newline final" {
  local f fails=0
  for f in "$SCENARIOS" "$GOLDENS_DIR/divergences.json" \
    "$GOLDENS_DIR"/*.golden.json; do
    if ! house_serialization_ok "$f"; then
      echo "fora da serializacao da casa (indent 2 + sort_keys + newline): $f" >&2
      fails=$((fails + 1))
    fi
  done
  [ "$fails" -eq 0 ]
}

@test "controle negativo: JSON cru sem newline (e sem sort) REPROVA a serializacao da casa" {
  local raw="$BATS_TEST_TMPDIR/cru.json"
  printf '{"b": 1, "a": 2}' > "$raw"
  if house_serialization_ok "$raw"; then
    echo "JSON cru de uma linha passou no guard de serializacao" >&2
    return 1
  fi
  # a metade do newline isolada: bem formatado e ordenado, mas sem newline
  local nonl="$BATS_TEST_TMPDIR/sem-newline.json"
  printf '%s' "$(jq -S . "$raw")" > "$nonl"
  if house_serialization_ok "$nonl"; then
    echo "JSON sem newline final passou no guard de serializacao" >&2
    return 1
  fi
}

@test "controle negativo: chave de timestamp num golden fixture REPROVA o guard de determinismo" {
  local g="$BATS_TEST_TMPDIR/com-timestamp.golden.json"
  jq -S '.recorded_at = "2026-08-10T00:00:00Z"' \
    "$GOLDENS_DIR/config-get-scope-hit.golden.json" > "$g"
  if free_of_timestamp_keys "$g"; then
    echo "golden com chave recorded_at passou no guard" >&2
    return 1
  fi
}

@test "seam de reuso: cenario injetado num manifesto fixture executa SEM mudanca no runner" {
  # A heranca das fases 34-35: verbo novo = entrada no manifesto + golden +
  # handler (ver o bloco do cabecalho). O manifesto fixture recebe um
  # cenario extra apontando um verbo ja implementado, e as MESMAS funcoes
  # do diferencial o executam pelo override de caminho.
  local base_count manifest seam_dir
  base_count="$(jq '.scenarios | length' "$SCENARIOS")"
  manifest="$BATS_TEST_TMPDIR/seam-scenarios.json"
  seam_dir="$BATS_TEST_TMPDIR/seam-goldens"
  mkdir -p "$seam_dir"
  jq -S '.scenarios += [(.scenarios[]
    | select(.id == "config-get-scope-hit")
    | .id = "seam-cenario-injetado")]' "$SCENARIOS" > "$manifest"
  jq -S '.scenario = "seam-cenario-injetado"' \
    "$GOLDENS_DIR/config-get-scope-hit.golden.json" \
    > "$seam_dir/seam-cenario-injetado.golden.json"
  SCENARIOS="$manifest"
  GOLDENS_DIR="$seam_dir"
  [ "$(jq '.scenarios | length' "$SCENARIOS")" -eq $((base_count + 1)) ]
  run_scenario "seam-cenario-injetado"
}

@test "seam de reuso, o inverso: cenario no manifesto SEM golden reprova o runner" {
  local manifest="$BATS_TEST_TMPDIR/seam-scenarios.json"
  local seam_dir="$BATS_TEST_TMPDIR/seam-goldens-vazio"
  mkdir -p "$seam_dir"
  jq -S '.scenarios += [(.scenarios[]
    | select(.id == "config-get-scope-hit")
    | .id = "seam-sem-golden")]' "$SCENARIOS" > "$manifest"
  SCENARIOS="$manifest"
  GOLDENS_DIR="$seam_dir"
  if run_scenario "seam-sem-golden" 2>/dev/null; then
    echo "cenario sem golden passou no runner — o comparador nao morde" >&2
    return 1
  fi
}

# --- o dispatcher em si -----------------------------------------------------

# Os representantes de familia-nao-implementada (35-04) e de orfao (35-05)
# sairam quando as superficies passaram a responder — a mecanica exit-4
# cumpriu o papel. O guarda remanescente da via exit-4/exit-2 e o controle
# negativo do verbo forjado.

@test "dispatcher: verbo fora do universo morre exit 2 (uso do dispatcher)" {
  make_tmp_repo
  run "$GSD" query verbo-que-nao-existe
  [ "$status" -eq 2 ]
}

@test "dispatcher: flag desconhecida antes do verbo e uso do dispatcher, exit 2" {
  make_tmp_repo
  run "$GSD" --nope query config-get model_profile
  [ "$status" -eq 2 ]
}

@test "config-get: flag desconhecida DENTRO do verbo e ignorada best-effort" {
  build_scenario_fixture "config-get-scope-hit"
  gsd_in_fixture query config-get model_profile --force-isolation
  [ "$GSD_STATUS" -eq 0 ]
  # sem --raw a saida e o JSON do valor (semantica medida do binario)
  [ "$(cat "$GSD_STDOUT")" = '"quality"' ]
}

@test "config-get emite nao-ASCII sem escape unicode no caminho JSON" {
  build_scenario_fixture "config-get-nonascii"
  gsd_in_fixture query config-get saudacao
  [ "$GSD_STATUS" -eq 0 ]
  grep -qF 'ção' "$GSD_STDOUT"
  if grep -qF '\u00e7' "$GSD_STDOUT"; then
    echo "escape unicode vazou na saída JSON" >&2
    return 1
  fi
}

@test "config-get sem --raw e com --raw divergem na forma: JSON com aspas vs texto cru" {
  build_scenario_fixture "config-get-scope-hit"
  gsd_in_fixture query config-get model_profile
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = '"quality"' ]
  gsd_in_fixture query config-get model_profile --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "quality" ]
  # nenhum dos dois carrega newline final (writeAllSync do binario)
  [ "$(tail -c1 "$GSD_STDOUT")" = "y" ]
}

# --- cobertura contra o universo do contrato (plano 03, Task 1) -------------

@test "CHECK-04: baseline do cairn-doctor fixada — o pin so muda com razao escrita" {
  # O teste E o registro (plano 35-01, Task 1): valores pinados como
  # constantes locais, um dono so. O pin so e atualizado DELIBERADAMENTE
  # pela fase que evoluir o doctor — nunca para "fazer o teste passar".
  #
  # ATUALIZADO 2026-08-11: a v1.6 evoluiu o doctor em duas checagens, ambas
  # nascidas de defeito medido nesta arvore e nenhuma delas cosmetica.
  #   - 22, issues-recoverable: um clone limpo nao recuperava NENHUMA das
  #     176 issues, enquanto o CLAUDE.md afirmava por escrito, havia
  #     semanas, que o JSONL era um export passivo. Nao existia.
  #   - 24, export-identity: o export rastreado publicava hostname e
  #     caminho absoluto de home num repositorio PUBLICO.
  #
  # ATUALIZADO 2026-08-12 pela FASE 37, que e' a fase que o pin anterior
  # nomeava como dona desta atualizacao (PLUG-02). O que mudou:
  #   - o check 10 (gsd-capability) INVERTEU de sentido. Perguntava se a
  #     capability cairn estava registrada contra o gsd-core instalado, e
  #     prescrevia INSTALAR gsd-core@cairngo; passou a perguntar se o
  #     runtime vendorizado esta inteiro, e prescreve UNINSTALL para
  #     qualquer linhagem externa (gsd-core ou gsd 4.x) ainda instalada.
  #   - resíduo em .gsd/ virou WARN com fix de limpeza, avaliado DEPOIS
  #     dos dois FAIL, porque uma maquina que migrou tem as duas coisas.
  #   - entrou o seam CAIRN_VENDORED_GSD, para que a recusa "este runtime
  #     esta incompleto" seja provavel por teste.
  # A inversao esta provada nas DUAS direcoes em
  # tests/cairn-doctor-lineage.bats (9 asserções, 9/9 vermelhas contra o
  # doctor do pin anterior).
  # ATUALIZADO 2026-08-12 pela v1.7, e a razao e' uma CORRECAO DE ESCOPO: ler
  # `.planning/` para MIGRAR nao e' o mesmo que ler `.planning/` como VERDADE.
  # Quem instala o cairn quase sempre vem do GSD e chega com um `.planning/`
  # cheio; o doctor era cego para esse diretorio e deixava essa pessoa sem
  # rota nenhuma. Entrou o achado `gsd-unmigrated` (com `migrate_detect_state`),
  # WARN e NUNCA fail — porque um GSD por migrar e' uma ROTA, nao um defeito.
  # O ramo de um-lado-so ja existia, mas simetrico: as duas direcoes davam a
  # mesma frase, e uma frase que nao distingue os dois casos nao orienta
  # nenhum dos dois.
  # ATUALIZADO 2026-08-12 pela fase 39, e a razao e' a MUDANCA DE FONTE: o
  # doctor parou de ler o roteiro do markdown e passou a deriva-lo do bd
  # (cairn_source.py). Milestone, fase ativa, fases, requisitos e completude
  # vem do tracker; o `.planning/ROADMAP.md`, quando existe, entra so como
  # ENTRADA de importacao — e' o que sustenta req-issue, phase-complete-open
  # e orphans num repo por migrar, e a leitura morre sozinha quando o
  # diretorio nao existe.
  #
  # Duas checagens mudaram de veredito por decisao, nao por acidente:
  #   - maps-fresh saiu INTEIRA (out-of-scope): media o frescor de uma copia
  #     do bd em disco, e a copia deixou de existir — o mapa e' impresso.
  #   - claims-stale sem trabalho aberto passou a ler `ok` em vez de
  #     `no-input`: com a fase ativa derivada, "nao ha fase ativa" quer dizer
  #     "nao ha claim", o que RESPONDE a pergunta em vez de impedi-la.
  #     Como no-input, deixava todo repo de trabalho concluido
  #     permanentemente INCOMPLETE (medido: dois casos de phase-artifacts
  #     falharam por isso, sem ter relacao com claims).
  # ATUALIZADO 2026-08-14 pela 3.1.0, e a razao sao DUAS mudancas de
  # comportamento no doctor, nenhuma cosmetica:
  #   - `label-pairs` ganhou uma SEGUNDA regra, emitida como achado distinto:
  #     um label de versao CRU (`v1.6` em vez de `m-v1.6`) e' um m-*
  #     malformado — nao casa com `bd list -l m-v1.6`, com listagem de ciclo
  #     nenhuma, nem com o board. Medido nesta arvore: o epico CairnGo-dhl
  #     carregava um e sobreviveu ao fecho INTEIRO do v1.6 (72 issues
  #     fechadas, release publicada), encontrado a mao meses depois. Achado
  #     separado do par quebrado porque a correcao e' outra — renomear o
  #     label, nao emparelha-lo com um phase-N que a issue talvez nem devesse
  #     ter. Backlog fica de fora por construcao, e o controle disso esta em
  #     tests/cairn-doctor.bats.
  #   - sairam tres constantes que nenhuma mensagem consumia
  #     (ACTIVE_PHASE_READERS, ACTIVE_PHASE_ISSUE, REQ_LEDGER_OUT_OF_REMIT_KINDS),
  #     uma delas endereçando um bead ja fechado. A medicao que a primeira
  #     carregava — as cinco superficies que leem active_phase — foi
  #     preservada na docstring de check_claims_stale, que e' onde ela
  #     informa quem le.
  # ATUALIZADO 2026-08-15 pela v3.3, e a razao e' o GATE GLOBAL que caiu.
  #
  # O doctor recusava todo repositorio com `.beads/` e sem `.planning/` — o
  # DESTINO da migracao, que e' o que o cairn existe para servir. Saia exit 0
  # com um note e ZERO checagens, e a mensagem ainda mandava rodar
  # /cairn:migrate "to bootstrap the missing side": recriar o diretorio que a
  # v1.7 aposentou. Medido depois: 24 checagens avaliadas onde havia um note.
  #
  # Mesma familia do ship gate corrigido na v3.1.0 — o gate foi consertado e
  # este ficou, com a mesma forma, no arquivo ao lado.
  #
  # O defeito foi reportado de FORA, por um agente usando o cairn 3.2.0 noutro
  # repositorio. Nenhum teste daqui o pegaria: havia um pinando o
  # comportamento errado como contrato, com uma nota que explicava a vacuidade
  # e culpava a coisa errada. Substituido por um par — o repo migrado e'
  # auditado, e a direcao inversa (.planning sem .beads) segue nao-aplicavel
  # com o achado gsd-unmigrated e a rota.
  #
  # Junto, um `if has_planning:` aninhado numa condicao que ja o exigia:
  # sempre-verdadeiro com forma de teste, a armadilha do `parent` do bd.
  # ATUALIZADO 2026-08-27 pelo ciclo v4.0 (phases 43, 44, 46), que e' o dono
  # desta atualizacao. Tres checks novos, nenhum cosmetico:
  #   - milestone-carrier (phase 43): todo ciclo aberto tem exatamente um
  #     carrier de milestone — ⚠ sem carrier nesta linha (✗ a partir da 4.1),
  #     ✗ com dois. O milestone deixou de ser so' um label.
  #   - jira-links (phase 44): gap, duplicata 1:1, chave inexistente (via o
  #     seam CAIRN_JIRA_FETCH ou REST), epic drift, status divergente e fila
  #     pendente; ⊘ out-of-scope sem backend jira em .cairn/sync.json.
  #   - planning-writes (phase 46): um .md novo ou modificado sob
  #     .planning/phases/ rastreado pelo git e' um documento escrito onde o
  #     bead e' a fonte, com o cairn-record que o substitui.
  # De quebra: 'milestone' entrou em NO_PHASE_EXEMPT, o lease-stale nomeia
  # leases de bead, e jira_fetch valida a chave antes de qualquer URL.
  # ATUALIZADO 2026-08-27 pela phase 54 (DOCTOR-01, CairnGo-9926): o
  # finding issues-recoverable aconselhava `bd export --all`, que no bd
  # 1.1.0 arrasta as memorias do `bd remember` para o export e trava o
  # auto-export ("shrink guard"). Os dois ramos passam a `bd export -o`,
  # com o comentario que diz por que — seis linhas, texto de conselho,
  # nenhuma checagem nova. O primeiro push da phase saiu SEM este pin
  # (run 33108429234, cancelada); este e' o fix-up.
  # ATUALIZADO 2026-08-27 pela phase 55 (DOCTOR-02, CairnGo-76u8), a
  # release 4.1.0: o check milestone-carrier deixa de avisar e passa a
  # REPROVAR um ciclo aberto sem carrier — a D-02 da phase 43 deu
  # exatamente uma release (4.0) para quem fez upgrade com ciclo aberto
  # criar o bead, e ela passou. O item perde a frase datada e ganha "the
  # bead /cairn:new and /cairn:milestone new create". Nenhum check novo.
  local doctor="$CAIRN_SCRIPTS_DIR/cairn-doctor.py"
  local pinned_blob="20f59c24119c916a51cc3527b155fdaf850a270b"
  local pinned_lines=4841
  [ -f "$doctor" ]
  local blob lines
  blob="$(git hash-object "$doctor")"
  if [ "$blob" != "$pinned_blob" ]; then
    echo "cairn-doctor.py MUDOU (blob $blob != baseline $pinned_blob) —" >&2
    echo "o pin so e atualizado deliberadamente pela fase que evoluir o" >&2
    echo "doctor, e com a razao escrita junto, como as tres acima" >&2
    return 1
  fi
  lines="$(wc -l < "$doctor" | tr -d ' ')"
  if [ "$lines" -ne "$pinned_lines" ]; then
    echo "cairn-doctor.py com $lines linhas != baseline $pinned_lines —" >&2
    echo "ver a mensagem do pin de blob" >&2
    return 1
  fi
}

# Universo COBERTO: as 11 famílias implementadas (5 triviais da 33 + 5 da
# 34 + checagem da 35). A exclusão nominal dos órfãos acabou no plano
# 35-05: a constante do dispatcher virou ROTA (MISC_CHECK_VERBS) e o
# universo derivado do inventário é o próprio 87.
# $1 = um contracts.json (o real, ou o fixture do controle negativo).
trivial_verbs_of() {
  jq -r '.verbs | to_entries[]
    | select(.value.family == "config" or .value.family == "commit"
      or .value.family == "skills" or .value.family == "loop-hooks"
      or .value.family == "dispatch-model" or .value.family == "estado"
      or .value.family == "roadmap-phase" or .value.family == "worktree"
      or .value.family == "init" or .value.family == "misc"
      or .value.family == "checagem")
    | .key' "$1" | sort
}

@test "cobertura: universo trivial do contrato == handlers do dispatcher, comm vazio nos dois sentidos" {
  local contract_verbs implemented all_verbs missing extra
  contract_verbs="$(trivial_verbs_of "$CONTRACTS_JSON")"
  implemented="$("$GSD" --list-implemented | sort)"
  # vivacidade: as duas enumeracoes tem que existir antes de comparar
  [ -n "$contract_verbs" ]
  [ -n "$implemented" ]
  # universo − handlers: verbo trivial do contrato sem handler reprova
  missing="$(comm -23 <(printf '%s\n' "$contract_verbs") \
    <(printf '%s\n' "$implemented"))"
  if [ -n "$missing" ]; then
    printf 'verbos triviais do contrato SEM handler no dispatcher:\n%s\n' \
      "$missing" >&2
    return 1
  fi
  # FECHO BIDIRECIONAL (fase 35, plano 05): com as 11 famílias no filtro
  # o universo coberto É o inventário inteiro (87) — handler sem contrato
  # é superfície fantasma e reprova; o comm fecha vazio nos DOIS sentidos.
  extra="$(comm -13 <(printf '%s\n' "$contract_verbs") \
    <(printf '%s\n' "$implemented"))"
  if [ -n "$extra" ]; then
    printf 'handlers implementados FORA do universo coberto:\n%s\n' \
      "$extra" >&2
    return 1
  fi
  # o fecho é 89/89: a contagem prende o universo ao número do contrato.
  #
  # Era 87 — o universo medido pelo inventário em 2026-08-10, escopos
  # workflows8 + agents. A fase 38 mediu um terceiro escopo que o runtime
  # executa e o inventário não varre, gsd-core/references/, e achou dois
  # verbos chamados de lá que nenhum contrato trazia:
  # `worktree.set-baseref` e `requirements.revert-phase`, ambos embrulhados
  # em `|| true`, ambos morrendo exit 2 sem que ninguém visse. Os dois
  # entraram no contrato com `scope: "references"` e estão declarados em
  # universe.references_extension. O pin só se move com razão escrita, e
  # esta é ela.
  [ "$(printf '%s\n' "$contract_verbs" | wc -l | tr -d ' ')" -eq 89 ]
}

@test "controle negativo: verbo trivial forjado no universo fixture VAZA pela mesma comparacao" {
  # A mesma comparacao do guard de cobertura, contra um universo simulado
  # que e o agregado real MAIS um verbo trivial forjado — se o comm o
  # engolisse, a cobertura estaria furada (molde de gsd-contracts.bats).
  local simulated="$BATS_TEST_TMPDIR/forged-universe.json"
  jq '.verbs += {"forged-trivial-verb":
    {"family": "config", "file": "config.json"}}' \
    "$CONTRACTS_JSON" > "$simulated"
  local contract_verbs implemented missing
  contract_verbs="$(trivial_verbs_of "$simulated")"
  implemented="$("$GSD" --list-implemented | sort)"
  missing="$(comm -23 <(printf '%s\n' "$contract_verbs") \
    <(printf '%s\n' "$implemented"))"
  [ -n "$missing" ]
  printf '%s\n' "$missing" | grep -qF "forged-trivial-verb"
}

@test "call_sites: a soma das 5 familias, recomputada dos contratos, da 97 workflows8 + 12 agents" {
  # A expectativa e recomputada dos proprios JSONs de contrato a cada
  # execucao, nunca digitada de memoria — os numeros citados vivem no
  # bloco MEASURED datado do cabecalho desta suite.
  local w a
  w="$(jq -s '[.[].verbs[].call_sites.workflows8] | add' \
    "$CONTRACTS_FAM_DIR/config.json" "$CONTRACTS_FAM_DIR/commit.json" \
    "$CONTRACTS_FAM_DIR/skills.json" "$CONTRACTS_FAM_DIR/loop-hooks.json" \
    "$CONTRACTS_FAM_DIR/dispatch-model.json")"
  a="$(jq -s '[.[].verbs[].call_sites.agents] | add' \
    "$CONTRACTS_FAM_DIR/config.json" "$CONTRACTS_FAM_DIR/commit.json" \
    "$CONTRACTS_FAM_DIR/skills.json" "$CONTRACTS_FAM_DIR/loop-hooks.json" \
    "$CONTRACTS_FAM_DIR/dispatch-model.json")"
  [ "$w" -eq 97 ]
  [ "$a" -eq 12 ]
}

# --- ex-orfaos de CHECK-03 pelo irmao DIRETO (plano 35-05) ------------------
# run-with-timeout e exit-only e review-lane fala texto: verificacao por
# bats direto no irmao (python3); o atravessamento via $GSD (rota
# MISC_CHECK_VERBS + argv opaco pelo exec) e provado no teste abaixo.

@test "ex-orfaos: a rota tres-destinos atravessa o dispatcher de ponta a ponta" {
  make_tmp_repo
  run "$GSD" query audit-open --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | jq -e 'has("counts") and has("scanned_at")'
  # argv opaco: o exec entrega argv[n:] intocado ao wrapper exit-only
  run "$GSD" run-with-timeout 5 -- sh -c 'exit 7'
  [ "$status" -eq 7 ]
  run "$GSD" review-lane flags --selected claude
  [ "$status" -eq 0 ]
  [ "$output" = "--claude" ]
}

CHECK_SIB="$CAIRN_SCRIPTS_DIR/cairn-gsd-check.py"

@test "run-with-timeout (irmao direto): comando sai 7 -> wrapper sai 7" {
  run python3 "$CHECK_SIB" run-with-timeout 5 -- sh -c 'exit 7'
  [ "$status" -eq 7 ]
}

@test "run-with-timeout (irmao direto): estouro do timer sai 124" {
  run python3 "$CHECK_SIB" run-with-timeout 1 -- sleep 3
  [ "$status" -eq 124 ]
}

@test "run-with-timeout (irmao direto): comando inexistente sai 127" {
  run python3 "$CHECK_SIB" run-with-timeout 5 -- /comando/que/nao/existe
  [ "$status" -eq 127 ]
}

@test "run-with-timeout (irmao direto): sem permissao de exec sai 126" {
  local f="$BATS_TEST_TMPDIR/nao-executavel"
  printf '#!/bin/sh\nexit 0\n' > "$f"
  chmod -x "$f"
  run python3 "$CHECK_SIB" run-with-timeout 5 -- "$f"
  [ "$status" -eq 126 ]
}

@test "run-with-timeout (irmao direto): seconds 0 roda SEM timer" {
  run python3 "$CHECK_SIB" run-with-timeout 0 -- sh -c 'exit 3'
  [ "$status" -eq 3 ]
}

@test "run-with-timeout (irmao direto): seconds vazio e usage exit 2 (fail-safe)" {
  run python3 "$CHECK_SIB" run-with-timeout '' -- true
  [ "$status" -eq 2 ]
}

@test "run-with-timeout (irmao direto): seconds negativo e usage exit 2" {
  run python3 "$CHECK_SIB" run-with-timeout -5 -- true
  [ "$status" -eq 2 ]
}

@test "run-with-timeout (irmao direto): sufixo s GNU-style aceito" {
  run python3 "$CHECK_SIB" run-with-timeout 5s -- true
  [ "$status" -eq 0 ]
}

@test "run-with-timeout (irmao direto): stdout do filho atravessa intocado" {
  run python3 "$CHECK_SIB" run-with-timeout 5 -- echo atravessou
  [ "$status" -eq 0 ]
  [ "$output" = "atravessou" ]
}

@test "review-lane (irmao direto): flags emite as flags das lanes linha a linha" {
  # 12 lanes / 13 flags (antigravity declara duas) — o dado de
  # REVIEWER_LANES transcrito da tag
  run python3 "$CHECK_SIB" review-lane flags
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -qxF -- '--gemini'
  printf '%s\n' "$output" | grep -qxF -- '--agy'
  [ "$(printf '%s\n' "$output" | wc -l | tr -d ' ')" -eq 13 ]
}

@test "review-lane (irmao direto): sections emite slug<TAB>reviewsSection" {
  run python3 "$CHECK_SIB" review-lane sections
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -q "^gemini	Gemini$"
  printf '%s\n' "$output" | grep -q "^llama_cpp	llama.cpp$"
}

@test "review-lane (irmao direto): --selected CSV filtra as lanes" {
  run python3 "$CHECK_SIB" review-lane flags --selected claude,codex
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | wc -l | tr -d ' ')" -eq 2 ]
}

@test "review-lane (irmao direto): subcommand invalido e usage exit 1" {
  run python3 "$CHECK_SIB" review-lane bogus
  [ "$status" -eq 1 ]
}

# --- o dedup de drift, que so existia como NameError (DEBT-01) -------------
#
# verify codebase-drift junta as entradas do diff no mapa `seen`, e quando o
# MESMO path chega duas vezes consulta DRIFT_PRIORITY para decidir qual
# categoria fica. O simbolo mora em cairn_gsd_fact e nao estava na lista de
# import do irmao de checagem: a linha era NameError em runtime, nao
# KeyError. Nunca reprovou porque nenhum fixture entregava path repetido.
#
# Este teste entrega. O stub de git emite o MESMO destino em duas entradas
# (um A e um R100) — a forma que o parser aceita e que a linha existe para
# tratar — e com o import ausente o handler morre em NameError antes de
# imprimir envelope. Com ele, dedup'a para um elemento.
@test "verify codebase-drift (irmao direto): path repetido no diff dedup'a em vez de NameError" {
  make_tmp_repo
  mkdir -p .planning/codebase
  printf '# Codebase Structure\n\n- `src/lib/` — helpers\n' \
    > .planning/codebase/STRUCTURE.md
  local bindir="$BATS_TEST_TMPDIR/dup-diff-bin"
  mkdir -p "$bindir"
  # Sem last_mapped_commit no STRUCTURE.md o handler diffa contra a empty
  # tree e nunca chama cat-file, entao dois subcomandos bastam.
  cat > "$bindir/git" <<'STUB'
#!/bin/sh
case "$1" in
  rev-parse) echo 1111111111111111111111111111111111111111 ;;
  diff) printf 'A\tmigrations/0001_init.sql\n'
        printf 'R100\tdb/old.sql\tmigrations/0001_init.sql\n' ;;
  *) exit 0 ;;
esac
STUB
  chmod +x "$bindir/git"
  run env PATH="$bindir:$PATH" python3 "$CHECK_SIB" verify codebase-drift
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.elements | length' '1'
  assert_json_eq "$output" '.elements[0].category' 'migration'
  assert_json_eq "$output" '.elements[0].path' 'migrations/0001_init.sql'
}

@test "fantasmas da fase 31 respondem falha nomeada, nunca resposta inventada" {
  # phase.list-artifacts, plan.task-structure e is existem no contrato mas
  # nao no binario da tag (descoberta da fase 31). Desde os planos 34-03/05
  # os tres respondem o CAMINHO DE ERRO do contrato (exit 1, mensagem
  # nomeando o fantasma) — nunca envelope inventado.
  make_tmp_repo
  run "$GSD" query phase.list-artifacts
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "Unknown phase subcommand"
  printf '%s' "$output" | grep -qF "fantasma"
  run "$GSD" query plan.task-structure
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "Unknown command: plan"
  printf '%s' "$output" | grep -qF "fantasma"
  run "$GSD" is
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "Unknown command: is"
}

@test "cobertura cruzada (corpus real, skip-gated): contracts.json .verbs bate com o inventario vivo" {
  local real_cache="$CAIRN_REPO_ROOT/.cairn/cache/gsd-core-v1.10.0"
  [ -d "$real_cache" ] || \
    skip "cache do clone ausente — rode cairn-inventory.sh uma vez com rede"
  run "$INVENTORY" --cache-dir "$real_cache" --json
  [ "$status" -eq 0 ]
  local inv_verbs agg_verbs d
  inv_verbs="$(printf '%s' "$output" | jq -r '.verbs | keys[]' | sort)"
  agg_verbs="$(jq -r '.verbs | keys[]' "$CONTRACTS_JSON" | sort)"
  d="$(comm -23 <(printf '%s\n' "$inv_verbs") <(printf '%s\n' "$agg_verbs"))"
  if [ -n "$d" ]; then
    printf 'verbos do inventario vivo FORA de contracts.json:\n%s\n' "$d" >&2
    return 1
  fi
  # A extensao declarada (universe.references_extension) sai da comparacao:
  # sao os verbos chamados sob gsd-core/references/, escopo que o inventario
  # nao varre. Lista datada no dado, nunca excecao anonima aqui — e
  # tests/gsd-contracts.bats prova que cada um tem sitio real. (fase 38, D-03)
  local declared
  declared="$(jq -r '.universe.references_extension.verbs[]? // empty' \
    "$CONTRACTS_JSON" | sort)"
  agg_verbs="$(comm -23 <(printf '%s\n' "$agg_verbs") \
    <(printf '%s\n' "$declared"))"
  d="$(comm -13 <(printf '%s\n' "$inv_verbs") <(printf '%s\n' "$agg_verbs"))"
  if [ -n "$d" ]; then
    printf 'verbos de contracts.json AUSENTES do inventario vivo:\n%s\n' "$d" >&2
    return 1
  fi
}

# --- a familia config completa (Task 2) -------------------------------------

# Fixture do cenario schema-default + seam apontando o manifest fixture
# COMMITADO — chamadas diretas de config-set/get offline-deterministicas.
setup_config_repo() {
  build_scenario_fixture "config-get-schema-default"
  GSD_SCENARIO_MANIFEST="$GOLDENS_DIR/config-defaults.fixture.json"
}

@test "config-set grava e o config-get subsequente devolve o valor (roundtrip)" {
  setup_config_repo
  gsd_in_fixture query config-set workflow.research false --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "workflow.research=false" ]
  gsd_in_fixture query config-get workflow.research --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "false" ]
}

@test "config-set null REMOVE a chave do arquivo, nunca persiste null" {
  setup_config_repo
  gsd_in_fixture query config-set workflow.research false --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq '.workflow | has("research")' \
    "$GSD_FIXTURE/.planning/config.json")" = "true" ]
  gsd_in_fixture query config-set workflow.research null --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "workflow.research unset" ]
  [ "$(jq '.workflow | has("research")' \
    "$GSD_FIXTURE/.planning/config.json")" = "false" ]
}

@test "config-set com valor rejeitado deixa o arquivo byte-identico (sha256)" {
  setup_config_repo
  gsd_in_fixture query config-set context_window 100000 --raw
  [ "$GSD_STATUS" -eq 0 ]
  local before after
  before="$(shasum -a 256 "$GSD_FIXTURE/.planning/config.json")"
  gsd_in_fixture query config-set context_window abc --raw
  [ "$GSD_STATUS" -eq 1 ]
  after="$(shasum -a 256 "$GSD_FIXTURE/.planning/config.json")"
  [ "${before%% *}" = "${after%% *}" ]
}

@test "config-set repetido com o mesmo valor e idempotente (sha256 identico)" {
  setup_config_repo
  gsd_in_fixture query config-set workflow.research false --raw
  [ "$GSD_STATUS" -eq 0 ]
  local first second
  first="$(shasum -a 256 "$GSD_FIXTURE/.planning/config.json")"
  gsd_in_fixture query config-set workflow.research false --raw
  [ "$GSD_STATUS" -eq 0 ]
  second="$(shasum -a 256 "$GSD_FIXTURE/.planning/config.json")"
  [ "${first%% *}" = "${second%% *}" ]
}

@test "config-set com chave fora do dominio morre exit 1 nomeando CONFIG_INVALID_KEY" {
  setup_config_repo
  gsd_in_fixture query config-set chave.totalmente.invalida x --raw
  [ "$GSD_STATUS" -eq 1 ]
  grep -qF "CONFIG_INVALID_KEY" "$GSD_STDERR"
}

@test "cadeia do manifest: o seam de env VENCE o clone em cache (precedencia)" {
  # a mesma posicao da cadeia do caminho (a): o override responde mesmo com
  # o cache real presente — provado com um valor que so o override carrega.
  build_scenario_fixture "config-get-schema-default"
  local override="$BATS_TEST_TMPDIR/override-manifest.json"
  printf '{"context_window": 111}\n' > "$override"
  GSD_SCENARIO_MANIFEST="$override"
  gsd_in_fixture query config-get context_window --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "111" ]
}

@test "cadeia do manifest: o passo (c) morre nomeado pedindo cache/rede" {
  build_scenario_fixture "config-get-schema-default"
  GSD_SCENARIO_MANIFEST="$BATS_TEST_TMPDIR/nao-existe.manifest.json"
  # config-set EXIGE o dominio de chaves — a cadeia quebrada morre nomeada
  gsd_in_fixture query config-set workflow.research false --raw
  [ "$GSD_STATUS" -eq 1 ]
  grep -qF "manifest de defaults indispon" "$GSD_STDERR"
  grep -qF "cairn-inventory.sh" "$GSD_STDERR"
}

@test "cadeia do manifest (b): o clone em cache verificado responde o schema default" {
  real_cache_manifest || \
    skip "cache do clone ausente — rode cairn-inventory.sh uma vez com rede"
  build_scenario_fixture "config-get-schema-default"
  GSD_SCENARIO_MANIFEST=""
  gsd_in_fixture query config-get context_window --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "200000" ]
}

@test "divergences.json: a tabela da fase existe, com schema e a divergencia workstream" {
  local d="$GOLDENS_DIR/divergences.json"
  [ -f "$d" ]
  jq -e '.schema_version == 1 and (.divergences | type == "array")' "$d"
  jq -e '[.divergences[]
    | select((.family | length) == 0 or (.verb | length) == 0
      or (.aspect | length) == 0 or (.upstream | length) == 0
      or (.cairn | length) == 0 or (.reason | length) == 0)]
    | length == 0' "$d"
  jq -e '.divergences[] | select(.aspect | test("workstream"))' "$d" \
    >/dev/null
}

# --- familias commit + skills (plano 02, Task 1) ----------------------------

# Fixture git limpo com .planning/config.json {} — base dos testes diretos
# da familia commit (o cenario commit-committed carrega exatamente isso).
setup_commit_repo() {
  build_scenario_fixture "commit-committed"
  GSD_SCENARIO_MANIFEST=""
}

@test "commit: posicionais multiplos entre o verbo e a flag viram UMA mensagem unida" {
  setup_commit_repo
  gsd_in_fixture query commit "feat: primeira" "e segunda parte" --raw
  [ "$GSD_STATUS" -eq 0 ]
  # --raw no sucesso imprime o hash cru (semantica medida do binario)
  grep -qE '^[0-9a-f]{7,40}$' "$GSD_STDOUT"
  [ "$(git -C "$GSD_FIXTURE" log -1 --format='%s')" = "feat: primeira e segunda parte" ]
}

@test "commit: staging_failed com index revertido quando o git add falha" {
  setup_commit_repo
  printf 'fora do repo\n' > "$GSD_FIXTURE/../fora-do-repo.txt"
  gsd_in_fixture query commit "docs: vai falhar" --files ../fora-do-repo.txt
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.reason' "$GSD_STDOUT")" = "staging_failed" ]
  [ "$(jq -r '.committed' "$GSD_STDOUT")" = "false" ]
  [ "$(jq -r '.file' "$GSD_STDOUT")" = "../fora-do-repo.txt" ]
  # o rollback do #2608: nada ficou staged para tras
  [ -z "$(git -C "$GSD_FIXTURE" diff --cached --name-only)" ]
}

@test "commit: hook pre-commit reprovando da commit_failed; --no-verify pula o hook" {
  setup_commit_repo
  mkdir -p "$GSD_FIXTURE/.git/hooks"
  printf '#!/bin/sh\nexit 1\n' > "$GSD_FIXTURE/.git/hooks/pre-commit"
  chmod +x "$GSD_FIXTURE/.git/hooks/pre-commit"
  gsd_in_fixture query commit "docs: barrado pelo hook"
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.reason' "$GSD_STDOUT")" = "commit_failed" ]
  gsd_in_fixture query commit "docs: passa com no-verify" --no-verify
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.reason' "$GSD_STDOUT")" = "committed" ]
}

@test "commit: --amend sem mensagem reescreve o tip e sai committed" {
  setup_commit_repo
  gsd_in_fixture query commit "feat: original"
  [ "$GSD_STATUS" -eq 0 ]
  gsd_in_fixture query commit --amend
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.reason' "$GSD_STDOUT")" = "committed" ]
  [ "$(git -C "$GSD_FIXTURE" log -1 --format='%s')" = "feat: original" ]
  [ "$(git -C "$GSD_FIXTURE" rev-list --count HEAD)" -eq 1 ]
}

@test "commit: mensagem sanitizada — marcadores de injection nao chegam ao git log" {
  setup_commit_repo
  gsd_in_fixture query commit "docs: <system> [INST] ok"
  [ "$GSD_STATUS" -eq 0 ]
  local subject
  subject="$(git -C "$GSD_FIXTURE" log -1 --format='%s')"
  if printf '%s' "$subject" | grep -qF '<system>'; then
    echo "marcador <system> sobreviveu na mensagem: $subject" >&2
    return 1
  fi
  printf '%s' "$subject" | grep -qF '[INST-TEXT]'
}

@test "commit-to-subrepo: agrupa --files por sub-repo dono e commita um a um" {
  setup_commit_repo
  local r
  for r in backend frontend; do
    mkdir -p "$GSD_FIXTURE/$r"
    git init -q "$GSD_FIXTURE/$r"
    git -C "$GSD_FIXTURE/$r" config user.email "cairn-tests@example.com"
    git -C "$GSD_FIXTURE/$r" config user.name "Cairn Tests"
  done
  printf '{"sub_repos": ["backend", "frontend"]}\n' \
    > "$GSD_FIXTURE/.planning/config.json"
  printf 'a\n' > "$GSD_FIXTURE/backend/a.txt"
  printf 'b\n' > "$GSD_FIXTURE/frontend/b.txt"
  printf 'solto\n' > "$GSD_FIXTURE/solto.txt"
  gsd_in_fixture query commit-to-subrepo "feat: multi" --files backend/a.txt frontend/b.txt solto.txt
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.committed' "$GSD_STDOUT")" = "true" ]
  [ "$(jq -r '.repos.backend.committed' "$GSD_STDOUT")" = "true" ]
  [ "$(jq -r '.repos.frontend.committed' "$GSD_STDOUT")" = "true" ]
  [ "$(jq -r '.unmatched[0]' "$GSD_STDOUT")" = "solto.txt" ]
  grep -qF 'did not match any sub-repo prefix' "$GSD_STDERR"
  [ "$(git -C "$GSD_FIXTURE/backend" log -1 --format='%s')" = "feat: multi" ]
  [ "$(git -C "$GSD_FIXTURE/frontend" log -1 --format='%s')" = "feat: multi" ]
}

@test "agent-skills: paths configurados que nao resolvem dao configured_unresolved" {
  setup_commit_repo
  printf '{"agent_skills": {"gsd-planner": ["skills/nao-existe"]}}\n' \
    > "$GSD_FIXTURE/.planning/config.json"
  gsd_in_fixture query agent-skills gsd-planner --json
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.reason' "$GSD_STDOUT")" = "configured_unresolved" ]
  [ "$(jq -r '.skills_count' "$GSD_STDOUT")" = "1" ]
  [ "$(jq -r '.warnings | length' "$GSD_STDOUT")" = "2" ]
  grep -qF 'Skill not found' "$GSD_STDERR"
}

@test "agent-skills: lista vazia da configured_empty com warning em stderr" {
  setup_commit_repo
  printf '{"agent_skills": {"gsd-planner": []}}\n' \
    > "$GSD_FIXTURE/.planning/config.json"
  gsd_in_fixture query agent-skills gsd-planner --json
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.reason' "$GSD_STDOUT")" = "configured_empty" ]
  [ "$(jq -r '.skills_count' "$GSD_STDOUT")" = "0" ]
  grep -qF 'has no skill paths' "$GSD_STDERR"
}

# --- familias loop-hooks + dispatch/model (plano 02, Task 2) ----------------

@test "loop render-hooks: envelope --raw carrega as 4 chaves do contrato" {
  setup_commit_repo
  gsd_in_fixture loop render-hooks plan:post --raw
  [ "$GSD_STATUS" -eq 0 ]
  jq -e 'has("point") and has("activeHooks") and has("rendered")
    and has("warnings")' "$GSD_STDOUT" >/dev/null
  [ "$(jq -r '.point' "$GSD_STDOUT")" = "plan:post" ]
}

@test "loop render-hooks: a tabela nativa nasce do capability.json do cairn" {
  setup_commit_repo
  # cairn.enabled default true no capability.json -> contribution ativa
  gsd_in_fixture loop render-hooks plan:post --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.activeHooks[0].capId' "$GSD_STDOUT")" = "cairn" ]
  [ "$(jq -r '.activeHooks[0].kind' "$GSD_STDOUT")" = "contribution" ]
  # cairn.enabled=false desliga tudo — envelope segue com as 4 chaves
  printf '{"cairn": {"enabled": false}}\n' > "$GSD_FIXTURE/.planning/config.json"
  gsd_in_fixture loop render-hooks plan:post --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.activeHooks | length' "$GSD_STDOUT")" = "0" ]
  [ "$(jq -r '.rendered' "$GSD_STDOUT")" = "_No active hooks at plan:post._" ]
}

@test "loop render-hooks: --active-cap imprime exatamente true|false com newline" {
  setup_commit_repo
  gsd_in_fixture loop render-hooks plan:post --active-cap cairn
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "true" ]
  gsd_in_fixture loop render-hooks ship:pre --active-cap cap-inventada
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "false" ]
  # newline final presente (modo scanner, captura $(...) limpa)
  [ "$(tail -c1 "$GSD_STDOUT" | od -An -c | tr -d ' ')" = "\n" ]
}

@test "loop render-hooks: flag sem valor morre exit 1 com a mensagem do upstream" {
  setup_commit_repo
  gsd_in_fixture loop render-hooks plan:post --active-cap
  [ "$GSD_STATUS" -eq 1 ]
  grep -qF "Missing value for --active-cap" "$GSD_STDERR"
  gsd_in_fixture loop render-hooks plan:post --config-dir
  [ "$GSD_STATUS" -eq 1 ]
  grep -qF "Missing value for --config-dir" "$GSD_STDERR"
}

@test "dispatch-isolation: grava o sentinel em toda invocacao e ecoa o modo" {
  setup_commit_repo
  gsd_in_fixture query dispatch-isolation --raw --phase 33 --plan 02
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "harness-worktree" ]
  [ -f "$GSD_FIXTURE/.gsd/dispatch-isolation-sentinel.json" ]
  [ "$(jq -r '.isolation' "$GSD_FIXTURE/.gsd/dispatch-isolation-sentinel.json")" = "harness-worktree" ]
  [ "$(jq -r '.harness_flag' "$GSD_FIXTURE/.gsd/dispatch-isolation-sentinel.json")" = 'isolation="worktree"' ]
  [ "$(jq -r '.phase' "$GSD_FIXTURE/.gsd/dispatch-isolation-sentinel.json")" = "33" ]
}

@test "dispatch-isolation: falha de escrita do sentinel NUNCA falha o verbo" {
  setup_commit_repo
  mkdir -p "$GSD_FIXTURE/.gsd"
  chmod 555 "$GSD_FIXTURE/.gsd"
  gsd_in_fixture query dispatch-isolation --raw
  chmod 755 "$GSD_FIXTURE/.gsd"
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "harness-worktree" ]
}

@test "dispatch-isolation: fail-closed — runtime desconhecido resolve none" {
  setup_commit_repo
  local out
  out="$(cd "$GSD_FIXTURE" && GSD_RUNTIME=runtime-inventado "$GSD" query dispatch-isolation --raw)"
  [ "$out" = "none" ]
}

@test "dispatch-isolation: --force-isolation fora do vocabulario e IGNORADO; none limpa o flag" {
  setup_commit_repo
  gsd_in_fixture query dispatch-isolation --raw --force-isolation modo-inventado
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "harness-worktree" ]
  gsd_in_fixture query dispatch-isolation --json --force-isolation none
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.isolation' "$GSD_STDOUT")" = "none" ]
  [ "$(jq -r '.harnessFlag' "$GSD_STDOUT")" = "null" ]
  [ "$(jq -r '.harness_flag' "$GSD_FIXTURE/.gsd/dispatch-isolation-sentinel.json")" = "null" ]
}

@test "dispatch-should-flatten: true|false exato; erro forcado imprime true" {
  setup_commit_repo
  gsd_in_fixture query dispatch-should-flatten --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "true" ]
  # config corrompida degrada defensivamente — segue exit 0 e true
  printf 'nao-e-json{' > "$GSD_FIXTURE/.planning/config.json"
  gsd_in_fixture query dispatch-should-flatten --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "true" ]
  # runtime desconhecido: dispatch ausente -> fail-closed true
  local out
  out="$(cd "$GSD_FIXTURE" && GSD_RUNTIME=runtime-inventado "$GSD" query dispatch-should-flatten --raw)"
  [ "$out" = "true" ]
}

@test "resolve-model: shape do envelope, unknown_agent e --pick model" {
  setup_commit_repo
  gsd_in_fixture query resolve-model gsd-planner
  [ "$GSD_STATUS" -eq 0 ]
  jq -e 'has("model") and has("profile") and has("effort")
    and (has("unknown_agent") | not)' "$GSD_STDOUT" >/dev/null
  gsd_in_fixture query resolve-model agente-inventado
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.unknown_agent' "$GSD_STDOUT")" = "true" ]
  gsd_in_fixture query resolve-model gsd-planner --pick model
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "opus" ]
  gsd_in_fixture query resolve-model
  [ "$GSD_STATUS" -eq 1 ]
  grep -qF "agent-type required" "$GSD_STDERR"
}

@test "resolve-model: model_profile do config do escopo muda o tier resolvido" {
  setup_commit_repo
  printf '{"model_profile": "quality"}\n' > "$GSD_FIXTURE/.planning/config.json"
  gsd_in_fixture query resolve-model gsd-verifier --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "sonnet" ]
  printf '{"model_profile": "budget"}\n' > "$GSD_FIXTURE/.planning/config.json"
  gsd_in_fixture query resolve-model gsd-verifier --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "haiku" ]
}

@test "resolve-dispatch-type: identidade em host unico; sem --requested vira coder" {
  setup_commit_repo
  gsd_in_fixture query resolve-dispatch-type --requested gsd-verifier --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "gsd-verifier" ]
  gsd_in_fixture query resolve-dispatch-type --raw
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "coder" ]
  # fail-closed observavel: runtime desconhecido segue ecoando o requested
  local out
  out="$(cd "$GSD_FIXTURE" && GSD_RUNTIME=runtime-inventado "$GSD" query resolve-dispatch-type --requested gsd-executor --raw)"
  [ "$out" = "gsd-executor" ]
}

# --- familia estado: o portador bd (plano 34-01, Task 2) --------------------

@test "estado: dois portadores gsd-state dao falha nomeada de ambiguidade (aresta adjacency)" {
  build_scenario_fixture "state-load-fato-ausente"
  bd -C "$GSD_FIXTURE" create "portador A" -t chore -l gsd-state --silent >/dev/null
  bd -C "$GSD_FIXTURE" create "portador B" -t chore -l gsd-state --silent >/dev/null
  gsd_in_fixture query state.load
  [ "$GSD_STATUS" -eq 1 ]
  grep -qF "ambíguo" "$GSD_STDERR"
  grep -qF "gsd-state" "$GSD_STDERR"
}

@test "estado: transicao dupla deixa UM label phase_status — o valor antigo nao consulta (aresta ordering)" {
  build_scenario_fixture "state-begin-phase-cria-portador"
  gsd_in_fixture query state.begin-phase 2
  [ "$GSD_STATUS" -eq 0 ]
  local id
  id="$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -r '.[0].id')"
  bd -C "$GSD_FIXTURE" set-state "$id" phase_status=verified --reason "transicao dupla (teste)" >/dev/null
  [ "$(bd -C "$GSD_FIXTURE" list -l phase_status:executing --all --limit 0 --json | jq 'length')" -eq 0 ]
  [ "$(bd -C "$GSD_FIXTURE" list -l phase_status:verified --all --limit 0 --json | jq 'length')" -eq 1 ]
  [ "$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq '[.[0].labels[] | select(startswith("phase_status:"))] | length')" -eq 1 ]
}

@test "estado: fato ausente com STATE.md presente da a MESMA falha nomeada (fonte unica, CORE-04)" {
  build_scenario_fixture "state-load-fato-ausente"
  gsd_in_fixture query state.load
  [ "$GSD_STATUS" -eq 1 ]
  local err_sem_md
  err_sem_md="$(cat "$GSD_STDERR")"
  [ -n "$err_sem_md" ]
  build_scenario_fixture "state-load-md-presente-fato-ausente"
  [ -f "$GSD_FIXTURE/.planning/STATE.md" ]
  gsd_in_fixture query state.load
  [ "$GSD_STATUS" -eq 1 ]
  [ "$(cat "$GSD_STDERR")" = "$err_sem_md" ]
}

@test "estado: campo nao mapeado nao toca o bd — contagem de labels identica (plano 34-02)" {
  build_scenario_fixture "state-update-campo-nao-mapeado"
  local before after
  before="$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -c '.[0].labels | sort')"
  gsd_in_fixture query state.update cor azul
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.updated' "$GSD_STDOUT")" = "false" ]
  after="$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -c '.[0].labels | sort')"
  [ "$before" = "$after" ]
}

@test "estado: record-session projeta session:YYYY-MM-DD consultavel por label (plano 34-02)" {
  build_scenario_fixture "state-record-session"
  gsd_in_fixture query state.record-session --stopped-at "teste de label"
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(bd -C "$GSD_FIXTURE" list -l "session:$(date +%Y-%m-%d)" --all --limit 0 --json | jq 'length')" -eq 1 ]
}

@test "estado: caso canonico current_phase 18 — record-metric atribui ao fato do bd, nunca a prosa obsoleta (CORE-03)" {
  # Replay do incidente: STATE.md diz 'Phase: 18', o portador bd diz
  # phase:34. As DUAS invocações atribuem a 34; leitura de fato não
  # transiciona nada (labels byte-iguais); o verbo não escreve markdown.
  build_scenario_fixture "state-record-metric-caso-18"
  grep -qF "Phase: 18" "$GSD_FIXTURE/.planning/STATE.md"
  local labels_before md_before labels_mid labels_after md_after
  labels_before="$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -c '.[0].labels | sort')"
  md_before="$(shasum -a 256 "$GSD_FIXTURE/.planning/STATE.md")"
  gsd_in_fixture query state.record-metric --phase 18 --plan 18-02 --duration 5min
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.phase' "$GSD_STDOUT")" = "34" ]
  [ "$(jq -r '.plan' "$GSD_STDOUT")" = "34-02" ]
  labels_mid="$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -c '.[0].labels | sort')"
  [ "$labels_before" = "$labels_mid" ]
  gsd_in_fixture query state.record-metric --phase 18 --plan 18-02 --duration 5min
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.phase' "$GSD_STDOUT")" = "34" ]
  labels_after="$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -c '.[0].labels | sort')"
  [ "$labels_before" = "$labels_after" ]
  md_after="$(shasum -a 256 "$GSD_FIXTURE/.planning/STATE.md")"
  [ "${md_before%% *}" = "${md_after%% *}" ]
}

@test "estado: blockers e decisions viram fatos consultaveis por label projetado (CORE-02)" {
  build_scenario_fixture "state-add-blocker"
  gsd_in_fixture query state.add-blocker "X bloqueia Y"
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(bd -C "$GSD_FIXTURE" list -l gsd-blocker --all --limit 0 --json | jq 'length')" -eq 1 ]
  gsd_in_fixture query state.add-decision --phase 34 --summary "decisao Z"
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(bd -C "$GSD_FIXTURE" list -l gsd-decision --all --limit 0 --json | jq 'length')" -eq 1 ]
}

@test "estado: begin-phase deixa trilha de auditoria com ator e motivo (event bead)" {
  build_scenario_fixture "state-begin-phase-cria-portador"
  gsd_in_fixture query state.begin-phase 7
  [ "$GSD_STATUS" -eq 0 ]
  local id
  id="$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -r '.[0].id')"
  run bd -C "$GSD_FIXTURE" show "$id.1" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | jq -e '.[0].created_by == "Cairn Tests"' >/dev/null
  printf '%s' "$output" | jq -e '.[0].description | contains("state.begin-phase")' >/dev/null
}

# --- familia roadmap-phase: transicoes (plano 34-03, Task 2) ----------------

@test "roadmap-phase: phase.complete reentrado e idempotente — labels byte-iguais, sem transicao espuria" {
  build_scenario_fixture "phase-complete"
  gsd_in_fixture query phase.complete 34
  [ "$GSD_STATUS" -eq 0 ]
  # posicao avancou: phase:35 planned (fase 35 existe no ROADMAP do fixture)
  [ "$(bd -C "$GSD_FIXTURE" list -l phase:35 --all --limit 0 --json | jq 'length')" -eq 1 ]
  [ "$(bd -C "$GSD_FIXTURE" list -l phase_status:planned --all --limit 0 --json | jq 'length')" -eq 1 ]
  # checkbox do ROADMAP marcado (documento)
  grep -qE '^\- \[x\] \*\*Phase 34' "$GSD_FIXTURE/.planning/ROADMAP.md"
  local labels_first
  labels_first="$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -c '.[0].labels | sort')"
  gsd_in_fixture query phase.complete 34
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -c '.[0].labels | sort')" = "$labels_first" ]
}

@test "roadmap-phase: a trilha de auditoria de phase.complete carrega ator e motivo" {
  build_scenario_fixture "phase-complete"
  gsd_in_fixture query phase.complete 34
  [ "$GSD_STATUS" -eq 0 ]
  local id
  id="$(bd -C "$GSD_FIXTURE" list -l gsd-state --all --limit 0 --json | jq -r '.[0].id')"
  # eventos do portador: algum carrega o motivo com o nome do verbo
  run bd -C "$GSD_FIXTURE" show "$id" --json
  [ "$status" -eq 0 ]
  local found=0 n
  for n in 3 4 5; do
    if bd -C "$GSD_FIXTURE" show "$id.$n" --json 2>/dev/null | jq -e '.[0].description | contains("phase.complete")' >/dev/null 2>&1; then
      found=1
    fi
  done
  [ "$found" -eq 1 ]
}

@test "roadmap-phase: annotate-dependencies e idempotente na segunda invocacao" {
  build_scenario_fixture "roadmap-annotate-dependencies"
  gsd_in_fixture query roadmap.annotate-dependencies 34
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.updated' "$GSD_STDOUT")" = "true" ]
  grep -qF "Wave 2" "$GSD_FIXTURE/.planning/ROADMAP.md"
  gsd_in_fixture query roadmap.annotate-dependencies 34
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.updated' "$GSD_STDOUT")" = "false" ]
}

# --- familia worktree (plano 34-04, Task 1) ---------------------------------

@test "worktree.create: branch pre-existente falha com o ramo do contrato e NADA criado pela metade" {
  build_scenario_fixture "worktree-create"
  git -C "$GSD_FIXTURE" branch agent-a1
  gsd_in_fixture query worktree.create --manifest wave.json --agent-id a1 --path wt/a1 --branch agent-a1 --base HEAD --root .
  [ "$GSD_STATUS" -eq 1 ]
  [ "$(jq -r '.ok' "$GSD_STDOUT")" = "false" ]
  jq -e '.reason | test("git")' "$GSD_STDOUT" >/dev/null
  # sem residuo: nenhuma worktree linkada, manifest intocado
  [ "$(git -C "$GSD_FIXTURE" worktree list --porcelain | grep -c '^worktree ')" -eq 1 ]
  [ "$(jq '.worktrees | length' "$GSD_FIXTURE/wave.json")" -eq 0 ]
}

@test "worktree.create: falha na gravacao do manifest faz rollback da arvore E da branch" {
  build_scenario_fixture "worktree-create"
  mkdir -p "$GSD_FIXTURE/mw"
  printf '{"orchestrator_root": ".", "worktrees": []}\n' > "$GSD_FIXTURE/mw/wave.json"
  chmod 555 "$GSD_FIXTURE/mw"
  gsd_in_fixture query worktree.create --manifest mw/wave.json --agent-id a3 --path wt/a3 --branch agent-a3 --base HEAD --root .
  chmod 755 "$GSD_FIXTURE/mw"
  [ "$GSD_STATUS" -eq 1 ]
  [ "$(jq -r '.reason' "$GSD_STDOUT")" = "manifest_write_failed" ]
  # rollback provado por residuo: nem worktree nem branch sobreviveram
  [ "$(git -C "$GSD_FIXTURE" worktree list --porcelain | grep -c '^worktree ')" -eq 1 ]
  if git -C "$GSD_FIXTURE" show-ref --verify --quiet refs/heads/agent-a3; then
    echo "branch agent-a3 sobreviveu ao rollback" >&2
    return 1
  fi
}

@test "worktree.base-check: sem settings resolve head e nao degrada (default declarado)" {
  build_scenario_fixture "worktree-reap-orphans"
  gsd_in_fixture query worktree.base-check
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.shouldDegrade' "$GSD_STDOUT")" = "false" ]
  [ "$(jq -r '.reason' "$GSD_STDOUT")" = "baseref-head" ]
}

@test "worktree.record-agent: idempotente para o mesmo agente (uma entrada so)" {
  build_scenario_fixture "worktree-record-agent"
  gsd_in_fixture query worktree.record-agent --manifest wave.json --agent-id a2 --path wt/a2 --branch agent-a2 --base abc123
  [ "$GSD_STATUS" -eq 0 ]
  gsd_in_fixture query worktree.record-agent --manifest wave.json --agent-id a2 --path wt/a2 --branch agent-a2 --base abc123
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq '.worktrees | length' "$GSD_FIXTURE/wave.json")" -eq 1 ]
}

# --- familia init: bundles (plano 34-04, Task 2) ----------------------------

@test "init: --pick de chave inexistente imprime undefined (semantica medida)" {
  build_scenario_fixture "init-plan-phase-pick"
  gsd_in_fixture query init.plan-phase 34 --pick chave-inexistente
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(cat "$GSD_STDOUT")" = "undefined" ]
}

@test "init: bundle sem portador propaga a falha nomeada do irmao de estado (CORE-04 por composicao)" {
  build_scenario_fixture "init-execute-phase-fato-ausente"
  gsd_in_fixture query init.execute-phase 34
  [ "$GSD_STATUS" -eq 1 ]
  grep -qF "state.begin-phase" "$GSD_STDERR"
  grep -qF "cairn-gsd-state" "$GSD_STDERR"
}

# A tabela do tipo de `section_manifest` (plano 36-02): id do cenário e o
# valor esperado. `null` é o valor degradado que a camada prompt especifica
# como superset seguro — todos os steps lidos (execute-phase.md:92), e o
# único que upstream produz sem o artefato gerado (src/init.cts:459-470 da
# tag: leitura ausente/malformada degrada para null, nunca para lista).
# `ausente` é o controle negativo do lado oposto: um verbo de init que nunca
# emitiu o campo e continua não emitindo — a correção não espalha a chave.
# O argv de cada linha sai do manifesto, nunca digitado aqui; a liveness do
# teste é a própria tabela.
@test "init: section_manifest e null nos 6 verbos que o emitem, e ausente no setimo" {
  local id want got arg fails=0
  local -a argv
  while read -r id want; do
    [ -n "$id" ] || continue
    build_scenario_fixture "$id"
    argv=()
    while IFS= read -r arg; do argv+=("$arg"); done \
      < <(scenario_spec "$id" | jq -r '.argv[]')
    gsd_in_fixture "${argv[@]}"
    if [ "$GSD_STATUS" -ne 0 ]; then
      echo "$id: init saiu $GSD_STATUS, esperado 0" >&2
      fails=$((fails + 1))
      continue
    fi
    got="$(jq -r 'if has("section_manifest")
      then (if .section_manifest == null then "null"
            else (.section_manifest | tojson) end)
      else "ausente" end' "$GSD_STDOUT")"
    if [ "$got" != "$want" ]; then
      echo "$id: section_manifest esperado $want, veio $got" >&2
      fails=$((fails + 1))
    fi
  done <<'TABELA'
init-autonomous null
init-debug null
init-execute-phase null
init-plan-phase null
init-quick null
init-verify-work null
init-phase-op ausente
TABELA
  [ "$fails" -eq 0 ]
}

# --- misc de planning-docs (plano 34-05, Task 1) ----------------------------

@test "misc: requirements.mark-complete muda SO a linha do id alvo (diff de 1 linha)" {
  build_scenario_fixture "requirements-mark-complete"
  local before="$BATS_TEST_TMPDIR/req-before"
  cp "$GSD_FIXTURE/.planning/REQUIREMENTS.md" "$before"
  gsd_in_fixture query requirements.mark-complete CORE-01
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(diff "$before" "$GSD_FIXTURE/.planning/REQUIREMENTS.md" | grep -c '^<')" -eq 1 ]
  grep -qF -- "- [x] **CORE-01**" "$GSD_FIXTURE/.planning/REQUIREMENTS.md"
  grep -qF -- "- [ ] **CORE-02**" "$GSD_FIXTURE/.planning/REQUIREMENTS.md"
}

@test "misc: research-store put/get fecham o ciclo (hit true, entry integra)" {
  build_scenario_fixture "research-store-miss"
  local key
  key="$(printf 'pergunta' | shasum -a 256 | awk '{print $1}')"
  gsd_in_fixture query research-store put "$key" --content "resposta" --source "doc" --provider "websearch" --confidence "high" --kind "api"
  [ "$GSD_STATUS" -eq 0 ]
  gsd_in_fixture query research-store get "$key"
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(jq -r '.hit' "$GSD_STDOUT")" = "true" ]
  [ "$(jq -r '.entry.content' "$GSD_STDOUT")" = "resposta" ]
}

@test "misc: quick-tasks-append cria fato consultavel por label gsd-quick-task" {
  build_scenario_fixture "quick-tasks-append"
  gsd_in_fixture quick-tasks-append --task "tarefa de teste"
  [ "$GSD_STATUS" -eq 0 ]
  [ "$(bd -C "$GSD_FIXTURE" list -l gsd-quick-task --all --limit 0 --json | jq 'length')" -eq 1 ]
}

# --- o recorder (Task 3) ----------------------------------------------------

RECORDER="$CAIRN_SCRIPTS_DIR/cairn-gsd-record.sh"

# Corpus stub local: um repo git carregando um gsd-tools.cjs de uma linha que
# imprime envelope canned — prova gates, mask e escrita atomica sem rede e
# sem o corpus real. Exporta REC_CACHE, REC_COMMIT, REC_GOLDENS, REC_SCENARIOS.
new_record_corpus_fixture() {
  local base
  base="$(mktemp -d "${BATS_TEST_TMPDIR:-${TMPDIR:-/tmp}}/rec.XXXXXX")"
  REC_CACHE="$base/cache/gsd-core-v1.10.0"
  mkdir -p "$REC_CACHE/gsd-core/bin"
  cat > "$REC_CACHE/gsd-core/bin/gsd-tools.cjs" <<'EOF'
process.stdout.write(JSON.stringify({ok: true, hash: "abc1234"}, null, 2));
EOF
  git init -q "$REC_CACHE"
  git -C "$REC_CACHE" config user.email "cairn-tests@example.com"
  git -C "$REC_CACHE" config user.name "Cairn Tests"
  git -C "$REC_CACHE" add -A
  git -C "$REC_CACHE" commit -qm "stub corpus"
  REC_COMMIT="$(git -C "$REC_CACHE" rev-parse HEAD)"
  REC_GOLDENS="$base/goldens"
  mkdir -p "$REC_GOLDENS"
  REC_SCENARIOS="$base/scenarios.json"
  cat > "$REC_SCENARIOS" <<EOF
{
  "scenarios": [
    {"argv": ["query", "config-get", "x"], "compare": "json",
     "expect_stderr": false,
     "fixture": {"files": {}, "git": true, "planning_config": {}},
     "id": "stub-ok", "mask": {".hash": "^[0-9a-f]{7}\$"},
     "verb": "config-get"},
    {"argv": ["query", "config-get", "x"], "compare": "json",
     "expect_stderr": false,
     "fixture": {"files": {}, "git": true, "planning_config": {}},
     "id": "stub-bad-mask", "mask": {".hash": "^ZZZ\$"},
     "verb": "config-get"}
  ],
  "schema_version": 1,
  "source": {"commit": "$REC_COMMIT", "repo": "stub/corpus", "tag": "v1.10.0"}
}
EOF
}

@test "recorder: grava golden com provenance recorded e mask aplicada (corpus stub)" {
  new_record_corpus_fixture
  run "$RECORDER" --cache-dir "$REC_CACHE" --expect-commit "$REC_COMMIT" --scenarios "$REC_SCENARIOS" --goldens-dir "$REC_GOLDENS" --only stub-ok
  [ "$status" -eq 0 ]
  jq -e '.provenance == "recorded"' "$REC_GOLDENS/stub-ok.golden.json"
  jq -e --arg c "$REC_COMMIT" '.source.commit == $c' "$REC_GOLDENS/stub-ok.golden.json"
  jq -e '.expect.exit_code == 0' "$REC_GOLDENS/stub-ok.golden.json"
  # mask aplicada: o marcador entrou e o valor vivo NAO vazou
  run jq -r '.expect.stdout' "$REC_GOLDENS/stub-ok.golden.json"
  printf '%s' "$output" | grep -qF '<masked>'
  if printf '%s' "$output" | grep -qF 'abc1234'; then
    echo "valor vivo vazou pelo mask" >&2
    return 1
  fi
  # doutrina de determinismo: nenhum timestamp no golden gravado
  if grep -qiE '"(timestamp|recorded_at|generated_at|date)"' "$REC_GOLDENS/stub-ok.golden.json"; then
    echo "golden gravado carrega timestamp" >&2
    return 1
  fi
}

@test "recorder: HEAD divergente morre exit 6 sem gravar nada" {
  new_record_corpus_fixture
  run "$RECORDER" --cache-dir "$REC_CACHE" --expect-commit 0000000000000000000000000000000000000000 --scenarios "$REC_SCENARIOS" --goldens-dir "$REC_GOLDENS"
  [ "$status" -eq 6 ]
  [ -z "$(ls "$REC_GOLDENS")" ]
}

@test "recorder: sem node no PATH morre exit 5" {
  new_record_corpus_fixture
  local bindir="$BATS_TEST_TMPDIR/nodeless-bin"
  mkdir -p "$bindir"
  ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$bindir/python3"
  ln -s "$(command -v git)" "$bindir/git"
  ln -s /bin/bash "$bindir/bash"
  ln -s "$(command -v dirname)" "$bindir/dirname"
  run env PATH="$bindir" "$RECORDER" --cache-dir "$REC_CACHE" --expect-commit "$REC_COMMIT" --scenarios "$REC_SCENARIOS" --goldens-dir "$REC_GOLDENS"
  [ "$status" -eq 5 ]
  [ -z "$(ls "$REC_GOLDENS")" ]
}

@test "recorder: falha injetada no meio aborta sem golden parcial nem temp" {
  new_record_corpus_fixture
  # o manifesto carrega stub-ok e depois stub-bad-mask (regex que nao casa):
  # a gravacao publica o primeiro inteiro e aborta no segundo
  run "$RECORDER" --cache-dir "$REC_CACHE" --expect-commit "$REC_COMMIT" --scenarios "$REC_SCENARIOS" --goldens-dir "$REC_GOLDENS"
  [ "$status" -eq 6 ]
  jq -e '.provenance == "recorded"' "$REC_GOLDENS/stub-ok.golden.json"
  [ ! -f "$REC_GOLDENS/stub-bad-mask.golden.json" ]
  [ -z "$(find "$REC_GOLDENS" -name '*.tmp.*')" ]
}

@test "reproducao (corpus real, skip-gated): o --record re-produz os goldens recorded byte a byte" {
  real_cache_manifest || skip "cache do clone ausente — rode cairn-inventory.sh uma vez com rede"
  command -v node >/dev/null 2>&1 || skip "node ausente do PATH — instale node para reproduzir os goldens"
  [ -f "$CAIRN_REPO_ROOT/.cairn/cache/gsd-core-v1.10.0/gsd-core/bin/lib/cli-exit.cjs" ] || skip "runtime do clone nao buildado — rode cairn-gsd-record.sh uma vez"
  local out="$BATS_TEST_TMPDIR/rerecord"
  mkdir -p "$out"
  run "$RECORDER" --goldens-dir "$out"
  [ "$status" -eq 0 ]
  local g id prov fails=0
  for g in "$GOLDENS_DIR"/*.golden.json; do
    id="$(jq -r '.scenario' "$g")"
    prov="$(jq -r '.provenance' "$g")"
    if [ ! -f "$out/$id.golden.json" ]; then
      # o recorder so pula cenario com divergent_from_real declarado no
      # manifesto (divergencia consciente da casa, fase 35) — ausencia
      # sem declaracao e falha
      if [ "$(jq -r --arg id "$id" '.scenarios[]
          | select(.id == $id) | .divergent_from_real // false' \
          "$SCENARIOS")" != "true" ]; then
        echo "golden nao re-gravado e sem divergencia declarada: $id" >&2
        fails=$((fails + 1))
      fi
      continue
    fi
    if [ "$prov" = "recorded" ]; then
      # expectativa recomputada da casa: byte a byte, nunca digitada
      if ! cmp -s "$g" "$out/$id.golden.json"; then
        echo "golden nao reproduz byte a byte: $id" >&2
        diff "$g" "$out/$id.golden.json" >&2 || true
        fails=$((fails + 1))
      fi
    else
      # derived-from-contract nao promete os bytes do binario real:
      # a gravacao real compara por forma (exit) e o promove a recorded
      if [ "$(jq -r '.expect.exit_code' "$g")" != "$(jq -r '.expect.exit_code' "$out/$id.golden.json")" ]; then
        echo "derived: exit diverge na gravacao real: $id" >&2
        fails=$((fails + 1))
      fi
    fi
  done
  [ "$fails" -eq 0 ]
}

# --- os dois verbos que a fase 38 achou mortos (PAR-02) ---------------------
# Medido em 2026-08-12: as duas chamadas existiam no runtime vendorizado, sob
# gsd-core/references/, e nenhuma resolvia — as duas embrulhadas em `|| true`,
# entao o exit 2 do dispatcher nunca chegava a lugar nenhum. Cobertura por
# bats direto (nao ha golden: o escopo varrido pelo inventario nao os viu).

@test "worktree.set-baseref: grafia pontuada grava head quando o arquivo nao existe" {
  make_tmp_repo
  run "$GSD" query worktree.set-baseref
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.changed' 'true'
  assert_json_eq "$output" '.baseRef' 'head'
  run jq -r '.worktree.baseRef' .claude/settings.local.json
  [ "$output" = "head" ]
}

@test "worktree.set-baseref: reentrado e no-op nomeado, nunca reescrita" {
  make_tmp_repo
  run "$GSD" query worktree.set-baseref
  [ "$status" -eq 0 ]
  local before
  before="$(file_mtime_ns .claude/settings.local.json)"
  run "$GSD" query worktree.set-baseref
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.skipped' 'already-head'
  assert_json_eq "$output" '.changed' 'false'
  [ "$(file_mtime_ns .claude/settings.local.json)" = "$before" ]
}

@test "worktree.set-baseref: baseRef explicito diferente NAO e sobrescrito" {
  make_tmp_repo
  mkdir -p .claude
  printf '{\n  "worktree": {\n    "baseRef": "fresh"\n  }\n}\n' \
    > .claude/settings.local.json
  local sha
  sha="$(shasum -a 256 .claude/settings.local.json | cut -d' ' -f1)"
  run "$GSD" query worktree.set-baseref
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.skipped' 'explicit-other'
  [ "$(shasum -a 256 .claude/settings.local.json | cut -d' ' -f1)" = "$sha" ]
}

@test "worktree.set-baseref: JSON malformado morre nomeado e deixa o arquivo intacto" {
  make_tmp_repo
  mkdir -p .claude
  printf '{ isto nao e json' > .claude/settings.local.json
  local sha
  sha="$(shasum -a 256 .claude/settings.local.json | cut -d' ' -f1)"
  run "$GSD" query worktree.set-baseref
  [ "$status" -eq 1 ]
  [[ "$output" == *"Refusing to modify"* ]]
  [ "$(shasum -a 256 .claude/settings.local.json | cut -d' ' -f1)" = "$sha" ]
}

@test "requirements.revert-phase: desmarca so a linha do ID pedido" {
  make_tmp_repo
  mkdir -p .planning
  printf -- '- [x] **REQ-01**: alfa\n- [x] **REQ-02**: beta\n' \
    > .planning/REQUIREMENTS.md
  run "$GSD" query requirements.revert-phase REQ-01
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.updated' 'true'
  assert_json_eq "$output" '.reverted | join(",")' 'REQ-01'
  run grep -c '^- \[x\]' .planning/REQUIREMENTS.md
  [ "$output" = "1" ]
  run grep -c 'REQ-02' .planning/REQUIREMENTS.md
  [ "$output" = "1" ]
  grep -q '^- \[ \] \*\*REQ-01\*\*' .planning/REQUIREMENTS.md
  grep -q '^- \[x\] \*\*REQ-02\*\*' .planning/REQUIREMENTS.md
}

@test "requirements.revert-phase: CSV particiona revertido, ja pendente e ausente" {
  make_tmp_repo
  mkdir -p .planning
  printf -- '- [x] **REQ-01**: alfa\n- [ ] **REQ-02**: beta\n' \
    > .planning/REQUIREMENTS.md
  run "$GSD" query requirements.revert-phase REQ-01,REQ-02,REQ-99
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.reverted | join(",")' 'REQ-01'
  assert_json_eq "$output" '.already_pending | join(",")' 'REQ-02'
  assert_json_eq "$output" '.not_found | join(",")' 'REQ-99'
  assert_json_eq "$output" '.total' '3'
}

@test "requirements.revert-phase: sem ID morre exit 1; sem arquivo responde reason" {
  make_tmp_repo
  run "$GSD" query requirements.revert-phase
  [ "$status" -eq 1 ]
  mkdir -p .planning
  run "$GSD" query requirements.revert-phase REQ-01
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.updated' 'false'
  assert_json_eq "$output" '.reason' 'REQUIREMENTS.md not found'
}

# --- teto de linhas do binario python (CairnGo-zzgn, decidido na fase 38) ---
#
# O teto D-01 da fase 34 — "nenhum arquivo passa de ~1.5k linhas" — nunca teve
# um teste. Ele vivia como asseracao de plano, o que quer dizer que valia no dia
# em que foi escrito e em nenhum outro. Medido em 2026-08-12: TRES dos seis
# arquivos ja passaram do teto, e o modulo compartilhado cairn_gsd_render.py e o
# caso que a issue nomeia — o excedente do irmao de checagem foi para la, o
# irmao fechou em 1492 e o numero que alguem olhava passou a ser o do arquivo
# errado.
#
# Este teste e o gate que faltava, em duas metades:
#
#   1. PINO POR ARQUIVO, e o pino so DESCE. Nenhum arquivo cresce em silencio,
#      inclusive os que ja estao acima do teto. Crescer exige mover o numero
#      aqui, o que e um ato visivel em review.
#   2. O TETO propriamente dito, com a divida NOMEADA. Os arquivos acima de
#      1500 estao numa lista declarada, cada um com a issue que os rastreia —
#      declarar, nunca improvisar. Mais um arquivo estourando 1500 reprova.
#
# CairnGo-2fyg executou a particao (saida (a) do design): o envelope ficou em
# cairn_gsd_render.py com os 4 simbolos que 2+ irmaos usam, o substrato de
# documento foi para cairn_gsd_parse.py e o de FATO (git, subprocess,
# auditoria) para cairn_gsd_fact.py. O render caiu de 1536 para 91 linhas e
# saiu da lista de excecao; os dois modulos novos entram no gate pelo glob
# cairn_gsd_*.py, sem ninguem precisar lembrar de adiciona-los.
#
# Fase 41 (DEBT-01): o pino do irmao de checagem SOBE de 1491 para 1492. A
# razao e uma so — a lista de import de cairn_gsd_fact ganhou DRIFT_PRIORITY
# e, reflowada em 79 colunas, passou de 5 para 6 linhas. O simbolo estava em
# uso na linha 519 sem estar importado: NameError latente no dedup de
# verify codebase-drift. Uma linha de import para matar um crash e o unico
# crescimento aqui; nenhuma logica nova entrou no arquivo.

@test "teto de linhas: cada arquivo do binario python fica no seu pino, e o pino so desce" {
  local file pin actual over=""
  while read -r pin file; do
    [ -n "$file" ] || continue
    actual="$(wc -l < "$CAIRN_SCRIPTS_DIR/$file" | tr -d ' ')"
    if [ "$actual" -gt "$pin" ]; then
      over="$over$file cresceu: $actual > pino $pin"$'\n'
    fi
  done <<'PINS'
2113 cairn-gsd.py
1560 cairn-gsd-state.py
1365 cairn-gsd-init.py
1492 cairn-gsd-check.py
378 cairn-gsd-record.py
91 cairn_gsd_render.py
656 cairn_gsd_parse.py
837 cairn_gsd_fact.py
PINS
  if [ -n "$over" ]; then
    printf 'arquivos do binario python acima do pino:\n%s' "$over" >&2
    return 1
  fi
}

@test "teto de linhas: so os arquivos declarados passam de 1500, e cada um tem issue" {
  # A lista de excecao E a divida, e ela e fechada: qualquer outro arquivo do
  # binario acima de 1500 reprova aqui, em vez de virar mais uma excecao muda.
  # cairn_gsd_render.py saiu daqui em CairnGo-2fyg, ao ser particionado.
  local declared="cairn-gsd.py cairn-gsd-state.py"
  local path name actual undeclared=""
  for path in "$CAIRN_SCRIPTS_DIR"/cairn-gsd*.py \
              "$CAIRN_SCRIPTS_DIR"/cairn_gsd_*.py; do
    [ -f "$path" ] || continue
    name="$(basename "$path")"
    actual="$(wc -l < "$path" | tr -d ' ')"
    if [ "$actual" -gt 1500 ] && \
       ! printf '%s\n' $declared | grep -qxF "$name"; then
      undeclared="$undeclared$name: $actual linhas, acima do teto e sem issue"$'\n'
    fi
  done
  if [ -n "$undeclared" ]; then
    printf 'arquivos acima do teto D-01 sem divida declarada:\n%s' \
      "$undeclared" >&2
    return 1
  fi
}
