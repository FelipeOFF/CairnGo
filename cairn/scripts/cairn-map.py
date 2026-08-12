#!/usr/bin/env python3
"""cairn-map — regenerate a phase's NN-BEADS-MAP.md view of bd state.

NN-BEADS-MAP.md is a GENERATED view of the beads tracker: everything between
the <!-- cairn:generated:start --> / <!-- cairn:generated:end --> markers is
owned by this script. Human notes outside the markers survive regeneration;
a pre-existing file without markers gets the block appended, never destroyed.

Usage:
    cairn-map.py <phase-number> [--milestone <m>] [--planning-dir <dir>]
                 [--check] [--json]

Behavior:
    1. Resolve the phase dir under <planning-dir>/phases/ by numeric prefix
       ('3' and '03' both match 03-auth; an optional project-code prefix like
       myproj-03-auth is tolerated — the same matching semantics documented
       in commands/plan.md). Default planning dir: $CLAUDE_PROJECT_DIR (or
       cwd) + /.planning.
    2. Query bd: bd -C <planning-dir's parent> list -l
       phase-<N>[,m-<milestone>] --all --limit 0 --json (open AND closed
       issues, pinned to the planning dir's own repo, never the cwd's).
       When --milestone is omitted it is inferred
       from the phase issues' m-* labels: a single shared label is used, no
       m-* labels at all (legacy repo) drops the milestone filter, and mixed
       labels are an error asking for an explicit --milestone.
    3. Rebuild the marker block: a requirement table (rows keyed by each
       issue's metadata.gsd.req), a gap list for issues without a
       requirement, and a gap list for phase requirements (parsed from
       ROADMAP.md's '**Requirements**:' line) that have no issue. A missing
       ROADMAP file/section skips that last list with a note.
    4. Write <phase-dir>/<NN>-BEADS-MAP.md (NN = zero-padded phase number),
       replacing ONLY the marker block and preserving everything outside it.

    --check  write nothing; exit 0 when the marker content is already
             current, exit 3 with a unified diff when it is stale.
    --json   print a machine summary on stdout:
             {phase, milestone, rows, gaps, file, changed}

Exit codes:
    0 ok    2 usage / ambiguous milestone    3 stale (--check only)
    4 phase dir not found                    5 bd unavailable
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cairn_source  # noqa: E402

HEADER_LINE = "A view of bd, printed on demand — nothing here is stored"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_PHASE = 4
EXIT_NO_BD = 5

USAGE = ("usage: cairn-map.py <phase-number> [--milestone <m>] "
         "[--planning-dir <dir>] [--check] [--json]")

REQ_ID = re.compile(r"[A-Za-z][A-Za-z0-9]*-\d+")


def die(msg, code):
    print(f"[cairn-map] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    opts = {"phase": None, "milestone": None, "planning_dir": None,
            "json": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--milestone":
            if i + 1 >= len(argv):
                die(f"--milestone needs a value\n{USAGE}", EXIT_USAGE)
            opts["milestone"] = argv[i + 1]
            i += 2
        elif arg == "--planning-dir":
            if i + 1 >= len(argv):
                die(f"--planning-dir needs a value\n{USAGE}", EXIT_USAGE)
            opts["planning_dir"] = argv[i + 1]
            i += 2
        elif arg == "--check":
            die("--check compared a generated file against bd, and the "
                "generated file is gone (v1.7): the map is printed from bd "
                "on demand, so it can never be stale. Drop the flag.",
                EXIT_USAGE)
        elif arg == "--json":
            opts["json"] = True
            i += 1
        elif arg.startswith("-"):
            die(f"unknown option '{arg}'\n{USAGE}", EXIT_USAGE)
        elif opts["phase"] is None:
            opts["phase"] = arg
            i += 1
        else:
            die(f"unexpected argument '{arg}'\n{USAGE}", EXIT_USAGE)
    if opts["phase"] is None:
        die(f"missing <phase-number>\n{USAGE}", EXIT_USAGE)
    if not re.fullmatch(r"\d+", opts["phase"]):
        die(f"phase must be a number, got '{opts['phase']}'\n{USAGE}",
            EXIT_USAGE)
    opts["phase_num"] = int(opts["phase"], 10)
    return opts


def bd_list(labels, root):
    """bd -C <root> list -l <labels-ANDed> --all (open and closed), parsed
    JSON. root pins the query to the planning dir's repo — without it, a
    --planning-dir pointed at another checkout would render THIS repo's
    issues into the other repo's map (cairn-gate and cairn-doctor pass
    -C the same way)."""
    if shutil.which("bd") is None:
        die("'bd' not found on PATH", EXIT_NO_BD)
    cmd = ["bd", "-C", str(root), "list", "-l", ",".join(labels),
           "--all", "--limit", "0", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"bd list failed: {proc.stderr.strip()}", EXIT_NO_BD)
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        die(f"bd list returned invalid JSON: {e}", EXIT_NO_BD)
    return data if isinstance(data, list) else [data]


def infer_milestone(issues):
    """Milestone shared by every phase issue's m-* label, or None (legacy
    repo without m-* labels). Mixed or multiple labels are an error."""
    per_issue = [[l for l in (iss.get("labels") or []) if l.startswith("m-")]
                 for iss in issues]
    if not per_issue or all(not m for m in per_issue):
        return None
    if all(len(m) == 1 for m in per_issue):
        names = {m[0][2:] for m in per_issue}
        if len(names) == 1:
            return names.pop()
    found = sorted({l for m in per_issue for l in m})
    die("phase issues carry mixed milestone labels "
        f"({', '.join(found) or 'some without any m-* label'}) — "
        "pass --milestone to pick one", EXIT_USAGE)


def phase_requirements(root, n):
    """Os requisitos da fase, DERIVADOS DO BD (v1.7).

    Liam-se da linha `**Requirements**:` dentro da seção `### Phase n` do
    ROADMAP.md. O requisito É o bead — seu id é a metadata `gsd.req` — então
    a lista sai do próprio tracker que a coluna da direita da tabela já
    consultava. Devolve [] quando a fase não tem requisito estampado; a
    distinção entre "sem requisito" e "sem arquivo" morre junto com o
    arquivo.
    """
    return cairn_source.phase_reqs(root).get(cairn_source.as_number(n), [])


def gsd_req(issue):
    """metadata.gsd.req of a bd issue, or None when absent."""
    md = issue.get("metadata")
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except json.JSONDecodeError:
            md = None
    gsd = md.get("gsd") if isinstance(md, dict) else None
    req = gsd.get("req") if isinstance(gsd, dict) else None
    return req.strip() if isinstance(req, str) and req.strip() else None


def md_cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def build_inner(issues, roadmap_reqs):
    """The generated content between the markers.

    Returns (inner_text, row_count, unmapped_issue_count, missing_reqs)
    where missing_reqs is None when ROADMAP requirements were unavailable.
    """
    rows, unmapped = [], []
    for iss in issues:
        req = gsd_req(iss)
        (rows if req else unmapped).append((req, iss))
    rows.sort(key=lambda r: (r[0], r[1].get("id", "")))
    unmapped.sort(key=lambda r: r[1].get("id", ""))

    lines = [HEADER_LINE, "",
             "| Requirement | Issue | Status | Title |",
             "|-------------|-------|--------|-------|"]
    for req, iss in rows:
        lines.append(f"| {md_cell(req)} | {md_cell(iss.get('id', '?'))} "
                     f"| {md_cell(iss.get('status', '?'))} "
                     f"| {md_cell(iss.get('title', ''))} |")

    if unmapped:
        lines += ["", "## Gaps — issues without a requirement", ""]
        for _, iss in unmapped:
            lines.append(f"- {iss.get('id', '?')} ({iss.get('status', '?')}) "
                         f"{md_cell(iss.get('title', ''))}")

    lines += ["", "## Gaps — requirements without an issue", ""]
    if roadmap_reqs is None:
        missing = None
        lines.append("Skipped — no '**Requirements**:' line found for this "
                     "phase in ROADMAP.md.")
    else:
        covered = {req for req, _ in rows}
        missing = sorted(r for r in set(roadmap_reqs) if r not in covered)
        if missing:
            lines += [f"- {r}" for r in missing]
        else:
            lines.append("None — every phase requirement is mapped to "
                         "an issue.")
    return "\n".join(lines), len(rows), len(unmapped), missing


def main():
    opts = parse_args(sys.argv[1:])
    n = opts["phase_num"]
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    root = Path(opts["planning_dir"]).resolve().parent \
        if opts["planning_dir"] else Path(project_dir).resolve()
    milestone = opts["milestone"]
    if milestone:
        issues = bd_list([f"phase-{n}", f"m-{milestone}"], root)
    else:
        issues = bd_list([f"phase-{n}"], root)
        milestone = infer_milestone(issues)

    inner, n_rows, n_unmapped, missing = build_inner(
        issues, phase_requirements(root, n))

    nn = f"{n:02d}"
    summary = {
        "phase": n,
        "milestone": milestone,
        "rows": n_rows,
        "gaps": {"issues_without_requirement": n_unmapped,
                 "requirements_without_issue":
                     len(missing) if missing is not None else None},
    }

    # v1.7 — A VISTA E' IMPRESSA, NAO ESCRITA.
    #
    # Ate aqui este script escrevia `<phase-dir>/NN-BEADS-MAP.md`: markdown
    # GERADO, com marcadores, splice do miolo, deteccao de marcador danificado
    # e uma checagem de frescor no doctor para o caso de a copia envelhecer.
    # Todo esse aparato existia por causa da COPIA, e a copia existia porque
    # nao havia outro jeito de olhar o bd. Ha: e' este comando.
    #
    # O que sai junto: o `--check` (frescor de uma copia que nao existe mais),
    # o `changed` e o `file` do resumo, e a exigencia de um diretorio de fase
    # em disco para pendurar o arquivo — uma fase e' um label, e nao precisa
    # de pasta. Quem quiser o arquivo redireciona a saida; essa e' decisao de
    # quem chama, nao do cairn.
    if opts["json"]:
        print(json.dumps(summary))
    else:
        print(f"# Phase {nn} — beads map")
        print()
        print(inner)
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
