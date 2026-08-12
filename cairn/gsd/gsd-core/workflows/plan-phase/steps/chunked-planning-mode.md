## 8.5. Chunked Planning Mode

**Skip if `CHUNKED_MODE` is `false`.**

Chunked mode splits the single planner run into a short outline run + N short per-plan
runs (~3–5 min each), committing each plan individually for crash resilience. Rerunning
`/gsd:plan-phase {N} --chunked` resumes from the last committed plan.

For recovering plans from a prior *non-chunked* run, use step 6's "Add more plans" or
proceed to `/gsd:execute-phase` — don't start a fresh chunked run over them.

### 8.5.1 Outline Phase (outline-only mode, ~2 min)

**Resume detection:** the outline is not persisted — it is cheap (~2 min) and
reproducible, and what a crash must not lose is the PLANS. So the resume signal
is the plan records themselves: if the phase already has plan records, the
outline ran, and 8.5.2 resumes from them.

```bash
EXISTING_PLANS=$(bd list -l "phase-${PHASE_NUMBER}" --all --limit 0 --json \
  | jq -r '[.[] | select((.labels // []) | any(startswith("plan-")))] | length')
if [ "${EXISTING_PLANS:-0}" -gt 0 ]; then
  : # plan records exist — skip the outline run and resume in 8.5.2
fi
```

Display:
```text
◆ Chunked mode: spawning outline planner... (runs in a subagent — no output until it returns, ~1–5 min; expected, not a freeze)
```

Spawn the planner in **outline-only** mode — it RETURNS the outline table and
records nothing:

```javascript
Agent(
  prompt="{same planning_context as step 8, plus:}

  **Chunked mode: outline-only.**
  Record NO plan in this Task, and write no file.

  Return a markdown table with columns:
  Plan ID | Objective | Wave | Depends On | Requirements

  End the return with a final line `## OUTLINE COMPLETE` — the orchestrator's
  stall-watch greps the agent's own output for that marker.
  Return: ## OUTLINE COMPLETE with plan count.",
  subagent_type="gsd-planner",
  model="{planner_model}",
  description="Outline Phase {phase} (chunked)",
  run_in_background=true
)
```

**ORCHESTRATOR RULE — ALL RUNTIMES:** `TS=$(date +%s)`; repeat `PLANNER_STALL_RESULT=$(gsd_stall_watch "$TS" "{outputFile}" ".beads" "## OUTLINE COMPLETE")` while waiting/active. The outline run touches no artifact, so `{outputFile}`'s marker is its ONLY completion signal — binding it is not optional here (see stall-detection-helpers.md).

Handle return:
- **`marker_received`:** Read the plan list from the agent's returned table. Continue to 8.5.2.
- **`stalled` / any other return or empty:** Display error. Offer: 1) Retry outline, 2) Stop.

### 8.5.2 Per-Plan Tasks (single-plan mode, ~3-5 min each)

For each plan entry from the returned outline table:

1. **Resume check:** Skip if the plan's RECORD already carries a body (resume
   safety) — UNLESS `--reviews` is set, whose purpose is to REPLAN with review
   feedback (§6), so existing records are re-recorded, not skipped (#2762).

   ```bash
   PLAN_BODY=$(bd list -l "phase-${PHASE_NUMBER},plan-${plan_id##*-}" --all --limit 0 --json \
     | jq -r '.[0].description // ""')
   if [ -n "$PLAN_BODY" ] && [[ "$ARGUMENTS" != *"--reviews"* ]]; then
     continue  # resume safety — NOT under --reviews (replan)
   fi
   ```

2. Display:
   ```text
   ◆ Chunked mode: planning {plan_id} ({k}/{N})... (runs in a subagent — no output until it returns, ~1–5 min; expected, not a freeze)
   ```

3. Spawn the planner in **single-plan** mode — it records exactly one plan:
   ```javascript
   Agent(
     prompt="{same planning_context as step 8, plus:}

     **Chunked mode: single-plan.**
     Record exactly ONE plan: cairn/scripts/cairn-record.sh plan --phase {phase_number} --plan {plan_number}
     Plan to record: {plan_id} — {objective}
     Wave: {wave} | Depends on: {depends_on}
     Phase requirement IDs to cover in this plan: {plan_requirements}

     Return: ## PLAN COMPLETE with the plan ID.",
     subagent_type="gsd-planner",
     model="{planner_model}",
     description="Plan {plan_id} (chunked {k}/{N})",
     run_in_background=true
   )
   ```

   **ORCHESTRATOR RULE — ALL RUNTIMES:** `TS=$(date +%s)`; repeat `PLANNER_STALL_RESULT=$(gsd_stall_watch "$TS" "{outputFile}" ".beads" "## PLAN COMPLETE")` while waiting/active — `stalled` falls into step 4 (preserves prior records). The freshness glob is the bd store, because that is where a live planner's output now lands.

4. **Verify the record:** the plan record exists and its body is non-empty.

   ```bash
   bd list -l "phase-${PHASE_NUMBER},plan-${plan_id##*-}" --all --limit 0 --json \
     | jq -e '.[0].description // "" | length > 0' >/dev/null
   ```

   If missing: offer 1) Retry, 2) Stop.

5. **Per-plan durability:** nothing to commit. The record is durable the moment
   `cairn-record.sh` returns — that is what made the per-plan commit necessary
   when the plan was a file, and what makes it redundant now.

After all N plans are recorded, treat this as `## PLANNING COMPLETE` and continue
to step 9.

