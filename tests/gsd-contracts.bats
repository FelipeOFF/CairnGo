#!/usr/bin/env bats
# gsd-contracts.bats — valida o schema e a consistência de cairn/gsd/contracts/:
# a tabela versionada do REM-03 (contratos de entrada/saída por verbo do
# gsd-tools.cjs da tag v1.10.0), na forma que D-02 travou — JSON, um arquivo
# por família mais um agregado, schema único validado por jq.
#
# A suíte valida os JSONs COMMITADOS: zero rede, zero fixtures. Os testes
# iteram cairn/gsd/contracts/*.json em glob, então os arquivos de família que
# os planos 03-04 criarem entram na validação sem tocar nesta suíte.
#
# Assertion style note (same as capability.bats / cairn-map.bats): a failing
# `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this bash, so
# substring checks use grep -qF over "$output" written through printf, and
# per-file loops accumulate failures and return 1 explicitly.

load 'helpers'

CONTRACTS_DIR="$CAIRN_REPO_ROOT/cairn/gsd/contracts"
AGG="$CONTRACTS_DIR/contracts.json"

# As 11 famílias do research §4 — o contrato de layout que o agregado declara.
EXPECTED_FAMILIES="estado config commit skills init loop-hooks worktree checagem roadmap-phase dispatch-model misc"

# Lista os arquivos de família presentes em disco (todos os *.json menos o agregado).
family_files() {
  local f
  for f in "$CONTRACTS_DIR"/*.json; do
    [ "$f" = "$AGG" ] && continue
    printf '%s\n' "$f"
  done
}

# ─── JSON válido e newline final ─────────────────────────────────────────────

@test "every file in cairn/gsd/contracts/ is valid JSON ending in a newline" {
  [ -d "$CONTRACTS_DIR" ]
  [ -f "$AGG" ]
  local f fails=0
  for f in "$CONTRACTS_DIR"/*.json; do
    if ! jq empty "$f" 2>/dev/null; then
      echo "invalid JSON: $f" >&2
      fails=$((fails + 1))
    fi
    if [ "$(tail -c1 "$f" | od -An -c | tr -d ' ')" != '\n' ]; then
      echo "missing trailing newline: $f" >&2
      fails=$((fails + 1))
    fi
  done
  [ "$fails" -eq 0 ]
}

# ─── Schema dos arquivos de família ──────────────────────────────────────────

@test "every family file has schema_version 1, family, source{repo,tag,commit} and non-empty verbs" {
  [ -f "$AGG" ]
  local f fails=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if ! jq -e '
        .schema_version == 1
        and (.family | type == "string" and length > 0)
        and (.source.repo | type == "string" and length > 0)
        and (.source.tag | type == "string" and length > 0)
        and (.source.commit | type == "string" and length > 0)
        and (.verbs | type == "array" and length > 0)
      ' "$f" >/dev/null; then
      echo "family envelope invalid: $f" >&2
      fails=$((fails + 1))
    fi
  done < <(family_files)
  [ "$fails" -eq 0 ]
}

@test "every verb entry carries verb, invocation, input.argv/flags, output.kind/exit_codes and a non-empty source_ref" {
  [ -f "$AGG" ]
  local f fails=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    # Entradas que violam o schema mínimo por verbo — a lista deve sair vazia.
    run jq -r '
      [ .verbs[]
        | select(
            ((.verb // "") == "")
            or ((.invocation // "") == "")
            or ((.input.argv | type) != "array")
            or ((.input.flags | type) != "array")
            or (((.output.kind // "") | IN("json", "text", "exit-only")) | not)
            or ((.output.exit_codes | type) != "object")
            or (((.output.exit_codes // {}) | length) == 0)
            or ((.source_ref.path // "") == "")
            or ((.source_ref.lines // "") == "")
          )
        | .verb // "(missing verb)"
      ] | .[]
    ' "$f"
    if [ "$status" -ne 0 ] || [ -n "$output" ]; then
      printf 'schema violations in %s:\n%s\n' "$f" "$output" >&2
      fails=$((fails + 1))
    fi
  done < <(family_files)
  [ "$fails" -eq 0 ]
}

@test "every verb entry has spellings[] containing the verb itself and call_sites counts" {
  [ -f "$AGG" ]
  local f fails=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    run jq -r '
      [ .verbs[]
        | select(
            ((.spellings | type) != "array")
            or ((.spellings | length) == 0)
            or ((.call_sites.workflows8 | type) != "number")
            or ((.call_sites.agents | type) != "number")
          )
        | .verb // "(missing verb)"
      ] | .[]
    ' "$f"
    if [ "$status" -ne 0 ] || [ -n "$output" ]; then
      printf 'spellings/call_sites violations in %s:\n%s\n' "$f" "$output" >&2
      fails=$((fails + 1))
    fi
  done < <(family_files)
  [ "$fails" -eq 0 ]
}

# ─── Verbos obrigatórios deste plano (âncoras do REM-03) ─────────────────────

@test "config.json contracts config-get and config-set, the most-called family" {
  local f="$CONTRACTS_DIR/config.json"
  [ -f "$f" ]
  jq -e '.verbs[] | select(.verb == "config-get")' "$f" >/dev/null
  jq -e '.verbs[] | select(.verb == "config-set")' "$f" >/dev/null
}

@test "loop-hooks.json registers the render-hooks subcommand of loop" {
  local f="$CONTRACTS_DIR/loop-hooks.json"
  [ -f "$f" ]
  run jq -r '.verbs[] | select(.verb == "loop") | (.invocation + " " + (.notes // ""))' "$f"
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -qF "render-hooks"
}

@test "no verb entry in any family file is missing its source_ref (REM-03: extraido da implementacao)" {
  [ -f "$AGG" ]
  local f fails=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if ! jq -e '[.verbs[] | select((.source_ref.path // "") == "" or (.source_ref.lines // "") == "")] | length == 0' "$f" >/dev/null; then
      echo "entries without source_ref in: $f" >&2
      fails=$((fails + 1))
    fi
  done < <(family_files)
  [ "$fails" -eq 0 ]
}

# ─── O agregado ──────────────────────────────────────────────────────────────

@test "contracts.json declares the 11 families of research §4 with one file each" {
  [ -f "$AGG" ]
  jq -e '.schema_version == 1' "$AGG"
  jq -e '.families | length == 11' "$AGG"
  local fam
  for fam in $EXPECTED_FAMILIES; do
    if ! jq -e --arg fam "$fam" '.families | has($fam)' "$AGG" >/dev/null; then
      echo "family missing from aggregate map: $fam" >&2
      return 1
    fi
  done
  # todo valor do mapa é um nome de arquivo .json não vazio
  jq -e '[.families[] | select((type != "string") or (test("^[a-z-]+\\.json$") | not))] | length == 0' "$AGG"
}

@test "contracts.json carries source identity, universe.derived_from and a written assignment_rule" {
  [ -f "$AGG" ]
  jq -e '.source.repo == "open-gsd/gsd-core"' "$AGG"
  jq -e '.source.tag | type == "string" and length > 0' "$AGG"
  jq -e '.source.commit | test("^[0-9a-f]{40}$")' "$AGG"
  jq -e '.universe.derived_from | type == "string" and length > 0' "$AGG"
  jq -e '.assignment_rule | type == "string" and length > 0' "$AGG"
}

@test "family files agree with the aggregate on source identity (repo/tag/commit)" {
  [ -f "$AGG" ]
  local f fails=0 agg_commit agg_tag agg_repo
  agg_repo=$(jq -r '.source.repo' "$AGG")
  agg_tag=$(jq -r '.source.tag' "$AGG")
  agg_commit=$(jq -r '.source.commit' "$AGG")
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if ! jq -e --arg r "$agg_repo" --arg t "$agg_tag" --arg c "$agg_commit" \
        '.source.repo == $r and .source.tag == $t and .source.commit == $c' "$f" >/dev/null; then
      echo "source identity diverges from aggregate: $f" >&2
      fails=$((fails + 1))
    fi
  done < <(family_files)
  [ "$fails" -eq 0 ]
}

# ─── Consistência bidirecional agregado ↔ famílias ───────────────────────────
# Famílias ainda não escritas pelos planos 03-04 não quebram: a consistência é
# checada sobre os arquivos PRESENTES em disco.

@test "aggregate → families: every indexed verb points to a family whose file exists and contains it" {
  [ -f "$AGG" ]
  local fails=0 verb fam file
  while IFS=$'\t' read -r verb fam file; do
    [ -n "$verb" ] || continue
    # a família do verbo tem que existir no mapa e apontar o mesmo arquivo
    if ! jq -e --arg fam "$fam" --arg file "$file" '.families[$fam] == $file' "$AGG" >/dev/null; then
      echo "verb '$verb': family '$fam' / file '$file' disagree with the families map" >&2
      fails=$((fails + 1))
      continue
    fi
    if [ ! -f "$CONTRACTS_DIR/$file" ]; then
      echo "verb '$verb' indexed to $file, which does not exist on disk" >&2
      fails=$((fails + 1))
      continue
    fi
    if ! jq -e --arg v "$verb" '[.verbs[].verb] | index($v)' "$CONTRACTS_DIR/$file" >/dev/null; then
      echo "verb '$verb' indexed to $file, but the file does not contain it" >&2
      fails=$((fails + 1))
    fi
  done < <(jq -r '.verbs | to_entries[] | [.key, .value.family, .value.file] | @tsv' "$AGG")
  [ "$fails" -eq 0 ]
}

@test "aggregate ↔ families: the verb SETS are identical in both directions (empty diff)" {
  [ -f "$AGG" ]
  # Recomputa os dois conjuntos do disco — nada digitado à mão: o índice do
  # agregado de um lado, a união dos verbos de todos os arquivos de família
  # do outro. A diferença tem que ser vazia NOS DOIS sentidos.
  local agg_verbs fam_verbs f
  agg_verbs="$(jq -r '.verbs | keys[]' "$AGG" | sort)"
  fam_verbs="$(
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      jq -r '.verbs[].verb' "$f"
    done < <(family_files) | sort
  )"
  local only_agg only_fam
  only_agg="$(comm -23 <(printf '%s\n' "$agg_verbs") <(printf '%s\n' "$fam_verbs"))"
  only_fam="$(comm -13 <(printf '%s\n' "$agg_verbs") <(printf '%s\n' "$fam_verbs"))"
  if [ -n "$only_agg" ] || [ -n "$only_fam" ]; then
    printf 'index-only verbs:\n%s\nfamily-only verbs:\n%s\n' "$only_agg" "$only_fam" >&2
    return 1
  fi
}

# ─── Cobertura real contra o inventário (skip-gated pelo cache) ──────────────
# O universo é MEDIDO por cairn/scripts/cairn-inventory.sh sobre o cache real
# da tag — a expectativa é recomputada a cada execução, nunca digitada.

INVENTORY="$CAIRN_REPO_ROOT/cairn/scripts/cairn-inventory.sh"

@test "real universe: every inventory verb has a contract — total coverage, no tolerance (REM-03 + REM-04)" {
  local real_cache="$CAIRN_REPO_ROOT/.cairn/cache/gsd-core-v1.10.0"
  [ -d "$real_cache" ] || \
    skip "cache do clone ausente — rode cairn-inventory.sh uma vez com rede"
  run "$INVENTORY" --cache-dir "$real_cache" --json
  [ "$status" -eq 0 ]

  local inv_verbs agg_verbs uncontracted extra
  inv_verbs="$(printf '%s' "$output" | jq -r '.verbs | keys[]' | sort)"
  agg_verbs="$(jq -r '.verbs | keys[]' "$AGG" | sort)"

  # inventário − índice: TEM que ser vazio. A tolerância aos 4 órfãos do
  # plano 04 morreu (o plano 04 os contratou): universo e índice coincidem
  # sem exceção nomeada.
  uncontracted="$(comm -23 <(printf '%s\n' "$inv_verbs") <(printf '%s\n' "$agg_verbs"))"
  if [ -n "$uncontracted" ]; then
    printf 'universe verbs WITHOUT contract:\n%s\n' "$uncontracted" >&2
    return 1
  fi

  # índice − inventário: nenhuma entrada órfã no agregado — todo verbo
  # contratado tem que existir no universo medido, MAIS a extensão declarada.
  #
  # A extensão existe porque o inventário varre workflows8 + agents e NÃO varre
  # gsd-core/references/, que o runtime executa (fase 38, M2). Os verbos que só
  # aparecem lá não podem sair do contrato — sem contrato o dispatcher morre
  # exit 2 e o `|| true` do sítio apaga a morte. Em vez de exceção anônima no
  # teste, a lista mora em universe.references_extension.verbs, datada e com
  # método escrito, e o teste a LÊ do dado. O teste logo abaixo fecha a brecha
  # de alguém escrever qualquer coisa ali.
  local declared
  declared="$(jq -r '.universe.references_extension.verbs[]? // empty' "$AGG" | sort)"
  agg_verbs="$(comm -23 <(printf '%s\n' "$agg_verbs") <(printf '%s\n' "$declared"))"
  extra="$(comm -13 <(printf '%s\n' "$inv_verbs") <(printf '%s\n' "$agg_verbs"))"
  if [ -n "$extra" ]; then
    printf 'aggregate verbs ABSENT from the measured universe:\n%s\n' "$extra" >&2
    return 1
  fi
}

@test "references_extension: todo verbo declarado e de fato chamado sob gsd-core/references/" {
  # A brecha que a tolerância abriria: bastaria escrever um verbo em
  # universe.references_extension para ele deixar de precisar existir no
  # universo medido. Este teste fecha a brecha pelo lado do fato — cada verbo
  # declarado tem que aparecer numa chamada `gsd_run` real sob
  # gsd-core/references/. Declaração sem sítio reprova.
  [ -f "$AGG" ]
  local verbs v
  verbs="$(jq -r '.universe.references_extension.verbs[]? // empty' "$AGG")"
  [ -n "$verbs" ]
  while IFS= read -r v; do
    [ -n "$v" ] || continue
    if ! grep -rqF -- "gsd_run query $v" \
        "$CAIRN_REPO_ROOT/cairn/gsd/gsd-core/references"; then
      printf 'verbo declarado em references_extension sem sitio real: %s\n' \
        "$v" >&2
      return 1
    fi
  done <<< "$verbs"
}

@test "negative control: a forged verb injected into a simulated universe does NOT pass coverage" {
  [ -f "$AGG" ]
  # Mesma comparação do teste de cobertura, contra um universo simulado que é
  # exatamente o índice do agregado MAIS um verbo forjado. Se a comparação
  # engolisse o verbo a mais, a cobertura estaria furada e o teste real não
  # morderia nada.
  local simulated="$BATS_TEST_TMPDIR/forged-universe.json"
  jq '{verbs: (.verbs + {"forged-verb-that-nobody-implemented": {}})}' "$AGG" > "$simulated"

  local inv_verbs agg_verbs uncontracted
  inv_verbs="$(jq -r '.verbs | keys[]' "$simulated" | sort)"
  agg_verbs="$(jq -r '.verbs | keys[]' "$AGG" | sort)"
  uncontracted="$(comm -23 <(printf '%s\n' "$inv_verbs") <(printf '%s\n' "$agg_verbs"))"
  # A diferença NÃO pode ser vazia: o verbo forjado tem que vazar.
  [ -n "$uncontracted" ]
  printf '%s\n' "$uncontracted" | grep -qF "forged-verb-that-nobody-implemented"
}

@test "the tolerance really died: the aggregate carries no verbs_pending_plan_04 and index == universe count" {
  [ -f "$AGG" ]
  jq -e '.universe | has("verbs_pending_plan_04") | not' "$AGG"
  jq -e '.universe.verbs_contracted == .universe.verbs_total' "$AGG"
  jq -e '(.verbs | length) == .universe.verbs_total' "$AGG"
}

@test "families → aggregate: every verb present in a family file is in the aggregate index" {
  [ -f "$AGG" ]
  local f fails=0 fam verb
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    fam=$(jq -r '.family' "$f")
    while IFS= read -r verb; do
      [ -n "$verb" ] || continue
      if ! jq -e --arg v "$verb" --arg fam "$fam" '.verbs[$v].family == $fam' "$AGG" >/dev/null; then
        echo "verb '$verb' present in $(basename "$f") but absent (or misfiled) in the aggregate index" >&2
        fails=$((fails + 1))
      fi
    done < <(jq -r '.verbs[].verb' "$f")
  done < <(family_files)
  [ "$fails" -eq 0 ]
}

# ─── Órfãos do bundle bakeado (REM-04, D-04) ─────────────────────────────────
# Os 4 verbos sem fonte em src/*.cts (research §4/§6 risco 5) entram no MESMO
# schema das demais entradas, com provenance declarando a extração do
# gsd-tools.cjs bakeado e source_ref apontando linhas do bundle DO CLONE.

ORPHAN_PAIRS="run-with-timeout=misc.json user-story.validate=checagem.json dispatch-isolation=dispatch-model.json dispatch-should-flatten=dispatch-model.json"

@test "the 4 bundle-only orphans are contracted in full schema with provenance and bundle source_ref (REM-04, D-04)" {
  local pair verb file fails=0
  for pair in $ORPHAN_PAIRS; do
    verb=${pair%%=*}
    file=${pair##*=}
    if [ ! -f "$CONTRACTS_DIR/$file" ]; then
      echo "family file missing: $file" >&2
      fails=$((fails + 1))
      continue
    fi
    if ! jq -e --arg v "$verb" '
        [ .verbs[]
          | select(.verb == $v)
          | select(
              (.provenance == "extraído do gsd-tools.cjs bakeado")
              and (.source_ref.path == "gsd-core/bin/gsd-tools.cjs")
              and ((.source_ref.lines // "") != "")
            )
        ] | length == 1
      ' "$CONTRACTS_DIR/$file" >/dev/null; then
      echo "orphan '$verb' absent or without provenance/bundle source_ref in $file" >&2
      fails=$((fails + 1))
    fi
  done
  [ "$fails" -eq 0 ]
}

@test "reverse direction 1: no entry carrying provenance points source_ref at src/ (bundle orphans never claim a src source)" {
  [ -f "$AGG" ]
  local f fails=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if ! jq -e '[.verbs[] | select(has("provenance") and ((.source_ref.path // "") | startswith("src/")))] | length == 0' "$f" >/dev/null; then
      echo "entry WITH provenance pointing at src/ in: $f" >&2
      fails=$((fails + 1))
    fi
  done < <(family_files)
  [ "$fails" -eq 0 ]
}

@test "reverse direction 2: no entry without provenance points source_ref at the baked gsd-tools.cjs" {
  [ -f "$AGG" ]
  local f fails=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if ! jq -e '[.verbs[] | select((has("provenance") | not) and (.source_ref.path == "gsd-core/bin/gsd-tools.cjs"))] | length == 0' "$f" >/dev/null; then
      echo "entry WITHOUT provenance pointing at the bundle in: $f" >&2
      fails=$((fails + 1))
    fi
  done < <(family_files)
  [ "$fails" -eq 0 ]
}

@test "the aggregate index carries the 4 orphans, each in its assigned family (REM-04)" {
  [ -f "$AGG" ]
  jq -e '.verbs["run-with-timeout"].family == "misc"' "$AGG"
  jq -e '.verbs["user-story.validate"].family == "checagem"' "$AGG"
  jq -e '.verbs["dispatch-isolation"].family == "dispatch-model"' "$AGG"
  jq -e '.verbs["dispatch-should-flatten"].family == "dispatch-model"' "$AGG"
}

# ─── Measurements datados (REM-05) ───────────────────────────────────────────
# Os dois números da abertura que não reproduziram, fechados com método escrito:
# init re-derivado pelos 9 bundle shapes e o instalador com filtro declarado.

@test "init.json carries the 9 bundle_shapes with consumed fields, composition source_ref and a python estimate each (REM-05)" {
  local f="$CONTRACTS_DIR/init.json"
  [ -f "$f" ]
  jq -e '.bundle_shapes | length == 9' "$f"
  # todo shape tem verbo init.*, campos consumidos, sítios de consumo com
  # arquivo:linha, composição em src/init.cts e estimativa positiva
  jq -e '
    [ .bundle_shapes[]
      | select(
          ((.verb // "") | startswith("init."))
          and ((.consumed_fields | type == "array") and (.consumed_fields | length > 0))
          and ((.consumption_sites | type == "array") and (.consumption_sites | length > 0))
          and ([.consumption_sites[] | select(((.file // "") == "") or ((.line | type) != "number"))] | length == 0)
          and (.source_ref.path == "src/init.cts")
          and ((.source_ref.lines // "") != "")
          and ((.python_estimate_lines | type == "number") and (.python_estimate_lines > 0))
        )
    ] | length == 9
  ' "$f"
  # cada campo consumido existe na shape contratada do verbo correspondente
  jq -e '
    . as $root
    | [ .bundle_shapes[]
        | .verb as $v
        | .consumed_fields[] as $field
        | select([$root.verbs[] | select(.verb == $v) | .output.shape[]] | index($field) | not)
      ] | length == 0
  ' "$f"
}

@test "measurements.init_budget: total = sum of per_shape, with a written method and date (REM-05)" {
  [ -f "$AGG" ]
  jq -e '.measurements.init_budget | (.total_estimated_lines > 0) and (.method | length > 0) and (.per_shape | length > 0) and ((.date // "") != "")' "$AGG"
  # a soma fecha: total == soma dos 9 per_shape, e per_shape espelha os
  # bundle_shapes de init.json (mesmos verbos, mesmos números)
  jq -e '.measurements.init_budget | ([.per_shape[]] | add) == .total_estimated_lines' "$AGG"
  local agg_pairs init_pairs
  agg_pairs="$(jq -r '.measurements.init_budget.per_shape | to_entries[] | "\(.key)=\(.value)"' "$AGG" | sort)"
  init_pairs="$(jq -r '.bundle_shapes[] | "\(.verb)=\(.python_estimate_lines)"' "$CONTRACTS_DIR/init.json" | sort)"
  if [ "$agg_pairs" != "$init_pairs" ]; then
    printf 'per_shape (aggregate) != bundle_shapes (init.json):\n%s\n---\n%s\n' "$agg_pairs" "$init_pairs" >&2
    return 1
  fi
}

@test "measurements.installer_cut: official number with declared filter, exact command and narrow component (REM-05)" {
  [ -f "$AGG" ]
  jq -e '.measurements.installer_cut | (.official_number > 0) and (.filter_patterns | length > 0) and (.command | length > 0) and (.narrow_subset.number > 0) and (.narrow_subset.command | length > 0) and (.narrow_subset.patterns | length > 0) and ((.date // "") != "")' "$AGG"
  # o estreito e componente do amplo: numero menor e padroes contidos
  jq -e '.measurements.installer_cut | .narrow_subset.number < .official_number' "$AGG"
  jq -e '.measurements.installer_cut | (.narrow_subset.patterns - .filter_patterns) | length == 0' "$AGG"
}

@test "real clone: re-running the recorded installer_cut commands reproduces the recorded numbers" {
  local real_cache="$CAIRN_REPO_ROOT/.cairn/cache/gsd-core-v1.10.0"
  [ -d "$real_cache" ] || \
    skip "cache do clone ausente — rode cairn-inventory.sh uma vez com rede"
  local cmd expected measured
  # amplo (oficial)
  cmd="$(jq -r '.measurements.installer_cut.command' "$AGG")"
  expected="$(jq -r '.measurements.installer_cut.official_number' "$AGG")"
  measured="$(cd "$CAIRN_REPO_ROOT" && eval "$cmd" | tr -d '[:space:]')"
  if [ "$measured" != "$expected" ]; then
    printf 'installer_cut official: recorded %s, re-measured %s\n' "$expected" "$measured" >&2
    return 1
  fi
  # estreito (componente)
  cmd="$(jq -r '.measurements.installer_cut.narrow_subset.command' "$AGG")"
  expected="$(jq -r '.measurements.installer_cut.narrow_subset.number' "$AGG")"
  measured="$(cd "$CAIRN_REPO_ROOT" && eval "$cmd" | tr -d '[:space:]')"
  if [ "$measured" != "$expected" ]; then
    printf 'installer_cut narrow: recorded %s, re-measured %s\n' "$expected" "$measured" >&2
    return 1
  fi
}
