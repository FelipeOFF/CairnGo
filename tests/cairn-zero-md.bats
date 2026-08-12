#!/usr/bin/env bats
# cairn-zero-md.bats — O PLACAR do milestone v1.7, e a catraca que o move.
#
# A v1.6 parou de LER markdown como estado (tests/cairn-prompt-state.bats, 4
# familias, 66 arquivos, zero sitios). Ela NAO parou de ESCREVER: 8 fases da
# v1.6 geraram 99 arquivos markdown (32 SUMMARY, 32 PLAN, 8 MAP, 8 CONTEXT,
# 6 LOG, 4 deferred-items, 3 PATTERNS, 2 VERIFICATION). Esta suite mede a
# outra metade — os sitios que MANDAM ESCREVER — e existe para que o numero
# so possa andar para baixo.
#
# AS DUAS FAMILIAS DE ESCRITA, e por que sao duas e nao uma:
#
#   W1  a INSTRUCAO: um verbo de escrita e o nome de um documento na mesma
#       linha ("Write SUMMARY.md", "Create CONTEXT.md", "generate the PLAN.md
#       files"). E' o sitio que faz o modelo produzir o arquivo.
#   W2  o DESTINO: o literal de caminho `.planning/...`. Uma metrica so de W1
#       declara verde um arquivo que parou de dizer "Write" e continua
#       entregando o caminho a um subagente, que escreve do outro lado — e' a
#       mesma armadilha da familia D da v1.6 (a leitura acontece FORA do
#       arquivo medido), agora do lado da escrita.
#
# W1 sozinha da verde com W2 de pe, e vice-versa. Por isso as duas, sempre.
#
# O QUE NAO E' FAMILIA. A mencao NUA de um nome de documento (`SUMMARY.md`
# sem verbo, sem caminho) NAO entra. MEDIDO na arvore pre-mudanca: 802
# ocorrencias, contra 123 de W1 — a maioria esmagadora e' prosa descritiva
# ("the SUMMARY.md format is..."), template, e tabela de artefatos. Documento
# nao e' fato, e converter prosa que DESCREVE em verbo que MANDA e' regressao,
# nao adaptacao (a mesma decisao escrita que a v1.6 tomou para PROJECT.md e
# ROADMAP.md). Ha caso de teste provando que o oraculo nao morde a forma nua.
#
# COMO A CATRACA FUNCIONA, e por que nao e' so uma guarda de zero.
# Uma guarda "zero sitios em toda a arvore" ficaria VERMELHA do primeiro dia
# ao ultimo do milestone — uma suite vermelha por meses nao e' oraculo, e'
# ruido que se aprende a ignorar. E uma guarda so sobre o que ja foi
# convertido passa vacuamente enquanto a tabela estiver vazia, que e'
# exatamente o defeito que a v1.6 encontrou em quatro ondas ("guarda que so
# passa nao prova nada").
#
# Entao sao TRES pecas, e cada uma pega o que as outras deixam:
#
#   ZM_LEDGER      a medicao DECLARADA, arquivo a arquivo. O teste compara
#                  com o disco EXATAMENTE e nos DOIS sentidos: contagem menor
#                  que a declarada e' conversao que ninguem registrou (o
#                  placar mentiria para baixo), maior e' sitio novo entrando
#                  pela porta dos fundos. Nenhuma conversao passa sem mover um
#                  numero escrito neste arquivo.
#   ZM_DECLARED_*  o PLACAR: a soma. E' o numero que o milestone persegue, e
#                  o teste o imprime a cada execucao.
#   ZM_CONVERTED   os caminhos ja convertidos, que devem medir ZERO nas duas
#                  familias. Esta e' a guarda com dentes, e ela tem controle
#                  negativo pareado apontado para arvore forjada — sem isso
#                  ela seria a guarda vacua que a v1.6 aprendeu a recusar.
#
# O milestone termina quando ZM_DECLARED_W1 e ZM_DECLARED_W2 forem 0 e
# ZM_LEDGER estiver vazia. Ate la, todo commit que converte um sitio TEM de
# editar este arquivo, e essa obrigacao e' o desenho, nao efeito colateral.
#
# MEDIDO vs. ASSUMIDO: todos os numeros abaixo sao MEDIDOS na arvore
# pre-mudanca (2026-08-12) por dois instrumentos independentes que
# concordaram — `grep -coE` por arquivo e uma varredura python linha a linha.
# Nenhum foi assumido, nenhum foi herdado do briefing sem remedicao.
#
# Estilo de assercao: um `[[ ]]` ou `! cmd` no meio do teste NAO reprova neste
# bash, entao substring usa grep -qF -- e negativa usa refute_zm.

load 'helpers'

refute_zm() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

ZM_SCOPE="$CAIRN_REPO_ROOT/cairn/gsd"

# Familia W1 — a INSTRUCAO de escrita. `[^|]{0,45}` fecha a busca dentro da
# linha sem atravessar borda de celula de tabela markdown (mesma doutrina da
# v1.6), e a janela de 45 caracteres foi medida: cobre "Write the phase's
# SUMMARY.md" sem casar um verbo e um nome de documento que so coabitam um
# paragrafo longo.
ZM_W1='(^|[^a-zA-Z])(Write|Create|Generate|Produce|Emit|Save|write|create|generate|produce|emit|save)[^|]{0,45}\b(SUMMARY|PLAN|CONTEXT|MAP|LOG|PATTERNS|VERIFICATION|RESEARCH|REVIEW|UI-SPEC|AI-SPEC|SPEC|STATE|ROADMAP|PROJECT|REQUIREMENTS)\.md'

# Familia W2 — o DESTINO. Conta OCORRENCIAS, nao linhas: uma linha que cita
# dois caminhos .planning/ tem dois sitios para converter, e contar linhas
# esconderia o segundo.
ZM_W2='\.planning/[A-Za-z0-9_./{}$-]*'

# --- as tabelas ---------------------------------------------------------------

# LEDGER — caminho relativo a cairn/gsd/ | sitios W1 | sitios W2
ZM_LEDGER="\
agents/gsd-codebase-mapper.md|0|5
agents/gsd-debug-session-manager.md|0|3
agents/gsd-debugger.md|0|22
commands/gsd/autonomous.md|0|2
commands/gsd/debug.md|0|1
commands/gsd/discuss-phase.md|1|0
commands/gsd/quick.md|0|8
gsd-core/references/agent-contracts.md|0|1
gsd-core/references/agent-skills-bootstrap.md|0|1
gsd-core/references/autonomous-smart-discuss.md|3|5
gsd-core/references/context-budget.md|0|3
gsd-core/references/debugger-fix-acceptance.md|0|1
gsd-core/references/debugger-semantic-recall.md|0|1
gsd-core/references/model-profiles.md|0|5
gsd-core/references/mvp-concepts.md|2|0
gsd-core/references/offer-next.md|0|1
gsd-core/references/questioning.md|5|0
gsd-core/references/scout-codebase.md|0|2
gsd-core/references/tdd.md|1|2
gsd-core/references/thinking-partner.md|0|1
gsd-core/references/universal-anti-patterns.md|1|2
gsd-core/references/user-story-template.md|1|0
gsd-core/templates/DEBUG.md|0|2
gsd-core/templates/context.md|0|2
gsd-core/templates/discussion-log.md|0|1
gsd-core/workflows/autonomous.md|4|4
gsd-core/workflows/debug.md|0|14
gsd-core/workflows/discuss-phase/modes/default.md|1|1
gsd-core/workflows/discuss-phase/modes/power.md|1|0
gsd-core/workflows/discuss-phase.md|4|8
gsd-core/workflows/fast.md|1|0
gsd-core/workflows/quick/steps/discussion-phase.md|2|0
gsd-core/workflows/quick/steps/quick-verification.md|1|0
gsd-core/workflows/quick/steps/research-phase.md|1|0
skills/gsd-autonomous/SKILL.md|0|2
skills/gsd-debug/SKILL.md|0|1
skills/gsd-discuss-phase/SKILL.md|1|0
skills/gsd-quick/SKILL.md|0|8
"

# O PLACAR. Some as colunas do ledger; e' o numero do milestone.
ZM_DECLARED_W1=30
ZM_DECLARED_W2=109

# CONVERTIDOS — caminhos que ja passaram pelo protocolo de registro e que
# DEVEM medir 0|0 nas duas familias. Uma linha aqui e uma linha no ledger com
# contagem nao-zero sao contraditorias, e ha teste que recusa a contradicao.
#
# ONDA 1 (2026-08-12) — os SEIS arquivos de maior densidade do corpus, 46 sitios
# W1 e 29 W2, todos convertidos para a fronteira cairn-record.sh: os tres
# agentes que produziam documento de desenho (patterns, research, ui-spec), os
# dois workflows que abriam e fechavam o registro de plano (plan-phase,
# execute-phase) e o quick, cujo plano e sumario passam a ser o mesmo registro
# aberto e fechado no bead da side-quest. O PLACAR caiu de 123|209 para 77|180.
ZM_CONVERTED="\
agents/gsd-code-reviewer.md
agents/gsd-executor.md
agents/gsd-integration-checker.md
agents/gsd-pattern-mapper.md
agents/gsd-phase-researcher.md
agents/gsd-plan-checker.md
agents/gsd-planner.md
agents/gsd-ui-auditor.md
agents/gsd-ui-checker.md
agents/gsd-ui-researcher.md
agents/gsd-verifier.md
commands/gsd/plan-phase.md
gsd-core/references/checkpoints.md
gsd-core/references/execute-phase-context-guard.md
gsd-core/references/execute-phase-requirement-revert.md
gsd-core/references/planner-antipatterns.md
gsd-core/references/planner-chunked.md
gsd-core/references/planner-gap-closure.md
gsd-core/references/planner-load-graph-context.md
gsd-core/references/planner-revision.md
gsd-core/references/verify-mvp-mode.md
gsd-core/templates/UAT.md
gsd-core/templates/summary.md
gsd-core/workflows/execute-phase.md
gsd-core/workflows/execute-phase/steps/executor-isolation-dispatch.md
gsd-core/workflows/execute-phase/steps/gap-closure-artifacts.md
gsd-core/workflows/execute-phase/steps/post-merge-gate.md
gsd-core/workflows/execute-phase/steps/regression-gate.md
gsd-core/workflows/plan-phase.md
gsd-core/workflows/plan-phase/steps/adr-ingest-express-path.md
gsd-core/workflows/plan-phase/steps/chunked-planning-mode.md
gsd-core/workflows/plan-phase/steps/prd-express-gate.md
gsd-core/workflows/plan-phase/steps/prd-express-path.md
gsd-core/workflows/plan-phase/steps/research-only-modifiers.md
gsd-core/workflows/plan-phase/steps/stall-detection-helpers.md
gsd-core/workflows/quick.md
gsd-core/workflows/verify-work.md
skills/gsd-plan-phase/SKILL.md
"

# --- o instrumento ------------------------------------------------------------

# Mede uma arvore e imprime "caminho|w1|w2" por arquivo com ao menos um sitio.
# Recebe a RAIZ por argumento — e' o que permite apontar o MESMO laco para uma
# arvore forjada nos controles negativos.
zm_measure() {
  ZM_ROOT="$1" ZM_RE1="$ZM_W1" ZM_RE2="$ZM_W2" python3 - <<'ZMPY'
import os, re
from pathlib import Path
root = Path(os.environ["ZM_ROOT"])
r1 = re.compile(os.environ["ZM_RE1"])
r2 = re.compile(os.environ["ZM_RE2"])
for f in sorted(root.rglob("*.md")):
    txt = f.read_text(encoding="utf-8", errors="replace")
    a = sum(1 for ln in txt.splitlines() if r1.search(ln))
    b = len(r2.findall(txt))
    if a or b:
        print("%s|%d|%d" % (f.relative_to(root), a, b))
ZMPY
}

zm_ledger_sorted() {
  printf '%s' "$ZM_LEDGER" | sed '/^$/d' | LC_ALL=C sort
}

# --- o oraculo ----------------------------------------------------------------

@test "zero-md: o ledger declarado bate com o disco, nos DOIS sentidos" {
  local measured declared
  measured="$(zm_measure "$ZM_SCOPE" | LC_ALL=C sort)"
  declared="$(zm_ledger_sorted)"
  if [ "$measured" != "$declared" ]; then
    echo "--- o ledger e o disco divergem ---" >&2
    diff <(printf '%s\n' "$declared") <(printf '%s\n' "$measured") >&2 || true
    echo "linha a MENOS no disco = conversao nao registrada (o placar mentiria" >&2
    echo "para baixo); linha a MAIS = sitio novo entrando sem ninguem ver." >&2
    return 1
  fi
}

@test "zero-md: o PLACAR declarado bate com a soma medida" {
  local w1 w2
  w1="$(zm_measure "$ZM_SCOPE" | awk -F'|' '{s+=$2} END {print s+0}')"
  w2="$(zm_measure "$ZM_SCOPE" | awk -F'|' '{s+=$3} END {print s+0}')"
  echo "PLACAR v1.7 — sitios de escrita restantes: W1=$w1 W2=$w2" >&2
  [ "$w1" -eq "$ZM_DECLARED_W1" ]
  [ "$w2" -eq "$ZM_DECLARED_W2" ]
}

@test "zero-md: todo caminho declarado CONVERTIDO mede zero nas duas familias" {
  local path measured
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    measured="$(zm_measure "$ZM_SCOPE" | grep -F -- "$path|" || true)"
    if [ -n "$measured" ]; then
      echo "declarado convertido mas ainda mede sitios: $measured" >&2
      return 1
    fi
  done <<<"$(printf '%s' "$ZM_CONVERTED" | sed '/^$/d')"
}

@test "zero-md: um caminho nao pode ser convertido E ter contagem no ledger" {
  local path row
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    row="$(zm_ledger_sorted | grep -F -- "$path|" || true)"
    if [ -n "$row" ]; then
      echo "contradicao: '$path' esta em ZM_CONVERTED e no ledger como '$row'" >&2
      return 1
    fi
  done <<<"$(printf '%s' "$ZM_CONVERTED" | sed '/^$/d')"
}

# --- controles negativos: sem estes, as guardas acima nao provam nada --------

@test "zero-md: controle negativo — W1 e DETECTADA em arvore forjada" {
  local forged="$BATS_TEST_TMPDIR/forged-w1"
  mkdir -p "$forged"
  printf 'Some prose.\nWrite SUMMARY.md when the wave closes.\n' > "$forged/a.md"
  run zm_measure "$forged"
  [ "$status" -eq 0 ]
  grep -qF -- "a.md|1|0" <<<"$output"
}

@test "zero-md: controle negativo — W2 e DETECTADA em arvore forjada" {
  local forged="$BATS_TEST_TMPDIR/forged-w2"
  mkdir -p "$forged"
  printf 'Read .planning/phases/03-x/PLAN.md and .planning/STATE.md now.\n' \
    > "$forged/b.md"
  run zm_measure "$forged"
  [ "$status" -eq 0 ]
  grep -qF -- "b.md|0|2" <<<"$output"
}

@test "zero-md: controle negativo — a guarda de CONVERTIDOS reprova quando ha sitio" {
  local forged="$BATS_TEST_TMPDIR/forged-conv"
  mkdir -p "$forged"
  printf 'Write SUMMARY.md now.\n' > "$forged/c.md"
  local measured
  measured="$(zm_measure "$forged" | grep -F -- "c.md|" || true)"
  [ -n "$measured" ]
}

@test "zero-md: a mencao NUA de documento NAO e mordida por nenhuma familia" {
  local forged="$BATS_TEST_TMPDIR/forged-bare"
  mkdir -p "$forged"
  printf 'The SUMMARY.md format has three sections.\n' > "$forged/d.md"
  printf 'See PLAN.md for the task list; VERIFICATION.md records the verdict.\n' \
    >> "$forged/d.md"
  run zm_measure "$forged"
  [ "$status" -eq 0 ]
  refute_zm "d.md"
}

@test "zero-md: a janela de W1 nao atravessa borda de celula de tabela" {
  local forged="$BATS_TEST_TMPDIR/forged-cell"
  mkdir -p "$forged"
  printf '| write the thing | the SUMMARY.md column |\n' > "$forged/e.md"
  run zm_measure "$forged"
  [ "$status" -eq 0 ]
  refute_zm "e.md"
}
