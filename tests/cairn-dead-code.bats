#!/usr/bin/env bats
# cairn-dead-code.bats — a guarda contra simbolo orfao.
#
# POR QUE ESTE ARQUIVO EXISTE. Uma varredura pontual, feita 2026-08-14,
# encontrou NOVE simbolos de topo definidos nos scripts e referenciados por
# nada: duas funcoes publicas do cairn_source (que chegaram a ser
# documentadas como API viva para outros agentes na mesma sessao), tres
# constantes do doctor criadas para entrar em mensagens que nunca as
# consumiram, e quatro sobras de refactor. Nenhuma delas quebrava nada, e e'
# exatamente por isso que sobreviveram a sete releases.
#
# O QUE ELE MEDE, E A DISTINCAO QUE CUSTOU CARO. Referencia de TESTE nao e'
# uso: um simbolo citado so' em tests/ esta morto em producao e vivo apenas
# na sua propria testemunha. A primeira versao deste detector contava as
# duas juntas e teria dado verde para essa classe inteira. `plan_counts`
# provou o ponto na hora: era referenciado so' pelo demo() do cairn_source,
# e virou orfao no instante em que o demo saiu.
#
# A DISCIPLINA E' A LISTA FECHADA, a mesma do teto D-01 em cairn-gsd.bats e
# do oraculo em cairn-roadmap-source.bats: um orfao tolerado esta declarado
# aqui com a razao de existir sem chamador. Declarar, nunca improvisar.

load 'helpers'

# Orfaos TOLERADOS, um por linha, no formato `arquivo.py:simbolo  razao`.
# Vazio hoje, e isso e' o estado alvo — uma entrada nova exige a razao junto.
declare_tolerated() {
  cat <<'EOF'
EOF
}

# Simbolos de topo sem NENHUMA referencia de producao nem de teste.
orphans() {
  python3 - "$CAIRN_SCRIPTS_DIR" <<'PY'
import ast, re, sys
from pathlib import Path

scripts = Path(sys.argv[1])
root = scripts.parent.parent          # a raiz do repo, a partir de cairn/scripts

def collect(pats):
    out = {}
    for pat in pats:
        for p in root.glob(pat):
            if p.is_file():
                out[p] = p.read_text(errors="replace")
    return out

PROD = collect(["cairn/scripts/*.py", "cairn/scripts/*.sh", "cairn/hooks/*.sh",
                "cairn/commands/*.md", "cairn/skills/**/*.md",
                "cairn/capability/**/*.py", "cairn/capability/**/*.sh",
                "cairn/capability/**/*.json", ".github/workflows/*.yml"])
TEST = collect(["tests/*.bats", "tests/*.bash"])
DUNDER = re.compile(r"^__.*__$")

for p in sorted(scripts.glob("*.py")):
    try:
        tree = ast.parse(p.read_text())
    except SyntaxError:
        continue
    for node in tree.body:
        names = ([node.name]
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef))
                 else [t.id for t in getattr(node, "targets", [])
                       if isinstance(t, ast.Name)])
        for name in names:
            # dunder e privados curtos nao sao superficie
            if DUNDER.match(name) or (name.startswith("_") and len(name) < 3):
                continue
            rx = re.compile(r"\b" + re.escape(name) + r"\b")
            prod = sum(1 for f, t in PROD.items() for m in rx.finditer(t)
                       if not (f == p
                               and t[:m.start()].count("\n") + 1 == node.lineno))
            if prod:
                continue
            if any(rx.search(t) for t in TEST.values()):
                continue          # vivo no teste — outro caso, outro teste
            print(f"{p.name}:{name}")
PY
}

@test "nenhum simbolo orfao fora da lista declarada" {
  local tolerated undeclared=""
  tolerated="$(declare_tolerated | awk '{print $1}')"

  while read -r entry; do
    [ -z "$entry" ] && continue
    if ! grep -qx -- "$entry" <<<"$tolerated"; then
      undeclared="$undeclared$entry"$'\n'
    fi
  done < <(orphans)

  if [ -n "$undeclared" ]; then
    printf 'simbolos sem chamador algum, e sem razao declarada:\n%s' \
      "$undeclared" >&2
    printf 'Apague-os, ou declare cada um em declare_tolerated() com a\n' >&2
    printf 'razao de existir sem chamador. Um simbolo que nada referencia\n' >&2
    printf 'nao quebra nada, e foi assim que nove deles atravessaram sete\n' >&2
    printf 'releases.\n' >&2
    return 1
  fi
}

# CONTROLE NEGATIVO, e ele reproduz a ARVORE, nao so' o arquivo. Um sandbox
# solto deixa a lista de producao vazia, e ai TODO simbolo vira orfao por
# construcao — o controle passaria provando apenas que a funcao enxerga
# `def`, nunca que ela distingue referenciado de orfao. Com `cairn/scripts/`
# montado de verdade, as duas metades da logica sao exercitadas: quem tem
# chamador some da lista, quem nao tem aparece.
@test "controle negativo: detecta o orfao E poupa o que tem chamador" {
  local sandbox="$BATS_TEST_TMPDIR/repo/cairn/scripts"
  mkdir -p "$sandbox"
  cat > "$sandbox/cairn-forjado.py" <<'PY'
def tem_chamador():
    return 1


def sem_chamador():
    return 2
PY
  # um segundo arquivo de PRODUCAO chama a primeira — e' o que deve salva-la
  cat > "$sandbox/cairn-consumidor.py" <<'PY'
from cairn_forjado import tem_chamador
print(tem_chamador())
PY

  local out
  out="$(CAIRN_SCRIPTS_DIR="$sandbox" orphans | sort | tr '\n' ' ')"
  [ "$out" = "cairn-forjado.py:sem_chamador " ]
}
