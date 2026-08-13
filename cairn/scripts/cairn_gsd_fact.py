"""cairn_gsd_fact.py — o substrato de FATO do binário, em UMA fonte.

Resolução defensiva de fato para o irmão de checagem: git read-only,
subprocess limitado, classificação de drift, flags de predicado, o frame do
checkpoint de UAT, as tabelas de roteamento de verificação, a varredura de
artefatos abertos e o conflito de gate negativo file-wide — portes com
proveniência src/*.cts da tag v1.10.0, por função.

Existe separado de cairn_gsd_parse.py porque parse LÊ um documento e isto
aqui INTERROGA o repositório: processo, filesystem e git. Enquanto os dois
viveram dentro de cairn_gsd_render.py, o arquivo fechou em 1536 linhas e o
nome "render" cobria envelope, parsing, git, predicados e auditoria ao mesmo
tempo (CairnGo-zzgn; partição em CairnGo-2fyg, saída (a) da fase 38).

Por que módulo e não de volta ao cairn-gsd-check.py, que é seu único
consumidor: medido, o irmão fecharia em ~2295 linhas, acima do teto D-01 que
a própria issue defende. O substrato fica em módulo, com o nome do que ele
contém, e o teto passa a medir os dois.

Semântica de VEREDITO (exits, shapes, rotas) continua no irmão. Nenhum
veredito aqui.

Não é CLI: sem wrapper .sh.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cairn_gsd_parse import (TASK_BLOCK_RE, collect_heading_section,  # noqa: E402,E501
                             parse_frontmatter_lines, read_text)


# --- frame do checkpoint de UAT (src/uat.cts L412-L594) ---------------------
# Tabela REDUZIDA às línguas da casa (english default + portuguese);
# demais caem em english — distância declarada em divergences.json.
CHECKPOINT_FRAMES = {
    "english": ("CHECKPOINT: Verification Required",
                "Type `pass` or describe what's wrong."),
    "portuguese": ("PONTO DE VERIFICAÇÃO: Verificação necessária",
                   "Digite `pass` ou descreva o que está errado."),
}
CHECKPOINT_ALIASES = {
    "english": "english", "en": "english", "en-us": "english",
    "en-gb": "english",
    "portuguese": "portuguese", "pt": "portuguese", "pt-br": "portuguese",
    "português": "portuguese", "portugues": "portuguese",
    "brazilian portuguese": "portuguese",
}


def build_checkpoint(number, name, expected, response_language):
    """buildCheckpoint: caixa de 64 colunas + teste corrente + instrução."""
    key = CHECKPOINT_ALIASES.get(
        (response_language or "").strip().lower(), "english") \
        if response_language else "english"
    banner, instruction = CHECKPOINT_FRAMES.get(key,
                                                CHECKPOINT_FRAMES["english"])
    content = f"  {banner}"
    pad = 62 - len(content)
    boxed = content + " " * pad if pad > 0 else content
    return "\n".join([
        "╔" + "═" * 62 + "╗",
        f"║{boxed}║",
        "╚" + "═" * 62 + "╝",
        "",
        f"**Test {number}: {name}**",
        "",
        expected,
        "",
        "─" * 62,
        instruction,
        "─" * 62,
    ])


# --- resolução de FATO defensiva (git read-only, subprocess limitado,
# dados de classificação) — movida do irmão check pelo teto D-01 -----------
SUMMARY_FILE_RE = re.compile(r"^\d+-(\d+)-SUMMARY\.md$")


def _run_git(argv, cwd):
    """Subprocess defensivo (molde run_git de cairn-gsd.py L818-832):
    falha vira None, nunca traceback."""
    try:
        proc = subprocess.run(["git"] + argv, capture_output=True,
                              text=True, cwd=str(cwd), timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _match_requested(git_path, files):
    """Path do git (repo-root-relative) → arquivo pedido, por igualdade ou
    sufixo com fronteira '/' (matchRequestedFile da tag)."""
    for f in files:
        if git_path == f or git_path.endswith("/" + f):
            return f
    return None


def _clean_commit_times(phase_dir, files):
    """Molde defaultPhaseCleanCommitTimesMs (src/verification.cts, #2348):
    epoch do commit por arquivo committed E limpo; diff inconclusivo →
    mapa vazio (fail-safe: tudo cai pra mtime)."""
    if not files:
        return {}
    out = _run_git(["log", "--first-parent", "--format=%ct",
                    "--name-only", "--"] + files, phase_dir)
    if not out:
        return {}
    times = {}
    current = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            current = int(line)
            continue
        if current is None:
            continue
        hit = _match_requested(line, files)
        if hit is not None and hit not in times:
            times[hit] = current
    if not times:
        return times
    diff = _run_git(["diff", "--name-only", "HEAD", "--"] + files, phase_dir)
    if diff is None:
        return {}
    for line in diff.splitlines():
        line = line.strip()
        if not line:
            continue
        hit = _match_requested(line, files)
        if hit is not None:
            times.pop(hit, None)
    return times


def _find_stale_summary(pdir):
    """(determined, stale) — molde findStaleVerificationSummary (#2348,
    #3057 B3): falha do check é (False, False), NUNCA 'not stale' fingido;
    tempo efetivo = commit time quando limpo, senão mtime."""
    try:
        names = sorted(p.name for p in pdir.iterdir() if p.is_file())
        vfiles = [n for n in names if n.endswith("-VERIFICATION.md")]
        if not vfiles:
            return True, False
        vfile = vfiles[0]
        summaries = [n for n in names if SUMMARY_FILE_RE.match(n)]
        if not summaries:
            return True, False
        clean = _clean_commit_times(pdir, [vfile] + summaries)

        def eff(name):
            if name in clean:
                return float(clean[name])
            return (pdir / name).stat().st_mtime

        vtime = eff(vfile)
        for s in summaries:
            if eff(s) > vtime:
                return True, True
        return True, False
    except OSError:
        return False, False


DRIFT_BARREL_RE = re.compile(
    r"^(packages|apps)/[^/]+/src/index\.(ts|tsx|js|mjs|cjs)$")
DRIFT_MIGRATION_RES = tuple(re.compile(p) for p in (
    r"^supabase/migrations/.+\.sql$", r"^prisma/migrations/.+",
    r"^drizzle/meta/.+", r"^drizzle/migrations/.+",
    r"^src/migrations/.+\.(ts|js|sql)$", r"^db/migrations/.+\.(sql|ts|js)$",
    r"^migrations/.+\.(sql|ts|js)$"))
DRIFT_ROUTE_RES = tuple(re.compile(p) for p in (
    r"^(apps|packages)/[^/]+/src/routes/.+\.(ts|tsx|js|jsx|mjs|cjs)$",
    r"^src/routes/.+\.(ts|tsx|js|jsx|mjs|cjs)$",
    r"^src/api/.+\.(ts|tsx|js|jsx|mjs|cjs)$",
    r"^(apps|packages)/[^/]+/src/api/.+\.(ts|tsx|js|jsx|mjs|cjs)$"))
DRIFT_PRIORITY = {"new_dir": 0, "barrel": 1, "route": 2, "migration": 3}


def _classify_drift_file(f):
    if any(r.match(f) for r in DRIFT_MIGRATION_RES):
        return "migration"
    if any(r.match(f) for r in DRIFT_ROUTE_RES):
        return "route"
    if DRIFT_BARREL_RE.match(f):
        return "barrel"
    return None


def _is_path_mapped(f, structure_md):
    parts = f.split("/")
    for i in range(len(parts) - 1, 0, -1):
        if "/".join(parts[:i]) in structure_md:
            return True
    return bool(parts) and (parts[0] + "/" in structure_md
                            or "`" + parts[0] + "`" in structure_md)


def _parse_predicate_flags(rest):
    """parsePredicateFlags (check-command-router.cts L1014-L1029)."""
    out, i = {}, 0
    while i < len(rest):
        a = rest[i]
        if isinstance(a, str) and a.startswith("--"):
            key = a[2:]
            nxt = rest[i + 1] if i + 1 < len(rest) else None
            if key and isinstance(nxt, str) and not nxt.startswith("--"):
                out[key] = nxt
                i += 2
                continue
        i += 1
    return out


def _trim_2000(s):
    return s[:2000] if len(s) > 2000 else s


def _run_bounded_shell(command, cwd, timeout_ms):
    """buildPredicateDeps.runBoundedShell: sh -c em subprocess limitado."""
    try:
        proc = subprocess.run(["sh", "-c", command], capture_output=True,
                              text=True, cwd=str(cwd),
                              timeout=timeout_ms / 1000.0)
    except subprocess.TimeoutExpired:
        return {"exitCode": None, "stdout": "", "stderr": "",
                "signal": None, "timedOut": True}
    except OSError as e:
        return {"exitCode": None, "stdout": "", "stderr": str(e),
                "signal": None, "timedOut": False}
    if proc.returncode < 0:
        try:
            sig = __import__("signal").Signals(-proc.returncode).name
        except (ValueError, AttributeError):
            sig = str(-proc.returncode)
        return {"exitCode": None, "stdout": proc.stdout,
                "stderr": proc.stderr, "signal": sig, "timedOut": False}
    return {"exitCode": proc.returncode, "stdout": proc.stdout,
            "stderr": proc.stderr, "signal": None, "timedOut": False}


def _find_phase_artifact(phase_dir, suffix):
    """buildPredicateDeps.findPhaseArtifact: basename-only, sem traversal."""
    pdir = Path(phase_dir)
    if not pdir.exists():
        return None
    if (suffix in (".", "..") or "\0" in suffix
            or os.path.basename(suffix) != suffix or "\\" in suffix):
        return None
    direct = pdir / suffix
    if direct.is_file():
        return str(direct)
    planning = pdir / ".planning" / suffix
    if planning.is_file():
        return str(planning)
    try:
        for f in sorted(os.listdir(pdir)):
            if f.endswith("-" + suffix) or f == suffix:
                cand = pdir / f
                if cand.is_file():
                    return str(cand)
    except OSError:
        pass
    return None


# VERIFICATION_ROUTING_TABLE transcrita de src/verification.cts L81-L121 da
# tag v1.10.0 (cache .cairn/cache/gsd-core-v1.10.0) — dado com proveniência,
# não lógica: (status, next_action, next_command bare).
VERIFICATION_ROUTING_TABLE = {
    "passed": ("passed", "Verification passed — continue.", ""),
    "gaps_found": ("gaps_found",
                   "Gaps found. Plan the fixes, then re-run execute-phase "
                   "before shipping.", ""),
    "human_needed": ("human_needed",
                     "Human verification required. Complete the manual tests "
                     "in the phase's *-UAT.md, then re-run the verify step "
                     "until status is passed.", "verify-work"),
    "stale": ("stale",
              "Verification is stale. Re-run verify-work before transition.",
              ""),
    # sentinelas internas — nunca escritas pelo verifier
    "missing": ("missing",
                "No verification report found — the verify step never "
                "completed. Re-run execute-phase.", "execute-phase"),
    "unknown": ("unknown", "", "execute-phase"),
}


# REVIEWER_LANES transcrito de src/review-lane-descriptor.cts L229-L604 —
# os campos que os subcommands do universo consomem: (slug, flags,
# reviewsSection). Merge com capabilities instaladas e invocação de CLIs
# não se aplicam à casa (divergência declarada em divergences.json).
REVIEWER_LANES = (
    ("gemini", ("--gemini",), "Gemini"),
    ("claude", ("--claude",), "Claude"),
    ("codex", ("--codex",), "Codex"),
    ("coderabbit", ("--coderabbit",), "CodeRabbit"),
    ("opencode", ("--opencode",), "OpenCode"),
    ("qwen", ("--qwen",), "Qwen"),
    ("cursor", ("--cursor",), "Cursor"),
    ("antigravity", ("--antigravity", "--agy"), "Antigravity"),
    ("ollama", ("--ollama",), "Ollama"),
    ("lm_studio", ("--lm-studio",), "LM Studio"),
    ("llama_cpp", ("--llama-cpp",), "llama.cpp"),
    ("kimi-code", ("--kimi-code",), "Kimi Code"),
)


# --- varredura de artefatos abertos (src/audit.cts L157-L867) ---------------
def _fm_of(path):
    text = read_text(path)
    if text is None:
        return None, None
    fm, _span = parse_frontmatter_lines(text)
    return fm, text


def _scan_dir_md(dirpath):
    try:
        return sorted(p for p in Path(dirpath).iterdir()
                      if p.is_file() and p.name.endswith(".md"))
    except OSError:
        return None


def scan_debug_sessions(plan_dir):
    d = Path(plan_dir) / "debug"
    if not d.exists():
        return []
    files = _scan_dir_md(d)
    if files is None:
        return [{"scan_error": True, "slug": "", "status": "",
                 "updated": "", "hypothesis": ""}]
    out = []
    for p in files:
        fm, text = _fm_of(p)
        if fm is None:
            continue
        status = (fm.get("status") or "unknown").lower()
        if status in ("resolved", "complete"):
            continue
        hyp = ""
        section = collect_heading_section(
            text, re.compile(r"^current focus", re.I))
        if section:
            hyp = section.strip().split("\n")[0].strip()[:100]
        out.append({"slug": p.stem, "status": status,
                    "updated": fm.get("updated") or fm.get("date") or "",
                    "hypothesis": hyp})
    return out


def scan_quick_tasks(plan_dir):
    d = Path(plan_dir) / "quick"
    if not d.exists():
        return []
    try:
        dirs = sorted(x for x in d.iterdir() if x.is_dir())
    except OSError:
        return [{"scan_error": True, "slug": "", "date": "", "status": "",
                 "description": ""}]
    out = []
    for td in dirs:
        status = "missing"
        try:
            summaries = [f for f in td.iterdir() if f.is_file()
                         and (f.name == "SUMMARY.md"
                              or f.name.endswith("-SUMMARY.md"))]
        except OSError:
            summaries = []
        pref = next((f for f in summaries
                     if f.name == f"{td.name}-SUMMARY.md"),
                    next(iter(summaries), None))
        if pref is not None:
            fm, _t = _fm_of(pref)
            status = ("unreadable" if fm is None
                      else (fm.get("status") or "unknown").lower())
        if status == "complete":
            continue
        dm = re.match(r"^(\d{4}-?\d{2}-?\d{2})-(.+)$", td.name)
        out.append({"slug": dm.group(2) if dm else td.name,
                    "date": dm.group(1) if dm else "", "status": status,
                    "description": ""})
    return out


def scan_threads(plan_dir):
    d = Path(plan_dir) / "threads"
    if not d.exists():
        return []
    files = _scan_dir_md(d)
    if files is None:
        return [{"scan_error": True, "slug": "", "status": "",
                 "updated": "", "title": ""}]
    out = []
    for p in files:
        fm, text = _fm_of(p)
        if fm is None:
            continue
        status = (fm.get("status") or "").lower().strip()
        if not status:
            bm = re.search(r"##\s*Status:\s*(OPEN|IN PROGRESS|IN_PROGRESS)",
                           text, re.I)
            if bm:
                status = bm.group(1).lower().replace(" ", "_")
        if status not in ("open", "in_progress", "in progress"):
            continue
        title = ""
        hm = re.search(r"^#\s*Thread:\s*(.+)$", text, re.M)
        if hm:
            title = hm.group(1).strip()
        out.append({"slug": p.stem, "status": status,
                    "updated": fm.get("updated") or "", "title": title})
    return out


def scan_todos(plan_dir):
    d = Path(plan_dir) / "todos" / "pending"
    if not d.exists():
        return []
    files = _scan_dir_md(d)
    if files is None:
        return [{"scan_error": True, "filename": "", "priority": "",
                 "area": "", "summary": ""}]
    out = []
    for p in files[:5]:
        fm, text = _fm_of(p)
        if fm is None:
            continue
        first = next((ln.strip() for ln in text.splitlines()
                      if ln.strip() and not ln.startswith("---")
                      and ":" not in ln[:20]), "")
        out.append({"filename": p.name,
                    "priority": fm.get("priority") or "",
                    "area": fm.get("area") or "",
                    "summary": (fm.get("summary") or first)[:120]})
    if len(files) > 5:
        out.append({"_remainder_count": len(files) - 5, "filename": "",
                    "priority": "", "area": "", "summary": ""})
    return out


def scan_seeds(plan_dir):
    d = Path(plan_dir) / "seeds"
    if not d.exists():
        return []
    files = _scan_dir_md(d)
    if files is None:
        return [{"scan_error": True, "seed_id": "", "slug": "",
                 "status": "", "title": ""}]
    out = []
    for p in files:
        if not p.name.startswith("SEED-"):
            continue
        fm, text = _fm_of(p)
        if fm is None:
            continue
        status = (fm.get("status") or "dormant").lower()
        if status not in ("dormant", "open", "pending", "proposed"):
            continue
        title = ""
        hm = re.search(r"^#\s*(.+)$", text, re.M)
        if hm:
            title = hm.group(1).strip()
        out.append({"seed_id": p.stem, "slug": fm.get("slug") or "",
                    "status": status, "title": title})
    return out


def _scan_phase_files(plan_dir, needle):
    """(phase_token, file, fm, text) por arquivo *<needle>*.md das fases."""
    phases = Path(plan_dir) / "phases"
    if not phases.exists():
        return []
    out = []
    try:
        dirs = sorted(x for x in phases.iterdir() if x.is_dir())
    except OSError:
        return None
    for pd in dirs:
        pm = re.match(r"^(?:[A-Za-z0-9]+-)?0*(\d+)", pd.name)
        phase = pm.group(1) if pm else pd.name
        try:
            files = sorted(f for f in pd.iterdir() if f.is_file()
                           and needle in f.name and f.name.endswith(".md"))
        except OSError:
            continue
        for f in files:
            fm, text = _fm_of(f)
            if fm is None:
                continue
            out.append((phase, f, fm, text))
    return out


def scan_uat_gaps(plan_dir):
    rows = _scan_phase_files(plan_dir, "-UAT")
    if rows is None:
        return [{"scan_error": True, "phase": "", "file": "",
                 "status": "", "open_scenario_count": 0}]
    out = []
    for phase, f, fm, text in rows:
        status = (fm.get("status") or "unknown").lower()
        if status in ("complete", "all_pass", "passed"):
            continue
        if status == "unknown" \
                and (fm.get("result") or "").lower() == "all_pass":
            continue
        pending = len(re.findall(r"result:\s*(?:pending|\[pending\])",
                                 text, re.I))
        out.append({"phase": phase, "file": f.name, "status": status,
                    "open_scenario_count": pending})
    return out


def scan_verification_gaps(plan_dir):
    rows = _scan_phase_files(plan_dir, "-VERIFICATION")
    if rows is None:
        return [{"scan_error": True, "phase": "", "file": "", "status": ""}]
    out = []
    for phase, f, fm, _text in rows:
        status = (fm.get("status") or "unknown").lower()
        if status not in ("gaps_found", "human_needed"):
            continue
        out.append({"phase": phase, "file": f.name, "status": status})
    return out


def scan_context_questions(plan_dir):
    rows = _scan_phase_files(plan_dir, "-CONTEXT")
    if rows is None:
        return [{"scan_error": True, "phase": "", "file": "",
                 "question_count": 0, "questions": []}]
    out = []
    for phase, f, _fm, text in rows:
        questions = []
        section = collect_heading_section(
            text, re.compile(r"^open questions", re.I))
        if section:
            questions = [re.sub(r"^[-*]\s*", "", ln.strip())[:200]
                         for ln in section.splitlines()
                         if ln.strip() and ln.strip() not in ("-", "*")
                         and re.match(r"^[-*]\s+\S", ln.strip())]
        if not questions:
            continue
        out.append({"phase": phase, "file": f.name,
                    "question_count": len(questions),
                    "questions": questions})
    return out


def scan_deferred_items(plan_dir):
    phases = Path(plan_dir) / "phases"
    if not phases.exists():
        return []
    out = []
    try:
        dirs = sorted(x for x in phases.iterdir() if x.is_dir())
    except OSError:
        return [{"scan_error": True, "phase": "", "file": "", "text": ""}]
    for pd in dirs:
        f = pd / "deferred-items.md"
        text = read_text(f)
        if text is None or not text.strip():
            continue
        pm = re.match(r"^(?:[A-Za-z0-9]+-)?0*(\d+)", pd.name)
        out.append({"phase": pm.group(1) if pm else pd.name,
                    "file": f.name, "text": text.strip()[:200]})
    return out


AUDIT_SCANNERS = (
    ("debug_sessions", scan_debug_sessions),
    ("quick_tasks", scan_quick_tasks),
    ("threads", scan_threads),
    ("todos", scan_todos),
    ("seeds", scan_seeds),
    ("uat_gaps", scan_uat_gaps),
    ("verification_gaps", scan_verification_gaps),
    ("context_questions", scan_context_questions),
    ("deferred_items", scan_deferred_items),
)


def format_audit_report(result):
    """formatAuditReport (src/audit.cts L870+): relatório humano."""
    counts, items = result["counts"], result["items"]
    hr = "━" * 53
    lines = [hr, "  Milestone Close: Open Artifact Audit", hr]
    if not result["has_open_items"]:
        lines += ["", "  All artifact types clear. Safe to proceed.", "",
                  hr]
        return "\n".join(lines)

    def real(arr):
        return [i for i in arr if not i.get("scan_error")
                and not i.get("_remainder_count")]

    if counts["debug_sessions"]:
        lines += ["", f"🔴 Debug Sessions ({counts['debug_sessions']} open)"]
        for i in real(items["debug_sessions"]):
            hyp = f" — {i['hypothesis']}" if i.get("hypothesis") else ""
            lines.append(f"   • {i['slug']} [{i['status']}]{hyp}")
    if counts["uat_gaps"]:
        lines += ["", f"🔴 UAT Gaps ({counts['uat_gaps']} phases with "
                  "incomplete UAT)"]
        for i in real(items["uat_gaps"]):
            lines.append(f"   • Phase {i['phase']}: {i['file']} "
                         f"[{i['status']}] — {i['open_scenario_count']} "
                         "pending scenarios")
    if counts["verification_gaps"]:
        lines += ["", f"🔴 Verification Gaps "
                  f"({counts['verification_gaps']} unresolved)"]
        for i in real(items["verification_gaps"]):
            lines.append(f"   • Phase {i['phase']}: {i['file']} "
                         f"[{i['status']}]")
    if counts["quick_tasks"]:
        lines += ["", f"🟡 Quick Tasks ({counts['quick_tasks']} incomplete)"]
        for i in real(items["quick_tasks"]):
            d = f" ({i['date']})" if i.get("date") else ""
            lines.append(f"   • {i['slug']}{d} [{i['status']}]")
    if counts["todos"]:
        lines += ["", f"🟡 Todos ({counts['todos']} pending)"]
        for i in real(items["todos"]):
            lines.append(f"   • {i['filename']} [{i.get('priority') or '?'}]"
                         f" {i.get('summary') or ''}".rstrip())
    if counts["threads"]:
        lines += ["", f"🟡 Threads ({counts['threads']} open)"]
        for i in real(items["threads"]):
            lines.append(f"   • {i['slug']} [{i['status']}] {i['title']}")
    if counts["seeds"]:
        lines += ["", f"🟢 Seeds ({counts['seeds']} unimplemented)"]
        for i in real(items["seeds"]):
            lines.append(f"   • {i['seed_id']} [{i['status']}] {i['title']}")
    if counts["context_questions"]:
        lines += ["", f"🟢 Context Questions "
                  f"({counts['context_questions']} files)"]
        for i in real(items["context_questions"]):
            lines.append(f"   • Phase {i['phase']}: {i['file']} — "
                         f"{i['question_count']} open questions")
    if counts["deferred_items"]:
        lines += ["", f"🟢 Deferred Items ({counts['deferred_items']} "
                  "phases)"]
        for i in real(items["deferred_items"]):
            lines.append(f"   • Phase {i['phase']}: {i['file']}")
    lines += ["", hr]
    return "\n".join(lines)


# --- conflito de gate negativo file-wide (#968, src/verify.cts L383-L560) ---
def pattern_required_in(pat, req_text):
    """Port linear de patternRequiredIn (#968 FIX 1, ReDoS-safe)."""
    hay = (req_text or "")[:8000]
    if not pat:
        return False
    pat = re.sub(r"\$$", "", re.sub(r"^\^", "", pat))
    if not pat:
        return False
    if not re.search(r"[.*+?^${}()|\[\]\\]", pat):
        return pat in hay
    sent = " "
    work = re.sub(r"\\[sSwWdD][*+?]?", sent, pat)
    work = re.sub(r"\.[*+?]", sent, work)
    work = work.replace(".", sent)
    work = re.sub(r"\\(.)", r"\1", work)
    if re.search(r"[*+?^${}()|\[\]]", "".join(work.split(sent))):
        return pat in hay
    frags = [f for f in work.split(sent) if f]
    if not frags:
        return False
    pos = 0
    for f in frags:
        idx = hay.find(f, pos)
        if idx == -1:
            return False
        pos = idx + len(f)
    return True


GREP_ARG_RE = re.compile(
    r"grep((?:\s+-{1,2}[A-Za-z][A-Za-z-]*)+)\s+"
    r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"|>&;$()\[\]]+))")


def scan_file_wide_negative_gate_conflict(content):
    """#968 warn-only — port compacto de scanFileWideNegativeGateConflict
    (src/verify.cts L383-L560): ban file-wide de um task A insatisfazível
    quando um sibling B exige o padrão no mesmo arquivo."""
    warnings = []
    text = (content or "").replace("\r\n", "\n").replace("\r", "\n") \
        .replace("\\\n", " ")
    allow = {m.group(1) for m in re.finditer(
        r"<!--\s*planner-region-allow:\s*(.+?)\s*-->", text)}

    def norm_path(p):
        p = p.strip()
        return p[2:] if p.startswith("./") else p

    tasks = []
    for m in TASK_BLOCK_RE.finditer(text):
        body = m.group(2) or ""
        nm = re.search(r"<name>(.*?)</name>", body, re.S)
        fm2 = re.search(r"<files>(.*?)</files>", body, re.S)
        files = ([f for f in re.split(r"[,\s]+", fm2.group(1).strip())
                  if f] if fm2 else [])
        gate, req = [], []
        for tag in ("verify", "automated", "acceptance_criteria"):
            gate += re.findall(rf"<{tag}>(.*?)</{tag}>", body, re.S)
        for tag in ("action", "acceptance_criteria"):
            req += re.findall(rf"<{tag}>(.*?)</{tag}>", body, re.S)
        tasks.append({"name": nm.group(1).strip() if nm else "unnamed",
                      "files": files,
                      "gate": re.sub(r"<[^>]+>", " ", "\n".join(gate)),
                      "req": "\n".join(req)})
    if len(tasks) < 2:
        return warnings
    known = {norm_path(f) for t in tasks for f in t["files"]}

    def opts_count(o):
        return (re.search(r"(?:^|\s)-[A-Za-z]*c[A-Za-z]*(?=\s|$)", o)
                or re.search(r"--count\b", o))

    def opts_invert(o):
        return (re.search(r"(?:^|\s)-[A-Za-z]*v[A-Za-z]*(?=\s|$)", o)
                or re.search(r"--invert-match\b", o))

    def plausible(s):
        return re.search(r"[A-Za-z0-9_]", s) and \
            not re.fullmatch(r"[-=!<>0-9]+", s)

    def zero_cmp(s):
        return (re.search(r"\s==?\s*0\b", s) or re.search(r"-eq\s+0\b", s)
                or re.search(r"\bequals\s+0\b", s))

    def is_file_like(tok):
        if "*" in tok:
            return False
        if "/" in tok or re.search(r"\.[a-zA-Z]{1,6}$", tok):
            return True
        return norm_path(tok) in known

    def region_scoped(seg):
        if "|" not in seg:
            return False
        before = seg[:seg.rfind("|")]
        return bool(re.search(r"\bsed\s+-n\b", before) or re.search(
            r"\bawk\b[^|]*/[^/]*/\s*,\s*/[^/]*/", before))

    def resolve_file(seg, after):
        m2 = re.match(r"\s+([^\s'\"|>&;$()\[\]]+)", after)
        if m2 and is_file_like(m2.group(1)):
            return m2.group(1)
        cm = re.search(r"\b(?:cat|tac)\s+([^\s'\"|>&;()]+)", seg)
        if cm and is_file_like(cm.group(1)):
            return cm.group(1)
        rm = re.search(r"<\s*([^\s'\"|>&;()]+)", seg)
        if rm and is_file_like(rm.group(1)):
            return rm.group(1)
        return None

    def scan_ban(seg, need_count):
        found = (None, None)
        for gm in GREP_ARG_RE.finditer(seg):
            opts = gm.group(1)
            if opts_invert(opts) or (need_count and not opts_count(opts)):
                continue
            raw_pat = gm.group(2)
            if raw_pat is None:
                raw_pat = gm.group(3)
            if raw_pat is None:
                raw_pat = (gm.group(4) if gm.group(4) is not None
                           and plausible(gm.group(4)) else None)
            if not raw_pat:
                continue
            raw_file = resolve_file(seg, seg[gm.end():])
            if raw_file:
                found = (raw_pat, raw_file)
        return found

    seen = set()
    for ai, ta in enumerate(tasks):
        segments = []
        for line in ta["gate"].split("\n"):
            segments += re.split(r"\s*(?:&&|\|\|)\s*", line)
        for seg in segments:
            if "grep" not in seg:
                continue
            leading_not = bool(
                re.search(r"(?:^|[\n;&|(]|\bthen\b|\bdo\b)\s*!\s*grep",
                          seg)
                or (re.search(r"(?:^|[\n;&|(]|\bthen\b|\bdo\b)\s*!\s*\w",
                              seg) and re.search(r"\|\s*grep\b", seg)))
            count_zero = zero_cmp(seg)
            pat = fil = None
            if leading_not and not count_zero:
                pat, fil = scan_ban(seg, False)
            if pat is None and count_zero:
                pat, fil = scan_ban(seg, True)
            if not pat or not fil or pat in allow or region_scoped(seg):
                continue
            gate_file = norm_path(fil)
            for bi, tb in enumerate(tasks):
                if bi == ai:
                    continue
                if not any(
                        norm_path(bf) == gate_file
                        or ("/" not in gate_file and os.path.basename(
                            norm_path(bf)) == gate_file)
                        for bf in tb["files"]):
                    continue
                if not pattern_required_in(pat, tb["req"]):
                    continue
                key = f"{ai}:{bi}:{pat}:{fil}"
                if key in seen:
                    continue
                seen.add(key)
                warnings.append(
                    f'Region-scope conflict (#968): task "{ta["name"]}" '
                    f'negative-greps "{pat}" file-wide on {fil}, but '
                    f'sibling task "{tb["name"]}" requires it in the same '
                    "file. A file-wide ban is unsatisfiable when a sibling "
                    "needs the construct elsewhere — region-scope task "
                    f'"{ta["name"]}"\'s gate (sed -n/awk range then grep) '
                    "or use an AST/test check. See planner-antipatterns.md "
                    '"Region-Scoped Negative Gates", or add '
                    f"<!-- planner-region-allow: {pat} --> if intentional.")
    return warnings
