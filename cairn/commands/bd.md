---
description: Run any beads (bd) command directly — raw passthrough
argument-hint: <bd args…>
---

Raw beads passthrough — no cairn orchestration. Run:

```bash
bd $ARGUMENTS
```

Show the output. Use this for anything the cairn workflow verbs don't cover
(e.g. `/cairn:bd dep add app-1 app-2`, `/cairn:bd prime`, `/cairn:bd show app-7`).
