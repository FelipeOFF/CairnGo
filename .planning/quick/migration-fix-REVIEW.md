# Review — migration fix (migrate/status/doctor/jira)

## 1. [major] cairn/scripts/cairn-doctor.py:685

--close-completed usa semântica ANY sobre labels de fase: fecha issue cross-phase quando QUALQUER phase-N dela está [x] no ROADMAP, mesmo com outra fase ainda ativa. Contradiz cairn-status, que usa ALL (in_done_phase: ns <= done_set, comentário explícito 'a cross-phase issue stays live while any of its phases is still open'). Reproduzido empiricamente: issue com labels phase-1,phase-2,m-v1.0 (fase 1 [x], fase 2 ativa) — cairn-status --json dá stale_complete=[] e a sugere como .next; cairn-doctor --close-completed a fecha ('doctor: phase 1 complete in ROADMAP'). O footer do status manda o usuário rodar exatamente esse flag, que mata a issue que o próprio status recomendou como próxima ação. check_phase_complete_open (linha 468) tem o mesmo ANY, então o WARN também diverge do status. Fora isso o escopo do flag está correto: idempotente (status!=closed), nunca toca quick/unphased (exige label phase-N; quick.md documenta 'no phase-* label'), milestone-scoped via in_milestone.

**Fix:** Alinhar com cairn-status: alvo e check só quando set(phase_nums(i)) é não-vazio E subconjunto de completed_set (todas as fases da issue completas). Aplicar em targets (linha 685) e em check_phase_complete_open (linha 468).

## 2. [major] cairn/scripts/gbsync.py:154

bd_create passa o título vindo do Jira como argumento POSICIONAL de 'bd create' — injeção de argumento. Título '--help' (ou '--dry-run' etc.) é parseado como flag: bd sai 0 imprimindo o help, bd_create devolve o texto inteiro como bd_id, do_import grava esse lixo multi-linha como chave no id-map.json e marca o external_id como mapeado. Reproduzido end-to-end: import reporta 'created=1 skipped=0 failed=0', bd list mostra 0 issues, e id-map.json fica com o help do bd como chave apontando para CHN-666 — o card externo nunca é importado e re-runs o pulam para sempre ('already mapped'). Títulos '-x...' inválidos apenas falham (recuperável), mas qualquer título externo iniciando com '-' entra no parser de flags do bd. bd_apply (pull) não é afetado porque usa --title com valor.

**Fix:** Usar a flag que o próprio bd oferece: ['bd','create','--title',title,'--body-file','-','--silent'] (confirmada no help: '--title  Issue title (alternative to positional argument)'). Adicionalmente validar o id retornado (uma única linha, sem espaços) antes de gravar no id-map.

## 3. [major] cairn/adapters/jira.py:67

O import novo repete o concern conhecido do mapa da codebase: api() chama urllib.request.urlopen(req) SEM timeout, e do_import faz até 3 requests sequenciais por ela; run_adapter no gbsync.py (linha 189) também roda o subprocess sem timeout. Uma conexão travada pendura 'gbsync import' (e o comando de prosa) indefinidamente. Bônus no mesmo ponto: api() só captura HTTPError — URLError (DNS/conn refused) vira traceback cru em vez do fail-loud do contrato. A paginação em si está correta (nextPageToken, cap IMPORT_MAX=200, termina em issues vazio/isLast; sem loop infinito possível pois cada iteração exige issues não-vazio).

**Fix:** urllib.request.urlopen(req, timeout=30) em api() (corrige push/pull/import de uma vez) e capturar urllib.error.URLError com mensagem + sys.exit(1). Opcional: timeout no subprocess.run de run_adapter como cinto de segurança.

## 4. [minor] cairn/scripts/cairn-migrate.py:755

O sweep do modo A tem a mesma semântica ANY do doctor: para cada fase completa n, fecha qualquer issue com label exata 'phase-{n}' — uma issue cross-phase (phase-1 completa + phase-2 viva, m-milestone correto) é varrida e fechada sem confirmação (modo C fica atrás de pending_confirmation; modo A não). Mitigante: o sweep só morde issues pré-existentes quando .beads/ já existe no plan-time (estado A normal tem board vazio). Segundo problema no mesmo ponto: o match é só 'phase-{n}' sem zero-padding, enquanto doctor/status aceitam 'phase-0N' — um filho com label padded escapa do sweep, fica aberto e faz o close do épico falhar (exit 8), exatamente o que o sweep existe para evitar. Proteções que EXISTEM contra fechar errado: quick/unphased intocáveis (exigem label de fase ou parentesco de épico), guard de m-<milestone> para strays de outro milestone, nota no plano listando fases fechadas só por checkbox, e modo C 100% atrás de confirmação.

**Fix:** No sweep: exigir que TODAS as phase-labels da issue estejam completas (mesmo predicado ALL do status), e comparar por número parseado (re ^phase-0*(\d+)$) em vez de string exata.

## 5. [minor] cairn/scripts/cairn-doctor.py:679

--close-completed roda ANTES de check_phase_complete_open computar a nota de divergência checkbox↔artefatos ('confirm the phase is really done before closing'), e após o close as issues somem do escopo do check — a nota é inatingível exatamente na execução em que seria necessária (nenhum teste cobre o combo close+divergência). O doctor.md instrui rodar plain primeiro e confirmar, mas o passo 1 encaminha $ARGUMENTS direto, então '/cairn:doctor --close-completed' digitado pelo usuário pula o fluxo. Além disso, os closes via subprocess 'bd close' não passam pelo hook post-bd-write (nenhum gbsync push) e, diferente do migrate apply, não há lembrete de /cairn:sync-pull quando .cairn/sync.json existe — mirrors externos ficam com N cards abertos silenciosamente.

**Fix:** Antes de fechar, computar disk_done e imprimir a nota de divergência (ou exigir flag extra/recusar nas fases divergentes); imprimir o mesmo lembrete de sync do migrate quando .cairn/sync.json existe.

## 6. [minor] cairn/adapters/jira.py:158

JQL montada por f-string com --project sem validação: 'project = {value} ORDER BY...' — um valor com operadores ('CHN OR assignee is not EMPTY') amplia o escopo da busca. Baixo risco real: roda com o token do próprio usuário, e o feed automático (detect_jira do migrate) só produz prefixos casados por [A-Z][A-Z0-9]+, sem espaço para operadores; a superfície é o usuário digitando --project malicioso, que poderia igualmente usar --query. No mesmo trecho, cfg['project_key'] dá KeyError/traceback cru quando config não tem project_key e query/project são null. Escaping HTTP ok (urllib.parse.quote na query e no token). Títulos importados: sem sanitização de caracteres de controle no dispatcher, mas o render do status já se protege via clean() (teste 'control bytes in titles cannot inject escapes' passa).

**Fix:** Validar project contra ^[A-Z][A-Z0-9_]*$ (mesma forma do detect) e falhar loud; trocar cfg['project_key'] por .get() com mensagem de erro clara.

## 7. [minor] cairn/scripts/cairn-migrate.py:1750

run_with_retry re-executa o handler imediatamente sem refresh do índice: se 'bd create' falhar DEPOIS de criar de fato a issue (exit não-zero pós-criação, ou output não parseável em do_create_epic/do_create_issue), o retry consulta o índice em memória (stale, não contém a issue recém-criada), não a encontra e cria duplicata. A idempotência prometida vale entre re-runs de apply (índice reconstruído do bd vivo), não dentro do retry imediato. Probabilidade baixa, mas é o único ponto onde a garantia 'never produces duplicates' quebra. O journaling de failed em si está correto (failed nunca conta como completed; replay dirigido verificado pelos testes).

**Fix:** Antes do retry de steps create_*, chamar applier.refresh_index() (ou restringir o retry a kinds idempotentes por natureza: close_issue, dep_add, write_file, frontmatter).

## 8. [minor] cairn/scripts/gbsync.py:424

Parsing das flags novas (--query/--project/--backend) faz args[i+1] sem checar bounds: 'gbsync.py import --query' (sem valor) morre com IndexError/traceback em vez do erro de uso. Padrão pré-existente do --since, mas o diff triplica a exposição. Contratos restantes checados sem regressão: exit codes de push/pull intocados, import segue a convenção 0/2 do pull; status --json ganha stale_complete aditivamente (note/--brief atualizados juntos); doctor insere check warn-only sem mudar exit codes e consumidores usam id, não posição; detect --json ganha external.jira aditivamente; o skip de dep_add para blocker completo é mudança intencional coberta por teste atualizado. Bats novos: sem asserções vácuas — todos asseguram estado real do bd/id-map/journal, exit codes e strings exatas, usam o padrão grep -qF/refute_in_output correto para este bash, e as 4 suítes passam integralmente (rodadas nesta review).

**Fix:** Trocar cada 'args[i+1]' por leitura com bounds-check que chama die(usage) quando a flag é o último argumento.
