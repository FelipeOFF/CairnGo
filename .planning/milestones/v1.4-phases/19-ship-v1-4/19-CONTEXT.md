# Phase 19: Ship v1.4 - Context

**Gathered:** 2026-08-01
**Status:** Ready for planning

<domain>
## Phase Boundary

O trabalho das seis fases anteriores chega a quem instalou o plugin. É a única
fase deste milestone cujo produto é lido por quem nunca abriu este repositório.

Requisitos: REL-01 … REL-04. Issues bd: ver `19-BEADS-MAP.md`.

Herdado e **não reaberto**: o formato do CHANGELOG é Keep a Changelog e já está em
uso; o procedimento de release está estabelecido pelas 1.4.0, 1.4.1 e 1.4.2, e as
notas daquelas três são o padrão de voz a seguir — elas abrem pela pergunta do
usuário ("Am I affected?"), não pela lista de mudanças.

</domain>

<decisions>
## Implementation Decisions

### O número

- **D-01: 1.5.0.** Seis fases de recurso novo, compatível para trás — é o que o
  semver pede, e desfaz uma colisão de nomes que já estava confundindo.

  A colisão: o plugin já estava em **1.4.2** e o milestone se chama **v1.4**. Os
  dois eixos vinham parecendo o mesmo número e não são: `v1.4 Honest State` é o
  nome do ciclo de planejamento, `1.5.0` é a versão do plugin que o ciclo entrega.
  A partir daqui os dois deixam de se imitar.

  Rejeitado 1.4.3: as três 1.4.x foram correções sucessivas do mesmo bug, e chamar
  seis fases de recurso de "patch" mente sobre o que mudou. Rejeitado 2.0.0: existe
  um repo privado `cairn2` e um commit que moveu o desenvolvimento 2.0 para lá;
  queimar o número aqui atropela aquele plano, e nada nesta entrega quebra
  compatibilidade.

### O que o lockstep quer dizer

- **D-02: dois eixos, cada um com a sua regra.**

  ```
  plugin.json  ≡  marketplace.json  ≡  topo do CHANGELOG  ≡  git tag
  capability.json  →  eixo próprio, só precisa ser semver válido
  ```

  O REL-02 pede um comando que verifique que as versões "combinam". A tentação é
  igualar tudo, e ela está errada: o `capability.json` está em **1.0.0** de
  propósito — a capability é instalada dentro do `gsd-core` e tem ciclo próprio.
  Forçá-la ao lockstep inventaria uma igualdade que não existe, que é a mesma
  classe de mentira verde que este milestone inteiro combate.

  O comando checa igualdade onde ela é real e validade onde a igualdade não se
  aplica. **O roadmap dizia "dois arquivos" e são três** — o
  `.claude-plugin/marketplace.json` também carrega `1.4.2`, e ninguém tinha
  reparado. Isso é evidência a favor do comando, não contra.

### O que quem já tem instalado precisa fazer

- **D-03: corrigir o `cairn-init.sh` e dizer na release.**

  O `cairn-init.sh` gitignora exatamente três entradas — `.cairn/id-map.json`,
  `.cairn/state.json`, `.cairn/conflicts.json` — e mais nada. O v1.4 acrescentou
  `.cairn/journal.jsonl`, `.cairn/reconcile-evidence.json` e `.cairn/hook.log`, que
  aparecem como arquivo não rastreado na árvore de quem atualizar.

  Não é cosmético: a fase 18 mediu que uma worktree preparada fica `?? .cairn/`
  **para sempre** sem essa regra, e por isso o `cleanup` nunca a considera
  removível. O reparo entra no init, idempotente como as três atuais, e a nota de
  migração vira *"rode `/cairn:init` de novo"* em vez de uma lista de linhas para
  colar à mão.

  Rejeitado só documentar: transfere ao usuário um passo que o próprio plugin sabe
  dar, e as três releases 1.4.x existiram precisamente por pergunta de migração sem
  resposta. Rejeitado corrigir em silêncio: quem não rodar o init nunca entende por
  que apareceu arquivo novo.

### Até onde o agente vai sozinho

- **D-04: preparar tudo, parar antes de publicar.** CHANGELOG, bump, comando de
  verificação, notas derivadas e a tag anotada **criada localmente**. O comando
  exato de `git push` da tag e de `gh release create` é apresentado; quem dispara é
  o Felipe.

  Publicar é irreversível e externo. Uma tag empurrada e uma release publicada são
  lidas por terceiros e ficam indexadas mesmo se removidas depois.

### Claude's Discretion

- Nome do script de verificação e se ele ganha subcomandos.
- Como as notas são derivadas do CHANGELOG (extração da seção da versão).
- Texto exato do CHANGELOG, respeitando o REL-01: em termos de quem usa.
- Se a verificação de versão também vira checagem do `cairn-doctor.py`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O que descrever
- `.planning/ROADMAP.md` — as fases 13 a 18 e o que cada uma entregou
- `.planning/phases/1{3,4,5,6,7,8}-*/1*-CONTEXT.md` — as decisões, para traduzir
  cada uma em benefício de usuário em vez de nome de função

### O padrão de voz das notas
- Releases `v1.4.0`, `v1.4.1`, `v1.4.2` no GitHub — abrem pela pergunta do usuário
  ("Am I affected?"), com um comando que ele roda para descobrir
- `CHANGELOG.md` — Keep a Changelog, entradas em negrito abrindo por uma frase que
  diz o que quebrava

### Código e arquivos que a fase toca
- `cairn/.claude-plugin/plugin.json` — `version` (1.4.2)
- `.claude-plugin/marketplace.json` — `version` (1.4.2), o terceiro portador
- `cairn/capability/capability.json` — `version` (1.0.0), eixo próprio
- `cairn/scripts/cairn-init.sh` — o array `CAIRN_IGNORES`, linhas ~57-61
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cairn-init.sh` já tem o laço idempotente de `.gitignore`; acrescentar entradas é
  estender um array, não escrever mecanismo.
- O CHANGELOG já segue Keep a Changelog com seções `## [x.y.z] - data`, então
  derivar as notas é extrair uma seção, não reescrever.
- As três releases anteriores estabelecem a estrutura das notas.

### Established Patterns
- Todo `cairn-X.py` tem par `.sh` e `tests/cairn-X.bats`.
- Escrita atrás de flag nomeada, leitura por default.
- Um teste que passaria com a feature removida não é prova.

### Integration Points
- Script novo de verificação de versão + par `.sh` + bats próprio.
- `cairn-init.sh` — o array de ignores.
- Possivelmente `cairn-doctor.py`, se a verificação virar checagem.

</code_context>

<specifics>
## Specific Ideas

- **O roadmap desta fase estava desatualizado sobre o próprio alvo.** Ele afirma
  que a versão vive em dois arquivos; são três. O erro foi encontrado ao inventariar
  antes de planejar, e é exatamente o argumento do REL-02: um humano conferindo de
  olho não achou o terceiro em três releases seguidas.

- **A nota de migração tem conteúdo real desta vez.** As três releases 1.4.x
  existiram porque a pergunta "o que eu preciso fazer?" ficou sem resposta. Aqui a
  resposta não é "nada": é rodar `/cairn:init` de novo, e a razão é concreta.

</specifics>

<deferred>
## Deferred Ideas

- Automatizar o bump (um comando que escreve as versões em vez de verificar) —
  verificar é o que o REL-02 pede; escrever é outra decisão.
- Unificar o eixo da capability com o do plugin — rejeitado na D-02 por eliminar
  uma independência que existe de propósito.
- Publicar a release a partir do agente — fora de escopo por decisão, D-04.

</deferred>

---

*Phase: 19-Ship v1.4*
*Context gathered: 2026-08-01*
