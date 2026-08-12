#!/usr/bin/env bats
# cairn-doctor-migration.bats — a rota de MIGRACAO do doctor.
#
# A DISTINCAO QUE ESTA SUITE EXISTE PARA DEFENDER, e que e' facil perder:
#
#     ler .planning/ para MIGRAR  !=  ler .planning/ como VERDADE
#
# O milestone v1.7 tira o .planning/ de circulacao: ele deixa de ser fonte de
# estado e deixa de ser escrito. A leitura ingenua dessa decisao — "entao o
# doctor para de olhar para .planning/" — produz uma REGRESSAO, nao a feature.
# Quem instala o cairn quase sempre vem do GSD e chega com um .planning/
# cheio; um doctor cego para esse diretorio deixa essa pessoa sem rota
# nenhuma, e um projeto que se propoe a substituir o GSD tem obrigacao de
# saber ler o que o GSD deixou.
#
# Entao as DUAS frases terminais, que valem para o codigo e para esta suite:
#
#   (1) ANTES de migrar, .planning/ e' lido UMA vez, como ENTRADA da migracao.
#   (2) DEPOIS de migrado, .planning/ nao e' lido nem escrito.
#
# Ha caso de teste abaixo que exige as duas frases NO CODIGO do doctor, e nao
# so num registro de sumario, porque e' precisamente essa a diferenca entre
# "o doctor le markdown" (regressao) e "o doctor reconhece um projeto por
# migrar" (feature). Um leitor futuro que encontre a leitura sem a doutrina ao
# lado vai concluir que ela e' residuo e apaga-la.
#
# MEDIDO ANTES DE ESCREVER CHECAGEM NOVA (2026-08-12), e a medicao mudou o
# desenho: cairn-doctor.py ja tinha o ramo de um-lado-so
# (`if has_planning != has_beads`), mas SIMETRICO — as duas direcoes recebiam
# a mesma frase ("run /cairn:migrate to bootstrap the missing side") e o mesmo
# early-exit com `checks: []`. E cairn-migrate.py `detect` JA classifica
# exatamente esta situacao como estado A (".planning present, .beads absent").
# Logo nao ha classificador novo aqui: a rota REUSA o que existe, e o que
# muda e' que a direcao ".planning sem .beads" ganha vocabulario proprio e
# achado proprio em vez de um dar-de-ombros compartilhado com a direcao
# oposta, que e' outro fato (bootstrap de um repo que nunca teve GSD).
#
# Estilo de assercao: um `[[ ]]` ou `! cmd` no meio do teste NAO reprova neste
# bash, entao substring usa grep -qF -- e negativa usa refute_dm.

load 'helpers'

refute_dm() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

DOCTOR="$CAIRN_SCRIPTS_DIR/cairn-doctor.py"

# Arvore de um projeto que veio do GSD e ainda nao migrou: .planning/ cheio,
# .beads/ ausente. E' o estado A do classificador de cairn-migrate.
make_gsd_only_tree() {
  make_tmp_repo
  mkdir -p .planning/phases/01-auth
  printf -- '# Roadmap\n\n- [x] Phase 1: Auth\n- [ ] Phase 2: API\n' \
    > .planning/ROADMAP.md
  printf -- '# State\n\nactive: 2\n' > .planning/STATE.md
  printf -- '# Plan\n' > .planning/phases/01-auth/01-PLAN.md
}

# O inverso: um repo com beads e sem GSD. NAO e' um GSD por migrar — e' um
# bootstrap. E' o controle negativo da rota inteira.
make_beads_only_tree() {
  make_tmp_repo
  bd init -q --prefix dm --non-interactive >/dev/null 2>&1
}

dm_json() {
  python3 "$DOCTOR" --project-dir . --json 2>/dev/null
}

# --- a rota ------------------------------------------------------------------

@test "doctor-migracao: GSD por migrar vira ACHADO, nao um dar-de-ombros" {
  make_gsd_only_tree
  run bash -c "python3 '$DOCTOR' --project-dir . --json"
  [ "$status" -eq 0 ]
  grep -qF -- "gsd-unmigrated" <<<"$output"
}

@test "doctor-migracao: o achado prescreve a rota de migracao" {
  make_gsd_only_tree
  run bash -c "python3 '$DOCTOR' --project-dir . --json"
  [ "$status" -eq 0 ]
  grep -qF -- "cairn:migrate" <<<"$output"
}

@test "doctor-migracao: o achado REUSA o classificador de cairn-migrate (estado A)" {
  make_gsd_only_tree
  run bash -c "python3 '$DOCTOR' --project-dir . --json"
  [ "$status" -eq 0 ]
  python3 -c "
import json,sys
d = json.loads('''$output''')
found = [c for c in d['checks'] if c['id'] == 'gsd-unmigrated']
assert found, 'nenhum achado gsd-unmigrated em checks[]'
assert found[0].get('state') == 'A', found[0]
"
}

@test "doctor-migracao: o achado conta o que ha para migrar" {
  make_gsd_only_tree
  run bash -c "python3 '$DOCTOR' --project-dir . --json"
  [ "$status" -eq 0 ]
  python3 -c "
import json,sys
d = json.loads('''$output''')
c = [c for c in d['checks'] if c['id'] == 'gsd-unmigrated'][0]
assert c['items'], 'o achado nao nomeia nada para migrar'
"
}

@test "doctor-migracao: o achado NAO reprova o doctor — e' rota, nao falha" {
  make_gsd_only_tree
  run bash -c "python3 '$DOCTOR' --project-dir . --json"
  [ "$status" -eq 0 ]
  python3 -c "
import json,sys
d = json.loads('''$output''')
assert d['failed'] is False, d['failed']
"
}

# --- controles negativos: a rota tem de DISTINGUIR as duas direcoes ---------

@test "doctor-migracao: controle negativo — beads sem GSD NAO e' GSD por migrar" {
  require_bd
  make_beads_only_tree
  run bash -c "python3 '$DOCTOR' --project-dir . --json"
  [ "$status" -eq 0 ]
  refute_dm "gsd-unmigrated"
}

@test "doctor-migracao: controle negativo — arvore vazia NAO e' GSD por migrar" {
  make_tmp_repo
  run bash -c "python3 '$DOCTOR' --project-dir . --json"
  [ "$status" -eq 0 ]
  refute_dm "gsd-unmigrated"
}

@test "doctor-migracao: controle negativo — repo ja fiado NAO e' GSD por migrar" {
  require_bd
  make_gsd_only_tree
  bd init -q --prefix dm --non-interactive >/dev/null 2>&1
  run bash -c "python3 '$DOCTOR' --project-dir . --json"
  refute_dm "gsd-unmigrated"
}

# --- a doutrina mora no CODIGO ----------------------------------------------

@test "doctor-migracao: as duas frases terminais estao NO CODIGO do doctor" {
  run cat "$DOCTOR"
  [ "$status" -eq 0 ]
  # (1) antes de migrar, lido UMA vez, como entrada da migracao
  grep -qiF -- "ENTRADA da migracao" <<<"$output"
  # (2) depois de migrado, nem lido nem escrito
  grep -qiF -- "nao e' lido nem escrito" <<<"$output"
}

@test "doctor-migracao: o codigo diz por que a leitura NAO e' regressao" {
  run cat "$DOCTOR"
  [ "$status" -eq 0 ]
  grep -qiF -- "migrar" <<<"$output"
  grep -qiF -- "VERDADE" <<<"$output"
}
