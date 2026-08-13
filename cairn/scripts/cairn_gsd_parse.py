"""cairn_gsd_parse.py — o substrato de documento do binário, em UMA fonte.

Leitura e parse dos artefatos GSD (PLAN.md, CONTEXT.md, SUMMARY.md): subset
de frontmatter, must_haves, tasks de PLAN, decisões de CONTEXT, superfícies
designadas de plano, presença de UI e o bloco coverage do SUMMARY — portes
com proveniência src/*.cts da tag v1.10.0, por função.

Existe separado de cairn_gsd_render.py porque as duas coisas não são a
mesma: o envelope é a semântica de SAÍDA que 2+ irmãos compartilham, e isto
aqui é a semântica de ENTRADA de um documento. Enquanto viveram no mesmo
arquivo, o módulo fechou em 1536 linhas e o nome "render" passou a mentir
sobre o conteúdo — o teto D-01 media o arquivo certo pelo número errado
(CairnGo-zzgn; partição em CairnGo-2fyg, saída (a) decidida na fase 38).

Semântica de VEREDITO (exits, shapes, rotas) continua nos irmãos. Nenhum
veredito aqui.

Não é CLI: sem wrapper .sh.
"""
import re
import sys
from pathlib import Path


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
