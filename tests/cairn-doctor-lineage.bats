#!/usr/bin/env bats
# cairn-doctor-lineage.bats — o check 10 do doctor, depois da INVERSÃO (PLUG-02).
#
# O check perguntava "a capability cairn está registrada contra o gsd-core
# instalado?" e prescrevia INSTALAR `gsd-core@cairngo`. Desde a fase 37 quem
# responde `/gsd:*` é o runtime vendorizado dentro do plugin, e qualquer
# linhagem externa instalada é achado com prescrição de UNINSTALL.
#
# Um check que valida o contrário do que validava é exatamente onde um teste
# que não morde passa despercebido. Por isso as duas direções, e ambas foram
# RODADAS contra o doctor pré-conversão (blob 94e26233…, 4042 linhas) antes de
# uma linha de implementação mudar:
#
#   direção A — a asserção NOVA fica vermelha no estado antigo (A1-A4);
#   direção B — a asserção ANTIGA deixa de ser produzível no estado novo (B1).
#
# Sem B1 a inversão poderia ser uma prescrição nova ACRESCENTADA ao lado da
# velha, com as duas saindo juntas, e A1-A4 passariam do mesmo jeito.
#
# Nota de runner, medida: `bats -j` não resolve nomes de @test que carregam
# "í" — quatro destes nove viraram "unknown test name" e NÃO rodaram, com a
# suíte ainda saindo 1 pelos outros. Um teste que não roda é pior que um
# vermelho, porque parece ausência de problema. Os títulos evitam o caractere.
#
# Este arquivo vive separado de cairn-doctor.bats de propósito: ele asserta
# sobre UM check, lido do `--json`, e por isso não pode ser derrubado — nem
# salvo — por nenhum dos outros 23. cairn-doctor.bats leva ~9 min; este leva
# segundos, e a diferença é o que torna a inversão testável dentro de um ciclo.

load 'helpers'

DOCTOR="$CAIRN_SCRIPTS_DIR/cairn-doctor.py"

# Um repo mínimo em que o doctor se considera aplicável: .planning/ + .beads/.
make_lineage_fixture() {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix lin --non-interactive >/dev/null 2>&1
}

# Um HOME de fixture com installed_plugins.json escrito à mão. $1 = HOME,
# demais args = ids de plugin ("gsd-core@cairngo", "gsd@cairngo"). Sem args,
# um arquivo de plugins vazio: a máquina limpa.
wire_installed_plugins() {
  local home="$1"; shift
  mkdir -p "$home/.claude/plugins"
  local entries="" id
  for id in "$@"; do
    [ -n "$entries" ] && entries="$entries,"
    entries="$entries\"$id\":[{\"installPath\":\"$home/.claude/plugins/cache/$id\"}]"
  done
  printf '{"plugins":{%s}}\n' "$entries" \
    > "$home/.claude/plugins/installed_plugins.json"
}

# Roda o doctor com HOME pinado e devolve SÓ a entrada do check 10, em JSON.
# Isolar o check é o que torna estas asserções imunes aos outros 23 — um deles
# ficando vermelho por motivo alheio não pode nem quebrar nem salvar esta
# medição.
capability_check() {
  local home="$1"; shift
  env -u CAIRN_GSD_BIN -u CLAUDE_PLUGIN_ROOT HOME="$home" \
    PATH="/usr/bin:/bin:$(dirname "$(command -v bd)")" "$@" \
    python3 "$DOCTOR" --json --project-dir "$PWD" 2>/dev/null \
    | python3 -c '
import json, sys
doc = json.load(sys.stdin)
for check in doc.get("checks", []):
    if check.get("id") == "gsd-capability":
        print(json.dumps(check, ensure_ascii=False))
        raise SystemExit(0)
raise SystemExit("gsd-capability nao aparece no relatorio")
'
}

field() { python3 -c 'import json,sys; print(json.load(sys.stdin)["'"$2"'"])' <<<"$1"; }

# Todo o texto do check numa linha só, para as asserções de substring.
flat() {
  python3 -c 'import json,sys
c = json.loads(sys.stdin.read())
print(c["detail"], " ".join(c.get("items") or []))' <<<"$1"
}

# Um binário GSD falso na forma que cairn-capability.py reconhece. $1 =
# "legacy" (a 4.x, sem subcomando capability) ou "core-unregistered" (gsd-core
# respondendo com uma lista de capabilities vazia). É este stub que faz o
# doctor ANTIGO chegar às duas prescrições que a direção B tem de derrubar —
# sem ele o check para antes, em "no GSD binary found", e os testes B ficariam
# verdes contra o estado antigo sem medir nada.
wire_gsd_stub() {
  local mode="$1" stub="$PWD/.gsd-stub"
  cat > "$stub" <<EOF
#!/usr/bin/env sh
mode="$mode"
EOF
  cat >> "$stub" <<'STUB'
[ "$1" = "capability" ] || { echo "unexpected: $*" >&2; exit 1; }
if [ "$mode" = "legacy" ]; then
  echo "Error: Unknown command: capability" >&2; exit 1
fi
echo '[]'
STUB
  chmod +x "$stub"
  printf '%s\n' "$stub"
}

refute_contains() {
  if grep -qF -- "$2" <<<"$1"; then
    echo "achei '$2' na saída do check, e ele não deveria estar lá" >&2
    return 1
  fi
}

# ---------------------------------------------------------------------------
# direção A — a asserção nova
# ---------------------------------------------------------------------------

@test "A1 sem linhagem externa e com runtime vendorizado completo, o check e ok" {
  require_bd
  make_lineage_fixture
  local home="$PWD/clean-home"
  wire_installed_plugins "$home"

  local check
  check="$(capability_check "$home")"
  [ "$(field "$check" status)" = "ok" ]
  # O detalhe nomeia o runtime vendorizado, não um binário GSD do ambiente.
  grep -qiE "vendored|vendorizado" <<<"$(flat "$check")"
}

@test "A2 gsd-core instalado FALHA, com prescrição de uninstall" {
  require_bd
  make_lineage_fixture
  local home="$PWD/dirty-home"
  wire_installed_plugins "$home" "gsd-core@cairngo"

  local check text
  check="$(capability_check "$home")"
  text="$(flat "$check")"
  [ "$(field "$check" status)" = "fail" ]
  grep -qF "gsd-core@cairngo" <<<"$text"
  grep -qF "uninstall" <<<"$text"
  grep -qF "/reload-plugins" <<<"$text"
}

@test "A2b a linhagem 4.x instalada também é uninstall, nunca upgrade" {
  # Este é o par que mais importa da direção A: contra o doctor ANTIGO o mesmo
  # estado dava fail dizendo "Install the official core: claude plugin install
  # gsd-core@cairngo". O verdict não mudou; a prescrição inverteu.
  require_bd
  make_lineage_fixture
  local home="$PWD/legacy-home"
  wire_installed_plugins "$home" "gsd@cairngo"

  local check text
  check="$(capability_check "$home")"
  text="$(flat "$check")"
  [ "$(field "$check" status)" = "fail" ]
  grep -qF "gsd@cairngo" <<<"$text"
  grep -qF "uninstall" <<<"$text"
}

@test "A2c as duas linhagens ao mesmo tempo nomeiam as duas" {
  require_bd
  make_lineage_fixture
  local home="$PWD/both-home"
  wire_installed_plugins "$home" "gsd@cairngo" "gsd-core@cairngo"

  local check text
  check="$(capability_check "$home")"
  text="$(flat "$check")"
  [ "$(field "$check" status)" = "fail" ]
  grep -qF "gsd@cairngo" <<<"$text"
  grep -qF "gsd-core@cairngo" <<<"$text"
}

@test "A3 runtime vendorizado incompleto FALHA acusando o plugin, não o ambiente" {
  require_bd
  make_lineage_fixture
  local home="$PWD/clean-home"
  wire_installed_plugins "$home"
  local broken="$PWD/broken-runtime"
  mkdir -p "$broken"

  local check text
  check="$(capability_check "$home" CAIRN_VENDORED_GSD="$broken")"
  text="$(flat "$check")"
  [ "$(field "$check" status)" = "fail" ]
  grep -qiE "vendored|vendorizado" <<<"$text"
  # Acusa o install, e não manda instalar outra coisa.
  refute_contains "$text" "plugin install gsd-core"
}

@test "A4 residuo em .gsd/ e warn com fix de limpeza, nunca fail" {
  # Resíduo é atrito, não inconsistência de estado — a mesma disciplina dos
  # checks 8 e 14: exit 7 gasto com atrito para de significar alguma coisa.
  # O doctor NOMEIA o fix; quem apaga é a pessoa.
  require_bd
  make_lineage_fixture
  mkdir -p .gsd/capabilities/cairn/scripts
  cp "$CAIRN_REPO_ROOT/cairn/capability/capability.json" \
     .gsd/capabilities/cairn/capability.json
  local home="$PWD/clean-home"
  wire_installed_plugins "$home"

  local check text
  check="$(capability_check "$home")"
  text="$(flat "$check")"
  [ "$(field "$check" status)" = "warn" ]
  grep -qF ".gsd/capabilities/cairn" <<<"$text"
  grep -qF "rm -rf" <<<"$text"
}

@test "A4b o residuo perde para a linhagem externa: um fail nao vira warn" {
  # Ordem de decisão, e ela importa. Uma máquina que rodou /cairn:init antes da
  # v1.6 tem AS DUAS coisas: o gsd-core instalado e o resíduo em .gsd/. Se o
  # resíduo fosse avaliado primeiro, o achado que exige ação sairia como warn.
  require_bd
  make_lineage_fixture
  mkdir -p .gsd/capabilities/cairn
  cp "$CAIRN_REPO_ROOT/cairn/capability/capability.json" \
     .gsd/capabilities/cairn/capability.json
  local home="$PWD/dirty-home"
  wire_installed_plugins "$home" "gsd-core@cairngo"

  local check
  check="$(capability_check "$home")"
  [ "$(field "$check" status)" = "fail" ]
}

# ---------------------------------------------------------------------------
# direção B — a asserção antiga
# ---------------------------------------------------------------------------

@test "B1 a prescricao antiga de INSTALAR gsd-core nao sai mais" {
  # O controle da INVERSÃO, e o único teste deste arquivo que não fala do
  # verdict. Contra o doctor antigo, este fixture (4.x instalado, capability
  # não registrada) imprimia "Install the official core: claude plugin install
  # gsd-core@cairngo" — medido. Se a fase tivesse ACRESCENTADO a prescrição
  # nova ao lado da velha, A1-A4 passariam e só este ficaria vermelho.
  require_bd
  make_lineage_fixture
  local home="$PWD/legacy-home" stub
  wire_installed_plugins "$home" "gsd@cairngo"
  stub="$(wire_gsd_stub legacy)"

  local text
  text="$(flat "$(capability_check "$home" CAIRN_GSD_BIN="$stub")")"
  refute_contains "$text" "plugin install gsd-core@cairngo"
  refute_contains "$text" "Install the official"
}

@test "B2 nenhum caminho do check manda re-rodar /cairn:init para registrar capability" {
  # A segunda metade da direção B. A capability foi ARQUIVADA (D-04): não há
  # mais host externo para as contributions, então "re-run /cairn:init" deixou
  # de ser um conserto — é um conselho para reinstalar o que o check agora pede
  # para limpar. Contra o doctor antigo esta era a saída padrão do fixture
  # limpo, e por isso este teste é vermelho lá.
  require_bd
  make_lineage_fixture
  local home="$PWD/clean-home" stub
  wire_installed_plugins "$home"
  stub="$(wire_gsd_stub core-unregistered)"

  local text
  text="$(flat "$(capability_check "$home" CAIRN_GSD_BIN="$stub")")"
  refute_contains "$text" "did not register"
  refute_contains "$text" "re-run /cairn:init"
}
