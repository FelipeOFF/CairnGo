#!/usr/bin/env python3
"""cairn-gsd.py — dispatcher único das famílias triviais do gsd-tools (D-01).

O binário python que responde, verbo a verbo, a superfície `gsd_run` que os
workflows do GSD chamam — na forma do binário real da tag pinada (medida
contra o gsd-tools.cjs do clone em 2026-08-10; ver a nota de divergência do
--raw abaixo). O roteamento É o contrato: a tabela spelling→verbo sai de
cairn/gsd/contracts/contracts.json `.verbs` mais os `spellings[]` de cada
arquivo de família; nenhuma tabela paralela é mantida aqui.

Usage:
    cairn-gsd.py <spelling do verbo> [argv do verbo]
    ex.: cairn-gsd.py query config-get <key.path> [--default <v>] [--raw]
         cairn-gsd.py query config-set <key.path> <valor> [--raw]
    cairn-gsd.py --list-implemented
         superfície de TESTE, fora dos contratos: imprime um verbo
         implementado por linha (as chaves de HANDLERS, ordenadas) e sai 0.
         O guard de cobertura de tests/cairn-gsd.bats consome esta
         enumeração em vez de manter lista paralela de verbos (TRIV-04).

Exit codes:
    0  caminho do contrato do verbo (chave resolvida, valor gravado, ...)
    1  erro contratado do verbo (CONFIG_KEY_NOT_FOUND, CONFIG_NO_FILE,
       CONFIG_PARSE_FAILED, CONFIG_INVALID_KEY, valor fora do domínio, ...)
    2  EXIT_USAGE — erro de uso do próprio dispatcher: flag do dispatcher
       desconhecida (antes do verbo) ou token fora do universo do contrato
    4  EXIT_UNIMPLEMENTED — verbo do universo cuja família ainda não é
       servida por este script; a mensagem nomeia a família e a fase que a
       entrega, nunca resposta vazia

Semântica de saída (MEDIDA no binário real, io.cts output()): SEM --raw a
saída é JSON.stringify(valor, null, 2) — string sai COM aspas; COM --raw a
saída é String(valor) — texto cru (objeto vira "[object Object]", array vira
join por vírgula). Nenhuma das duas carrega newline final. O contrato
config.json da fase 31 descreve o --raw INVERTIDO em relação ao binário; este
script segue o binário (é ele que os goldens gravam) e a divergência de
documentação está declarada em tests/fixtures/gsd-goldens/divergences.json.

Flags desconhecidas DENTRO de um verbo são ignoradas best-effort (o espírito
do --force-isolation do contrato); flag desconhecida ANTES do verbo é uso do
dispatcher, exit 2.

Resolução do manifest de defaults de config (TRIV-01), em CADEIA DECLARADA:
    (a) cairn/gsd/gsd-core/config-defaults.manifest.json, se existir — passa
        a valer quando a fase 32 (vendorização) mergear;
    (b) senão, o config-defaults.manifest.json do clone em cache
        .cairn/cache/gsd-core-v1.10.0 — resolvido relativo à RAIZ DO REPO
        DESTE SCRIPT, como o caminho (a), porque o manifest é asset estático
        da tag pinada e não do projeto em que o verbo roda —, com o HEAD
        verificado contra o commit pinado da tag (forma copiada de
        ensure_corpus do cairn-inventory.py; módulo nunca importado);
    (c) senão, die nomeado pedindo cache/rede ("rode cairn-inventory.sh uma
        vez com rede").
Quando a chave existe em mais de uma camada, vence a primeira. Seam de teste:
CAIRN_GSD_CONFIG_MANIFEST aponta o manifest diretamente e vence a cadeia
inteira — os testes provam a precedência sem criar arquivo sob cairn/gsd/.
O config-schema.manifest.json (validKeys/dynamicKeyPatterns do config-set) é
resolvido como IRMÃO do manifest de defaults encontrado; quando o irmão não
existe, o domínio de chaves válidas deriva dos caminhos do próprio manifest
de defaults mais os padrões dinâmicos que o contrato nomeia.

A árvore cairn/gsd/ é SOMENTE-LEITURA para este script (a fase 32 a vendoriza
em worktree paralelo com invariante de exatidão nos dois sentidos): este
script lê contratos e, quando existir, o manifest do caminho (a) — e nunca
escreve nada lá.

Divergências deliberadas do upstream ficam declaradas em
tests/fixtures/gsd-goldens/divergences.json — nunca improvisadas.
"""
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

EXIT_OK = 0
EXIT_CONTRACT = 1
EXIT_USAGE = 2
EXIT_UNIMPLEMENTED = 4

TAG_PREFIX = "[cairn-gsd]"

USAGE = ("usage: cairn-gsd.py <spelling do verbo> [argv do verbo] — "
         "ex.: query config-get <key.path> [--default <v>] [--raw]")

# Contratos da fase 31, relativos a este script. Arquivos NOSSOS: leitura
# estrita, die em falta ou JSON inválido — um contrato ilegível é bug do
# repositório, não condição de runtime a engolir.
CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "gsd" / "contracts"

# Cadeia do manifest de defaults (TRIV-01) — ver docstring.
VENDORED_MANIFEST = (Path(__file__).resolve().parent.parent / "gsd"
                     / "gsd-core" / "config-defaults.manifest.json")
MANIFEST_ENV = "CAIRN_GSD_CONFIG_MANIFEST"
CACHE_RELPATH = ".cairn/cache/gsd-core-v1.10.0"
TAG_COMMIT = "68a04ccf8ef74803bdb651e12c3b85b218bbccdf"
SCHEMA_MANIFEST_NAME = "config-schema.manifest.json"

PLANNING_CONFIG_RELPATH = ".planning/config.json"

# Fase que entrega cada família ainda não servida por este script — a
# tabela de MENSAGEM do die exit 4 (irmão ausente do disco, órfãos, fase 35).
PHASE_BY_FAMILY = {
    "estado": "fase 34",
    "roadmap-phase": "fase 34",
    "worktree": "fase 34",
    "init": "fase 34",
    "misc": "fase 34",
    "checagem": "fase 35",
}

# Roteamento D-01 (fase 34): as famílias pesadas vivem em scripts irmãos
# invocados por os.execv com o VERBO canônico já resolvido — o roteamento
# spelling→verbo fica SÓ aqui (build_routes); nenhuma tabela paralela no
# irmão. Irmão ainda inexistente no disco cai no die exit 4 de
# PHASE_BY_FAMILY (estado transitório entre ondas da fase).
FAMILY_SCRIPT = {
    "estado": "cairn-gsd-state.py",
    "roadmap-phase": "cairn-gsd-state.py",
    "worktree": "cairn-gsd-init.py",
    "init": "cairn-gsd-init.py",
    "checagem": "cairn-gsd-check.py",
}
# misc roteia POR VERBO (partição registrada no plano 34-01): os 7 verbos de
# planning-docs vão pro irmão de estado; os demais (menos os órfãos da 35)
# pro irmão de init.
MISC_STATE_VERBS = frozenset((
    "summary-extract",
    "todo.match-phase",
    "requirements.mark-complete",
    "requirements.revert-phase",
    "quick-tasks-append",
    "history-digest",
    "research-plan",
    "research-store",
))
# Ex-órfãos de CHECK-03 (fase 35, D-01): a constante mudou de PAPEL —
# era a lista de EXCLUSÃO (ORPHANS_PHASE_35, die exit 4 nomeando a fase);
# agora é ROTA explícita pro irmão de checagem (molde MISC_STATE_VERBS).
# Os 5 são família misc em contracts.json e respondem em cairn-gsd-check.py.
MISC_CHECK_VERBS = frozenset((
    "audit-open",
    "review-lane",
    "agent.classify-failure",
    "task.is-behavior-adding",
    "run-with-timeout",
))

# isSecretKey/maskSecret do upstream (src/secrets.cts), reproduzidos exatos:
# o conjunto é FECHADO e por igualdade de key.path inteiro, não por padrão.
SECRET_CONFIG_KEYS = frozenset(("brave_search", "firecrawl", "exa_search"))

# Padrões dinâmicos que o contrato nomeia — o fallback quando o
# config-schema.manifest.json não resolve pela cadeia.
FALLBACK_DYNAMIC_PATTERNS = (
    re.compile(r"^agent_skills\.[a-zA-Z0-9_-]+$"),
    re.compile(r"^features\.[a-zA-Z0-9_]+$"),
)

# Sentinela para "ausente" (o undefined do JS, que JSON.stringify descarta) —
# distinto de None, que é o null do JSON e sobrevive na saída.
_UNDEFINED = object()


def die(msg, code=EXIT_USAGE):
    print(f"{TAG_PREFIX} error: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# roteamento — o contrato é a fonte
# --------------------------------------------------------------------------- #
def load_json_strict(path):
    """JSON de um arquivo NOSSO (contratos/manifests): falta ou inválido é
    die, com o caminho nomeado — nunca traceback."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        die(f"contrato ilegível: {path}: {e}", EXIT_USAGE)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        die(f"contrato não é JSON válido: {path}: {e}", EXIT_USAGE)


def build_routes():
    """spelling → (verb, family), derivado de contracts.json .verbs mais os
    spellings[] do arquivo de cada família."""
    agg = load_json_strict(CONTRACTS_DIR / "contracts.json")
    verbs = agg.get("verbs")
    if not isinstance(verbs, dict) or not verbs:
        die(f"contracts.json sem índice .verbs utilizável em {CONTRACTS_DIR}",
            EXIT_USAGE)
    routes = {}
    family_docs = {}
    for verb, meta in verbs.items():
        family = meta.get("family")
        fname = meta.get("file")
        if not family or not fname:
            die(f"entrada de verbo sem family/file em contracts.json: {verb}",
                EXIT_USAGE)
        doc = family_docs.get(fname)
        if doc is None:
            doc = load_json_strict(CONTRACTS_DIR / fname)
            family_docs[fname] = doc
        entry = next((v for v in doc.get("verbs", [])
                      if v.get("verb") == verb), None)
        if entry is None:
            die(f"verbo '{verb}' indexado em contracts.json mas ausente de "
                f"{fname}", EXIT_USAGE)
        spellings = entry.get("spellings") or []
        if not spellings:
            die(f"verbo '{verb}' sem spellings em {fname}", EXIT_USAGE)
        for spelling in spellings:
            routes[spelling] = (verb, family)
    return routes


def phase_for(verb, family):
    return PHASE_BY_FAMILY.get(family, "fase 33")


def script_for(verb, family):
    """O script irmão que serve o verbo (D-01), ou None quando o verbo é
    deste script. misc roteia por VERBO em TRÊS destinos (fase 35):
    planning-docs → estado; ex-órfãos de CHECK-03 → check; resto → init."""
    if family == "misc":
        if verb in MISC_STATE_VERBS:
            return "cairn-gsd-state.py"
        if verb in MISC_CHECK_VERBS:
            return "cairn-gsd-check.py"
        return "cairn-gsd-init.py"
    return FAMILY_SCRIPT.get(family)


# --------------------------------------------------------------------------- #
# .planning/config.json do escopo
# --------------------------------------------------------------------------- #
def planning_config_path():
    return Path.cwd() / PLANNING_CONFIG_RELPATH


def load_scope_config():
    """O dict de .planning/config.json do cwd, ou None quando o arquivo não
    existe. Parse quebrado é erro contratado (CONFIG_PARSE_FAILED, exit 1) —
    um config ilegível não degrada para 'chave ausente'."""
    path = planning_config_path()
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        die(f"CONFIG_PARSE_FAILED: não consegui ler {path}: {e}",
            EXIT_CONTRACT)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        die(f"CONFIG_PARSE_FAILED: {path} não é JSON válido: {e}",
            EXIT_CONTRACT)
    if not isinstance(data, dict):
        die(f"CONFIG_PARSE_FAILED: {path} precisa ser um objeto JSON, "
            f"achei {type(data).__name__}", EXIT_CONTRACT)
    return data


def dotted_get(data, key):
    """(value, found) por dotted-path com gate de own-property: só desce em
    dict e só por chave PRESENTE — o equivalente python do gate que protege
    __proto__/constructor no upstream."""
    cur = data
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


def dotted_set(data, key, value):
    """Grava um dotted-path criando os objetos intermediários; um não-dict no
    lugar de um contêiner é substituído (a forma de _setNestedValue).
    Devolve o valor anterior ou _UNDEFINED quando a folha não existia."""
    parts = key.split(".")
    cur = data
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    previous = cur[parts[-1]] if parts[-1] in cur else _UNDEFINED
    cur[parts[-1]] = value
    return previous


def dotted_unset(data, key):
    """(previous, existed) removendo a folha do dotted-path quando existe.
    Caminho intermediário ausente ou não-dict lê como inexistente."""
    parts = key.split(".")
    cur = data
    for part in parts[:-1]:
        if not isinstance(cur, dict) or part not in cur:
            return _UNDEFINED, False
        cur = cur[part]
    if not isinstance(cur, dict) or parts[-1] not in cur:
        return _UNDEFINED, False
    previous = cur.pop(parts[-1])
    return previous, True


def is_secret_key(key):
    return key in SECRET_CONFIG_KEYS


def mask_secret(value):
    """maskSecret do upstream, exato: null/vazio vira '(unset)', valor curto
    vira '****', o resto mostra só os 4 últimos caracteres."""
    if value is None or value is _UNDEFINED or value == "":
        return "(unset)"
    s = js_string(value)
    if len(s) < 8:
        return "****"
    return "****" + s[-4:]


# --------------------------------------------------------------------------- #
# render — uma função só serializa (separação modelo/render da casa)
# --------------------------------------------------------------------------- #
def js_number_text(n):
    """A forma do String(number) do JS: inteiro sem ponto, decimal com."""
    if isinstance(n, int):
        return str(n)
    if float(n).is_integer():
        return str(int(n))
    return repr(float(n))


def js_string(value):
    """String(valor) do JS, para a saída --raw: string crua, bool minúsculo,
    null literal, objeto '[object Object]', array join por vírgula."""
    if isinstance(value, str):
        return value
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return js_number_text(value)
    if isinstance(value, list):
        return ",".join("" if item is None else js_string(item)
                        for item in value)
    if isinstance(value, dict):
        return "[object Object]"
    return str(value)


def stringify(value):
    """JSON.stringify(valor, null, 2) do upstream: indent 2, ordem de
    inserção preservada, não-ASCII sem escape, sem newline final."""
    return json.dumps(value, indent=2, ensure_ascii=False)


def render_value(value, raw):
    """A string de saída de um valor resolvido, na semântica MEDIDA do
    binário (io.cts output()): --raw é String(valor); sem --raw é o JSON."""
    if raw:
        return js_string(value)
    return stringify(value)


def emit(text):
    """Escreve a saída EXATAMENTE como o binário: sem newline final."""
    sys.stdout.write(text)


# --------------------------------------------------------------------------- #
# a cadeia do manifest (TRIV-01)
# --------------------------------------------------------------------------- #
def resolve_config_manifest_path(required):
    """O CAMINHO do manifest de defaults pela cadeia declarada (docstring).
    required=True faz o passo (c) morrer nomeado; required=False devolve
    None quando nenhuma fonte existe."""
    override = os.environ.get(MANIFEST_ENV)
    if override:
        path = Path(override)
        if path.is_file():
            return path
        if required:
            die(f"manifest de defaults indisponível: {MANIFEST_ENV} aponta "
                f"para arquivo inexistente ({path}) — corrija o seam ou rode "
                "cairn-inventory.sh uma vez com rede para popular o cache",
                EXIT_CONTRACT)
        return None
    if VENDORED_MANIFEST.is_file():
        return VENDORED_MANIFEST
    cached = cached_manifest_path()
    if cached is not None:
        return cached
    if required:
        die("manifest de defaults indisponível: nem "
            "cairn/gsd/gsd-core/config-defaults.manifest.json (fase 32) nem "
            f"o clone em cache {CACHE_RELPATH} — rode cairn-inventory.sh uma "
            "vez com rede para popular o cache", EXIT_CONTRACT)
    return None


def cached_manifest_path():
    """O config-defaults.manifest.json do clone em cache, SÓ com o HEAD
    verificado contra o commit pinado — a doutrina de ensure_corpus do
    cairn-inventory.py, forma copiada, módulo nunca importado. Qualquer
    falha (sem cache, git ausente, HEAD divergente, arquivo ausente) devolve
    None: quem decide se isso mata é o chamador."""
    script_repo_root = Path(__file__).resolve().parent.parent.parent
    cache_dir = script_repo_root / CACHE_RELPATH
    if not (cache_dir / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(cache_dir), "rev-parse", "HEAD"],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or proc.stdout.strip() != TAG_COMMIT:
        return None
    hits = sorted(cache_dir.rglob("config-defaults.manifest.json"))
    for hit in hits:
        if ".git" not in hit.parts:
            return hit
    return None


def load_defaults_manifest(required):
    path = resolve_config_manifest_path(required)
    if path is None:
        return None
    manifest = load_json_strict(path)
    if not isinstance(manifest, dict):
        die(f"manifest de defaults não é um objeto JSON: {path}",
            EXIT_CONTRACT)
    return manifest


def schema_default(key):
    """(value, found) para o default de schema da chave, por dotted-get no
    manifest resolvido pela cadeia — a camada de TRIV-01. A chave-comentário
    do manifest não é config."""
    manifest = load_defaults_manifest(required=False)
    if manifest is None or key == "_comment" or key.startswith("_comment."):
        return None, False
    return dotted_get(manifest, key)


def manifest_dotted_paths(node, prefix=""):
    """Todos os dotted-paths (folhas E contêineres) do manifest de defaults,
    para o fallback do domínio de chaves válidas do config-set."""
    paths = set()
    if not isinstance(node, dict):
        return paths
    for key, value in node.items():
        if key == "_comment":
            continue
        dotted = f"{prefix}.{key}" if prefix else key
        paths.add(dotted)
        if isinstance(value, dict):
            paths.update(manifest_dotted_paths(value, dotted))
    return paths


def load_valid_key_domain():
    """O domínio de chaves válidas do config-set: o config-schema.manifest
    IRMÃO do manifest de defaults resolvido (validKeys + runtimeStateKeys +
    dynamicKeyPatterns) unido aos caminhos do próprio manifest de defaults
    (que cobre as chaves federadas de capability, ex. workflow.research);
    sem o irmão, só os caminhos do manifest + os padrões do contrato.
    Devolve (keys:set, patterns:list[regex])."""
    defaults_path = resolve_config_manifest_path(required=True)
    defaults = load_json_strict(defaults_path)
    if not isinstance(defaults, dict):
        die(f"manifest de defaults não é um objeto JSON: {defaults_path}",
            EXIT_CONTRACT)
    keys = manifest_dotted_paths(defaults)
    patterns = list(FALLBACK_DYNAMIC_PATTERNS)
    sibling = defaults_path.parent / SCHEMA_MANIFEST_NAME
    if sibling.is_file():
        schema = load_json_strict(sibling)
        if isinstance(schema, dict):
            for k in schema.get("validKeys") or []:
                if isinstance(k, str):
                    keys.add(k)
            for k in schema.get("runtimeStateKeys") or []:
                if isinstance(k, str):
                    keys.add(k)
            compiled = []
            for entry in schema.get("dynamicKeyPatterns") or []:
                src = (entry or {}).get("source")
                if isinstance(src, str):
                    try:
                        compiled.append(re.compile(src))
                    except re.error:
                        pass
            if compiled:
                patterns = compiled
    return keys, patterns


def is_valid_config_key(key, keys, patterns):
    if key in keys:
        return True
    return any(p.match(key) for p in patterns)


# --------------------------------------------------------------------------- #
# handlers — config-get
# --------------------------------------------------------------------------- #
def parse_config_get_args(rest):
    """(key, default, has_default, raw). Flags desconhecidas dentro do verbo
    são ignoradas best-effort; key.path ausente é erro do CONTRATO (exit 1),
    não do dispatcher."""
    key = None
    default = None
    has_default = False
    raw = False
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "--default":
            if i + 1 >= len(rest):
                die("Usage: config-get <key.path> [--default <value>]",
                    EXIT_CONTRACT)
            default = rest[i + 1]
            has_default = True
            i += 2
            continue
        if tok == "--raw":
            raw = True
            i += 1
            continue
        if tok.startswith("-"):
            i += 1  # best-effort: flag desconhecida do verbo é ignorada
            continue
        if key is None:
            key = tok
        i += 1
    if key is None:
        die("Usage: config-get <key.path> [--default <value>]",
            EXIT_CONTRACT)
    return key, default, has_default, raw


def emit_resolved(key, value, raw):
    """A emissão centralizada com a invariante de máscara do upstream
    (emitResolvedDefault): chave secreta nunca ecoa plaintext."""
    if is_secret_key(key):
        masked = mask_secret(value)
        emit(masked if raw else stringify(masked))
        return
    emit(render_value(value, raw))


def handle_config_get(rest):
    """Cadeia do contrato: config do escopo → --default → default do schema
    (manifest resolvido pela cadeia declarada) → CONFIG_KEY_NOT_FOUND.
    A camada 'root do workstream' (#2702) NÃO existe no cairn — divergência
    declarada na tabela da fase."""
    key, default, has_default, raw = parse_config_get_args(rest)
    scope = load_scope_config()
    if scope is not None:
        value, found = dotted_get(scope, key)
        if found:
            emit_resolved(key, value, raw)
            return EXIT_OK
    if has_default:
        emit_resolved(key, default, raw)
        return EXIT_OK
    value, found = schema_default(key)
    if found:
        emit_resolved(key, value, raw)
        return EXIT_OK
    if scope is None:
        die(f"CONFIG_NO_FILE: {planning_config_path()} não existe e nenhum "
            f"fallback resolve '{key}'", EXIT_CONTRACT)
    die(f"CONFIG_KEY_NOT_FOUND: Key not found: {key}", EXIT_CONTRACT)


# --------------------------------------------------------------------------- #
# handlers — config-set
# --------------------------------------------------------------------------- #
def parse_config_set_args(rest):
    """(key, value, raw); chave OU valor ausente é o guard do #3593 —
    exit 1, nunca gravação de undefined."""
    positionals = []
    raw = False
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "--raw":
            raw = True
        elif tok.startswith("-") and len(positionals) >= 2:
            pass  # best-effort: flag desconhecida do verbo é ignorada
        else:
            # um valor legítimo pode começar com '-' (número negativo);
            # antes de key+valor completos, tudo que não é --raw é posicional
            positionals.append(tok)
        i += 1
    if len(positionals) < 2:
        die("Usage: config-set <key.path> <valor>", EXIT_CONTRACT)
    return positionals[0], positionals[1], raw


def js_number(text):
    """Number(text) do JS restrito a finitos: devolve int/float ou None
    quando não coage (#1581: Infinity NÃO coage)."""
    t = text.strip()
    if t == "":
        return None
    if re.fullmatch(r"[+-]?0[xX][0-9a-fA-F]+", t):
        sign = -1 if t[0] == "-" else 1
        return sign * int(t.lstrip("+-"), 16)
    try:
        n = float(t)
    except (TypeError, ValueError):
        return None
    if math.isinf(n) or math.isnan(n):
        return None
    if n.is_integer() and abs(n) < 2 ** 53:
        return int(n)
    return n


def coerce_set_value(key, val):
    """A coerção do cmdConfigSet, na ordem do upstream: booleans, null
    (unset), número finito, JSON de '['/'{' com fallback string; e
    project_code fica string verbatim (#1581)."""
    parsed = val
    if val == "true":
        parsed = True
    elif val == "false":
        parsed = False
    elif val == "null":
        parsed = None
    else:
        number = js_number(val)
        if number is not None:
            parsed = number
        elif val.startswith("[") or val.startswith("{"):
            try:
                parsed = json.loads(val)
            except json.JSONDecodeError:
                parsed = val
    if parsed is not None and key == "project_code":
        parsed = val
    return parsed


def assert_enum(key, parsed, raw_text, choices):
    if parsed not in choices:
        die(f"Invalid {key} '{raw_text}'. Must be one of: "
            f"{', '.join(choices)}.", EXIT_CONTRACT)


def is_bool(v):
    return isinstance(v, bool)


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_set_value(key, parsed, raw_text):
    """Os validadores centrais hardcoded do cmdConfigSet — valor rejeitado
    morre AQUI, antes de qualquer escrita ('a rejected value leaves the file
    untouched'). A validação por tipo do capability-registry não é
    reproduzida — divergência declarada na tabela da fase."""
    if key == "context":
        assert_enum(key, parsed, raw_text, ["dev", "research", "review"])
    if key == "workflow.drift_action":
        assert_enum(key, parsed, raw_text, ["warn", "auto-remap"])
    if key == "workflow.drift_threshold":
        if not is_int(parsed) or parsed < 1:
            die(f"Invalid workflow.drift_threshold '{raw_text}'. Must be a "
                "positive integer.", EXIT_CONTRACT)
    if key == "context_window":
        if not is_int(parsed) or parsed < 1:
            die(f"Invalid context_window '{raw_text}'. Must be a positive "
                "integer (token count).", EXIT_CONTRACT)
    if key == "workflow.smart_zone_tokens":
        if not is_int(parsed) or parsed < 1 or abs(parsed) > 2 ** 53 - 1:
            die(f"Invalid workflow.smart_zone_tokens '{raw_text}'. Must be a "
                "positive integer (token count).", EXIT_CONTRACT)
    if key in ("workflow.post_planning_gaps", "git.create_tag",
               "statusline.show_context_tokens", "statusline.show_git",
               "plan_review.source_grounding"):
        if not is_bool(parsed):
            die(f"Invalid {key} '{raw_text}'. Must be a boolean (true or "
                "false).", EXIT_CONTRACT)
    if key == "ship.pr_body_sections":
        validate_ship_pr_body_sections(parsed)
    if key == "workflow.human_verify_mode":
        assert_enum(key, parsed, raw_text, ["mid-flight", "end-of-phase"])
    if key == "workflow.context_guard_mode":
        assert_enum(key, parsed, raw_text, ["auto", "warn", "off"])
    if key == "statusline.context_position":
        assert_enum(key, parsed, raw_text, ["front", "end"])
    if key == "statusline.state_format":
        assert_enum(key, parsed, raw_text, ["full", "compact"])
    if key == "code_quality.fallow.scope":
        assert_enum(key, parsed, raw_text, ["phase", "repo"])
    if key == "code_quality.fallow.profile":
        assert_enum(key, parsed, raw_text, ["minimal", "standard", "strict"])
    if key == "plan_review.source_grounding_authority":
        assert_enum(key, parsed, raw_text,
                    ["grep", "intel", "treesitter", "lsp", "scip"])
    if key == "workflow.security_asvs_level":
        if not is_int(parsed) or parsed < 1 or parsed > 3:
            die(f"Invalid workflow.security_asvs_level '{raw_text}'. Must be "
                "an integer 1, 2, or 3.", EXIT_CONTRACT)


def validate_ship_pr_body_sections(parsed):
    allowed = {"heading", "enabled", "source", "fallback", "template"}
    if not isinstance(parsed, list):
        die("Invalid ship.pr_body_sections value. Expected a JSON array of "
            "section objects.", EXIT_CONTRACT)
    for section in parsed:
        if not isinstance(section, dict) or not set(section) <= allowed:
            die("Invalid ship.pr_body_sections value. Expected a JSON array "
                "of section objects.", EXIT_CONTRACT)


def write_scope_config(config):
    """Escrita do .planning/config.json na forma do binário: indent 2, ordem
    de inserção preservada, não-ASCII sem escape, newline final — em arquivo
    temp irmão publicado por rename atômico (platformWriteSync), o que faz
    duas gravações concorrentes terminarem sempre em JSON válido."""
    path = planning_config_path()
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    data = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        die(f"Failed to write config.json: {e}", EXIT_CONTRACT)


def load_scope_config_for_set():
    """Como o setConfigValue: arquivo ausente é objeto vazio; parse quebrado
    é CONFIG_PARSE_FAILED."""
    data = load_scope_config()
    return {} if data is None else data


def result_json(pairs):
    """O envelope JSON do config-set na ordem de inserção do upstream,
    descartando _UNDEFINED como o JSON.stringify descarta undefined."""
    return {k: v for k, v in pairs if v is not _UNDEFINED}


def handle_config_set(rest):
    key, val, raw = parse_config_set_args(rest)
    keys, patterns = load_valid_key_domain()
    if not is_valid_config_key(key, keys, patterns):
        die(f'CONFIG_INVALID_KEY: Unknown config key: "{key}". Valid keys: '
            f"{', '.join(sorted(keys))}, agent_skills.<agent-type>, "
            "features.<feature_name>", EXIT_CONTRACT)

    parsed = coerce_set_value(key, val)

    # #2046: null desfaz (deleta) a chave — curto-circuito antes de todo
    # validador tipado, para limpar uma chave tipada em vez de rejeitar.
    if parsed is None:
        config = load_scope_config_for_set()
        previous, existed = dotted_unset(config, key)
        write_scope_config(config)
        if is_secret_key(key):
            masked_prev = (_UNDEFINED if previous is _UNDEFINED
                           else mask_secret(previous))
            payload = result_json((
                ("updated", existed), ("unset", True), ("key", key),
                ("value", None), ("previousValue", masked_prev),
                ("masked", True)))
        else:
            payload = result_json((
                ("updated", existed), ("unset", True), ("key", key),
                ("value", None), ("previousValue", previous)))
        emit(f"{key} unset" if raw else stringify(payload))
        return EXIT_OK

    validate_set_value(key, parsed, val)

    config = load_scope_config_for_set()
    previous = dotted_set(config, key, parsed)
    write_scope_config(config)

    if is_secret_key(key):
        masked = mask_secret(parsed)
        masked_prev = (_UNDEFINED if previous is _UNDEFINED
                       else mask_secret(previous))
        payload = result_json((
            ("updated", True), ("key", key), ("value", masked),
            ("previousValue", masked_prev), ("masked", True)))
        emit(f"{key}={masked}" if raw else stringify(payload))
        return EXIT_OK

    payload = result_json((
        ("updated", True), ("key", key), ("value", parsed),
        ("previousValue", previous)))
    emit(f"{key}={js_string(parsed)}" if raw else stringify(payload))
    return EXIT_OK


# --------------------------------------------------------------------------- #
# git — subprocess no cwd resolvido (a família commit fala com git assim)
# --------------------------------------------------------------------------- #
def run_git(argv, cwd=None, timeout=60):
    """(code, stdout, stderr, timed_out) para um git no cwd dado, saídas com
    strip (a forma do execGit do upstream). git ausente ou timeout devolve
    code None com o erro no campo stderr — quem decide o efeito é o
    chamador (a família commit trata como staging/commit falho)."""
    try:
        proc = subprocess.run(["git"] + list(argv), capture_output=True,
                              text=True, cwd=str(cwd) if cwd else None,
                              timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return None, "", str(e), True
    except (OSError, subprocess.SubprocessError) as e:
        return None, "", str(e), False
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), False


def is_git_ignored(cwd, target):
    """isGitIgnored do upstream (#2206): trailing slash removido antes do
    check-ignore --no-index; exit 0 = ignorado."""
    normalized = target.rstrip("/")
    code, _, _, _ = run_git(
        ["check-ignore", "-q", "--no-index", "--", normalized], cwd=cwd)
    return code == 0


# --------------------------------------------------------------------------- #
# leitura defensiva de config (para tudo que os handlers leem e não são donos)
# --------------------------------------------------------------------------- #
def load_scope_config_defensive(root=None):
    """O dict de .planning/config.json sem morrer nunca: ausente, ilegível ou
    quebrado degrada para {} — a doutrina do loadConfigResolved do upstream
    (config quebrada usa defaults) na forma reduzida do host único."""
    base = Path(root) if root else Path.cwd()
    path = base / PLANNING_CONFIG_RELPATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_scope_config_resolved(root=None):
    """(config, source, degraded) — a projeção de proveniência que o
    agent-skills --json ecoa: config do projeto legível → ("root", False);
    ausente → ("global-defaults", False); quebrado → degradado."""
    base = Path(root) if root else Path.cwd()
    path = base / PLANNING_CONFIG_RELPATH
    if not path.is_file():
        return {}, "global-defaults", False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}, "global-defaults", True
    if not isinstance(data, dict):
        return {}, "global-defaults", True
    return data, "root", False


def config_chain_value(key, fallback, root=None):
    """Cadeia de leitura dos handlers que não são donos da chave: config do
    escopo (defensiva) → default do schema (manifest em cadeia, sem morrer)
    → fallback hardcoded (o CONFIG_DEFAULTS bakeado do upstream)."""
    scope = load_scope_config_defensive(root)
    value, found = dotted_get(scope, key)
    if found:
        return value
    value, found = schema_default(key)
    if found:
        return value
    return fallback


def js_truthy(value):
    """A truthiness do JS para valores vindos de JSON: objeto/array são
    sempre truthy; false/0/""/null são falsy."""
    if isinstance(value, (dict, list)):
        return True
    return bool(value)


def find_project_root(cwd):
    """findProjectRoot reduzido: sobe procurando um diretório com .planning;
    sem âncora, o próprio cwd."""
    cur = Path(cwd).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / ".planning").is_dir():
            return candidate
    return cur


def output_like_binary(result, raw, raw_value=_UNDEFINED):
    """output() do io.cts: com --raw E rawValue definido sai String(rawValue);
    senão sai o JSON do resultado (indent 2, sem newline final)."""
    if raw and raw_value is not _UNDEFINED:
        emit(js_string(raw_value))
    else:
        emit(stringify(result))


# --------------------------------------------------------------------------- #
# handlers — família commit (TRIV-02)
# --------------------------------------------------------------------------- #
# sanitizeForPrompt do upstream (src/security.cts L334-L355), exato: chars
# invisíveis removidos e marcadores de injection neutralizados.
_INVISIBLE_CHARS_RE = re.compile("[\u200B-\u200F\u2028-\u202F\uFEFF\u00AD]")
_ROLE_TAG_RE = re.compile(r"<(\/?)\s*(?:system|assistant|human|user)\s*>",
                          re.IGNORECASE)
_INST_MARKER_RE = re.compile(r"\[(\/?)(SYSTEM|INST)\]", re.IGNORECASE)
_SYS_MARKER_RE = re.compile(r"<<\/?\s*SYS\s*>>", re.IGNORECASE)


def sanitize_for_prompt(text):
    if not text or not isinstance(text, str):
        return text
    s = _INVISIBLE_CHARS_RE.sub("", text)
    s = _ROLE_TAG_RE.sub(
        lambda m: f"＜{m.group(1) or ''}system-text＞", s)
    s = _INST_MARKER_RE.sub(
        lambda m: f"[{m.group(1)}{m.group(2).upper()}-TEXT]", s)
    s = _SYS_MARKER_RE.sub("«SYS-TEXT»", s)
    return s


def parse_commit_args(rest):
    """routeCommit (gsd-tools.cjs L906-L918): posicionais entre o verbo e a
    primeira flag (--files delimita) unidos com espaço formam a mensagem;
    --files coleta tudo depois que não começa com --."""
    raw = "--raw" in rest
    amend = "--amend" in rest
    no_verify = "--no-verify" in rest
    files_idx = rest.index("--files") if "--files" in rest else -1
    end = files_idx if files_idx != -1 else len(rest)
    message_args = [a for a in rest[:end] if not a.startswith("--")]
    message = " ".join(message_args) or None
    files = ([a for a in rest[files_idx + 1:] if not a.startswith("--")]
             if files_idx != -1 else [])
    return message, files, raw, amend, no_verify


def handle_commit(rest):
    """cmdCommit (src/commands.cts L793-L1035) em python sobre git. Cadeia de
    decisão do envelope na ordem do contrato; exit 0 em TODOS os caminhos de
    envelope — só mensagem ausente sem --amend sai 1. A pré-criação de branch
    do #1278 (branching_strategy) não é portada — divergência declarada."""
    message, files, raw, amend, no_verify = parse_commit_args(rest)
    if not message and not amend:
        die("commit message required", EXIT_CONTRACT)
    sanitized = sanitize_for_prompt(message) if message else message
    cwd = Path.cwd()

    # commit_docs, na semântica MEDIDA do binário (probe 2026-08-10): com
    # .planning gitignored o loadConfig NÃO aplica o default merged — config
    # sem a chave resolve falsy e o skip sai como skipped_commit_docs_false
    # ANTES do check de gitignore; só um commit_docs=true explícito alcança
    # o skipped_gitignored. Sem gitignore, o default do schema (true) vale.
    planning_ignored = is_git_ignored(cwd, ".planning")
    scope = load_scope_config_defensive()
    commit_docs, found = dotted_get(scope, "commit_docs")
    if not found:
        if planning_ignored:
            commit_docs = False
        else:
            value, ok = schema_default("commit_docs")
            commit_docs = value if ok else True
    if not js_truthy(commit_docs):
        result = {"committed": False, "skipped": True, "hash": None,
                  "reason": "skipped_commit_docs_false"}
        output_like_binary(result, raw, "skipped")
        return EXIT_OK

    if planning_ignored:
        result = {"committed": False, "skipped": True, "hash": None,
                  "reason": "skipped_gitignored"}
        output_like_binary(result, raw, "skipped")
        return EXIT_OK

    explicit = bool(files)
    to_stage = files if explicit else [".planning/"]
    _, pre_out, _, _ = run_git(["diff", "--cached", "--name-only"], cwd=cwd)
    pre_staged = {line.strip() for line in pre_out.splitlines()
                  if line.strip()}
    staged = []
    failures = []
    for f in to_stage:
        full = Path(os.path.abspath(os.path.join(str(cwd), f)))
        if not full.exists():
            if explicit:
                # --files explícito: arquivo ausente é pulado (#2014) — nunca
                # stagear a deleção de um arquivo temporariamente ausente.
                continue
            code, out, err, timed_out = run_git(
                ["rm", "--cached", "--ignore-unmatch", f], cwd=cwd)
            if code != 0:
                failures.append({"file": f, "error": err or out,
                                 "timed_out": timed_out})
        else:
            code, out, err, timed_out = run_git(["add", f], cwd=cwd)
            if code == 0:
                staged.append(f)
            else:
                failures.append({"file": f, "error": err or out,
                                 "timed_out": timed_out})

    if failures:
        # #2608: fail closed E limpo — desstagear só o que ESTA chamada
        # stageou, e reportar a causa do staging, não um sintoma adiante.
        to_unstage = [p for p in staged if p not in pre_staged]
        if to_unstage:
            run_git(["reset", "-q", "--"] + to_unstage, cwd=cwd)
        first = failures[0]
        result = {
            "committed": False,
            "hash": None,
            "reason": ("staging_timeout" if first["timed_out"]
                       else "staging_failed"),
            "file": first["file"],
            "error": first["error"],
            "failures": failures,
        }
        output_like_binary(result, raw, "failed")
        return EXIT_OK

    if explicit and not staged and not amend:
        result = {"committed": False, "hash": None,
                  "reason": "nothing_to_commit"}
        output_like_binary(result, raw, "nothing")
        return EXIT_OK

    merge_code, _, _, _ = run_git(
        ["rev-parse", "-q", "--verify", "MERGE_HEAD"], cwd=cwd)
    can_scope = explicit and staged and not amend and merge_code != 0
    commit_args = (["commit", "--amend", "--no-edit"] if amend
                   else ["commit", "-m", sanitized])
    if no_verify:
        commit_args.append("--no-verify")
    if can_scope:
        commit_args += ["--"] + staged
    code, out, err, _ = run_git(commit_args, cwd=cwd)
    if code != 0:
        if "nothing to commit" in out or "nothing to commit" in err:
            result = {"committed": False, "hash": None,
                      "reason": "nothing_to_commit"}
            output_like_binary(result, raw, "nothing")
            return EXIT_OK
        result = {"committed": False, "hash": None,
                  "reason": "commit_failed", "error": err or out}
        output_like_binary(result, raw, "failed")
        return EXIT_OK

    code, hash_out, _, _ = run_git(["rev-parse", "--short", "HEAD"], cwd=cwd)
    commit_hash = hash_out if code == 0 else None
    result = {"committed": True, "hash": commit_hash, "reason": "committed"}
    output_like_binary(result, raw, commit_hash or "committed")
    return EXIT_OK


def group_files_by_subrepo(files, sub_repos):
    """groupFilesBySubrepo do upstream (#311/#391): bucket por primeiro
    segmento e, dentro do bucket, vence o prefixo mais longo (sub-repos
    aninhados roteiam para o mais específico)."""
    by_first_seg = {}
    for repo in sub_repos:
        by_first_seg.setdefault(str(repo).split("/")[0], []).append(repo)
    grouped = {}
    unmatched = []
    for f in files:
        candidates = by_first_seg.get(f.split("/")[0]) or []
        match = None
        match_len = -1
        for repo in candidates:
            if f.startswith(str(repo) + "/") and len(str(repo)) > match_len:
                match = repo
                match_len = len(str(repo))
        if match is not None:
            grouped.setdefault(match, []).append(f)
        else:
            unmatched.append(f)
    return grouped, unmatched


def handle_commit_to_subrepo(rest):
    """cmdCommitToSubrepo (src/commands.cts L1088-L1184): agrupa os --files
    pelo sub-repo dono e commita um a um; falha por repo é comunicada dentro
    de repos.<nome>.reason; committed de topo é o OR dos repos. A mensagem
    NÃO passa pelo sanitize aqui — fidelidade ao binário medido."""
    raw = "--raw" in rest
    message = rest[0] if rest else None
    files_idx = rest.index("--files") if "--files" in rest else -1
    files = ([a for a in rest[files_idx + 1:] if not a.startswith("--")]
             if files_idx != -1 else [])
    if not message:
        die("commit message required", EXIT_CONTRACT)
    cwd = Path.cwd()
    config = load_scope_config_defensive()
    sub_repos = config.get("sub_repos")
    if not isinstance(sub_repos, list) or not sub_repos:
        die("no sub_repos configured in .planning/config.json", EXIT_CONTRACT)
    if not files:
        die("--files required for commit-to-subrepo", EXIT_CONTRACT)

    grouped, unmatched = group_files_by_subrepo(files, sub_repos)
    if unmatched:
        sys.stderr.write(
            f"Warning: {len(unmatched)} file(s) did not match any sub-repo "
            f"prefix: {', '.join(unmatched)}\n")

    repos = {}
    for repo, repo_files in grouped.items():
        repo_cwd = cwd / repo
        _, pre_out, _, _ = run_git(["diff", "--cached", "--name-only"],
                                   cwd=repo_cwd)
        pre_staged = {line.strip() for line in pre_out.splitlines()
                      if line.strip()}
        staged_rel = []
        failures = []
        for f in repo_files:
            rel = f[len(str(repo)) + 1:]
            code, out, err, timed_out = run_git(["add", rel], cwd=repo_cwd)
            if code == 0:
                staged_rel.append(rel)
            else:
                failures.append({"file": f, "error": err or out,
                                 "timed_out": timed_out})
        if failures:
            to_unstage = [p for p in staged_rel if p not in pre_staged]
            if to_unstage:
                run_git(["reset", "-q", "--"] + to_unstage, cwd=repo_cwd)
            first = failures[0]
            repos[repo] = {
                "committed": False, "hash": None, "files": repo_files,
                "reason": ("staging_timeout" if first["timed_out"]
                           else "staging_failed"),
                "error": first["error"],
            }
            continue
        merge_code, _, _, _ = run_git(
            ["rev-parse", "-q", "--verify", "MERGE_HEAD"], cwd=repo_cwd)
        can_scope = bool(staged_rel) and merge_code != 0
        commit_args = ["commit", "-m", message]
        if can_scope:
            commit_args += ["--"] + staged_rel
        code, out, err, _ = run_git(commit_args, cwd=repo_cwd)
        if code != 0:
            if "nothing to commit" in out or "nothing to commit" in err:
                repos[repo] = {"committed": False, "hash": None,
                               "files": repo_files,
                               "reason": "nothing_to_commit"}
            else:
                repos[repo] = {"committed": False, "hash": None,
                               "files": repo_files, "reason": "error",
                               "error": err}
            continue
        code, hash_out, _, _ = run_git(["rev-parse", "--short", "HEAD"],
                                       cwd=repo_cwd)
        repos[repo] = {"committed": True,
                       "hash": hash_out if code == 0 else None,
                       "files": repo_files}

    result = {"committed": any(r.get("committed") for r in repos.values()),
              "repos": repos}
    if unmatched:
        result["unmatched"] = unmatched
    raw_text = " ".join(f"{r}:{v.get('hash') or 'skip'}"
                        for r, v in repos.items())
    output_like_binary(result, raw, raw_text)
    return EXIT_OK


# --------------------------------------------------------------------------- #
# handlers — família skills (TRIV-02)
# --------------------------------------------------------------------------- #
_GLOBAL_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+(:[A-Za-z0-9_-]+)*$")


def _global_skills_base():
    """A base de skills globais do host claude: CLAUDE_CONFIG_DIR ou
    ~/.claude, subdiretório skills/."""
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    root = Path(base) if base else (Path.home() / ".claude")
    return root / "skills"


def _validate_project_skill_path(root, skill_path):
    """(safe, error) — a redução do validatePath do upstream: caminho
    absoluto ou que escapa a raiz do projeto (inclusive por symlink) é
    inseguro."""
    if os.path.isabs(skill_path):
        return False, "absolute paths are not allowed"
    resolved = os.path.realpath(os.path.join(str(root), skill_path))
    root_real = os.path.realpath(str(root))
    if resolved != root_real and not resolved.startswith(root_real + os.sep):
        return False, "path escapes the project root"
    return True, None


def build_agent_skills_block(config, agent_type, project_root, diagnostics):
    """buildAgentSkillsBlock (src/init.cts L3167-L3320) reduzido ao host
    claude: entradas project-relative resolvem <path>/SKILL.md; global:
    com nome namespaced vira diretiva do Skill tool; global: simples resolve
    na base de skills do claude. Warnings vão para stderr E para o canal
    warnings do envelope."""
    def warn(message):
        sys.stderr.write(message)
        diagnostics.append(message.rstrip("\n"))

    if not config or not config.get("agent_skills") or not agent_type:
        return ""
    agent_skills = config.get("agent_skills")
    if not isinstance(agent_skills, dict):
        return ""
    skill_paths = agent_skills.get(agent_type)
    if not skill_paths:
        return ""
    if isinstance(skill_paths, str):
        skill_paths = [skill_paths]
    if not isinstance(skill_paths, list):
        kind = type(skill_paths).__name__
        warn(f'[agent-skills] WARNING: Agent "{agent_type}" has a malformed '
             f"agent_skills value (expected string or array, got {kind}) "
             "— ignoring\n")
        return ""
    if not skill_paths:
        return ""

    entries = []
    for skill_path in skill_paths:
        if not isinstance(skill_path, str):
            kind = type(skill_path).__name__
            warn("[agent-skills] WARNING: Ignoring non-string skill entry "
                 f"({kind}) — skipping\n")
            continue
        if skill_path.startswith("global:"):
            name = skill_path[7:]
            if not name:
                warn('[agent-skills] WARNING: "global:" prefix with empty '
                     "skill name — skipping\n")
                continue
            if not _GLOBAL_SKILL_NAME_RE.match(name):
                warn(f'[agent-skills] WARNING: Invalid global skill name '
                     f'"{name}" — skipping\n')
                continue
            if ":" in name:
                # Skill namespaced de plugin: diretiva, não @-include (claude
                # é Skill-tool-capable).
                entries.append(("directive", name))
                continue
            global_dir = _global_skills_base() / name
            display = f"~/.claude/skills/{name}"
            if not (global_dir / "SKILL.md").is_file():
                warn(f'[agent-skills] WARNING: Global skill not found at '
                     f'"{display}/SKILL.md" — skipping\n')
                continue
            entries.append(("include", f"{global_dir}/SKILL.md"))
            continue
        safe, error = _validate_project_skill_path(project_root, skill_path)
        if not safe:
            warn(f'[agent-skills] WARNING: Skipping unsafe path '
                 f'"{skill_path}": {error}\n')
            continue
        if not (Path(project_root) / skill_path / "SKILL.md").is_file():
            warn(f'[agent-skills] WARNING: Skill not found at '
                 f'"{skill_path}/SKILL.md" — skipping\n')
            continue
        entries.append(("include", f"{skill_path}/SKILL.md"))

    if not entries:
        warn(f'[agent-skills] WARNING: Agent "{agent_type}" has '
             f"{len(skill_paths)} configured skill path(s) but none resolved "
             "to a valid skill — all were skipped (see warnings above)\n")
        return ""

    lines = "\n".join(
        (f"- Load the `{ref}` skill via the Skill tool before proceeding "
         "(plugin-provided).") if kind == "directive"
        else f"- @{ref.replace(os.sep, '/')}"
        for kind, ref in entries)
    return ("<agent_skills>\nRead these user-configured skills:\n"
            f"{lines}\n</agent_skills>")


def handle_agent_skills(rest):
    """cmdAgentSkills (src/init.cts L3326-L3449): default emite o bloco XML
    cru (expansão shell ${AGENT_SKILLS_*}); --json emite o IR tipado com o
    envelope Resolution embutido em .value. Sem <agent-type> devolve bloco
    vazio com exit 0. O fallback de persona (#2454) é gated a runtimes
    não-claude no upstream e NÃO é portado (host único claude) — divergência
    declarada na tabela da fase."""
    json_mode = "--json" in rest
    raw = "--raw" in rest
    toks = [t for t in rest if t not in ("--json", "--raw")]
    agent_type = toks[0] if toks else None
    if not agent_type:
        output_like_binary("", raw, "")
        return EXIT_OK

    project_root = find_project_root(Path.cwd())
    config, source, degraded = load_scope_config_resolved(project_root)
    warnings = []
    block = build_agent_skills_block(config, agent_type, project_root,
                                    warnings)

    agent_skills_map = (config.get("agent_skills")
                       if isinstance(config.get("agent_skills"), dict)
                       else {})
    configured = agent_type in agent_skills_map

    skill_paths = agent_skills_map.get(agent_type, []) if configured else []
    if not configured:
        reason = "not_configured"
        skill_paths = []
    else:
        if isinstance(skill_paths, str):
            skill_paths = [skill_paths]
        if not isinstance(skill_paths, list):
            skill_paths = []
        non_blank = [p for p in skill_paths
                     if isinstance(p, str) and p.strip()]
        if not skill_paths or not non_blank:
            reason = "configured_empty"
            skill_paths = []
            sys.stderr.write(
                f'[agent-skills] WARNING: Agent "{agent_type}" is configured '
                "in agent_skills but has no skill paths — skills_count will "
                "be 0\n")
        elif not block:
            reason = "configured_unresolved"
        else:
            reason = "resolved"

    normalized = skill_paths if isinstance(skill_paths, list) else []

    if json_mode:
        envelope = {
            "agent_type": agent_type,
            "block": block or "",
            "skills_count": len(normalized),
            "warnings": warnings,
            "configured": configured,
            "reason": reason,
            "source": source,
            "degraded": degraded,
            "value": {"block": block or "",
                      "skills_count": len(normalized)},
        }
        output_like_binary(envelope, raw)
        return EXIT_OK

    # #1400: o bloco cru sai pelo caminho síncrono — aqui, raw forçado.
    output_like_binary(block or "", True, block or "")
    return EXIT_OK


# --------------------------------------------------------------------------- #
# handlers — família loop-hooks (TRIV-03): tabela NATIVA
# --------------------------------------------------------------------------- #
# O vocabulário canônico de 12 pontos (loop-host-contract do upstream, o
# mesmo fechado assertado em tests/capability.bats).
CANONICAL_POINTS = (
    "discuss:pre", "discuss:post",
    "plan:pre", "plan:post",
    "execute:pre", "execute:wave:pre", "execute:wave:post", "execute:post",
    "verify:pre", "verify:post",
    "ship:pre", "ship:post",
)

# A FONTE da tabela nativa: o manifest da capability do próprio cairn. O
# capability-registry de 7k linhas do upstream NÃO é reimplementado — os
# hooks nascem das entradas por point de steps/contributions/gates daqui.
CAPABILITY_JSON = (Path(__file__).resolve().parent.parent
                   / "capability" / "capability.json")


def load_capability_native_table():
    """Leitura DEFENSIVA do capability.json do cairn: ausente, ilegível ou
    quebrado degrada para None (tabela vazia) — nunca mata o verbo."""
    try:
        doc = json.loads(CAPABILITY_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _activation_value(when, config, cap_doc):
    """isActive do loop-resolver, reduzido à precedência de host único: sem
    `when` o hook é incondicional; `when` malformado é INATIVO; a chave
    resolve no config do projeto e, ausente, no default declarado pelo
    próprio capability.json (.config[chave].default)."""
    if when is None:
        return True
    if not isinstance(when, str) or not when:
        return False
    value, found = dotted_get(config, when)
    if found:
        return js_truthy(value)
    cap_config = (cap_doc.get("config")
                  if isinstance(cap_doc.get("config"), dict) else {})
    entry = cap_config.get(when)
    if isinstance(entry, dict):
        return js_truthy(entry.get("default"))
    return False


def _to_fragment(value):
    if not isinstance(value, dict):
        return None
    fragment = {}
    if isinstance(value.get("inline"), str):
        fragment["inline"] = value["inline"]
    if isinstance(value.get("path"), str):
        fragment["path"] = value["path"]
    return fragment or None


def _to_string_array(value):
    if not isinstance(value, list):
        return []
    return [x for x in value if isinstance(x, str)]


def resolve_native_hooks(point, config):
    """resolveLoopHooks sobre a tabela nativa: itera steps, contributions e
    gates do capability.json filtrando por point e ativação; a forma de cada
    ActiveHook segue a ordem de montagem do upstream."""
    doc = load_capability_native_table()
    if doc is None:
        return []
    cap_id = doc.get("id") if isinstance(doc.get("id"), str) else ""
    hooks = []
    for kind, key in (("step", "steps"), ("contribution", "contributions"),
                      ("gate", "gates")):
        entries = doc.get(key)
        if not isinstance(entries, list):
            continue
        for h in entries:
            if not isinstance(h, dict) or h.get("point") != point:
                continue
            if not _activation_value(h.get("when"), config, doc):
                continue
            when = h.get("when") if isinstance(h.get("when"), str) else None
            on_error = (h.get("onError")
                        if isinstance(h.get("onError"), str) else None)
            active = {"capId": cap_id, "kind": kind}
            if kind == "step":
                ref = h.get("ref") if isinstance(h.get("ref"), dict) else None
                fragment = _to_fragment(h.get("fragment"))
                if ref is not None:
                    active["ref"] = ref
                if fragment is not None:
                    active["fragment"] = fragment
                if when is not None:
                    active["when"] = when
                for field in ("produces", "consumes"):
                    arr = _to_string_array(h.get(field))
                    if arr:
                        active[field] = arr
                if on_error is not None:
                    active["onError"] = on_error
            elif kind == "contribution":
                into = (h.get("into")
                        if isinstance(h.get("into"), str) else None)
                fragment = _to_fragment(h.get("fragment"))
                if into is not None:
                    active["into"] = into
                if fragment is not None:
                    active["fragment"] = fragment
                if when is not None:
                    active["when"] = when
                for field in ("produces", "consumes"):
                    arr = _to_string_array(h.get(field))
                    if arr:
                        active[field] = arr
                if on_error is not None:
                    active["onError"] = on_error
            else:  # gate
                if when is not None:
                    active["when"] = when
                if h.get("check") is not None:
                    active["check"] = h.get("check")
                if isinstance(h.get("blocking"), bool):
                    active["blocking"] = h.get("blocking")
                if on_error is not None:
                    active["onError"] = on_error
            hooks.append(active)
    return hooks


def render_native_hooks(point, hooks):
    """renderLoopHooks do upstream, portado: vazio vira o placeholder; steps
    com ordinal, contributions em bloco rotulado, gates em uma linha."""
    if not hooks:
        return f"_No active hooks at {point}._"
    lines = []
    step_ordinal = 0
    for h in hooks:
        if h["kind"] == "step":
            step_ordinal += 1
            ref = h.get("ref") or {}
            if isinstance(ref, dict) and ref.get("skill"):
                ref_str = f"skill:{ref['skill']}"
            elif isinstance(ref, dict) and ref.get("agent"):
                ref_str = f"agent:{ref['agent']}"
            else:
                ref_str = json.dumps(ref, separators=(",", ":"),
                                     ensure_ascii=False)
            lines.append(f"### Step {step_ordinal}: {ref_str} ({h['capId']})")
            if h.get("produces"):
                lines.append(f"- produces: {', '.join(h['produces'])}")
            if h.get("consumes"):
                lines.append(f"- consumes: {', '.join(h['consumes'])}")
            if h.get("when"):
                lines.append(f"- when: `{h['when']}`")
            if h.get("onError"):
                lines.append(f"- onError: {h['onError']}")
            fragment = h.get("fragment") or {}
            if fragment.get("inline"):
                lines.append("")
                lines.append(fragment["inline"])
            elif fragment.get("path"):
                lines.append("")
                lines.append("_Step fragment path is declared but not "
                             f"rendered by loop-resolver: {fragment['path']}_")
            lines.append("")
        elif h["kind"] == "contribution":
            into = h.get("into", "(unset)")
            lines.append(f'<contribution from="{h["capId"]}" into="{into}">')
            fragment = h.get("fragment") or {}
            if fragment.get("inline"):
                lines.append(fragment["inline"])
            elif fragment.get("path"):
                lines.append("_Contribution fragment path is declared but "
                             "not rendered by loop-resolver: "
                             f"{fragment['path']}_")
            if h.get("produces"):
                lines.append(f"- produces: {', '.join(h['produces'])}")
            if h.get("consumes"):
                lines.append(f"- consumes: {', '.join(h['consumes'])}")
            if h.get("when"):
                lines.append(f"- when: `{h['when']}`")
            if h.get("onError"):
                lines.append(f"- onError: {h['onError']}")
            lines.append("</contribution>")
            lines.append("")
        else:  # gate
            check = h.get("check")
            if check is None:
                check_str = "(none)"
            elif isinstance(check, (dict, list)):
                check_str = json.dumps(check, separators=(",", ":"),
                                       ensure_ascii=False)
            elif isinstance(check, (str, int, float, bool)):
                check_str = js_string(check)
            else:
                check_str = "(complex)"
            blocking = js_string(bool(h.get("blocking", False)))
            on_error = h.get("onError", "skip")
            lines.append(f"**Gate** ({h['capId']}): check={check_str}, "
                         f"blocking={blocking}, onError={on_error}")
            if h.get("when"):
                lines.append(f"- when: `{h['when']}`")
            lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _parse_dual_form_flag(toks, name, example=None):
    """routeLoop: --nome <valor> e --nome=<valor>; presença sem valor morre
    exit 1 com a mensagem do upstream."""
    suffix = f" (e.g. --{name} {example})" if example else ""
    eq_prefix = f"--{name}="
    for t in toks:
        if t.startswith(eq_prefix):
            value = t[len(eq_prefix):].strip()
            if not value:
                die(f"Missing value for --{name}{suffix}", EXIT_CONTRACT)
            return value
    if f"--{name}" in toks:
        idx = toks.index(f"--{name}")
        value = toks[idx + 1] if idx + 1 < len(toks) else None
        if not value or value.startswith("--"):
            die(f"Missing value for --{name}{suffix}", EXIT_CONTRACT)
        return value
    return None


def handle_loop(rest):
    """loop render-hooks <point> (spelling top-level `loop`): valida o point
    contra o vocabulário canônico de 12, monta activeHooks da tabela NATIVA
    e emite o envelope {point, activeHooks, rendered, warnings}. `--raw`
    emite o MESMO envelope (o output do binário sem rawValue é JSON nos dois
    modos); `--active-cap <capId>` imprime exatamente true|false + newline,
    sem envelope. warnings sai SEMPRE (a forma das 4 chaves do contrato;
    o binário omite a chave vazia — divergência declarada)."""
    toks = [t for t in rest if t != "--raw"]
    sub = toks[0] if toks else None
    if sub != "render-hooks":
        die(f"Unknown loop subcommand: {sub}. Available: render-hooks",
            EXIT_CONTRACT)
    config_dir = _parse_dual_form_flag(toks, "config-dir")
    active_cap = _parse_dual_form_flag(toks, "active-cap", example="tdd")
    runtime_override = _parse_dual_form_flag(toks, "runtime")
    if config_dir:
        # path.resolve do upstream; em host único influencia só a resolução
        # de diretório — nenhum estado multi-runtime a consultar aqui.
        config_dir = os.path.abspath(config_dir)
    _ = runtime_override  # #2003: aceito nas duas formas; host único claude
    point = toks[1] if len(toks) > 1 else None
    if not point:
        die("loop render-hooks requires a <point> argument. Valid points: "
            + ", ".join(CANONICAL_POINTS), EXIT_CONTRACT)
    if point not in CANONICAL_POINTS:
        die(f'Invalid loop point: "{point}". Valid points: '
            + ", ".join(CANONICAL_POINTS), EXIT_CONTRACT)
    config = load_scope_config_defensive()
    hooks = resolve_native_hooks(point, config)
    if active_cap is not None:
        is_active = any(h.get("capId") == active_cap for h in hooks)
        sys.stdout.write("true\n" if is_active else "false\n")
        return EXIT_OK
    envelope = {
        "point": point,
        "activeHooks": hooks,
        "rendered": render_native_hooks(point, hooks),
        "warnings": [],
    }
    emit(stringify(envelope))
    return EXIT_OK


# --------------------------------------------------------------------------- #
# handlers — família dispatch/model (TRIV-03), host único fail-closed
# --------------------------------------------------------------------------- #
# Tabela estática de host: copiada de gsd-core/bin/lib/capability-registry.cjs
# runtimes.claude.runtime (tag v1.10.0, commit 68a04cc) — dispatch +
# harnessIsolationFlag. Runtime fora da tabela resolve fail-closed
# (none / true / eco do requested); o registry multi-host não é vendorizado.
HOST_RUNTIMES = {
    "claude": {
        "dispatch": {
            "namedDispatch": True,
            "nested": True,
            "maxDepth": 5,
            "background": True,
            "subagentToolkit": "full",
            "backgroundDispatch": False,
            "isolation": "harness-worktree",
        },
        "harnessIsolationFlag": 'isolation="worktree"',
    },
}

VALID_ISOLATION = ("harness-worktree", "orchestrator-worktree", "none")


def resolve_runtime():
    """A precedência de config-get runtime: GSD_RUNTIME > config.runtime >
    'claude' (o marcador per-install .gsd-runtime do upstream não existe no
    cairn — coberto pela divergência da tabela estática)."""
    env = os.environ.get("GSD_RUNTIME")
    if env:
        return env
    config = load_scope_config_defensive()
    runtime = config.get("runtime")
    if isinstance(runtime, str) and runtime:
        return runtime
    return "claude"


def _flag_value(rest, flag):
    """Valor posicional de uma flag, à maneira dos routers do gsd-tools:
    o token seguinte, quando existe e não começa com --."""
    if flag not in rest:
        return None
    idx = rest.index(flag)
    value = rest[idx + 1] if idx + 1 < len(rest) else None
    if value is None or value.startswith("--"):
        return None
    return value


def write_dispatch_isolation_sentinel(cwd, isolation, harness_flag,
                                      phase, plan):
    """writeDispatchIsolationSentinel (gsd-tools.cjs L1776-L1800): payload
    compacto {isolation, harness_flag, phase, plan, written_at} publicado por
    temp único + rename atômico. NUNCA levanta — falha de escrita não falha
    o verbo."""
    try:
        sentinel_dir = Path(cwd) / ".gsd"
        sentinel_path = sentinel_dir / "dispatch-isolation-sentinel.json"
        payload = {
            "isolation": isolation,
            "harness_flag": harness_flag or None,
            "phase": phase or None,
            "plan": plan or None,
            "written_at": int(time.time() * 1000),
        }
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        tmp = sentinel_path.with_name(
            sentinel_path.name + f".tmp-{os.getpid()}-{int(time.time() * 1000)}")
        tmp.write_text(json.dumps(payload, separators=(",", ":"),
                                  ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, sentinel_path)
    except OSError:
        pass


def handle_dispatch_isolation(rest):
    """routeDispatchIsolation (#3045 CORE REDESIGN): resolve o modo do
    vocabulário fechado com fail-closed TOTAL para none (ADR-1239), persiste
    a decisão no sentinel em TODA invocação, e emite o modo cru (--raw e
    default) ou o envelope {runtime, isolation, exec, harnessFlag} (--json).
    Sempre exit 0."""
    isolation = "none"
    runtime_id = None
    exec_resolved = None
    harness_flag = None
    try:
        runtime_id = resolve_runtime()
        entry = HOST_RUNTIMES.get(runtime_id)
        declared = ((entry or {}).get("dispatch") or {}).get("isolation")
        if isinstance(declared, str) and declared in VALID_ISOLATION:
            isolation = declared
        if isolation == "harness-worktree":
            flag = (entry or {}).get("harnessIsolationFlag")
            if isinstance(flag, str) and flag:
                harness_flag = flag
            else:
                # host declarando harness isolation sem flag não dá ao
                # scheduler nada a passar — degrada para sequencial
                isolation = "none"
        if isolation == "orchestrator-worktree":
            # nenhuma entrada da tabela de host único declara
            # orchestrator-worktree; sem exec resolvível o modo degrada
            isolation = "none"
    except Exception:
        isolation = "none"
        exec_resolved = None
        harness_flag = None
    forced = _flag_value(rest, "--force-isolation")
    if forced and forced in VALID_ISOLATION:
        isolation = forced
        if isolation == "none":
            harness_flag = None
            exec_resolved = None
    phase_arg = _flag_value(rest, "--phase")
    plan_arg = _flag_value(rest, "--plan")
    write_dispatch_isolation_sentinel(Path.cwd(), isolation, harness_flag,
                                      phase_arg, plan_arg)
    if "--json" in rest:
        output_like_binary({"runtime": runtime_id, "isolation": isolation,
                            "exec": exec_resolved,
                            "harnessFlag": harness_flag}, "--raw" in rest)
    else:
        emit(isolation)
    return EXIT_OK


def should_flatten_dispatch(dispatch):
    """shouldFlattenDispatch (src/host-integration.cts L607-L621), exato:
    só um host que pode backgroundar um orquestrador aninhável com folga de
    profundidade evita o flatten — qualquer dúvida devolve True."""
    if not isinstance(dispatch, dict):
        return True
    can_background = (dispatch.get("background") is True
                      and dispatch.get("backgroundDispatch") is True)
    if not can_background:
        return True
    can_nest = (dispatch.get("nested") is True
                and dispatch.get("subagentToolkit") == "full")
    if not can_nest:
        return True
    depth = dispatch.get("maxDepth")
    if (not isinstance(depth, (int, float)) or isinstance(depth, bool)
            or not math.isfinite(depth)):
        depth = 0
    depth_sufficient = depth < 0 or depth > 1
    return not depth_sufficient


def handle_dispatch_should_flatten(rest):
    """routeDispatchShouldFlatten (#1708/#853): --raw e default imprimem
    exatamente true|false; --json emite {runtime, shouldFlatten, dispatch}.
    Fail-closed: runtime desconhecido, dispatch ausente ou qualquer erro
    imprime true. Sempre exit 0. Na tabela de host único o claude resolve
    true — backgroundDispatch:false no descritor vendorizado (o mesmo valor
    do binário medido)."""
    try:
        runtime_id = resolve_runtime()
        entry = HOST_RUNTIMES.get(runtime_id)
        dispatch = (entry or {}).get("dispatch") if entry else None
        should = (should_flatten_dispatch(dispatch)
                  if dispatch is not None else True)
        if "--json" in rest:
            output_like_binary({"runtime": runtime_id,
                                "shouldFlatten": should,
                                "dispatch": dispatch}, "--raw" in rest)
        else:
            emit("true" if should else "false")
    except Exception:
        emit("true")
    return EXIT_OK


# resolveDispatchType (src/host-integration.cts L654-L679): em runtime de
# named-dispatch (claude, e todo dispatch desconhecido/ausente) o verbo é
# identidade sobre o requested; só namedDispatch:false mapeia por sufixo.
DISPATCH_TYPE_SUFFIX_MAP = (
    (re.compile(r"-?(planner|roadmapper|selector|spec)$", re.IGNORECASE),
     "plan"),
    (re.compile(r"-?(researcher|mapper|checker|verifier|auditor|analyzer|"
                r"synthesizer|profiler|curator|classifier|reviewer)$",
                re.IGNORECASE), "explore"),
)
GENERIC_NAMES_TO_CODER = frozenset((
    "general-purpose", "general", "default", "sonnet", "opus", "haiku",
))


def resolve_dispatch_type(requested, dispatch):
    if not isinstance(requested, str) or not requested:
        return "coder"
    if isinstance(dispatch, dict) and dispatch.get("namedDispatch") is False:
        if requested in GENERIC_NAMES_TO_CODER:
            return "coder"
        for pattern, builtin in DISPATCH_TYPE_SUFFIX_MAP:
            if pattern.search(requested):
                return builtin
        return "coder"
    return requested


def handle_resolve_dispatch_type(rest):
    """routeResolveDispatchType (#2508 Phase 4 Option A): identidade em host
    único; fail-closed total ecoa o requested inalterado. --requested ausente
    vira string vazia e resolve para 'coder'. Sempre exit 0."""
    requested = _flag_value(rest, "--requested") or ""
    try:
        runtime_id = resolve_runtime()
        entry = HOST_RUNTIMES.get(runtime_id)
        dispatch = (entry or {}).get("dispatch") if entry else None
        resolved = resolve_dispatch_type(requested, dispatch)
        if "--json" in rest:
            output_like_binary({"runtime": runtime_id,
                                "requested": requested,
                                "resolved": resolved,
                                "dispatch": dispatch}, "--raw" in rest)
        else:
            emit(str(resolved))
    except Exception:
        emit(str(requested))
    return EXIT_OK


# --------------------------------------------------------------------------- #
# handlers — resolve-model (TRIV-03)
# --------------------------------------------------------------------------- #
# MODEL_PROFILES: o manifest de defaults resolvido pela cadeia do plano 01
# NÃO carrega model_profiles (medido em gsd-core/bin/shared/
# config-defaults.manifest.json da tag), então a tabela vem COPIADA do
# catálogo do clone — gsd-core/bin/shared/model-catalog.json .agents
# (tag v1.10.0, commit 68a04cc) — na projeção (quality=golden, balanced,
# budget, routingTier). O fallback é offline por construção: resolve-model
# não pode depender do cache.
MODEL_CATALOG_AGENTS = {
    "gsd-planner": ("opus", "opus", "sonnet", "heavy"),
    "gsd-roadmapper": ("opus", "sonnet", "sonnet", "heavy"),
    "gsd-executor": ("opus", "sonnet", "sonnet", "standard"),
    "gsd-phase-researcher": ("opus", "sonnet", "haiku", "standard"),
    "gsd-project-researcher": ("opus", "sonnet", "haiku", "standard"),
    "gsd-research-synthesizer": ("sonnet", "sonnet", "haiku", "light"),
    "gsd-debugger": ("opus", "sonnet", "sonnet", "heavy"),
    "gsd-codebase-mapper": ("sonnet", "haiku", "haiku", "light"),
    "gsd-verifier": ("sonnet", "sonnet", "haiku", "standard"),
    "gsd-plan-checker": ("sonnet", "sonnet", "haiku", "light"),
    "gsd-integration-checker": ("sonnet", "sonnet", "haiku", "light"),
    "gsd-nyquist-auditor": ("sonnet", "sonnet", "haiku", "light"),
    "gsd-pattern-mapper": ("sonnet", "sonnet", "haiku", "light"),
    "gsd-ui-researcher": ("opus", "sonnet", "haiku", "standard"),
    "gsd-ui-checker": ("sonnet", "sonnet", "haiku", "light"),
    "gsd-ui-auditor": ("sonnet", "sonnet", "haiku", "light"),
    "gsd-doc-writer": ("opus", "sonnet", "haiku", "standard"),
    "gsd-doc-verifier": ("sonnet", "sonnet", "haiku", "light"),
    "gsd-advisor-researcher": ("opus", "sonnet", "haiku", "standard"),
    "gsd-ai-researcher": ("opus", "sonnet", "haiku", "standard"),
    "gsd-assumptions-analyzer": ("opus", "sonnet", "sonnet", "heavy"),
    "gsd-code-fixer": ("opus", "sonnet", "sonnet", "standard"),
    "gsd-code-reviewer": ("opus", "sonnet", "sonnet", "standard"),
    "gsd-debug-session-manager": ("opus", "sonnet", "sonnet", "heavy"),
    "gsd-doc-classifier": ("sonnet", "haiku", "haiku", "light"),
    "gsd-doc-synthesizer": ("opus", "sonnet", "haiku", "standard"),
    "gsd-domain-researcher": ("opus", "sonnet", "haiku", "standard"),
    "gsd-eval-auditor": ("opus", "sonnet", "haiku", "standard"),
    "gsd-eval-planner": ("opus", "opus", "sonnet", "heavy"),
    "gsd-framework-selector": ("opus", "sonnet", "sonnet", "heavy"),
    "gsd-intel-updater": ("opus", "sonnet", "haiku", "light"),
    "gsd-mempalace-curator": ("sonnet", "sonnet", "haiku", "light"),
    "gsd-security-auditor": ("opus", "sonnet", "sonnet", "heavy"),
    "gsd-user-profiler": ("opus", "sonnet", "sonnet", "heavy"),
}
ADAPTIVE_TIER_MAP = {"heavy": "opus", "standard": "sonnet", "light": "haiku"}
MODEL_ALIAS_MAP = {"opus": "claude-opus-4-8", "sonnet": "claude-sonnet-5",
                   "haiku": "claude-haiku-4-5"}
EFFORT_SET = frozenset(("low", "medium", "high", "xhigh"))
# effort do manifest da tag (fallback quando a cadeia não resolve):
EFFORT_DEFAULTS_FALLBACK = {
    "default": "high",
    "routing_tier_defaults": {"light": "low", "standard": "high",
                              "heavy": "xhigh"},
    "agent_overrides": {},
}


def resolve_model_alias(config, agent_type, profile):
    """resolveModelInternal reduzido ao caminho de host único claude: perfil
    → tier alias do MODEL_PROFILES, com resolve_model_ids=true materializando
    o id completo. As camadas model_overrides/model_policy/runtime-tier do
    upstream não são portadas — divergência declarada."""
    meta = MODEL_CATALOG_AGENTS.get(agent_type)
    profile_lc = str(profile).lower()
    if not meta:
        if profile_lc == "quality":
            return "opus"
        if profile_lc == "budget":
            return "haiku"
        if profile_lc == "inherit":
            return "inherit"
        return "sonnet"
    quality, balanced, budget, routing_tier = meta
    if profile_lc == "inherit":
        return "inherit"
    profiles = {"quality": quality, "balanced": balanced, "budget": budget,
                "adaptive": ADAPTIVE_TIER_MAP.get(routing_tier)}
    alias = profiles.get(profile_lc) or balanced
    if config.get("resolve_model_ids") is True:
        return MODEL_ALIAS_MAP.get(alias, alias)
    return alias


def resolve_effort(config, agent_type):
    """resolveEffortInternal na ordem do upstream: agent_overrides →
    routing_tier_defaults pelo tier default do agente → effort.default. A
    camada canônica (config sem bloco effort) vem do manifest resolvido pela
    cadeia, senão da cópia embutida."""
    effort_cfg = (config.get("effort")
                  if isinstance(config.get("effort"), dict) else None)
    if effort_cfg is None:
        value, found = schema_default("effort")
        source = value if found and isinstance(value, dict) \
            else EFFORT_DEFAULTS_FALLBACK
    else:
        source = effort_cfg
    overrides = source.get("agent_overrides")
    if isinstance(overrides, dict):
        v = overrides.get(agent_type)
        if isinstance(v, str) and v in EFFORT_SET:
            return v
    meta = MODEL_CATALOG_AGENTS.get(agent_type)
    if meta:
        tier_defaults = source.get("routing_tier_defaults")
        if isinstance(tier_defaults, dict):
            v = tier_defaults.get(meta[3])
            if isinstance(v, str) and v in EFFORT_SET:
                return v
    default = source.get("default")
    if isinstance(default, str) and default in EFFORT_SET:
        return default
    return "high"


def handle_resolve_model(rest):
    """cmdResolveModel (src/commands.cts L495-L510): envelope {model,
    profile, effort} (+unknown_agent:true fora do MODEL_PROFILES, exit 0);
    sem --raw sai o JSON, com --raw só o model id, --pick extrai uma chave.
    agent-type ausente é exit 1."""
    raw = False
    pick = None
    agent_type = None
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "--raw":
            raw = True
            i += 1
        elif tok == "--pick":
            pick = rest[i + 1] if i + 1 < len(rest) else None
            i += 2
        elif tok.startswith("-"):
            i += 1
        else:
            if agent_type is None:
                agent_type = tok
            i += 1
    if not agent_type:
        die("agent-type required", EXIT_CONTRACT)
    config = load_scope_config_defensive()
    profile = config.get("model_profile")
    if not profile:
        value, found = schema_default("model_profile")
        profile = value if found and value else "balanced"
    model = resolve_model_alias(config, agent_type, profile)
    effort = resolve_effort(config, agent_type)
    result = {"model": model, "profile": profile, "effort": effort}
    if agent_type not in MODEL_CATALOG_AGENTS:
        result["unknown_agent"] = True
    if pick:
        emit(js_string(result[pick]) if pick in result else "undefined")
        return EXIT_OK
    output_like_binary(result, raw, model)
    return EXIT_OK


HANDLERS = {
    "config-get": handle_config_get,
    "config-set": handle_config_set,
    "commit": handle_commit,
    "commit-to-subrepo": handle_commit_to_subrepo,
    "agent-skills": handle_agent_skills,
    "loop": handle_loop,
    "dispatch-isolation": handle_dispatch_isolation,
    "dispatch-should-flatten": handle_dispatch_should_flatten,
    "resolve-model": handle_resolve_model,
    "resolve-dispatch-type": handle_resolve_dispatch_type,
}


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    argv = sys.argv[1:]
    if not argv:
        die(USAGE, EXIT_USAGE)
    if argv[0] == "--list-implemented":
        # Superfície de TESTE (fora dos contratos — ver docstring): o guard
        # de cobertura do bats compara esta enumeração com o universo de
        # contracts.json via comm, sem manter lista paralela de verbos.
        # Agregada (D-01): o dispatcher roda cada irmão EXISTENTE com
        # --list-implemented e concatena com as próprias chaves — o contrato
        # de superfície única se mantém e o bats não muda.
        verbs = set(HANDLERS)
        here = Path(__file__).resolve().parent
        for script in sorted(set(FAMILY_SCRIPT.values())):
            sibling = here / script
            if not sibling.is_file():
                continue
            try:
                proc = subprocess.run(
                    [sys.executable, str(sibling), "--list-implemented"],
                    capture_output=True, text=True)
            except (OSError, subprocess.SubprocessError):
                continue
            if proc.returncode == 0:
                verbs.update(line.strip() for line in
                             proc.stdout.splitlines() if line.strip())
        for verb in sorted(verbs):
            print(verb)
        sys.exit(EXIT_OK)
    if argv[0].startswith("-"):
        die(f"flag desconhecida antes do verbo: {argv[0]}\n{USAGE}",
            EXIT_USAGE)
    routes = build_routes()
    max_words = max(len(s.split()) for s in routes)
    for n in range(min(max_words, len(argv)), 0, -1):
        spelling = " ".join(argv[:n])
        hit = routes.get(spelling)
        if hit is None:
            continue
        verb, family = hit
        handler = HANDLERS.get(verb)
        if handler is None:
            # D-01: família servida por irmão vira exec (substituição de
            # processo — stdout/stderr/exit preservados, precedente shell
            # de cairn-gsd.sh); o irmão recebe o VERBO canônico, nunca o
            # spelling. Irmão ausente do disco cai no die exit 4 abaixo.
            script = script_for(verb, family)
            if script is not None:
                sibling = Path(__file__).resolve().parent / script
                if sibling.is_file():
                    os.execv(sys.executable,
                             [sys.executable, str(sibling), verb]
                             + argv[n:])
            die(f"verbo '{verb}' pertence à família '{family}', entregue "
                f"pela {phase_for(verb, family)} — ainda não implementado "
                f"neste script", EXIT_UNIMPLEMENTED)
        sys.exit(handler(argv[n:]))
    die(f"verbo desconhecido (fora do universo do contrato): "
        f"{' '.join(argv[:2])}\n{USAGE}", EXIT_USAGE)


if __name__ == "__main__":
    main()
