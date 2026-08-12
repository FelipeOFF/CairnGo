#!/usr/bin/env python3
"""cairn-preamble — the runtime-resolution line of the vendored prompt layer.

ESTE SCRIPT ESCREVE SOB `cairn/gsd/` — E SÓ NAS LINHAS DE PREÂMBULO DOS
CAMINHOS REGISTRADOS EM `cairn/gsd-adaptations.json`.

Isso o torna o PRIMEIRO script da casa a escrever naquela árvore, e por isso a
declaração vem alta, no molde do docstring de rede de cairn-inventory.py. Os
quatro irmãos do dispatcher (cairn-gsd.py, -init, -state, -check) declaram
`cairn/gsd/` SOMENTE-LEITURA e continuam verdadeiros: nenhum deles passa a
escrever. Este escreve, e só aqui:

    - uma linha por arquivo, a do preâmbulo de resolução de runtime;
    - apenas em caminho previamente registrado em cairn/gsd-adaptations.json;
    - nunca sob cairn/gsd/contracts/**, nunca cairn/gsd/MANIFEST.json;
    - write-only-when-changed: uma reescrita byte-idêntica não toca o mtime.

O QUE "PREÂMBULO" SIGNIFICA AQUI (armadilha SHIM-HOMÔNIMO)
----------------------------------------------------------
"Preâmbulo" é o bloco de RESOLUÇÃO DE RUNTIME: a primeira linha dentro de um
fence ```bash que descobre onde mora o executável do GSD e define `gsd_run`.
São 34 blocos na árvore vendorizada, em dois sabores upstream.

NÃO é o `summary.shim_matches` de cairn/gsd/MANIFEST.json, que tem oito
entradas e descreve o par comando↔skill de cada workflow. Confundir os dois
custa 16-versus-34 arquivos a quem for procurar.

POR QUE A FORMA MUDA (fase 36, D-01)
------------------------------------
A forma upstream resolve um runtime node (`gsd-core/bin/gsd-tools.cjs`) tentando
até 19 diretórios de host e termina em `exit 1` sugerindo instalar o pacote
externo. Medido na fase 36: nenhum dos 169 arquivos vendorizados mencionava o
binário python deste repo, então o caminho que o usuário executa e o caminho
que os testes das fases 33-35 provam eram DOIS. A fase 37 remove o plugin
externo; um preâmbulo que ainda o resolvesse entregaria `exit 1` ao usuário.

A forma nova é UMA para os 34 (as duas variantes upstream colapsam): a cadeia
de 19 diretórios existia para achar um runtime FORA do repo, e o binário do
repo não tem essa incerteza. O append de PATH em `$CLAUDE_ENV_FILE`, que só a
variante longa fazia, sai junto — ele exportava o diretório do runtime antigo.

Usage:
    cairn-preamble.py --print-form
    cairn-preamble.py list   [--root <dir>] [--registry <path>] [--json]
    cairn-preamble.py check  [<path>...] [--root <dir>] [--registry <path>]
    cairn-preamble.py apply  [<path>...] [--root <dir>] [--registry <path>]

Commands:
    --print-form  A linha canônica, e só ela, sem newline. É a FONTE ÚNICA da
                  forma: nenhum outro arquivo carrega uma segunda cópia
                  autoritativa, e os testes extraem daqui.
    list          Cada caminho registrado e seu estado: `new`, `old` ou
                  `none` (registrado, sem linha de preâmbulo — é o caso dos
                  arquivos que entram no registro por adaptação de conteúdo).
    check         Exit 3 (stale) quando algum registrado ainda carrega a forma
                  antiga, com o unified diff no stdout. Mesmo significado que
                  cairn-map.py --check e cairn-wrap.py --check dão ao 3.
    apply         Substitui a linha, write-only-when-changed.

Exit:
    0  ok
    2  uso, ou recusa nominal (caminho fora de cairn/gsd/, caminho protegido,
       caminho ausente do registro)
    3  stale (`check` achou forma antiga)
"""

import argparse
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
# 3 = stale, o mesmo significado que cairn-map.py --check e cairn-wrap.py
# --check já dão ao 3.
EXIT_STALE = 3

TAG_PREFIX = "[cairn-preamble]"

VENDOR_RELDIR = "cairn/gsd"
REGISTRY_RELPATH = "cairn/gsd-adaptations.json"
PROTECTED_PREFIXES = ("contracts/",)
PROTECTED_PATHS = ("MANIFEST.json",)

# O marcador da forma ANTIGA: a variável que nomeia o runtime node. Grafia
# literal, e é por PREFIXO de linha que a detecção acontece — os 34 blocos
# moram em linhas diferentes de arquivos diferentes, então número de linha
# não serve de âncora.
OLD_MARKER = '_GSD_SHIM_NAME='

# O marcador da forma NOVA, mesmo contrato de prefixo.
NEW_MARKER = 'CAIRN_GSD="${CAIRN_GSD:-}";'

# A FORMA. Fonte única; qualquer outra cópia é derivada desta por
# --print-form. Uma linha, posicionada onde a antiga estava (primeira linha
# dentro do fence bash).
#
# A cadeia de resolução tem quatro elos e nada mais: (1) $CAIRN_GSD já
# exportado, o escape deliberado; (2) $CLAUDE_PROJECT_DIR; (3) o toplevel do
# git a partir do cwd; (4) o $PWD. Não achando executável em nenhum, falha
# NOMEADA — o último caminho tentado e o comando que cria o fato — e exit 1,
# a doutrina de cairn-gsd-state.py:176-178. Nenhum `node`, nenhum `npx`,
# nenhuma menção ao instalador do pacote externo: a fase 37 mata esse comando
# e um preâmbulo que o sugira manda o usuário para um caminho morto.
#
# Os exits de cairn-gsd.sh (0/1 por contrato do verbo, 2 uso do dispatcher,
# 4 família não servida) chegam ao workflow sem tradução, porque gsd_run
# apenas exec'a o wrapper.
FORM = (
    'CAIRN_GSD="${CAIRN_GSD:-}"; '
    'if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; '
    'for _cg_root in "${CLAUDE_PROJECT_DIR:-}" '
    '"$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do '
    '[ -n "$_cg_root" ] || continue; '
    '_cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; '
    'if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; '
    'if [ ! -x "${CAIRN_GSD:-}" ]; then '
    'echo "ERROR: cairn-gsd.sh not found (last path tried: '
    '${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that '
    'lives in the repo. Run it from inside the CairnGo checkout, or export '
    'CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; '
    'export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }'
)

USAGE = (
    "usage: cairn-preamble.py --print-form\n"
    "       cairn-preamble.py list  [--root <dir>] [--registry <path>] "
    "[--json]\n"
    "       cairn-preamble.py check [<path>...] [--root <dir>] "
    "[--registry <path>]\n"
    "       cairn-preamble.py apply [<path>...] [--root <dir>] "
    "[--registry <path>]"
)


def die(msg, code=EXIT_USAGE):
    print(f"{TAG_PREFIX} error: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_root(explicit):
    """Raiz do projeto. O precedente da casa é CLAUDE_PROJECT_DIR
    (cairn-inventory.py resolve_corpus); o toplevel do git entra depois, para
    que o script funcione de qualquer subdiretório do checkout."""
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=False)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except OSError:
        pass
    return Path(".").resolve()


def registry_path(root, explicit):
    if explicit:
        return Path(explicit).resolve()
    return root / REGISTRY_RELPATH


def load_registry(path):
    """O registro versionado. Ausente = vazio: um checkout sem adaptação
    nenhuma é estado legítimo, e é exatamente o que a Task 1 da fase 36
    deixa no disco."""
    if not path.is_file():
        return {"schema_version": 1, "adaptations": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        die(f"registro de adaptações ilegível em {path}: {e}")
    if not isinstance(data.get("adaptations"), list):
        die(f"registro de adaptações em {path} não tem a lista adaptations")
    return data


def registered_paths(registry):
    return [e["path"] for e in registry["adaptations"] if e.get("path")]


def to_rel(root, raw):
    """Caminho na grafia do registro (relativa à raiz vendorizada, igual a
    files[] do MANIFEST), ou None quando ele não mora sob cairn/gsd/.

    Aceita as duas grafias que um humano digita: a do registro
    (`gsd-core/workflows/fast.md`) e a do repositório
    (`cairn/gsd/gsd-core/workflows/fast.md`)."""
    s = raw.strip()
    if os.path.isabs(s):
        try:
            return str(Path(s).resolve().relative_to(
                (root / VENDOR_RELDIR).resolve()))
        except (ValueError, OSError):
            return None
    while s.startswith("./"):
        s = s[2:]
    prefix = VENDOR_RELDIR + "/"
    if s.startswith(prefix):
        return s[len(prefix):]
    if s.startswith("..") or s.startswith("cairn/"):
        return None
    return s


def refuse_unless_writable(root, raw, allowed):
    """Recusa nominal em três níveis, molde cairn-migrate.py:1861-1863.

    A mensagem diz o caminho E que a adaptação se registra ANTES de existir
    no disco: registrar depois de editar deixa o oráculo de bytes cego, e
    registrar sem editar o deixa vermelho (ele exige divergência de todo
    caminho registrado)."""
    rel = to_rel(root, raw)
    if rel is None:
        die(f"recusando {raw} — caminho fora de {VENDOR_RELDIR}/; este "
            "script só escreve na árvore vendorizada")
    if rel in PROTECTED_PATHS or rel.startswith(PROTECTED_PREFIXES):
        die(f"recusando {VENDOR_RELDIR}/{rel} — cairn-preamble nunca escreve "
            "em contracts/** nem em MANIFEST.json")
    if rel not in allowed:
        die(f"recusando {VENDOR_RELDIR}/{rel} — caminho ausente de "
            f"{REGISTRY_RELPATH}; a adaptação se registra ANTES de existir no "
            "disco, na mesma task que a aplica")
    return rel


def find_preamble(lines):
    """Índice da linha de preâmbulo e sua natureza.

    Detecção por PREFIXO de marcador, nunca por número de linha."""
    for i, line in enumerate(lines):
        if line.startswith(OLD_MARKER):
            return i, "old"
        if line.startswith(NEW_MARKER):
            return i, "new"
    return -1, "none"


def read_lines(path):
    text = path.read_text(encoding="utf-8")
    return text, text.split("\n")


def rewrite(text, lines, idx):
    lines = list(lines)
    lines[idx] = FORM
    return "\n".join(lines)


def targets(root, args, registry):
    allowed = set(registered_paths(registry))
    if args.paths:
        return [refuse_unless_writable(root, raw, allowed)
                for raw in args.paths]
    return sorted(allowed)


def do_list(args):
    root = resolve_root(args.root)
    registry = load_registry(registry_path(root, args.registry))
    rows = []
    for rel in sorted(registered_paths(registry)):
        path = root / VENDOR_RELDIR / rel
        if not path.is_file():
            rows.append({"path": rel, "state": "missing"})
            continue
        _, lines = read_lines(path)
        _, state = find_preamble(lines)
        rows.append({"path": rel, "state": state})
    counts = {}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    if args.json:
        print(json.dumps({"root": str(root), "entries": rows,
                          "counts": counts}, indent=2, sort_keys=True))
    else:
        for row in rows:
            print(f"{row['state']:>7}  {row['path']}")
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"{TAG_PREFIX} {len(rows)} registrado(s): {summary or 'vazio'}")
    sys.exit(EXIT_OK)


def do_check(args):
    root = resolve_root(args.root)
    registry = load_registry(registry_path(root, args.registry))
    stale = []
    for rel in targets(root, args, registry):
        path = root / VENDOR_RELDIR / rel
        if not path.is_file():
            die(f"caminho registrado ausente do disco: {VENDOR_RELDIR}/{rel}")
        text, lines = read_lines(path)
        idx, state = find_preamble(lines)
        if state != "old":
            continue
        stale.append(rel)
        updated = rewrite(text, lines, idx)
        sys.stdout.writelines(difflib.unified_diff(
            text.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"{VENDOR_RELDIR}/{rel} (no disco)",
            tofile=f"{VENDOR_RELDIR}/{rel} (forma canônica)"))
    if stale:
        print(f"{TAG_PREFIX} {len(stale)} arquivo(s) ainda na forma antiga — "
              "rode `cairn-preamble.sh apply`", file=sys.stderr)
        sys.exit(EXIT_STALE)
    print(f"{TAG_PREFIX} ✓ todo caminho registrado está na forma canônica")
    sys.exit(EXIT_OK)


def do_apply(args):
    root = resolve_root(args.root)
    registry = load_registry(registry_path(root, args.registry))
    changed, already, without = [], [], []
    for rel in targets(root, args, registry):
        path = root / VENDOR_RELDIR / rel
        if not path.is_file():
            die(f"caminho registrado ausente do disco: {VENDOR_RELDIR}/{rel}")
        text, lines = read_lines(path)
        idx, state = find_preamble(lines)
        if state == "none":
            without.append(rel)
            continue
        updated = rewrite(text, lines, idx)
        # Uma reescrita byte-idêntica ainda é uma escrita: só toca o arquivo
        # quando o conteúdo de fato difere, para o mtime ficar parado num
        # no-op (molde cairn-wrap.py:596-599).
        if updated == text:
            already.append(rel)
            continue
        path.write_text(updated, encoding="utf-8")
        changed.append(rel)
    print(f"{TAG_PREFIX} {len(changed)} trocado(s), {len(already)} já na "
          f"forma canônica, {len(without)} registrado(s) sem preâmbulo")
    for rel in without:
        print(f"{TAG_PREFIX} sem preâmbulo (adaptação de conteúdo): {rel}")
    sys.exit(EXIT_OK)


def build_parser():
    p = argparse.ArgumentParser(prog="cairn-preamble.py", add_help=True,
                                description=USAGE)
    p.add_argument("--print-form", action="store_true")
    sub = p.add_subparsers(dest="command")
    for name in ("list", "check", "apply"):
        s = sub.add_parser(name)
        s.add_argument("paths", nargs="*")
        s.add_argument("--root")
        s.add_argument("--registry")
        if name == "list":
            s.add_argument("--json", action="store_true")
    return p


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--print-form":
        sys.stdout.write(FORM)
        sys.exit(EXIT_OK)
    args = build_parser().parse_args(argv)
    if args.print_form:
        sys.stdout.write(FORM)
        sys.exit(EXIT_OK)
    if args.command == "list":
        do_list(args)
    elif args.command == "check":
        do_check(args)
    elif args.command == "apply":
        do_apply(args)
    else:
        print(USAGE, file=sys.stderr)
        sys.exit(EXIT_USAGE)


if __name__ == "__main__":
    main()
