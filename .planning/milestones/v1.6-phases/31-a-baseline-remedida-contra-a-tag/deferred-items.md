# Deferred items — fase 31

Descobertas fora do escopo dos planos desta fase. Registradas, não corrigidas.

## tests/cairn-trend.bats: "real tree: the series is not contiguous, and the holes are the no-frontmatter cycles" falha pré-existente

- **Descoberto em:** 2026-08-10, na regressão `bats tests/` do plano 31-01.
- **Evidência de pré-existência:** a falha reproduz idêntica no checkout main
  (`~/Projects/CairnGo`), que não contém nenhum commit do plano 31-01. Nenhum
  commit do plano toca `.planning/` nem o trend.
- **Sintoma:** `[ "$holes" -eq "$na" ]` falha em tests/cairn-trend.bats:607 —
  o teste real-tree assume que os vãos da série são exatamente os ciclos
  no-frontmatter, e a forma do `.planning/` mudou com o arquivamento do v1.5
  (2026-08-07) e a abertura do v1.6.
- **Rota sugerida:** revisitar a premissa do teste real-tree contra a árvore
  pós-arquivamento (dono natural: manutenção do cairn-trend, fora desta fase).
