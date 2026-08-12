**Step 7.1 detail — `class == "quota-exceeded"` recovery.**

Do not offer "retry now". Run the step-5 spot-check first; if SUMMARY.md is missing but
commits exist, route to safe-resume (`state.verify-against-disk`) instead of an immediate
redispatch.

**7.1a — automatic provider escalation does not exist in this installation.** Upstream GSD
swaps PROVIDER on a quota failure (#2296, opt-in through `dynamic_routing.provider_escalation`)
by asking the binary which execution target comes next. That verb is outside the cairn
universe of 87: the dispatcher answers

```text
[cairn-gsd] error: verbo desconhecido (fora do universo do contrato)
```

on stderr with exit 2 and writes nothing to stdout. The branch that used to read the answer
piped that empty string through five `jq` filters with no `|| true` and no default. Measured:
the pipe does not abort — `jq` on empty input exits 0 and prints nothing — so all five
variables come out EMPTY, and empty is neither `"true"` nor `"false"`, so NONE of the three
prose branches below matched. On a quota failure, the one moment this path exists for, the
step went silent. There is no ladder to configure and none to spend: recovery here is MANUAL,
and 7.1b below is the whole of it. Escalating later is adding the handler plus its golden and
restoring this branch; until then the degraded behaviour is written down instead of breaking
mid-pipe. The decision is recorded in `tests/fixtures/gsd-goldens/divergences.json`.

**7.1b — manual recovery (the only path).**

```text
⚠ Plan {plan_id} terminated by provider quota / rate limit
  Runtime sentinel: {SENTINEL}
  {RETRY_HINT}
  Partial commits on worktree branch: {N}
  SUMMARY.md present: {yes|no}
  1. Wait for quota reset, then resume (recommended)
2. Switch to a different runtime / model and resume
3. Abort phase and report partial state
```

Never silently retry the same runtime: name the quota failure and hand the choice over.
Re-run `/gsd:execute-phase` after the quota resets for Option 1. Option 2 is a change of
runtime or model in the invocation itself — nothing in this installation rewrites it for you.
