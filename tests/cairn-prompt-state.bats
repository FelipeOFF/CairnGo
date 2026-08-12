#!/usr/bin/env bats
# cairn-prompt-state.bats — a metade SEMÂNTICA do teste de prompt: nenhum
# arquivo adaptado pela fase 36 lê `.planning/` como FONTE DE ESTADO.
#
# POR QUE ESTA SUÍTE NÃO EXISTIA. Até a fase 36 havia exatamente UM teste que
# validava o conteúdo de um `.md` sob `cairn/gsd/`: a byte-paridade contra o
# clone da tag v1.10.0 (`cairn-vendoring.bats`, oráculo
# `assert_tree_bytes_match`). Ele afirma o INVERSO do que esta fase faz —
# "nada mudou" — e por isso não pode ser esticado para dizer "mudou o
# suficiente". As duas metades convivem: aquela mede BYTES contra o upstream
# (e a fase 36 a reescreveu para dois sentidos contra
# `cairn/gsd-adaptations.json`); esta mede SEMÂNTICA contra o critério de
# ADAPT-02.
#
# POR QUE QUATRO FAMÍLIAS, E NÃO UM GREP POR NOME DE ARQUIVO. A métrica óbvia
# — "o arquivo não cita `.planning/STATE.md`" — declara verde uma cobertura
# que não existe. MEDIDO em 2026-08-11 sobre `cairn/gsd/`:
#
#   * 12 linhas referenciam o estado por VARIÁVEL, sem citar o nome do
#     arquivo (`STATE_PATH`, `{state_path}`, `STATE_FILE`, `state_raw`);
#     cinco delas injetam o caminho no prompt de um subagente, que então lê o
#     markdown FORA do workflow medido. Uma SEXTA injeção existe e fica FORA
#     dessas 12 porque não usa nenhuma das quatro grafias de estado — é o
#     caminho literal (`execute-phase.md:750`), e por isso era invisível às
#     três primeiras famílias: daí a família D;
#   * 66 linhas de workflows+agents citam `STATE.md`, e só 8 casam a forma
#     imperativa clássica (`Update STATE.md`); outras 7 dizem a mesma coisa
#     com as palavras trocadas (`- [ ] STATE.md updated ...`).
#
# Daí as quatro famílias abaixo. Uma delas sozinha dá verde com a outra de pé.
#
# MEDIDO vs. ASSUMIDO nesta suíte:
#   * MEDIDO — as quatro grafias da família B, e a ausência de `state_raw` na
#     árvore de hoje (`grep -rc state_raw cairn/gsd/` = 0). A grafia entra na
#     família mesmo com zero ocorrências: ela é o nome que o upstream usa no
#     bundle cru e um sítio novo nasceria mudo sem ela.
#   * MEDIDO — a forma passiva da família C. `grep -rE 'STATE\.md
#     (updated|read|checked|written)' cairn/gsd/{gsd-core/workflows,agents}`
#     dá 7 linhas, todas prosa de critério de sucesso, zero falso-positivo.
#     O plano 36-03 escreveu a família C só com a forma imperativa; a forma
#     passiva foi ACRESCENTADA aqui porque `fast.md:108`
#     (`- [ ] STATE.md updated if it exists`) é um dos três sítios que o
#     próprio plano manda converter e a forma imperativa NÃO o pega — o
#     oráculo daria verde no arquivo com o sítio de pé, que é exatamente a
#     falha que esta suíte existe para impedir.
#   * DECISÃO ESCRITA — `state_exists` fica FORA da família B. É campo do
#     bundle de init, fato que já vem do binário (contrato da fase 34). Pô-lo
#     na família obrigaria quatro isenções PERMANENTES (autonomous.md:101 e
#     :104, execute-phase.md:152) para descrever comportamento correto, e
#     isenção que nunca morre é ruído que treina a ignorar a tabela. Há um
#     caso de teste dedicado provando a exclusão.
#   * NÃO É FAMÍLIA NENHUMA — leitura de DOCUMENTO: PROJECT.md,
#     REQUIREMENTS.md, ROADMAP.md, CONTEXT.md e os arquivos de sessão sob
#     `.planning/debug/`. Documento não é fato (36-PATTERNS §5d), e converter
#     documento em verbo é regressão, não adaptação. Há um caso de teste
#     dedicado provando que o oráculo não os morde.
#
# A TABELA CRESCEU PLANO A PLANO E FECHOU NA ONDA 7. Até ali `PS_ADAPTED`
# cobria só o que já tinha passado por uma onda, e um arquivo que nenhuma onda
# mediu não era testado — o que deixava a cobertura em 31 dos 66 arquivos do
# escopo. A onda 7 fecha: os 66 caminhos do escopo declarado por D-02 (os 8
# workflows raiz, os 42 fragments deles e os 16 agentes) estão na tabela, e o
# caso de completude abaixo compara o conjunto do DISCO com o da tabela nos
# DOIS sentidos. Um arquivo novo em qualquer um dos três diretórios entra no
# escopo sozinho e reprova a suíte até alguém decidir o que ele é.
#
# POR QUE 66 E NÃO OS 39 QUE O PLANO 36-07 DESCREVE (8 raiz + 15 fragments com
# preâmbulo + 16 agentes): os 15 são os fragments que CARREGAM preâmbulo, e o
# escopo de D-02 são os 8 workflows "com fragments, 50 arquivos" — carregar
# preâmbulo é consequência de chamar o dispatcher, não fronteira de escopo.
# MEDIDO na onda 7: os 42 fragments dão ZERO nas quatro famílias, então cobrir
# os 27 restantes não custou uma conversão sequer e fechou o buraco pelo qual um
# sítio de estado poderia nascer num fragment sem preâmbulo sem ninguém ver.
#
# MEDIDO NA ONDA 6, e publicado porque o número é o achado: as quatro famílias
# nos 16 agentes davam A=1, B=0, C=2, D=0 — TRÊS sítios, não os zero que o
# plano previa. Dois eram do gsd-planner (o template de PLAN.md mandava carregar
# o arquivo de estado no contexto de todo plano gerado, e o critério de sucesso
# falava do arquivo) e foram convertidos aqui; o terceiro é o do executor, que
# virou pendência declarada. "Zero" teria sido uma afirmação não medida.
#
# Estilo de asserção (herdado de cairn-vendoring.bats):
#   - toda guarda vem com o controle negativo pareado: guarda que só passa
#     não prova nada. O oráculo recebe a RAIZ por argumento para que o mesmo
#     laço possa ser apontado para uma árvore forjada.
#   - resíduo é nomeado no stderr com arquivo, linha e família; contagem
#     divergente nomeia caminho, padrão, esperado e encontrado.
#   - a tabela de isenções é conferida nos DOIS sentidos: contagem menor que
#     a declarada é isenção morta (o sítio sumiu e a linha ficou), maior é
#     sítio novo entrando pela porta dos fundos.

load 'helpers'

PS_ROOT="$CAIRN_REPO_ROOT/cairn/gsd"
PS_ADAPTATIONS="$CAIRN_REPO_ROOT/cairn/gsd-adaptations.json"

# --- as quatro famílias, como dados -------------------------------------------

# Família A — leitura MECÂNICA do arquivo de estado: um comando que LÊ, tendo
# o arquivo de estado como argumento, mais a forma `@`-referência que carrega
# o arquivo no prompt de um subagente. `[^|]*` fecha a busca dentro da linha
# sem atravessar borda de célula de tabela markdown.
PS_RE_A='(cat|grep|head|tail|wc|test -f|\[ -f)[^|]*\.planning/STATE\.md|@\.planning/STATE\.md'

# Família C — prosa imperativa sobre o arquivo de estado, nas duas ordens:
# verbo antes do nome (instrução) e particípio depois (critério de sucesso).
# `exists` entra no segundo alternante porque a EXISTÊNCIA do arquivo como
# predicado em prosa é o mesmo fato que o bundle já entrega em `state_exists`
# — medido: 1 ocorrência na árvore (`fast.md:66`), convertida pelo plano
# 36-03, e o alternante fica de guarda contra a volta da forma.
PS_RE_C='(Update|Read|Write|Check) STATE\.md|STATE\.md`? (updated|read|checked|written|exists)'

# Família D — o caminho de estado INJETADO em prompt de subagente. A leitura
# acontece FORA do arquivo medido: o workflow entrega o caminho num
# `<files_to_read>`, o subagente lê o markdown do outro lado, e uma métrica
# aplicada só ao workflow declara verde com o arquivo ainda sendo lido. Por
# isso a forma é CLASSE, não caso a caso.
#
# MEDIDO (2026-08-11, árvore inteira de cairn/gsd/): a forma tem TRÊS grafias e
# a regex morde exatamente 3 linhas, zero falso-positivo —
# `plan-phase.md:695` e `verify-work.md:709` (`- {state_path} (Project State)`)
# e `execute-phase.md:750` (`- ${PROJECT_ROOT}/.planning/STATE.md (State)`).
#
# POR QUE ISTO NÃO É REDUNDANTE COM A FAMÍLIA B, e por que a terceira grafia
# muda o placar: as duas primeiras JÁ casam a família B pelo literal
# `{state_path}` — só elas, a família D não acrescenta cobertura ali. A
# terceira NÃO casa NADA hoje: não tem comando de leitura (família A), não usa
# nenhuma das quatro grafias de variável (família B) e não é prosa (família C).
# O 36-PATTERNS §5b listou CINCO sítios de injeção e não a inclui; medida aqui,
# a lista é de seis, e a que faltava é justamente a que nenhuma família via.
#
# O RÓTULO ENTRE PARÊNTESES É PARTE DA FORMA, não enfeite: a injeção vive numa
# lista de arquivos a ler, e toda entrada dessas listas carrega o rótulo
# (`(Project State)`, `(State)`, `(Plan)`, `(Project context)`). Exigi-lo é o
# que separa a injeção de um caminho de estado numa lista de arquivos a
# COMMITAR (a forma `- \`.planning/STATE.md\``), que é política de commit e não
# leitura — mordê-la obrigaria uma isenção permanente para descrever
# comportamento correto, o ruído que o cabeçalho recusa. Uma injeção escrita sem
# rótulo escaparia; nenhuma das seis medidas é assim, e a fronteira fica escrita
# em vez de suposta.
#
# A ÂNCORA DESSA FRONTEIRA ERA `quick.md:617` E NÃO É MAIS, por medição da onda
# 7. A onda 4 manteve aquela linha citando `readModifyWriteStateMd`, que descreve
# o UPSTREAM; medido no binário da casa, `quick-tasks-append` cria um bead e
# `state.record-session` transiciona o portador, e o sha1 do markdown de estado
# não muda em nenhum dos dois. A linha era peso morto numa lista de commit e caiu
# junto com as três irmãs de `execute-phase.md`. A REGRA continua exatamente como
# está escrita acima — a fronteira entre ler e commitar não depende de existir um
# sítio vivo dela — e o caso de falso-positivo abaixo a exercita com a forma, que
# é o que precisa continuar não sendo mordido.
PS_RE_D='^[[:space:]]*-[[:space:]]+`?(\$\{?(STATE_PATH|STATE_FILE)\}?|\{state_path\}|[^[:space:]|]*STATE\.md)`?[[:space:]]*\('

# Família B — estado por VARIÁVEL: as quatro grafias, uma por linha, casadas
# como texto literal. Cada ocorrência remanescente exige linha própria em
# PS_EXEMPTIONS. `state_exists` NÃO está aqui, por decisão escrita no
# cabeçalho.
PS_PATTERNS_B='STATE_PATH
{state_path}
STATE_FILE
state_raw'

# --- as tabelas ---------------------------------------------------------------

# SOB O ORÁCULO — caminho relativo a cairn/gsd/ | onda que o pôs aqui |
# o que a fase fez com os BYTES do arquivo (editado|intocado).
#
# POR QUE A TERCEIRA COLUNA. Estar sob esta métrica e ter os bytes mudados são
# coisas DIFERENTES, e a onda 6 provou a diferença: dos 16 agentes, 8 nunca
# foram tocados (não têm preâmbulo, não chamam o dispatcher) e ainda assim têm
# zero sítio de estado — é medição publicada, não edição. Registrá-los em
# `cairn/gsd-adaptations.json` para satisfazer um vínculo simples reprovaria os
# DOIS sentidos do oráculo de bytes de `cairn-vendoring.bats` ("a adaptação
# registrada sumiu" e "registrados que não divergem"), porque o registro
# significa "diverge do upstream de propósito", não "foi conferido". A coluna
# escreve qual é o caso e o teste de completude confere os dois sentidos.
PS_ADAPTED="\
agents/gsd-advisor-researcher.md|6|intocado
agents/gsd-code-reviewer.md|6|editado
agents/gsd-codebase-mapper.md|6|editado
agents/gsd-debug-session-manager.md|6|editado
agents/gsd-debugger.md|6|editado
agents/gsd-executor.md|7|editado
agents/gsd-integration-checker.md|6|editado
agents/gsd-nyquist-auditor.md|6|intocado
agents/gsd-pattern-mapper.md|6|editado
agents/gsd-phase-researcher.md|6|editado
agents/gsd-plan-checker.md|6|editado
agents/gsd-planner.md|6|editado
agents/gsd-ui-auditor.md|6|editado
agents/gsd-ui-checker.md|6|editado
agents/gsd-ui-researcher.md|6|editado
agents/gsd-verifier.md|6|editado
gsd-core/workflows/autonomous.md|5|editado
gsd-core/workflows/autonomous/steps/converge-banner.md|7|intocado
gsd-core/workflows/autonomous/steps/converge-dispatch-bg.md|7|intocado
gsd-core/workflows/autonomous/steps/converge-dispatch-inline.md|7|intocado
gsd-core/workflows/autonomous/steps/converge-fail-fast.md|5|editado
gsd-core/workflows/autonomous/steps/converge-loop.md|7|intocado
gsd-core/workflows/debug.md|3|editado
gsd-core/workflows/discuss-phase.md|4|editado
gsd-core/workflows/discuss-phase/modes/advisor.md|4|editado
gsd-core/workflows/discuss-phase/modes/all.md|7|intocado
gsd-core/workflows/discuss-phase/modes/analyze.md|7|intocado
gsd-core/workflows/discuss-phase/modes/auto.md|7|editado
gsd-core/workflows/discuss-phase/modes/batch.md|7|intocado
gsd-core/workflows/discuss-phase/modes/chain.md|4|editado
gsd-core/workflows/discuss-phase/modes/default.md|7|editado
gsd-core/workflows/discuss-phase/modes/power.md|7|editado
gsd-core/workflows/discuss-phase/modes/text.md|7|editado
gsd-core/workflows/discuss-phase/templates/context.md|7|editado
gsd-core/workflows/discuss-phase/templates/discussion-log.md|7|intocado
gsd-core/workflows/execute-phase.md|7|editado
gsd-core/workflows/execute-phase/steps/codebase-drift-gate.md|7|editado
gsd-core/workflows/execute-phase/steps/executor-isolation-dispatch.md|7|editado
gsd-core/workflows/execute-phase/steps/gap-closure-artifacts.md|7|editado
gsd-core/workflows/execute-phase/steps/partial-wave.md|7|editado
gsd-core/workflows/execute-phase/steps/per-plan-worktree-gate.md|7|editado
gsd-core/workflows/execute-phase/steps/post-merge-gate.md|7|editado
gsd-core/workflows/execute-phase/steps/regression-gate-run.md|7|editado
gsd-core/workflows/execute-phase/steps/regression-gate.md|7|editado
gsd-core/workflows/execute-phase/steps/worktree-recovery-policy.md|7|intocado
gsd-core/workflows/fast.md|3|editado
gsd-core/workflows/plan-phase.md|5|editado
gsd-core/workflows/plan-phase/steps/adr-ingest-express-path.md|7|editado
gsd-core/workflows/plan-phase/steps/chunked-planning-mode.md|5|editado
gsd-core/workflows/plan-phase/steps/closed-phase-gate.md|7|intocado
gsd-core/workflows/plan-phase/steps/prd-express-gate.md|7|editado
gsd-core/workflows/plan-phase/steps/prd-express-path.md|5|editado
gsd-core/workflows/plan-phase/steps/research-only-early-exit.md|7|intocado
gsd-core/workflows/plan-phase/steps/research-only-modifiers.md|7|editado
gsd-core/workflows/plan-phase/steps/reviews-prerequisite.md|7|intocado
gsd-core/workflows/plan-phase/steps/stall-detection-helpers.md|5|editado
gsd-core/workflows/plan-phase/steps/windows-troubleshooting.md|7|intocado
gsd-core/workflows/quick.md|4|editado
gsd-core/workflows/quick/steps/discussion-phase.md|7|editado
gsd-core/workflows/quick/steps/plan-checker-loop.md|7|intocado
gsd-core/workflows/quick/steps/quick-verification.md|7|editado
gsd-core/workflows/quick/steps/research-phase.md|4|editado
gsd-core/workflows/quick/steps/worktree-pre-dispatch-commit.md|4|editado
gsd-core/workflows/verify-work.md|5|editado
gsd-core/workflows/verify-work/steps/automated-ui-verification.md|7|intocado
gsd-core/workflows/verify-work/steps/mvp-uat-framing.md|5|editado
"

# ISENÇÕES — caminho|padrão|contagem esperada|motivo escrito.
# Vazia hoje: os arquivos das ondas 3 a 6 entram todos com zero isenção.
PS_EXEMPTIONS="\
"

# SÍTIOS PENDENTES — caminho|família|contagem medida hoje|plano que fecha|motivo.
#
# POR QUE ISTO NÃO É UMA LINHA DE PS_EXEMPTIONS, que seria o lugar óbvio:
# `ps_exempt_count` só é consultada para caminhos que estão em PS_ADAPTED, e
# nenhum destes está (são das ondas 5 e 7). Uma linha de isenção para caminho
# não adaptado é INERTE — não afirma nada, não reprova nada, e sobreviveria
# calada ao plano que a deveria matar. Exatamente a "isenção que nunca morre"
# que o cabeçalho recusa.
#
# A COLUNA DE FAMÍLIA entrou na onda 6. A tabela nasceu só da família D, e a
# medição dos 16 agentes achou uma pendência de família C — o critério de
# sucesso do gsd-executor, num arquivo que o plano 06 tem PROIBIDO de tocar
# (execute-phase e seu agente são do 07). Sem a coluna, a pendência viraria
# silêncio ou uma segunda tabela quase idêntica.
#
# A tabela é conferida por teste próprio, nos DOIS sentidos e com duas forças
# independentes matando cada linha quando o plano que a fecha passar: a
# contagem cai de 1 para 0 (pendência morta), e o caminho aparece em
# PS_ADAPTED (declarado pendente e adaptado ao mesmo tempo).
# VAZIA desde a onda 7, e vazia é o estado CORRETO no fim da fase: as duas
# linhas que ela carregava (`execute-phase.md` família D e `agents/gsd-executor.md`
# família C) morreram nos commits que fecharam os sítios, cada uma pelas duas
# forças — a contagem caiu para zero e o caminho entrou em PS_ADAPTED. A tabela
# fica no arquivo, com o mecanismo intacto: é ela que permite a uma onda futura
# declarar "medi, achei, e o plano me proíbe de tocar" sem virar silêncio.
PS_PENDING="\
"

# --- o oráculo ----------------------------------------------------------------

# Contagem declarada para (caminho, padrão) na tabela de isenções; 0 quando a
# tabela não fala do par. Lê PS_EXEMPTIONS do escopo — cada teste bats roda em
# subprocesso próprio, então um teste que a sobrescreve para forjar um caso não
# vaza para os outros.
ps_exempt_count() {
  local path="$1" pat="$2" f_path f_pat f_count total=0
  while IFS='|' read -r f_path f_pat f_count _; do
    [ -n "$f_path" ] || continue
    [ "$f_path" = "$path" ] || continue
    [ "$f_pat" = "$pat" ] || continue
    total=$((total + f_count))
  done <<EOF
$PS_EXEMPTIONS
EOF
  echo "$total"
}

# ps_family_re <A|C|D> — a regex da família, para a tabela de pendentes poder
# nomear qual delas o sítio ainda casa. A família B fica de fora de propósito:
# ela é lista literal, não regex, e uma pendência dela seria uma linha de
# PS_EXEMPTIONS no dia em que o caminho entrasse na tabela de adaptados. Pedir
# B aqui morre nomeado em vez de devolver regex vazia, que casaria tudo.
ps_family_re() {
  case "$1" in
    A) printf '%s' "$PS_RE_A" ;;
    C) printf '%s' "$PS_RE_C" ;;
    D) printf '%s' "$PS_RE_D" ;;
    *) echo "família sem regex nesta tabela: '$1' (esperado A, C ou D)" >&2
       return 2 ;;
  esac
}

# ps_registry_agrees <raiz> <registro> — a terceira coluna de PS_ADAPTED contra
# `cairn/gsd-adaptations.json`, nos DOIS sentidos. Lê PS_ADAPTED do escopo.
ps_registry_agrees() {
  local root="$1" registry="$2" path bytes n fails=0
  while IFS='|' read -r path _ bytes _; do
    [ -n "$path" ] || continue
    if [ ! -f "$root/$path" ]; then
      echo "caminho da tabela ausente do disco: $path (raiz $root)" >&2
      fails=$((fails + 1))
      continue
    fi
    n="$(jq -r --arg p "$path" \
      '[.adaptations[] | select(.path == $p)] | length' "$registry")"
    case "$bytes" in
      editado)
        [ "$n" = "1" ] && continue
        echo "declarado editado mas não registrado em gsd-adaptations.json: $path (encontrado $n) — o oráculo de bytes reprovaria o mesmo arquivo por outro motivo" >&2
        fails=$((fails + 1))
        ;;
      intocado)
        [ "$n" = "0" ] && continue
        echo "declarado intocado mas REGISTRADO em gsd-adaptations.json: $path (encontrado $n) — o registro afirma bytes divergentes do upstream, e este arquivo não os tem" >&2
        fails=$((fails + 1))
        ;;
      *)
        echo "coluna de bytes desconhecida em $path: '$bytes' (esperado editado|intocado)" >&2
        fails=$((fails + 1))
        ;;
    esac
  done <<EOF
$PS_ADAPTED
EOF
  [ "$fails" -eq 0 ]
}

# assert_no_state_facts <raiz> <caminho relativo>...
# Aplica as quatro famílias a cada caminho e nomeia cada resíduo no stderr. A
# raiz é argumento para que o controle negativo aponte o MESMO laço para uma
# árvore forjada (molde assert_cut_holds:466-492 e o controle negativo :509-518;
# as âncoras :422-448/:465-474 do 36-PATTERNS envelheceram com a edição do 36-01).
assert_no_state_facts() {
  local root="$1"; shift
  local fails=0 path hits pat want found
  for path in "$@"; do
    [ -n "$path" ] || continue
    if [ ! -f "$root/$path" ]; then
      echo "declarado adaptado mas ausente da raiz: $path (raiz $root)" >&2
      fails=$((fails + 1))
      continue
    fi
    hits="$(grep -nE "$PS_RE_A" "$root/$path" || true)"
    if [ -n "$hits" ]; then
      echo "família A (leitura mecânica do arquivo de estado) em $path:" >&2
      echo "$hits" >&2
      fails=$((fails + 1))
    fi
    hits="$(grep -nE "$PS_RE_C" "$root/$path" || true)"
    if [ -n "$hits" ]; then
      echo "família C (prosa imperativa sobre o arquivo de estado) em $path:" >&2
      echo "$hits" >&2
      fails=$((fails + 1))
    fi
    hits="$(grep -nE "$PS_RE_D" "$root/$path" || true)"
    if [ -n "$hits" ]; then
      echo "família D (caminho de estado injetado em prompt de subagente) em $path:" >&2
      echo "$hits" >&2
      fails=$((fails + 1))
    fi
    while IFS= read -r pat; do
      [ -n "$pat" ] || continue
      found="$(grep -oF -- "$pat" "$root/$path" | wc -l | tr -d ' ')" || true
      want="$(ps_exempt_count "$path" "$pat")"
      [ "$found" = "$want" ] && continue
      if [ "$found" -lt "$want" ]; then
        echo "isenção morta: $path padrão '$pat' esperado $want, encontrado $found — o sítio sumiu e a linha da tabela ficou" >&2
      else
        echo "família B (estado por variável) não declarada: $path padrão '$pat' esperado $want, encontrado $found" >&2
      fi
      fails=$((fails + 1))
    done <<EOF
$PS_PATTERNS_B
EOF
  done
  [ "$fails" -eq 0 ]
}

# Os caminhos da tabela de adaptados, um por linha.
ps_adapted_paths() {
  local line
  while IFS='|' read -r line _; do
    [ -n "$line" ] || continue
    echo "$line"
  done <<EOF
$PS_ADAPTED
EOF
}

# Os caminhos da tabela de pendentes, um por linha.
ps_pending_paths() {
  local line
  while IFS='|' read -r line _; do
    [ -n "$line" ] || continue
    echo "$line"
  done <<EOF
$PS_PENDING
EOF
}

# ps_scope_paths <raiz> — o escopo declarado por D-02, computado do DISCO e não
# de uma segunda lista à mão: os workflows raiz COM seus fragments, e os agentes.
# Derivar do disco é o que faz a completude valer para o futuro — uma lista
# escrita à mão concordaria consigo mesma para sempre, e um arquivo novo entraria
# na árvore calado. A raiz é argumento pelo mesmo motivo das outras funções: o
# controle negativo aponta o mesmo laço para uma árvore forjada.
ps_scope_paths() {
  local root="$1"
  ( cd "$root" 2>/dev/null || return 1
    find gsd-core/workflows -type f -name '*.md'
    find agents -type f -name '*.md' ) | LC_ALL=C sort
}

# ps_scope_covered <raiz> — a completude nos DOIS sentidos. O esperado é
# ESCOPO menos PENDENTES: um caminho declarado pendente está em escopo e
# deliberadamente fora da tabela de adaptados (a asserção de adaptado
# reprovaria nele, que é o ponto de declará-lo pendente). Sem esse desconto a
# tabela de pendentes ficaria impossível de usar, e uma onda futura teria de
# escolher entre mentir na tabela e não declarar a pendência.
ps_scope_covered() {
  local root="$1" fails=0 p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    echo "no escopo e fora das duas tabelas: $p — decida o que ele é (adaptado, com a coluna de bytes, ou pendente com família e plano que o fecha) em vez de deixá-lo sem vigilância" >&2
    fails=$((fails + 1))
  done < <(comm -23 \
    <(comm -23 <(ps_scope_paths "$root") <(ps_pending_paths | LC_ALL=C sort)) \
    <(ps_adapted_paths | LC_ALL=C sort))
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    echo "na tabela de adaptados e fora do escopo do disco: $p — ou o arquivo sumiu da árvore, ou a linha descreve um caminho que D-02 não cobre" >&2
    fails=$((fails + 1))
  done < <(comm -13 \
    <(comm -23 <(ps_scope_paths "$root") <(ps_pending_paths | LC_ALL=C sort)) \
    <(ps_adapted_paths | LC_ALL=C sort))
  [ "$fails" -eq 0 ]
}

# --- a asserção sobre a árvore real -------------------------------------------

@test "os arquivos adaptados nao tem sitio de estado em nenhuma das quatro familias" {
  local -a paths=()
  local p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    paths+=("$p")
  done < <(ps_adapted_paths)
  # A tabela cresce plano a plano (fecha no 36-07). Enquanto ela está vazia a
  # liveness desta métrica é provada só pelos controles forjados abaixo.
  if [ "${#paths[@]}" -eq 0 ]; then
    skip "tabela de adaptados vazia — nenhum arquivo sob o oráculo ainda"
  fi
  run assert_no_state_facts "$PS_ROOT" "${paths[@]}"
  [ "$status" -eq 0 ]
}

@test "controle negativo: numa copia forjada, um sitio de cada uma das tres primeiras familias e mordido e nomeado" {
  # A metade de liveness de A, B e C. A cópia parte de um arquivo REAL já
  # adaptado, e recebe um sítio por família — três quebras independentes, três
  # frases distintas. Compartilhar mensagem esconderia qual família está de pé.
  # A família D tem controle próprio no teste seguinte, porque a grafia que a
  # prova é justamente a que as outras três não veem.
  local forged="$BATS_TEST_TMPDIR/forjada"
  local rel="gsd-core/workflows/debug.md"
  mkdir -p "$forged/$(dirname "$rel")"
  cp "$PS_ROOT/$rel" "$forged/$rel"
  {
    echo 'STATE_CONTENT=$(cat .planning/STATE.md 2>/dev/null || true)'
    echo 'STATE_PATH=$(_gsd_field "$INIT" state_path)'
    echo '**Update STATE.md for phase start:**'
  } >> "$forged/$rel"

  run assert_no_state_facts "$forged" "$rel"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "família A (leitura mecânica"
  printf '%s' "$output" | grep -qF "família C (prosa imperativa"
  printf '%s' "$output" | grep -qF "família B (estado por variável) não declarada"
  printf '%s' "$output" | grep -qF "STATE_PATH"
  printf '%s' "$output" | grep -qF "$rel"
}

@test "controle negativo: a injecao reinjetada num arquivo ja adaptado e mordida e nomeada" {
  # A metade de liveness da família D. A cópia parte de um arquivo REAL já
  # adaptado (quick.md, onda 4) e recebe de volta UMA linha de injeção — na
  # grafia de CAMINHO LITERAL, medida em execute-phase.md:750. A grafia
  # importa: reinjetar `- ${STATE_PATH} (Project State)` faria o controle
  # passar pela família B, provando o oráculo antigo e não a regra nova.
  local forged="$BATS_TEST_TMPDIR/injecao"
  local rel="gsd-core/workflows/quick.md"
  mkdir -p "$forged/$(dirname "$rel")"
  cp "$PS_ROOT/$rel" "$forged/$rel"
  echo '- ${PROJECT_ROOT}/.planning/STATE.md (State)' >> "$forged/$rel"

  run assert_no_state_facts "$forged" "$rel"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "família D (caminho de estado injetado em prompt de subagente)"
  printf '%s' "$output" | grep -qF ".planning/STATE.md (State)"
  # E a linha reinjetada NÃO é vista por nenhuma das outras três — medido no
  # arquivo forjado, não inferido da mensagem: se alguma a visse, a família D
  # seria decorativa e o sítio já estaria coberto. (Um `grep -qv` sobre a saída
  # não serviria: com várias linhas ele passa por qualquer linha que não case,
  # o que é sempre.)
  run bash -c 'grep -cE "$1" "$2"' _ "$PS_RE_A" "$forged/$rel"
  [ "$output" = "0" ]
  run bash -c 'grep -cE "$1" "$2"' _ "$PS_RE_C" "$forged/$rel"
  [ "$output" = "0" ]
  run bash -c 'grep -cF "STATE_PATH" "$1"' _ "$forged/$rel"
  [ "$output" = "0" ]
}

@test "falso-positivo: leitura legitima de documento nao casa nenhuma das quatro familias" {
  # As formas medidas de leitura de DOCUMENTO, copiadas dos sítios reais
  # (discuss-phase.md:238-239 e :85, plan-phase.md:1356, debug.md:40 e :71).
  # Sem este caso a suíte empurraria a conversão de documento em verbo, que o
  # CONTEXT proíbe como regressão.
  #
  # As quatro últimas linhas são a fronteira da família D, e existem porque a
  # regra nova é a que mais fácil derraparia para cima de documento: entregar
  # o caminho de um DOCUMENTO a um subagente (contexto do projeto, plano,
  # decisões do usuário) é legítimo e não casa, e o caminho de estado numa
  # lista de arquivos a COMMITAR, sem rótulo, também não — é política de
  # commit, não leitura.
  local fx="$BATS_TEST_TMPDIR/documento"
  mkdir -p "$fx/gsd-core/workflows"
  cat > "$fx/gsd-core/workflows/doc.md" <<'EOF'
cat .planning/PROJECT.md 2>/dev/null || true
cat .planning/REQUIREMENTS.md 2>/dev/null || true
1. Read the phase goal from ROADMAP.md
Read at most **3** prior CONTEXT.md files, most recent first.
ls .planning/debug/*.md 2>/dev/null | grep -v resolved
Check `.planning/debug/{SLUG}.md` exists. If not, print "No debug session found".
- ${PROJECT_PATH} (Project context)
- ${QUICK_DIR}/${quick_id}-PLAN.md (Plan)
- .planning/phases/${PADDED_PHASE}/${PADDED_PHASE}-CONTEXT.md (User decisions)
- `.planning/STATE.md`
EOF
  run assert_no_state_facts "$fx" "gsd-core/workflows/doc.md"
  [ "$status" -eq 0 ]
}

@test "state_exists e campo do bundle, nao familia B: consumi-lo nao e sitio de estado" {
  # As três linhas reais que consomem o campo de existência do bundle
  # (autonomous.md:101 e :104, execute-phase.md:152). Se elas casassem a
  # família B, quatro sítios CORRETOS exigiriam isenção permanente nos planos
  # 05 e 07 — descrever comportamento certo com uma linha de exceção.
  local fx="$BATS_TEST_TMPDIR/bundle"
  mkdir -p "$fx/gsd-core/workflows"
  cat > "$fx/gsd-core/workflows/bundle.md" <<'EOF'
Parse JSON for: `phase_dir`, `state_exists`, `commit_docs`.
**If `state_exists` is false:** Error — "No STATE.md found. Run `/gsd:new-milestone` first."
**If `state_exists` is false but `.planning/` exists:** Offer reconstruct or continue.
EOF
  run assert_no_state_facts "$fx" "gsd-core/workflows/bundle.md"
  [ "$status" -eq 0 ]
}

@test "a tabela de isencoes e conferida nos dois sentidos: morta reprova, sitio novo reprova" {
  local fx="$BATS_TEST_TMPDIR/isencao"
  local rel="gsd-core/workflows/isento.md"
  mkdir -p "$fx/$(dirname "$rel")"
  cat > "$fx/$rel" <<'EOF'
STATE_PATH=$(_gsd_field "$INIT" state_path)
API_SURFACE_PATH="$(dirname "$STATE_PATH")/intel/API-SURFACE.md"
EOF

  # Contagem exata declarada: verde.
  PS_EXEMPTIONS="$rel|STATE_PATH|2|transporte de caminho, não leitura de fato"
  run assert_no_state_facts "$fx" "$rel"
  [ "$status" -eq 0 ]

  # Sentido A — isenção morta: a tabela declara mais do que existe.
  PS_EXEMPTIONS="$rel|STATE_PATH|3|declarada a mais"
  run assert_no_state_facts "$fx" "$rel"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "isenção morta"
  printf '%s' "$output" | grep -qF "esperado 3, encontrado 2"

  # Sentido B — sítio novo: a tabela declara menos do que existe.
  PS_EXEMPTIONS="$rel|STATE_PATH|1|declarada a menos"
  run assert_no_state_facts "$fx" "$rel"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "família B (estado por variável) não declarada"
  printf '%s' "$output" | grep -qF "esperado 1, encontrado 2"

  # Tabela muda: tudo é sítio novo.
  PS_EXEMPTIONS=""
  run assert_no_state_facts "$fx" "$rel"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "esperado 0, encontrado 2"
}

@test "os sitios pendentes sao conferidos nos dois sentidos, por familia, e morrem com o plano que os fecha" {
  local path fam count plan fails=0 found adapted re
  while IFS='|' read -r path fam count plan _; do
    [ -n "$path" ] || continue
    if [ ! -f "$PS_ROOT/$path" ]; then
      echo "declarado pendente mas ausente do disco: $path" >&2
      fails=$((fails + 1))
      continue
    fi
    if ! re="$(ps_family_re "$fam")"; then
      fails=$((fails + 1))
      continue
    fi
    found="$(grep -cE "$re" "$PS_ROOT/$path" || true)"
    if [ "$found" -lt "$count" ]; then
      echo "pendência morta: $path família $fam esperado $count, encontrado $found — o sítio sumiu (plano $plan) e a linha da tabela ficou" >&2
      fails=$((fails + 1))
    elif [ "$found" -gt "$count" ]; then
      echo "sítio novo não declarado: $path família $fam esperado $count, encontrado $found" >&2
      fails=$((fails + 1))
    fi
    adapted="$(ps_adapted_paths | grep -cxF "$path" || true)"
    if [ "$adapted" != "0" ]; then
      echo "declarado pendente E adaptado ao mesmo tempo: $path — o plano $plan passou e a linha de pendência tem de morrer" >&2
      fails=$((fails + 1))
    fi
  done <<EOF
$PS_PENDING
EOF
  [ "$fails" -eq 0 ]
}

@test "controle negativo: a tabela de pendentes reprova nos dois sentidos e quando o sitio e adaptado" {
  # Mesma metade de liveness das outras famílias, aplicada à tabela: uma
  # pendência declarada a mais, uma a menos, e uma que já foi adaptada.
  local fx="$BATS_TEST_TMPDIR/pendente"
  local rel="gsd-core/workflows/pendente.md"
  mkdir -p "$fx/$(dirname "$rel")"
  printf '%s\n' '- {state_path} (Project State)' > "$fx/$rel"

  # Contagem exata: a checagem passa.
  run bash -c 'grep -cE "$1" "$2"' _ "$PS_RE_D" "$fx/$rel"
  [ "$output" = "1" ]

  # Sentido A — pendência morta: o sítio some e a linha fica.
  printf '%s\n' '- ${PROJECT_PATH} (Project context)' > "$fx/$rel"
  run bash -c 'grep -cE "$1" "$2"' _ "$PS_RE_D" "$fx/$rel"
  [ "$output" = "0" ]

  # Sentido B — sítio novo entrando pela porta dos fundos, na grafia literal.
  printf '%s\n' '- {state_path} (Project State)' > "$fx/$rel"
  printf '%s\n' '- ${PROJECT_ROOT}/.planning/STATE.md (State)' >> "$fx/$rel"
  run bash -c 'grep -cE "$1" "$2"' _ "$PS_RE_D" "$fx/$rel"
  [ "$output" = "2" ]

  # A terceira força: um caminho não pode ser pendente e adaptado ao mesmo
  # tempo. Nenhum dos declarados está na tabela de adaptados hoje.
  local p
  while IFS='|' read -r p _; do
    [ -n "$p" ] || continue
    run bash -c 'printf "%s\n" "$1" | grep -cxF "$2" || true' _ "$(ps_adapted_paths)" "$p"
    [ "$output" = "0" ]
  done <<EOF
$PS_PENDING
EOF

  # A coluna de família, que a onda 6 acrescentou, também tem de morder: uma
  # família sem regex nesta tabela morre NOMEADA em vez de devolver regex
  # vazia, que casaria toda linha de todo arquivo e daria a pendência por
  # cumprida.
  run ps_family_re B
  [ "$status" -eq 2 ]
  printf '%s' "$output" | grep -qF "família sem regex nesta tabela: 'B'"
  run ps_family_re C
  [ "$status" -eq 0 ]
  [ "$output" = "$PS_RE_C" ]
}

@test "completude parcial: todo caminho da tabela existe no disco e a coluna de bytes bate com gsd-adaptations.json nos dois sentidos" {
  # O fecho TOTAL — a tabela cobrir os 8 workflows raiz e os 16 agentes — é do
  # plano 36-07; a onda 6 pôs os 16 agentes (15 aqui, o executor é do 07 e está
  # na tabela de pendentes). Aqui vale a metade parcial, agora nos DOIS
  # sentidos: quem a fase EDITOU está registrado como divergência autorizada
  # (senão o oráculo de bytes de cairn-vendoring.bats reprova o mesmo arquivo
  # por outro motivo), e quem está INTOCADO não está registrado (registrar um
  # byte-idêntico ao upstream reprova aquele mesmo oráculo pelo outro lado).
  [ -f "$PS_ADAPTATIONS" ]
  run ps_registry_agrees "$PS_ROOT" "$PS_ADAPTATIONS"
  [ "$status" -eq 0 ]
}

@test "completude: o escopo do disco e as duas tabelas sao o MESMO conjunto, nos dois sentidos" {
  # O FECHO da fase 36. Até a onda 6 a cobertura era parcial por desenho (a
  # tabela crescia plano a plano); aqui ela para de ser opcional. É este caso
  # que impede a fase 37, ao mexer no plugin, de deixar um arquivo do escopo
  # fora da vigilância sem ninguém notar: o escopo sai do `find`, não de uma
  # lista, então acrescentar um workflow, um fragment ou um agente reprova a
  # suíte até que alguém decida se ele é adaptado ou pendente.
  run ps_scope_covered "$PS_ROOT"
  [ "$status" -eq 0 ]
  # E o número, publicado: 66 arquivos no escopo, nenhum pendente hoje.
  [ "$(ps_scope_paths "$PS_ROOT" | wc -l | tr -d ' ')" -eq 66 ]
  [ "$(ps_adapted_paths | wc -l | tr -d ' ')" -eq 66 ]
}

@test "controle negativo: a completude reprova nos dois sentidos, e a pendencia desconta do escopo" {
  # A metade de liveness do caso acima, na árvore forjada. Três defeitos, três
  # frases distintas — um arquivo do escopo que ninguém declarou, uma linha da
  # tabela sem arquivo no disco, e a prova de que declarar pendência é o que
  # tira o primeiro do vermelho (senão a tabela de pendentes seria inutilizável
  # e a onda seguinte teria de mentir para ficar verde).
  local fx="$BATS_TEST_TMPDIR/completude"
  mkdir -p "$fx/gsd-core/workflows/execute-phase/steps" "$fx/agents"
  printf 'prosa\n' > "$fx/gsd-core/workflows/coberto.md"
  printf 'prosa\n' > "$fx/gsd-core/workflows/execute-phase/steps/esquecido.md"
  printf 'prosa\n' > "$fx/agents/agente.md"

  # Sentido A — um arquivo do escopo fora das duas tabelas.
  local PS_ADAPTED="\
gsd-core/workflows/coberto.md|7|intocado
agents/agente.md|7|intocado
"
  local PS_PENDING=""
  run ps_scope_covered "$fx"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "no escopo e fora das duas tabelas"
  printf '%s' "$output" | grep -qF "steps/esquecido.md"

  # Declarar a pendência tira exatamente esse do vermelho — e nada mais.
  PS_PENDING="gsd-core/workflows/execute-phase/steps/esquecido.md|D|1|36-08|forjado
"
  run ps_scope_covered "$fx"
  [ "$status" -eq 0 ]

  # Sentido B — uma linha da tabela que o disco não tem.
  PS_ADAPTED="\
gsd-core/workflows/coberto.md|7|intocado
gsd-core/workflows/fantasma.md|7|intocado
agents/agente.md|7|intocado
"
  run ps_scope_covered "$fx"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "na tabela de adaptados e fora do escopo do disco"
  printf '%s' "$output" | grep -qF "fantasma.md"

  # E a tabela consertada fica verde pelo MESMO laço — senão as duas asserções
  # acima estariam reprovando por qualquer motivo em vez dos dois nomeados.
  PS_ADAPTED="\
gsd-core/workflows/coberto.md|7|intocado
agents/agente.md|7|intocado
"
  run ps_scope_covered "$fx"
  [ "$status" -eq 0 ]
}

@test "controle negativo: a coluna de bytes reprova nos dois sentidos, e uma coluna desconhecida nao passa calada" {
  # A metade de liveness da coluna que a onda 6 acrescentou. Três defeitos,
  # três frases distintas: um editado que ninguém registrou, um intocado
  # registrado como se divergisse, e uma coluna que não é nenhum dos dois.
  local base="$BATS_TEST_TMPDIR/coluna"
  mkdir -p "$base/arvore/w"
  printf 'prosa\n' > "$base/arvore/w/editado.md"
  printf 'prosa\n' > "$base/arvore/w/intocado.md"
  printf 'prosa\n' > "$base/arvore/w/estranho.md"
  printf '%s\n' '{"schema_version":1,"adaptations":[{"path":"w/intocado.md","phase":"36","waves":[6],"reason":"forjado"}]}' \
    > "$base/registro.json"

  local PS_ADAPTED="\
w/editado.md|6|editado
w/intocado.md|6|intocado
w/estranho.md|6|conferido
"
  run ps_registry_agrees "$base/arvore" "$base/registro.json"
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF "declarado editado mas não registrado"
  printf '%s' "$output" | grep -qF "w/editado.md"
  printf '%s' "$output" | grep -qF "declarado intocado mas REGISTRADO"
  printf '%s' "$output" | grep -qF "w/intocado.md"
  printf '%s' "$output" | grep -qF "coluna de bytes desconhecida"
  printf '%s' "$output" | grep -qF "'conferido'"

  # E a tabela consertada fica verde pelo mesmo laço — senão a asserção acima
  # estaria reprovando por qualquer motivo, não pelos três nomeados.
  printf '%s\n' '{"schema_version":1,"adaptations":[{"path":"w/editado.md","phase":"36","waves":[6],"reason":"forjado"}]}' \
    > "$base/registro.json"
  PS_ADAPTED="\
w/editado.md|6|editado
w/intocado.md|6|intocado
"
  run ps_registry_agrees "$base/arvore" "$base/registro.json"
  [ "$status" -eq 0 ]
}

# --- o ponta a ponta que ADAPT-02 pede ---------------------------------------

# Extrai o bloco ```bash do arquivo que CONTÉM a agulha, verbatim. Extrair do
# arquivo, e não redigitar o comando no teste, é o que faz a prova valer: um
# teste que digitasse a linha passaria com o arquivo errado.
ps_extract_bash_block() {
  awk -v needle="$2" '
    /^```bash$/ { inb = 1; buf = ""; next }
    /^```$/     { if (inb && buf ~ needle) { printf "%s", buf; exit }
                  inb = 0; buf = ""; next }
    inb         { buf = buf $0 "\n" }
  ' "$1"
}

@test "ponta a ponta: o bloco de fast.md roda num repo de fixture e o fato fica no bd" {
  # O caminho que o usuário executa, e o mesmo que o incidente de estado
  # obsoleto atravessava. O ambiente é decepado (`env -u`) e o binário é
  # resolvido pela cadeia do próprio preâmbulo a partir do cwd — molde
  # run_form_in de cairn-preamble.bats.
  require_bd
  local fx="$BATS_TEST_TMPDIR/e2e" block
  mkdir -p "$fx/.planning"
  git init -q "$fx"
  git -C "$fx" config user.email "cairn-tests@example.com"
  git -C "$fx" config user.name "Cairn Tests"
  echo '{}' > "$fx/.planning/config.json"
  # O elo 3 da cadeia do preâmbulo é `$PWD/cairn/scripts/cairn-gsd.sh`: o
  # fixture ganha a árvore do checkout por link, e não uma variável de
  # ambiente que pularia a resolução sob teste.
  ln -s "$CAIRN_REPO_ROOT/cairn" "$fx/cairn"
  ( cd "$fx" && bd init -q --prefix e2e --non-interactive ) >/dev/null 2>&1

  block="$(ps_extract_bash_block "$PS_ROOT/gsd-core/workflows/fast.md" \
    'quick-tasks-append')"
  [ -n "$block" ]
  printf '%s' "$block" | grep -qF 'gsd_run quick-tasks-append'
  # O predicado saiu do markdown: nada consulta um arquivo para decidir se
  # chama o verbo.
  run bash -c 'printf %s "$1" | grep -c "^if "' _ "$block"
  [ "$output" = "0" ]

  printf '%s' "$block" > "$fx/bloco.sh"
  run env -u CLAUDE_PROJECT_DIR -u CAIRN_GSD TASK='tarefa de ponta a ponta' \
    bash -c "cd '$fx' && bash ./bloco.sh"
  [ "$status" -eq 0 ]
  [ "$(bd -C "$fx" list -l gsd-quick-task --all --limit 0 --json \
      | jq 'length')" -eq 1 ]
}

@test "ponta a ponta: o gate de intel de plan-phase le a indisponibilidade do binario e segue sem o artefato" {
  # ADAPT-05, item intel — a metade EXECUTADA da decisão. As quatro famílias
  # não veem este sítio: ele não lê estado, ele consome o payload de uma
  # capability. Sem este caso, `divergences.json` afirmaria que o sítio trata a
  # resposta e nada na suíte checaria se ele ainda a trata.
  #
  # O bloco é EXTRAÍDO do arquivo, nunca redigitado aqui: um teste que
  # redigitasse o `if` passaria com o workflow errado.
  local fx="$BATS_TEST_TMPDIR/intel" block
  mkdir -p "$fx"
  block="$(ps_extract_bash_block "$PS_ROOT/gsd-core/workflows/plan-phase.md" \
    'intel api-surface')"
  [ -n "$block" ]

  {
    printf 'gsd_run() { "%s/cairn/scripts/cairn-gsd.sh" "$@"; }\n' "$CAIRN_REPO_ROOT"
    # `$(...)` come a newline final do bloco: sem o \n aqui o `fi` colaria na
    # linha seguinte e o arquivo nem seria bash válido.
    printf '%s\n' "$block"
    printf 'printf "API_SURFACE_PATH=[%%s]\\n" "$API_SURFACE_PATH"\n'
  } > "$fx/bloco.sh"

  run env -u CLAUDE_PROJECT_DIR -u CAIRN_GSD \
    bash -c "cd '$fx' && bash ./bloco.sh"
  # exit 0: indisponibilidade DECLARADA não derruba o planejamento.
  [ "$status" -eq 0 ]
  # A razão vem do binário e chega ao humano DENTRO da frase do passo. Medido:
  # exigir só a razão solta seria decoração — a forma cega despeja o payload
  # inteiro em stdout, então a razão aparece nela também e a asserção passaria
  # com o sítio errado. A frase inteira, numa linha, é o que separa as duas.
  printf '%s' "$output" | grep -qF "intel unavailable, planning without an API surface: $(
    "$CAIRN_REPO_ROOT/cairn/scripts/cairn-gsd.sh" intel api-surface \
      | jq -r '.reason')"
  # E as duas consequências que o passo 8 consome: caminho VAZIO (a entrada de
  # API Surface some do prompt do planner) e nenhuma alegação de regeneração.
  printf '%s' "$output" | grep -qF 'API_SURFACE_PATH=[]'
  printf '%s' "$output" | grep -qvF 'API surface regenerated' || {
    echo "o sítio declarou o artefato regenerado com a capability desligada" >&2
    return 1
  }
}

@test "controle negativo: o gate de intel que IGNORA o payload entrega ao planner o caminho de um arquivo que ninguem escreveu" {
  # A metade de liveness do caso acima, na forma exata que o sítio tinha antes
  # desta onda: rodar o subcomando, montar o caminho e ecoar "regenerated" sem
  # olhar para a resposta. As MESMAS asserções do caso acima têm de cair.
  local fx="$BATS_TEST_TMPDIR/intel-cego"
  mkdir -p "$fx"
  {
    printf 'gsd_run() { "%s/cairn/scripts/cairn-gsd.sh" "$@"; }\n' "$CAIRN_REPO_ROOT"
    printf 'PROJECT_ROOT="%s"\n' "$fx"
    printf 'gsd_run intel api-surface >/dev/null\n'
    printf 'API_SURFACE_PATH="${PROJECT_ROOT}/.planning/intel/API-SURFACE.md"\n'
    printf 'echo "✓ API surface regenerated: ${API_SURFACE_PATH}"\n'
    printf 'printf "API_SURFACE_PATH=[%%s]\\n" "$API_SURFACE_PATH"\n'
  } > "$fx/bloco.sh"

  run env -u CLAUDE_PROJECT_DIR -u CAIRN_GSD \
    bash -c "cd '$fx' && bash ./bloco.sh"
  [ "$status" -eq 0 ]
  # 1) a razão do binário NÃO aparece — o payload foi jogado fora
  run bash -c 'printf %s "$1" | grep -cF "$2" || true' _ "$output" \
    "$("$CAIRN_REPO_ROOT/cairn/scripts/cairn-gsd.sh" intel api-surface | jq -r '.reason')"
  [ "$output" = "0" ]
  # 2) o caminho NÃO está vazio, e 3) o passo afirma ter regenerado
  run bash -c 'bash "$1/bloco.sh"' _ "$fx"
  printf '%s' "$output" | grep -qF 'API surface regenerated'
  run bash -c 'printf %s "$1" | grep -cF "API_SURFACE_PATH=[]" || true' _ "$output"
  [ "$output" = "0" ]
  # E o arquivo que o caminho promete de fato não existe.
  [ ! -f "$fx/.planning/intel/API-SURFACE.md" ]
}
