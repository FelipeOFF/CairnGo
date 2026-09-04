# CairnGo

![CairnGo — spec · tickets · implement](assets/cairngo-hero.png)

<p align="center">
  <a href="https://github.com/FelipeOFF/CairnGo/actions/workflows/ci.yml"><img src="https://github.com/FelipeOFF/CairnGo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-5.1.0-blue" alt="Version 5.1.0"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
</p>

**Spec-driven development on [beads](https://github.com/gastownhall/beads).**
`/cairn-grill` interviews onto a spec bead. `/cairn-implement` tickets and implements. Specs and tickets live on `bd`. Optional spokes (Jira, GitHub, GitLab, Asana, Azure Boards) mirror that graph. There is no `.planning/` destination and no `CONTEXT.md` as the plan.

Grok: `/cairn-implement`. Claude Code: `/cairn:implement` (also `/cairn:cairn-implement`).

## Install

```bash
# Grok
grok plugin marketplace add FelipeOFF/CairnGo
grok plugin install cairn --trust

# Claude Code
/plugin marketplace add FelipeOFF/CairnGo
/plugin install cairn@cairngo
```

Needs `bd` ≥ 1.1.0 (`brew install beads`). `/cairn-init` offers to install it.

## Loop

```text
/cairn-init                 # git + bd, tracker templates
/cairn-grill                # new idea: interview, write the spec bead, stop
/cairn-implement <spec>     # tickets + implement the frontier
/cairn-status               # READY ∩ ready-for-agent / DOING / BLOCKED
/cairn-doctor               # graph health
/cairn-sync-config          # optional spoke
```

bd is the hub. Jira: spec = Epic, ticket = Story/Task, `bd dep` = blocks, `m-vX.Y` = Fix Version.

## Docs

| Doc | What's inside |
|---|---|
| [Plugin README](cairn/README.md) | model, commands, spoke map |
| [Sync](cairn/docs/sync.md) | hub-and-spoke adapters |
| [BENCHMARKS.md](BENCHMARKS.md) | harness, corpus, measured cells |
| [CHANGELOG](CHANGELOG.md) | release history |

## Benchmarks

<!-- cairn:generated:benchmarks-teaser:start -->
**24 benchmark cell(s)** measured (20260727-haiku-4-5); full methodology, raw data and reproduction in [BENCHMARKS.md](BENCHMARKS.md).
<!-- cairn:generated:benchmarks-teaser:end -->

## License

[LICENSE](LICENSE).
