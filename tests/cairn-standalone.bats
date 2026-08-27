#!/usr/bin/env bats
# cairn-standalone.bats — o plugin é autocontido (PLUG-01, PLUG-03, PLUG-05).
#
# A fase 37 fecha a janela em que /gsd:* velho (markdown, cache 1.8.0) e
# /cairn:* novo (bd) coexistem. Este arquivo é o oráculo dessa troca, e cada
# asserção aqui foi escrita e RODADA contra o estado PRÉ-conversão: se ela não
# ficou vermelha lá, ela não mede nada.
#
# Vermelho medido em 2026-08-12, antes de qualquer edição de produção:
#   1 marketplace ainda lista gsd-core          -> vermelho
#   2 plugin.json ainda depende de gsd-core     -> vermelho
#   3 as duas versões concordam                 -> JÁ VERDE (controle: a
#     edição dos dois JSON não pode arrastar o carregador que o check 15 lê)
#   4 nenhum `inline` chama preflight/`/gsd:`   -> vermelho (13 chamam)
#   5 todo `vendored` aponta arquivo existente  -> vermelho (0 declaram)
#   6 `implementation` fora do vocabulário é 2  -> vermelho (chave não existe)
#   8 nenhuma fase alheia nem milestone mexido -> verde, e é para continuar
#   9 controle: o filtro do 8 ainda barra os três caminhos que uma migração
#     de dados teria tocado -> verde, e existe porque um filtro largo demais
#     é como uma garantia vira frase outra vez
#
# Estilo da casa: status exato (`-eq`), nunca `-ne 0`; negativa por função,
# porque `!` inline suprime o errexit do bats e a falha nunca falharia o teste.

load 'helpers'

WRAP="$CAIRN_SCRIPTS_DIR/cairn-wrap.sh"
MARKETPLACE="$CAIRN_REPO_ROOT/.claude-plugin/marketplace.json"
PLUGIN_JSON="$CAIRN_REPO_ROOT/cairn/.claude-plugin/plugin.json"
COMMANDS_DIR="$CAIRN_REPO_ROOT/cairn/commands"

refute_in_file() {
  if grep -qF -- "$1" "$2"; then
    echo "achei '$1' em $2, e ele não deveria estar lá" >&2
    return 1
  fi
}

# ---------------------------------------------------------------------------
# 1-3 — o plugin não declara mais dependência de plugin externo
# ---------------------------------------------------------------------------

@test "o marketplace não publica mais nenhuma linhagem GSD além do cairn" {
  # Lido do JSON, nunca por grep de linha: uma entrada comentada, reindentada
  # ou movida de posição continuaria escapando de um grep e não escapa daqui.
  run python3 -c "
import json, sys
data = json.load(open('$MARKETPLACE'))
names = [p.get('name', '') for p in data.get('plugins', [])]
extra = [n for n in names if n != 'cairn']
print(','.join(names))
sys.exit(1 if extra else 0)
"
  [ "$status" -eq 0 ] || {
    echo "o marketplace ainda publica: $output" >&2
    return 1
  }
}

@test "plugin.json larga gsd-core e mantém context-mode" {
  # O controle negativo é a segunda metade: uma remoção larga demais leva o
  # context-mode junto, e sem esta asserção isso passaria verde.
  run python3 -c "
import json, sys
deps = json.load(open('$PLUGIN_JSON')).get('dependencies', [])
names = [d if isinstance(d, str) else d.get('name', '') for d in deps]
has_gsd = any(n.startswith('gsd') for n in names)
has_ctx = 'context-mode' in names
print(','.join(names))
sys.exit(0 if (not has_gsd and has_ctx) else 1)
"
  [ "$status" -eq 0 ] || {
    echo "dependencies == $output (esperado: sem gsd*, com context-mode)" >&2
    return 1
  }
}

@test "os dois carregadores de versão continuam concordando" {
  # Controle da edição dos JSON. O check 15 (release-versions) lê
  # metadata.version do marketplace e version do plugin.json; remover uma
  # entrada de plugin não pode encostar em nenhum dos dois.
  run python3 -c "
import json
m = json.load(open('$MARKETPLACE'))['metadata']['version']
p = json.load(open('$PLUGIN_JSON'))['version']
print(m, p)
raise SystemExit(0 if m == p else 1)
"
  [ "$status" -eq 0 ] || {
    echo "versões divergiram: $output" >&2
    return 1
  }
}

# ---------------------------------------------------------------------------
# 4-6 — os 13 declaram ONDE vive sua implementação, e param de delegar
# ---------------------------------------------------------------------------

# Imprime "<comando> <implementation>" por comando que declara a chave.
declared_implementations() {
  local f name value
  for f in "$COMMANDS_DIR"/*.md; do
    value="$(sed -n '/^---$/,/^---$/p' "$f" \
             | sed -n 's/^implementation:[[:space:]]*//p' | head -1)"
    [ -n "$value" ] || continue
    name="$(basename "$f" .md)"
    echo "$name $value"
  done
}

@test "nenhum comando de implementação inline delega para fora" {
  # O par de proibições é o coração de PLUG-01: um `inline` que ainda chama
  # preflight declara uma delegação que não existe, e um preflight que não
  # pode falhar é o gate vazio que cairn-capability.py documenta.
  local name impl file found=0
  while read -r name impl; do
    [ "$impl" = "inline" ] || continue
    found=$((found + 1))
    file="$COMMANDS_DIR/$name.md"
    refute_in_file 'cairn-wrap.sh" preflight' "$file"
    refute_in_file 'Run `/gsd:' "$file"
    refute_in_file 'Run `/gsd:' "$file"
  done < <(declared_implementations)
  [ "$found" -gt 0 ] || {
    echo "nenhum comando declara implementation: inline" >&2
    return 1
  }
}

@test "todo comando de implementação vendorizada aponta um arquivo que existe" {
  local name impl file target found=0
  while read -r name impl; do
    [ "$impl" = "vendored" ] || continue
    found=$((found + 1))
    file="$COMMANDS_DIR/$name.md"
    # O alvo é nomeado no corpo do comando, sob cairn/gsd/. Extraído do texto,
    # nunca digitado aqui: um comando que aponte para o lugar errado falha.
    target="$(grep -o 'gsd/commands/gsd/[a-z0-9-]*\.md' "$file" | head -1)"
    [ -n "$target" ] || {
      echo "$name.md declara vendored mas não nomeia arquivo sob gsd/" >&2
      return 1
    }
    [ -f "$CAIRN_REPO_ROOT/cairn/$target" ] || {
      echo "$name.md aponta cairn/$target, que não existe" >&2
      return 1
    }
  done < <(declared_implementations)
  # Zero e' o estado desde a phase 46: os comandos de planejamento passaram a
  # ser autossuficientes (cairn-record), e o runtime vendorizado fica para o
  # passthrough /cairn:gsd. O teste segue valendo para o dia em que um voltar
  # a declarar vendored — ai o arquivo tem de existir.
  [ "$found" -ge 0 ]
}

@test "os treze declaram implementation, e o conjunto é exatamente treze inline" {
  # A contagem é exata dos dois lados. Um comando que perdesse a chave no meio
  # da conversão sairia da lista em silêncio, e é isso que a igualdade impede.
  local total vendored inline
  total="$(declared_implementations | wc -l | tr -d ' ')"
  vendored="$(declared_implementations | grep -c ' vendored$' || true)"
  inline="$(declared_implementations | grep -c ' inline$' || true)"
  [ "$total" -eq 13 ] || { echo "declaram implementation: $total (esperado 13)" >&2; return 1; }
  # Phase 46: o ultimo vendored (discuss-phase) virou inline — nenhum
  # wrapper le mais o runtime vendorizado.
  [ "$vendored" -eq 0 ] || { echo "vendored: $vendored (esperado 0)" >&2; return 1; }
  [ "$inline" -eq 13 ] || { echo "inline: $inline (esperado 13)" >&2; return 1; }
}

@test "um valor de implementation fora do vocabulário é erro de uso nomeado" {
  # Vocabulário fechado, no molde exato do wrap-family desconhecido que já
  # existe (cairn-wrap.py). Sem esta asserção, um typo viraria "não é wrapper".
  local dir
  dir="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/cairn-impl.XXXXXX")"
  {
    echo '---'
    echo 'description: does alpha'
    echo 'wraps: plan-phase'
    echo 'wrap-family: phase'
    echo 'implementation: banana'
    echo '---'
    echo
    echo 'Body.'
  } > "$dir/alpha.md"

  run bash "$WRAP" list --commands-dir "$dir" --json
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF 'alpha.md'
  echo "$output" | grep -qF 'banana'
}

# ---------------------------------------------------------------------------
# 7 — a garantia do research vira asserção (PLUG-05)
# ---------------------------------------------------------------------------

@test "a troca nao migra dado nenhum: nenhuma fase alheia, nenhum arquivo de milestone" {
  # "Nada em .planning/ nem .beads/ muda; é troca de plugin, não migração de
  # dados" é a garantia que o research repete em dois documentos. Aqui ela
  # deixa de ser frase — mas a asserção precisa dizer o que a frase quer dizer,
  # e não mais que isso.
  #
  # O que ela PROÍBE, e é onde ela morde: tocar o diretório de qualquer OUTRA
  # fase, tocar o arquivo de qualquer milestone arquivado, ou tocar o banco do
  # beads. Uma migração de dado real aterrissaria em pelo menos um dos três.
  #
  # O que ela PERMITE, nomeado um a um e nunca por padrão largo:
  #   - .planning/phases/37-troca-de-plugin/  — o trabalho desta fase;
  #   - ROADMAP.md, REQUIREMENTS.md, STATE.md — a escrituração que TODA fase
  #     move ao fechar (checkbox, tabela de cobertura, contadores). Medido em
  #     2026-08-12: o diff destes três contra a base da fase é exatamente isso.
  #   - .beads/issues.jsonl                   — o export passivo do tracker,
  #     que se move quando uma issue da fase abre ou fecha.
  #
  # A base é derivada, nunca digitada: o pai do PRIMEIRO commit que tocou o
  # diretório desta fase. Um merge-base contra o branch do milestone mediria a
  # fase 36 junto e ficaria vermelho por trabalho que não é desta fase — medido
  # em 2026-08-12, antes de a asserção ser corrigida.
  cd "$CAIRN_REPO_ROOT" || return 1
  local first base
  first="$(git log --reverse --format=%H \
           -- .planning/phases/37-troca-de-plugin 2>/dev/null | head -1)"
  [ -n "$first" ] || skip "a fase 37 ainda não tem commit próprio"
  base="$(git rev-parse "$first^" 2>/dev/null || true)"
  [ -n "$base" ] || skip "sem base de comparação"
  # A PONTA também é derivada, e tem que ser: o último commit que tocou o
  # diretório desta fase. `..HEAD` mediria toda fase posterior junto — a 38
  # abriu seu próprio diretório e o oráculo da 37 ficou vermelho por trabalho
  # que nunca prometeu não fazer (medido em 2026-08-12). A garantia é sobre a
  # troca de plugin, então a janela é a da troca.
  local tip
  tip="$(git log -1 --format=%H -- .planning/phases/37-troca-de-plugin \
         2>/dev/null || true)"
  [ -n "$tip" ] || skip "sem ponta de comparação"

  local offenders
  offenders="$(git diff --name-only "$base".."$tip" -- .planning .beads \
               | grep -v '^\.planning/phases/37-troca-de-plugin/' \
               | grep -v '^\.planning/\(ROADMAP\|REQUIREMENTS\|STATE\)\.md$' \
               | grep -v '^\.beads/issues\.jsonl$' || true)"
  [ -z "$offenders" ] || {
    echo "a fase 37 moveu arquivos que prometeu não tocar:" >&2
    echo "$offenders" >&2
    return 1
  }
}

@test "controle: o oraculo de imutabilidade morde mesmo" {
  # Sem este par, o teste acima passaria com o filtro largo demais — e um
  # filtro largo demais é como uma garantia vira frase de novo. Aqui um
  # caminho que a migração REAL teria tocado é submetido ao mesmo filtro, e
  # ele tem de sobreviver.
  local sample
  sample="$(printf '%s\n' \
    ".planning/phases/36-workflows-steps-e-agentes-falam-bd/36-01-SUMMARY.md" \
    ".planning/milestones/v1.5-ROADMAP.md" \
    ".beads/beads.db" \
    | grep -v '^\.planning/phases/37-troca-de-plugin/' \
      | grep -v '^\.planning/\(ROADMAP\|REQUIREMENTS\|STATE\)\.md$' \
      | grep -v '^\.beads/issues\.jsonl$')"
  [ "$(wc -l <<<"$sample" | tr -d ' ')" -eq 3 ] || {
    echo "o filtro do teste anterior deixaria passar uma migração de dados:" >&2
    echo "$sample" >&2
    return 1
  }
}
