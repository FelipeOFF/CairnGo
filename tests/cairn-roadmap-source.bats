#!/usr/bin/env bats
# cairn-roadmap-source.bats — o oraculo da FONTE DO ROTEIRO (CairnGo-9c0h.6).
#
# POR QUE ESTE ARQUIVO EXISTE. O roteiro do projeto morava em
# `.planning/ROADMAP.md`, e 12 scripts o liam. A v1.7 mudou a fonte para o bd
# e a conversao foi feita leitor a leitor — mas uma conversao sem oraculo e'
# uma asseracao valida no dia em que foi escrita e em nenhum outro. Sem este
# teste, o proximo refactor reintroduz uma leitura e a suite fica verde.
#
# O QUE ELE MEDE, E O QUE ELE DELIBERADAMENTE NAO MEDE. Contar MENCOES a
# ROADMAP.md seria medir a coisa errada: prosa que EXPLICA a regra das duas
# fontes menciona o arquivo sem ler nada, e um teste que a contasse puniria
# justamente a documentacao da mudanca. Mede-se LEITURA — a expressao que
# abre o arquivo.
#
# A DISCIPLINA E' A LISTA FECHADA, emprestada do teto D-01 em cairn-gsd.bats:
# toda leitura sobrevivente esta declarada aqui com a razao de sobreviver, e
# um arquivo fora da lista reprova. Declarar, nunca improvisar.

load 'helpers'

# Os UNICOS scripts que podem abrir ROADMAP.md, e por que cada um pode.
#
#   modo roteiro  — a regra das duas fontes: enquanto ha `.planning/ROADMAP.md`
#                   em disco ele e' a ENTRADA de um GSD por importar, e o
#                   leitor o consulta ANTES de cair no bd. Ler para comparar
#                   com o bd nao e' ler como verdade.
#   importacao    — o migrate le uma vez, que e' a razao de ele existir.
#   o GSD         — cairn-gsd-{init,state,check} SAO o binario GSD
#                   reimplementado, com paridade pinada por goldens. Eles leem
#                   .planning/*.md porque ELES SAO O GSD; converte-los
#                   quebraria o runtime que serve o unico caso que o escopo
#                   permite.
declare_allowed() {
  cat <<'EOF'
cairn-doctor.py     modo roteiro
cairn-status.py     modo roteiro
cairn-gate.py       modo roteiro
cairn-bookkeep.py   modo roteiro
cairn-reconcile.py  modo roteiro
cairn-trend.py      modo roteiro
cairn-migrate.py    importacao
cairn-gsd-init.py   o GSD reimplementado
cairn-gsd-state.py  o GSD reimplementado
cairn-gsd-check.py  o GSD reimplementado
EOF
}

# Uma linha LE quando carrega uma expressao que abre o arquivo. Comentario
# nao le; docstring nao le.
readers_by_file() {
  python3 - "$CAIRN_SCRIPTS_DIR" <<'PY'
import re, sys
from pathlib import Path
READ = re.compile(r'(read_lines|read_text|\.read_text|open|\.is_file|\.exists)\s*\(')
for p in sorted(Path(sys.argv[1]).glob("*.py")):
    n = 0
    for line in p.read_text().splitlines():
        code = line.split("#", 1)[0]
        if "ROADMAP.md" not in code:
            continue
        if code.lstrip().startswith(('"""', "'''")):
            continue
        if READ.search(code) or re.search(r'/\s*"ROADMAP\.md"', code):
            n += 1
    if n:
        print(f"{p.name} {n}")
PY
}

@test "so os scripts declarados abrem ROADMAP.md, e cada um tem uma razao" {
  local allowed undeclared=""
  allowed="$(declare_allowed | awk '{print $1}')"

  while read -r name count; do
    [ -z "$name" ] && continue
    if ! grep -qx -- "$name" <<<"$allowed"; then
      undeclared="$undeclared$name: $count leitura(s) de ROADMAP.md, sem razao declarada"$'\n'
    fi
  done < <(readers_by_file)

  if [ -n "$undeclared" ]; then
    printf 'scripts lendo o roteiro fora da lista fechada:\n%s' "$undeclared" >&2
    printf 'A fonte do roteiro e o bd (cairn_source.py). Se a leitura for\n' >&2
    printf 'legitima — a regra das duas fontes, ou importacao — declare-a em\n' >&2
    printf 'declare_allowed() com a razao, em vez de deixa-la muda.\n' >&2
    return 1
  fi
}

# CONTROLE NEGATIVO. Um teste de ausencia que nunca viu presenca nao prova
# nada: se o detector estivesse quebrado, o teste acima passaria vazio e
# pareceria sucesso. Este exercita o detector contra uma leitura forjada.
@test "controle negativo: o detector encontra uma leitura recem-plantada" {
  local sandbox="$BATS_TEST_TMPDIR/scripts"
  mkdir -p "$sandbox"
  cat > "$sandbox/cairn-forjado.py" <<'PY'
# esta mencao a ROADMAP.md e' comentario, e NAO deve contar
"""nem esta, em docstring: ROADMAP.md"""
for line in read_lines(planning_dir / "ROADMAP.md"):
    pass
PY

  # uma leitura, nem uma a mais: o comentario e a docstring do mesmo arquivo
  # mencionam ROADMAP.md e nao podem entrar na conta
  local out
  out="$(CAIRN_SCRIPTS_DIR="$sandbox" readers_by_file)"
  [ "$out" = "cairn-forjado.py 1" ]
}

@test "cairn_source e' a fonte, e ela nao le markdown nenhum" {
  # A fonte unica nao pode ter fallback para documento: um fallback silencioso
  # e' a volta da segunda verdade por outro nome.
  run grep -c "ROADMAP.md" "$CAIRN_SCRIPTS_DIR/cairn_source.py"
  # mencoes em prosa sao esperadas (o modulo explica de onde veio), leituras nao
  local reading
  reading="$(readers_by_file | grep "^cairn_source.py " || true)"
  [ -z "$reading" ]
}
