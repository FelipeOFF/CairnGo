#!/usr/bin/env python3
"""cairn-gsd-init.py — irmão de init do dispatcher cairn-gsd.py (D-01).

Serve as famílias worktree e init (+ 17 misc genéricos, plano 34-05).
Worktree fala com git (moldes de cairn-parallel: subprocess defensivo,
rollback de criação parcial); init compõe bundles de contexto de config +
filesystem + FATO de estado — fato vem SEMPRE do irmão cairn-gsd-state.py
por subprocess (uma implementação de consulta na casa, nunca duas), e a
falha nomeada do irmão é PROPAGADA (CORE-04 por composição). Invocado pelo
dispatcher via os.execv com o VERBO canônico como argv[1].

Usage:
    cairn-gsd-init.py <verbo canônico> [argv]   |   --list-implemented

Exit codes (vocabulário do dispatcher; o execv preserva):
    0 contrato; 1 erro contratado ({ok: false, reason} dos verbos worktree,
    falha nomeada propagada do irmão de estado); 2 uso (--manifest ausente);
    4 verbo do irmão ainda sem handler.

Saída na semântica medida do binário: sem --raw JSON.stringify(v, null, 2);
--raw com rawValue definido String(rawValue); sem newline final.
Divergências deliberadas: tests/fixtures/gsd-goldens/divergences.json.
A árvore cairn/gsd/ é SOMENTE-LEITURA para este script.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cairn_gsd_render import (_UNDEFINED, emit, js_string,
                              output_like_binary, parse_verb_args,
                              stringify)  # noqa: E402

EXIT_OK = 0
EXIT_CONTRACT = 1
EXIT_USAGE = 2
EXIT_UNIMPLEMENTED = 4

TAG_PREFIX = "[cairn-gsd-init]"

USAGE = "usage: cairn-gsd-init.py <verbo canônico> [argv do verbo]"

HERE = Path(__file__).resolve().parent
CONTRACTS_DIR = HERE.parent / "gsd" / "contracts"
VENDORED_AGENTS_DIR = HERE.parent / "gsd" / "agents"

PLAN_FILE = re.compile(r"^\d+-(\d+)-PLAN\.md$")
SUMMARY_FILE = re.compile(r"^\d+-(\d+)-SUMMARY\.md$")
PHASE_DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")
HEAD_MILESTONE = re.compile(r"^#{1,6}\s+Milestone:\s*(.+?)\s*$")
CHECKBOX_PHASE = re.compile(r"^\s*-\s*\[([ xX])\]\s.*?\bPhase\s+0*(\d+)\b")
HEAD_PHASE_TITLE = re.compile(r"^#{1,6}\s+Phase\s+0*(\d+)\s*:\s*(.+?)\s*$")
REQ_LINE = re.compile(r"^\*\*Requirements\*\*\s*:(.*)$")
REQ_ID = re.compile(r"[A-Za-z][A-Za-z0-9]*-\d+")

def die(msg, code=EXIT_USAGE):
    print(f"{TAG_PREFIX} error: {msg}", file=sys.stderr)
    sys.exit(code)

# ---- git (molde run_git de cairn-parallel: die nomeado nunca traceback) ---- #
def run_git(args, cwd, timeout=60):
    """(code, stdout, stderr) de um git; git ausente/timeout viram code None."""
    try:
        proc = subprocess.run(["git"] + list(args), capture_output=True,
                              text=True, cwd=str(cwd), timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "", str(e)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

def find_project_root(cwd):
    cur = Path(cwd).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / ".planning").is_dir():
            return candidate
    return cur

def load_config_defensive(root):
    try:
        data = json.loads((root / ".planning" / "config.json")
                          .read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}

# ---- manifest de wave (worktree.json: shape {orchestrator_root, worktrees}) - #
def load_manifest(path):
    """(manifest, err_reason) — leitura validada do manifest da wave."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None, "manifest_read_failed"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None, "invalid_manifest_json"
    if not isinstance(data, dict) or not isinstance(
            data.get("worktrees"), list):
        return None, "manifest_shape_invalid"
    return data, None

def write_manifest(path, manifest):
    """Grava por temp+rename atômico; devolve False na falha (o chamador
    decide rollback)."""
    p = Path(path)
    tmp = p.with_name(p.name + f".tmp.{os.getpid()}")
    try:
        tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)
                       + "\n", encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False
    return True

def fail(reason, raw, extra=None, code=EXIT_CONTRACT):
    result = {"ok": False, "reason": reason}
    if extra:
        result.update(extra)
    output_like_binary(result, raw, "failed")
    return code

# ---- handlers — família worktree ------------------------------------------- #
def handle_worktree(rest):
    """`worktree set-baseref`: grava worktree.baseRef='head' em
    .claude/settings.local.json, no-clobber (contrato)."""
    pos, _ = parse_verb_args(rest)
    raw = "--raw" in rest
    sub = pos[0] if pos else None
    if sub != "set-baseref":
        die(f"Unknown worktree subcommand: {sub}. Available: set-baseref",
            EXIT_CONTRACT)
    path = Path.cwd() / ".claude" / "settings.local.json"
    settings = {}
    if path.is_file():
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            die(f"Refusing to modify malformed JSON: {path}", EXIT_CONTRACT)
        if not isinstance(settings, dict):
            die(f"Refusing to modify malformed JSON: {path}", EXIT_CONTRACT)
    wt = settings.get("worktree")
    current = wt.get("baseRef") if isinstance(wt, dict) else None
    if current == "head":
        result = {"changed": False, "skipped": "already-head",
                  "baseRef": "head", "file": str(path)}
    elif current is not None:
        result = {"changed": False, "skipped": "explicit-other",
                  "baseRef": current, "file": str(path)}
    else:
        settings.setdefault("worktree", {})["baseRef"] = "head"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(settings, indent=2,
                                       ensure_ascii=False) + "\n",
                            encoding="utf-8")
        except OSError as e:
            die(f"falha escrevendo {path}: {e}", EXIT_CONTRACT)
        result = {"changed": True, "baseRef": "head", "file": str(path),
                  "previous": None}
    output_like_binary(result, raw)
    return EXIT_OK

def handle_worktree_set_baseref(rest):
    """`worktree.set-baseref` — a MESMA operação de `worktree set-baseref`,
    pela grafia pontuada.

    Duas grafias, uma implementação. O contrato da fase 33 registrou só a
    forma com espaço porque o inventário do universo varre workflows8 +
    agents, e o único sítio que ele viu (execute-phase.md:131) usa espaço.
    A fase 38 mediu `gsd-core/references/` — fora do escopo varrido — e achou
    a forma pontuada em execute-phase-between-wave-reset.md:30, embrulhada em
    `2>/dev/null || true`: o dispatcher morria exit 2 e o `|| true` apagava a
    morte, então o reset de baseRef entre ondas simplesmente não acontecia.

    Delegar em vez de reimplementar é o ponto: duas cópias da mesma escrita
    no-clobber concordariam entre si até no dia em que as duas estivessem
    erradas.
    """
    return handle_worktree(["set-baseref"] + list(rest))

def handle_worktree_base_check(rest):
    """#683 reduzido a host único: baseRef do settings.local.json do
    projeto; ausente resolve 'head' (divergência declarada) — curto-circuito
    shouldDegrade false; não-head compara HEAD vs forkRef via git."""
    raw = "--raw" in rest
    cwd = Path.cwd()
    base_ref = None
    path = cwd / ".claude" / "settings.local.json"
    if path.is_file():
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
            wt = settings.get("worktree") if isinstance(settings, dict) \
                else None
            if isinstance(wt, dict) and isinstance(wt.get("baseRef"), str):
                base_ref = wt["baseRef"]
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    if base_ref is None or base_ref == "head":
        result = {"shouldDegrade": False, "reason": "baseref-head",
                  "message": "baseRef is head — worktrees fork do HEAD "
                             "corrente, sem degradação"}
        output_like_binary(result, raw)
        return EXIT_OK
    code_h, head_sha, _ = run_git(["rev-parse", "HEAD"], cwd)
    if code_h != 0:
        result = {"shouldDegrade": True, "reason": "no-head",
                  "headAbsenceVerified": True, "forkRef": base_ref,
                  "message": "repo sem HEAD resolvível — degrade para "
                             "sequencial"}
        output_like_binary(result, raw)
        return EXIT_OK
    code_f, fork_sha, err = run_git(["rev-parse", base_ref], cwd)
    if code_f != 0:
        result = {"shouldDegrade": True, "reason": "fork-ref-unresolvable",
                  "forkRef": base_ref, "headSha": head_sha,
                  "message": f"baseRef '{base_ref}' não resolve: {err}"}
        output_like_binary(result, raw)
        return EXIT_OK
    diverged = fork_sha != head_sha
    result = {"shouldDegrade": diverged,
              "reason": "diverged" if diverged else "match",
              "forkRef": base_ref, "forkSha": fork_sha,
              "headSha": head_sha,
              "message": ("HEAD divergiu da base de fork — degrade"
                          if diverged else "HEAD casa com a base de fork")}
    output_like_binary(result, raw)
    return EXIT_OK

def handle_worktree_create(rest):
    """Cria o worktree de agente E o registra no manifest na mesma operação;
    falha na gravação do manifest desfaz árvore E branch (rollback provado
    por teste de resíduo — nunca worktree órfã de branch nem o inverso)."""
    _, flags = parse_verb_args(rest, value_flags=(
        "--manifest", "--agent-id", "--path", "--branch", "--base",
        "--root"))
    raw = "--raw" in rest
    manifest_path = flags.get("--manifest")
    if not manifest_path:
        die("usage: worktree.create --manifest <path> --agent-id <id> "
            "--path <worktree> --branch <branch> --base <sha> --root <dir>",
            EXIT_USAGE)
    manifest, err = load_manifest(manifest_path)
    if err:
        return fail(err, raw)
    missing = [f for f in ("--agent-id", "--path", "--branch", "--base")
               if not (flags.get(f) or "").strip()]
    if missing:
        return fail("usage", raw,
                    {"hint": f"campos ausentes: {', '.join(missing)}"})
    root_flag = flags.get("--root")
    if not root_flag:
        return fail("root_required", raw)
    cwd = Path.cwd()
    root_abs = os.path.realpath(os.path.join(str(cwd), root_flag))
    path_abs = os.path.abspath(os.path.join(str(cwd), flags["--path"]))
    if path_abs != root_abs and not path_abs.startswith(root_abs + os.sep):
        return fail("path_outside_root", raw,
                    {"hint": f"{path_abs} fora de {root_abs}"})
    branch = flags["--branch"]
    code, _, err_git = run_git(
        ["worktree", "add", "-b", branch, path_abs, flags["--base"]], cwd)
    if code != 0:
        return fail("git_worktree_add_failed", raw,
                    {"error": err_git,
                     "hint": "verifique branch/base — nada foi criado"})
    entry = {"agent_id": flags["--agent-id"], "path": path_abs,
             "branch": branch, "base": flags["--base"]}
    manifest["worktrees"].append(entry)
    if not write_manifest(manifest_path, manifest):
        # rollback: a árvore E a branch que ESTA chamada criou
        run_git(["worktree", "remove", "--force", path_abs], cwd)
        run_git(["branch", "-D", branch], cwd)
        return fail("manifest_write_failed", raw,
                    {"hint": "worktree desfeita (rollback)"})
    result = {"ok": True, "reason": "created", "entry": entry,
              "cwd": path_abs,
              "manifest_path": os.path.abspath(
                  os.path.join(str(cwd), manifest_path))}
    output_like_binary(result, raw, path_abs)
    return EXIT_OK

def handle_worktree_record_agent(rest):
    """#1297: registra worktree JÁ criado no manifest da wave; idempotente
    por agent_id (uma entrada só)."""
    _, flags = parse_verb_args(rest, value_flags=(
        "--manifest", "--agent-id", "--path", "--branch", "--base"))
    raw = "--raw" in rest
    manifest_path = flags.get("--manifest")
    if not manifest_path:
        die("usage: worktree.record-agent --manifest <path> --agent-id <id> "
            "--path <worktree> --branch <branch> --base <sha>", EXIT_USAGE)
    manifest, err = load_manifest(manifest_path)
    if err:
        return fail(err, raw)
    missing = [f for f in ("--agent-id", "--path", "--branch", "--base")
               if not (flags.get(f) or "").strip()]
    if missing:
        return fail("usage", raw,
                    {"hint": f"campos ausentes: {', '.join(missing)}"})
    cwd = Path.cwd()
    entry = {"agent_id": flags["--agent-id"],
             "path": os.path.abspath(os.path.join(str(cwd),
                                                  flags["--path"])),
             "branch": flags["--branch"], "base": flags["--base"]}
    manifest["worktrees"] = [w for w in manifest["worktrees"]
                             if not (isinstance(w, dict)
                                     and w.get("agent_id")
                                     == entry["agent_id"])]
    manifest["worktrees"].append(entry)
    if not write_manifest(manifest_path, manifest):
        return fail("manifest_write_failed", raw)
    result = {"ok": True, "reason": "ok", "entry": entry,
              "manifest_path": os.path.abspath(
                  os.path.join(str(cwd), manifest_path))}
    output_like_binary(result, raw, True)
    return EXIT_OK

def handle_worktree_cleanup_wave(rest):
    """Limpeza pós-wave das árvores registradas no manifest; branches ficam
    (divergência declarada — a poda é decisão do merge)."""
    _, flags = parse_verb_args(rest, value_flags=("--manifest",))
    raw = "--raw" in rest
    manifest_path = flags.get("--manifest")
    if not manifest_path:
        die("usage: worktree.cleanup-wave --manifest <path>", EXIT_USAGE)
    manifest, err = load_manifest(manifest_path)
    if err:
        return fail(err, raw)
    cwd = Path.cwd()
    entries = []
    failures = 0
    removed = 0
    for w in manifest["worktrees"]:
        if not isinstance(w, dict):
            continue
        path = str(w.get("path") or "")
        abs_path = os.path.abspath(os.path.join(str(cwd), path))
        if not os.path.isdir(abs_path):
            entries.append({"path": path, "action": "skipped",
                            "reason": "missing"})
            continue
        code, _, err_git = run_git(
            ["worktree", "remove", "--force", abs_path], cwd)
        if code == 0:
            removed += 1
            entries.append({"path": path, "action": "removed",
                            "reason": "wave-complete"})
        else:
            failures += 1
            entries.append({"path": path, "action": "failed",
                            "reason": err_git})
    ok = failures == 0
    result = {"ok": ok,
              "plan": {"action": "cleanup", "discovery": "manifest",
                       "reason": "wave-complete", "entries": entries},
              "result": {"ok": ok, "removed": removed}}
    output_like_binary(result, raw, "ok" if ok else "failed")
    return EXIT_OK if ok else EXIT_CONTRACT

def handle_worktree_reap_orphans(rest):
    """Fail-open: órfão = worktree linkado cujo diretório sumiu (prunable);
    heurísticas de lock/merge não portadas (divergência declarada)."""
    raw = "--raw" in rest
    cwd = Path.cwd()
    entries = []
    reaped = 0
    try:
        code, out, _ = run_git(["worktree", "list", "--porcelain"], cwd)
        if code == 0:
            paths = [ln[len("worktree "):] for ln in out.splitlines()
                     if ln.startswith("worktree ")]
            for p in paths[1:]:  # o primeiro é a árvore principal
                if not os.path.isdir(p):
                    run_git(["worktree", "prune"], cwd)
                    entries.append({"path": p, "status": "reaped",
                                    "reason": "missing-dir"})
                    reaped += 1
    except Exception as e:  # fail-open deliberado (contrato)
        sys.stderr.write(f"{TAG_PREFIX} warning: reap falhou: {e}\n")
    result = {"ok": True, "reaped": reaped, "entries": entries}
    output_like_binary(result, raw)
    return EXIT_OK

# ---- composição de bundles init (fato via irmão de estado) ----------------- #
def run_sibling(script, argv):
    """(code, stdout, stderr) de um irmão python — molde run_sibling_json de
    cairn-bookkeep ('duas implementações que podem discordar é a doença')."""
    try:
        proc = subprocess.run([sys.executable, str(HERE / script)] + argv,
                              capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as e:
        return 1, "", f"{TAG_PREFIX} error: irmão {script} falhou: {e}"
    return proc.returncode, proc.stdout, proc.stderr

def state_facts():
    """state.load do irmão de estado; a falha nomeada é PROPAGADA (CORE-04
    por composição — o bundle nunca preenche default de fato)."""
    code, out, err = run_sibling("cairn-gsd-state.py", ["state.load"])
    if code != 0:
        sys.stderr.write(err)
        sys.exit(code)
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        die("state.load do irmão devolveu JSON inválido", EXIT_CONTRACT)
    dims = {}
    for ln in (data.get("state_raw") or "").splitlines():
        if ": " in ln:
            k, v = ln.split(": ", 1)
            dims[k] = v
    return data, dims

def state_exists_report():
    """Variante de RELATÓRIO (manager/milestone-op): a ausência do fato É a
    resposta — devolve False em vez de propagar (divergência declarada)."""
    code, _, _ = run_sibling("cairn-gsd-state.py", ["state.load"])
    return code == 0

def plan_index(phase):
    """phase-plan-index do irmão de estado — uma implementação de índice."""
    code, out, _ = run_sibling("cairn-gsd-state.py",
                               ["phase-plan-index", str(phase)])
    if code != 0:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}

def resolve_model(agent):
    """resolve-model do dispatcher — o catálogo mora lá, não aqui."""
    code, out, _ = run_sibling("cairn-gsd.py",
                               ["query", "resolve-model", agent,
                                "--pick", "model"])
    return out.strip() if code == 0 and out.strip() else None

def locate_phase_dir(root, target):
    phases = root / ".planning" / "phases"
    if not phases.is_dir():
        return None
    for d in sorted(phases.iterdir()):
        if not d.is_dir():
            continue
        m = PHASE_DIR_PREFIX.match(d.name)
        if str(target).isdigit():
            if m and int(m.group(1)) == int(target):
                return d
        elif str(target).lower() in d.name.lower():
            return d
    return None

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40]

def milestone_info(root):
    """(name, version, slug) do primeiro '## Milestone:' do ROADMAP."""
    p = root / ".planning" / "ROADMAP.md"
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return None, None, None
    for ln in text.splitlines():
        m = HEAD_MILESTONE.match(ln)
        if m:
            name = m.group(1)
            first = name.split()[0] if name.split() else ""
            version = first if first.startswith("v") else None
            return name, version, slugify(name)
    return None, None, None

def roadmap_phases(root):
    """(titles {n: nome}, complete {n: bool}) dos checkboxes/headings."""
    p = root / ".planning" / "ROADMAP.md"
    titles, complete = {}, {}
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return titles, complete
    for ln in text.splitlines():
        mt = HEAD_PHASE_TITLE.match(ln)
        if mt:
            titles.setdefault(int(mt.group(1)), mt.group(2).strip())
        mc = CHECKBOX_PHASE.match(ln)
        if mc:
            n = int(mc.group(2))
            complete[n] = complete.get(n, False) or \
                mc.group(1).lower() == "x"
    return titles, complete

def phase_req_ids(root, phase_n):
    """Ids da linha **Requirements**: da seção da fase no ROADMAP."""
    p = root / ".planning" / "ROADMAP.md"
    try:
        lines = p.read_text(encoding="utf-8").split("\n")
    except OSError:
        return []
    in_section = False
    head = re.compile(r"^(#{1,6})\s+Phase\s+0*(\d+)\b")
    for ln in lines:
        m = head.match(ln)
        if m:
            in_section = int(m.group(2)) == phase_n
            continue
        if in_section:
            mr = REQ_LINE.match(ln.strip())
            if mr:
                return REQ_ID.findall(mr.group(1))
    return []

def artifact_path(d, token):
    """Path absoluto do primeiro artefato .md da fase com o token no nome."""
    if d is None:
        return None
    for f in sorted(d.iterdir()):
        if f.suffix == ".md" and token in f.name.upper():
            return str(f)
    return None

def common_bundle(root):
    """As chaves comuns de withProjectRoot, na redução de host único:
    agents da árvore vendorizada (determinístico por construção)."""
    config = load_config_defensive(root)
    installed = VENDORED_AGENTS_DIR.is_dir() and any(
        f.suffix == ".md" for f in VENDORED_AGENTS_DIR.iterdir())
    title = None
    proj = root / ".planning" / "PROJECT.md"
    if proj.is_file():
        try:
            for ln in proj.read_text(encoding="utf-8").splitlines():
                if ln.startswith("# "):
                    title = ln[2:].strip()
                    break
        except OSError:
            pass
    return config, {
        "project_root": str(root),
        "agents_dir": str(VENDORED_AGENTS_DIR),
        "agents_installed": bool(installed),
        "missing_agents": [],
        "agent_runtime": "claude",
        "project_code": config.get("project_code"),
        "project_title": title,
        "response_language": config.get("response_language"),
    }

def wf(config, key, default):
    """config.workflow.<key> com default (leitura defensiva)."""
    w = config.get("workflow")
    if isinstance(w, dict) and key in w:
        return w[key]
    return default

def emit_bundle(result, rest):
    """--pick extrai a chave na semântica medida (String; ausente ->
    undefined); senão o envelope JSON."""
    pick = None
    if "--pick" in rest:
        i = rest.index("--pick")
        pick = rest[i + 1] if i + 1 < len(rest) else None
    if pick:
        emit(js_string(result[pick]) if pick in result else "undefined")
        return EXIT_OK
    output_like_binary(result, "--raw" in rest)
    return EXIT_OK

def resolve_phase_fields(root, target):
    """Campos de resolução de fase compartilhados pelos bundles."""
    d = locate_phase_dir(root, target)
    if d is None:
        return None, {"phase_found": False, "phase_dir": None,
                      "phase_name": None, "phase_number": None,
                      "phase_slug": None}
    m = PHASE_DIR_PREFIX.match(d.name)
    slug = d.name[m.end():] if m else d.name
    return d, {"phase_found": True, "phase_dir": str(d),
               "phase_name": slug,
               "phase_number": int(m.group(1)) if m else None,
               "phase_slug": slug}

# ---- handlers — família init ------------------------------------------------ #
# D-03 (2026-08-11, ADAPT-01) — `section_manifest` sai `null` nos 6 bundles
# que o carregam, e os outros 5 sítios apontam para AQUI.
#  (1) null é o valor especificado para o caso degradado, e a camada prompt o
#      lê como superset seguro: "read all three unconditionally"
#      (gsd-core/workflows/execute-phase.md:92). São 21 gates literais na
#      prosa, todos na forma `If section_manifest is null or "<id>" is in
#      its included list`.
#  (2) lista vazia não é NENHUM dos dois valores do contrato (null, ou objeto
#      com included/excluded/read): debug.md:31 declara textualmente que null
#      e um included vazio não são a mesma coisa. MEDIDO (2026-08-11, clone da
#      tag v1.10.0 em .cairn/cache): upstream também nunca emite lista —
#      src/init.cts:459-470 degrada leitura ausente/malformada de
#      workflows/section-manifest.json para null, e esse artefato não existe
#      na árvore vendorizada, então null é o que upstream produziria aqui.
#  (3) a composição por manifesto + steps é PRESERVADA, não achatada: achatar
#      inlinaria 21 arquivos / 806 linhas nos workflows raiz (+12,4% sobre as
#      6.502 linhas lidas SEMPRE) para adaptar 10 das 38 chamadas dos
#      fragments, com o estado em markdown 65-vs-8 a favor da raiz. Preencher
#      included/excluded de verdade é incremento medido de outra fase; esta
#      corrige só o TIPO. Divergência: tests/fixtures/gsd-goldens/
#      divergences.json, aspect `section-manifest-empty`.
def handle_init_autonomous(rest):
    root = find_project_root(Path.cwd())
    _, common = common_bundle(root)
    result = dict(common)
    result["section_manifest"] = None  # D-03 acima
    result["plan_strategy_converge"] = "--converge" in rest
    return emit_bundle(result, rest)

def handle_init_debug(rest):
    root = find_project_root(Path.cwd())
    config, common = common_bundle(root)
    result = dict(common)
    result.update({
        "section_manifest": None,  # null — D-03, topo da família
        "debug_dir": str(root / ".planning" / "debug"),
        "debugger_model": resolve_model("gsd-debugger"),
        "tdd_mode": bool(config.get("tdd_mode", False)),
        "commit_docs": bool(config.get("commit_docs", True)),
        "diagnose": "--diagnose" in rest,
    })
    return emit_bundle(result, rest)

def handle_init_execute_phase(rest):
    pos, _ = parse_verb_args(rest, value_flags=("--pick",),
                             bool_flags=("--raw", "--validate", "--tdd",
                                         "--wave"))
    if not pos:
        die("phase required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    config, common = common_bundle(root)
    facts, dims = state_facts()  # propaga a falha nomeada sem portador
    d, phase_fields = resolve_phase_fields(root, pos[0])
    idx = plan_index(pos[0]) if d is not None else {}
    plans = sorted(f.name for f in d.iterdir()
                   if PLAN_FILE.match(f.name)) if d else []
    summaries = sorted(f.name for f in d.iterdir()
                       if SUMMARY_FILE.match(f.name)) if d else []
    incomplete = idx.get("incomplete") or []
    runnable = idx.get("runnable") or []
    mname, mversion, mslug = milestone_info(root)
    planning = root / ".planning"
    result = dict(common)
    result.update(phase_fields)
    result.update({
        "section_manifest": None,  # null — D-03, topo da família
        "phase_req_ids": phase_req_ids(
            root, phase_fields.get("phase_number") or -1),
        "plans": plans, "summaries": summaries, "plan_count": len(plans),
        "incomplete_plans": incomplete,
        "incomplete_count": len(incomplete),
        "runnable_plans": runnable, "runnable_count": len(runnable),
        "halted_plans": [], "blocked_by": [],
        "executor_model": resolve_model("gsd-executor"),
        "verifier_model": resolve_model("gsd-verifier"),
        "verifier_enabled": bool(wf(config, "verifier", True)),
        "commit_docs": bool(config.get("commit_docs", True)),
        "sub_repos": config.get("sub_repos") or [],
        "parallelization": bool(wf(config, "parallelization", True)),
        "context_window": config.get("context_window"),
        "branching_strategy": (config.get("git") or {}).get(
            "branching_strategy", "none")
        if isinstance(config.get("git"), dict) else "none",
        "branch_name": None, "phase_branch_template": None,
        "milestone_branch_template": None,
        "milestone_name": mname, "milestone_version": mversion,
        "milestone_slug": mslug,
        "config_path": str(planning / "config.json"),
        "config_exists": (planning / "config.json").is_file(),
        "roadmap_path": str(planning / "ROADMAP.md"),
        "roadmap_exists": (planning / "ROADMAP.md").is_file(),
        "requirements_path": str(planning / "REQUIREMENTS.md"),
        "state_path": str(planning / "STATE.md"),
        "state_exists": bool(facts.get("state_exists")),
        "state_validation_ran": False, "state_warnings": [],
        "tdd_mode": bool(config.get("tdd_mode", False)),
    })
    return emit_bundle(result, rest)

def handle_init_manager(rest):
    root = find_project_root(Path.cwd())
    _, common = common_bundle(root)
    titles, complete = roadmap_phases(root)
    numbers = sorted(set(titles) | set(complete))
    exists = state_exists_report()
    in_progress = 0
    current = numbers[0] if numbers else None
    if exists:
        _, dims = state_facts()
        if dims.get("phase", "").isdigit():
            current = int(dims["phase"])
        in_progress = 1 if dims.get("phase_status") == "executing" else 0
    mname, mversion, _ = milestone_info(root)
    result = dict(common)
    result.update({
        "project_exists": (root / ".planning" / "PROJECT.md").is_file(),
        "roadmap_exists": (root / ".planning" / "ROADMAP.md").is_file(),
        "state_exists": exists,
        "phase_count": len(numbers),
        "completed_count": sum(1 for n in numbers if complete.get(n)),
        "in_progress_count": in_progress,
        "all_complete": bool(numbers) and all(complete.get(n)
                                              for n in numbers),
        "milestone_name": mname, "milestone_version": mversion,
        "phases": [{"phase": n, "name": titles.get(n),
                    "complete": bool(complete.get(n))} for n in numbers],
        "discuss": f"/gsd:discuss-phase {current}",
        "plan": f"/gsd:plan-phase {current}",
        "execute": f"/gsd:execute-phase {current}",
        "manager_flags": [], "recommended_actions": [],
        "waiting_signal": False,
    })
    return emit_bundle(result, rest)

def handle_init_milestone_op(rest):
    root = find_project_root(Path.cwd())
    config, common = common_bundle(root)
    titles, complete = roadmap_phases(root)
    numbers = sorted(set(titles) | set(complete))
    mname, mversion, mslug = milestone_info(root)
    archive = root / ".planning" / "milestones"
    archived = sorted(d.name for d in archive.iterdir()
                      if d.is_dir()) if archive.is_dir() else []
    result = dict(common)
    result.update({
        "milestone_name": mname, "milestone_version": mversion,
        "milestone_slug": mslug,
        "phase_count": len(numbers),
        "completed_phases": sum(1 for n in numbers if complete.get(n)),
        "all_phases_complete": bool(numbers) and all(
            complete.get(n) for n in numbers),
        "roadmap_exists": (root / ".planning" / "ROADMAP.md").is_file(),
        "state_exists": state_exists_report(),
        "project_exists": (root / ".planning" / "PROJECT.md").is_file(),
        "phases_dir_exists": (root / ".planning" / "phases").is_dir(),
        "archive_exists": archive.is_dir(),
        "archive_count": len(archived),
        "archived_milestones": archived,
        "commit_docs": bool(config.get("commit_docs", True)),
    })
    return emit_bundle(result, rest)

def _phase_op_fields(root, config, target):
    """Campos compartilhados de phase-op/plan-phase (artefatos + paths)."""
    d, fields = resolve_phase_fields(root, target)
    planning = root / ".planning"
    n = fields.get("phase_number")
    fields.update({
        "padded_phase": f"{n:02d}" if isinstance(n, int) else None,
        "expected_phase_dir": fields.get("phase_dir") or (
            str(planning / "phases" / f"{target}-") if target else None),
        "plan_count": len([f for f in d.iterdir()
                           if PLAN_FILE.match(f.name)]) if d else 0,
        "planning_exists": planning.is_dir(),
        "has_plans": bool(d) and any(PLAN_FILE.match(f.name)
                                     for f in d.iterdir()),
        "research_path": artifact_path(d, "RESEARCH"),
        "context_path": artifact_path(d, "CONTEXT"),
        "reviews_path": artifact_path(d, "REVIEW"),
        "verification_path": artifact_path(d, "VERIFICATION"),
        "uat_path": artifact_path(d, "UAT"),
        "commit_docs": bool(config.get("commit_docs", True)),
        "roadmap_exists": (planning / "ROADMAP.md").is_file(),
        "roadmap_path": str(planning / "ROADMAP.md"),
        "requirements_path": str(planning / "REQUIREMENTS.md"),
        "state_path": str(planning / "STATE.md"),
    })
    for key in ("research", "context", "reviews", "verification"):
        fields[f"has_{key}"] = fields[f"{key}_path"] is not None
    return d, fields

def handle_init_phase_op(rest):
    pos, _ = parse_verb_args(rest, value_flags=("--pick",))
    if not pos:
        die("phase required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    config, common = common_bundle(root)
    _, fields = _phase_op_fields(root, config, pos[0])
    result = dict(common)
    result.update(fields)
    result.update({
        "brave_search": config.get("brave_search"),
        "exa_search": config.get("exa_search"),
        "firecrawl": config.get("firecrawl"),
    })
    return emit_bundle(result, rest)

def handle_init_plan_phase(rest):
    pos, flags = parse_verb_args(
        rest, value_flags=("--pick", "--granularity", "--prd", "--ingest",
                           "--research-phase"),
        bool_flags=("--raw", "--validate", "--tdd", "--reviews",
                    "--chunked"))
    if not pos:
        die("phase required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    config, common = common_bundle(root)
    _, dims = state_facts()  # propaga a falha nomeada sem portador
    d, fields = resolve_phase_fields(root, pos[0])
    _, op_fields = _phase_op_fields(root, config, pos[0])
    n = fields.get("phase_number")
    phase_status = dims.get("phase_status") \
        if dims.get("phase") == str(n) else None
    mode = None
    code, out, _ = run_sibling("cairn-gsd-state.py",
                               ["phase.mvp-mode", str(pos[0])])
    if code == 0:
        try:
            mvp = json.loads(out)
            mode = "mvp" if mvp.get("active") else "standard"
        except json.JSONDecodeError:
            pass
    result = dict(common)
    result.update(op_fields)
    # o shape de plan-phase carrega verification_path mas não a flag
    result.pop("has_verification", None)
    result.update({
        "section_manifest": None,  # null — D-03, topo da família
        "patterns_path": artifact_path(d, "PATTERNS"),
        "phase_req_ids": phase_req_ids(root, n if isinstance(n, int)
                                       else -1),
        "phase_status": phase_status,
        "researcher_model": resolve_model("gsd-phase-researcher"),
        "planner_model": resolve_model("gsd-planner"),
        "checker_model": resolve_model("gsd-plan-checker"),
        "research_enabled": bool(wf(config, "research", True)),
        "plan_checker_enabled": bool(wf(config, "plan_checker", True)),
        "nyquist_validation_enabled": bool(
            wf(config, "nyquist_validation", False)),
        "auto_advance": bool(wf(config, "auto_advance", False)),
        "auto_chain_active": bool(wf(config, "_auto_chain_active", False)),
        "mode": mode, "text_mode": bool(config.get("text_mode", False)),
        "granularity": flags.get("--granularity") or "standard",
        "tdd_mode": bool(config.get("tdd_mode", False)),
        "state_validation_ran": False, "state_warnings": [],
    })
    return emit_bundle(result, rest)

def handle_init_quick(rest):
    known = {"--discuss", "--research", "--validate", "--full", "--raw"}
    words = [t for t in rest if t not in known
             and not (t == "--pick"
                      or (rest.index(t) > 0
                          and rest[rest.index(t) - 1] == "--pick"))]
    description = " ".join(words) or None
    root = find_project_root(Path.cwd())
    config, common = common_bundle(root)
    slug = slugify(description) if description else None
    date = time.strftime("%Y-%m-%d")
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    quick_id = f"{date}-{slug}" if slug else None
    quick_dir = root / ".planning" / "quick"
    result = dict(common)
    result.update({
        "section_manifest": None,  # null — D-03, topo da família
        "description": description, "slug": slug,
        "date": date, "timestamp": timestamp, "quick_id": quick_id,
        "quick_dir": str(quick_dir),
        "task_dir": str(quick_dir / quick_id) if quick_id else None,
        "branch_name": f"quick/{slug}" if slug else None,
        "planner_model": resolve_model("gsd-planner"),
        "executor_model": resolve_model("gsd-executor"),
        "verifier_model": resolve_model("gsd-verifier"),
        "checker_model": resolve_model("gsd-plan-checker"),
        "reviewer_model": resolve_model("gsd-code-reviewer"),
        "planning_exists": (root / ".planning").is_dir(),
        "roadmap_exists": (root / ".planning" / "ROADMAP.md").is_file(),
        "commit_docs": bool(config.get("commit_docs", True)),
    })
    return emit_bundle(result, rest)

def handle_init_verify_work(rest):
    pos, _ = parse_verb_args(rest, value_flags=("--pick",))
    if not pos:
        die("phase required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    config, common = common_bundle(root)
    d, fields = resolve_phase_fields(root, pos[0])
    pc = len([f for f in d.iterdir()
              if PLAN_FILE.match(f.name)]) if d else 0
    sc = len([f for f in d.iterdir()
              if SUMMARY_FILE.match(f.name)]) if d else 0
    planning = root / ".planning"
    result = dict(common)
    result.update({k: fields[k] for k in ("phase_found", "phase_dir",
                                          "phase_name", "phase_number")})
    result.update({
        "section_manifest": None,  # null — D-03, topo da família
        "phase_completion": f"{sc}/{pc}",
        "has_verification": artifact_path(d, "VERIFICATION") is not None,
        "planner_model": resolve_model("gsd-planner"),
        "checker_model": resolve_model("gsd-plan-checker"),
        "commit_docs": bool(config.get("commit_docs", True)),
        "roadmap_path": str(planning / "ROADMAP.md"),
        "state_path": str(planning / "STATE.md"),
        "ui_phase_active": False,
    })
    return emit_bundle(result, rest)

# ---- handlers — misc genérico (partição do plano 34-01, 17 verbos) --------- #
CAP_MSG = ("capability não habilitada no cairn — o subsistema foi cortado "
           "pelo research §4; nenhum call site do corpus o consome")
SCHEMA_FIELDS = {"plan": ("phase", "plan", "wave", "depends_on"),
                 "summary": ("phase", "plan")}
SMART_ZONE_DEFAULT = 150000


def parse_frontmatter_lines(text):
    """(dict, span) — subset YAML plano + o intervalo de linhas do bloco."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, None
    out, end = {}, None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out, end


def handle_classify_confidence(rest):
    """Redução declarada: verified -> high, senão medium; verdict offline
    fica null (sem --package) — SLOP nunca é afirmado sem registry."""
    _, flags = parse_verb_args(rest, value_flags=(
        "--provider", "--package", "--ecosystem"),
        bool_flags=("--raw", "--verified"))
    if not flags.get("--provider"):
        die("--provider required", EXIT_CONTRACT)
    pkg = flags.get("--package")
    eco = flags.get("--ecosystem")
    if pkg and not eco:
        die("--package requer --ecosystem", EXIT_CONTRACT)
    verified = "--verified" in rest
    result = {"provider": flags["--provider"], "package": pkg,
              "ecosystem": eco, "verified": verified,
              "confidence": "high" if verified else "medium",
              "legitimacyVerdict": "unverified" if pkg else None}
    output_like_binary(result, "--raw" in rest)
    return EXIT_OK


def handle_estimate_check(rest):
    """#2630 sem calibração (divergência declarada): budget do config."""
    _, flags = parse_verb_args(rest, value_flags=("--tokens",),
                               bool_flags=("--raw", "--calibrated"))
    tokens = flags.get("--tokens")
    if tokens is None or not str(tokens).isdigit():
        die("--tokens required (inteiro)", EXIT_CONTRACT)
    tokens = int(tokens)
    config = load_config_defensive(find_project_root(Path.cwd()))
    w = config.get("workflow")
    budget = (w.get("smart_zone_tokens")
              if isinstance(w, dict)
              and isinstance(w.get("smart_zone_tokens"), int)
              else SMART_ZONE_DEFAULT)
    ratio = round(tokens / budget, 2) if budget else 0
    over = tokens > budget
    result = {"raw_tokens": tokens, "calibrated_tokens": tokens,
              "calibration_applied": False, "calibration_factor": 1.0,
              "sample_count": 0, "confidence": "low",
              "pre_calibrated": "--calibrated" in rest,
              "budget": budget, "budget_valid": True, "ratio": ratio,
              "over_budget": over,
              "recommendation": "split" if over else "proceed"}
    output_like_binary(result, "--raw" in rest)
    return EXIT_OK


def handle_frontmatter_get(rest):
    pos, flags = parse_verb_args(rest, value_flags=("--field",))
    raw = "--raw" in rest
    if not pos:
        die("file required", EXIT_CONTRACT)
    p = Path(pos[0])
    if not p.is_file():
        output_like_binary({"error": "File not found"}, raw, False)
        return EXIT_OK
    fm, _ = parse_frontmatter_lines(p.read_text(encoding="utf-8"))
    field = flags.get("--field")
    if field is None:
        output_like_binary(fm, raw)
        return EXIT_OK
    if field not in fm:
        output_like_binary({"error": "Field not found"}, raw, False)
        return EXIT_OK
    output_like_binary({field: fm[field]}, raw, fm[field])
    return EXIT_OK


def handle_frontmatter_set(rest):
    """Edição escopada SÓ da linha da chave alvo; campo dict (bloco
    indentado) devolve o guard de no-op do contrato (#1660)."""
    pos, flags = parse_verb_args(rest, value_flags=("--field", "--value"))
    raw = "--raw" in rest
    if not pos or not flags.get("--field") or flags.get("--value") is None:
        die("Usage: frontmatter.set <file> --field <campo> --value <valor>",
            EXIT_CONTRACT)
    p = Path(pos[0])
    if not p.is_file():
        output_like_binary({"error": "File not found"}, raw, False)
        return EXIT_OK
    text = p.read_text(encoding="utf-8")
    field, value = flags["--field"], flags["--value"]
    lines = text.split("\n")
    _, end = parse_frontmatter_lines(text)
    if end is None:
        output_like_binary({"error": "no frontmatter block"}, raw, False)
        return EXIT_OK
    target = None
    for i in range(1, end):
        if re.match(rf"^{re.escape(field)}\s*:", lines[i]):
            target = i
            break
    if target is not None and target + 1 < end \
            and re.match(r"^\s+\S", lines[target + 1]) \
            and not lines[target].split(":", 1)[1].strip():
        output_like_binary(
            {"error": f"campo '{field}' é bloco aninhado — o parser não "
             "faz round-trip fiel; edite o arquivo direto (#1660)"},
            raw, False)
        return EXIT_OK
    if target is not None:
        lines[target] = f"{field}: {value}"
    else:
        lines.insert(end, f"{field}: {value}")
    p.write_text("\n".join(lines), encoding="utf-8")
    result = {"updated": True, "field": field, "value": value,
              "path": pos[0]}
    output_like_binary(result, raw, True)
    return EXIT_OK


def handle_frontmatter_validate(rest):
    pos, flags = parse_verb_args(rest, value_flags=("--schema",))
    raw = "--raw" in rest
    schema = flags.get("--schema")
    if not pos or not schema:
        die("Usage: frontmatter.validate <file> --schema <nome>",
            EXIT_CONTRACT)
    required = SCHEMA_FIELDS.get(schema)
    if required is None:
        die(f"schema desconhecido: {schema} "
            f"({'|'.join(sorted(SCHEMA_FIELDS))})", EXIT_CONTRACT)
    p = Path(pos[0])
    if not p.is_file():
        output_like_binary({"error": "File not found"}, raw, False)
        return EXIT_OK
    fm, _ = parse_frontmatter_lines(p.read_text(encoding="utf-8"))
    present = [f for f in required if f in fm]
    missing = [f for f in required if f not in fm]
    result = {"valid": not missing, "schema": schema, "present": present,
              "missing": missing, "errors": [], "invalidValue": None}
    output_like_binary(result, raw, not missing)
    return EXIT_OK


def handle_git_base_branch(rest):
    """Texto puro; degradação NÃO-verificada sai 'main' com warning em
    stderr e exit 0 (semântica medida #3057)."""
    cwd = Path.cwd()
    for name in ("main", "master"):
        code, _, _ = run_git(["show-ref", "--verify", "--quiet",
                              f"refs/heads/{name}"], cwd)
        if code == 0:
            emit(name)
            return EXIT_OK
    code, out, _ = run_git(["symbolic-ref", "--short", "HEAD"], cwd)
    if code == 0 and out and run_git(
            ["show-ref", "--verify", "--quiet",
             f"refs/heads/{out}"], cwd)[0] == 0:
        emit(out)
        return EXIT_OK
    sys.stderr.write(f"{TAG_PREFIX} warning: base branch não verificável "
                     "— degradando para 'main' (#3057)\n")
    emit("main")
    return EXIT_OK


def capability_unavailable(name, valid_subs, rest):
    """Indisponibilidade DECLARADA (nunca silêncio) para capability cortada."""
    pos, _ = parse_verb_args(rest)
    sub = pos[0] if pos else None
    if sub not in valid_subs:
        die(f"Unknown {name} subcommand: {sub}. "
            f"Available: {', '.join(valid_subs)}", EXIT_CONTRACT)
    output_like_binary({"available": False,
                        "reason": f"{name}: {CAP_MSG}"}, "--raw" in rest)
    return EXIT_OK


def handle_graphify(rest):
    return capability_unavailable(
        "graphify", ("build", "diff", "query", "status"), rest)


def handle_intel(rest):
    return capability_unavailable(
        "intel", ("api-surface", "diff", "extract-exports", "patch-meta",
                  "query", "snapshot", "status", "update", "validate"),
        rest)


def learnings_store():
    base = os.environ.get("CAIRN_LEARNINGS_DIR")
    return Path(base) if base else Path.home() / ".cairn" / "learnings"


def handle_learnings_copy(rest):
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    src = root / ".planning" / "learnings"
    files = sorted(src.glob("*.md")) if src.is_dir() else []
    created = skipped = 0
    if files:
        dest = learnings_store()
        dest.mkdir(parents=True, exist_ok=True)
        for f in files:
            target = dest / f.name
            if target.exists():
                skipped += 1
            else:
                target.write_text(f.read_text(encoding="utf-8"),
                                  encoding="utf-8")
                created += 1
    result = {"total": len(files), "created": created, "skipped": skipped}
    output_like_binary(result, raw)
    return EXIT_OK


def handle_learnings_query(rest):
    _, flags = parse_verb_args(rest, value_flags=("--tag",))
    raw = "--raw" in rest
    tag = flags.get("--tag")
    if not tag:
        die("--tag required", EXIT_CONTRACT)
    store = learnings_store()
    hits = []
    if store.is_dir():
        for f in sorted(store.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                continue
            fm, _ = parse_frontmatter_lines(text)
            tags = [t.strip() for t in
                    str(fm.get("tags", "")).strip("[]").split(",")]
            if tag in tags:
                hits.append({"file": f.name, "tags": tags})
    result = {"tag": tag, "count": len(hits), "learnings": hits}
    output_like_binary(result, raw)
    return EXIT_OK


def handle_normalize_test_command(rest):
    """#1857: reescreve runner watch-mode para one-shot (texto puro)."""
    pos, _ = parse_verb_args(rest, value_flags=("--cwd",))
    cmd = " ".join(pos)
    toks = cmd.split()
    if "vitest" in toks and "run" not in toks:
        i = toks.index("vitest")
        toks.insert(i + 1, "run")
        cmd = " ".join(toks)
    elif "jest" in toks and "--watchAll=false" not in toks:
        cmd = cmd + " --watchAll=false"
    emit(cmd)
    return EXIT_OK


def handle_package_legitimacy(rest):
    """Offline fail-safe: verdict 'unverified' — nunca afirma legitimidade
    sem registry (divergência declarada)."""
    pos, flags = parse_verb_args(rest, value_flags=("--ecosystem",))
    raw = "--raw" in rest
    if not pos or pos[0] != "check":
        die(f"Unknown package-legitimacy subcommand: "
            f"{pos[0] if pos else None}. Available: check", EXIT_CONTRACT)
    eco = flags.get("--ecosystem")
    if not eco:
        die("--ecosystem required", EXIT_CONTRACT)
    pkgs = pos[1:]
    result = [{"package": p, "ecosystem": eco, "verdict": "unverified",
               "reason": "offline — verificação de registry indisponível "
                         "no cairn; trate como não-verificado"}
              for p in pkgs]
    output_like_binary(result, raw)
    return EXIT_OK


def handle_plan_task_structure(rest):
    die("Unknown command: plan — plan.task-structure é verbo fantasma da "
        "tag (contrato da fase 31); a checagem real é "
        "verify.plan-structure (fase 35)", EXIT_CONTRACT)


def handle_is(rest):
    die("Unknown command: is — falso positivo da métrica registrado no "
        "contrato da fase 31 (prosa de comentário, não chamada)",
        EXIT_CONTRACT)


def handle_teams_status(rest):
    """Puro: active só com env strictly-truthy E runtime claude; --active
    codifica o boolean no exit (exceção deliberada do contrato)."""
    env = os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS")
    present = env is not None
    active = env in ("1", "true")
    source = "on: env" if active else "off: flag absent"
    if "--active" in rest:
        emit("true" if active else "false")
        return EXIT_OK if active else EXIT_CONTRACT
    result = {"active": active, "env_present": present,
              "runtime": "claude", "source": source}
    output_like_binary(result, "--raw" in rest)
    return EXIT_OK


def handle_websearch(rest):
    """Host único: o claude tem WebSearch nativa — o verbo declara a
    indisponibilidade (fail-open do contrato) e orienta a ferramenta."""
    pos, _ = parse_verb_args(rest, value_flags=("--limit", "--freshness"))
    result = {"available": False, "query": " ".join(pos) or None,
              "reason": "use a ferramenta WebSearch nativa do host claude "
                        "— API de busca externa não é gerenciada pelo "
                        "cairn"}
    output_like_binary(result, "--raw" in rest)
    return EXIT_OK


def handle_windows(rest):
    """Ledger de broken-windows (#1950) em .planning/windows.json; entry
    sem timestamp (doutrina de determinismo — divergência declarada)."""
    pos, flags = parse_verb_args(rest, value_flags=(
        "--kind", "--phase", "--file", "--line", "--description"))
    raw = "--raw" in rest
    sub = pos[0] if pos else None
    root = find_project_root(Path.cwd())
    ledger_path = root / ".planning" / "windows.json"
    ledger = {"entries": []}
    if ledger_path.is_file():
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            die(f"ledger malformado: {ledger_path}", EXIT_CONTRACT)
        if not isinstance(ledger, dict) \
                or not isinstance(ledger.get("entries"), list):
            die(f"ledger malformado: {ledger_path}", EXIT_CONTRACT)

    def save():
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(json.dumps(ledger, indent=2,
                                          ensure_ascii=False) + "\n",
                               encoding="utf-8")

    if sub == "append":
        missing = [f for f in ("--kind", "--phase", "--file",
                               "--description") if not flags.get(f)]
        if missing:
            die(f"flags obrigatórias ausentes: {', '.join(missing)}",
                EXIT_CONTRACT)
        entry = {"id": len(ledger["entries"]) + 1,
                 "kind": flags["--kind"], "phase": flags["--phase"],
                 "file": flags["--file"], "line": flags.get("--line"),
                 "description": flags["--description"], "status": "open"}
        ledger["entries"].append(entry)
        save()
        output_like_binary({"ok": True, "ledger": str(ledger_path),
                            "entry": entry}, raw, True)
        return EXIT_OK
    if sub == "status":
        output_like_binary({"ok": True, "ledger": str(ledger_path),
                            "entries": ledger["entries"]}, raw)
        return EXIT_OK
    if sub in ("waive", "fixed"):
        if len(pos) < 2 or (sub == "waive" and len(pos) < 3):
            die(f"Usage: windows {sub} <id>"
                + (" <reason>" if sub == "waive" else ""), EXIT_CONTRACT)
        target = next((e for e in ledger["entries"]
                       if str(e.get("id")) == pos[1]), None)
        if target is None:
            die(f"entrada {pos[1]} não existe no ledger", EXIT_CONTRACT)
        target["status"] = "waived" if sub == "waive" else "fixed"
        if sub == "waive":
            target["waive_reason"] = pos[2]
        save()
        output_like_binary({"ok": True, "ledger": str(ledger_path),
                            "entry": target}, raw, True)
        return EXIT_OK
    die(f"Unknown windows subcommand: {sub}. "
        "Available: append, status, waive, fixed", EXIT_CONTRACT)


HANDLERS = {
    "classify-confidence": handle_classify_confidence,
    "estimate-check": handle_estimate_check,
    "frontmatter.get": handle_frontmatter_get,
    "frontmatter.set": handle_frontmatter_set,
    "frontmatter.validate": handle_frontmatter_validate,
    "git.base-branch": handle_git_base_branch,
    "graphify": handle_graphify,
    "intel": handle_intel,
    "is": handle_is,
    "learnings.copy": handle_learnings_copy,
    "learnings.query": handle_learnings_query,
    "normalize-test-command": handle_normalize_test_command,
    "package-legitimacy": handle_package_legitimacy,
    "plan.task-structure": handle_plan_task_structure,
    "teams-status": handle_teams_status,
    "websearch": handle_websearch,
    "windows": handle_windows,
    "init.autonomous": handle_init_autonomous,
    "init.debug": handle_init_debug,
    "init.execute-phase": handle_init_execute_phase,
    "init.manager": handle_init_manager,
    "init.milestone-op": handle_init_milestone_op,
    "init.phase-op": handle_init_phase_op,
    "init.plan-phase": handle_init_plan_phase,
    "init.quick": handle_init_quick,
    "init.verify-work": handle_init_verify_work,
    "worktree": handle_worktree,
    "worktree.base-check": handle_worktree_base_check,
    "worktree.set-baseref": handle_worktree_set_baseref,
    "worktree.cleanup-wave": handle_worktree_cleanup_wave,
    "worktree.create": handle_worktree_create,
    "worktree.record-agent": handle_worktree_record_agent,
    "worktree.reap-orphans": handle_worktree_reap_orphans,
}

# ---- main ------------------------------------------------------------------ #
def family_of(verb):
    try:
        agg = json.loads(
            (CONTRACTS_DIR / "contracts.json").read_text(encoding="utf-8"))
        return ((agg.get("verbs") or {}).get(verb) or {}).get("family") \
            or "?"
    except (OSError, json.JSONDecodeError, ValueError):
        return "?"

def main():
    argv = sys.argv[1:]
    if not argv:
        die(USAGE, EXIT_USAGE)
    if argv[0] == "--list-implemented":
        for verb in sorted(HANDLERS):
            print(verb)
        sys.exit(EXIT_OK)
    verb = argv[0]
    handler = HANDLERS.get(verb)
    if handler is None:
        die(f"verbo '{verb}' da família '{family_of(verb)}' é entregue pela "
            "fase 34 — ainda não implementado neste script",
            EXIT_UNIMPLEMENTED)
    sys.exit(handler(argv[1:]))

if __name__ == "__main__":
    main()
