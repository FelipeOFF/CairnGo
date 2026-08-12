# Phase 35: O binário python, checagem e verbos órfãos - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 6 (1 script novo, 1 dispatcher modificado, harness + goldens estendidos, registro de baseline do doctor, wrapper .sh opcional)
**Analogs found:** 5 / 6 (o avaliador de predicado do ADR-2008 e o passthrough do run-with-timeout não têm análogo completo em código — ver No Analog Found)

## File Classification

| Arquivo novo/modificado | Role | Data Flow | Análogo mais próximo | Qualidade |
|---|---|---|---|---|
| `cairn/scripts/cairn-gsd-check.py` (novo) | verb-handler CLI (checagem 11 + órfãos 5 = 16 verbos) | request-response sobre `.planning/` (documento) + subprocess passthrough (run-with-timeout) | `cairn-gsd-state.py` (forma inteira do irmão) + `cairn-status.py` (leitura de artefatos de fase) + `cairn-doctor.py` (parse de PLAN.md) | exact (forma) / role-match (fontes) |
| `cairn/scripts/cairn-gsd.py` (mod) | dispatcher/roteador | request-response (exec pro irmão) | ele próprio (FAMILY_SCRIPT + script_for + agregação de --list-implemented) | exact |
| `tests/cairn-gsd.bats` (mod) | test harness (diferencial + cobertura) | batch | ele próprio — o seam da 33/34 | exact |
| `tests/fixtures/gsd-goldens/scenarios.json` + `*.golden.json` (novos cenários) | fixture | — | os 107 cenários / 110 goldens existentes | exact |
| Registro de baseline do doctor (CHECK-04 — forma a decidir no plano) | config/test | — | `TAG_COMMIT` (cairn-gsd.py:99), `source.commit` dos goldens, byte-parity de cairn-vendoring.bats:179-189 | role-match |
| `cairn-gsd-check.sh` (opcional) | wrapper shell | — | `cairn/scripts/cairn-gsd.sh` | exact |

Universo da fase (16 = 87 − 71, de `cairn/gsd/contracts/`):
- **checagem (11, checagem.json):** check, check.decision-coverage-plan, uat.classify-coverage, uat.render-checkpoint, user-story.validate, verification.status, verify, verify.artifacts, verify.commits, verify.key-links, verify.plan-structure
- **órfãos (5, misc.json com source_ref do bundle bakeado — REM-04):** audit-open, review-lane, agent.classify-failure, task.is-behavior-adding, run-with-timeout — hoje `ORPHANS_PHASE_35` em cairn-gsd.py:139-145

**As duas grafias de verification.status JÁ estão contratadas nos spellings** (checagem.json, verbo verification.status: `["query verification status", "query verification.status"]`). `build_routes` (cairn-gsd.py:184-214) registra todo spelling do contrato, e o loop de despacho (L2080-2084) tenta do maior n-grama pro menor — a grafia espaçada de 3 palavras casa em n=3 SEM mudança no dispatcher. Nenhuma tabela nova de normalização é necessária; o análogo do upstream (gsd-tools.cjs L3826-L3835) já está absorvido pelo mecanismo de spellings.

## Pattern Assignments

### `cairn/scripts/cairn-gsd-check.py` (verb-handler, checagem + órfãos)

**Análogo primário:** `cairn/scripts/cairn-gsd-state.py` — copiar a forma inteira do irmão:

- **Docstring-contrato** (cairn-gsd-state.py:1-18): usage, exit codes um a um, regras medidas com data, "cairn/gsd/ é SOMENTE-LEITURA". A versão do check acrescenta a doutrina própria da família: *veredito no payload (passed/active/block/valid), NUNCA no exit — exit 0 = gate avaliado* (checagem.json, exit_codes de check/verify/verify.plan-structure).
- **Imports + render como fonte única** (L27-30): `sys.path.insert(0, str(Path(__file__).resolve().parent))` e `from cairn_gsd_render import (_UNDEFINED, emit, js_string, output_like_binary, parse_verb_args, stringify)`. O módulo (cairn_gsd_render.py, 81 linhas) já existe: `js_string` L27-45 (String(v) do JS), `stringify` L48-49 (JSON.stringify(v, null, 2)), `emit` L52-53 (sem newline final), `output_like_binary` L56-60, `parse_verb_args` L63-81 (value_flags/bool_flags, flag desconhecida ignorada best-effort). **Consumir, nunca duplicar.**
- **Constantes de exit + die** (L32-37, L97-99): `EXIT_OK/CONTRACT/USAGE/UNIMPLEMENTED`, `TAG_PREFIX = "[cairn-gsd-check]"`.
- **HANDLERS + main** (L1439-1469 e L1482-1496): dict verbo→handler ordenável, `--list-implemented` imprime `sorted(HANDLERS)` (L1486-1489), verbo sem handler → die exit 4 nomeando a família via `family_of` (L1472-1480) — a mensagem do check diz "fase 35".

**Dispatchers internos (check e verify são comandos de família):** o contrato manda `check` normalizar pontos→hifens no subcommand e rotear 12 subcommands; `verify` roteia por VERIFY_SUBCOMMANDS; subcommand desconhecido é `error()` exit 1 (checagem.json, notes dos verbos check/verify). O molde de tabela interna é o próprio HANDLERS dict; nenhum roteador genérico novo — um dict subcommand→função dentro do handler do verbo de família basta.

**Leitura de artefatos de fase (documento) — reaproveitar por cópia de forma:**

- `verification.status` → `verification_status(pdir)` (cairn-status.py:1066-1085) já resolve o `status:` literal do frontmatter de `NN-VERIFICATION.md` com regex leniente (sem lib YAML):

```python
    candidates = sorted(p for p in pdir.iterdir()
                        if p.is_file() and p.name.endswith("-VERIFICATION.md"))
    ...
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^status\s*:\s*(.+?)\s*$", line)
```

  E a escada de estado do disco (cairn-status.py:903-912): `has("-VERIFICATION.md")` → verified; planos done/total; `has("-SUMMARY.md")` → executed. A tabela `next_action/next_command` (VERIFICATION_ROUTING_TABLE do upstream) vem do contrato, não tem análogo — implementar da shape contratada (`next_action, next_command, status, verification_stale_check_indeterminate`).

- `verify.plan-structure` → frontmatter: `parse_frontmatter_lines(text)` (cairn-gsd-init.py:876-890, subset YAML plano com span do bloco) é o parser da casa — os handlers `frontmatter.get/set/validate` (L940/L961/L1004) já o exercitam. Campos de PLAN.md: `parse_plan_files_modified` (cairn-doctor.py:1999-2013, `files_modified:` inline e em lista) e o filtro de superseded (`phase_files_modified`, cairn-doctor.py:2033-2045). O fail-loud em NUL/binário (#2701) e a validação de tasks vêm do contrato (shape `valid/errors/warnings/tasks/task_count/frontmatter_fields/path/error`; arquivo inexistente = `{error}` com exit 0).
- Regexes de fase/plano: `PHASE_DIR_PREFIX`/`PLAN_FILE`/`SUMMARY_FILE` já existem em cairn-status.py:385-387 E em cairn-gsd-state.py:93-95 — copiar do irmão (terceira cópia idêntica é aceitável na casa; import cruzado entre irmãos não tem precedente).
- `task.is-behavior-adding` lê um arquivo de task (path fora do escopo → error USAGE exit 1); `audit-open` varre `.planning/` inteiro (shape `counts/has_open_items/items/scanned_at`). Análogo de varredura + shape defensivo: a família phase.* do irmão de estado.

**Órfãos de classificação pura:** `agent.classify-failure` (texto→class, misc.json com AGENT_FAILURE_CLASSES) e `review-lane` (dado estático REVIEWER_LANES; o único sítio do universo usa o subcommand `flags`, saída `kind: text` linha a linha) — sem análogo necessário além da forma de handler; a semântica inteira está nas notes/source_ref de misc.json (proveniência do bundle declarada).

**`run-with-timeout` — análogo PARCIAL:** a casa tem subprocess com timeout, mas sempre capturando saída:

```python
# cairn-gsd.py:818-832 — run_git: TimeoutExpired vira valor, nunca traceback
    try:
        proc = subprocess.run(["git"] + list(argv), capture_output=True,
                              text=True, cwd=str(cwd) if cwd else None,
                              timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return None, "", str(e), True
```

(mesma forma em check_bd_doctor, cairn-doctor.py:1609-1620, timeout=60 → status warn). O verbo exige o CONTRÁRIO da captura: passthrough de stdout/stderr do filho e a tabela de exits do GNU timeout — `0..255` do comando, `124` estouro, `125` spawn genérico, `126` EACCES, `127` ENOENT, `128+n` morto por sinal (misc.json). Argv do comando é OPACO — o dispatcher já entrega isso de graça: depois de casar o spelling em n=1, `argv[n:]` segue intocado pro exec (nenhum parse global de flags acontece antes, cairn-gsd.py:2075-2077 só rejeita flag ANTES do verbo). Ver No Analog Found para o substituto.

---

### `cairn/scripts/cairn-gsd.py` (modificado — rotas da checagem e fim dos órfãos)

**O que muda, com âncoras:**

1. `FAMILY_SCRIPT` (L120-125) ganha `"checagem": "cairn-gsd-check.py"`. Isso sozinho já cobre roteamento (via `script_for` L231) E agregação de `--list-implemented` — o loop L2059 itera `sorted(set(FAMILY_SCRIPT.values()))`, então o irmão novo entra na enumeração sem tocar o bats.
2. `PHASE_BY_FAMILY` (L106-113): a entrada `"checagem": "fase 35"` (L112) vira mensagem de estado transitório (irmão ausente do disco) — mesmo papel que as entradas da 34 durante as ondas.
3. **ARMADILHA DE ROTEAMENTO (a maior da fase):** esvaziar `ORPHANS_PHASE_35` (L139-145) NÃO manda os órfãos pro check — manda pro ramo misc de `script_for` (L228-230), que os despacha pra `cairn-gsd-init.py` (verbo sem handler lá → die exit 4 "fase 34", mensagem ERRADA). Os 5 órfãos são família `misc` e precisam de rota EXPLÍCITA pro irmão check. A forma mínima no molde existente: repor a constante por um set de roteamento (ex.: `CHECK_MISC_VERBS`, molde `MISC_STATE_VERBS` L129-137) e estender o ramo misc de `script_for` para três destinos. O D-01 diz "perde a constante da lista de EXCLUSÃO" — a lista muda de papel (exclusão→rota), não de existência.
4. `phase_for` (L217-220) perde o caso especial de órfão (L218) junto com a exclusão.
5. O ponto de exec NÃO muda (L2092-2098): `script_for` devolvendo o script novo já cai no `os.execv` existente com o verbo canônico.

**ARMADILHA GÊMEA NO BATS:** `dispatcher_orphans()` (tests/cairn-gsd.bats:567-578) deriva a lista dos órfãos por regex sobre a CONSTANTE NOMINAL:

```python
m = re.search(r"ORPHANS_PHASE_35 = frozenset\(\((.*?)\)\)", src, re.S)
if not m:
    sys.exit("ORPHANS_PHASE_35 não encontrada no dispatcher")
```

Se a fase RENOMEIA ou DELETA a constante, essa função mata a suíte inteira de cobertura. `frozenset(())` vazio ainda casa o regex (grupo vazio → zero verbos → exclusão nula). O plano precisa mover dispatcher e bats NA MESMA ONDA: ou esvazia mantendo o nome (e o guard fecha sozinho), ou renomeia e atualiza `dispatcher_orphans`/`trivial_verbs_of` juntos.

---

### `tests/cairn-gsd.bats` + `tests/fixtures/gsd-goldens/` (estendidos — o seam da 33/34)

**Cenário novo = manifesto + golden irmão, nenhuma linha do runner muda.** O seam continua o mesmo da 34: entrada em `scenarios.json` (107 hoje) + `<id>.golden.json` (110 arquivos); integridade por `comm` dois-sentidos (L385-395), serialização da casa `jq -S` + newline (L426), determinismo (L344).

**Guard de cobertura — as duas mudanças obrigatórias** (`trivial_verbs_of`, L583-592):

```bash
trivial_verbs_of() {
  jq -r '.verbs | to_entries[]
    | select(.value.family == "config" or .value.family == "commit"
      or .value.family == "skills" or .value.family == "loop-hooks"
      or .value.family == "dispatch-model" or .value.family == "estado"
      or .value.family == "roadmap-phase" or .value.family == "worktree"
      or .value.family == "init" or .value.family == "misc")
    | .key' "$1" | sort \
    | comm -23 - <(dispatcher_orphans | sort)
}
```

A 35 soma `or .value.family == "checagem"` (10→11 famílias, universo fecha 87) e a exclusão `comm -23` zera (via constante vazia ou remoção coordenada — ver armadilha acima). O teste de cobertura (L594-612) e o controle negativo do verbo forjado (L632) não mudam. A cobertura cruzada contra o corpus real (L745) é skip-gated e também não muda.

**Fixtures:** os verbos de checagem leem DOCUMENTO — `fixture.files` + `fixture.git`/`fixture.git_commit` (build_scenario_fixture, L75-121) cobrem quase tudo; `fixture.bd` (L99-121, da 34) fica disponível se algum veredito cruzar fato do bd. Shape real de cenário com bd (state-load-fato-ausente):

```json
{"fixture": {"bd": {"init": true, "prefix": "sfa", "seed": []},
             "files": {}, "git": true, "planning_config": {}}}
```

**Provenance: `recorded` VOLTA a ser possível.** O bloqueio da 34 (verbo que responde do bd não pode ser gravado do binário real) não se aplica aqui — checagem lê markdown/filesystem, exatamente o que o recorder reproduz. `cairn-gsd-record.py` + os skip-gates (cairn-gsd.bats:1479-1481: cache do clone, node, runtime buildado) permitem goldens `recorded` para o diferencial do CHECK-02; `derived-from-contract` (comparação por FORMA, L239, schema L331) segue válido onde gravar não compensar. Divergência consciente → `tests/fixtures/gsd-goldens/divergences.json` (schema testado em L861-870), nunca silenciada.

**Masks por VALOR para os campos de tempo do payload.** `free_of_timestamp_keys` (L378-383) proíbe as CHAVES `timestamp/recorded_at/generated_at/date/time` — `scanned_at` (payload do audit-open) NÃO está na lista, então a chave pode existir no golden, mas o valor precisa de mask. Molde real (cenário commit-committed): `"mask": {".hash": "^[0-9a-f]{7,40}$"}`; `apply_mask_file` (L167-179) valida o valor contra o regex e troca por `<masked>` — valor que não casa é ERRO, não skip.

---

### Baseline do doctor (CHECK-04 — registro verificável, forma a decidir)

**Fatos medidos em 2026-08-11 (HEAD 76ef1fa):**
- `wc -l cairn/scripts/cairn-doctor.py` → **3907**
- último commit que o toca: `git log -1 --format=%h -- cairn/scripts/cairn-doctor.py` → **a2527ee** (2026-08-07, "feat(doctor): a checagem 23...")
- blob: `git hash-object cairn/scripts/cairn-doctor.py` → **e2040aea2068967eaec204e049fff0dbceb2ef50**
- suíte: tests/cairn-doctor.bats com 124 @test

**Moldes de registro na casa (o plano escolhe a combinação):**
- **Pin por commit em constante:** `TAG_COMMIT = "68a04cc..."` (cairn-gsd.py:99) — um hash com dono e comentário.
- **Pin por proveniência em fixture:** o campo `source.commit` de todo golden (schema testado em cairn-gsd.bats:331).
- **Prova de não-mudança por bytes:** `assert_tree_bytes_match` (tests/cairn-vendoring.bats:179-189) e o teste "byte-identical to the pinned cache" (L503) — a forma de um teste que REPROVA se o arquivo mudou. A versão mínima pro doctor: um registro (commit + blob hash) num arquivo da fase e um teste bats que compara `git hash-object` corrente com o registrado — falha nomeada se alguém evoluir o doctor dentro da 35.

## Shared Patterns

### Veredito no payload, NUNCA no exit
**Fonte:** checagem.json, exit_codes de check ("0: gate avaliado — o veredito vai no payload (passed/active/block), nunca no exit"), verify ("veredito em block/directive"), verify.plan-structure ("veredito em valid/errors"; arquivo inexistente = `{error}` com exit 0) + doutrina do CONTEXT.
**Aplicar a:** todos os 11 de checagem + task.is-behavior-adding. Exit 1 é reservado a erro de USO contratado (subcommand desconhecido, --file ausente, path inválido) — os cenários de golden precisam separar "gate reprovou" (exit 0, payload false) de "gate não avaliou" (exit 1).

### Envelope de saída na fonte única
**Fonte:** `cairn_gsd_render.py` (módulo inteiro, 81 linhas) — semântica medida do io.cts.
**Aplicar a:** todo verbo do irmão novo. `--raw` = String(valor) (`js_string`); default = JSON.stringify(v, null, 2) (`stringify`); sem newline final (`emit`). `review-lane` é `kind: text` — emite linha a linha fora do envelope JSON, conforme contrato.

### Falha nomeada (die com o fato E o remédio)
**Fonte:** cairn-gsd-state.py:97-99 (die) + L176-178 (`die_missing_dim` — nomeia a dimensão E o comando que a cria) + cairn-gsd.py:2099-2101.
**Aplicar a:** artefato de fase ausente quando o contrato manda exit 1 (ex.: uat.render-checkpoint com --file inexistente), subcommand desconhecido (mensagem "Unknown ... Available: ..." na forma do contrato), contrato ilegível (`load_json_strict`, cairn-gsd.py:171-181). Nunca traceback.

### Subprocess defensivo
**Fonte:** cairn-gsd.py:818-832 (run_git com timeout, TimeoutExpired→valor), cairn-doctor.py:1609-1620 (timeout com degradação nomeada), cairn-gsd-state.py:102-112 (run_bd).
**Aplicar a:** qualquer subprocess do irmão — EXCETO o run-with-timeout, que inverte a captura (passthrough) e traduz a morte do filho em exit code contratado, não em die.

### Docstring-contrato no topo
**Fonte:** cairn-gsd-state.py:1-18 e cairn-gsd.py:1-69.
**Aplicar a:** cairn-gsd-check.py. Usage, exits, doutrina do veredito-no-payload, teto 1.5k declarado, "cairn/gsd/ é SOMENTE-LEITURA", divergências em divergences.json.

## No Analog Found

| Padrão | Verbo(s) | Motivo | O que usar no lugar |
|---|---|---|---|
| Avaliador de predicado (ADR-2008) | check (subcommand predicate) | Nenhum avaliador de expressão/predicado em `cairn/scripts/*.py` (grep: só menções em comentário — cairn-doctor.py:120/1083, cairn-capability.py:48) | Implementar da semântica do contrato (checagem.json, notes de check: "avaliador genérico que recebe --flag value pairs"); diferencial por CENÁRIO no harness contra o gsd-tools real da tag via `--record` skip-gated (CHECK-02, discrição do CONTEXT) |
| Subprocess passthrough com exits GNU-timeout | run-with-timeout | Todo subprocess da casa captura saída; nenhum devolve 124/125/126/127/128+n | `subprocess.Popen` SEM capture (herda stdout/stderr) + `wait(timeout)` + kill de process group no estouro; tabela de exits e regras de `<seconds>` (sufixo 's', 0 = sem timer, vazio/negativo = usage exit 2 fail-safe) direto de misc.json; ENOENT→127, EACCES→126, morto por sinal→128+n |
| Parser de seção `## Current Test` de UAT.md | uat.render-checkpoint, uat.classify-coverage | Nenhum script da casa lê UAT.md (grep vazio) | Parse de seção na forma leniente da casa (molde `verification_status`, cairn-status.py:1066-1085: regex + strip, sem lib); shape e casos de erro (sessão completa = exit 1) do contrato; golden `recorded` viável (entrada é arquivo) |

## Metadata

**Analog search scope:** `cairn/scripts/`, `tests/`, `tests/fixtures/gsd-goldens/`, `cairn/gsd/contracts/`
**Files scanned:** 10 scripts (cairn-gsd.py, cairn-gsd-state.py, cairn-gsd-init.py, cairn_gsd_render.py, cairn-status.py, cairn-doctor.py, cairn-gate.py, cairn-bookkeep.py, cairn-capability.py, cairn-gsd-record.py) + 2 bats (cairn-gsd.bats, cairn-vendoring.bats) + 3 contratos (checagem.json, misc.json, roadmap-phase.json) + manifesto/goldens
**Pattern extraction date:** 2026-08-11 (HEAD 76ef1fa, branch feat/v1.6-transplante)
