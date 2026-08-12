#!/usr/bin/env python3
"""cairn-inventory — o inventário do corpus GSD na tag pinada, sítio a sítio.

WHY THIS EXISTS
---------------
Nenhuma fase do milestone v1.6 pode ser orçada sobre número que não reproduz.
Este comando é a fonte dos números que as fases seguintes citam: cada chamada
`gsd_run` no corpus da tag, com arquivo, linha, escopo e verbo — sob UMA
métrica declarada, a regex larga (BROAD_RE) que cobre `query` e os
subcomandos top-level. O universo de verbos que ele emite é o insumo direto
dos contratos por verbo.

ESTE SCRIPT FALA COM A REDE NA PRIMEIRA EXECUÇÃO — E SÓ NELA
------------------------------------------------------------
A convenção que o cairn-review.py estabeleceu: a rede vive num arquivo que a
declara em voz alta. Aqui ela existe para UMA coisa: `git clone --depth 1
--branch v1.10.0` do upstream para um cache local fora do controle de versão
(D-01). Com o cache válido presente, a execução é 100% offline — nenhum
socket, nenhum fetch. E "válido" é verificado, nunca presumido: o HEAD do
cache é comparado com o commit pinado da tag (TAG_COMMIT) em TODA execução,
hit ou clone fresco. Cache cujo HEAD diverge morre com exit 6 nomeando os
dois shas — a doutrina do review: cache sem o commit verificado é pior que
cache nenhum, porque parece corpus e não é.

A medição nunca lê ~/.claude nem qualquer runtime instalado: o corpus é
exclusivamente o clone cacheado da tag (source com source — risco 12 do
research: ruído de instalação infla qualquer comparação com o instalado).

Usage:
    cairn-inventory.py [--json] [--cache-dir <dir>] [--source <url|path>]
                       [--expect-commit <sha>] [--refresh]
    cairn-inventory.py closure [--json] [--write <path>] [flags de corpus]
    cairn-inventory.py vendor [--manifest <path>] [--dest <dir>]
                       [flags de corpus]

SUBCOMANDOS DO TRANSPLANTE
--------------------------
`closure` emite o fecho transitivo dos workflows do cairn sobre o corpus
pinado — a lista de inclusão do vendoring — e a grava como manifest com
`--write`, byte-idêntico à saída de `--json` (mesma serialização da casa).
`vendor` copia exatamente os arquivos do manifest, do cache verificado para
o destino, arquivo a arquivo (nunca por diretório inteiro), e reconfere
cada cópia contra o cache antes de sair. Os dois resolvem o corpus pelo
mesmo ensure_corpus da invocação flat: corpus não verificado nunca é lido.

Exit codes:
    0  ok — o corpus foi medido.
    2  usage — flag desconhecida ou valor faltando; no vendor, também o
       manifest ausente no caminho dado.
    5  dependência indisponível — git ausente, ou o clone falhou e não há
       cache para cair.
    6  corpus inválido — o HEAD do cache não confere com o commit esperado
       da tag. O inventário nunca mede corpus não verificado. No closure,
       também um SKILL.md do fecho prometendo shim fora da lista; no
       vendor, manifest cujo source.commit diverge do commit esperado ou
       cópia que não bate byte a byte com o cache.

MEASURED VERSUS ASSUMED
-----------------------
MEASURED (2026-08-10, contra o cache do clone da tag v1.10.0, HEAD
68a04ccf8ef74803bdb651e12c3b85b218bbccdf, cada número com o comando ao lado):
  - TAG_COMMIT: a tag é LIGHTWEIGHT. `git ls-remote
    https://github.com/open-gsd/gsd-core refs/tags/v1.10.0
    'refs/tags/v1.10.0^{}'` devolveu só a linha da tag, nenhuma linha peeled
    — o sha da tag É o commit, e `git -C <cache> rev-parse HEAD` confirma.
  - workflows8: 189 sítios (reproduz o research exato) e 59 verbos distintos
    (o research balizou 60-61; a normalização da grafia dupla que este
    inventário fixa — `query verification status` == `verification.status`,
    um verbo só — mede 59). Comando:
    `cairn-inventory.sh --json | jq '.summary.workflows8'`.
  - agents: 65 sítios / 42 verbos sobre AGENTS_SCOPE (o research mediu 64/42
    sobre "12 agentes despachados" sem registrar o comando; a lista declarada
    decide). Comando: `cairn-inventory.sh --json | jq '.summary.agents'`.
  - AGENTS_SCOPE (16 nomes): derivada pela interseção mecânica entre os .md
    sob agents/ e os nomes referenciados pelos 8 workflows. Comando, rodado
    na raiz do cache:
      for f in agents/*.md; do n="$(basename "$f" .md)";
        for w in discuss-phase plan-phase execute-phase verify-work quick \
                 fast autonomous debug; do
          grep -qw "$n" "gsd-core/workflows/$w.md" && echo "$n"; done;
      done | sort -u
    (o resultado é idêntico incluindo os subdiretórios de steps/modes no
    grep). Divergência com o research anotada: o fecho de 13 do research é
    exatamente esta lista menos o trio ui-* (gsd-ui-auditor 457 +
    gsd-ui-checker 341 + gsd-ui-researcher 380 = 1.178 linhas, a diferença
    entre as 9.900 linhas dos 16 e as 8.722 dos 13).
  - calibração: 534 chamadas / 116 verbos no corpus, exato com o research.
    Comando: `grep -rhoE 'gsd_run query [a-z][a-z0-9._-]+'
    gsd-core/workflows commands | wc -l` e
    `... | awk '{print $3}' | sort -u | wc -l`.
  - loop render-hooks: 17 sítios nos 8, exato com o research. Comando:
    `cairn-inventory.sh --json | jq '.summary.loop_render_hooks_sites'`.
  - contabilidade workflows8: 651 = 189 + 460 + 2, exato com o research.
    Comando: `cairn-inventory.sh --json | jq '.accounting.workflows8'`.
    Veredito humano sobre os 2 other, sítio a sítio: os dois são prosa —
    gsd-core/workflows/execute-phase.md:378 ("independent `gsd_run` calls —
    nothing it reads...") e gsd-core/workflows/autonomous.md:81 ("This block
    must stay AFTER the launcher preamble... because it calls `gsd_run`"),
    menções em backtick dentro de comentário, não chamadas.
  - contabilidade agents: 227 = 65 + 160 + 2. Comando:
    `cairn-inventory.sh --json | jq '.accounting.agents'`. Veredito humano
    sobre os 2 other: prosa também — agents/gsd-debug-session-manager.md:337
    e agents/gsd-planner.md:658, menções em backtick.
  - fecho do transplante (closure): 171 arquivos / 29.957 linhas
    (2026-08-10). Comando: `cairn-inventory.sh closure --json |
    jq '.totals'`. Divergência com os 160/28.071 do research §2.1 anotada
    ao lado do medido, que vence: AGENTS_SCOPE tem 16 nomes onde o research
    somou 13 (o trio ui-*), os shims 1:1 são 16 arquivos — o par
    commands/gsd/<w>.md + skills/gsd-<w>/SKILL.md por workflow, onde o
    research contou só os 8 SKILL.md —, o LICENSE entra como entrada da
    própria lista, e os 3 contexts/66 linhas do research ficam FORA:
    nenhum arquivo do corpus referencia caminho contexts/*.md (verificado
    com `grep -rn 'contexts/' --include='*.md'` sobre o cache inteiro,
    zero hits) — a inclusão deles no research era fiat, não fecho.

ASSUMED (não medido):
  - Que a fatia de steps/modes incluída no escopo workflows8 coincide com a
    que o research usou nos 189: o número reproduziu exato, o que sustenta a
    coincidência mas não a prova.
  - Que AGENTS_SCOPE é o fecho de dispatch REAL: a interseção é por menção
    de nome com fronteira de palavra, não por chamada Agent() comprovada — o
    dispatch nos workflows é prosa, sem marcador mecânico único.
  - Que os subcomandos não-query da métrica larga (loop, check,
    run-with-timeout, graphify e afins) esgotam as formas de chamada:
    other == 2 por fatia é evidência de completude, não prova.
  - Que o layout de shims descoberto no clone (commands/gsd/<w>.md e
    skills/gsd-<w>/SKILL.md) cobre todos os workflows do fecho: os pares
    existem para os 8 hoje (shim_matches sem lista vazia no summary do
    closure), mas um rename upstream mudaria o match sem erro fatal — o
    zero-match é registrado, não reprovado.
  - Que a regex do fecho (REF_RE, references/templates/contexts por
    caminho .md) esgota as formas de referência do corpus: contexts/ com
    zero hits é evidência de que nada mais aponta para fora do fecho, não
    prova.
"""
import argparse
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
# 5 = uma dependência deste script está indisponível: o git não existe, ou o
# clone falhou e não há cache válido para cair. Mesmo código que o
# cairn-review.py usa para "o helper que eu chamo não respondeu".
EXIT_NO_HELPER = 5
# 6 = o corpus existe mas não é o corpus: o HEAD do cache diverge do commit
# pinado da tag. Código próprio porque a resposta certa do chamador é
# diferente (apagar o cache / --refresh), e porque medir por cima seria
# publicar número de um corpus que ninguém verificou.
EXIT_BAD_CORPUS = 6

SOURCE_URL = "https://github.com/open-gsd/gsd-core"
TAG = "v1.10.0"
# O sha da tag, pinado. Obtido por
#   git ls-remote https://github.com/open-gsd/gsd-core \
#       refs/tags/v1.10.0 'refs/tags/v1.10.0^{}'
# que devolveu SÓ a linha da tag (nenhuma linha `^{}`): a tag é LIGHTWEIGHT,
# não anotada, então o sha da tag É o sha do commit. A validação de HEAD
# abaixo prova isso contra o clone em toda execução.
TAG_COMMIT = "68a04ccf8ef74803bdb651e12c3b85b218bbccdf"

# A MÉTRICA ADOTADA (REM-02). O research mediu o corpus sob duas regexes e as
# duas contagens não são contradição, são método: a de calibração enxerga só
# `gsd_run query <verbo>`; esta, a larga, cobre também os subcomandos
# top-level não-query (loop, check, run-with-timeout, graphify) que igualmente
# precisam de resposta do binário. O plano adota UMA métrica — esta — e a
# outra sobrevive apenas como reprodução documentada do método (CALIBRATION_RE
# alimenta summary.corpus_calibration e nada mais).
BROAD_RE = re.compile(r"gsd_run (query )?[a-z][a-z-]*(\.[a-z-]+)?")
# A regex de calibração do research — reproduz a contagem de referência sobre
# o corpus inteiro (workflows + commands). Nunca gera sites[] nem verbs{}.
CALIBRATION_RE = re.compile(r"gsd_run query [a-z][a-z0-9._-]+")

# Os workflows que o cairn usa; o conjunto define o fecho do transplante.
WORKFLOWS_8 = (
    "discuss-phase",
    "plan-phase",
    "execute-phase",
    "verify-work",
    "quick",
    "fast",
    "autonomous",
    "debug",
)

# Os agentes do escopo agents: a interseção mecânica entre os nomes que
# existem sob agents/ no clone e os que os 8 workflows referenciam. Derivada
# UMA vez contra o clone real (o comando está no bloco datado do docstring);
# a lista declarada decide — a divergência com a baliza do research fica
# anotada lá, não aqui.
AGENTS_SCOPE = (
    "gsd-advisor-researcher",
    "gsd-code-reviewer",
    "gsd-codebase-mapper",
    "gsd-debug-session-manager",
    "gsd-debugger",
    "gsd-executor",
    "gsd-integration-checker",
    "gsd-nyquist-auditor",
    "gsd-pattern-mapper",
    "gsd-phase-researcher",
    "gsd-plan-checker",
    "gsd-planner",
    "gsd-ui-auditor",
    "gsd-ui-checker",
    "gsd-ui-researcher",
    "gsd-verifier",
)

# Raízes da varredura de calibração, relativas à raiz do clone.
CORPUS_ROOTS = ("gsd-core/workflows", "commands")

# Onde o cache mora, relativo à raiz do projeto (D-01). O commit da tag é a
# chave de invalidação: se TAG_COMMIT muda, o cache antigo passa a morrer com
# exit 6 e um --refresh o refaz.
CACHE_RELPATH = ".cairn/cache/gsd-core-" + TAG

# A linha que define o shim nos preâmbulos dos workflows. Toda ocorrência de
# `gsd_run` numa linha que contém isto é preâmbulo, não chamada.
SHIM_DEF = "gsd_run() {"

TAG_PREFIX = "[cairn-inventory]"

USAGE = ("usage: cairn-inventory.py [--json] [--cache-dir <dir>] "
         "[--source <url|path>] [--expect-commit <sha>] [--refresh]")


def die(msg, code=EXIT_USAGE):
    print(f"{TAG_PREFIX} error: {msg}", file=sys.stderr)
    sys.exit(code)


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def build_parser():
    p = argparse.ArgumentParser(prog="cairn-inventory.py", add_help=True,
                                description=USAGE)
    p.add_argument("--json", action="store_true")
    p.add_argument("--cache-dir")
    p.add_argument("--source")
    p.add_argument("--expect-commit")
    p.add_argument("--refresh", action="store_true")
    return p


def run_git(argv):
    """(returncode, stdout, stderr) para um comando git, ou (None, "", err)
    quando o próprio git não existe."""
    try:
        proc = subprocess.run(["git"] + argv, capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "", str(e)
    return proc.returncode, proc.stdout, proc.stderr


def ensure_corpus(cache_dir, source, expected_commit, refresh):
    """Garante o clone cacheado e VALIDA o HEAD, sempre.

    Cache-hit não toca a fonte (é o que faz a execução offline); clone fresco
    só acontece sem cache ou sob --refresh. Nos dois caminhos o HEAD é
    comparado com o commit esperado — hit ou fresco, corpus não verificado
    não é medido.
    """
    state = "hit"
    is_clone = (cache_dir / ".git").exists()
    if refresh and is_clone:
        shutil.rmtree(cache_dir)
        is_clone = False
        state = "refreshed"
    if not is_clone:
        if state != "refreshed":
            state = "cloned"
        argv = ["clone", "--depth", "1", "--branch", TAG,
                str(source), str(cache_dir)]
        code, _, err = run_git(argv)
        if code is None:
            die(f"could not run `git {' '.join(argv)}`: {err}",
                EXIT_NO_HELPER)
        if code != 0:
            die(f"`git {' '.join(argv)}` exited {code}: "
                f"{(err or '').strip()[:300]}", EXIT_NO_HELPER)
    code, out, err = run_git(["-C", str(cache_dir), "rev-parse", "HEAD"])
    if code is None:
        die(f"could not run git rev-parse on the cache: {err}",
            EXIT_NO_HELPER)
    if code != 0:
        die(f"cache at {cache_dir} is not a readable git clone: "
            f"{(err or '').strip()[:200]}", EXIT_BAD_CORPUS)
    head = out.strip()
    if head != expected_commit:
        die(f"cache HEAD {head} does not match the expected tag commit "
            f"{expected_commit} — refusing to measure an unverified corpus "
            f"(delete the cache or pass --refresh)", EXIT_BAD_CORPUS)
    return {
        "repo": str(source),
        "tag": TAG,
        "commit": head,
        "cache_dir": str(cache_dir),
        "cache_state": state,
    }


def workflows8_files(root):
    """Os arquivos do escopo workflows8: para cada nome, o .md de topo mais
    os arquivos sob o subdiretório de steps/modes, quando existem."""
    files = []
    base = root / "gsd-core" / "workflows"
    for name in WORKFLOWS_8:
        md = base / f"{name}.md"
        if md.is_file():
            files.append(md)
        sub = base / name
        if sub.is_dir():
            files.extend(sorted(p for p in sub.rglob("*") if p.is_file()))
    return files


def subcommand_after(line, end):
    """O token completo imediatamente após o match, quando é uma palavra
    minúscula com hífens — nunca uma flag (que começa em `-`) nem um valor."""
    rest = line[end:]
    if not rest[:1].isspace():
        return None
    parts = rest.split()
    if not parts:
        return None
    tok = parts[0]
    if re.fullmatch(r"[a-z][a-z-]*", tok):
        return tok
    return None


def scan_scope(files, root, scope):
    """Todo match de BROAD_RE nos arquivos do escopo vira um site.

    Linhas que definem o shim ficam de fora dos sites: as ocorrências delas
    pertencem ao balde shim_preambles da contabilidade, nunca a calls.
    """
    sites = []
    for path in files:
        rel = str(path.relative_to(root))
        for lineno, line in enumerate(read_text(path).split("\n"), 1):
            if SHIM_DEF in line:
                continue
            for m in BROAD_RE.finditer(line):
                raw = m.group(0)
                tokens = raw.split()
                if len(tokens) >= 2 and tokens[1] == "query":
                    command = "query"
                    verb = tokens[2] if len(tokens) > 2 else "query"
                else:
                    command = tokens[1] if len(tokens) > 1 else ""
                    verb = command
                sites.append({
                    "file": rel,
                    "line": lineno,
                    "scope": scope,
                    "command": command,
                    "verb": verb,
                    "subcommand": subcommand_after(line, m.end()),
                    "spelling": raw[len("gsd_run "):],
                    "raw": raw,
                })
    return sites


def agents_files(root):
    """Os arquivos do escopo agents: os nomes de AGENTS_SCOPE que existem
    sob agents/ no corpus (num fixture, só os que o fixture carrega)."""
    files = []
    for name in AGENTS_SCOPE:
        md = root / "agents" / f"{name}.md"
        if md.is_file():
            files.append(md)
    return files


def normalize_spellings(sites):
    """A grafia dupla vira UM verbo.

    Um site `query <família> <token>` só é normalizado para `<família>.<token>`
    quando a forma pontuada existe em algum lugar do próprio corpus — a regra
    é dirigida pelo dado, nunca por lista: `query verification status` vira
    `verification.status` porque a grafia pontuada também está lá, e um
    `query config-get workflow` jamais viraria `config-get.workflow` porque
    ninguém escreve essa forma pontuada.
    """
    dotted = {s["verb"] for s in sites if "." in s["verb"]}
    for s in sites:
        if (s["command"] == "query" and "." not in s["verb"]
                and s["subcommand"]
                and f"{s['verb']}.{s['subcommand']}" in dotted):
            s["spelling"] = f"{s['spelling']} {s['subcommand']}"
            s["verb"] = f"{s['verb']}.{s['subcommand']}"
            s["subcommand"] = None
    return sites


def verbs_index(sites):
    """{verbo: {count, scopes, spellings}} sobre os sites dos escopos
    inventariados. A calibração nunca entra aqui."""
    verbs = {}
    for s in sites:
        entry = verbs.setdefault(s["verb"], {"count": 0, "scopes": set(),
                                             "spellings": set()})
        entry["count"] += 1
        entry["scopes"].add(s["scope"])
        entry["spellings"].add(s["spelling"])
    return {v: {"count": e["count"], "scopes": sorted(e["scopes"]),
                "spellings": sorted(e["spellings"])}
            for v, e in verbs.items()}


def calibration_summary(root):
    """A reprodução documentada do método do research: CALIBRATION_RE sobre
    as raízes do corpus. Alimenta APENAS summary.corpus_calibration."""
    calls = 0
    verbs = set()
    for rel in CORPUS_ROOTS:
        base = root / rel
        if not base.is_dir():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            for m in CALIBRATION_RE.finditer(read_text(path)):
                calls += 1
                verbs.add(m.group(0).split()[2])
    return {"calls": calls, "verbs": len(verbs)}


def find_occurrences(line):
    """Posições de toda ocorrência bruta da substring gsd_run na linha."""
    positions = []
    start = 0
    while True:
        p = line.find("gsd_run", start)
        if p == -1:
            return positions
        positions.append(p)
        start = p + 1


def account_scope(files, root):
    """Toda ocorrência bruta de gsd_run classificada dentro da fatia do seu
    escopo: calls, shim_preambles ou other — other enumerado sítio a sítio.
    A identidade total_raw == calls + shim_preambles + other vale por
    construção E é assertada pelos testes, sempre.
    """
    total = calls = shim = 0
    other_sites = []
    for path in files:
        rel = str(path.relative_to(root))
        for lineno, line in enumerate(read_text(path).split("\n"), 1):
            positions = find_occurrences(line)
            if not positions:
                continue
            total += len(positions)
            if SHIM_DEF in line:
                # A linha que define o shim classifica TODAS as suas
                # ocorrências juntas: são preâmbulo, não chamada.
                shim += len(positions)
                continue
            starts = {m.start() for m in BROAD_RE.finditer(line)}
            for p in positions:
                if p in starts:
                    calls += 1
                else:
                    other_sites.append({
                        "file": rel,
                        "line": lineno,
                        "excerpt": line.strip()[:120],
                    })
    return {
        "total_raw": total,
        "calls": calls,
        "shim_preambles": shim,
        "other": len(other_sites),
        "other_sites": other_sites,
    }


def build_model(root, src_info):
    """Tudo que o renderer e o --json vão precisar, num modelo só. Nenhum
    número de summary é computado fora daqui."""
    w8_files = workflows8_files(root)
    ag_files = agents_files(root)
    sites = normalize_spellings(
        scan_scope(w8_files, root, "workflows8")
        + scan_scope(ag_files, root, "agents"))
    w8_sites = [s for s in sites if s["scope"] == "workflows8"]
    ag_sites = [s for s in sites if s["scope"] == "agents"]
    return {
        "source": src_info,
        "metric": {
            "name": "broad",
            "regex": BROAD_RE.pattern,
            "calibration_regex": CALIBRATION_RE.pattern,
        },
        "scopes": {
            "workflows8": {
                "files": [str(p.relative_to(root)) for p in w8_files],
            },
            "agents": {
                "files": [str(p.relative_to(root)) for p in ag_files],
            },
            "corpus": {"roots": list(CORPUS_ROOTS)},
        },
        "sites": sites,
        "verbs": verbs_index(sites),
        "summary": {
            "workflows8": {
                "sites": len(w8_sites),
                "verbs": len({s["verb"] for s in w8_sites}),
            },
            "agents": {
                "sites": len(ag_sites),
                "verbs": len({s["verb"] for s in ag_sites}),
            },
            "corpus_calibration": calibration_summary(root),
            "loop_render_hooks_sites": sum(
                1 for s in w8_sites
                if s["verb"] == "loop" and s["subcommand"] == "render-hooks"),
            "top_verbs": [
                {"verb": v, "count": e["count"]}
                for v, e in sorted(verbs_index(sites).items(),
                                   key=lambda kv: (-kv[1]["count"], kv[0]))[:5]
            ],
        },
        "accounting": {
            "workflows8": account_scope(w8_files, root),
            "agents": account_scope(ag_files, root),
        },
    }


def render(model):
    """Posiciona strings que o modelo já produziu; nada é computado aqui —
    nenhuma divisão, nenhuma contagem. É o que torna "todo número da prosa
    existe como escalar no --json" uma alegação mecanicamente checável (o
    GUARD numbers_not_in_json da suíte)."""
    src = model["source"]
    s = model["summary"]
    w8, ag = s["workflows8"], s["agents"]
    cal = s["corpus_calibration"]
    acc_w8 = model["accounting"]["workflows8"]
    acc_ag = model["accounting"]["agents"]
    lines = [
        f"{TAG_PREFIX} corpus {src['tag']} @ {src['commit']} "
        f"({src['cache_state']})",
        TAG_PREFIX,
        f"{TAG_PREFIX} ▸ workflows8: {w8['sites']} sítios, "
        f"{w8['verbs']} verbos distintos",
        f"{TAG_PREFIX} ▸ agents:     {ag['sites']} sítios, "
        f"{ag['verbs']} verbos distintos",
        f"{TAG_PREFIX} ▸ calibração (corpus): {cal['calls']} chamadas, "
        f"{cal['verbs']} verbos",
        f"{TAG_PREFIX} ▸ loop render-hooks (workflows8): "
        f"{s['loop_render_hooks_sites']} sítios",
    ]
    if s["top_verbs"]:
        joined = " · ".join(f"{t['verb']} {t['count']}"
                            for t in s["top_verbs"])
        lines.append(f"{TAG_PREFIX} ▸ mais chamados: {joined}")
    lines.append(TAG_PREFIX)
    for name, acc in (("workflows8", acc_w8), ("agents", acc_ag)):
        lines.append(
            f"{TAG_PREFIX} ▸ contabilidade {name}: {acc['total_raw']} = "
            f"{acc['calls']} chamadas + {acc['shim_preambles']} preâmbulos "
            f"shim + {acc['other']} other")
        for site in acc["other_sites"]:
            lines.append(f"{TAG_PREFIX}   other: {site['file']}:"
                         f"{site['line']}")
    return lines


# --- subcomandos do transplante: closure e vendor ---------------------------

# Shims 1:1 dos workflows do fecho, no layout REAL do clone (descoberto por
# ls no cache, nunca assumido): commands/gsd/<nome>.md e
# skills/gsd-<nome>/SKILL.md. O research §3 propunha fechar shims via
# `requires:` (9 commands a mais, 34 shims), em contradição com o §2.1 e com
# o Goal da fase — o goal venceu: shims 1:1, e check_skill_requires() abaixo
# é a guarda derivada dessa rejeição.
SHIM_CANDIDATES = (
    "commands/gsd/{name}.md",
    "skills/gsd-{name}/SKILL.md",
)

# Caminho referenciado que puxa arquivo para o fecho: references, templates
# e contexts, em qualquer grafia da casa (~/.claude/gsd-core/...,
# @-prefixada, ou nua relativa a gsd-core/). O lookbehind impede casar no
# meio de outra palavra (ex.: "preferences/" contém "references/").
REF_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:gsd-core/)?"
    r"(?:references|templates|contexts)/[A-Za-z0-9][A-Za-z0-9._/-]*\.md")

# A entrada fixa do fecho: o MIT do upstream entra pela MESMA lista que o
# resto (D-02 + VEND-02) — nada chega a cairn/gsd/ por fora do manifest.
LICENSE_ENTRY = "LICENSE"

CLOSURE_USAGE = ("usage: cairn-inventory.py closure [--json] "
                 "[--write <path>] [--cache-dir <dir>] "
                 "[--source <url|path>] [--expect-commit <sha>] [--refresh]")
VENDOR_USAGE = ("usage: cairn-inventory.py vendor [--manifest <path>] "
                "[--dest <dir>] [--adaptations <path>] "
                "[--clobber-adaptations] [--cache-dir <dir>] "
                "[--source <url|path>] [--expect-commit <sha>] [--refresh]")

# O nome do registro de adaptações, resolvido A PARTIR DO --dest.
#
# Nunca a partir da raiz de resolve_corpus: aquela raiz sai de uma variável de
# ambiente que fica ausente dentro do bats e cai no diretório corrente, que é
# a raiz do repo real. Resolvendo por lá, uma rodada de FIXTURE carregaria o
# registro de PRODUÇÃO e o vendor recusaria a fixture — matando os testes que
# criam justamente caminhos que o registro real contém.
ADAPTATIONS_BASENAME = "gsd-adaptations.json"


def add_corpus_flags(p):
    """As mesmas flags de corpus da invocação flat, num parser dedicado."""
    p.add_argument("--cache-dir")
    p.add_argument("--source")
    p.add_argument("--expect-commit")
    p.add_argument("--refresh", action="store_true")
    return p


def resolve_corpus(args):
    """A resolução de corpus que main() sempre fez, compartilhada com os
    subcomandos: raiz do projeto, cache, fonte e commit esperado."""
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    cache_dir = (Path(args.cache_dir).resolve() if args.cache_dir
                 else root / CACHE_RELPATH)
    source = args.source or SOURCE_URL
    expected = args.expect_commit or TAG_COMMIT
    return root, cache_dir, source, expected


def skill_requires(text):
    """Nomes declarados em `requires:` de um SKILL.md — cobre a forma flow
    (`requires: [a, b]`, a única no clone hoje) e a forma bloco
    (`requires:` seguido de itens `- a`)."""
    names = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = re.match(r"^requires:\s*\[([^\]]*)\]\s*$", line)
        if m:
            names.extend(t.strip() for t in m.group(1).split(",")
                         if t.strip())
            continue
        if re.match(r"^requires:\s*$", line):
            j = i + 1
            while j < len(lines):
                item = re.match(r"^\s*-\s+(\S+)\s*$", lines[j])
                if not item:
                    break
                names.append(item.group(1))
                j += 1
    return names


def check_skill_requires(root, included):
    """A guarda da rejeição do research §3: o fecho segue shims 1:1, então
    nenhum SKILL.md do conjunto pode declarar `requires:` apontando para
    command fora da lista — seria prometer um shim que o vendoring não
    entrega. No clone real o `requires:` vive no frontmatter dos commands
    (fora do escopo desta guarda por decisão de plano); ela morde no dia em
    que um SKILL.md passar a declarar."""
    for rel in sorted(included):
        if not (rel.startswith("skills/") and rel.endswith("/SKILL.md")):
            continue
        for name in skill_requires(read_text(root / rel)):
            target = SHIM_CANDIDATES[0].format(name=name)
            if target not in included:
                die(f"{rel} declares `requires: {name}` but {target} is "
                    f"not in the vendored list — the closure cannot "
                    f"promise a shim it does not deliver", EXIT_BAD_CORPUS)


def closure_files(root):
    """O fecho transitivo do transplante sobre o corpus verificado.

    Sementes: os arquivos do escopo workflows8 (md de topo + steps/modes),
    os agentes de AGENTS_SCOPE presentes, os shims 1:1 que existem no clone
    e o LICENSE. Depois, passadas de grep por REF_RE sobre o conjunto
    corrente até ponto fixo — só entra caminho que EXISTE no cache (método
    do research §2.1). Zero shim para um workflow não é erro fatal: fica
    registrado no summary do modelo.
    """
    included = set()
    for p in workflows8_files(root) + agents_files(root):
        included.add(str(p.relative_to(root)))
    shim_matches = {}
    for name in WORKFLOWS_8:
        found = sorted(rel for rel in
                       (pat.format(name=name) for pat in SHIM_CANDIDATES)
                       if (root / rel).is_file())
        shim_matches[name] = found
        included.update(found)
    if (root / LICENSE_ENTRY).is_file():
        included.add(LICENSE_ENTRY)
    grew = True
    while grew:
        grew = False
        for rel in sorted(included):
            for m in REF_RE.finditer(read_text(root / rel)):
                cand = m.group(0)
                if not cand.startswith("gsd-core/"):
                    cand = "gsd-core/" + cand
                if cand not in included and (root / cand).is_file():
                    included.add(cand)
                    grew = True
    check_skill_requires(root, included)
    return sorted(included), shim_matches


def build_closure_model(root, src_info):
    """O modelo do manifest — separação build_model/render da casa: nada é
    computado fora daqui. source espelha o envelope de
    cairn/gsd/contracts/config.json; derived_from carrega data date-only,
    sem hora, para que duas execuções no mesmo dia emitam bytes idênticos
    (critério de determinismo do manifest)."""
    files, shim_matches = closure_files(root)
    return {
        "schema_version": 1,
        "source": {
            "repo": "open-gsd/gsd-core",
            "tag": src_info["tag"],
            "commit": src_info["commit"],
        },
        "derived_from": {
            "command": "cairn/scripts/cairn-inventory.sh closure --json",
            "date": date.today().isoformat(),
        },
        "files": files,
        "totals": {
            "files": len(files),
            "lines": sum(len(read_text(root / f).splitlines())
                         for f in files),
        },
        "summary": {"shim_matches": shim_matches},
    }


def render_closure(model):
    """Render humano do closure: só posiciona strings do modelo."""
    src = model["source"]
    totals = model["totals"]
    lines = [
        f"{TAG_PREFIX} closure {src['tag']} @ {src['commit']}",
        f"{TAG_PREFIX} ▸ files: {totals['files']}   "
        f"lines: {totals['lines']}",
    ]
    for name, found in sorted(model["summary"]["shim_matches"].items()):
        if not found:
            lines.append(f"{TAG_PREFIX} ▸ shim sem match no clone: {name}")
    return lines


def closure_payload(model):
    """OS bytes do manifest — --json e --write passam OBRIGATORIAMENTE por
    aqui: mesmo serializer da casa (indent 2, sort_keys, ensure_ascii
    False) e newline final explícito."""
    return json.dumps(model, indent=2, sort_keys=True,
                      ensure_ascii=False) + "\n"


def cmd_closure(argv):
    p = argparse.ArgumentParser(prog="cairn-inventory.py closure",
                                add_help=True, description=CLOSURE_USAGE)
    p.add_argument("--json", action="store_true")
    p.add_argument("--write", metavar="PATH")
    add_corpus_flags(p)
    args = p.parse_args(argv)
    root, cache_dir, source, expected = resolve_corpus(args)
    src_info = ensure_corpus(cache_dir, source, expected, args.refresh)
    model = build_closure_model(cache_dir, src_info)
    payload = closure_payload(model)
    if args.write:
        write_path = Path(args.write)
        if not write_path.is_absolute():
            write_path = root / write_path
        write_path.parent.mkdir(parents=True, exist_ok=True)
        write_path.write_text(payload, encoding="utf-8")
    if args.json:
        sys.stdout.write(payload)
    else:
        for line in render_closure(model):
            print(line)
    sys.exit(EXIT_OK)


def load_adaptations(path):
    """Os caminhos declarados adaptados sob a árvore vendorizada.

    Registro ausente = conjunto vazio: um checkout que ainda não adaptou nada
    é estado legítimo, e a fixture sintética dos testes nunca tem registro."""
    if not path.is_file():
        return set()
    try:
        data = json.loads(read_text(path))
    except ValueError as e:
        die(f"registro de adaptações em {path} não é JSON válido: {e}")
    entries = data.get("adaptations")
    if not isinstance(entries, list):
        die(f"registro de adaptações em {path} não tem a lista adaptations")
    return {e.get("path") for e in entries if isinstance(e, dict)
            and e.get("path")}


def cmd_vendor(argv):
    p = argparse.ArgumentParser(prog="cairn-inventory.py vendor",
                                add_help=True, description=VENDOR_USAGE)
    p.add_argument("--manifest", default="cairn/gsd/MANIFEST.json",
                   metavar="PATH")
    p.add_argument("--dest", default="cairn/gsd", metavar="DIR")
    p.add_argument("--adaptations", metavar="PATH")
    p.add_argument("--clobber-adaptations", action="store_true")
    add_corpus_flags(p)
    args = p.parse_args(argv)
    root, cache_dir, source, expected = resolve_corpus(args)
    # Corpus verificado PRIMEIRO — nada de cópia sobre cache não validado.
    ensure_corpus(cache_dir, source, expected, args.refresh)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    dest = Path(args.dest)
    if not dest.is_absolute():
        dest = root / dest
    if not manifest_path.is_file():
        die(f"manifest not found at {manifest_path} — run `closure "
            f"--write` first")
    try:
        manifest = json.loads(read_text(manifest_path))
    except ValueError as e:
        die(f"manifest at {manifest_path} is not valid JSON: {e}")
    mcommit = (manifest.get("source") or {}).get("commit", "")
    if mcommit != expected:
        die(f"manifest commit {mcommit or '<missing>'} does not match the "
            f"expected tag commit {expected} — regenerate the manifest "
            f"with `closure --write` before vendoring", EXIT_BAD_CORPUS)
    files = manifest.get("files") or []
    # VEND-REVERT: uma re-vendorização copia o cache POR CIMA da árvore, e
    # antes da fase 36 isso desfazia adaptações sem erro nenhum — a cópia é
    # byte a byte do upstream e a conferência posterior confirma zero
    # divergência, ou seja, o sucesso é justamente o estado indesejado. Daí a
    # recusa vir ANTES da primeira cópia.
    adaptations_path = (Path(args.adaptations).resolve() if args.adaptations
                        else dest.parent / ADAPTATIONS_BASENAME)
    adapted = load_adaptations(adaptations_path)
    clash = [rel for rel in files if rel in adapted]
    if clash and not args.clobber_adaptations:
        named = "\n  ".join(clash)
        die(f"recusando vendorizar: {len(clash)} caminho(s) de files[] "
            f"carregam adaptação registrada em {adaptations_path} — copiar o "
            f"cache por cima as desfaria em silêncio:\n  {named}\n"
            "saídas: rode com --clobber-adaptations para sobrescrever de "
            "propósito, e reaplique depois com `cairn-preamble.sh apply`",
            EXIT_BAD_CORPUS)
    copied = 0
    for rel in files:
        src_path = cache_dir / rel
        if not src_path.is_file():
            die(f"manifest entry {rel} does not exist in the verified "
                f"cache — the manifest does not match the corpus",
                EXIT_BAD_CORPUS)
        dst_path = dest / rel
        # Cópia POR LISTA, arquivo a arquivo — nunca copytree de diretório
        # do clone (é assim que um hook indesejado entraria), e NUNCA
        # rmtree no dest: cairn/gsd/contracts/ mora lá e não é desta fase.
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        copied += 1
    diverged = [rel for rel in files
                if not filecmp.cmp(dest / rel, cache_dir / rel,
                                   shallow=False)]
    if diverged:
        die("vendored copy diverges from the verified cache: "
            + ", ".join(diverged), EXIT_BAD_CORPUS)
    print(f"{TAG_PREFIX} vendored {copied} files into {dest}")
    if clash:
        print(f"{TAG_PREFIX} sobrescreveu {len(clash)} adaptação(ões) "
              f"registrada(s) em {adaptations_path}; reaplique com "
              "`cairn/scripts/cairn-preamble.sh apply`")
    sys.exit(EXIT_OK)


def main():
    # Dispatch de subcomando — rota (b): testar sys.argv[1] e despachar para
    # um parser dedicado. A rota (a), add_subparsers com default, é o
    # precedente da casa (cairn-config.py), considerada e descartada:
    # duas suítes chamam a invocação FLAT sem subcomando e um subparser
    # opcional exigiria duplicar as flags flat no top-level; testar argv[1]
    # preserva aquele contrato byte a byte.
    if len(sys.argv) > 1 and sys.argv[1] == "closure":
        cmd_closure(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "vendor":
        cmd_vendor(sys.argv[2:])
    args = build_parser().parse_args()
    root, cache_dir, source, expected = resolve_corpus(args)
    src_info = ensure_corpus(cache_dir, source, expected, args.refresh)
    model = build_model(cache_dir, src_info)
    if args.json:
        print(json.dumps(model, indent=2, sort_keys=True,
                         ensure_ascii=False))
    else:
        for line in render(model):
            print(line)
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
