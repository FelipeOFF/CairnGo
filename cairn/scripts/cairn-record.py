#!/usr/bin/env python3
"""cairn-record — a fronteira UNICA de escrita de registro de planejamento.

Substitui os 123 sitios de "Write <DOC>.md" da camada prompt por UMA chamada.
Grava FATO estruturado no bd e NUNCA escreve arquivo nenhum — nem markdown,
nem json, nem temporario. Esta e' a invariante que da nome ao milestone v1.7,
e ha caso de teste que a mede contando `*.md` na arvore antes e depois.

Usage:
    cairn-record.py <kind> --phase <N> [--plan <P>] [--issue <ID>]
                    [--milestone <M>] [--title <T>] [--project-dir <D>]
                    [--json]
    O CORPO DO REGISTRO VEM SEMPRE DE STDIN. Nao ha flag de corpo: um corpo
    em argv vaza para a lista de processos e trunca em prosa longa, que e'
    exatamente o material que este script existe para carregar.

Exit codes:
    0 ok                      1 fato ausente ou ambiguo (NOMEADO)
    2 uso                     4 kind desconhecido
    5 bd indisponivel

MEDIDO vs. ASSUMIDO
-------------------
MEDIDO (bd 1.1.0, 2026-08-12): `bd create` e `bd update` aceitam
--description, --design, --notes, --acceptance, --parent, --append-notes,
--body-file -, --design-file -, --metadata, --silent. Nada precisou ser
inventado; o desenho inteiro cabe nos campos que ja existem.

MEDIDO: os campos longos so aparecem em `bd show --json` quando nao-vazios, e
`--acceptance` na CLI le-se `acceptance_criteria` no JSON. As duas grafias
convivem porque sao de camadas diferentes (flag vs. payload), e o teste usa a
do JSON.

MEDIDO, E E' O QUE PARTE A FRONTEIRA EM DUAS: context-mode NAO tem CLI.
`command -v ctx ctx-mode context-mode` devolve vazio — os `ctx_*` sao tools
MCP, model-side. LOGO UM SCRIPT PYTHON NAO INDEXA, e nenhuma quantidade de
desenho aqui muda isso. A fronteira e' partida de proposito:

    - o SCRIPT (este) grava o FATO estruturado no bd — deterministico,
      testavel, e' o que a suite mede;
    - a CAMADA PROMPT chama `ctx_index` para a PROSA, sob o label
      `gb/{bd_id}/{phase}` da convencao cairn-context.

Registrado alto porque a alternativa — inventar um formato de arquivo para a
prosa — e' precisamente o que o milestone recusa, e um leitor futuro que nao
souber da ausencia de CLI vai propor essa alternativa de novo.

UM SUMMARY NAO E' UM REGISTRO NOVO
----------------------------------
E' o FECHO do registro que o PLAN abriu. Por isso `summary` nao cria bead: ele
poe o corpo em notes do bead do plano e o fecha. A contagem de beads NAO sobe
quando um summary e' gravado, e ha teste que compara antes/depois. Esta e' a
diferenca entre "o plano e o sumario sao dois arquivos" (o mundo que sai) e
"sao dois momentos do mesmo registro" (o mundo que entra).

QUEM E' O PORTADOR DA FASE
--------------------------
MEDIDO: `bd create --parent` faz o filho HERDAR os labels do pai (um filho de
um bead `phase-1` nasce `phase-1`). Logo "o bead com label phase-N" NAO
identifica o portador — depois do primeiro plano gravado ha dois, e depois de
tres planos ha quatro.

A PRIMEIRA REGRA ESCRITA AQUI FOI "o phase-N SEM PAI", E ELA NAO FUNCIONA.
MEDIDO (bd 1.1.0, 2026-08-12): o JSON do bd NAO tem chave `parent` — nem em
`list`, nem em `show`, nem no export `.beads/issues.jsonl`. As chaves sao
assignee, close_reason, closed_at, comment_count, created_at, created_by,
dependencies, dependency_count, dependent_count, description, id, issue_type,
labels, metadata, owner, priority, status, title, updated_at. Um filtro
`not i.get("parent")` e' portanto uma condicao SEMPRE-VERDADEIRA disfarcada
de filtro: ele nao eliminava ninguem, e este resolvedor devolvia "portador
ambiguo" em TODAS as 38 fases deste repositorio. A hierarquia existe e e'
visivel por outro caminho — o id do filho e' o do pai mais sufixo
(`CairnGo-9c0h` -> `CairnGo-9c0h.3`), e `bd list --parent <id>` filtra — mas
o campo nao viaja no JSON.

A REGRA QUE RESISTE E' A METADATA: um REQUISITO tem `gsd.req`, o portador da
fase NAO tem. Isso e' o que de fato distingue, e nao depende de campo ausente
nem de hierarquia.

E QUANDO NAO HA PORTADOR NENHUM. MEDIDO no mesmo dia: das 38 fases deste
repo, ZERO tem epico e quase nenhuma tem bead sem `gsd.req` — todo bead
`phase-N` daqui e' um requisito. "Existe um portador por fase" descrevia o
fixture, nao o repositorio. Entao a ausencia nao e' erro do usuario: e' o
estado normal de um projeto com historico, e o resolvedor CRIA o portador,
imprimindo o id que criou. CORE-04 proibe o fallback SILENCIOSO e o fallback
para markdown; criar o fato que falta e dizer em voz alta que criou nao e'
nenhum dos dois.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

EXIT_OK = 0
EXIT_CONTRACT = 1
EXIT_USAGE = 2
EXIT_UNKNOWN_KIND = 4
EXIT_NO_BD = 5

TAG_PREFIX = "[cairn-record]"

USAGE = ("usage: cairn-record.py <kind> --phase <N> [--plan <P>] "
         "[--issue <ID>] [--milestone <M>] [--title <T>] "
         "[--project-dir <D>] [--json]   (corpo sempre por stdin)")

# kind -> (alvo, campo do bd, modo)
#
# alvo:  "phase" o portador da fase | "plan" o registro de uma onda
# campo: a chave do JSON do bd onde o corpo aterrissa
# modo:  "create" abre registro | "close" fecha o registro aberto
#        "set" substitui o campo | "append" acrescenta sem apagar
#
# POR QUE OS SEIS DOCUMENTOS DE DESENHO COLAPSAM EM `design`. CONTEXT,
# RESEARCH, PATTERNS, SPEC, UI-SPEC e AI-SPEC sao, todos, a mesma pergunta
# ("o que se sabe antes de construir") feita por comandos diferentes. Dar um
# campo proprio a cada um exigiria seis campos que o bd nao tem, e a saida
# seria inventar formato — o que este milestone recusa. Eles compartilham
# `design` e se distinguem pelo kind no cabecalho do corpo.
KINDS = {
    "plan":         ("plan",  "description",         "create"),
    "summary":      ("plan",  "notes",               "close"),
    "context":      ("phase", "design",              "set"),
    "research":     ("phase", "design",              "set"),
    "patterns":     ("phase", "design",              "set"),
    "spec":         ("phase", "design",              "set"),
    "ui-spec":      ("phase", "design",              "set"),
    "ai-spec":      ("phase", "design",              "set"),
    "verification": ("phase", "acceptance_criteria", "set"),
    "review":       ("phase", "notes",               "append"),
    "log":          ("phase", "notes",               "append"),
}

# campo do JSON -> flag da CLI do bd (as duas grafias de acceptance)
FIELD_FLAG = {
    "description": "--description",
    "design": "--design",
    "notes": "--notes",
    "acceptance_criteria": "--acceptance",
}


def die(msg, code):
    """Falha NOMEADA: uma linha com prefixo, no stdout, e o exit contratado."""
    print("%s %s" % (TAG_PREFIX, msg))
    sys.exit(code)


def bd(args, root, check=True):
    """Roda bd fixado no repo do projeto, nunca no cwd de quem chamou."""
    cmd = ["bd", "-C", str(root)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        die("bd falhou: %s: %s" % (" ".join(args[:2]),
                                   (proc.stderr or proc.stdout).strip()),
            EXIT_CONTRACT)
    return proc


def bd_json(args, root):
    """Saida --json do bd como lista, tolerante a dict ou a ruido de warning."""
    proc = bd(args + ["--json"], root, check=False)
    out = (proc.stdout or "").strip()
    start = min([i for i in (out.find("["), out.find("{")) if i >= 0] or [-1])
    if start < 0:
        return []
    try:
        data = json.loads(out[start:])
    except ValueError:
        return []
    return data if isinstance(data, list) else [data]


def issue_req(issue):
    """O `gsd.req` do bead, ou None. Tolerante a metadata como string JSON."""
    meta = issue.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            return None
    gsd = (meta or {}).get("gsd") or {}
    return gsd.get("req") if isinstance(gsd, dict) else None


def phase_labels(phase, milestone):
    labels = "phase-%s" % phase
    if milestone:
        labels += ",m-%s" % milestone
    return labels


def infer_milestone(issues):
    """O m-<M> dos beads da fase, quando todos concordam. A convencao cairn e'
    o PAR m-<milestone> + phase-<N>: um portador criado so com phase-N nasceria
    fora dela, e nenhuma chamada da camada prompt passa --milestone."""
    ms = {l[2:] for i in issues for l in (i.get("labels") or [])
          if l.startswith("m-")}
    return ms.pop() if len(ms) == 1 else None


def create_phase_carrier(phase, milestone, root):
    """Cria o portador que falta, e NOMEIA o que criou (ver cabecalho)."""
    gsd = {"phase": phase}
    if milestone:
        gsd["milestone"] = milestone
    proc = bd(["create", "Phase %s" % phase, "--type", "epic",
               "--labels", phase_labels(phase, milestone),
               "--metadata", json.dumps({"gsd": gsd}), "--silent"], root)
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    new_id = lines[-1] if lines else ""
    if not new_id:
        die("bd create nao devolveu id ao criar o portador da fase %s" % phase,
            EXIT_CONTRACT)
    print("%s portador da fase %s nao existia — criado: %s"
          % (TAG_PREFIX, phase, new_id))
    return new_id


def is_child_id(issue_id):
    """O bd nao emite `parent`, mas a hierarquia esta VISIVEL no id: o filho e'
    o id do pai mais sufixo (`CairnGo-9c0h` -> `CairnGo-9c0h.3`). O ponto vem
    depois do prefixo do projeto, entao a busca comeca depois do primeiro `-`."""
    tail = issue_id.split("-", 1)[1] if "-" in issue_id else issue_id
    return "." in tail


def is_carrier(issue):
    """Portador = o bead da fase que nao e' nenhuma das tres outras coisas que
    carregam o mesmo label `phase-N`:

      - um REQUISITO, que tem `gsd.req`;
      - um REGISTRO DE PLANO, que tem `plan-NN` (e herda `phase-N` do pai —
        MEDIDO: `bd create --parent` herda os labels, e foi assim que o
        primeiro plano gravado passou a disputar a vaga de portador);
      - qualquer FILHO, cujo id carrega o sufixo do pai.

    As tres condicoes sao independentes: uma so nao basta, porque um filho
    pode nao ter req, e um plano pode ser criado sem passar por aqui."""
    labels = issue.get("labels") or []
    return (not issue_req(issue)
            and not any(l.startswith("plan-") for l in labels)
            and not is_child_id(issue.get("id", "")))


def resolve_phase_carrier(phase, milestone, root):
    """O bead `phase-N` que nao e' requisito, nem plano, nem filho. Ver o
    cabecalho para por que a metadata, e nao o campo `parent`, distingue."""
    issues = bd_json(["list", "-l", phase_labels(phase, milestone),
                      "--all", "--limit", "0"], root)
    carriers = [i for i in issues if is_carrier(i)]
    if len(carriers) > 1:
        ids = ", ".join(i["id"] for i in carriers)
        die("portador ambiguo para phase-%s: %s. Passe --issue <ID> para "
            "dizer em qual gravar." % (phase, ids), EXIT_CONTRACT)
    if carriers:
        return carriers[0]["id"]
    return create_phase_carrier(phase, milestone or infer_milestone(issues),
                                root)


def resolve_plan_record(phase, plan, milestone, root):
    """O bead de uma onda: label phase-N + plan-P. None quando ainda nao existe."""
    labels = "phase-%s,plan-%s" % (phase, plan)
    if milestone:
        labels += ",m-%s" % milestone
    issues = bd_json(["list", "-l", labels, "--all", "--limit", "0"], root)
    return issues[0]["id"] if issues else None


def main():
    parser = argparse.ArgumentParser(prog="cairn-record.py", add_help=True,
                                     usage=USAGE)
    parser.add_argument("kind", nargs="?")
    parser.add_argument("--phase")
    parser.add_argument("--plan")
    parser.add_argument("--issue")
    parser.add_argument("--milestone")
    parser.add_argument("--title")
    parser.add_argument("--project-dir")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if not args.kind:
        print(USAGE, file=sys.stderr)
        sys.exit(EXIT_USAGE)

    if args.kind not in KINDS:
        die("kind desconhecido: %s. Conhecidos: %s"
            % (args.kind, ", ".join(sorted(KINDS))), EXIT_UNKNOWN_KIND)

    target_kind, field, mode = KINDS[args.kind]

    if not args.issue and not args.phase:
        print("%s %s precisa de --phase <N> ou --issue <ID>"
              % (TAG_PREFIX, args.kind), file=sys.stderr)
        sys.exit(EXIT_USAGE)
    if target_kind == "plan" and not args.plan:
        print("%s kind '%s' precisa de --plan <P> (a onda que o registro "
              "abre ou fecha)" % (TAG_PREFIX, args.kind), file=sys.stderr)
        sys.exit(EXIT_USAGE)

    if shutil.which("bd") is None:
        die("bd nao esta no PATH — o registro mora no bd; instale beads "
            "(https://github.com/gastownhall/beads).", EXIT_NO_BD)

    root = os.path.abspath(args.project_dir
                           or os.environ.get("CLAUDE_PROJECT_DIR")
                           or os.getcwd())

    body = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    if not body:
        die("corpo vazio: o registro vem por stdin e nada chegou.",
            EXIT_USAGE)

    # --- resolucao do alvo ----------------------------------------------------
    if args.issue:
        issue = args.issue
    elif target_kind == "plan":
        issue = resolve_plan_record(args.phase, args.plan, args.milestone,
                                    root)
        if issue is None and mode != "create":
            die("nenhum registro de plano phase-%s/plan-%s — um summary FECHA "
                "o registro que o plan abriu, e este nao foi aberto. Grave o "
                "plan primeiro: `cairn-record.sh plan --phase %s --plan %s`."
                % (args.phase, args.plan, args.phase, args.plan),
                EXIT_CONTRACT)
    else:
        issue = resolve_phase_carrier(args.phase, args.milestone, root)

    # --- a escrita ------------------------------------------------------------
    if mode == "create" and issue is None:
        parent = args.issue or resolve_phase_carrier(args.phase,
                                                     args.milestone, root)
        labels = "phase-%s,plan-%s" % (args.phase, args.plan)
        if args.milestone:
            labels += ",m-%s" % args.milestone
        title = args.title or ("Phase %s plan %s" % (args.phase, args.plan))
        proc = bd(["create", title, "--parent", parent, "--labels", labels,
                   "--type", "task", "--description", body, "--silent"], root)
        lines = [ln.strip() for ln in (proc.stdout or "").splitlines()
                 if ln.strip()]
        issue = lines[-1] if lines else ""
        if not issue:
            die("bd create nao devolveu id de issue", EXIT_CONTRACT)
    elif mode == "create":
        bd(["update", issue, "--description", body], root)
    elif mode == "set":
        bd(["update", issue, FIELD_FLAG[field], body], root)
    elif mode == "append":
        bd(["update", issue, "--append-notes", body], root)
    elif mode == "close":
        bd(["update", issue, "--notes", body], root)
        bd(["close", issue], root)

    if args.as_json:
        print(json.dumps({"kind": args.kind, "issue": issue, "field": field,
                          "mode": mode, "phase": args.phase,
                          "plan": args.plan}))
    else:
        print("%s %s -> %s.%s (%s)"
              % (TAG_PREFIX, args.kind, issue, field, mode))
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
