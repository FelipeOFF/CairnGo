---
description: Ship — verify every completed phase's beads are closed, then GSD ship / push
group: loop
---

Pre-ship gate, then ship:

1. Run the deterministic gate first:
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-gate.sh"` — exit 6 means blocked
   (it lists the offending issue ids); exit 5 means bd is unavailable (warn,
   then check manually as below). If the script is unavailable, check by hand:
   for each completed phase `N`, `bd list -l m-<milestone>,phase-<N> --all`
   must show no non-closed issue (milestone from ROADMAP.md's current
   milestone header; any status other than `closed` blocks). If anything is
   non-closed, **stop** and report it — do not push.
2. When all completed phases are clean, run `/gsd:ship` to finalize (it handles
   the push). If the project doesn't use `/gsd:ship`, push the branch directly.

Never push with non-closed issues on a phase marked done. The git pre-push
shim installed by `/cairn:init` enforces this same gate outside the agent.
