"""cairn_source — o roteiro do projeto, derivado do bd.

O MANTRA QUE ESTE MÓDULO EXISTE PARA CUMPRIR (decisão do usuário, 2026-08-12):

    O cairn NÃO gera markdown. `.planning/` existe para UMA coisa — importar
    o que um GSD já produziu — e depois de importado ninguém volta lá.
    Pergunta sobre uma fase é pergunta ao bd, e o bd responde com o fato e
    com a prosa.

O que estava errado antes deste módulo, e não é um detalhe de implementação:
o roteiro do projeto — quais fases existem, o que cada uma promete, quais
requisitos carrega, quais já terminaram, qual milestone está correndo — era
lido de `ROADMAP.md` por ~25 parsers espalhados em 8 scripts, cada um com sua
própria gramática de markdown. MEDIDO em 2026-08-12: 116 sítios de leitura de
`ROADMAP.md` em 13 scripts.

Um repositório que não escreve mais markdown deixa esses 25 parsers cegos, e
cego não é verde: é o `⊘ nothing to compare` que o doctor passou a imprimir em
seis checagens de uma vez. A resposta não é reabrir o markdown — é mudar a
pergunta de endereço.

O QUE É FATO, E ONDE ELE MORA NO BD
-----------------------------------
Nada aqui é inventado: são as convenções que o cairn já estampa em toda issue.

    fase           label `phase-N`         (N não-padded: `phase-7`, `phase-38`)
    milestone      label `m-vX.Y`
    requisito      metadata `gsd.req`      (o bead É o requisito)
    portador       o bead da fase que não é requisito, nem plano, nem filho
    plano          label `plan-NN` + o `phase-N` herdado do pai
    completude     status do bead — `closed` é terminado, e nada mais é

UMA LEITURA, NÃO TRINTA (o requisito de velocidade)
---------------------------------------------------
MEDIDO: `bd list --all --limit 0 --json` custa ~0,49 s neste repo com 231
issues. O doctor faz dezenas de perguntas ao roteiro numa execução; trinta
chamadas seriam quinze segundos de doctor.

Então a leitura é UMA, por (raiz, processo), guardada em `_CACHE`. Todas as
perguntas abaixo derivam da mesma lista em memória. Não há banco novo, e não
precisa haver: o bd já é o banco, e o que faltava era parar de consultá-lo em
laço. Um processo que precise reler chama `invalidate()`.

O QUE ESTE MÓDULO NÃO FAZ
-------------------------
Não escreve. Não cria bead, não fecha bead, não conserta convenção. Quem
escreve é `cairn-record` (registro) e `cairn-migrate` (importação); um leitor
que também escreve é como o doctor vira a coisa que ele deveria medir.

Não lê `.planning/`. Nem para conferir, nem para "completar" o que o bd não
souber — um fallback para markdown é exatamente o que o mantra proíbe, e é
como o markdown volta a ser fonte de verdade pela porta dos fundos.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

PHASE_LABEL = re.compile(r"^phase-(\d+(?:\.\d+)?)$")
MILESTONE_LABEL = re.compile(r"^m-(v[\d.]+\S*)$")
PLAN_LABEL = re.compile(r"^plan-(\S+)$")

_CACHE = {}


def invalidate(root=None):
    """Esquece a leitura guardada — para quem escreveu no bd e vai reler."""
    if root is None:
        _CACHE.clear()
    else:
        _CACHE.pop(str(Path(root).resolve()), None)


def bd_available():
    return shutil.which("bd") is not None


def issues(root):
    """TODA issue do repo, uma vez por (raiz, processo).

    Devolve [] quando o bd não está no PATH ou a chamada falha — um leitor
    decide o que fazer com o vazio; este módulo não inventa dado nem levanta
    exceção no caminho de leitura.
    """
    key = str(Path(root).resolve())
    if key in _CACHE:
        return _CACHE[key]
    data = []
    if bd_available():
        try:
            proc = subprocess.run(
                ["bd", "-C", key, "list", "--all", "--limit", "0", "--json"],
                capture_output=True, text=True, timeout=60)
            out = (proc.stdout or "").strip()
            # O bd manda warning para stderr, mas um wrapper futuro pode
            # misturar: começa no primeiro delimitador JSON, não no byte 0.
            start = min([i for i in (out.find("["), out.find("{")) if i >= 0]
                        or [-1])
            if start >= 0:
                parsed = json.loads(out[start:])
                data = parsed if isinstance(parsed, list) else [parsed]
        except (OSError, ValueError, subprocess.SubprocessError):
            data = []
    _CACHE[key] = data
    return data


# --- o que cada issue carrega -------------------------------------------------

def labels(issue):
    return issue.get("labels") or []


def gsd(issue):
    """A metadata `gsd`, tolerante a metadata que venha como string JSON."""
    meta = issue.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            return {}
    value = (meta or {}).get("gsd") or {}
    return value if isinstance(value, dict) else {}


def issue_req(issue):
    return gsd(issue).get("req")


def issue_phases(issue):
    """Números de fase (str, não-padded) que a issue carrega."""
    out = []
    for label in labels(issue):
        m = PHASE_LABEL.match(label)
        if m:
            out.append(m.group(1))
    return out


def issue_milestones(issue):
    return [m.group(1) for m in
            (MILESTONE_LABEL.match(l) for l in labels(issue)) if m]


def issue_plan(issue):
    for label in labels(issue):
        m = PLAN_LABEL.match(label)
        if m:
            return m.group(1)
    return None


def is_child_id(issue_id):
    """O bd NÃO emite `parent` em saída JSON nenhuma (medido em bd 1.1.0), mas
    a hierarquia está visível no id: o filho é o id do pai mais sufixo
    (`CairnGo-9c0h` -> `CairnGo-9c0h.3`). O ponto vem depois do prefixo do
    projeto, então a busca começa depois do primeiro `-`."""
    tail = issue_id.split("-", 1)[1] if "-" in issue_id else issue_id
    return "." in tail


def is_carrier(issue):
    """Portador da fase: o bead que não é nenhuma das três outras coisas que
    usam o mesmo label `phase-N` — requisito (`gsd.req`), registro de plano
    (`plan-NN`, que herda o label do pai) ou filho (id com sufixo)."""
    return (not issue_req(issue)
            and not issue_plan(issue)
            and not is_child_id(issue.get("id", "")))


# --- as perguntas que se faziam ao ROADMAP.md ---------------------------------

class _AllMilestones:
    """O tipo do sentinela, para que ele se identifique num traceback."""
    def __repr__(self):
        return "ALL_MILESTONES"


ALL_MILESTONES = _AllMilestones()
"""Recorte explícito: TODO ciclo que o bd conhece.

`None` NÃO significa mais isso. Ler a docstring de `in_milestone` antes de
usar — o sentinela existe para que "quero todos os ciclos" seja uma frase
escrita, e não o resultado de um argumento esquecido.
"""


def in_milestone(issue, key):
    """A issue pertence ao recorte?

    TRÊS VALORES, E `None` MUDOU DE LADO NA v3.1:

        ALL_MILESTONES  -> todo ciclo que o bd conhece
        "v1.7"          -> aquele ciclo
        None            -> NENHUM ciclo. Devolve vazio, sempre.

    `None` significava "todos", e esse default produziu DOIS incidentes com
    a lição escrita ao lado dele. No primeiro, `req-issue` acusou os 174
    requisitos de cinco ciclos encerrados de não terem issue no ciclo de
    hoje. No segundo — a v3.0.0, em produção — o board despejou as 38 fases
    de sete ciclos como pendentes e mandou o usuário replanejar trabalho já
    entregue.

    A causa nunca foi um chamador distraído: é que `milestone(root)` devolve
    `None` LEGITIMAMENTE quando nenhum ciclo está aberto, e todo leitor que
    passasse esse valor adiante recebia o oposto do que pediu. O modo de
    falha era o pior possível — resposta plausível, jamais uma exceção.

    Invertido, o mesmo esquecimento produz lista vazia: visível, e do lado
    seguro. Quem quer todos os ciclos escreve `ALL_MILESTONES`.
    """
    if key is ALL_MILESTONES:
        return True
    if key is None:
        return False
    return key in issue_milestones(issue)


def phases(root, milestone_key):
    """Os números de fase do recorte, como int quando inteiro.

    O `milestone_key` é OBRIGATÓRIO — ver `in_milestone` para o porquê e
    para o que `None` significa (nenhum ciclo, não todos).

    O ESCOPO NÃO É DETALHE. O `ROADMAP.md` ATIVO listava só o ciclo corrente
    — as fases dos ciclos anteriores saíam dele no arquivamento, e é por isso
    que uma checagem podia cruzar "todo requisito do roteiro" contra "as
    issues do milestone corrente" sem produzir absurdo. O bd guarda TODOS os
    ciclos ao mesmo tempo, então quem herda o papel do roteiro ativo tem de
    herdar também o seu recorte: sem `milestone_key`, `req-issue` acusaria
    os 174 requisitos de cinco ciclos encerrados de não terem issue no ciclo
    de hoje. (Medido: foi exatamente o que aconteceu na primeira tentativa.)
    """
    out = set()
    for issue in issues(root):
        if not in_milestone(issue, milestone_key):
            continue
        for n in issue_phases(issue):
            out.add(as_number(n))
    return out


def as_number(n):
    """'7' -> 7, '2.1' -> 2.1 — a fase é numérica, e quem compara compara
    número. Um valor que não converte volta como veio, em vez de virar
    exceção num leitor que só queria listar fases."""
    try:
        return int(n)
    except (TypeError, ValueError):
        try:
            return float(n)
        except (TypeError, ValueError):
            return n


def phase_reqs(root, milestone_key):
    """{fase: [req ids]} do recorte — o requisito é o bead, e o id é
    `gsd.req`. `milestone_key` obrigatório; ver `in_milestone`."""
    out = {}
    for issue in issues(root):
        req = issue_req(issue)
        if not req or not in_milestone(issue, milestone_key):
            continue
        for n in issue_phases(issue):
            out.setdefault(as_number(n), []).append(req)
    return {k: sorted(set(v)) for k, v in out.items()}


def phase_issues(root, phase):
    """Toda issue da fase, portador incluído."""
    want = str(phase)
    return [i for i in issues(root) if want in issue_phases(i)]


def phase_carrier(root, phase):
    """O portador da fase, ou None. Nunca cria — quem cria é cairn-record."""
    carriers = [i for i in phase_issues(root, phase) if is_carrier(i)]
    return carriers[0] if len(carriers) == 1 else None


def phase_name(root, phase):
    """O nome da fase: o título do portador. None quando não há portador —
    e a ausência é dita, nunca preenchida com o título de um requisito."""
    carrier = phase_carrier(root, phase)
    return carrier.get("title") if carrier else None


def phase_goal(root, phase):
    """O que a fase promete: a `description` do portador."""
    carrier = phase_carrier(root, phase)
    return (carrier.get("description") or "") if carrier else ""


def completed_phases(root, milestone_key):
    """Fases do recorte cujo trabalho terminou (`milestone_key` obrigatório): TODA issue da fase fechada, e
    ao menos uma issue existindo. Uma fase vazia não é uma fase completa — é
    uma fase sem trabalho, e chamá-la de completa é o `all([])` que faz um
    relatório dizer 'pronto' sobre o que nunca começou.

    A completude olha TODA issue da fase, mesmo quando o recorte é de um
    ciclo: uma fase cujo `m-` corrente fechou mas que ainda tem trabalho
    aberto sob outro label não terminou, e dizer que terminou é a mentira
    que o recorte poderia introduzir."""
    scope = {as_number(n) for i in issues(root) if in_milestone(i, milestone_key)
             for n in issue_phases(i)}
    by_phase = {}
    for issue in issues(root):
        for n in issue_phases(issue):
            if as_number(n) in scope:
                by_phase.setdefault(as_number(n), []).append(issue)
    return {n for n, group in by_phase.items()
            if group and all(i.get("status") == "closed" for i in group)}


def milestone(root):
    """O milestone corrente: o `m-*` com issue NÃO fechada mais frequente.

    Um ciclo corrente é aquele que ainda tem trabalho aberto — é o que
    distingue do arquivado sem consultar data nem posição em lista, e sem
    perguntar a nenhum documento se ele está 🚧.
    """
    counts = {}
    for issue in issues(root):
        if issue.get("status") == "closed":
            continue
        for key in issue_milestones(issue):
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def open_cycle(root):
    """(chave do ciclo aberto, há ciclo aberto?) — a pergunta que cinco
    leitores faziam cada um do seu jeito.

    Existe porque `milestone(root)` devolve `None` em dois casos que PARECEM
    o mesmo e não são: não há ciclo aberto, e não há bd algum. Cada
    consumidor que tratasse esse `None` sozinho inventaria a sua própria
    resposta — e foi assim que o board acabou dizendo `completed: 1` sobre o
    mesmo repositório em que `completed_phases()` dizia 38.

    Devolve o par para que o chamador não precise comparar com `None` de
    novo, que é a comparação que já saiu errada uma vez.
    """
    key = milestone(root)
    return key, key is not None


def milestones(root):
    """Todo milestone que o bd conhece, do mais recente para o mais antigo
    pela ordem natural da versão."""
    keys = set()
    for issue in issues(root):
        keys.update(issue_milestones(issue))

    def version_key(k):
        return [int(p) if p.isdigit() else p
                for p in re.split(r"[.\-]", k.lstrip("v"))]

    return sorted(keys, key=version_key, reverse=True)


def milestone_phases(root, key):
    """Fases que carregam o label de um milestone."""
    out = set()
    for issue in issues(root):
        if key in issue_milestones(issue):
            for n in issue_phases(issue):
                out.add(as_number(n))
    return out


def phase_plans(root, phase):
    """[(plano, fechado)] da fase, ordenado pelo id do plano. O plano é um
    registro (label `plan-NN`), e 'completo' é o bead fechado."""
    out = []
    for issue in phase_issues(root, phase):
        plan = issue_plan(issue)
        if plan:
            out.append((plan, issue.get("status") == "closed"))
    return sorted(out)



def active_phase(root):
    """A fase corrente, derivada do trabalho e não de um campo escrito à mão.

    Ordem: a menor fase com issue `in_progress`; senão a menor fase com issue
    aberta. None quando não há fase aberta nenhuma — um projeto entre ciclos
    não tem fase ativa, e inventar uma é pior que dizer que não há.

    Isto substitui o `active_phase:` do frontmatter do STATE.md, que era um
    número que alguém tinha de lembrar de mover. O trabalho já diz onde está.
    """
    doing, open_ = set(), set()
    for issue in issues(root):
        status = issue.get("status")
        if status == "closed":
            continue
        for n in issue_phases(issue):
            (doing if status == "in_progress" else open_).add(as_number(n))
    pool = doing or open_
    if not pool:
        return None
    numeric = [n for n in pool if isinstance(n, (int, float))]
    return min(numeric) if numeric else sorted(pool, key=str)[0]


def unlabeled(root):
    """Issues abertas sem nenhum `phase-*` — o que o doctor chama de órfão
    no eixo que não depende de roteiro nenhum."""
    return [i for i in issues(root)
            if i.get("status") != "closed" and not issue_phases(i)]
