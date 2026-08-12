"""cairn_gsd_render.py — o envelope medido do binário, em UMA fonte (D-01).

Módulo compartilhado pelos irmãos cairn-gsd-state.py, cairn-gsd-init.py e
cairn-gsd-check.py: a semântica de saída MEDIDA do gsd-tools real (io.cts
output(): sem --raw JSON.stringify(v, null, 2); com --raw e rawValue
definido String(rawValue); sem newline final) e o parse de argv na forma da
casa. O dispatcher cairn-gsd.py mantém a cópia original (é dele que a forma
foi copiada); este módulo existe para os irmãos não carregarem cópias que
possam divergir — a doença do milestone com outro chapéu.

Fase 35 (teto D-01, discrição do CONTEXT + precedente 34-05 desvio 2): a
seção "parsing de documento" abaixo carrega o substrato compartilhado de
leitura dos artefatos GSD (frontmatter subset, must_haves, tasks de PLAN.md,
decisões de CONTEXT.md, presença de UI, conflito de gate file-wide) —
portes com proveniência src/*.cts da tag v1.10.0. Sem ela o irmão de
checagem não fecharia em 1500 linhas com os 16 verbos; comprimir handlers
até ilegível seria pior que a fonte única. Semântica de VEREDITO (exits,
shapes, rotas) continua nos irmãos.

Não é CLI: sem wrapper .sh (nota registrada no SUMMARY do 34-05).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_UNDEFINED = object()


def js_number_text(n):
    if isinstance(n, int):
        return str(n)
    if float(n).is_integer():
        return str(int(n))
    return repr(float(n))


def js_string(value):
    """String(valor) do JS para --raw: bool minúsculo, null literal,
    objeto '[object Object]', array join por vírgula."""
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
    return json.dumps(value, indent=2, ensure_ascii=False)


def emit(text):
    sys.stdout.write(text)


def output_like_binary(result, raw, raw_value=_UNDEFINED):
    if raw and raw_value is not _UNDEFINED:
        emit(js_string(raw_value))
    else:
        emit(stringify(result))


def parse_verb_args(rest, value_flags=(), bool_flags=("--raw",)):
    """Forma da casa: flags de valor nomeadas, bools, flag desconhecida
    ignorada best-effort; o resto é posicional."""
    pos, flags = [], {}
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in value_flags:
            flags[tok] = rest[i + 1] if i + 1 < len(rest) else None
            i += 2
        elif tok in bool_flags:
            flags[tok] = True
            i += 1
        elif tok.startswith("-"):
            i += 1
        else:
            pos.append(tok)
            i += 1
    return pos, flags


# ═══════════════════════════════════════════════════════════════════════════
# parsing de documento (fase 35, teto D-01) — substrato compartilhado de
# leitura dos artefatos GSD; proveniência por função. Nenhum veredito aqui.
# ═══════════════════════════════════════════════════════════════════════════
def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def find_project_root(cwd):
    """Sobe procurando .planning (molde cairn-gsd-state.py L255)."""
    cur = Path(cwd).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / ".planning").is_dir():
            return candidate
    return cur


def parse_frontmatter_lines(text):
    """(dict, span) — subset YAML plano; molde cairn-gsd-init.py L876-890."""
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


def plan_files_modified_from(text):
    """files_modified em flow-list ou block-list — molde
    parse_plan_files_modified (cairn-doctor.py L1999-2013)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    body = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    for i, line in enumerate(body):
        m = re.match(r"^files_modified\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1)
        if "[" in rest:
            inner = rest[rest.index("[") + 1:]
            if "]" in inner:
                inner = inner[:inner.index("]")]
            return [t.strip().strip("'\"") for t in inner.split(",")
                    if t.strip().strip("'\"")]
        files = []
        for cont in body[i + 1:]:
            mi = re.match(r"^\s*-\s*(.+?)\s*$", cont)
            if not mi:
                break
            files.append(mi.group(1).strip("'\""))
        return files
    return []


def parse_must_haves_block(content, block_name):
    """Port de parseMustHavesBlock (src/frontmatter.cts L497-L637 da tag):
    o subset YAML de 3 níveis must_haves > bloco > itens."""
    fm_m = re.match(r"^---\r?\n([\s\S]+?)\r?\n---", content)
    if not fm_m:
        return []
    yaml = fm_m.group(1)
    mh = re.search(r"^(\s*)must_haves:\s*$", yaml, re.M)
    if not mh:
        return []
    bm = re.search(rf"^(\s+){re.escape(block_name)}:\s*$", yaml, re.M)
    if not bm or len(bm.group(1)) <= len(mh.group(1)):
        return []
    block_indent = len(bm.group(1))
    start = yaml.find(bm.group(0))
    block_lines = re.split(r"\r?\n", yaml[start:])[1:]
    items, current, li_indent = [], None, -1

    def push(cur):
        if cur is not None and cur != "":
            items.append(cur)

    for line in block_lines:
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= block_indent:
            break
        trimmed = line.strip()
        if trimmed.startswith("- "):
            if li_indent == -1:
                li_indent = indent
            if indent == li_indent:
                push(current)
                after = trimmed[2:]
                t2 = after.strip()
                if ((t2.startswith('"') and t2.endswith('"'))
                        or (t2.startswith("'") and t2.endswith("'"))):
                    current = t2[1:-1]
                elif ":" not in after:
                    current = after.strip("'\"")
                else:
                    kv = re.match(r'^(\w+):\s+"?([^"]*)"?\s*$', after)
                    current = ({kv.group(1): kv.group(2)} if kv
                               else after.strip("'\""))
                continue
        if isinstance(current, dict) and indent > li_indent:
            if trimmed.startswith("- "):
                arr_val = trimmed[2:].strip("'\"")
                keys = list(current.keys())
                last = keys[-1] if keys else None
                if last is not None:
                    if not isinstance(current[last], list):
                        existing = current[last]
                        current[last] = [existing] if existing else []
                    current[last].append(arr_val)
            else:
                kv = re.match(r'^(\w+):\s*"?([^"]*)"?\s*$', trimmed)
                if kv:
                    val = kv.group(2).strip()
                    current[kv.group(1)] = (int(val)
                                            if re.fullmatch(r"\d+", val)
                                            else val)
    push(current)
    if not items and block_lines:
        non_empty = sum(1 for ln in block_lines if ln.strip())
        if non_empty:
            print(f"[gsd-tools] WARNING: must_haves.{block_name} block has "
                  f"{non_empty} content lines but parsed 0 items. Possible "
                  "YAML formatting issue — verification will fall back to "
                  "LLM-derived truths.", file=sys.stderr)
    return items


TASK_BLOCK_RE = re.compile(
    r"<task(\s[^>]{0,1000})?>((?:(?!<task[\s>]).)*?)</task>", re.S)


def extract_plan_task_infos(content):
    """Port de extractPlanTaskInfos (src/verify.cts L721-L761)."""
    infos = []
    for m in TASK_BLOCK_RE.finditer(content or ""):
        attrs = m.group(1) or ""
        body = m.group(2) or ""
        tm = re.search(r"\btype\s*=\s*[\"']?([\w:-]+)", attrs, re.I)
        nm = re.search(r"<name>(.*?)</name>", body, re.S)
        infos.append({
            "name": nm.group(1).strip() if nm else "",
            "type": tm.group(1).lower() if tm else "",
            "hasName": nm is not None,
            "hasFiles": "<files>" in body,
            "hasAction": "<action>" in body,
            "hasVerify": "<verify>" in body,
            "hasDone": "<done>" in body,
            "hasWhatBuilt": "<what-built>" in body,
            "hasHowToVerify": "<how-to-verify>" in body,
            "hasDecision": "<decision>" in body,
            "hasOptions": "<options>" in body,
            "hasInstructions": "<instructions>" in body,
            "hasVerification": "<verification>" in body,
            "hasResumeSignal": "<resume-signal>" in body,
        })
    return infos


def strip_fences(text):
    """(texto sem blocos cercados, fence não terminada?)."""
    out, in_fence, delim, unterminated = [], False, None, False
    for line in text.split("\n"):
        s = line.strip()
        if not in_fence and (s.startswith("```") or s.startswith("~~~")):
            in_fence, delim = True, s[:3]
            continue
        if in_fence and s.startswith(delim):
            in_fence = False
            continue
        if not in_fence:
            out.append(line)
    if in_fence:
        unterminated = True
    return "\n".join(out), unterminated


def collect_heading_section(content, head_re):
    """Corpo da primeira seção cujo heading casa head_re (level-bounded)."""
    lines = content.split("\n")
    start = level = None
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m and head_re.search(m.group(2)):
            start, level = i, len(m.group(1))
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = re.match(r"^(#{1,6})\s", lines[j])
        if m and len(m.group(1)) <= level:
            end = j
            break
    return "\n".join(lines[start + 1:end])


# --- decisões de CONTEXT.md — port compacto de src/decisions.cts ------------
BULLET_COLON = re.compile(
    r"^\s*-\s+\*\*D-([A-Za-z0-9][A-Za-z0-9_-]*)"
    r"(?:\s*\[([^\]]+)\])?[^:*]*:\*\*\s*(.*)$")
BULLET_EMDASH = re.compile(
    r"^\s*-\s+\*\*D-([A-Za-z0-9][A-Za-z0-9_-]*)"
    r"(?:\s*\[([^\]]+)\])?[^*]*[—–][^*]*\*\*\s*(.*)$")
BULLET_TITLED = re.compile(
    r"^\s*-\s+\*\*D-([A-Za-z0-9][A-Za-z0-9_-]*)"
    r"(?:\s*\[([^\]]+)\])?[^:*]*:[^:*]*\*\*\s*(.*)$")
BOLD_LEAD_BULLET = re.compile(r"^\s*-\s+\*\*[A-Z]+[0-9]*-[A-Za-z0-9]", re.M)
NON_TRACKABLE_TAGS = {"informational", "folded", "deferred"}
DISCRETION_HEADINGS = {"claude's discretion", "claudes discretion",
                       "claude discretion"}


def parse_decision_lines(block):
    """(decisions, parse_misses) — parseDecisionLines da tag."""
    out, category, in_discretion, current, misses = [], "", False, None, 0

    def flush():
        nonlocal current
        if current:
            current["text"] = current["text"].strip()
            out.append(current)
            current = None

    for line in block.split("\n"):
        trimmed = line.strip()
        hm = re.match(r"^###\s+(.+?)\s*$", trimmed)
        if hm:
            flush()
            category = hm.group(1)
            normalized = re.sub(r"[‘’‚‛“”„‟''\"`]", "",
                                category.lower()).strip()
            in_discretion = normalized in DISCRETION_HEADINGS
            continue
        matched = False
        for rx in (BULLET_COLON, BULLET_EMDASH, BULLET_TITLED):
            m = rx.match(line)
            if m:
                flush()
                tags = ([t.strip().lower() for t in m.group(2).split(",")
                         if t.strip()] if m.group(2) else [])
                current = {"id": f"D-{m.group(1)}",
                           "text": m.group(3) or "", "category": category,
                           "tags": tags,
                           "trackable": not in_discretion and not any(
                               t in NON_TRACKABLE_TAGS for t in tags)}
                matched = True
                break
        if matched:
            continue
        if re.match(r"^\s*-\s+\*\*D-", line):
            flush()
            misses += 1
            continue
        if (current and trimmed and not trimmed.startswith("-")
                and re.match(r"^[ \t]", line)):
            current["text"] += " " + trimmed
            continue
        if trimmed == "":
            flush()
    flush()
    return out, misses


def extract_decisions(content):
    """(trackable, outcome) — extractDecisions (decisions.cts L242+)."""
    if not content or not isinstance(content, str):
        return [], "none-present"
    stripped, unterminated = strip_fences(content)
    blocks = re.findall(r"<decisions>((?:(?!<decisions[\s>]).)*?)"
                        r"</decisions>", stripped, re.S)
    if blocks:
        combined = "\n\n".join(blocks)
        decisions, misses = parse_decision_lines(combined)
        if decisions and misses == 0:
            return [d for d in decisions if d["trackable"]], "parsed"
        if misses > 0:
            return ([d for d in decisions if d["trackable"]],
                    "could-not-parse")
        if (re.search(r"\bD-[A-Za-z0-9]", combined, re.M)
                or BOLD_LEAD_BULLET.search(combined) or unterminated):
            return [], "could-not-parse"
        return [], "none-present"
    section = collect_heading_section(content,
                                      re.compile(r"decisions?\b", re.I))
    if section is not None:
        section, _u = strip_fences(section)
        decisions, misses = parse_decision_lines(section)
        if decisions and misses == 0:
            return [d for d in decisions if d["trackable"]], "parsed"
        if misses > 0:
            return ([d for d in decisions if d["trackable"]],
                    "could-not-parse")
        if (re.search(r"\bD-[A-Za-z0-9]", section, re.M)
                or BOLD_LEAD_BULLET.search(section)):
            return [], "could-not-parse"
        return [], "none-present"
    if unterminated or re.search(r"\bD-[A-Za-z0-9]", stripped, re.M):
        return [], "could-not-parse"
    return [], "none-present"


# --- superfícies de plano p/ cobertura de decisões (#2372) ------------------
XML_DECISION_TAGS = ("objective", "tasks", "task", "action", "read_first",
                     "behavior", "verify", "acceptance_criteria", "done")
DESIGNATED_HEADINGS_RE = re.compile(
    r"^#{1,6}\s+(?:must[_ ]haves?|truths?|tasks?|objective)\b", re.I)


def normalize_phrase(text):
    return re.sub(r"\s+", " ",
                  re.sub(r"[^a-z0-9\s]", " ",
                         str(text or "").lower())).strip()


def extract_plan_designated_sections(plan_content):
    """extractPlanDesignatedSections (#2372): frontmatter must_haves/truths/
    objective + headings designados + corpos dos 9 XML tags (per-tag)."""
    if not plan_content:
        return ""
    cleaned = re.sub(r"<!--(?:(?!<!--).)*?-->", " ", plan_content,
                     flags=re.S)
    cleaned, _u = strip_fences(cleaned)
    fm_m = re.match(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$", cleaned)
    frontmatter = fm_m.group(1) if fm_m else ""
    body = fm_m.group(2) if fm_m else cleaned
    parts = []
    for key in ("must_haves", "truths", "objective"):
        m = re.search(rf"^{key}\s*:(.*)$", frontmatter, re.M)
        if m:
            block = [m.group(1) or ""]
            for line in frontmatter[m.end():].split("\n")[1:]:
                if line == "" or re.match(r"^\s", line):
                    block.append(line)
                else:
                    break
            parts.append("\n".join(block))
    body_parts, in_designated = [], False
    for ln in body.split("\n"):
        hm = re.match(r"^(#{1,6})\s", ln)
        if hm:
            in_designated = bool(DESIGNATED_HEADINGS_RE.match(ln))
            if in_designated:
                body_parts.append(ln)
            continue
        if in_designated:
            body_parts.append(ln)
    parts.append("\n".join(body_parts))
    xml_parts = []
    for tag in XML_DECISION_TAGS:
        xml_parts += re.findall(
            rf"<{tag}(?:\s[^>]{{0,1000}})?>"
            rf"((?:(?!<{tag}[\s>]).)*?)</{tag}>",
            cleaned, re.S | re.I)
    parts.append("\n".join(xml_parts))
    return "\n\n".join(parts)


# --- presença de UI (ui-safety-gate.cts L57-L115) ---------------------------
UI_TOKENS = ("UI", "interface", "frontend", "component", "layout", "page",
             "screen", "view", "form", "dashboard", "widget")
UI_GATE_RE = re.compile(
    "(^|[^a-zA-Z0-9])(" + "|".join(UI_TOKENS) + ")([^a-zA-Z0-9]|$)", re.I)


def check_ui_presence(text):
    """checkUiPresence: hint **UI hint**: yes|no autoritativo (#2150)."""
    if not isinstance(text, str):
        return False
    normalised = text.replace("\r\n", "\n")
    hm = re.search(r"^\s*\*\*UI hint\*\*\s*:\s*(yes|no)\b", normalised,
                   re.I | re.M)
    hint = hm.group(1).lower() if hm else None
    if hint == "no":
        return False
    if hint == "yes":
        return True
    sniffable = "\n".join(
        ln for ln in normalised.split("\n")
        if not re.match(r"^\s*\*\*UI hint\*\*\s*:", ln, re.I))
    return any(UI_GATE_RE.search(ln) for ln in sniffable.split("\n"))


# --- bloco coverage do SUMMARY (src/coverage.cts L126-L292) -----------------
def get_frontmatter_yaml(content):
    """getFrontmatterYaml: o YAML entre os --- do topo, ou None."""
    if content.startswith("---\r\n"):
        start = 5
    elif content.startswith("---\n"):
        start = 4
    else:
        return None
    close = content.find("\n---", start)
    if close == -1:
        return None
    end = close - 1 if content[close - 1] == "\r" else close
    return content[start:end]


def _cov_scalar(raw):
    t = raw.strip()
    if t == "":
        return ""
    if ((t.startswith('"') and t.endswith('"'))
            or (t.startswith("'") and t.endswith("'"))):
        return t[1:-1]
    if t == "true":
        return True
    if t == "false":
        return False
    if t in ("null", "~"):
        return None
    return t


def _cov_indent(line):
    return len(line) - len(line.lstrip(" "))


def _cov_set(obj, key, value):
    if key in ("__proto__", "constructor", "prototype"):
        return
    obj[key] = value


def cov_parse_node(lines, indent):
    """parseNode do mini-YAML do coverage (porte fiel, subset)."""
    first = next((ln for ln in lines if ln.strip()), None)
    if first is None:
        return None
    if _cov_indent(first) == indent and re.match(r"^ *-( |$)", first):
        return _cov_sequence(lines, indent)
    return _cov_mapping(lines, indent)


def _cov_sequence(lines, indent):
    items, starts = [], []
    for i, ln in enumerate(lines):
        if ln.strip() and _cov_indent(ln) == indent \
                and re.match(r"^ *-( |$)", ln):
            starts.append(i)
    for k, start in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        item = list(lines[start:end])
        item[0] = " " * (indent + 2) + item[0][indent + 2:]
        first = next((ln for ln in item if ln.strip()), None)
        head = first.strip() if first else ""
        if re.match(r"^[\w-]+:( |$)", head):
            items.append(_cov_mapping(item, indent + 2))
        elif head == "":
            items.append(None)
        else:
            items.append(_cov_scalar(head))
    return items


def _cov_mapping(lines, indent):
    out, i = {}, 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or _cov_indent(ln) != indent:
            i += 1
            continue
        km = re.match(r"^([\w-]+):\s*(.*)$", ln.strip())
        if not km:
            i += 1
            continue
        key, inline = km.group(1), km.group(2)
        if inline == "[]":
            _cov_set(out, key, [])
            i += 1
        elif inline == "":
            j = i + 1
            while j < len(lines) and (not lines[j].strip()
                                      or _cov_indent(lines[j]) > indent):
                j += 1
            block = lines[i + 1:j]
            first = next((ln2 for ln2 in block if ln2.strip()), None)
            _cov_set(out, key, None if first is None
                     else cov_parse_node(block, _cov_indent(first)))
            i = j
        else:
            _cov_set(out, key, _cov_scalar(inline))
            i += 1
    return out


def parse_coverage(content):
    """parseCoverage: (found, entries, malformed) — bloco quebrado NUNCA
    passa por 'all covered' (fail-safe)."""
    yaml = get_frontmatter_yaml(content)
    if yaml is None:
        return False, [], False
    lines = re.split(r"\r?\n", yaml)
    cov_idx = next((i for i, ln in enumerate(lines)
                    if re.match(r"^coverage:(\s|$)", ln)), -1)
    if cov_idx == -1:
        return False, [], False
    raw_inline = re.match(r"^coverage:\s*(.*)$", lines[cov_idx]).group(1)
    inline = re.sub(r"\s*#.*$", "", raw_inline).strip()
    if inline == "[]":
        return True, [], False
    if inline != "":
        return True, [], True
    j = cov_idx + 1
    while j < len(lines):
        ln = lines[j]
        if ln.strip() == "":
            j += 1
            continue
        if re.match(r"^[A-Za-z0-9_-]+:(\s|$)", ln):
            break
        j += 1
    block = lines[cov_idx + 1:j]
    first = next((ln for ln in block if ln.strip()), None)
    if first is None:
        return True, [], False
    node = cov_parse_node(block, _cov_indent(first))
    if not isinstance(node, list) or not node:
        return True, [], True
    return True, node, False


# --- validação de shape do bloco coverage (src/coverage.cts L294-L420) ----
_COV_KINDS = ("unit", "integration", "e2e", "automated_ui",
              "manual_procedural", "other")
_COV_STATUSES = ("pass", "fail", "unknown")


def _cov_validate_entry(entry, index, seen_ids):
    """validateEntry (src/coverage.cts L294-L355)."""
    errors = []
    if not isinstance(entry, dict):
        return [{"index": index, "id": None, "code": "malformed_entry",
                 "message": "coverage entry is not a mapping"}]
    eid = entry.get("id") if isinstance(entry.get("id"), str) else None

    def push(code, message, field=None):
        e = {"index": index, "id": eid, "code": code}
        if field is not None:
            e["field"] = field
        e["message"] = message
        errors.append(e)

    if not isinstance(entry.get("id"), str) or not entry["id"].strip():
        push("missing_id", "entry is missing a non-empty id", "id")
    elif entry["id"] in seen_ids:
        push("duplicate_id", f'duplicate coverage id "{entry["id"]}"', "id")
    else:
        seen_ids.add(entry["id"])
    if not isinstance(entry.get("description"), str) \
            or not entry["description"].strip():
        push("missing_description",
             "entry is missing a non-empty description", "description")
    if "human_judgment" not in entry:
        push("missing_human_judgment",
             "entry is missing the required human_judgment flag",
             "human_judgment")
    elif not isinstance(entry["human_judgment"], bool):
        push("invalid_human_judgment",
             "human_judgment must be a boolean (true|false)",
             "human_judgment")
    if entry.get("human_judgment") is True and (
            not isinstance(entry.get("rationale"), str)
            or not entry["rationale"].strip()):
        push("missing_rationale",
             "rationale is required when human_judgment is true",
             "rationale")
    v = entry.get("verification")
    if v is not None and not isinstance(v, list):
        push("verification_not_list", "verification must be a list",
             "verification")
    elif isinstance(v, list):
        for vi, ve in enumerate(v):
            if not isinstance(ve, dict):
                push("malformed_entry", "verification item is not a mapping",
                     f"verification[{vi}]")
                continue
            if not isinstance(ve.get("kind"), str) \
                    or ve["kind"] not in _COV_KINDS:
                push("invalid_kind", "verification kind must be one of "
                     + ", ".join(_COV_KINDS), f"verification[{vi}].kind")
            if not isinstance(ve.get("status"), str) \
                    or ve["status"] not in _COV_STATUSES:
                push("invalid_status", "verification status must be one of "
                     + ", ".join(_COV_STATUSES),
                     f"verification[{vi}].status")
            if not isinstance(ve.get("ref"), str) or not ve["ref"].strip():
                push("missing_ref",
                     "verification entry is missing a non-empty ref",
                     f"verification[{vi}].ref")
    return errors


def _cov_entry_view(entry):
    if not isinstance(entry, dict):
        return {"id": None, "description": None, "verification": [],
                "human_judgment": None}
    vlist = entry.get("verification")
    vlist = vlist if isinstance(vlist, list) else []
    view = {
        "id": entry.get("id") if isinstance(entry.get("id"), str) else None,
        "description": (entry.get("description")
                        if isinstance(entry.get("description"), str)
                        else None),
        "verification": [
            {"kind": ve.get("kind") if isinstance(ve, dict)
             and isinstance(ve.get("kind"), str) else None,
             "ref": ve.get("ref") if isinstance(ve, dict)
             and isinstance(ve.get("ref"), str) else None,
             "status": ve.get("status") if isinstance(ve, dict)
             and isinstance(ve.get("status"), str) else None}
            for ve in vlist],
        "human_judgment": (entry.get("human_judgment")
                           if isinstance(entry.get("human_judgment"), bool)
                           else None),
    }
    if isinstance(entry.get("requirement"), str):
        view["requirement"] = entry["requirement"]
    if isinstance(entry.get("rationale"), str):
        view["rationale"] = entry["rationale"]
    return view


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
