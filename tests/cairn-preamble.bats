#!/usr/bin/env bats
# cairn-preamble.bats — a linha de preâmbulo da camada prompt vendorizada.
#
# A fase 36 é a primeira do milestone a ESCREVER sob cairn/gsd/, e a onda zero
# (D-01) troca os 34 blocos de resolução de runtime para apontar o binário
# python do próprio repo. Esta suíte prova duas coisas distintas:
#
#   1. a FORMA funciona RODANDO, em três posições (raiz do repo, subdiretório
#      do repo, fora de qualquer checkout cairn) — substituição textual
#      declarada verde por grep não prova que o workflow fala com o binário;
#   2. o REESCRITOR é cirúrgico: recusa por nome o que não está registrado,
#      é idempotente, e o --check sai 3 com diff quando algo ficou para trás.
#
# Cada guarda vem com seu controle negativo, no molde de
# cairn-vendoring.bats:465-474: a rodada fora do checkout é a metade de
# liveness da resolução, e a recusa por caminho não registrado é a da
# allowlist. Nenhum gate de execução resolve caminho de máquina: a raiz sai
# de $CAIRN_REPO_ROOT do helper.
#
# Estilo de asserção: status pelo valor EXATO, nunca por negação; substring
# por `grep -qF` (um `! cmd` no meio do teste não reprova neste bash).

load 'helpers'

PREAMBLE="$CAIRN_SCRIPTS_DIR/cairn-preamble.sh"
REGISTRY="$CAIRN_REPO_ROOT/cairn/gsd-adaptations.json"

# A forma canônica, sempre extraída da FONTE ÚNICA. Um teste que digitasse a
# linha à mão passaria mesmo com o script errado.
canonical_form() {
  bash "$PREAMBLE" --print-form
}

# Roda a forma num cwd dado, com o ambiente decepado, e devolve o que o
# comando anexado imprimir. O `env -u` importa: sem ele o exit 1 do caso
# "fora do checkout" poderia vir de herança de env, não da resolução.
run_form_in() {
  local dir="$1" form="$2"
  shift 2
  ( cd "$dir" && env -u CLAUDE_PROJECT_DIR -u CAIRN_GSD \
      bash -c "$form"'; '"$*" )
}

# Uma árvore vendorizada de fixture: <tmp>/cairn/gsd/<rel> com um bloco na
# forma antiga, mais o registro forjado que a autoriza.
make_vendor_fixture() {
  local base="$1" rel="$2"
  mkdir -p "$base/cairn/gsd/$(dirname "$rel")"
  cat > "$base/cairn/gsd/$rel" <<'EOF'
# fixture workflow

```bash
_GSD_SHIM_NAME="gsd-tools.cjs"; GSD_TOOLS="x"; gsd_run() { node "$GSD_TOOLS" "$@"; }
gsd_run query init.debug
```

Prosa que nao muda.
EOF
  cat > "$base/cairn/gsd-adaptations.json" <<EOF
{
  "schema_version": 1,
  "adaptations": [
    {"path": "$rel", "phase": "36", "waves": [1], "reason": "fixture"}
  ]
}
EOF
}

# ---------------------------------------------------------------------------
# A forma: uma fonte só, e ela roda
# ---------------------------------------------------------------------------

@test "--print-form emite UMA linha e nao menciona o runtime morto" {
  local form
  form="$(canonical_form)"
  [ -n "$form" ]
  [ "$(printf '%s' "$form" | wc -l | tr -d ' ')" -eq 0 ]
  # A onda zero existe para tirar o runtime node do caminho executado: se a
  # forma nova ainda o nomeasse, ou ainda sugerisse o instalador do pacote
  # que a fase 37 remove, ela mandaria o usuario para um caminho morto.
  refute_form_mentions "$form" 'gsd-tools'
  refute_form_mentions "$form" 'npx'
  refute_form_mentions "$form" 'node '
  printf '%s' "$form" | grep -qF 'cairn/scripts/cairn-gsd.sh'
  printf '%s' "$form" | grep -qF 'gsd_run()'
}

refute_form_mentions() {
  if printf '%s' "$1" | grep -qF -- "$2"; then
    echo "a forma canonica ainda menciona '$2'" >&2
    return 1
  fi
}

@test "a forma resolve o binario do repo a partir da RAIZ do checkout" {
  run run_form_in "$CAIRN_REPO_ROOT" "$(canonical_form)" \
    'gsd_run query init.debug'
  [ "$status" -eq 0 ]
  printf '%s' "$output" | jq -e '.project_root' >/dev/null
}

@test "a forma resolve o binario a partir de um SUBDIRETORIO do checkout" {
  # O elo 3 da cadeia: o toplevel do git, nao o cwd. Sem ele, todo workflow
  # rodado de dentro de um subdiretorio falharia.
  run run_form_in "$CAIRN_REPO_ROOT/cairn" "$(canonical_form)" \
    'gsd_run query init.debug'
  [ "$status" -eq 0 ]
  printf '%s' "$output" | jq -e '.project_root' >/dev/null
}

@test "o elo 2 caindo para o 3: variavel de projeto apontando OUTRO repo" {
  # CLAUDE_PROJECT_DIR aponta um repo git qualquer, sem cairn/scripts. A
  # cadeia nao pode parar ali: cai para o toplevel do cwd e resolve.
  local other="$BATS_TEST_TMPDIR/outro-repo"
  mkdir -p "$other"
  git init -q "$other"
  run env -u CAIRN_GSD CLAUDE_PROJECT_DIR="$other" bash -c \
    "cd '$CAIRN_REPO_ROOT' && $(canonical_form)"'; gsd_run query init.debug'
  [ "$status" -eq 0 ]
  printf '%s' "$output" | jq -e '.project_root' >/dev/null
}

@test "controle negativo: fora de qualquer checkout cairn, exit 1 NOMEADO" {
  # A metade de liveness da resolucao. Nunca exit 0 silencioso, nunca
  # fallback markdown: a falha nomeia o ultimo caminho tentado e o comando
  # que cria o fato.
  local alheio="$BATS_TEST_TMPDIR/nao-e-cairn"
  mkdir -p "$alheio"
  git init -q "$alheio"
  run run_form_in "$alheio" "$(canonical_form)" 'gsd_run query init.debug'
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF 'cairn-gsd.sh'
  printf '%s' "$output" | grep -qF 'CAIRN_GSD='
}

@test "o escape deliberado: CAIRN_GSD ja exportado vence a cadeia inteira" {
  local alheio="$BATS_TEST_TMPDIR/alheio-com-escape"
  mkdir -p "$alheio"
  git init -q "$alheio"
  run env CLAUDE_PROJECT_DIR="$alheio" \
    CAIRN_GSD="$CAIRN_SCRIPTS_DIR/cairn-gsd.sh" \
    bash -c "cd '$alheio' && $(canonical_form)"'; gsd_run query init.debug'
  [ "$status" -eq 0 ]
  printf '%s' "$output" | jq -e '.project_root' >/dev/null
}

# ---------------------------------------------------------------------------
# O reescritor: recusa nominal, check, idempotencia
# ---------------------------------------------------------------------------

@test "o registro de producao existe, tem schema e descreve caminhos reais" {
  [ -f "$REGISTRY" ]
  jq -e '.schema_version == 1' "$REGISTRY"
  jq -e '.adaptations | type == "array"' "$REGISTRY"
  # A CONTAGEM nao e asserida aqui, de proposito. Ate a task que adapta o
  # registro nascia vazio (caminho registrado e caminho que DEVE divergir do
  # cache, e registrar antes de adaptar reprovava o oraculo dois-sentidos);
  # dai em diante ele cresce, e os planos 03 a 07 registram caminhos novos.
  # Um numero fixado nesta suite viraria falso-vermelho no primeiro deles.
  # O que nao envelhece e o INVARIANTE: forma da entrada, ordem, unicidade,
  # e existencia no disco. A contagem exata de cada onda mora no verify do
  # plano correspondente, que e datado por construcao.
  jq -e 'all(.adaptations[]; has("path") and has("phase")
             and (.waves | type == "array") and (.waves | length > 0)
             and (.reason | length > 0))' "$REGISTRY"
  # Ordenado por path e sem repetido: o registro e lido por TRES consumidores
  # (o reescritor, o oraculo de bytes, o vendor) e um path duplicado daria
  # allowlist ambigua a todos os tres.
  jq -e '[.adaptations[].path] == ([.adaptations[].path] | sort)' "$REGISTRY"
  jq -e '([.adaptations[].path] | length)
         == ([.adaptations[].path] | unique | length)' "$REGISTRY"
  # Todo caminho registrado existe no disco: um registro apontando para nada
  # deixaria o oraculo exigindo divergencia de um arquivo ausente.
  local p
  while read -r p; do
    [ -f "$CAIRN_REPO_ROOT/cairn/gsd/$p" ]
  done < <(jq -r '.adaptations[].path' "$REGISTRY")
}

@test "apply recusa por nome: caminho ausente do registro, exit 2, sem escrever" {
  # O caminho ausente e DERIVADO do registro, nunca fixado a mao: os planos
  # 03 a 07 registram caminhos novos, e um literal aqui viraria falso-VERDE
  # no dia em que o caminho escolhido entrasse no registro — o teste seguiria
  # passando por outro motivo. `contracts/` fica de fora porque ali a recusa
  # e a de outra classe, com outra mensagem, coberta pelo teste vizinho.
  local absent before after
  absent="$(comm -23 \
    <(cd "$CAIRN_REPO_ROOT/cairn/gsd" \
        && find . -name '*.md' -not -path './contracts/*' \
        | sed 's|^\./||' | LC_ALL=C sort) \
    <(jq -r '.adaptations[].path' "$REGISTRY" | LC_ALL=C sort) | head -1)"
  [ -n "$absent" ]
  before="$(shasum "$CAIRN_REPO_ROOT/cairn/gsd/$absent")"
  run bash "$PREAMBLE" apply "$absent"
  [ "$status" -eq 2 ]
  printf '%s' "$output" | grep -qF 'gsd-adaptations.json'
  after="$(shasum "$CAIRN_REPO_ROOT/cairn/gsd/$absent")"
  [ "$before" = "$after" ]
}

@test "apply recusa por nome: caminho fora da arvore vendorizada, exit 2" {
  run bash "$PREAMBLE" apply cairn/scripts/cairn-gsd.py
  [ "$status" -eq 2 ]
  printf '%s' "$output" | grep -qF 'fora de cairn/gsd/'
}

@test "apply recusa por nome: contracts e MANIFEST, exit 2" {
  run bash "$PREAMBLE" apply cairn/gsd/MANIFEST.json
  [ "$status" -eq 2 ]
  printf '%s' "$output" | grep -qF 'MANIFEST.json'
  run bash "$PREAMBLE" apply contracts/contracts.json
  [ "$status" -eq 2 ]
  printf '%s' "$output" | grep -qF 'contracts/'
}

@test "check sai 3 com unified diff quando um registrado esta na forma antiga" {
  local base="$BATS_TEST_TMPDIR/stale"
  make_vendor_fixture "$base" "gsd-core/workflows/fixt.md"
  run bash "$PREAMBLE" check --root "$base"
  [ "$status" -eq 3 ]
  printf '%s' "$output" | grep -qF '_GSD_SHIM_NAME='
  printf '%s' "$output" | grep -qF 'CAIRN_GSD='
}

@test "apply troca a linha, e a segunda rodada e byte-identica com mtime intacto" {
  local base="$BATS_TEST_TMPDIR/idem"
  local rel="gsd-core/workflows/fixt.md"
  make_vendor_fixture "$base" "$rel"
  local f="$base/cairn/gsd/$rel"

  run bash "$PREAMBLE" apply --root "$base"
  [ "$status" -eq 0 ]
  grep -qF 'CAIRN_GSD=' "$f"
  # A prosa fora da linha sobrevive byte a byte: escrita cirurgica.
  grep -qF 'Prosa que nao muda.' "$f"
  run bash "$PREAMBLE" check --root "$base"
  [ "$status" -eq 0 ]

  local sha_before mtime_before sha_after mtime_after
  sha_before="$(shasum "$f" | cut -d' ' -f1)"
  mtime_before="$(file_mtime_ns "$f")"
  run bash "$PREAMBLE" apply --root "$base"
  [ "$status" -eq 0 ]
  sha_after="$(shasum "$f" | cut -d' ' -f1)"
  mtime_after="$(file_mtime_ns "$f")"
  [ "$sha_before" = "$sha_after" ]
  # write-only-when-changed (molde cairn-wrap.py:596-599): uma reescrita
  # byte-identica ainda seria uma escrita, e o mtime denunciaria.
  [ "$mtime_before" = "$mtime_after" ]
}

@test "list nomeia o estado de cada registrado, inclusive o sem preambulo" {
  local base="$BATS_TEST_TMPDIR/lista"
  make_vendor_fixture "$base" "gsd-core/workflows/fixt.md"
  mkdir -p "$base/cairn/gsd/gsd-core/workflows/x/steps"
  printf 'so prosa, nenhum preambulo\n' \
    > "$base/cairn/gsd/gsd-core/workflows/x/steps/sem.md"
  jq '.adaptations += [{"path":"gsd-core/workflows/x/steps/sem.md","phase":"36","waves":[1],"reason":"fixture sem preambulo"}]' \
    "$base/cairn/gsd-adaptations.json" > "$base/reg.json"
  mv "$base/reg.json" "$base/cairn/gsd-adaptations.json"

  run bash "$PREAMBLE" list --root "$base" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.counts.old' '1'
  assert_json_eq "$output" '.counts.none' '1'

  run bash "$PREAMBLE" apply --root "$base"
  [ "$status" -eq 0 ]
  # Registrado sem preambulo nao e erro nem edicao inventada: e o caso dos
  # arquivos que entram no registro por adaptacao de CONTEUDO (planos 03+).
  printf '%s' "$output" | grep -qF 'sem preâmbulo'
  run bash "$PREAMBLE" list --root "$base" --json
  assert_json_eq "$output" '.counts.new' '1'
  assert_json_eq "$output" '.counts.none' '1'
}
