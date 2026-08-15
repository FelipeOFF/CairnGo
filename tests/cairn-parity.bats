#!/usr/bin/env bats
# cairn-parity.bats — o gate de paridade da fase 38.
#
# Três perguntas, e todas as três com o mesmo critério de honestidade: uma
# superfície que responde sem ter medido não conta como pronta, e um teste que
# não morde é defeito do teste.
#
#   1. (PAR-01) todo verbo que o binário python serve tem cobertura executável;
#   2. (PAR-02) toda chamada `gsd_run` do runtime vendorizado resolve num verbo
#      que o binário serve, e nenhum comando manda rodar `/gsd:` que não resolve;
#   3. (PAR-02/03/04) um repositório construído do zero, sem gsd-core instalado,
#      sai limpo no doctor e verde no gate.
#
# Medido em 2026-08-12, ANTES de qualquer edição de produção desta fase:
#   1 cobertura por verbo             -> TODOS, JÁ VERDE (o oráculo é o controle
#     O NUMERO SAIA DAQUI EM 2026-08-15, e a razao e' que ele ja tinha
#     mentido uma vez: o comentario dizia 87/87 enquanto contracts.json
#     carregava 89 (os dois do references_extension da fase 38). O teste
#     sempre DERIVOU o universo do proprio contracts.json e por isso seguiu
#     verde e correto — quem envelheceu foi a prosa ao lado dele. Um numero
#     cravado em comentario nao tem quem o revalide, entao nao se crava.
#     negativo: handler forjado sem cobertura tem que vazar pela MESMA função)
#   2 scan de `gsd_run` no vendor     -> vermelho, 2 rotas mortas em references/
#   3 mencoes /gsd: em cairn/commands -> vermelho, 10 passos e nenhum registro
#   4 doctor no repositório novo      -> a medir no plano 03
#
# Estilo da casa: status exato (`-eq`), nunca `-ne 0`; nome de `@test` em ASCII
# puro — `bats -j` não resolve nome com acento, e um teste que não roda sai da
# conta sem avisar (medido na fase 37, 4 testes viraram `unknown test name`).

load 'helpers'

GSD="$CAIRN_SCRIPTS_DIR/cairn-gsd.py"
SCENARIOS="$CAIRN_TESTS_DIR/fixtures/gsd-goldens/scenarios.json"

# --- PAR-01: cobertura por verbo -------------------------------------------

# Imprime cada handler de HANDLERS_FILE que NÃO tem cobertura executável, uma
# por linha. Cobertura é qualquer uma das duas:
#
#   (a) um cenário no manifesto golden — `.scenarios[].verb` — que é o que o
#       comparador diferencial da fase 33 roda de verdade contra o binário;
#   (b) uma INVOCAÇÃO direta em algum .bats do diretório: o token logo depois
#       de um dispatcher ($GSD, $CHECK_SIB, $STATE_SIB, cairn-gsd*.py), com o
#       `query` opcional no meio.
#
# (b) exige invocação, não menção: um verbo citado em comentário não é coberto,
# e contar citação como cobertura é exatamente a mentira que este arquivo
# existe para impedir.
#
# Saída vazia = cobertura completa. A função é UMA só, e o controle negativo
# abaixo chama esta mesma — um guard cuja prova de mordida roda outro código
# não provou coisa nenhuma.
uncovered_handlers() {
  local handlers_file="$1" scenarios="$2" bats_dir="$3"
  python3 - "$handlers_file" "$scenarios" "$bats_dir" <<'PY'
import json, re, sys, pathlib

handlers_file, scenarios_path, bats_dir = sys.argv[1:4]
handlers = [l.strip() for l in open(handlers_file, encoding="utf-8")
            if l.strip()]

with open(scenarios_path, encoding="utf-8") as fh:
    golden = {s.get("verb") for s in json.load(fh).get("scenarios", [])}

blob = "\n".join(
    p.read_text(encoding="utf-8", errors="replace")
    for p in sorted(pathlib.Path(bats_dir).glob("*.bats")))

DISPATCH = r'(?:\$GSD|\$CHECK_SIB|\$STATE_SIB|cairn-gsd[\w.-]*)"?'
for verb in handlers:
    if verb in golden:
        continue
    pat = DISPATCH + r'\s+(?:query\s+)?' + re.escape(verb) + r'(?![\w.-])'
    if re.search(pat, blob):
        continue
    print(verb)
PY
}

@test "cobertura: todo verbo implementado tem cenario golden ou teste bats direto" {
  local handlers="$BATS_TEST_TMPDIR/handlers.txt"
  "$GSD" --list-implemented > "$handlers"
  [ -s "$handlers" ]
  run uncovered_handlers "$handlers" "$SCENARIOS" "$CAIRN_TESTS_DIR"
  [ "$status" -eq 0 ]
  if [ -n "$output" ]; then
    printf 'verbos implementados SEM cobertura executavel:\n%s\n' "$output" >&2
    return 1
  fi
}

@test "controle negativo: verbo implementado sem cenario nem bats VAZA pela mesma funcao" {
  # O mesmo insumo real, mais UMA linha forjada. Se a comparação engolisse um
  # handler descoberto, o teste acima estaria verde por vacuidade.
  local handlers="$BATS_TEST_TMPDIR/handlers-forged.txt"
  "$GSD" --list-implemented > "$handlers"
  printf 'forged.uncovered-verb\n' >> "$handlers"
  run uncovered_handlers "$handlers" "$SCENARIOS" "$CAIRN_TESTS_DIR"
  [ "$status" -eq 0 ]
  [ "$output" = "forged.uncovered-verb" ]
}

# --- PAR-02: paridade executavel do corpo vendorizado -----------------------
#
# A pergunta é a do card, na parte que É verificável dentro de bats: o runtime
# que o plugin carrega chama alguma coisa que o binário python não serve? Todas
# as chamadas mortas medidas moram sob `gsd-core/references/`, e nenhuma delas
# grita: as duas estão embrulhadas em `|| true`, então o dispatcher morre exit 2
# e o workflow segue como se tivesse funcionado.

SCAN="$CAIRN_TESTS_DIR/parity-scan.py"
CONTRACTS_DIR="$CAIRN_REPO_ROOT/cairn/gsd/contracts"

@test "paridade: todo gsd_run do runtime vendorizado resolve num verbo servido" {
  run python3 "$SCAN" --contracts "$CONTRACTS_DIR" \
    --corpus "$CAIRN_REPO_ROOT/cairn/gsd"
  [ "$status" -eq 0 ]
  if [ -n "$output" ]; then
    printf 'chamadas gsd_run que o dispatcher NAO roteia:\n%s\n' "$output" >&2
    return 1
  fi
}

@test "controle negativo: chamada forjada no corpus fixture VAZA pelo mesmo scanner" {
  # Mesmo binário, mesma tabela de rotas, corpus trocado. O fixture carrega uma
  # chamada morta e duas armadilhas que precisam ser ignoradas — prosa em crase
  # e o spelling com espaço `query verification status`, que resolve.
  run python3 "$SCAN" --contracts "$CONTRACTS_DIR" \
    --corpus "$CAIRN_TESTS_DIR/fixtures/parity-corpus"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == *"query forged.dead-route" ]]
}

# --- PAR-02: os comandos param de nomear verbo que a instalacao nao resolve --
#
# Dívida medida pela fase 37 e mandada para cá com dado (M3 do 38-CONTEXT):
# 23 menções `/gsd:` em 11 comandos, das quais 10 eram PASSO — linha que manda
# rodar um verbo que uma instalação limpa não resolve. A decisão D-01 é
# descartar, não vendorizar, e descartar quer dizer três coisas: o passo é
# reescrito, a menção que sobra é registrada com motivo, e o registro é travado
# nos DOIS sentidos.

REGISTRY="$CAIRN_REPO_ROOT/cairn/gsd-parity.json"
COMMANDS_DIR="$CAIRN_REPO_ROOT/cairn/commands"
VENDORED_DIR="$CAIRN_REPO_ROOT/cairn/gsd/commands/gsd"

# Imprime as divergências entre as menções `/gsd:` reais e o registro, nos dois
# sentidos: `sem-registro <arquivo> <verbo>` para menção não registrada, e
# `registro-obsoleto <arquivo> <verbo>` para entrada que não corresponde a
# menção nenhuma. Verbo vendorizado (arquivo existe sob cairn/gsd/commands/gsd/)
# dispensa registro — ele resolve.
#
# Uma allowlist que só cresce vira silêncio com carimbo; o segundo sentido é o
# que a impede de virar isso.
unregistered_gsd_mentions() {
  local commands_dir="$1" registry="$2" vendored_dir="$3"
  python3 - "$commands_dir" "$registry" "$vendored_dir" <<'PY'
import json, os, re, sys

commands_dir, registry_path, vendored_dir = sys.argv[1:4]

with open(registry_path, encoding="utf-8") as fh:
    registry = json.load(fh)

# (verbo, arquivo) declarados; "*" e o coringa das mencoes genericas /gsd:*
declared = set()
for entry in registry.get("verbs", []):
    for mention in entry.get("mentions", []):
        declared.add((entry["verb"], mention))

vendored = {p[:-3] for p in os.listdir(vendored_dir) if p.endswith(".md")}

seen = set()
rows = []
for name in sorted(os.listdir(commands_dir)):
    if not name.endswith(".md"):
        continue
    rel = "cairn/commands/" + name
    text = open(os.path.join(commands_dir, name), encoding="utf-8").read()
    for match in re.finditer(r"/gsd:([a-z][a-z-]*)?", text):
        verb = match.group(1) or "*"
        if verb in vendored:
            continue
        seen.add((verb, rel))
        if (verb, rel) not in declared:
            rows.append("sem-registro %s %s" % (rel, verb))

for verb, rel in sorted(declared - seen):
    rows.append("registro-obsoleto %s %s" % (rel, verb))

for row in sorted(set(rows)):
    print(row)
PY
}

@test "registro de paridade: toda mencao /gsd: esta registrada, e todo registro tem mencao" {
  [ -f "$REGISTRY" ]
  run unregistered_gsd_mentions "$COMMANDS_DIR" "$REGISTRY" "$VENDORED_DIR"
  [ "$status" -eq 0 ]
  if [ -n "$output" ]; then
    printf 'registro de paridade fora de sincronia:\n%s\n' "$output" >&2
    return 1
  fi
}

@test "registro de paridade: disposicao de vocabulario fechado e motivo escrito" {
  [ -f "$REGISTRY" ]
  # Vocabulário fechado, e `descartado` OBRIGA nomear o que fazer no lugar —
  # é o que separa uma decisão registrada de um silêncio com carimbo.
  run jq -e '
    [ .verbs[]
      | select(
          ((.disposition | IN("passthrough", "descartado")) | not)
          or ((.reason // "") | length) < 40
          or (.disposition == "descartado"
              and ((.replacement // "") | length) < 10)
        )
      | .verb
    ] | length == 0' "$REGISTRY"
  [ "$status" -eq 0 ]
}

@test "nenhum comando manda RODAR um verbo gsd que a instalacao nao resolve" {
  # A forma imperativa medida em M3: `Run \`/gsd:x\`` / `run \`/gsd:x\``, e a
  # linha nua num bloco de código. A negativa ("never run", "do **not** run")
  # não é passo — é a instrução de NÃO fazer, e ela pode continuar nomeando o
  # verbo. `gsd.md` é o passthrough declarado e fica fora por construção.
  local hits
  hits="$(grep -rnE '(^[[:space:]]*/gsd:|[Rr]un `/gsd:)' "$COMMANDS_DIR" \
    | grep -v '^.*/gsd\.md:' \
    | grep -viE 'never run|do \*\*not\*\* run|not run' || true)"
  # Toda linha que sobrou nomeia um verbo — e ele TEM que ser vendorizado.
  local line verb
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    verb="$(printf '%s' "$line" | sed -E 's|.*/gsd:([a-z][a-z-]*).*|\1|')"
    if [ ! -f "$VENDORED_DIR/$verb.md" ]; then
      printf 'passo mandando rodar verbo nao resolvivel:\n%s\n' "$line" >&2
      return 1
    fi
  done <<< "$hits"
}

# --- PAR-02/03/04: o repositorio novo, sem gsd-core instalado ---------------
#
# "Fecha discuss, plan, execute e verify inteiros" nao roda dentro de bats: os
# quatro verbos sao prompts que um agente executa. O que E verificavel, e o que
# esta abaixo, e o que sobra quando se tira o agente da conta (D-04 do CONTEXT):
# os caminhos que os quatro comandos apontam existem dentro do plugin, os
# verbos que eles executam respondem no repositorio novo, o doctor sai limpo
# ali, e o gate sai verde — com o controle que prova que ele sabe ficar
# vermelho.
#
# O repositorio e construido do zero e ligado como /cairn:new manda: uma issue
# por requisito, com o par de labels e o carimbo `gsd`, as issues da fase
# COMPLETA fechadas, e os mapas gerados. Um repositorio mal ligado sairia sujo
# no doctor por estar mal ligado, e o teste estaria medindo o fixture.

PLUGINS_FIXTURE="$CAIRN_TESTS_DIR/fixtures/parity/installed_plugins.json"
DOCTOR="$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
GATE="$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
MAP="$CAIRN_SCRIPTS_DIR/cairn-map.sh"

# Repositório novo, ligado à maneira do cairn. Deixa o cwd dentro dele.
wire_new_repo() {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix par --non-interactive >/dev/null 2>&1
  bd create "AUTH-01: User can sign up with email and password" --id par-001 \
    -t task -l m-v1,phase-1 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1"}}' \
    --silent >/dev/null
  bd create "AUTH-02: User can log in with valid credentials" --id par-002 \
    -t task -l m-v1,phase-1 \
    --metadata '{"gsd":{"req":"AUTH-02","phase":1,"milestone":"v1"}}' \
    --silent >/dev/null
  bd create "API-01: Public API requests beyond the limit receive HTTP 429" \
    --id par-003 -t task -l m-v1,phase-2 \
    --metadata '{"gsd":{"req":"API-01","phase":2,"milestone":"v1"}}' \
    --silent >/dev/null
  bd close par-001 >/dev/null
  bd close par-002 >/dev/null
  bash "$MAP" 1 >/dev/null
  bash "$MAP" 2 >/dev/null
  beads_export_refresh
  git add -A >/dev/null 2>&1
  git commit -q -m "repositorio novo, ligado" >/dev/null 2>&1
}

@test "repositorio novo: os quatro comandos do ciclo apontam so caminhos que existem no plugin" {
  local cmd path missing=""
  for cmd in discuss-phase plan work verify; do
    [ -f "$COMMANDS_DIR/$cmd.md" ]
    while IFS= read -r path; do
      [ -n "$path" ] || continue
      path="${path#\$\{CLAUDE_PLUGIN_ROOT\}/}"
      [ -e "$CAIRN_REPO_ROOT/cairn/$path" ] || \
        missing="$missing$cmd: $path"$'\n'
    done < <(grep -ohE '\$\{CLAUDE_PLUGIN_ROOT\}/[A-Za-z0-9._/-]+' \
             "$COMMANDS_DIR/$cmd.md" | sort -u)
    # e nenhum deles nomeia um verbo /gsd: — o ciclo fecha dentro do plugin
    if grep -q '/gsd:' "$COMMANDS_DIR/$cmd.md"; then
      missing="$missing$cmd: nomeia /gsd:"$'\n'
    fi
  done
  if [ -n "$missing" ]; then
    printf 'comandos do ciclo apontando para fora do plugin:\n%s' "$missing" >&2
    return 1
  fi
}

@test "repositorio novo: os verbos que o ciclo executa respondem sem gsd-core instalado" {
  require_bd
  wire_new_repo

  # A ORDEM e a do ciclo, e ela e load-bearing: os bundles init.* compoem o
  # FATO de estado pelo irmao de estado, cujo portador vive no bd e nasce em
  # begin-phase. Antes disso a falha nomeada do irmao e PROPAGADA (CORE-04) —
  # medido aqui: init.plan-phase sai != 0 num repositorio onde nenhuma fase
  # comecou, e esta certo que saia.
  run "$GSD" query state.begin-phase 2
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.created' 'true'
  run "$GSD" query state.load
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.state_exists' 'true'

  # plan: o que o planejador pergunta antes de escrever o PLAN
  run "$GSD" query phases.list
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.count' '2'
  run "$GSD" query roadmap.get-phase 1
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.phase_name' 'Auth'
  run "$GSD" query init.plan-phase 1
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.project_root' "$(pwd -P)"

  # execute: o bundle do executor e a estrutura do plano que ele vai rodar
  run "$GSD" query init.execute-phase 1
  [ "$status" -eq 0 ]
  run "$GSD" query phase.list-plans 1
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.plan_count' '1'
  run "$GSD" query verify.plan-structure \
    .planning/phases/01-auth/01-01-PLAN.md
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.valid' 'true'

  # verify: o bundle do verificador fecha o ciclo no mesmo repositorio
  run "$GSD" query init.verify-work 1
  [ "$status" -eq 0 ]
}

@test "repositorio novo: o doctor sai limpo, zero falhas e zero avisos" {
  require_bd
  wire_new_repo
  # O seam é obrigatório: sem ele o check 10 leria a lista de plugins de quem
  # está rodando a suíte, e o veredito do teste passaria a depender da máquina.
  run env CAIRN_INSTALLED_PLUGINS="$PLUGINS_FIXTURE" bash "$DOCTOR"
  [ "$status" -eq 0 ]
  refute_line_matching '✗'
  refute_line_matching '⚠'
  [[ "$output" == *"no external GSD lineage installed"* ]]
}

@test "repositorio novo: o gate sai verde" {
  require_bd
  wire_new_repo
  run bash "$GATE"
  [ "$status" -eq 0 ]
  [[ "$output" == *"no open issues in completed phase"* ]]
}

@test "controle negativo: issue aberta numa fase completa faz o gate sair 6" {
  # O verde acima não vale nada sem este. Um gate que nunca fica vermelho não
  # é gate, e a fase 1 do fixture é completa no ROADMAP — reabrir a issue dela
  # é exatamente o estado que o gate existe para barrar.
  require_bd
  wire_new_repo
  bd update par-001 --status open >/dev/null 2>&1
  run bash "$GATE"
  [ "$status" -eq 6 ]
  [[ "$output" == *"par-001"* ]]
}

# Falha nomeando a linha, e por função porque `!` inline suprime o errexit do
# bats — a negativa inline nunca falharia o teste.
refute_line_matching() {
  local pattern="$1" hit
  hit="$(printf '%s\n' "$output" | grep -- "$pattern" || true)"
  if [ -n "$hit" ]; then
    printf 'linha inesperada no relatorio:\n%s\n' "$hit" >&2
    return 1
  fi
}

@test "controle negativo: gsd-core instalado ao lado suja o doctor do mesmo repositorio" {
  # O limpo acima e sobre "sem gsd-core instalado" (PAR-03), e sem este par a
  # frase nao teria como ser falsa: mesmo repositorio, mesmo comando, so a
  # lista de plugins troca. Duas linhagens respondendo ao mesmo tempo e a
  # janela que a vendorizacao fechou, e o doctor tem que dizer isso.
  require_bd
  wire_new_repo
  run env CAIRN_INSTALLED_PLUGINS="$CAIRN_TESTS_DIR/fixtures/parity/installed_plugins_with_gsd.json" \
    bash "$DOCTOR"
  [ "$status" -eq 7 ]
  [[ "$output" == *"an external GSD plugin is still installed"* ]]
  [[ "$output" == *"claude plugin uninstall gsd-core@cairngo"* ]]
}
