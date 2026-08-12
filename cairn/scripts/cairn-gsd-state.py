#!/usr/bin/env python3
"""cairn-gsd-state.py — irmão de estado do dispatcher cairn-gsd.py (D-01).

Estado + roadmap-phase + 7 misc de planning-docs sobre o bd: FATO vive em
labels projetados de um bead portador único; DOCUMENTO segue no filesystem.
Invocado pelo dispatcher via os.execv com o VERBO canônico como argv[1].
Usage: cairn-gsd-state.py <verbo> [argv] | --list-implemented. Exits: 0
contrato; 1 erro contratado (FATO ausente nomeia o fato E o comando que o
cria — CORE-04); 2 uso; 4 verbo ainda sem handler.

As três regras não opcionais do bd (medidas 2026-08-10, bd 1.1.0):
(1) consulta SÓ por label projetado — metadata aninhado devolve rc 0
silencioso; (2) transição SÓ via `bd set-state <id> dim=val --actor
--reason` (event bead = auditoria; update direto vira root sem motivo);
(3) fato ausente é falha NOMEADA — nunca fallback para markdown.
Envelope: cairn_gsd_render (semântica medida). Divergências:
tests/fixtures/gsd-goldens/divergences.json. cairn/gsd/ é SOMENTE-LEITURA.
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

TAG_PREFIX = "[cairn-gsd-state]"

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "gsd" / "contracts"

# D-02 (LOCKED, one-way): o vocabulário de dimensões — a FONTE ÚNICA. Os
# verbos gsd MAPEIAM para estas 5; labels projetados `dim:valor` são o
# índice permanente do bd (migração de acervo para renomear). `progress`
# NÃO é dimensão: é DERIVADO. Nenhuma sexta dimensão, nunca.
VERB_DIMENSIONS = {
    # dimensão -> vocabulário fechado (None = valor livre com forma)
    "dimensions": {
        "phase": None,                     # número corrente (phase:<N>)
        "phase_status": ("planned", "executing", "verified", "complete"),
        "plan": None,                      # NN-MM corrente (plan:<NN-MM>)
        "verification": ("passed", "failed", "pending"),
        "session": None,                   # YYYY-MM-DD da última atividade
    },
    # verbo -> dimensões que ESCREVE (transição sempre via set-state)
    "writes": {
        "state.begin-phase": ("phase", "phase_status"),
        "state.planned-phase": ("phase", "phase_status"),
        "state.advance-plan": ("plan",),
        "state.record-session": ("session",),
        "state.update": (),  # dimensão vem de field_map, por campo
        "phase.complete": ("phase", "phase_status"),
    },
    # campo do state.update -> dimensão; fora do mapa não toca o bd
    "field_map": {
        "phase": "phase",
        "status": "phase_status",
        "phase_status": "phase_status",
        "plan": "plan",
        "current_plan": "plan",
        "verification": "verification",
        "session": "session",
    },
}

# O bead portador: único por repo (label âncora gsd-state); 0 num leitor ->
# falha nomeada prescrevendo begin-phase; >1 -> ambiguidade nomeada.
ANCHOR_LABEL = "gsd-state"
CARRIER_TITLE = "gsd: portador de estado (D-02)"

# Coleções (CORE-02): fatos consultáveis por label, beads próprios.
BLOCKER_LABEL = "gsd-blocker"
DECISION_LABEL = "gsd-decision"

# Forma dos valores livres (CORE-02 encoding): validada em toda escrita.
DIMENSION_FORMS = {
    "phase": re.compile(r"^\d+$"),
    "plan": re.compile(r"^\d+-\d+$"),
    "session": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
}

FIELD_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")

PLAN_FILE = re.compile(r"^\d+-(\d+)-PLAN\.md$")
SUMMARY_FILE = re.compile(r"^\d+-(\d+)-SUMMARY\.md$")
PHASE_DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")

def die(msg, code=EXIT_USAGE):
    print(f"{TAG_PREFIX} error: {msg}", file=sys.stderr)
    sys.exit(code)

# acesso ao bd — molde run_bd de cairn-lease.py: falha vira die nomeado,
def run_bd(args, root):
    cmd = ["bd", "-C", str(root)] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        die("'bd' não está no PATH — instale beads para os verbos de estado",
            EXIT_CONTRACT)
    if proc.returncode != 0:
        die(f"bd {args[0] if args else ''} falhou: "
            f"{proc.stderr.strip() or 'erro desconhecido'}", EXIT_CONTRACT)
    return proc.stdout

def bd_json(args, root):
    out = run_bd(args + ["--json"], root)
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError as e:
        die(f"bd devolveu JSON inválido: {e}", EXIT_CONTRACT)
    if data is None:
        return []
    return data if isinstance(data, list) else [data]

def as_str_list(val):
    """Shape defensivo dos campos do bd (molde cairn-status.py)."""
    if isinstance(val, str):
        val = [val]
    if not isinstance(val, list):
        return []
    out = []
    for x in val:
        if isinstance(x, dict):
            x = x.get("id")
        if x is not None:
            out.append(str(x))
    return out

def resolve_actor(root):
    """Mesma ordem que o bd documenta: BEADS_ACTOR > git user.name > USER."""
    env_actor = os.environ.get("BEADS_ACTOR")
    if env_actor:
        return env_actor
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "config", "user.name"],
            capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except FileNotFoundError:
        pass
    user = os.environ.get("USER")
    if user:
        return user
    die("ator irresolvível (BEADS_ACTOR, git user.name e USER vazios) — "
        "toda transição exige ator", EXIT_CONTRACT)

# o portador — consulta SEMPRE por label projetado (CORE-02)
def list_by_label(root, label):
    return bd_json(["list", "-l", label, "--all", "--limit", "0"], root)

def find_carrier(root, required=True):
    issues = list_by_label(root, ANCHOR_LABEL)
    if not issues:
        if required:
            die("o bd não tem portador de estado gsd (label gsd-state) "
                "neste repo; rode 'cairn-gsd.sh query state.begin-phase <N>' "
                "para criar o fato", EXIT_CONTRACT)
        return None
    if len(issues) > 1:
        ids = ", ".join(sorted(str(i.get("id")) for i in issues))
        die(f"portador de estado ambíguo: {len(issues)} beads carregam o "
            f"label gsd-state ({ids}) — o portador é único por repo; feche "
            "os excedentes", EXIT_CONTRACT)
    return issues[0]

def die_missing_dim(dim, cmd="state.begin-phase <N>"):
    die(f"o portador não tem a dimensão {dim}; rode 'cairn-gsd.sh query "
        f"{cmd}' para criar o fato", EXIT_CONTRACT)

def need_phase(rest, value_flags=()):
    pos, flags = parse_verb_args(rest, value_flags=value_flags)
    if not pos:
        die("phase required", EXIT_CONTRACT)
    return pos, flags

def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        die(f"fase não-inteira: {value}", EXIT_CONTRACT)

def create_carrier(root):
    out = run_bd(["create", CARRIER_TITLE, "-t", "chore",
                  "-l", ANCHOR_LABEL, "--silent"], root)
    issue_id = out.strip().splitlines()[-1].strip() if out.strip() else ""
    if not issue_id:
        die("bd create não devolveu id para o portador gsd-state",
            EXIT_CONTRACT)
    return issue_id

def carrier_dimensions(issue):
    """As dimensões D-02 presentes nos labels projetados do portador."""
    dims = {}
    for lab in as_str_list(issue.get("labels")):
        if ":" not in lab:
            continue
        dim, val = lab.split(":", 1)
        if dim in VERB_DIMENSIONS["dimensions"]:
            dims[dim] = val
    return dims

def set_dimension(root, issue_id, dim, value, actor, reason):
    """Transição de dimensão EXCLUSIVAMENTE via set-state com ator e motivo."""
    vocab = VERB_DIMENSIONS["dimensions"].get(dim)
    if vocab is not None and value not in vocab:
        die(f"valor '{value}' fora do vocabulário da dimensão {dim} "
            f"({'|'.join(vocab)})", EXIT_CONTRACT)
    form = DIMENSION_FORMS.get(dim)
    if form is not None and not form.match(value):
        die(f"valor '{value}' fora da forma da dimensão {dim} "
            f"({form.pattern})", EXIT_CONTRACT)
    out = bd_json(["set-state", issue_id, f"{dim}={value}",
                   "--actor", actor, "--reason", reason], root)
    entry = out[0] if out else {}
    return bool(entry.get("changed"))

def carrier_metadata(root, issue_id):
    """Metadata corrente do portador (leitura para read-modify-write)."""
    data = bd_json(["show", issue_id], root)
    entry = data[0] if data else {}
    meta = entry.get("metadata")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, ValueError):
            meta = {}
    return meta if isinstance(meta, dict) else {}

def write_metadata(root, issue_id, meta):
    """Escrita de metadata que NÃO é transição de estado (molde write_lease."""
    run_bd(["update", issue_id, "--metadata", json.dumps(meta)], root)

def gsd_meta_slot(meta):
    """O slot cairn.gsd do metadata, criado defensivamente."""
    cairn = meta.get("cairn")
    if not isinstance(cairn, dict):
        cairn = {}
        meta["cairn"] = cairn
    gsd = cairn.get("gsd")
    if not isinstance(gsd, dict):
        gsd = {}
        cairn["gsd"] = gsd
    return gsd

def find_project_root(cwd):
    """findProjectRoot reduzido: sobe procurando .planning; sem âncora, o."""
    cur = Path(cwd).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / ".planning").is_dir():
            return candidate
    return cur

def phase_dir_of(root, phase_n):
    """O diretório .planning/phases/ da fase N (documento), ou None."""
    phases = root / ".planning" / "phases"
    if not phases.is_dir():
        return None
    for entry in sorted(phases.iterdir()):
        if not entry.is_dir():
            continue
        m = PHASE_DIR_PREFIX.match(entry.name)
        if m and int(m.group(1)) == phase_n:
            return entry
    return None

def count_phase_plans(root, phase_n):
    d = phase_dir_of(root, phase_n)
    if d is None:
        return 0
    return sum(1 for f in d.iterdir() if PLAN_FILE.match(f.name))

# handlers — família estado
def transition_position(rest, verb, status):
    """Caminho ÚNICO de transição de posição (begin-phase e planned-phase o."""
    pos, flags = parse_verb_args(
        rest, value_flags=("--phase", "--name", "--plans"))
    phase = flags.get("--phase") or (pos[0] if pos else None)
    if phase is None:
        die(f"{verb} requer a fase (--phase <N> ou posicional)",
            EXIT_CONTRACT)
    try:
        phase_n = int(str(phase).strip())
    except ValueError:
        die(f"fase não-inteira: {phase}", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    plans = flags.get("--plans")
    if plans is not None:
        try:
            plan_count = int(str(plans).strip())
        except (TypeError, ValueError):
            die(f"--plans com valor não-inteiro: {plans}", EXIT_CONTRACT)
    else:
        plan_count = count_phase_plans(root, phase_n)
    carrier = find_carrier(root, required=False)
    created = False
    if carrier is None:
        issue_id = create_carrier(root)
        created = True
    else:
        issue_id = str(carrier.get("id"))
    actor = resolve_actor(root)
    reason = f"{verb} {phase_n} via cairn-gsd"
    updated = []
    if set_dimension(root, issue_id, "phase", str(phase_n), actor, reason):
        updated.append("phase")
    if set_dimension(root, issue_id, "phase_status", status, actor, reason):
        updated.append("phase_status")
    result = {"phase": phase_n, "phase_name": flags.get("--name"),
              "plan_count": plan_count, "updated": updated}
    if created:
        result["created"] = True
    return result

def handle_state_begin_phase(rest):
    """Shape do contrato: {error, phase, phase_name, plan_count, updated}."""
    result = transition_position(rest, "state.begin-phase", "executing")
    output_like_binary(result, "--raw" in rest, True)
    return EXIT_OK

def handle_state_planned_phase(rest):
    """Shape: {error, phase, plan_count, updated, warning} — warning quando."""
    result = transition_position(rest, "state.planned-phase", "planned")
    if not result["updated"]:
        result["warning"] = ("transição no-op — o portador já carrega "
                            "phase e phase_status nesses valores")
    output_like_binary(result, "--raw" in rest, True)
    return EXIT_OK

def handle_state_update(rest):
    """state.update <field> <value>: traduz o campo para a dimensão D-02."""
    pos, _ = parse_verb_args(rest)
    raw = "--raw" in rest
    if len(pos) < 2:
        die("Usage: state.update <field> <value>", EXIT_CONTRACT)
    field, value = pos[0], pos[1]
    if not FIELD_NAME_RE.match(field):
        die(f"nome de campo inválido: '{field}'", EXIT_CONTRACT)
    dim = VERB_DIMENSIONS["field_map"].get(field)
    if dim is None:
        result = {"updated": False,
                  "reason": f"campo '{field}' não projeta dimensão D-02 — "
                            "documento, não fato"}
        output_like_binary(result, raw, False)
        return EXIT_OK
    root = find_project_root(Path.cwd())
    carrier = find_carrier(root)
    set_dimension(root, str(carrier.get("id")), dim, value,
                  resolve_actor(root), f"state.update {field}={value}")
    output_like_binary({"updated": [field]}, raw, True)
    return EXIT_OK

def handle_state_advance_plan(rest):
    """Avança a dimensão plan para o NN-MM seguinte; total_plans é contagem."""
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    carrier = find_carrier(root)
    dims = carrier_dimensions(carrier)
    plan_val = dims.get("plan")
    if plan_val is None:
        die_missing_dim("plan", "state.update plan <NN-MM>")
    m = re.match(r"^(\d+)-(\d+)$", plan_val)
    if m is None:
        die(f"dimensão plan malformada no portador: {plan_val}",
            EXIT_CONTRACT)
    phase_part, cur = m.group(1), int(m.group(2))
    total = count_phase_plans(root, int(phase_part))
    if total and cur >= total:
        result = {"advanced": False, "reason": "last_plan",
                  "status": "ready_for_verification",
                  "current_plan": plan_val, "total_plans": total}
        output_like_binary(result, raw, False)
        return EXIT_OK
    nxt = f"{phase_part}-{cur + 1:02d}"
    set_dimension(root, str(carrier.get("id")), "plan", nxt,
                  resolve_actor(root),
                  f"state.advance-plan {plan_val}→{nxt}")
    result = {"advanced": True, "previous_plan": plan_val,
              "current_plan": nxt, "total_plans": total}
    output_like_binary(result, raw, True)
    return EXIT_OK

def handle_state_update_progress(rest):
    """progress é DERIVADO, nunca dimensão (D-02): completed/total contados."""
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    find_carrier(root)
    phases = root / ".planning" / "phases"
    total = completed = 0
    if phases.is_dir():
        for d in sorted(phases.iterdir()):
            if not d.is_dir():
                continue
            for f in d.iterdir():
                if PLAN_FILE.match(f.name):
                    total += 1
                elif SUMMARY_FILE.match(f.name):
                    completed += 1
    percent = round(completed * 100 / total) if total else 0
    filled = round(percent / 5)
    bar = "[" + "█" * filled + "░" * (20 - filled) + f"] {percent}%"
    result = {"updated": True, "percent": percent, "completed": completed,
              "total": total, "bar": bar}
    output_like_binary(result, raw, bar)
    return EXIT_OK

def handle_state_record_session(rest):
    """Transiciona session=YYYY-MM-DD (última atividade) via set-state;."""
    _, flags = parse_verb_args(
        rest, value_flags=("--stopped-at", "--resume-file"))
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    carrier = find_carrier(root)
    issue_id = str(carrier.get("id"))
    today = time.strftime("%Y-%m-%d")
    set_dimension(root, issue_id, "session", today, resolve_actor(root),
                  "state.record-session")
    updated = ["session"]
    payload = {}
    if flags.get("--stopped-at") is not None:
        payload["stopped_at"] = flags["--stopped-at"]
        updated.append("stopped_at")
    if flags.get("--resume-file") is not None:
        payload["resume_file"] = flags["--resume-file"]
        updated.append("resume_file")
    if payload:
        meta = carrier_metadata(root, issue_id)
        gsd_meta_slot(meta)["session"] = payload
        write_metadata(root, issue_id, meta)
    output_like_binary({"recorded": True, "updated": updated}, raw, True)
    return EXIT_OK

def handle_state_load(rest):
    """Leitor do tracer: config/roadmap/debug_dir são DOCUMENTO (filesystem);."""
    root = find_project_root(Path.cwd())
    carrier = find_carrier(root)
    dims = carrier_dimensions(carrier)
    state_raw = "\n".join(f"{k}: {dims[k]}" for k in sorted(dims))
    config_exists = (root / ".planning" / "config.json").is_file()
    config = load_config_defensive(root)
    result = {
        "config": config,
        "config_exists": config_exists,
        "debug_dir": str(root / ".planning" / "debug"),
        "roadmap_exists": (root / ".planning" / "ROADMAP.md").is_file(),
        "state_exists": True,
        "state_raw": state_raw,
    }
    output_like_binary(result, "--raw" in rest)
    return EXIT_OK

# documento — parsers de ROADMAP/PLAN por cópia de forma (bookkeep/status).
HEAD_ANY = re.compile(r"^(#{1,6})\s")
HEAD_PHASE = re.compile(r"^(#{1,6})\s+Phase\s+0*(\d+)\b")
HEAD_PHASE_TITLE = re.compile(r"^#{1,6}\s+Phase\s+0*(\d+)\s*:\s*(.+?)\s*$")
HEAD_MILESTONE = re.compile(r"^#{1,6}\s+Milestone:\s*(.+?)\s*$")
CHECKBOX_PHASE = re.compile(r"^\s*-\s*\[([ xX])\]\s.*?\bPhase\s+0*(\d+)\b")
PLAN_CHECKBOX = re.compile(r"^\s*-\s*\[([ xX])\]\s*(\d+-\d+)-PLAN\.md\b")
GOAL_LINE = re.compile(r"^\*\*Goal:?\*\*:?\s*(.*)$")
MODE_LINE = re.compile(r"^(?:\*\*)?Mode(?:\*\*)?:\s*(\S+)", re.IGNORECASE)
SUCCESS_HEAD = re.compile(r"success criteria", re.IGNORECASE)

def roadmap_text(root):
    """Texto do ROADMAP.md, ou None quando ausente (documento)."""
    p = root / ".planning" / "ROADMAP.md"
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except OSError as e:
        die(f"falha de leitura de {p}: {e}", EXIT_CONTRACT)

def phase_section_bounds(lines, phase_n):
    """(start, end, title) da seção de detalhe da fase, ou None."""
    start = level = title = None
    for i, ln in enumerate(lines):
        m = HEAD_PHASE.match(ln)
        if m and int(m.group(2)) == phase_n:
            start, level = i, len(m.group(1))
            mt = HEAD_PHASE_TITLE.match(ln)
            title = mt.group(2).strip() if mt else None
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = HEAD_ANY.match(lines[j])
        if m and len(m.group(1)) <= level:
            end = j
            break
    return start, end, title

def parse_frontmatter(text):
    """Subset YAML plano (molde parse_state_frontmatter do bookkeep):"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out

def fm_list(val):
    """Lista inline do frontmatter: '[a, b]' -> ['a', 'b']."""
    v = (val or "").strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("'\"") for x in v[1:-1].split(",")
                if x.strip()]
    return [v.strip("'\"")] if v else []

def phase_dirs(root, include_archived=False):
    """Diretórios de fase de .planning/phases (e arquivados, opcional)."""
    dirs = []
    phases = root / ".planning" / "phases"
    if phases.is_dir():
        dirs += sorted(d for d in phases.iterdir() if d.is_dir())
    if include_archived:
        ms = root / ".planning" / "milestones"
        if ms.is_dir():
            for md in sorted(ms.iterdir()):
                if md.is_dir() and md.name.endswith("-phases"):
                    dirs += sorted(d for d in md.iterdir() if d.is_dir())
    return dirs

def locate_phase_dir(root, target, include_archived=False):
    """O diretório da fase por número ou token, ou None."""
    for d in phase_dirs(root, include_archived):
        m = PHASE_DIR_PREFIX.match(d.name)
        if str(target).isdigit():
            if m and int(m.group(1)) == int(target):
                return d
        elif str(target).lower() in d.name.lower():
            return d
    return None

def dir_counts(d):
    """(plans, summaries) de um diretório de fase; (0, 0) quando None."""
    if d is None or not d.is_dir():
        return 0, 0
    p = s = 0
    for f in d.iterdir():
        if PLAN_FILE.match(f.name):
            p += 1
        elif SUMMARY_FILE.match(f.name):
            s += 1
    return p, s

def load_config_defensive(root):
    """Config do escopo sem morrer nunca (molde do dispatcher)."""
    try:
        data = json.loads((root / ".planning" / "config.json")
                          .read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}

# handlers — família roadmap-phase (leitores)
def handle_find_phase(rest):
    """Localiza o diretório da fase (fases vivas + arquivadas); não achada."""
    pos, _ = parse_verb_args(rest)
    raw = "--raw" in rest
    if not pos:
        die("phase identifier required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    searched = [".planning/phases"]
    ms = root / ".planning" / "milestones"
    if ms.is_dir():
        searched += [f".planning/milestones/{m.name}"
                     for m in sorted(ms.iterdir())
                     if m.is_dir() and m.name.endswith("-phases")]
    hit = locate_phase_dir(root, pos[0], include_archived=True)
    if hit is None:
        output_like_binary({"found": False,
                            "searched_directories": searched}, raw, "")
        return EXIT_OK
    m = PHASE_DIR_PREFIX.match(hit.name)
    rel = hit.relative_to(root).as_posix()
    result = {
        "found": True, "directory": rel,
        "phase_number": int(m.group(1)) if m else None,
        "phase_name": hit.name[m.end():] if m else hit.name,
        "plans": sorted(f.name for f in hit.iterdir()
                        if PLAN_FILE.match(f.name)),
        "summaries": sorted(f.name for f in hit.iterdir()
                            if SUMMARY_FILE.match(f.name)),
    }
    output_like_binary(result, raw, rel)
    return EXIT_OK

def handle_phases_list(rest):
    """Sem --type: {directories, count}; com --type plans|summaries:"""
    _, flags = parse_verb_args(rest, value_flags=("--type", "--phase"),
                               bool_flags=("--raw", "--include-archived"))
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    archived = "--include-archived" in rest
    typ = flags.get("--type")
    dirs = phase_dirs(root, archived)
    if typ is None:
        names = [d.name for d in dirs]
        output_like_binary({"directories": names, "count": len(names)},
                           raw, "\n".join(names))
        return EXIT_OK
    if typ not in ("plans", "summaries"):
        die(f"--type desconhecido: {typ} (plans|summaries)", EXIT_CONTRACT)
    matcher = PLAN_FILE if typ == "plans" else SUMMARY_FILE
    phase_dir_out = None
    if flags.get("--phase"):
        d = locate_phase_dir(root, flags["--phase"], archived)
        if d is None:
            output_like_binary({"files": [], "count": 0, "phase_dir": None,
                                "error": "Phase not found"}, raw, "")
            return EXIT_OK
        dirs = [d]
        phase_dir_out = d.relative_to(root).as_posix()
    files = []
    for d in dirs:
        files += sorted((d / f.name).relative_to(root).as_posix()
                        for f in d.iterdir() if matcher.match(f.name))
    output_like_binary({"files": files, "count": len(files),
                        "phase_dir": phase_dir_out}, raw, "\n".join(files))
    return EXIT_OK

def handle_phase_list_plans(rest):
    """#1437: PLANs da fase com paths relativos utilizáveis."""
    pos, _ = need_phase(rest)
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    d = locate_phase_dir(root, pos[0])
    if d is None:
        result = {"phase": pos[0], "plan_count": 0, "has_plans": False,
                  "plans": [], "phase_dir": None}
        output_like_binary(result, raw)
        return EXIT_OK
    plans = sorted((d / f.name).relative_to(root).as_posix()
                   for f in d.iterdir() if PLAN_FILE.match(f.name))
    result = {"phase": pos[0],
              "phase_dir": d.relative_to(root).as_posix(),
              "plan_count": len(plans), "has_plans": bool(plans),
              "plans": plans}
    output_like_binary(result, raw)
    return EXIT_OK

def handle_phase_plan_index(rest):
    """Indexa PLANs da fase: wave/status/checkpoints dos frontmatters."""
    pos, _ = need_phase(rest)
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    d = locate_phase_dir(root, pos[0])
    if d is None:
        result = {"phase": pos[0], "error": "Phase not found", "plans": [],
                  "waves": {}, "incomplete": [], "runnable": [],
                  "has_checkpoints": False}
        output_like_binary(result, raw)
        return EXIT_OK
    summaries = {f.name for f in d.iterdir() if SUMMARY_FILE.match(f.name)}
    plans, waves, incomplete = [], {}, []
    complete_ids = set()
    for f in sorted(d.iterdir()):
        if not PLAN_FILE.match(f.name):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            text = ""
        fm = parse_frontmatter(text)
        plan_id = f.name[:-len("-PLAN.md")]
        wave_raw = str(fm.get("wave", "")).strip()
        wave = int(wave_raw) if wave_raw.isdigit() else 1
        done = f.name.replace("-PLAN.md", "-SUMMARY.md") in summaries
        entry = {"id": plan_id, "file": f.name, "wave": wave,
                 "autonomous": str(fm.get("autonomous", "")).strip().lower()
                 == "true",
                 "depends_on": fm_list(fm.get("depends_on")),
                 "status": "complete" if done else "incomplete",
                 "has_checkpoints": 'type="checkpoint' in text}
        plans.append(entry)
        waves.setdefault(str(wave), []).append(plan_id)
        if done:
            complete_ids.add(plan_id)
        else:
            incomplete.append(plan_id)
    runnable = [p["id"] for p in plans if p["status"] != "complete"
                and all(dep in complete_ids for dep in p["depends_on"])]
    result = {"phase": pos[0], "plans": plans, "waves": waves,
              "incomplete": incomplete, "runnable": runnable,
              "has_checkpoints": any(p["has_checkpoints"] for p in plans)}
    output_like_binary(result, raw)
    return EXIT_OK

def handle_roadmap_get_phase(rest):
    """Seção da fase no ROADMAP (documento): found/goal/mode/section; fase."""
    pos, _ = need_phase(rest)
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    text = roadmap_text(root)
    if text is None:
        die("falha de leitura: .planning/ROADMAP.md ausente", EXIT_CONTRACT)
    target = str(pos[0])
    if target.startswith("999") or not target.isdigit():
        output_like_binary({"found": False}, raw, "")
        return EXIT_OK
    phase_n = int(target)
    lines = text.split("\n")
    bounds = phase_section_bounds(lines, phase_n)
    if bounds is None:
        if any(m and int(m.group(2)) == phase_n
               for m in map(CHECKBOX_PHASE.match, lines)):
            result = {"found": False, "error": "malformed_roadmap",
                      "message": f"Phase {phase_n} está no checklist mas "
                                 "não tem seção de detalhe"}
        else:
            result = {"found": False}
        output_like_binary(result, raw, "")
        return EXIT_OK
    start, end, title = bounds
    section = "\n".join(lines[start:end]).rstrip()
    goal = mode = None
    criteria = []
    for i in range(start, end):
        mg = GOAL_LINE.match(lines[i])
        if mg and goal is None:
            goal = mg.group(1).strip()
        mm = MODE_LINE.match(lines[i])
        if mm and mode is None:
            mode = mm.group(1).lower()
        if SUCCESS_HEAD.search(lines[i]):
            for j in range(i + 1, end):
                mb = re.match(r"^\s*-\s+(.*)$", lines[j])
                if mb:
                    criteria.append(mb.group(1).strip())
                elif criteria:
                    break
    result = {"found": True, "phase_number": phase_n, "phase_name": title,
              "goal": goal, "mode": mode, "success_criteria": criteria,
              "section": section}
    output_like_binary(result, raw, section)
    return EXIT_OK

def handle_roadmap_analyze(rest):
    """A regra documento-vs-fato no verbo mais misto: a lista de fases e."""
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    text = roadmap_text(root)
    if text is None:
        result = {"error": "ROADMAP.md not found", "milestones": [],
                  "phases": [], "current_phase": None}
        output_like_binary(result, raw)
        return EXIT_OK
    carrier = find_carrier(root)
    dims = carrier_dimensions(carrier)
    if "phase" not in dims:
        die_missing_dim("phase")
    current = int(dims["phase"])
    lines = text.split("\n")
    titles, complete = {}, {}
    milestones = []
    for ln in lines:
        mt = HEAD_PHASE_TITLE.match(ln)
        if mt:
            titles.setdefault(int(mt.group(1)), mt.group(2).strip())
        mc = CHECKBOX_PHASE.match(ln)
        if mc:
            n = int(mc.group(2))
            complete[n] = complete.get(n, False) or \
                mc.group(1).lower() == "x"
        mm = HEAD_MILESTONE.match(ln)
        if mm:
            milestones.append(mm.group(1))
    numbers = sorted(set(titles) | set(complete))
    phases = []
    total_plans = total_summaries = 0
    for n in numbers:
        pc, sc = dir_counts(locate_phase_dir(root, n))
        total_plans += pc
        total_summaries += sc
        phases.append({"phase": n, "name": titles.get(n),
                       "complete": complete.get(n, False),
                       "plan_count": pc, "summary_count": sc})
    result = {
        "milestones": milestones, "phases": phases,
        "phase_count": len(phases),
        "completed_phases": sum(1 for p in phases if p["complete"]),
        "current_phase": current,
        "next_phase": next((n for n in numbers if n > current), None),
        "total_plans": total_plans, "total_summaries": total_summaries,
        "progress_percent": (round(total_summaries * 100 / total_plans)
                             if total_plans else 0),
        "missing_phase_details": [n for n in sorted(complete)
                                  if n not in titles],
    }
    output_like_binary(result, raw)
    return EXIT_OK

def handle_phase_mvp_mode(rest):
    """Precedência cli_flag > roadmap (Mode: na seção) > config.mvp_mode."""
    pos, _ = parse_verb_args(rest, bool_flags=("--raw", "--cli-flag"))
    raw = "--raw" in rest
    if not pos:
        die("phase required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    cli = "--cli-flag" in rest
    roadmap_mode = None
    text = roadmap_text(root)
    if text is not None and str(pos[0]).isdigit():
        bounds = phase_section_bounds(text.split("\n"), int(pos[0]))
        if bounds is not None:
            for ln in text.split("\n")[bounds[0]:bounds[1]]:
                mm = MODE_LINE.match(ln)
                if mm:
                    roadmap_mode = mm.group(1).lower()
                    break
    config_mvp = load_config_defensive(root).get("mvp_mode")
    if cli:
        active, source = True, "cli_flag"
    elif roadmap_mode == "mvp":
        active, source = True, "roadmap"
    elif config_mvp:
        active, source = bool(config_mvp), "config"
    else:
        active, source = False, "none"
    result = {"active": active, "cli_flag_present": cli,
              "config_mvp_mode": config_mvp, "roadmap_mode": roadmap_mode,
              "source": source}
    output_like_binary(result, raw)
    return EXIT_OK

def roadmap_titles(lines):
    """{n: título} dos headings de detalhe 'Phase N: ...'."""
    out = {}
    for ln in lines:
        m = HEAD_PHASE_TITLE.match(ln)
        if m:
            out.setdefault(int(m.group(1)), m.group(2).strip())
    return out

def handle_phase(rest):
    """`phase uat-passed <fase>`: predicado FAIL-CLOSED sobre os artefatos."""
    pos, _ = parse_verb_args(rest)
    raw = "--raw" in rest
    sub = pos[0] if pos else None
    if sub != "uat-passed":
        die(f"Unknown phase subcommand: {sub}. Available: uat-passed",
            EXIT_CONTRACT)
    if len(pos) < 2:
        die("phase required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    d = locate_phase_dir(root, pos[1])
    if d is None:
        die(f"fase não encontrada: {pos[1]}", EXIT_CONTRACT)
    uat = sorted(f.name for f in d.iterdir()
                 if f.suffix == ".md" and "UAT" in f.name.upper())
    verif = sorted(f.name for f in d.iterdir()
                   if "VERIFICATION" in f.name.upper())
    checks, blockers = [], []
    for name in uat:
        try:
            fm = parse_frontmatter((d / name).read_text(encoding="utf-8"))
        except OSError:
            fm = {}
        status = str(fm.get("status", "")).strip().lower() or "unknown"
        checks.append({"file": name, "status": status})
        if status not in ("passed", "complete"):
            blockers.append(f"{name}: status {status}")
    if not uat:
        blockers = ["no UAT artifacts found (fail-closed)"]
    result = {"phase": pos[1], "passed": bool(uat) and not blockers,
              "blockers": blockers, "checks": checks,
              "no_uat_artifacts": not uat, "policy": "fail-closed",
              "uat_files": uat, "verification_files": verif,
              "verification_stale_check_indeterminate": True}
    output_like_binary(result, raw)
    return EXIT_OK

def write_roadmap(root, lines, had_trailing_newline):
    p = root / ".planning" / "ROADMAP.md"
    data = "\n".join(lines) + ("\n" if had_trailing_newline else "")
    try:
        p.write_text(data, encoding="utf-8")
    except OSError as e:
        die(f"falha escrevendo {p}: {e}", EXIT_CONTRACT)

def handle_phase_complete(rest):
    """Transição mais gorda da fase: phase_status=complete e avanço da."""
    pos, _ = need_phase(rest)
    raw = "--raw" in rest
    phase_n = to_int(pos[0])
    root = find_project_root(Path.cwd())
    text = roadmap_text(root)
    if text is None:
        die("phase.complete precisa de .planning/ROADMAP.md (documento) — "
            "arquivo ausente", EXIT_CONTRACT)
    d = locate_phase_dir(root, phase_n)
    if d is None:
        die(f"fase {phase_n} não encontrada em .planning/phases",
            EXIT_CONTRACT)
    had_nl = text.endswith("\n")
    lines = text.split("\n")
    titles = roadmap_titles(lines)
    numbers = sorted(set(titles) | {
        int(m.group(2)) for m in map(CHECKBOX_PHASE.match, lines) if m})
    nxt = next((n for n in numbers if n > phase_n), None)
    roadmap_updated = False
    for i, ln in enumerate(lines):
        m = CHECKBOX_PHASE.match(ln)
        if m and int(m.group(2)) == phase_n and m.group(1).lower() != "x":
            s, e = m.span(1)
            lines[i] = ln[:s] + "x" + ln[e:]
            roadmap_updated = True
            break
    if roadmap_updated:
        write_roadmap(root, lines, had_nl)
    carrier = find_carrier(root)
    dims = carrier_dimensions(carrier)
    issue_id = str(carrier.get("id"))
    actor = resolve_actor(root)
    reason = f"phase.complete {phase_n} via cairn-gsd"
    target_phase = str(nxt if nxt is not None else phase_n)
    target_status = "planned" if nxt is not None else "complete"
    state_updated = False
    if not (dims.get("phase") == target_phase
            and dims.get("phase_status") == target_status):
        if dims.get("phase") == str(phase_n):
            if set_dimension(root, issue_id, "phase_status", "complete",
                             actor, reason):
                state_updated = True
        if set_dimension(root, issue_id, "phase", target_phase, actor,
                         reason):
            state_updated = True
        if set_dimension(root, issue_id, "phase_status", target_status,
                         actor, reason):
            state_updated = True
    _, plans_executed = dir_counts(d)
    result = {"completed_phase": phase_n,
              "phase_name": titles.get(phase_n),
              "is_last_phase": nxt is None, "next_phase": nxt,
              "next_phase_name": titles.get(nxt),
              "plans_executed": plans_executed,
              "roadmap_updated": roadmap_updated,
              "state_updated": state_updated,
              "requirements_updated": False, "auto_pruned": [],
              "has_warnings": False, "warnings": [],
              "verification_stale_check_indeterminate": True}
    output_like_binary(result, raw, True)
    return EXIT_OK

def handle_roadmap_update_plan_progress(rest):
    """Contagens do disco (documento) + status do portador (FATO) —."""
    pos, _ = need_phase(rest)
    raw = "--raw" in rest
    phase_n = to_int(pos[0])
    root = find_project_root(Path.cwd())
    d = locate_phase_dir(root, phase_n)
    if d is None:
        die(f"fase {phase_n} não encontrada em .planning/phases",
            EXIT_CONTRACT)
    plan_count, summary_count = dir_counts(d)
    if plan_count == 0:
        output_like_binary({"updated": False, "reason": "no_plans",
                            "phase": phase_n}, raw, False)
        return EXIT_OK
    carrier = find_carrier(root)
    dims = carrier_dimensions(carrier)
    status = dims.get("phase_status")
    if status is None:
        die_missing_dim("phase_status")
    done_ids = {f.name[:-len("-SUMMARY.md")] for f in d.iterdir()
                if SUMMARY_FILE.match(f.name)}
    updated = False
    text = roadmap_text(root)
    if text is not None:
        had_nl = text.endswith("\n")
        lines = text.split("\n")
        bounds = phase_section_bounds(lines, phase_n)
        if bounds is not None:
            for i in range(bounds[0], bounds[1]):
                m = PLAN_CHECKBOX.match(lines[i])
                if m and m.group(2) in done_ids \
                        and m.group(1).lower() != "x":
                    s, e = m.span(1)
                    lines[i] = lines[i][:s] + "x" + lines[i][e:]
                    updated = True
            if updated:
                write_roadmap(root, lines, had_nl)
    result = {"updated": updated, "phase": phase_n,
              "plan_count": plan_count, "summary_count": summary_count,
              "complete": summary_count == plan_count, "status": status,
              "verification_stale_check_indeterminate": True}
    output_like_binary(result, raw, f"{summary_count}/{plan_count} {status}")
    return EXIT_OK

def handle_roadmap_annotate_dependencies(rest):
    """Anota o checklist de planos da fase com headers de wave (documento);."""
    pos, _ = need_phase(rest)
    raw = "--raw" in rest
    phase_n = to_int(pos[0])
    root = find_project_root(Path.cwd())
    text = roadmap_text(root)
    if text is None:
        output_like_binary({"updated": False, "reason": "roadmap_missing",
                            "phase": phase_n}, raw, False)
        return EXIT_OK
    d = locate_phase_dir(root, phase_n)
    if d is None:
        output_like_binary({"updated": False, "reason": "phase_dir_missing",
                            "phase": phase_n}, raw, False)
        return EXIT_OK
    waves, truth_count = {}, {}
    for f in sorted(d.iterdir()):
        if not PLAN_FILE.match(f.name):
            continue
        try:
            body = f.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = parse_frontmatter(body)
        plan_id = f.name[:-len("-PLAN.md")]
        w = str(fm.get("wave", "")).strip()
        waves.setdefault(w if w.isdigit() else "1", []).append(plan_id)
        for t in fm_block_list(body, "truths"):
            truth_count[t] = truth_count.get(t, 0) + 1
    if not waves:
        output_like_binary({"updated": False, "reason": "no_plans",
                            "phase": phase_n}, raw, False)
        return EXIT_OK
    constraints = sorted(t for t, c in truth_count.items() if c >= 2)
    had_nl = text.endswith("\n")
    lines = text.split("\n")
    bounds = phase_section_bounds(lines, phase_n)
    if bounds is None:
        output_like_binary({"updated": False, "reason": "no_phase_section",
                            "phase": phase_n}, raw, False)
        return EXIT_OK
    start, end, _ = bounds
    section_lines = lines[start:end]
    if any(re.match(r"^\*\*Wave \d+\*\*", ln) for ln in section_lines):
        result = {"updated": False, "reason": "already_annotated",
                  "phase": phase_n, "waves": waves,
                  "cross_cutting_constraints": constraints}
        output_like_binary(result, raw, False)
        return EXIT_OK
    wave_of = {pid: w for w, ids in waves.items() for pid in ids}
    out, prev_wave = [], None
    for ln in section_lines:
        m = PLAN_CHECKBOX.match(ln)
        if m:
            w = wave_of.get(m.group(2))
            if w is not None and w != prev_wave:
                header = f"**Wave {w}**"
                if prev_wave is not None:
                    header += f" *(blocked on Wave {prev_wave} completion)*"
                out.append(header)
                prev_wave = w
        out.append(ln)
    if prev_wave is None:
        output_like_binary({"updated": False, "reason": "no_plan_checklist",
                            "phase": phase_n}, raw, False)
        return EXIT_OK
    lines[start:end] = out
    write_roadmap(root, lines, had_nl)
    result = {"updated": True, "phase": phase_n, "waves": waves,
              "cross_cutting_constraints": constraints}
    output_like_binary(result, raw, True)
    return EXIT_OK

def handle_phase_list_artifacts(rest):
    """Verbo FANTASMA (descoberta da 31): não existe na tag — responde o."""
    die("Unknown phase subcommand. Available: uat-passed — "
        "phase.list-artifacts é verbo fantasma da tag (contrato da fase 31)",
        EXIT_CONTRACT)

def read_text_arg(pos, flags, text_flag, file_flag):
    """(texto, erro) — posicional/flag direta, ou leitura de arquivo; falha."""
    text = flags.get(text_flag) or (pos[0] if pos else None)
    path = flags.get(file_flag)
    if text is None and path:
        try:
            text = Path(path).read_text(encoding="utf-8").strip()
        except OSError as e:
            return None, f"não consegui ler {path}: {e}"
    return text, None

def handle_state_add_blocker(rest):
    """Blocker vira FATO de coleção: bead próprio com o label projetado."""
    pos, flags = parse_verb_args(rest, value_flags=("--text", "--text-file"))
    raw = "--raw" in rest
    text, err = read_text_arg(pos, flags, "--text", "--text-file")
    if err:
        output_like_binary({"added": False, "reason": err}, raw, False)
        return EXIT_OK
    if not text:
        output_like_binary({"error": "text required"}, raw, False)
        return EXIT_OK
    root = find_project_root(Path.cwd())
    run_bd(["create", text, "-t", "chore", "-l", BLOCKER_LABEL,
            "--actor", resolve_actor(root), "--silent"], root)
    output_like_binary({"added": True, "blocker": text}, raw, True)
    return EXIT_OK

def handle_state_add_decision(rest):
    """Decision vira FATO de coleção (label gsd-decision); o texto segue a."""
    _, flags = parse_verb_args(rest, value_flags=(
        "--phase", "--summary", "--summary-file",
        "--rationale", "--rationale-file"))
    raw = "--raw" in rest
    summary, err = read_text_arg([], flags, "--summary", "--summary-file")
    if err:
        output_like_binary({"added": False, "reason": err}, raw, False)
        return EXIT_OK
    if not summary:
        output_like_binary({"error": "summary required"}, raw, False)
        return EXIT_OK
    rationale, err = read_text_arg([], flags, "--rationale",
                                   "--rationale-file")
    if err:
        output_like_binary({"added": False, "reason": err}, raw, False)
        return EXIT_OK
    phase = flags.get("--phase") or "?"
    decision = f"[Phase {phase}]: {summary}"
    if rationale:
        decision += f" — {rationale}"
    root = find_project_root(Path.cwd())
    run_bd(["create", decision, "-t", "chore", "-l", DECISION_LABEL,
            "--actor", resolve_actor(root), "--silent"], root)
    output_like_binary({"added": True, "decision": decision}, raw, True)
    return EXIT_OK

def handle_state_record_metric(rest):
    """O caso canônico current_phase 18 (CORE-03): a atribuição de fase e."""
    _, flags = parse_verb_args(rest, value_flags=(
        "--phase", "--plan", "--duration", "--tasks", "--files"))
    raw = "--raw" in rest
    duration = flags.get("--duration")
    if not duration:
        output_like_binary({"error": "duration required"}, raw, False)
        return EXIT_OK
    root = find_project_root(Path.cwd())
    carrier = find_carrier(root)
    dims = carrier_dimensions(carrier)
    if "phase" not in dims:
        die_missing_dim("phase")
    phase_fact = int(dims["phase"])
    plan_fact = dims.get("plan") or flags.get("--plan") or "-"
    issue_id = str(carrier.get("id"))
    meta = carrier_metadata(root, issue_id)
    gsd = gsd_meta_slot(meta)
    metrics = gsd.get("metrics")
    if not isinstance(metrics, list):
        metrics = []
    metrics.append({"phase": phase_fact, "plan": plan_fact,
                    "duration": duration,
                    "tasks": flags.get("--tasks") or "-",
                    "files": flags.get("--files") or "-"})
    gsd["metrics"] = metrics
    write_metadata(root, issue_id, meta)
    result = {"recorded": True, "phase": phase_fact, "plan": plan_fact,
              "duration": duration}
    output_like_binary(result, raw, True)
    return EXIT_OK

# misc de planning-docs (partição do plano 34-01) — DOCUMENTOS, nunca fato
QUICK_TASK_LABEL = "gsd-quick-task"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

def fm_block_list(text, key):
    """Itens '- x' sob a chave indentada `key:` do frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    out, collecting = [], False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if re.match(rf"^\s*{re.escape(key)}:\s*$", line):
            collecting = True
            continue
        if collecting:
            m = re.match(r"^\s+-\s+(.*)$", line)
            if m:
                out.append(m.group(1).strip().strip('"'))
            elif line.strip() and not line.startswith("    "):
                collecting = False
    return out

def emit_picked(result, rest, raw_value=_UNDEFINED):
    """--pick (semântica medida) por cima do envelope; senão o JSON/raw."""
    if "--pick" in rest:
        i = rest.index("--pick")
        pick = rest[i + 1] if i + 1 < len(rest) else None
        if pick:
            emit(js_string(result[pick]) if pick in result else "undefined")
            return EXIT_OK
    output_like_binary(result, "--raw" in rest, raw_value)
    return EXIT_OK

def handle_summary_extract(rest):
    """Frontmatter estruturado de um SUMMARY (documento)."""
    pos, flags = parse_verb_args(rest, value_flags=("--fields", "--pick"))
    if not pos:
        die("summary-path required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    p = root / pos[0] if not os.path.isabs(pos[0]) else Path(pos[0])
    if not p.is_file():
        output_like_binary({"error": "File not found", "path": pos[0]},
                           "--raw" in rest, False)
        return EXIT_OK
    text = p.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    one_liner = fm.get("one-liner") or fm.get("one_liner")
    if not one_liner:
        m = re.search(r"^\*\*(.+?)\*\*", text.split("---", 2)[-1],
                      re.MULTILINE)
        one_liner = m.group(1).strip() if m else None
    decisions = []
    for item in fm_block_list(text, "decisions"):
        parts = item.split(" — ", 1)
        decisions.append({"summary": parts[0].strip(),
                          "rationale": parts[1].strip()
                          if len(parts) > 1 else None})
    reqs = fm.get("requirements-completed") \
        or fm.get("requirements_completed")
    result = {
        "path": pos[0], "one_liner": one_liner,
        "key_files": fm_block_list(text, "created")
        + fm_block_list(text, "modified"),
        "tech_added": fm_block_list(text, "added"),
        "patterns": fm_block_list(text, "patterns"),
        "decisions": decisions,
        "requirements_completed": fm_list(reqs) if reqs else [],
    }
    fields = flags.get("--fields")
    if fields:
        keep = {f.strip() for f in fields.split(",") if f.strip()}
        result = {k: v for k, v in result.items()
                  if k in keep or k == "path"}
    return emit_picked(result, rest)

def handle_todo_match_phase(rest):
    """Todos pendentes de .planning/todos casados contra a fase (documento)."""
    pos, _ = need_phase(rest)
    root = find_project_root(Path.cwd())
    todos = root / ".planning" / "todos"
    matches, total = [], 0
    if todos.is_dir():
        for f in sorted(todos.iterdir()):
            if f.suffix != ".md":
                continue
            total += 1
            fm = parse_frontmatter(f.read_text(encoding="utf-8"))
            if str(fm.get("phase", "")).strip() == str(pos[0]):
                matches.append(f.name)
    result = {"phase": pos[0], "matches": matches, "todo_count": total}
    output_like_binary(result, "--raw" in rest)
    return EXIT_OK

def handle_requirements_mark_complete(rest):
    """Flip do checkbox da linha alvo e SÓ dela; a tabela de traceability
    não é editada (divergência declarada — bookkeep é o dono)."""
    pos, _ = parse_verb_args(rest)
    raw = "--raw" in rest
    ids = []
    for tok in pos:
        ids += [x.strip() for x in tok.split(",") if x.strip()]
    if not ids:
        die("requirement IDs required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    p = root / ".planning" / "REQUIREMENTS.md"
    if not p.is_file():
        output_like_binary({"updated": False,
                            "reason": "REQUIREMENTS.md not found"},
                           raw, False)
        return EXIT_OK
    text = p.read_text(encoding="utf-8")
    had_nl = text.endswith("\n")
    lines = text.split("\n")
    marked, already, not_found, table_unmatched = [], [], [], []
    table_ids = {m.group(1) for m in
                 (re.match(r"^\|\s*([A-Za-z][A-Za-z0-9]*-\d+)\s*\|", ln)
                  for ln in lines) if m}
    for rid in ids:
        hit = False
        for i, ln in enumerate(lines):
            m = re.match(rf"^(\s*-\s*\[)([ xX])(\]\s.*\b{re.escape(rid)}\b)",
                         ln)
            if m:
                hit = True
                if m.group(2).lower() == "x":
                    already.append(rid)
                else:
                    lines[i] = m.group(1) + "x" + m.group(3) \
                        + ln[m.end(3):]
                    marked.append(rid)
                break
        if not hit:
            not_found.append(rid)
        if rid not in table_ids:
            table_unmatched.append(rid)
    if marked:
        p.write_text("\n".join(lines) + ("\n" if had_nl else ""),
                     encoding="utf-8")
    result = {"updated": bool(marked), "ids": ids,
              "marked_complete": marked, "already_complete": already,
              "not_found": not_found, "table_unmatched": table_unmatched,
              "total": len(ids), "write_set": ids,
              "write_set_complete": not not_found}
    output_like_binary(result, raw, bool(marked))
    return EXIT_OK

def handle_requirements_revert_phase(rest):
    """Inverso exato de mark-complete: `[x]` volta a `[ ]` na linha do ID, e
    SÓ nela; a tabela de traceability não é editada (mesma divergência
    declarada — bookkeep é o dono dela).

    Chamado por gsd-core/references/execute-phase-requirement-revert.md:5,
    quando o verify acha gaps depois de o execute já ter marcado os requisitos
    como Complete. A chamada existia desde a vendorização e nunca resolveu: o
    `>/dev/null 2>&1 || true` do sítio apagava o exit 2, e um requisito
    marcado cedo demais ficava marcado. Medido em 2026-08-12 (fase 38, M2).

    A forma do envelope espelha mark-complete porque é o par dela — o shape
    do binário real não foi medido para este verbo (o clone pinado não expõe
    a fonte), e a divergência está DECLARADA em
    tests/fixtures/gsd-goldens/divergences.json em vez de inventada em
    silêncio.
    """
    pos, _ = parse_verb_args(rest)
    raw = "--raw" in rest
    ids = []
    for tok in pos:
        ids += [x.strip() for x in tok.split(",") if x.strip()]
    if not ids:
        die("requirement IDs required", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    p = root / ".planning" / "REQUIREMENTS.md"
    if not p.is_file():
        output_like_binary({"updated": False,
                            "reason": "REQUIREMENTS.md not found"},
                           raw, False)
        return EXIT_OK
    text = p.read_text(encoding="utf-8")
    had_nl = text.endswith("\n")
    lines = text.split("\n")
    reverted, already, not_found = [], [], []
    for rid in ids:
        hit = False
        for i, ln in enumerate(lines):
            m = re.match(rf"^(\s*-\s*\[)([ xX])(\]\s.*\b{re.escape(rid)}\b)",
                         ln)
            if m:
                hit = True
                if m.group(2) == " ":
                    already.append(rid)
                else:
                    lines[i] = m.group(1) + " " + m.group(3) \
                        + ln[m.end(3):]
                    reverted.append(rid)
                break
        if not hit:
            not_found.append(rid)
    if reverted:
        p.write_text("\n".join(lines) + ("\n" if had_nl else ""),
                     encoding="utf-8")
    result = {"updated": bool(reverted), "ids": ids,
              "reverted": reverted, "already_pending": already,
              "not_found": not_found, "total": len(ids)}
    output_like_binary(result, raw, bool(reverted))
    return EXIT_OK

def handle_quick_tasks_append(rest):
    """Quick task vira bead com label gsd-quick-task (research §4: quick
    tasks já são issues bd na casa) — divergência declarada."""
    pos, flags = parse_verb_args(rest, value_flags=("--task",))
    raw = "--raw" in rest
    task = flags.get("--task") or (" ".join(pos) if pos else None)
    if not task:
        die("--task required", EXIT_USAGE)
    root = find_project_root(Path.cwd())
    run_bd(["create", task, "-t", "task", "-l", QUICK_TASK_LABEL,
            "--actor", resolve_actor(root), "--silent"], root)
    result = {"ok": True, "row": task, "variant": "bd-issue"}
    output_like_binary(result, raw, True)
    return EXIT_OK

def handle_history_digest(rest):
    """Digest dos SUMMARYs (fases vivas + milestones arquivados, antigos
    primeiro) — documento puro."""
    raw = "--raw" in rest
    root = find_project_root(Path.cwd())
    phases, decisions, tech = [], [], []
    dirs = phase_dirs(root, include_archived=True)
    archived = [d for d in dirs if "milestones" in d.parts]
    live = [d for d in dirs if "milestones" not in d.parts]
    for d in archived + live:
        for f in sorted(d.iterdir()):
            if not SUMMARY_FILE.match(f.name):
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = parse_frontmatter(text)
            name = fm.get("phase") or d.name
            phases.append({"name": name,
                           "provides": fm_block_list(text, "provides"),
                           "affects": fm_block_list(text, "affects"),
                           "patterns": fm_block_list(text, "patterns")})
            for item in fm_block_list(text, "decisions"):
                decisions.append({"phase": name, "decision": item})
            for t in fm_block_list(text, "added"):
                if t not in tech:
                    tech.append(t)
    result = {"phases": phases, "decisions": decisions,
              "tech_stack": tech}
    output_like_binary(result, raw)
    return EXIT_OK

def handle_research_plan(rest):
    """Plano de research: provider único websearch (host claude) + chave
    sha256 da question — o contrato do research-store preservado."""
    import hashlib
    _, flags = parse_verb_args(rest, value_flags=("--input",))
    raw = "--raw" in rest
    inp = flags.get("--input")
    if not inp:
        die("--input required", EXIT_CONTRACT)
    try:
        data = json.loads(Path(inp).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        die(f"--input ilegível ou inválido: {e}", EXIT_CONTRACT)
    questions = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(questions, list):
        die("--input precisa ser objeto com questions array", EXIT_CONTRACT)
    items = [{"question": str(q), "provider": "websearch",
              "key": hashlib.sha256(str(q).encode()).hexdigest()}
             for q in questions]
    output_like_binary({"items": items}, raw)
    return EXIT_OK

def handle_research_store(rest):
    """Cache de research por chave sha256 sob .planning/research/.store;
    sem TTL (stale sempre false — divergência declarada)."""
    pos, flags = parse_verb_args(rest, value_flags=(
        "--content", "--source", "--provider", "--confidence", "--kind"))
    raw = "--raw" in rest
    sub = pos[0] if pos else None
    key = pos[1] if len(pos) > 1 else None
    if sub not in ("get", "put"):
        die(f"Unknown research-store subcommand: {sub}", EXIT_CONTRACT)
    if not key or not SHA256_RE.match(key):
        die("chave sha256 de 64 chars requerida (vem de research-plan)",
            EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    store = root / ".planning" / "research" / ".store"
    entry_path = store / f"{key}.json"
    if sub == "get":
        if not entry_path.is_file():
            output_like_binary({"hit": False, "stale": False,
                                "entry": None}, raw, False)
            return EXIT_OK
        try:
            entry = json.loads(entry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            die(f"entry ilegível: {entry_path}", EXIT_CONTRACT)
        output_like_binary({"hit": True, "stale": False, "entry": entry},
                           raw, True)
        return EXIT_OK
    missing = [f for f in ("--content", "--source", "--provider",
                           "--confidence", "--kind")
               if not flags.get(f)]
    if missing:
        die(f"put requer {', '.join(missing)}", EXIT_CONTRACT)
    entry = {"content": flags["--content"], "source": flags["--source"],
             "provider": flags["--provider"],
             "confidence": flags["--confidence"], "kind": flags["--kind"]}
    try:
        store.mkdir(parents=True, exist_ok=True)
        entry_path.write_text(json.dumps(entry, indent=2,
                                         ensure_ascii=False) + "\n",
                              encoding="utf-8")
    except OSError as e:
        die(f"falha gravando {entry_path}: {e}", EXIT_CONTRACT)
    output_like_binary({"hit": True, "stale": False, "entry": entry},
                       raw, True)
    return EXIT_OK

HANDLERS = {
    "find-phase": handle_find_phase,
    "history-digest": handle_history_digest,
    "quick-tasks-append": handle_quick_tasks_append,
    "requirements.mark-complete": handle_requirements_mark_complete,
    "requirements.revert-phase": handle_requirements_revert_phase,
    "research-plan": handle_research_plan,
    "research-store": handle_research_store,
    "summary-extract": handle_summary_extract,
    "todo.match-phase": handle_todo_match_phase,
    "phase": handle_phase,
    "phase-plan-index": handle_phase_plan_index,
    "phase.complete": handle_phase_complete,
    "phase.list-artifacts": handle_phase_list_artifacts,
    "phase.list-plans": handle_phase_list_plans,
    "phase.mvp-mode": handle_phase_mvp_mode,
    "phases.list": handle_phases_list,
    "roadmap.analyze": handle_roadmap_analyze,
    "roadmap.annotate-dependencies": handle_roadmap_annotate_dependencies,
    "roadmap.get-phase": handle_roadmap_get_phase,
    "roadmap.update-plan-progress": handle_roadmap_update_plan_progress,
    "state.add-blocker": handle_state_add_blocker,
    "state.add-decision": handle_state_add_decision,
    "state.advance-plan": handle_state_advance_plan,
    "state.begin-phase": handle_state_begin_phase,
    "state.load": handle_state_load,
    "state.planned-phase": handle_state_planned_phase,
    "state.record-metric": handle_state_record_metric,
    "state.record-session": handle_state_record_session,
    "state.update": handle_state_update,
    "state.update-progress": handle_state_update_progress,
}

# main — recebe o verbo canônico já resolvido pelo dispatcher
def family_of(verb):
    """Família do verbo, do índice de contratos — só no caminho de erro."""
    try:
        agg = json.loads(
            (CONTRACTS_DIR / "contracts.json").read_text(encoding="utf-8"))
        meta = (agg.get("verbs") or {}).get(verb) or {}
        return meta.get("family") or "?"
    except (OSError, json.JSONDecodeError, ValueError):
        return "?"

def main():
    argv = sys.argv[1:]
    if not argv:
        die("usage: cairn-gsd-state.py <verbo> [argv]", EXIT_USAGE)
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
