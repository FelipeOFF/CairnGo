---
description: Run a command from an external GSD install — raw passthrough, and cairn does not require one
argument-hint: <gsd-command> [args…]
group: escape
---

Raw GSD passthrough — no cairn orchestration. Invoke:

```text
/gsd:$ARGUMENTS
```

The first token is the GSD command name, the rest are its arguments
(e.g. `/cairn:gsd debug`, `/cairn:gsd new-milestone`, `/cairn:gsd help`).

**This addresses an EXTERNAL gsd-core, which cairn no longer installs or
requires.** Since v1.6 the GSD runtime is vendored inside the plugin, and
`/cairn:doctor` reports an installed gsd-core as something to uninstall — two
lineages answering `/gsd:*` and `/cairn:*` at the same time is the defect the
vendoring closed. This command survives as the escape hatch for someone who
keeps a gsd-core installed for their own reasons and wants one of the verbs
cairn's own loop does not carry; on a clean cairn install `/gsd:*` does not
resolve and this command has nothing to reach.
