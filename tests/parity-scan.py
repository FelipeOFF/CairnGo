#!/usr/bin/env python3
"""parity-scan.py — toda chamada `gsd_run` de um corpus que o dispatcher NAO
roteia (PAR-02).

Ferramenta de teste, fora dos contratos: o guard de paridade da fase 38
consome a saída em vez de manter uma lista paralela de rotas mortas.

Usage:
    parity-scan.py --contracts <dir> --corpus <dir>

Imprime uma linha `caminho:linha<TAB>token` por chamada não resolvida, e nada
quando o corpus inteiro resolve. Exit 0 sempre que a varredura completa (é
ferramenta de dado, não gate — quem julga é o teste); exit 2 em erro de uso.

A tabela spelling→verbo é reconstruída da MESMA fonte que build_routes() do
cairn-gsd.py usa — `contracts.json` `.verbs` mais os `spellings[]` do arquivo
de cada família. Uma segunda tabela aqui concordaria com a primeira mesmo
quando as duas estivessem erradas, e concordância lida como saúde é o defeito
que este repositório inteiro existe para pegar.

DUAS regras de leitura, e as duas saíram de falso positivo medido em
2026-08-12:

1. Menção em prosa não é chamada. `gsd_run` dentro de um trecho de código
   inline (número ímpar de crases antes dele na linha) é documentação; só a
   ocorrência fora de crase — bloco cercado ou linha de shell — é chamada.
   Sem isso, `` `gsd_run query`, from ``  vira "rota morta".
2. Token carrega pontuação de `$( )` e de prosa. `$(gsd_run query state.load)`
   entrega `state.load)`; a normalização tira crase, parênteses, vírgula,
   ponto e aspas das pontas antes de comparar. Sem isso,
   `gsd_run query verification status` — que RESOLVE, pelo spelling com
   espaço — seria acusado.
"""
import json
import os
import re
import sys

USAGE = "usage: parity-scan.py --contracts <dir> --corpus <dir>"
EXIT_OK = 0
EXIT_USAGE = 2

CLEAN = re.compile(r"^[a-z][a-z0-9._-]*$")
TRIM = "`'\"()[]{},;:. \\"


def die(msg):
    sys.stderr.write(msg.rstrip("\n") + "\n")
    sys.exit(EXIT_USAGE)


def build_routes(contracts_dir):
    """spelling -> verbo, de contracts.json mais os spellings[] das familias."""
    agg_path = os.path.join(contracts_dir, "contracts.json")
    try:
        with open(agg_path, encoding="utf-8") as fh:
            agg = json.load(fh)
    except (OSError, ValueError) as exc:
        die("contracts.json ilegivel em %s: %s" % (contracts_dir, exc))
    verbs = agg.get("verbs")
    if not isinstance(verbs, dict) or not verbs:
        die("contracts.json sem indice .verbs utilizavel em %s" % contracts_dir)
    docs = {}
    routes = {}
    for verb, meta in verbs.items():
        fname = meta.get("file")
        if not fname:
            die("entrada de verbo sem file em contracts.json: %s" % verb)
        if fname not in docs:
            with open(os.path.join(contracts_dir, fname), encoding="utf-8") as fh:
                docs[fname] = json.load(fh)
        entry = next((v for v in docs[fname].get("verbs", [])
                      if v.get("verb") == verb), None)
        if entry is None:
            die("verbo '%s' indexado mas ausente de %s" % (verb, fname))
        for spelling in entry.get("spellings") or []:
            routes[spelling] = verb
    return routes


def normalize(token):
    """Token sem a pontuacao que $( ) e prosa grudam nas pontas."""
    return token.strip(TRIM)


def in_inline_code(line, pos):
    """A posicao esta dentro de um trecho `codigo inline`?"""
    return line[:pos].count("`") % 2 == 1


def unresolved_in_line(line, routes, max_tokens):
    """Os tokens de chamada da linha que nenhum spelling resolve."""
    found = []
    for match in re.finditer(r"gsd_run\s+", line):
        if in_inline_code(line, match.start()):
            continue
        raw = line[match.end():].split()
        tokens = []
        for token in raw[:max_tokens]:
            norm = normalize(token)
            if not CLEAN.match(norm):
                break
            tokens.append(norm)
        if not tokens:
            continue
        if any(" ".join(tokens[:n]) in routes
               for n in range(len(tokens), 0, -1)):
            continue
        found.append(" ".join(tokens))
    return found


def scan(corpus_dir, routes):
    max_tokens = max(len(s.split()) for s in routes)
    rows = []
    for base, _dirs, files in os.walk(corpus_dir):
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = os.path.join(base, name)
            with open(path, encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    if "gsd_run() {" in line:
                        continue
                    for token in unresolved_in_line(line, routes, max_tokens):
                        rows.append("%s:%d\t%s" % (path, lineno, token))
    return rows


def main(argv):
    contracts = corpus = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--contracts" and i + 1 < len(argv):
            contracts = argv[i + 1]
            i += 2
        elif arg == "--corpus" and i + 1 < len(argv):
            corpus = argv[i + 1]
            i += 2
        else:
            die("argumento desconhecido '%s'\n%s" % (arg, USAGE))
    if not contracts or not corpus:
        die(USAGE)
    if not os.path.isdir(contracts):
        die("--contracts nao e diretorio: %s" % contracts)
    if not os.path.isdir(corpus):
        die("--corpus nao e diretorio: %s" % corpus)
    for row in scan(corpus, build_routes(contracts)):
        print(row)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
