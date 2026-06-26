---
description: Run any GSD command directly — raw passthrough
argument-hint: <gsd-command> [args…]
---

Raw GSD passthrough — no cairn orchestration. Invoke:

```text
/gsd:$ARGUMENTS
```

The first token is the GSD command name, the rest are its arguments
(e.g. `/cairn:gsd debug`, `/cairn:gsd new-milestone`, `/cairn:gsd help`).
Use this for any GSD command the cairn workflow verbs don't wrap.
