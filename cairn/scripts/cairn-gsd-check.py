#!/usr/bin/env python3
"""cairn-gsd-check.py — irmão de checagem do dispatcher cairn-gsd.py (D-01).

A família checagem (11 verbos) + os 5 ex-órfãos de CHECK-03 (fase 35).
Invocado pelo dispatcher via os.execv com o VERBO canônico como argv[1].
Usage: cairn-gsd-check.py <verbo> [argv] | --list-implemented.

A doutrina exit-code da família: o veredito de todo gate AVALIADO vai no
PAYLOAD (passed/active/block/valid), NUNCA no exit — exit 0 = gate
avaliado, mesmo reprovando. Exits: 0 contrato; 1 erro de USO contratado
(subcommand desconhecido, flag obrigatória ausente, path inválido); 2 uso
deste script; 4 verbo ainda sem handler. Exceções contratadas:
run-with-timeout é exit-only (tabela GNU-timeout) e review-lane fala texto.

Teto D-01: wc -l ≤ 1500. Envelope em cairn_gsd_render, substrato de
documento em cairn_gsd_parse, substrato de FATO em cairn_gsd_fact (fonte
única, nenhuma cópia local — partição CairnGo-2fyg). Divergências:
tests/fixtures/gsd-goldens/divergences.json. cairn/gsd/ é SOMENTE-LEITURA.
"""
import datetime
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cairn_gsd_render import (emit, js_string,  # noqa: E402
                              output_like_binary, parse_verb_args)
from cairn_gsd_parse import (  # noqa: E402
    _cov_entry_view, _cov_validate_entry, check_ui_presence,
    collect_heading_section, extract_decisions, extract_plan_designated_sections,
    extract_plan_task_infos, find_project_root, normalize_phrase, parse_coverage,
    parse_frontmatter_lines, parse_must_haves_block, plan_files_modified_from,
    read_text)
from cairn_gsd_fact import (  # noqa: E402
    _classify_drift_file, _find_phase_artifact, _find_stale_summary,
    _is_path_mapped, _parse_predicate_flags, _run_bounded_shell, _run_git,
    _trim_2000, AUDIT_SCANNERS, DRIFT_PRIORITY, REVIEWER_LANES,
    VERIFICATION_ROUTING_TABLE, build_checkpoint, format_audit_report,
    scan_file_wide_negative_gate_conflict)

EXIT_OK = 0
EXIT_CONTRACT = 1
EXIT_USAGE = 2
EXIT_UNIMPLEMENTED = 4

TAG_PREFIX = "[cairn-gsd-check]"

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "gsd" / "contracts"

# Regexes de fase/plano — cópia de forma de cairn-gsd-state.py L93-95.
PLAN_FILE = re.compile(r"^\d+-(\d+)-PLAN\.md$")
PHASE_DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")


def die(msg, code=EXIT_USAGE):
    print(f"{TAG_PREFIX} error: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# verification.status — o verbo das duas grafias (CHECK-01)
# --------------------------------------------------------------------------- #
def resolve_runtime(cwd):
    """GSD_RUNTIME > .planning/config.json runtime > 'claude' — a cadeia de
    resolveRuntime (src/runtime-slash.cts L88-L118 da tag)."""
    env = os.environ.get("GSD_RUNTIME")
    if env and env.strip():
        return env.strip().lower()
    text = read_text(Path(cwd) / ".planning" / "config.json")
    if text is not None:
        try:
            cfg = json.loads(text)
            rt = cfg.get("runtime") if isinstance(cfg, dict) else None
            if isinstance(rt, str) and rt.strip():
                return rt.strip().lower()
        except (json.JSONDecodeError, ValueError):
            pass
    return "claude"


def project_next_command(bare, runtime, tail=""):
    """formatGsdSlash (src/runtime-slash.cts L40-L75): codex é o único
    runtime shell-var do capability-registry da tag → $gsd-<cmd> minúsculo;
    os demais /gsd-<cmd>. Comando vazio fica vazio."""
    if not bare:
        return ""
    if runtime == "codex":
        return f"$gsd-{bare.lower()}{tail}"
    return f"/gsd-{bare}{tail}"


def _frontmatter_status(vfile):
    """O `status:` literal do frontmatter — molde verification_status de
    cairn-status.py L1066-1085 (regex leniente + strip, sem lib YAML)."""
    text = read_text(vfile)
    if text is None:
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^status\s*:\s*(.+?)\s*$", line)
        if m:
            val = m.group(1).split("#", 1)[0].strip().strip("'\"").strip()
            return val or None
    return None


def handle_verification_status(rest):
    pos, flags = parse_verb_args(rest)
    if not pos:
        die("phase directory required for verification.status",
            EXIT_CONTRACT)
    raw = bool(flags.get("--raw"))
    pdir = Path(pos[0])
    if not pdir.is_absolute():
        pdir = Path.cwd() / pdir
    runtime = resolve_runtime(Path.cwd())
    # #2617: o número da fase só entra como argumento quando é
    # inequivocamente um número (extractPhaseToken + checagem numérica).
    m = re.match(r"^(\d+(?:\.\d+)*)-", pdir.name)
    phase_arg = f" {m.group(1)}" if m else ""

    def route(key, next_action=None, tail=phase_arg, bare=None):
        entry = VERIFICATION_ROUTING_TABLE[key]
        return {
            "status": entry[0],
            "next_action": entry[1] if next_action is None else next_action,
            "next_command": project_next_command(
                entry[2] if bare is None else bare, runtime, tail),
        }

    try:
        names = sorted(p.name for p in pdir.iterdir()
                       if p.is_file() and p.name.endswith("-VERIFICATION.md"))
    except OSError:
        names = []
    if not names:
        output_like_binary(route("missing"), raw)
        return EXIT_OK
    status_val = _frontmatter_status(pdir / names[0])
    if not status_val:
        output_like_binary(route("missing"), raw)
        return EXIT_OK
    if status_val == "gaps_found":
        output_like_binary(
            route("gaps_found", bare="plan-phase",
                  tail=f"{phase_arg} --gaps"), raw)
        return EXIT_OK
    determined, stale = _find_stale_summary(pdir)
    if determined and stale:
        output_like_binary(route("stale", bare="verify-work"), raw)
        return EXIT_OK
    if (status_val in VERIFICATION_ROUTING_TABLE
            and status_val not in ("missing", "unknown", "stale",
                                   "gaps_found")):
        result = route(status_val)
    else:
        result = route(
            "unknown",
            next_action=(f"Unexpected verification status '{status_val}'. "
                         "Re-run execute-phase verification."))
    if not determined:
        # #3057 B3, fail-open preservado: o check não completou — a chave
        # aparece SÓ nesse caso, com o nome do shape do contrato
        # (checagem.json; a tag emite staleCheckIndeterminate camelCase
        # nesta superfície — distância declarada em divergences.json).
        result["verification_stale_check_indeterminate"] = True
    output_like_binary(result, raw)
    return EXIT_OK


# --------------------------------------------------------------------------- #
# leitores de PLAN.md — a família verify (parser/extrator no render)
# --------------------------------------------------------------------------- #
def validate_plan_task_structure(t):
    """Port de validatePlanTaskStructure (src/verify.cts L783-L824):
    o conjunto canônico por tipo (checkpoints.md)."""
    errors, warnings = [], []
    name = t["name"] if t["hasName"] else "unnamed"
    if not t["hasName"]:
        errors.append("Task missing <name> element")
    if t["type"].startswith("checkpoint:"):
        if not t["hasResumeSignal"]:
            errors.append(f"Task '{name}' missing <resume-signal>")
        if t["type"] == "checkpoint:human-verify":
            if not t["hasWhatBuilt"]:
                errors.append(f"Task '{name}' missing <what-built>")
            if not t["hasHowToVerify"]:
                errors.append(f"Task '{name}' missing <how-to-verify>")
        elif t["type"] == "checkpoint:decision":
            if not t["hasDecision"]:
                errors.append(f"Task '{name}' missing <decision>")
            if not t["hasOptions"]:
                errors.append(f"Task '{name}' missing <options>")
        elif t["type"] == "checkpoint:human-action":
            if not t["hasAction"]:
                errors.append(f"Task '{name}' missing <action>")
            if not t["hasInstructions"]:
                errors.append(f"Task '{name}' missing <instructions>")
            if not t["hasVerification"]:
                errors.append(f"Task '{name}' missing <verification>")
    else:
        if not t["hasAction"]:
            errors.append(f"Task '{name}' missing <action>")
        if not t["hasVerify"]:
            warnings.append(f"Task '{name}' missing <verify>")
        if not t["hasDone"]:
            warnings.append(f"Task '{name}' missing <done>")
        if not t["hasFiles"]:
            warnings.append(f"Task '{name}' missing <files>")
    return errors, warnings


def handle_verify_plan_structure(rest):
    pos, flags = parse_verb_args(rest)
    raw = bool(flags.get("--raw"))
    if not pos:
        die("file path required", EXIT_CONTRACT)
    fpath = pos[0]
    if "\0" in fpath:
        die("file path contains null bytes", EXIT_CONTRACT)
    full = Path(fpath) if os.path.isabs(fpath) else Path.cwd() / fpath
    content = read_text(full)
    if not content:
        output_like_binary({"error": "File not found", "path": fpath}, raw)
        return EXIT_OK
    # #2701: fail-loud em NUL/binário ANTES de qualquer checagem
    nul = content.find("\0")
    if nul != -1:
        msg = (f"{fpath}: file contains NUL bytes (first at offset {nul}). "
               "Artifact files must be UTF-8 text. A NUL-corrupted file is "
               "binary-classified and silently skipped by recursive / "
               "binary-skipping search tools (rg, grep -I), so downstream "
               "verification reports its contents as missing rather than "
               "corrupt.")
        output_like_binary({"valid": False, "errors": [msg]}, raw)
        return EXIT_OK
    fm, _ = parse_frontmatter_lines(content)
    errors, warnings = [], []
    for field in ("phase", "plan", "type", "wave", "depends_on",
                  "files_modified", "autonomous", "must_haves"):
        if field not in fm:
            errors.append(f"Missing required frontmatter field: {field}")
    tasks_out = []
    for t in extract_plan_task_infos(content):
        errs, warns = validate_plan_task_structure(t)
        errors.extend(errs)
        warnings.extend(warns)
        tasks_out.append({"name": t["name"] if t["hasName"] else "unnamed",
                          "type": t["type"], "hasFiles": t["hasFiles"],
                          "hasAction": t["hasAction"],
                          "hasVerify": t["hasVerify"],
                          "hasDone": t["hasDone"]})
    if not tasks_out:
        warnings.append("No <task> elements found")
    wave = (fm.get("wave") or "").strip()
    if (wave.isdigit() and int(wave) > 1
            and (fm.get("depends_on") or "").strip() in ("", "[]")):
        warnings.append("Wave > 1 but depends_on is empty")
    if (re.search(r"<task\s+type=[\"']?checkpoint", content)
            and str(fm.get("autonomous")) != "false"):
        errors.append("Has checkpoint tasks but autonomous is not false")
    # #1951: rating one-way sem checkpoint:decision anterior — warn
    decision_offsets = [m.start() for m in re.finditer(
        r"<task\s+type=[\"']?checkpoint:decision", content)]
    for m in re.finditer(r"<reversibility\s[^>]*rating=[\"']?one-way",
                         content):
        if not any(off < m.start() for off in decision_offsets):
            warnings.append(
                'Task rated <reversibility rating="one-way"> has no '
                "preceding checkpoint:decision — a one-way door must be "
                "confirmed before the agent walks through it")
    warnings.extend(scan_file_wide_negative_gate_conflict(content))
    output_like_binary(
        {"valid": not errors, "errors": errors, "warnings": warnings,
         "task_count": len(tasks_out), "tasks": tasks_out,
         "frontmatter_fields": list(fm.keys())},
        raw, "valid" if not errors else "invalid")
    return EXIT_OK


def handle_verify_artifacts(rest):
    pos, flags = parse_verb_args(rest)
    raw = bool(flags.get("--raw"))
    if not pos:
        die("plan file path required", EXIT_CONTRACT)
    fpath = pos[0]
    full = Path(fpath) if os.path.isabs(fpath) else Path.cwd() / fpath
    content = read_text(full)
    if not content:
        output_like_binary({"error": "File not found", "path": fpath}, raw)
        return EXIT_OK
    artifacts = parse_must_haves_block(content, "artifacts")
    if not artifacts:
        output_like_binary({"error": "No must_haves.artifacts found in "
                                     "frontmatter", "path": fpath}, raw)
        return EXIT_OK
    results = []
    for art in artifacts:
        if not isinstance(art, dict):
            continue
        apath = art.get("path")
        if not apath:
            continue
        afull = Path.cwd() / apath
        exists = afull.exists()
        issues = []
        if exists:
            fc = read_text(afull) or ""
            line_count = len(fc.split("\n"))
            ml = art.get("min_lines")
            if ml and line_count < int(ml):
                issues.append(f"Only {line_count} lines, need {ml}")
            if art.get("contains") and str(art["contains"]) not in fc:
                issues.append(f"Missing pattern: {art['contains']}")
            if art.get("exports"):
                exps = (art["exports"] if isinstance(art["exports"], list)
                        else [art["exports"]])
                for e in exps:
                    if str(e) not in fc:
                        issues.append(f"Missing export: {e}")
        else:
            issues.append("File not found")
        results.append({"path": apath, "exists": exists, "issues": issues,
                        "passed": exists and not issues})
    passed_n = sum(1 for r in results if r["passed"])
    all_passed = passed_n == len(results)
    output_like_binary(
        {"all_passed": all_passed, "passed": passed_n,
         "total": len(results), "artifacts": results},
        raw, "valid" if all_passed else "invalid")
    return EXIT_OK


def collect_promised_files(phase_dir, min_wave):
    """Arquivos prometidos por planos de wave >= min_wave (#1202)."""
    promised = set()
    try:
        plan_files = sorted(p for p in phase_dir.iterdir()
                            if p.is_file() and PLAN_FILE.match(p.name))
    except OSError:
        return promised
    for pf in plan_files:
        text = read_text(pf)
        if not text:
            continue
        fm, _ = parse_frontmatter_lines(text)
        try:
            wave = int((fm.get("wave") or "").strip())
        except ValueError:
            continue
        if wave < min_wave:
            continue
        promised.update(f.strip() for f in plan_files_modified_from(text)
                        if f.strip())
    return promised


def handle_verify_key_links(rest):
    pos, flags = parse_verb_args(rest)
    raw = bool(flags.get("--raw"))
    if not pos:
        die("plan file path required", EXIT_CONTRACT)
    fpath = pos[0]
    full = Path(fpath) if os.path.isabs(fpath) else Path.cwd() / fpath
    content = read_text(full)
    if not content:
        output_like_binary({"error": "File not found", "path": fpath}, raw)
        return EXIT_OK
    key_links = parse_must_haves_block(content, "key_links")
    if not key_links:
        output_like_binary({"error": "No must_haves.key_links found in "
                                     "frontmatter", "path": fpath}, raw)
        return EXIT_OK
    fm, _ = parse_frontmatter_lines(content)
    try:
        cur_wave = int((fm.get("wave") or "").strip())
    except ValueError:
        cur_wave = 1
    promised = None
    results, pending_count = [], 0
    for link in key_links:
        if not isinstance(link, dict):
            continue
        check = {"from": link.get("from"), "to": link.get("to"),
                 "via": link.get("via") or "", "verified": False,
                 "detail": ""}
        from_path = str(link.get("from") or "")
        src = read_text(Path.cwd() / from_path) if from_path else None
        if not src:
            if promised is None:
                promised = collect_promised_files(full.parent, cur_wave)
            if from_path.strip() and from_path.strip() in promised:
                check["pending"] = True
                check["detail"] = ("Source file not yet created — declared "
                                   "in files_modified of a "
                                   "same-or-later-wave plan")
                pending_count += 1
            else:
                check["detail"] = ("Source file not found (from: must be a "
                                   "relative file path; describe components"
                                   "/endpoints in via:)")
        elif link.get("pattern"):
            try:
                regex = re.compile(str(link["pattern"]))
            except re.error:
                regex = None
                check["detail"] = f"Invalid regex pattern: {link['pattern']}"
            if regex is not None:
                if regex.search(src):
                    check["verified"] = True
                    check["detail"] = "Pattern found in source"
                else:
                    tgt = read_text(Path.cwd() / str(link.get("to") or ""))
                    if tgt and regex.search(tgt):
                        check["verified"] = True
                        check["detail"] = "Pattern found in target"
                    else:
                        check["detail"] = (f'Pattern "{link["pattern"]}" '
                                           "not found in source or target")
        else:
            if str(link.get("to") or "") in src:
                check["verified"] = True
                check["detail"] = "Target referenced in source"
            else:
                check["detail"] = "Target not referenced in source"
        results.append(check)
    verified = sum(1 for r in results if r["verified"])
    hard_failed = sum(1 for r in results
                      if not r["verified"] and not r.get("pending"))
    all_verified = hard_failed == 0
    output_like_binary(
        {"all_verified": all_verified, "verified": verified,
         "pending": pending_count, "total": len(results),
         "links": results},
        raw, "valid" if all_verified else "invalid")
    return EXIT_OK


def handle_verify_commits(rest):
    """git cat-file -t == 'commit' por hash; partição valid/invalid
    (cmdVerifyCommits, src/verify.cts L1035-L1062)."""
    pos, flags = parse_verb_args(rest)
    raw = bool(flags.get("--raw"))
    if not pos:
        die("At least one commit hash required", EXIT_CONTRACT)
    valid, invalid = [], []
    for h in pos:
        out = _run_git(["cat-file", "-t", h], Path.cwd())
        (valid if out is not None and out.strip() == "commit"
         else invalid).append(h)
    output_like_binary(
        {"all_valid": not invalid, "valid": valid, "invalid": invalid,
         "total": len(pos)},
        raw, "valid" if not invalid else "invalid")
    return EXIT_OK


# --- codebase-drift — port compacto de cmdVerifyCodebaseDrift + detectDrift
# (src/verify.cts L2520+, src/drift.cts; dados de classificação verbatim) ----
def _drift_skip(reason):
    return {"block": False, "skipped": True, "reason": reason,
            "action_required": False, "directive": "none", "elements": []}


def handle_verify_codebase_drift(rest):
    _, flags = parse_verb_args(rest)
    raw = bool(flags.get("--raw"))
    cwd = Path.cwd()
    structure_path = cwd / ".planning" / "codebase" / "STRUCTURE.md"
    if not structure_path.exists():
        output_like_binary(_drift_skip("no-structure-md"), raw)
        return EXIT_OK
    structure_md = read_text(structure_path)
    if structure_md is None:
        output_like_binary(_drift_skip("cannot-read-structure-md"), raw)
        return EXIT_OK
    fm, _span = parse_frontmatter_lines(structure_md)
    last_mapped = (fm.get("last_mapped_commit") or "").strip() or None
    if _run_git(["rev-parse", "HEAD"], cwd) is None:
        output_like_binary(_drift_skip("not-a-git-repo"), raw)
        return EXIT_OK
    empty_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    base = last_mapped or empty_tree
    if base != empty_tree and _run_git(["cat-file", "-t", base],
                                       cwd) is None:
        base = empty_tree
    diff = _run_git(["diff", "--name-status", base, "HEAD"], cwd)
    if diff is None:
        output_like_binary(_drift_skip("git-diff-failed"), raw)
        return EXIT_OK
    added = []
    for line in diff.splitlines():
        m = re.match(r"^([A-Z])\d*\t(.+?)(?:\t(.+))?$", line.strip("\n"))
        if not m:
            continue
        if m.group(1) in ("A", "R", "C"):
            added.append(m.group(3) or m.group(2))
    wf = read_workflow_config(find_project_root(cwd))
    threshold = (wf.get("drift_threshold")
                 if isinstance(wf.get("drift_threshold"), int)
                 and wf.get("drift_threshold") >= 1 else 3)
    action = ("auto-remap" if wf.get("drift_action") == "auto-remap"
              else "warn")
    seen = {}
    for f in added:
        cat = _classify_drift_file(f)
        if cat is None:
            if _is_path_mapped(f, structure_md):
                continue
            cat = "new_dir"
        prior = seen.get(f)
        if prior and DRIFT_PRIORITY[prior] >= DRIFT_PRIORITY[cat]:
            continue
        seen[f] = cat
    elements = sorted(
        ({"category": c, "path": p} for p, c in seen.items()),
        key=lambda e: (e["category"], e["path"]))
    action_required = len(elements) >= threshold
    directive, spawn_mapper, affected, message = "none", False, [], ""
    if action_required:
        directive = action
        tops = set()
        for e in elements:
            parts = e["path"].split("/")
            if parts[0] in ("apps", "packages") and len(parts) >= 2:
                tops.add(f"{parts[0]}/{parts[1]}")
            elif parts[0]:
                tops.add(parts[0])
        affected = sorted(tops)
        spawn_mapper = action == "auto-remap"
        by = {}
        for e in elements:
            by.setdefault(e["category"], []).append(e["path"])
        lines = [f"Codebase drift detected: {len(elements)} structural "
                 "element(s) since last mapping.", ""]
        labels = {"new_dir": "New directories", "barrel":
                  "New barrel exports", "migration": "New migrations",
                  "route": "New route modules"}
        for cat in ("new_dir", "barrel", "migration", "route"):
            if cat in by:
                lines.append(f"{labels[cat]}:")
                lines += [f"  - {p}" for p in by[cat]]
        lines.append("")
        runtime = resolve_runtime(cwd)
        if action == "auto-remap":
            lines.append("Auto-remap scheduled for paths: "
                         + ", ".join(affected))
        else:
            lines.append(
                f"Run {project_next_command('map-codebase', runtime)}"
                f" --paths {','.join(affected)} to refresh "
                "planning context.")
        message = "\n".join(lines)
    output_like_binary(
        {"block": action_required, "skipped": False, "reason": None,
         "action_required": action_required, "directive": directive,
         "spawn_mapper": spawn_mapper, "affected_paths": affected,
         "elements": elements, "threshold": threshold, "action": action,
         "last_mapped_commit": last_mapped, "message": message}, raw)
    return EXIT_OK


def _verify_unavailable(subcommand, raw):
    """Indisponibilidade declarada (molde 34-05): subcommand válido no
    router sem sítio no universo da 31 — nunca envelope inventado."""
    output_like_binary(
        {"available": False,
         "reason": (f"verify {subcommand}: subcommand sem sítio no universo "
                    "da fase 31 — superfície não observada, indisponível "
                    "por declaração (divergences.json, family checagem)")},
        raw)
    return EXIT_OK


def handle_verify(rest):
    """Comando de família (routeVerifyCommand, VERIFY_SUBCOMMANDS) — dict
    interno subcommand→função; um dono por semântica."""
    subs = ("plan-structure", "phase-completeness", "references", "commits",
            "artifacts", "key-links", "schema-drift", "codebase-drift")
    pos, flags = parse_verb_args(rest, bool_flags=("--raw", "--skip"))
    sub = pos[0] if pos else None
    raw = bool(flags.get("--raw"))
    if sub not in subs:
        die(f"Unknown verify subcommand. Available: {', '.join(subs)}",
            EXIT_CONTRACT)
    tail = rest[rest.index(sub) + 1:] if sub in rest else []
    if sub == "plan-structure":
        return handle_verify_plan_structure(tail)
    if sub == "commits":
        return handle_verify_commits(tail)
    if sub == "artifacts":
        return handle_verify_artifacts(tail)
    if sub == "key-links":
        return handle_verify_key_links(tail)
    if sub == "codebase-drift":
        return handle_verify_codebase_drift(tail)
    if sub == "schema-drift" and flags.get("--skip"):
        output_like_binary({"skipped": True, "reason": "--skip"}, raw)
        return EXIT_OK
    return _verify_unavailable(sub, raw)


# --------------------------------------------------------------------------- #
# check — o dispatcher de gates (routeCheckCommand, check-command-router.cts
# L1447-L1524; cmdAutoMode L107-L123; decision-coverage L281-L353)
# --------------------------------------------------------------------------- #
def read_workflow_config(root):
    """workflow do config com fallback top-level (readWorkflowConfig)."""
    text = read_text(Path(root) / ".planning" / "config.json")
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    wf = parsed.get("workflow") if isinstance(parsed.get("workflow"),
                                              dict) else {}
    out = dict(wf)
    for key in ("auto_advance", "_auto_chain_active",
                "context_coverage_gate"):
        if key not in out and key in parsed:
            out[key] = parsed[key]
    return out


def handle_check_auto_mode(raw):
    wf = read_workflow_config(find_project_root(Path.cwd()))
    auto_advance = bool(wf.get("auto_advance", False))
    chain = bool(wf.get("_auto_chain_active", False))
    source = ("both" if chain and auto_advance else
              "auto_chain" if chain else
              "auto_advance" if auto_advance else "none")
    output_like_binary({"active": chain or auto_advance, "source": source,
                        "auto_chain_active": chain,
                        "auto_advance": auto_advance}, raw)
    return EXIT_OK


def _gate_enabled(root):
    value = read_workflow_config(root).get("context_coverage_gate")
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("false", "true"):
        return value.lower() != "false"
    return True


def _decision_mentioned(haystack, decision):
    """decisionMentioned: \\bD-NN\\b OU soft-phrase de 6 palavras."""
    if not haystack:
        return False
    if re.search(rf"\b{re.escape(decision['id'])}\b", haystack):
        return True
    words = normalize_phrase(decision["text"]).split()
    if len(words) < 6:
        return False
    return " ".join(words[:6]) in normalize_phrase(haystack)


def handle_check_decision_coverage_plan(rest):
    pos, flags = parse_verb_args(rest)
    raw = bool(flags.get("--raw"))
    root = find_project_root(Path.cwd())
    phase_dir_arg = pos[0] if pos else ""
    context_arg = pos[1] if len(pos) > 1 else None
    if not _gate_enabled(root):
        output_like_binary(
            {"passed": True, "skipped": True,
             "reason": "workflow.context_coverage_gate is false", "total": 0,
             "covered": 0, "uncovered": [],
             "message": "Decision coverage gate disabled by config."}, raw)
        return EXIT_OK
    # #2770: argumento vazio é erro de CALLER — fail-closed, nunca skip
    if not context_arg:
        output_like_binary(
            {"passed": False, "skipped": False,
             "reason": "missing context path argument", "total": 0,
             "covered": 0, "uncovered": [],
             "message": "Decision coverage gate called without a context "
                        "path argument — the caller (e.g. the plan-phase "
                        "workflow) must pass the CONTEXT.md path. An empty "
                        "argument is a caller error, not evidence there is "
                        "nothing to check (#2770)."}, raw)
        return EXIT_OK
    context_path = (Path(context_arg) if os.path.isabs(context_arg)
                    else Path.cwd() / context_arg)
    if not context_path.exists():
        output_like_binary(
            {"passed": True, "skipped": True, "reason": "CONTEXT.md missing",
             "total": 0, "covered": 0, "uncovered": [],
             "message": "No CONTEXT.md - nothing to check."}, raw)
        return EXIT_OK
    decisions, outcome = extract_decisions(read_text(context_path) or "")
    if outcome == "could-not-parse":
        partial = bool(decisions)
        output_like_binary(
            {"passed": False, "skipped": False, "reason": "could-not-parse",
             "total": len(decisions), "covered": 0, "uncovered": [],
             "message": (
                 "Decision coverage gate: decisions could not be fully "
                 "parsed — one or more `- **D-NN ...**` bullets appear "
                 "malformed (missing `:` or ` — ` separator). Fix the "
                 "bullet format so all D-NN decisions can be read before "
                 "re-running the gate." if partial else
                 "Decision coverage gate: could not parse decisions — "
                 "possible format mismatch. The CONTEXT.md appears to be "
                 "decision-shaped (has a <decisions> block, a decisions "
                 "heading, or D- tokens) but no D-NN bullets could be "
                 "extracted. Check the formatting of the decisions block "
                 "and ensure bullets follow the `- **D-NN:** text` or "
                 "`- **D-NN — title** body` form.")}, raw)
        return EXIT_OK
    if not decisions:
        output_like_binary(
            {"passed": True, "skipped": True,
             "reason": "no trackable decisions", "total": 0, "covered": 0,
             "uncovered": [],
             "message": "No trackable decisions in CONTEXT.md."}, raw)
        return EXIT_OK
    phase_dir = ((Path(phase_dir_arg) if os.path.isabs(phase_dir_arg)
                  else Path.cwd() / phase_dir_arg)
                 if phase_dir_arg else None)
    sections = []
    if phase_dir and phase_dir.is_dir():
        try:
            sections = [extract_plan_designated_sections(
                read_text(phase_dir / e.name) or "")
                for e in sorted(phase_dir.iterdir())
                if e.is_file() and e.name.endswith("-PLAN.md")]
        except OSError:
            sections = []
    uncovered, covered = [], 0
    for d in decisions:
        if any(_decision_mentioned(s, d) for s in sections):
            covered += 1
        else:
            uncovered.append({"id": d["id"], "text": d["text"],
                              "category": d["category"]})
    if uncovered:
        message = "\n".join(
            ["## Decision Coverage Gap", "",
             f"{len(uncovered)} CONTEXT.md decision(s) are not covered by "
             "any plan:", ""]
            + [f"- **{u['id']}** ({u['category'] or 'uncategorized'}): "
               f"{u['text']}" for u in uncovered]
            + ["",
               "Resolve by citing `D-NN:` in any of the scanned plan "
               "surfaces: front-matter",
               "`must_haves`/`truths`/`objective`, a `## must_haves`/"
               "`truths`/`tasks`/`objective`",
               "heading, or an `<objective>`/`<tasks>`/`<task>`/`<action>`/"
               "`<read_first>`/`<behavior>`/`<verify>`/"
               "`<acceptance_criteria>`/`<done>`",
               "tag body. Other locations (prose outside those headings, "
               "comments, other XML tags) are not scanned.",
               "OR move the decision to `### Claude's Discretion` / tag it "
               "`[informational]` if it should not be tracked."])
    else:
        message = "All trackable CONTEXT.md decisions are covered by plans."
    output_like_binary(
        {"passed": not uncovered, "skipped": False, "total": len(decisions),
         "covered": covered, "uncovered": uncovered, "message": message},
        raw)
    return EXIT_OK


def handle_check_ui_plan_gate(rest):
    """computeUiPlanGate (check-command-router.cts L509-L580): frontend ×
    UI-SPEC no diretório da fase; block = frontend sem spec."""
    pos, flags = parse_verb_args(rest)
    raw = bool(flags.get("--raw"))
    phase = pos[0] if pos else ""
    if not phase:
        die("ui-plan-gate requires a phase argument: check ui-plan-gate "
            "<phase>", EXIT_CONTRACT)
    root = find_project_root(Path.cwd())
    section, lookup_failed = "", False
    text = read_text(root / ".planning" / "ROADMAP.md")
    if text is not None and str(phase).isdigit():
        lines = text.split("\n")
        start = level = None
        for i, ln in enumerate(lines):
            m = re.match(r"^(#{1,6})\s+Phase\s+0*(\d+)\b", ln)
            if m and int(m.group(2)) == int(phase):
                start, level = i, len(m.group(1))
                break
        if start is None:
            lookup_failed = True
        else:
            end = len(lines)
            for j in range(start + 1, len(lines)):
                m = re.match(r"^(#{1,6})\s", lines[j])
                if m and len(m.group(1)) <= level:
                    end = j
                    break
            section = "\n".join(lines[start:end])
    frontend = check_ui_presence(section)
    phases_root = root / ".planning" / "phases"
    phase_dir = None
    if phases_root.is_dir():
        for d in sorted(phases_root.iterdir()):
            if not d.is_dir():
                continue
            m = PHASE_DIR_PREFIX.match(d.name)
            if str(phase).isdigit():
                if m and int(m.group(1)) == int(phase):
                    phase_dir = d
                    break
            elif str(phase).lower() in d.name.lower():
                phase_dir = d
                break
    ui_spec = None
    if phase_dir is not None:
        specs = sorted(f.name for f in phase_dir.iterdir()
                       if f.is_file() and f.name.endswith("UI-SPEC.md"))
        if specs:
            ui_spec = str(phase_dir / specs[0])
    has_spec = ui_spec is not None
    result = {"frontend": frontend, "hasUiSpec": has_spec,
              "block": frontend and not has_spec,
              "uiSpecPath": ui_spec if has_spec else None}
    if lookup_failed:
        result["phaseLookupFailed"] = True
    output_like_binary(result, raw)
    return EXIT_OK


CHECK_SUBCOMMANDS = ("api-coverage-verify-pre", "auto-mode",
                     "decision-coverage-plan", "decision-coverage-verify",
                     "gap-analysis-plan-post", "predicate",
                     "prohibition-enforcement", "tdd-review-checkpoint",
                     "ui-plan-gate", "ui-safety-gate", "verify-schema-drift",
                     "verify-codebase-drift")


def handle_check(rest):
    """Dispatcher de gates: pontos→hifens no subcommand, 12 rotas."""
    raw = "--raw" in rest
    sub = rest[0] if rest else None
    if isinstance(sub, str):
        sub = sub.replace(".", "-")
    tail = rest[1:]
    if sub == "auto-mode":
        return handle_check_auto_mode(raw)
    if sub == "decision-coverage-plan":
        return handle_check_decision_coverage_plan(tail)
    if sub == "ui-plan-gate":
        return handle_check_ui_plan_gate(tail)
    if sub == "verify-schema-drift":
        if os.environ.get("GSD_SKIP_SCHEMA_CHECK") == "true":
            output_like_binary({"skipped": True,
                                "reason": "GSD_SKIP_SCHEMA_CHECK"}, raw)
            return EXIT_OK
        return _verify_unavailable("schema-drift", raw)
    if sub == "verify-codebase-drift":
        return handle_verify_codebase_drift(tail)
    if sub == "predicate":
        return handle_check_predicate(tail)
    if sub in ("api-coverage-verify-pre", "decision-coverage-verify",
               "gap-analysis-plan-post", "prohibition-enforcement",
               "tdd-review-checkpoint", "ui-safety-gate"):
        # sem sítio no universo da 31 — indisponibilidade declarada (34-05)
        output_like_binary(
            {"available": False,
             "reason": (f"check {sub}: subcommand sem sítio no universo da "
                        "fase 31 — superfície não observada, indisponível "
                        "por declaração (divergences.json, family "
                        "checagem)")}, raw)
        return EXIT_OK
    die("Unknown check subcommand. Available: " + ", ".join(
        CHECK_SUBCOMMANDS), EXIT_CONTRACT)


# --- predicado ADR-2008 (gate-predicate-evaluator.cts, port integral) -------
def _eval_command_exit_zero(pred, ctx):
    command = pred.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ValueError('command-exit-zero predicate requires a non-empty '
                         'string "command"')
    if len(command) > 4096:
        raise ValueError('command-exit-zero predicate "command" exceeds '
                         'max length 4096')
    timeout_ms = 30000
    raw_t = pred.get("timeout")
    if raw_t is not None:
        bad = (isinstance(raw_t, bool)
               or not isinstance(raw_t, (int, float))
               or raw_t != raw_t or raw_t in (float("inf"), float("-inf"))
               or raw_t <= 0)
        if bad:
            raise ValueError('command-exit-zero predicate "timeout" must '
                             'be a positive finite number (seconds)')
        timeout_ms = int(raw_t * 1000)
    subst = {"PHASE_NUMBER": ctx.get("phaseNumber") or "",
             "PHASE_DIR": ctx.get("phaseDir") or "",
             "PHASE_REQ_IDS": ctx.get("phaseReqIds") or ""}
    interpolated = re.sub(r"\$\{(PHASE_NUMBER|PHASE_DIR|PHASE_REQ_IDS)\}",
                          lambda m: subst[m.group(1)], command)
    res = _run_bounded_shell(interpolated, ctx["cwd"], timeout_ms)
    if res["timedOut"]:
        return {"block": True,
                "message": _trim_2000(
                    f"command timed out after {round(timeout_ms / 1000)}s: "
                    f"{res['stderr'] or interpolated}"),
                "details": {"kind": "command-exit-zero", "timedOut": True,
                            "signal": res["signal"]}}
    if res["exitCode"] == 0:
        return {"block": False, "message": "command exited 0",
                "details": {"kind": "command-exit-zero", "exitCode": 0}}
    code = "<none>" if res["exitCode"] is None else str(res["exitCode"])
    tail = _trim_2000(res["stderr"] or res["stdout"] or "")
    message = f"command exited {code}: {tail}" if tail \
        else f"command exited {code}"
    return {"block": True, "message": _trim_2000(message),
            "details": {"kind": "command-exit-zero",
                        "exitCode": res["exitCode"],
                        "signal": res["signal"]}}


def _pred_str(v):
    return json.dumps(v, ensure_ascii=False) if isinstance(
        v, (dict, list)) else js_string(v)


def _eval_artifact_fm_equals(pred, ctx):
    suffix = pred.get("artifact")
    if not isinstance(suffix, str) or not suffix.strip():
        raise ValueError('artifact-frontmatter-equals predicate requires a '
                         'non-empty string "artifact"')
    field = pred.get("field")
    if not isinstance(field, str) or not field.strip():
        raise ValueError('artifact-frontmatter-equals predicate requires a '
                         'non-empty string "field"')
    if "equals" not in pred:
        raise ValueError('artifact-frontmatter-equals predicate requires '
                         'an "equals" key')
    expected = pred["equals"]
    phase_dir = ctx.get("phaseDir")
    target_dir = (phase_dir if isinstance(phase_dir, str)
                  and phase_dir.strip() else ctx["cwd"])
    fp = _find_phase_artifact(target_dir, suffix)
    if not fp:
        return {"block": True,
                "message": f"Artifact matching {suffix} not found in "
                           f"{target_dir}",
                "details": {"kind": "artifact-frontmatter-equals",
                            "artifactNotFound": True}}
    fm, _span = parse_frontmatter_lines(read_text(fp) or "")
    actual = fm.get(field)
    expected_str = _pred_str(expected)
    actual_str = ("undefined" if actual is None else _pred_str(actual))
    matches = actual == expected or (actual is not None
                                     and actual_str == expected_str)
    if matches:
        return {"block": False,
                "message": f'Frontmatter field "{field}" matches expected '
                           f"value ({expected_str})",
                "details": {"kind": "artifact-frontmatter-equals",
                            "match": True}}
    return {"block": True,
            "message": f'Frontmatter field "{field}" in {suffix} is '
                       f"{actual_str}, expected {expected_str}",
            "details": {"kind": "artifact-frontmatter-equals",
                        "match": False, "actual": actual,
                        "expected": expected}}


def _evaluate_predicate(predicate, ctx):
    """evaluatePredicate (gate-predicate-evaluator.cts L224-L256): dispatch
    por kind; malformado/desconhecido LEVANTA — o wrapper vira exit 1."""
    if not isinstance(predicate, dict):
        raise ValueError("predicate must be an object")
    kind = predicate.get("kind")
    if not isinstance(kind, str) or not kind:
        raise ValueError("predicate.kind must be a non-empty string")
    if kind == "command-exit-zero":
        return _eval_command_exit_zero(predicate, ctx)
    if kind == "artifact-frontmatter-equals":
        return _eval_artifact_fm_equals(predicate, ctx)
    raise ValueError(f'Unknown predicate kind: "{kind}". Known kinds: '
                     "command-exit-zero, artifact-frontmatter-equals")


def handle_check_predicate(rest):
    """check predicate (#2008): avaliador genérico de --flag value pairs;
    diferencial CHECK-02 provado por goldens recorded do binário real."""
    raw = "--raw" in rest
    flags = _parse_predicate_flags(rest)
    pj = flags.get("predicate")
    if not pj:
        die("predicate requires --predicate <json> (the gate hook "
            "check.predicate object)", EXIT_CONTRACT)
    try:
        predicate = json.loads(pj)
    except json.JSONDecodeError:
        die("predicate --predicate value must be valid JSON", EXIT_CONTRACT)
    ctx = {"cwd": str(Path.cwd()),
           "phaseNumber": flags.get("phase-number"),
           "phaseDir": flags.get("phase-dir"),
           "phaseReqIds": flags.get("phase-req-ids")}
    try:
        result = _evaluate_predicate(predicate, ctx)
    except ValueError as e:
        die(f"gate predicate evaluation failed: {e}", EXIT_CONTRACT)
    output_like_binary(result, raw)
    return EXIT_OK


# --------------------------------------------------------------------------- #
# user-story.validate — validação de string pura (CHECK-01)
# --------------------------------------------------------------------------- #
def handle_user_story_validate(rest):
    """Port de routeUserStory validate (gsd-tools.cjs L3179-L3230): guards
    por cláusula ANTES da regex cheia — a ordem é a semântica; zero
    filesystem, zero .planning/. História inválida sai 0 com valid false."""
    raw = "--raw" in rest
    story = ""
    if "--story" in rest:
        idx = rest.index("--story")
        if idx + 1 < len(rest) and not rest[idx + 1].startswith("--"):
            story = rest[idx + 1]
    errors = []
    trimmed = story.strip()
    slots = None
    if not trimmed:
        errors.append('Story is empty. Required format: "As a [role], '
                      'I want to [capability], so that [outcome]."')
    else:
        if not re.match(r"^As a \S", trimmed, re.I):
            errors.append('Story must start with "As a [user role]," '
                          "(role must be non-empty).")
        if not re.search(r", I want to \S", trimmed, re.I):
            errors.append('Story must include ", I want to [capability]," '
                          "(capability must be non-empty).")
        if not re.search(r", so that \S", trimmed, re.I):
            errors.append('Story must include ", so that [outcome]." '
                          "(outcome must be non-empty).")
        if not trimmed.endswith("."):
            errors.append("Story must end with a period (.).")
        if not errors:
            m = re.match(r"^As a (\S.*?), I want to (\S.*?), "
                         r"so that (\S.*?)\.$", trimmed)
            if not m:
                errors.append("Story does not match the canonical format: "
                              '"As a [role], I want to [capability], '
                              'so that [outcome]."')
            else:
                slots = {"role": m.group(1), "capability": m.group(2),
                         "outcome": m.group(3)}
    output_like_binary({"valid": not errors, "errors": errors,
                        "slots": slots}, raw)
    return EXIT_OK


# --------------------------------------------------------------------------- #
# uat.render-checkpoint + uat.classify-coverage — leitores de UAT/SUMMARY
# --------------------------------------------------------------------------- #
def _safe_rel_path(p, label):
    """requireSafePath compacto: NUL e traversal morrem nomeados."""
    if "\0" in p:
        die(f"{label}: path contém null bytes", EXIT_CONTRACT)
    if ".." in Path(p).parts:
        die(f"Invalid {label} path: path traversal", EXIT_CONTRACT)
    return Path(p) if os.path.isabs(p) else Path.cwd() / p


def handle_uat_render_checkpoint(rest):
    """cmdRenderCheckpoint (src/uat.cts L235-L261) + parseCurrentTest
    (L266-L324, forma leniente da casa): renderiza o bloco do teste
    corrente no response_language do config; sessão completa = erro."""
    _, flags = parse_verb_args(rest, value_flags=("--file",))
    raw = bool(flags.get("--raw"))
    fpath = flags.get("--file")
    if not fpath:
        die("UAT file required: use uat render-checkpoint --file <path>",
            EXIT_CONTRACT)
    full = _safe_rel_path(fpath, "UAT file")
    content = read_text(full)
    if content is None:
        die(f"UAT file not found: {fpath}", EXIT_CONTRACT)
    body = collect_heading_section(content,
                                   re.compile(r"^current\s+test$", re.I))
    if body is None:
        die("UAT file is missing a Current Test section", EXIT_CONTRACT)
    section = re.sub(r"^<!--[\s\S]*?-->\s*\n?", "", body).rstrip()
    if not section.strip():
        die("Current Test section is empty", EXIT_CONTRACT)
    if re.search(r"\[testing complete\]", section, re.I):
        die("UAT session is already complete; no pending checkpoint to "
            "render", EXIT_CONTRACT)
    num_m = re.search(r"^number:\s*(\d+)\s*$", section, re.M)
    name_m = re.search(r"^name:\s*(.+?)\s*$", section, re.M)
    blk_m = (re.search(r"^expected:\s*\|\n([\s\S]*?)(?=^\w[\w-]*:\s)",
                       section, re.M)
             or re.search(r"^expected:\s*\|\n([\s\S]+)", section, re.M))
    inl_m = re.search(r"^expected:\s*(.+?)\s*$", section, re.M)
    if not num_m or not name_m or (not blk_m and not inl_m):
        # sem o fallback parseFirstPendingTest da tag — distância declarada
        die("Current Test section is malformed", EXIT_CONTRACT)
    if blk_m:
        expected = "\n".join(re.sub(r"^ {2}", "", ln)
                             for ln in blk_m.group(1).split("\n")).strip()
    else:
        expected = inl_m.group(1).strip()
    cfg_text = read_text(Path.cwd() / ".planning" / "config.json")
    lang = None
    if cfg_text:
        try:
            cfg = json.loads(cfg_text)
            if isinstance(cfg, dict) and isinstance(
                    cfg.get("response_language"), str):
                lang = cfg["response_language"]
        except (json.JSONDecodeError, ValueError):
            lang = None
    number = int(num_m.group(1))
    name = name_m.group(1).strip()
    checkpoint = build_checkpoint(number, name, expected, lang)
    try:
        rel = full.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        rel = str(full)
    output_like_binary({"file_path": rel, "test_number": number,
                        "test_name": name, "checkpoint": checkpoint},
                       raw, checkpoint)
    return EXIT_OK


def handle_uat_classify_coverage(rest):
    """cmdClassify + classifyContent (src/coverage.cts L426-L491, #1602):
    auto_passed é o caso estreito totalmente provado; o resto vai a
    humano (fail-safe); mode distingue coverage/legacy."""
    _, flags = parse_verb_args(rest, value_flags=("--summary", "--file"))
    raw = bool(flags.get("--raw"))
    fpath = flags.get("--summary") or flags.get("--file")
    if not fpath:
        die("SUMMARY file required: use uat classify-coverage --summary "
            "<path>", EXIT_CONTRACT)
    full = _safe_rel_path(fpath, "SUMMARY file")
    content = read_text(full)
    if content is None:
        die(f"SUMMARY file not found: {fpath}", EXIT_CONTRACT)
    try:
        rel = full.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        rel = str(full)
    found, entries, malformed = parse_coverage(content)

    def legacy(errors):
        return {"mode": "legacy", "summary_file": rel, "total": 0,
                "all_auto_covered": False, "auto_passed": [],
                "present": [], "errors": errors}

    if not found:
        output_like_binary(legacy([]), raw)
        return EXIT_OK
    if malformed:
        output_like_binary(legacy([{
            "index": -1, "id": None, "code": "malformed_block",
            "message": "coverage block is present but could not be parsed "
                       "into entries; falling back to prose extraction"}]),
            raw)
        return EXIT_OK
    seen_ids = set()
    auto_passed, present, all_errors = [], [], []
    for index, entry in enumerate(entries):
        errs = _cov_validate_entry(entry, index, seen_ids)
        all_errors.extend(errs)
        view = _cov_entry_view(entry)
        vlist = (entry.get("verification")
                 if isinstance(entry, dict)
                 and isinstance(entry.get("verification"), list) else [])
        auto = (not errs and isinstance(entry, dict)
                and entry.get("human_judgment") is False and vlist
                and all(isinstance(ve, dict) and ve.get("status") == "pass"
                        for ve in vlist))
        if auto:
            view["source"] = "automated"
            auto_passed.append(view)
        else:
            if errs:
                reason = "validation_failed"
            elif isinstance(entry, dict) \
                    and entry.get("human_judgment") is True:
                reason = "human_judgment"
            elif not vlist:
                reason = "no_verification"
            else:
                reason = "verification_not_passing"
            view["reason"] = reason
            present.append(view)
    output_like_binary(
        {"mode": "coverage", "summary_file": rel, "total": len(entries),
         "all_auto_covered": not present, "auto_passed": auto_passed,
         "present": present, "errors": all_errors}, raw)
    return EXIT_OK


# --------------------------------------------------------------------------- #
# os 5 ex-órfãos de CHECK-03 (misc.json, semântica REM-04 com proveniência)
# --------------------------------------------------------------------------- #
_QUOTA_SENTINELS = ("429", "usage_limit_reached", "usage limit",
                    "rate limit", "rate-limited", "rate_limit",
                    "resource_exhausted", "quota", "too many requests",
                    "exceeded your")
_HANDOFF_SENTINEL = "classifyhandoffifneeded is not defined"


def handle_agent_classify_failure(rest):
    """classifyAgentFailure (src/agent-command-router.cts L40-L113, #2296):
    tokens '--' filtrados, resto unido por espaço; AGENT_FAILURE_CLASSES."""
    raw = "--raw" in rest
    body = " ".join(a for a in rest if a not in ("--", "--raw"))
    normalized = body.lower()
    result = None
    if normalized.strip():
        for s in _QUOTA_SENTINELS:
            if s in normalized:
                result = {"class": "quota-exceeded", "sentinel": s}
                m = re.search(r"\bretry[-_ ]after[:\s]+(\d+)\b", body, re.I)
                if m:
                    result["retryAfterSeconds"] = int(m.group(1))
                break
        if result is None and _HANDOFF_SENTINEL in normalized:
            result = {"class": "classify-handoff-bug",
                      "sentinel": _HANDOFF_SENTINEL}
    if result is None:
        result = {"class": "unknown-failure"}
    output_like_binary(result, raw)
    return EXIT_OK


def handle_audit_open(rest):
    """auditOpenArtifacts + formatAuditReport (src/audit.cts L157-L950):
    varre os tipos de artefato aberto do .planning/; --json emite o
    AuditResult; audit-open não tem subcommands — token extra é exit 1."""
    pos, flags = parse_verb_args(rest, bool_flags=("--raw", "--json"))
    if pos:
        die(f"Unknown audit-open subcommand: {pos[0]} — audit-open não tem "
            "subcommands", EXIT_CONTRACT)
    raw = bool(flags.get("--raw"))
    plan_dir = Path.cwd() / ".planning"
    items, counts = {}, {}
    for key, scanner in AUDIT_SCANNERS:
        try:
            arr = scanner(plan_dir)
        except OSError:
            arr = [{"scan_error": True}]
        items[key] = arr
        counts[key] = sum(1 for i in arr if not i.get("scan_error")
                          and not i.get("_remainder_count"))
    counts["total"] = sum(counts[k] for k, _s in AUDIT_SCANNERS)
    now = datetime.datetime.now(datetime.timezone.utc)
    result = {
        "scanned_at": (now.strftime("%Y-%m-%dT%H:%M:%S.")
                       + f"{now.microsecond // 1000:03d}Z"),
        "has_open_items": counts["total"] > 0,
        "counts": counts,
        "items": items,
    }
    if flags.get("--json"):
        output_like_binary(result, raw)
    else:
        emit(format_audit_report(result))
    return EXIT_OK


def handle_task_is_behavior_adding(rest):
    """isBehaviorAddingTaskContent (src/task-command-router.cts L37-L111):
    o predicado do gate MVP+TDD — tdd=true + <behavior> + fonte não-teste;
    path fora do escopo/inexistente = exit 1 USAGE."""
    raw = "--raw" in rest
    content = None
    if rest and rest[0] == "--task-content":
        content = rest[1] if len(rest) > 1 else None
    elif rest and not rest[0].startswith("-"):
        requested = rest[0]
        project_root = Path.cwd().resolve()
        resolved = (Path(requested) if os.path.isabs(requested)
                    else project_root / requested).resolve()
        try:
            resolved.relative_to(project_root)
        except ValueError:
            die(f"Task file is outside project scope: {requested}",
                EXIT_CONTRACT)
        if not resolved.exists():
            die(f"Task file not found: {requested}", EXIT_CONTRACT)
        content = read_text(resolved)
    if not content:
        die('Usage: task.is-behavior-adding <plan-file-path> | '
            '--task-content "<xml>"', EXIT_CONTRACT)
    tdd_true = bool(re.search(r"\btdd\s*=\s*[\"']true[\"']", content, re.I))
    bm = re.search(r"<behavior>([\s\S]*?)</behavior>", content, re.I)
    has_behavior = bool(bm and bm.group(1).strip())
    fm2 = re.search(r"<files>([\s\S]*?)</files>", content, re.I)
    has_source = False
    if fm2:
        for line in re.split(r"[\n,]", fm2.group(1)):
            f = re.sub(r"^[-*]\s*", "", line.strip())
            if not f:
                continue
            if (not re.search(r"\.md$", f, re.I)
                    and not re.search(r"\.json$", f, re.I)
                    and not re.search(r"\.test\.[^.]+$", f, re.I)
                    and not re.search(r"\.spec\.[^.]+$", f, re.I)
                    and not re.search(r"(^|[\\/])tests?[\\/]", f, re.I)
                    and not re.search(
                        r"\.(yml|yaml|toml|ini|cfg|conf|properties)$",
                        f, re.I)
                    and not re.search(r"(^|[\\/])\.env(\..+)?$", f, re.I)):
                has_source = True
                break
    is_adding = tdd_true and has_behavior and has_source
    missing = []
    if not tdd_true:
        missing.append('tdd="true" frontmatter absent')
    if not has_behavior:
        missing.append("<behavior> block missing or empty")
    if not has_source:
        missing.append("<files> has no non-test source file")
    output_like_binary(
        {"is_behavior_adding": is_adding,
         "checks": {"tdd_true": tdd_true,
                    "has_behavior_block": has_behavior,
                    "has_source_files": has_source},
         "reason": None if is_adding
         else "Not behavior-adding: " + "; ".join(missing)}, raw)
    return EXIT_OK


def handle_review_lane(rest):
    """routeReviewLane (gsd-tools.cjs L1178+, ADR-2782): flags e sections
    emitem TEXTO linha a linha (kind text, fora do envelope); plan/invoke
    declaram indisponibilidade — a casa não instala capabilities de
    reviewer nem invoca CLIs headless (divergences.json)."""
    sub = rest[0] if rest else None
    if sub not in ("plan", "invoke", "sections", "flags"):
        die("Usage: review-lane <plan|invoke|sections|flags> "
            "[--selected a,b] [--run-dir D] [--repo-root R]", EXIT_CONTRACT)
    raw = "--raw" in rest
    _, flags = parse_verb_args(rest, value_flags=(
        "--selected", "--run-dir", "--repo-root"))
    selected = [s.strip() for s in (flags.get("--selected") or "").split(",")
                if s.strip()]
    by_slug = {slug: (fl, sec) for slug, fl, sec in REVIEWER_LANES}
    chosen = selected or [s for s, _f, _sec in REVIEWER_LANES]
    if sub == "sections":
        rows = [f"{s}\t{by_slug[s][1]}" for s in chosen if s in by_slug]
        emit("\n".join(rows) + ("\n" if rows else ""))
        return EXIT_OK
    if sub == "flags":
        rows = [f for s in chosen if s in by_slug for f in by_slug[s][0]
                if re.fullmatch(r"--[a-z0-9][a-z0-9-]*", f)]
        emit("\n".join(rows) + ("\n" if rows else ""))
        return EXIT_OK
    output_like_binary(
        {"available": False,
         "reason": (f"review-lane {sub}: resolução/execução de reviewers "
                    "sem sítio no universo da fase 31 — a casa não instala "
                    "capabilities de reviewer nem invoca CLIs headless; "
                    "indisponibilidade declarada (divergences.json)")}, raw)
    return EXIT_OK


def handle_run_with_timeout(rest):
    """run-with-timeout (#2351, gsd-tools.cjs L3452-L3590): a EXCEÇÃO da
    doutrina de subprocess da casa — Popen SEM capture (stdio herdado),
    process group próprio, SIGTERM→SIGKILL 3s no estouro (exit 124),
    SIGINT/SIGTERM encaminhados; tabela GNU-timeout (125/126/127/128+n);
    <seconds> com sufixo 's', 0 = sem timer, inválido = usage 2 fail-safe;
    argv do comando OPACO. Caminho Win32 (.cmd/.bat) não se aplica à casa
    (divergência declarada)."""
    if not rest:
        die("usage: run-with-timeout <seconds> [--] <command> [args...]",
            EXIT_USAGE)
    raw_secs = str(rest[0]).strip()
    cmd = list(rest[1:])
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    m = re.fullmatch(r"(\d+(?:\.\d+)?)s?", raw_secs)
    if not m:
        die(f"run-with-timeout: <seconds> inválido: {raw_secs!r} — vazio, "
            "negativo ou não numérico é usage (fail-safe, nunca unbounded)",
            EXIT_USAGE)
    seconds = float(m.group(1))
    if not cmd:
        die("run-with-timeout: comando ausente", EXIT_USAGE)
    try:
        proc = subprocess.Popen(cmd, start_new_session=True)
    except FileNotFoundError:
        sys.exit(127)
    except PermissionError:
        sys.exit(126)
    except (OSError, subprocess.SubprocessError):
        sys.exit(125)

    def forward(signum, _frame):
        try:
            os.killpg(proc.pid, signum)
        except OSError:
            pass

    old_int = signal.signal(signal.SIGINT, forward)
    old_term = signal.signal(signal.SIGTERM, forward)
    timed_out = False
    try:
        proc.wait(timeout=seconds if seconds > 0 else None)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            proc.wait()
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
    if timed_out:
        sys.exit(124)
    rc = proc.returncode
    sys.exit(128 - rc if rc < 0 else rc)


# --------------------------------------------------------------------------- #
# main — recebe o verbo canônico já resolvido pelo dispatcher
# --------------------------------------------------------------------------- #
HANDLERS = {
    "agent.classify-failure": handle_agent_classify_failure,
    "audit-open": handle_audit_open,
    "review-lane": handle_review_lane,
    "run-with-timeout": handle_run_with_timeout,
    "check": handle_check,
    "check.decision-coverage-plan": handle_check_decision_coverage_plan,
    "task.is-behavior-adding": handle_task_is_behavior_adding,
    "uat.classify-coverage": handle_uat_classify_coverage,
    "uat.render-checkpoint": handle_uat_render_checkpoint,
    "user-story.validate": handle_user_story_validate,
    "verification.status": handle_verification_status,
    "verify": handle_verify,
    "verify.artifacts": handle_verify_artifacts,
    "verify.commits": handle_verify_commits,
    "verify.key-links": handle_verify_key_links,
    "verify.plan-structure": handle_verify_plan_structure,
}


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
        die("usage: cairn-gsd-check.py <verbo> [argv]", EXIT_USAGE)
    if argv[0] == "--list-implemented":
        for verb in sorted(HANDLERS):
            print(verb)
        sys.exit(EXIT_OK)
    verb = argv[0]
    handler = HANDLERS.get(verb)
    if handler is None:
        die(f"verbo '{verb}' da família '{family_of(verb)}' é entregue pela "
            "fase 35 — ainda não implementado neste script",
            EXIT_UNIMPLEMENTED)
    sys.exit(handler(argv[1:]))


if __name__ == "__main__":
    main()
