# Milestones

## v1.1 Metrics & Benchmarks (Shipped: 2026-07-27)

**Phases completed:** 6 phases, 14 plans, 17 tasks

**Known deferred items at close:** 2 (verification gaps das fases 04/06 — coleta live bloqueada em ANTHROPIC_API_KEY, ação de operador pós-milestone via `bench-all.sh --yes`; ver STATE.md Deferred Items)

**Key accomplishments:**

- smoke-convert benchmark fixture with an agent-unwritable verify.sh whose exit code is proven (via bats, zero API calls) to be the sole pass/fail signal in both directions
- bench-run.py measurement harness proven at zero API cost: stubbed claude via CAIRN_BENCH_CLAUDE_BIN, one sorted JSONL row per run wired to the real verify.sh, JSON parsed regardless of exit code, byte-identical determinism (wall-clock excluded)
- Two genuinely live claude -p rows committed ($0.1223481 error_max_turns + $0.167407 success, both verify_passed:true), bats stub rebuilt key-for-key against the real schema, README documents real costs with the client-side-estimate caveat, both RESEARCH.md open questions resolved empirically
- Env do subprocess claude agora é um dict explícito {HOME, PATH, ANTHROPIC_API_KEY-se-presente} (substitui, nunca faz merge), com vanilla/gsd-only/cairn como manifests JSON pinados e tudo provado 8/8 em bats a custo $0.
- stage-plugins.py materializa os plugin_dirs pinados dos manifests (clone da tag + build + verificação sintática do MCP entrypoint + .staged-ref + rename atômico), idempotente e fail-loud, provado 5/5 em bats a $0 — e o GSD v4.3.1 E o context-mode v1.0.169 reais foram staged e verificados de verdade.
- bench-matrix.py embaralha os baselines declarados com random.Random(seed) e invoca bench-run.py uma vez por arm na ordem embaralhada, com seed/run_order_index stamped como JSON integers em toda row (contíguos 0..N-1, mesma ordem para o mesmo seed), provado 5/5 em bats a $0 — e o smoke check live de auth isolado documentado honestamente como PENDING (key ausente, re-checada na execução).
- bench-matrix.py now launches N=5 seeded-interleaved repetitions per baseline across the full baseline x rep cross-product, with rep_index provenance stamped into every row via bench-run.py's new optional --rep-index
- Deterministic JSONL aggregator (`bench-aggregate.py`) with belt-and-braces success gating, modelUsage-preferred 4-way token decomposition, and median+min/max/IQR per (task, baseline) cell — proven byte-for-byte against pre-verified expected output at $0.
- Fourth benchmark arm `competitor-ralph-specum` pinned to the live-reconfirmed tag tzachbon/smart-ralph@v4.0.0 with a `defaults_source` audit trail and FAIR-02 byte-identical `claude_flags`/`model` (proven mechanically by `jq -S` diff in bats), plus backward-compatible `plugin_dir_subpath` resolution in bench-run.py so `--plugin-dir` targets the nested `plugins/ralph-specum/` plugin.json — real repo staged and structurally confirmed, 32/32 bats at $0, live load-check explicitly PENDING.
- Five new $0-provable benchmark fixtures (bugfix, feature, refactor-with-anti-cheat, honest-non-win micro-edit, 3-file long-horizon) replicating the smoke-convert contract, each proven in both directions by tests/bench-corpus.bats (10 tests) with zero API involvement.
- bench-matrix.py now runs the full 6-task corpus via --tasks (list or glob) through the identical seeded 4-arm pipeline, the honest-non-win category flows from task.json into every aggregated cell, and the README's corpus rationale / ~$40 cost ceiling / PENDING variance pilot are all CI-enforced by 7 new $0 bats checks.
- Deterministic stdlib-only bench-chart.py turning aggregated.json into byte-identical grouped cost+pass-rate and 4-way token-composition SVG charts, proven by an 8-test bats suite at $0 with zero SVG committed
- Methodology-first BENCHMARKS.md with an honestly-pending generated Results block, README teaser markers, and bench-publish.py regenerating both from aggregated.json with cairn-map.py's proven splice mechanics — all proven by 7 bats tests against temp copies, $0 spent
- bench-all.sh orchestrates stage->matrix->aggregate->chart->publish behind a plan-first print with the verbatim ~$40 ceiling, a tripwire-proven $0 dry-run default, and a --yes+key double gate — 6 new bats tests, 199/199 suite green, zero real-file mutation, zero API spend

---
